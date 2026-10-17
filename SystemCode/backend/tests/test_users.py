import json


def test_last_admin_is_protected_and_duplicates_rejected(client, login):
    admin = login("admin")
    me = next(
        u for u in client.get("/api/admin/users", headers=admin).json() if u["username"] == "admin"
    )
    for change in ({"role": "manager"}, {"is_active": False}):
        r = client.patch(f"/api/admin/users/{me['id']}", json=change, headers=admin)
        assert r.status_code == 409 and "last active admin" in r.json()["detail"]

    body = {"username": "second", "full_name": "S", "role": "admin", "password": "longenough"}
    assert client.post("/api/admin/users", json=body, headers=admin).status_code == 201
    assert client.post("/api/admin/users", json=body, headers=admin).status_code == 409
    short = body | {"username": "other", "password": "short"}
    assert client.post("/api/admin/users", json=short, headers=admin).status_code == 422

    r = client.patch(f"/api/admin/users/{me['id']}", json={"is_active": False}, headers=admin)
    assert r.status_code == 409 and "own account" in r.json()["detail"]
    assert client.get("/api/admin/users", headers=login("manager")).status_code == 403


def test_audit_never_holds_passwords(client, login, engine):
    from sqlmodel import Session, select

    from anchorai.db.models import AuditLog

    admin = login("admin")
    body = {"username": "temp1", "role": "staff", "password": "s3cret-pass-1"}
    uid = client.post("/api/admin/users", json=body, headers=admin).json()["id"]
    reset = {"password": "s3cret-pass-2"}
    assert (
        client.post(f"/api/admin/users/{uid}/password", json=reset, headers=admin).status_code
        == 204
    )
    login("temp1", "s3cret-pass-2")
    with Session(engine) as session:
        rows = session.exec(select(AuditLog).where(AuditLog.action.like("user.%"))).all()
    assert len(rows) >= 2
    dump = json.dumps([[r.before, r.after] for r in rows])
    assert "s3cret" not in dump and "$2b$" not in dump and "password_hash" not in dump


def test_passwords_are_limited_by_bytes_and_reset_signs_out_old_tokens(client, login):
    admin = login("admin")
    body = {"username": "temp2", "role": "staff", "password": "é" * 37}
    assert client.post("/api/admin/users", json=body, headers=admin).status_code == 422
    body["password"] = "é" * 36
    uid = client.post("/api/admin/users", json=body, headers=admin).json()["id"]
    assert (
        client.post(
            f"/api/admin/users/{uid}/password", json={"password": "日" * 25}, headers=admin
        ).status_code
        == 422
    )

    old = login("temp2", body["password"])
    assert client.get("/api/auth/me", headers=old).status_code == 200
    reset = {"password": "brand-new-pass"}
    assert (
        client.post(f"/api/admin/users/{uid}/password", json=reset, headers=admin).status_code
        == 204
    )
    assert client.get("/api/auth/me", headers=old).status_code == 401
    assert client.get("/api/auth/me", headers=login("temp2", "brand-new-pass")).status_code == 200


def test_reactivating_a_user_does_not_revive_old_tokens(client, login):
    admin = login("admin")
    body = {"username": "temp3", "role": "staff", "password": "longenough"}
    uid = client.post("/api/admin/users", json=body, headers=admin).json()["id"]
    old = login("temp3", "longenough")
    url = f"/api/admin/users/{uid}"
    assert client.patch(url, json={"is_active": False}, headers=admin).status_code == 200
    assert client.get("/api/auth/me", headers=old).status_code == 401
    assert client.patch(url, json={"is_active": True}, headers=admin).status_code == 200
    assert client.get("/api/auth/me", headers=old).status_code == 401
    assert client.get("/api/auth/me", headers=login("temp3", "longenough")).status_code == 200


def test_username_taken_during_hashing_is_a_conflict(client, login, engine, monkeypatch):
    from sqlmodel import Session

    from anchorai.auth import users
    from anchorai.db.models import User

    admin = login("admin")
    real_hash = users.hash_password

    def hash_then_lose_race(password):
        with Session(engine) as other:
            other.add(User(username="racer", password_hash="x", role="staff"))
            other.commit()
        return real_hash(password)

    monkeypatch.setattr(users, "hash_password", hash_then_lose_race)
    body = {"username": "racer", "role": "staff", "password": "longenough"}
    assert client.post("/api/admin/users", json=body, headers=admin).status_code == 409


def test_oversized_ids_are_rejected_not_a_crash(client, login):
    admin = login("admin")
    big = 10**20
    assert client.patch(f"/api/admin/users/{big}", json={}, headers=admin).status_code == 422
    assert client.get(f"/api/admin/audit?offset={big}", headers=admin).status_code == 422
