from sqlmodel import Session, select

from anchorai.db.models import AuditLog


def test_login_returns_token_and_user(client):
    r = client.post("/api/auth/login", json={"username": "manager", "password": "anchorai"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["user"]["role"] == "manager"


def test_bad_password_and_unknown_user_look_the_same(client):
    wrong = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    unknown = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_a_valid_token(client, login):
    assert client.get("/api/auth/me").status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert client.get("/api/auth/me", headers=bad).status_code == 401
    assert client.get("/api/auth/me", headers=login("staff1")).json()["username"] == "staff1"


def test_role_enforcement(client, login):
    assert client.post("/api/plan", json={}).status_code == 401
    assert client.post("/api/plan", json={}, headers=login("staff1")).status_code == 403
    # Manager passes the role check and reaches the (unimplemented) handler or validation.
    assert client.post("/api/plan", json={}, headers=login("manager")).status_code not in (401, 403)
    assert client.put("/api/rules/x", json={}, headers=login("manager")).status_code == 403
    assert client.get("/api/health").status_code == 200


def test_login_is_audited(client, engine):
    client.post("/api/auth/login", json={"username": "staff2", "password": "anchorai"})
    with Session(engine) as session:
        entry = session.exec(select(AuditLog).where(AuditLog.username == "staff2")).first()
    assert entry is not None and entry.action == "login"
