from sqlmodel import Session, select

from anchorai.db.models import AuditLog
from anchorai.discovery import service


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


def test_reseeding_keeps_admin_offer_deletions(engine):
    from anchorai.db.models import OfferCatalog
    from anchorai.db.seeds import run_seeds

    with Session(engine) as session:
        assert session.get(OfferCatalog, "discount_1m") is not None
        session.delete(session.get(OfferCatalog, "discount_1m"))
        session.commit()
        run_seeds(session, ("base", "demo"))
        assert session.get(OfferCatalog, "discount_1m") is None
        assert session.get(OfferCatalog, "checkin_message") is not None


def test_deactivated_staff_leave_the_roster(client, login, engine):
    from anchorai.db.models import User

    admin = login("admin")
    with Session(engine) as session:
        staff2 = session.exec(select(User).where(User.username == "staff2")).one()
        staff2.is_active = False
        session.add(staff2)
        session.commit()
        staff_id = staff2.id
    try:
        roster = client.get("/api/admin/offers", headers=admin).json()["staff"]
        assert "staff2" not in {r["username"] for r in roster} and roster
        change = {"weekly_hours": 10, "skills": []}
        r = client.put(f"/api/admin/offers/staff/{staff_id}", json=change, headers=admin)
        assert r.status_code == 404
    finally:
        with Session(engine) as session:
            staff2 = session.get(User, staff_id)
            staff2.is_active = True
            session.add(staff2)
            session.commit()
