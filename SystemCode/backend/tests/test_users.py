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
        rows = session.exec(select(AuditLog).where(AuditLog.action.like("user_%"))).all()
    assert len(rows) >= 2
    dump = json.dumps([[r.before, r.after] for r in rows])
    assert "s3cret" not in dump and "$2b$" not in dump and "password_hash" not in dump
