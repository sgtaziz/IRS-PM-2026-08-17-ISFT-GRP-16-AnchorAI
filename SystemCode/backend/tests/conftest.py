import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from anchorai.api.main import app
from anchorai.db.seeds import run_seeds
from anchorai.db.session import get_session, make_engine


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    engine = make_engine(f"sqlite:///{tmp_path_factory.mktemp('db') / 'test.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        run_seeds(session, ("base",))
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    def _login(username: str, password: str = "anchorai") -> dict[str, str]:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
