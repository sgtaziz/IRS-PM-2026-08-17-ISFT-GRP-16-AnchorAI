import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from anchorai.api.main import app
from anchorai.db.seeds import run_seeds
from anchorai.db.session import get_session, make_engine
from anchorai.discovery import service
from anchorai.discovery.scores import score_frame
from anchorai.features import FEATURES, build_features
from anchorai.scenario.tables import read_tables, write_tables

FIXTURES = Path(__file__).parent / "fixtures"


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


@pytest.fixture
def built(tmp_path, monkeypatch):
    tables = read_tables(FIXTURES)
    write_tables(tables, tmp_path)
    members = tables["members"]
    features = build_features(members)
    ids = features.index
    segment_ids = pd.Series(np.where(members["churn"] == 1, 0, 1), index=ids)
    segments = pd.DataFrame(
        {
            "segment_id": [0, 1],
            "name": ["At risk", "Steady"],
            "description": ["a", "b"],
            "size": segment_ids.value_counts().sort_index().to_numpy(),
            "churn_rate": [1.0, 0.0],
            "lifetime": [1.0, 4.0],
        }
    )
    probs = pd.Series(np.linspace(0.05, 0.95, len(ids)), index=ids)
    contributions = pd.DataFrame(0.1, index=ids, columns=FEATURES)
    scores = score_frame(members, segment_ids, segments["name"], probs, contributions)
    features.rename_axis("member_id").reset_index().to_parquet(tmp_path / "features.parquet")
    segments.to_parquet(tmp_path / "segments.parquet")
    scores.to_parquet(tmp_path / "member_scores.parquet")
    (tmp_path / "model_card.json").write_text(json.dumps({"n_members": len(ids)}))
    monkeypatch.setattr(service, "generated_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "_cache", None)
    return segments
