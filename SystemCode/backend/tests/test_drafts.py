import pytest
from openai import APIConnectionError

from anchorai.assistant import drafts
from anchorai.assistant.drafts import FORBIDDEN, NUMBER, SMS_LIMIT

CASES = [
    ("M0008", "free_pt_session", "call"),
    ("M0008", "checkin_message", "sms"),
    ("M0008", "discount_1m", "email"),
    ("M0007", "free_pt_session", "in_person"),
]


def post(client, headers, member="M0008", offer="checkin_message", channel="sms"):
    body = {"member_id": member, "offer_id": offer, "channel": channel}
    return client.post("/api/drafts", json=body, headers=headers)


@pytest.fixture
def no_llm(monkeypatch):
    def down(*args, **kwargs):
        raise APIConnectionError(request=None)

    monkeypatch.setattr(drafts, "chat", down)


@pytest.mark.parametrize(("member", "offer", "channel"), CASES)
def test_template_uses_only_evidence(client, login, built, no_llm, member, offer, channel):
    r = post(client, login("staff1"), member, offer, channel)
    assert r.status_code == 200
    d = r.json()
    assert d["source"] == "template" and d["channel"] == channel
    assert not FORBIDDEN.search(d["text"] + (d["subject"] or ""))
    evidence_numbers = set(NUMBER.findall(" ".join(d["evidence"])))
    assert set(NUMBER.findall(d["text"] + (d["subject"] or ""))) <= evidence_numbers
    assert (d["subject"] is not None) == (channel == "email")
    if channel == "sms":
        assert len(d["text"]) <= SMS_LIMIT


def test_llm_text_is_used_when_clean(client, login, built, monkeypatch):
    monkeypatch.setattr(drafts, "chat", lambda *a, **k: "Hi, we'd love to see you again.")
    d = post(client, login("manager")).json()
    assert d["source"] == "llm" and d["text"].startswith("Hi")


@pytest.mark.parametrize(
    "reply",
    [
        "Hi, you are at risk of leaving.",
        "Hi, enjoy 50% off!",
        "We hate to see you leaving.",
        "You are a high-value member.",
        "Hi from the New and slipping group.",
        "Hi, this is [Gym Name].",
        "x" * (SMS_LIMIT + 1),
        "",
    ],
)
def test_unsafe_llm_output_falls_back(client, login, built, monkeypatch, reply):
    monkeypatch.setattr(drafts, "chat", lambda *a, **k: reply)
    assert post(client, login("staff1")).json()["source"] == "template"


def test_unknown_blocked_and_roles(client, login, built, no_llm):
    staff = login("staff1")
    assert post(client, staff, member="NOPE").status_code == 404
    assert post(client, staff, offer="nope").status_code == 422
    assert post(client, staff, channel="pigeon").status_code == 422
    assert post(client, staff, member="M0005").status_code == 409
    assert client.post("/api/drafts", json={}).status_code == 401


def test_inactive_offer_and_unsupported_channel(client, login, built, no_llm, engine):
    from sqlmodel import Session

    from anchorai.db.models import OfferCatalog

    staff, manager = login("staff1"), login("manager")
    assert post(client, staff, offer="checkin_message", channel="call").status_code == 409
    with Session(engine) as s:
        row = s.get(OfferCatalog, "checkin_message")
        row.active = False
        s.add(row)
        s.commit()
    try:
        r = post(client, staff)
        assert r.status_code == 409 and "not active" in r.json()["detail"]
        item = {"member_id": "M0008", "offer_id": "checkin_message", "channel": "sms"}
        checked = client.post("/api/rules/check", json={"items": [item]}, headers=manager).json()[0]
        assert checked["offer_active"] is False and checked["allowed"] is True
        glossary = client.get("/api/rules/glossary", headers=staff).json()
        assert "checkin_message" not in glossary["offer_channels"]
    finally:
        with Session(engine) as s:
            row = s.get(OfferCatalog, "checkin_message")
            row.active = True
            s.add(row)
            s.commit()
