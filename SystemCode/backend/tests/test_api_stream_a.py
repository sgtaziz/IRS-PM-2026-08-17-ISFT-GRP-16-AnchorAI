import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlmodel import Session, select

from anchorai.db.models import AuditLog
from anchorai.discovery import service
from anchorai.discovery.scores import score_frame
from anchorai.features import FEATURES, build_features
from anchorai.scenario.tables import read_tables, write_tables

FIXTURES = Path(__file__).parent / "fixtures"


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


def test_member_list_pages_sorts_and_filters(client, login, built):
    manager = login("manager")
    r = client.get(
        "/api/members", params={"page_size": 5, "sort": "churn_prob"}, headers=manager
    ).json()
    assert r["total"] == 12 and len(r["items"]) == 5
    assert [i["churn_prob"] for i in r["items"]] == sorted(
        (i["churn_prob"] for i in r["items"]), reverse=True
    )
    steady = client.get("/api/members", params={"segment": "Steady"}, headers=manager).json()
    assert steady["total"] == int(built.loc[1, "size"])
    csv = client.get("/api/members/export.csv", params={"risk_band": "high"}, headers=manager)
    assert csv.text.splitlines()[0].startswith("member_id,segment_id")


def test_member_endpoints_enforce_roles(client, login, built):
    staff = login("staff1")
    assert client.get("/api/members", headers=staff).status_code == 403
    assert client.get("/api/members/segments", headers=staff).status_code == 403
    detail = client.get("/api/members/M0002", headers=staff)
    assert detail.status_code == 200 and detail.json()["score"]["member_id"] == "M0002"
    assert client.get("/api/members/search", params={"q": "M000"}, headers=staff).json()
    assert client.get("/api/members/M9999", headers=staff).status_code == 404


def test_members_report_unbuilt_data(client, login, tmp_path, monkeypatch):
    monkeypatch.setattr(service, "generated_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "_cache", None)
    r = client.get("/api/members", headers=login("manager"))
    assert r.status_code == 503 and "data build" in r.json()["detail"]


def test_offer_writes_are_admin_only_and_audited(client, login, engine):
    offer = {
        "offer_id": "trial_class",
        "name": "Trial class",
        "cost": 5.0,
        "staff_minutes": 5,
        "channels": ["sms"],
    }
    assert (
        client.post("/api/admin/offers/offers", json=offer, headers=login("manager")).status_code
        == 403
    )
    admin = login("admin")
    assert client.post("/api/admin/offers/offers", json=offer, headers=admin).status_code == 201
    assert client.post("/api/admin/offers/offers", json=offer, headers=admin).status_code == 409
    bad = {**offer, "offer_id": "x", "channels": ["fax"]}
    assert client.post("/api/admin/offers/offers", json=bad, headers=admin).status_code == 422
    view = client.get("/api/admin/offers", headers=admin).json()
    assert "trial_class" in {o["offer_id"] for o in view["offers"]}
    staff = view["staff"][0]
    change = {"weekly_hours": 12, "skills": ["calls"]}
    r = client.put(f"/api/admin/offers/staff/{staff['user_id']}", json=change, headers=admin)
    assert r.json()["weekly_hours"] == 12
    assert client.delete("/api/admin/offers/offers/trial_class", headers=admin).status_code == 204
    with Session(engine) as session:
        actions = set(session.exec(select(AuditLog.action)))
    assert {"offer.create", "offer.delete", "staff.update"} <= actions
