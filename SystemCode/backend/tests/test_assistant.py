import json
from datetime import date

import numpy as np
import pytest
from openai import APIConnectionError
from sqlmodel import Session

from anchorai.assistant import service
from anchorai.assistant.classifier import IntentClassifier, IntentSpec, load_intents
from anchorai.assistant.prompt import DONT_KNOW
from anchorai.assistant.service import HistoryTurn, answer
from anchorai.assistant.slots import extract_slots

INSTRUCTORS = {"Maya Chen": "I04", "Sam Rivera": "I01"}
CLASSES = {"HIIT": "K02", "Core": "K08"}


@pytest.mark.parametrize(
    ("text", "members", "amount"),
    [
        ("what happens if the budget drops to 1000", [], 1000.0),
        ("Is it worth spending $4000 instead of $2000?", [], 4000.0),
        ("Run the plan with a $3k budget", [], 3000.0),
        ("What does a 1500 dollar budget buy us?", [], 1500.0),
        ("Why was 1043 picked over 2210?", ["M1043", "M2210"], None),
        ("compare member 155 with M0155", ["M0155"], None),
        ("what's 2 plus 2", [], None),
        ("top 10 members at risk in 2026", [], None),
        ("week 42 plan for 12 months", [], None),
    ],
)
def test_money_never_becomes_a_member(text, members, amount):
    slots, _ = extract_slots(text, INSTRUCTORS, CLASSES)
    assert slots.member_ids == members and slots.amount == amount


def test_names_and_common_word_classes():
    slots, text = extract_slots("who goes to Maya's hiit class", INSTRUCTORS, CLASSES)
    assert slots.instructor_ids == ["I04"] and slots.class_ids == ["K02"]
    assert "INSTRUCTOR" in text and "CLASS" in text
    # Common words aren't classes or instructors unless the question makes them so.
    assert extract_slots("our core problem is churn", INSTRUCTORS, CLASSES)[0].class_ids == []
    assert extract_slots("Core members at risk?", INSTRUCTORS, CLASSES)[0].class_ids == []
    assert extract_slots("i'm sam, from sales", INSTRUCTORS, CLASSES)[0].instructor_ids == []


@pytest.mark.parametrize(
    ("text", "limit", "filters"),
    [
        ("who are the top 10 members at risk?", 10, {}),
        ("first five members to call", 5, {}),
        ("high risk members in club C2", None, {"risk_band": "high", "club_id": "C2"}),
        ("show me new members who are slipping", None, {"new_members": True}),
        ("which solo trainers are at risk", None, {"segment": "solo trainers"}),
        ("show the 30 riskiest", 30, {}),
        ("which members should we call this week", None, {}),
        ("what if budget $2000 top 15 members", 15, {}),
        ("who is at risk in the next 3 weeks", None, {}),
    ],
)
def test_list_slots(text, limit, filters):
    slots, normalised = extract_slots(text, INSTRUCTORS, CLASSES)
    assert slots.limit == limit and slots.member_ids == []
    assert slots.amount == (2000.0 if "$2000" in text else None)
    for field, value in filters.items():
        assert getattr(slots, field) == value
    assert limit is None or "COUNT" in normalised


def bag_of_words(texts):
    vocab = ["risk", "offer", "compare", "budget", "plan", "affected", "member"]
    rows = np.array([[t.lower().count(w) for w in vocab] for t in texts], dtype=float) + 1e-9
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


@pytest.fixture
def classifier():
    specs = [
        IntentSpec("member_risk", "", ["MEMBER risk"], (1, 1)),
        IntentSpec("compare_members", "", ["compare MEMBER MEMBER risk"], (2, 9)),
        IntentSpec("plan_summary", "", ["plan"]),
    ]
    return IntentClassifier(bag_of_words, specs, 0.5, INSTRUCTORS, CLASSES)


def test_slot_rule_and_threshold(classifier):
    assert classifier.classify("compare risk for M0001").intent == "member_risk"
    assert classifier.classify("compare risk M0001 vs M0002").intent == "compare_members"
    assert classifier.classify("why the risk?", context_member_id="M0003").slots.member_ids == [
        "M0003"
    ]
    assert classifier.classify("weather tomorrow").intent == "unknown"
    # On M0003's page, naming one more member makes a comparison of the two.
    paired = classifier.classify("compare risk vs M0002", context_member_id="M0003")
    assert paired.intent == "compare_members" and paired.slots.member_ids == ["M0003", "M0002"]


def test_write_requests_are_unknown(classifier):
    for text in ("Delete member M0012", "please remove M0001 from the plan", "update M0003 risk"):
        assert classifier.classify(text).intent == "unknown"
    assert classifier.classify("why is M0001 at risk and not deleted").intent == "member_risk"


def test_shipped_intents_load():
    specs, threshold = load_intents()
    assert {s.name for s in specs} == {
        "member_risk",
        "member_actions",
        "compare_members",
        "graph_impact",
        "list_members",
        "plan_summary",
        "what_if_budget",
    }
    assert 0 < threshold < 1 and all(len(s.examples) >= 10 for s in specs)


def test_list_members_tool(built, engine):
    from anchorai.assistant.slots import Slots
    from anchorai.assistant.tools import list_members

    with Session(engine) as session:
        top = list_members(session, Slots(limit=3))
        assert top.evidence[0].ref is None and "Showing the 3 members" in top.evidence[0].text
        members = top.evidence[1:]
        assert len(members) == 3 and all(e.kind == "member" and e.ref for e in members)
        probs = [float(e.text.split("probability ")[1].split("%")[0].strip("<>")) for e in members]
        assert probs == sorted(probs, reverse=True)
        # No limit means 10; a huge one shows everything up to 25 (the fixture has 12 members).
        assert len(list_members(session, Slots()).evidence) == 11
        assert len(list_members(session, Slots(limit=999)).evidence) == 13
        assert "(high risk)" in list_members(session, Slots(risk_band="high")).evidence[1].text
        nothing = list_members(session, Slots(club_id="C99"))
        assert not nothing.evidence and nothing.note


def test_answer_is_grounded_and_degrades(built, engine, classifier):
    with Session(engine) as session:
        prompts = []
        reply = answer(
            session,
            "M0001 risk",
            classifier=classifier,
            chat=lambda m: prompts.append(m) or "ok [E1]",
        )
        assert reply.intent == "member_risk" and reply.grounded and reply.llm_used
        assert reply.evidence[0].id == "E1" and reply.evidence[0].ref == "M0001"
        assert "[E1] M0001: churn probability" in prompts[0][1]["content"]

        def down(_):
            raise APIConnectionError(request=None)

        fallback = answer(session, "M0001 risk", classifier=classifier, chat=down)
        assert fallback.grounded and not fallback.llm_used and "[E1]" in fallback.answer

        never = lambda _: pytest.fail("LLM must not be called")
        assert answer(session, "weather", classifier=classifier, chat=never).answer == DONT_KNOW
        missing = answer(session, "M9999 risk", classifier=classifier, chat=never)
        assert missing.answer == "I couldn't find member M9999." and not missing.grounded
        plan = answer(session, "plan", role="manager", classifier=classifier, chat=never)
        assert plan.answer.startswith("No weekly plan")
        staff_plan = answer(session, "plan", role="staff", classifier=classifier, chat=never)
        assert staff_plan.answer == "Plan details are only available to managers."


def test_follow_ups_continue_the_previous_turn(built, engine, classifier):
    risk = HistoryTurn(
        question="M0001 risk",
        answer="High risk [E1][E2].",
        intent="member_risk",
        slots={"member_ids": ["M0001"], "instructor_ids": ["I99"]},
    )
    with Session(engine) as session:
        prompts = []
        reply = answer(
            session,
            "explain that simply",
            history=[risk],
            classifier=classifier,
            chat=lambda m: prompts.append(m) or "ok [E1]",
        )
        assert reply.follow_up and reply.intent == "member_risk"
        assert reply.slots.member_ids == ["M0001"] and reply.slots.instructor_ids == []
        # Earlier turns go in as chat messages, without their stale evidence ids.
        assert [m["role"] for m in prompts[0]] == ["system", "user", "assistant", "user"]
        assert prompts[0][2]["content"] == "High risk."

        def down(_):
            raise APIConnectionError(request=None)

        other = answer(session, "and M0002?", history=[risk], classifier=classifier, chat=down)
        assert other.slots.member_ids == ["M0002"] and "[E1]" in other.answer
        offline = answer(session, "say more", history=[risk], classifier=classifier, chat=down)
        assert offline.grounded and "offline" in offline.answer

        never = lambda _: pytest.fail("LLM must not be called")
        thanks = answer(session, "thanks!", history=[risk], classifier=classifier, chat=never)
        assert thanks.answer == DONT_KNOW and not thanks.follow_up

        plan = HistoryTurn(question="plan", answer="x", intent="plan_summary")
        blocked = answer(session, "and then?", history=[plan], classifier=classifier)
        assert blocked.answer == "Plan details are only available to managers."


def test_chat_and_feedback_endpoints(client, login, built, monkeypatch, classifier):
    monkeypatch.setattr(service, "get_classifier", lambda: classifier)
    monkeypatch.setattr(service.llm, "chat", lambda m: "answer [E1]")
    staff = login("staff1")
    assert client.post("/api/assistant/chat", json={"message": "x"}).status_code == 401
    r = client.post(
        "/api/assistant/chat", json={"message": "why the risk", "member_id": "M0002"}, headers=staff
    )
    assert r.status_code == 200
    body = r.json()
    assert (
        body["intent"] == "member_risk"
        and body["evidence"]
        and body["slots"]["member_ids"] == ["M0002"]
    )
    fb = {"message": "why the risk", "answer": body["answer"], "intent": "member_risk", "rating": 1}
    assert client.post("/api/assistant/feedback", json=fb, headers=staff).status_code == 200
    assert (
        client.post("/api/assistant/feedback", json=fb | {"rating": 5}, headers=staff).status_code
        == 422
    )


def sse(response):
    events = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


def test_chat_stream_endpoint(client, login, built, monkeypatch, classifier):
    monkeypatch.setattr(service, "get_classifier", lambda: classifier)
    staff = login("staff1")
    body = {"message": "why the risk", "member_id": "M0002"}
    assert client.post("/api/assistant/chat/stream", json=body).status_code == 401

    monkeypatch.setattr(service.llm, "chat_stream", lambda m: iter(["High ", "risk [E1]."]))
    events = sse(client.post("/api/assistant/chat/stream", json=body, headers=staff))
    assert [e for e, _ in events] == ["meta", "delta", "delta", "done"]
    meta, done = events[0][1], events[-1][1]
    assert meta["intent"] == "member_risk" and meta["tool"] and meta["evidence"][0]["id"] == "E1"
    assert "answer" not in meta
    assert done == {"grounded": True, "llm_used": True, "answer": "High risk [E1]."}

    def broken(_):
        yield "partial "
        raise APIConnectionError(request=None)

    monkeypatch.setattr(service.llm, "chat_stream", broken)
    events = sse(client.post("/api/assistant/chat/stream", json=body, headers=staff))
    done = events[-1][1]
    assert not done["llm_used"] and done["grounded"] and "[E1]" in done["answer"]
    # The template replaces the partial text through `done`; it is never appended as a delta.
    assert [e for e, _ in events] == ["meta", "delta", "done"]
    assert events[1][1] == {"text": "partial "}

    monkeypatch.setattr(service.llm, "chat_stream", lambda m: pytest.fail("no LLM"))
    unknown = sse(
        client.post("/api/assistant/chat/stream", json={"message": "weather"}, headers=staff)
    )
    assert [e for e, _ in unknown] == ["meta", "delta", "done"]
    assert unknown[-1][1] == {"grounded": False, "llm_used": False, "answer": DONT_KNOW}


def explanation(member_id, **overrides):
    base = {
        "explanation_id": f"X-{member_id}",
        "member_id": member_id,
        "churn_prob": 0.6,
        "top_drivers": [["lifetime", 0.4]],
        "rule_trace": [],
        "similar_cases": [
            {"outcome": "retained after a call"},
            {"outcome": "left"},
            {"outcome": "x"},
        ],
        "graph_signals": ["A class they attend has been cancelled"],
        "summary": "Picked for a call because visits dropped.",
    }
    return base | overrides


@pytest.fixture
def plan(engine):
    from sqlmodel import delete

    from anchorai.db.models import Plan, PlanItem

    with Session(engine) as session:
        row = Plan(week_start=date(2099, 1, 5), status="draft")
        session.add(row)
        session.commit()
        session.add_all(
            [
                PlanItem(
                    plan_id=row.id,
                    member_id="M0001",
                    offer_id="free_pt_session",
                    channel="call",
                    expected_value=0.12,
                    explanation_id="X-M0001",
                    explanation=explanation("M0001"),
                ),
                PlanItem(
                    plan_id=row.id,
                    member_id="M0002",
                    offer_id="checkin_message",
                    channel="sms",
                    expected_value=0.05,
                    explanation_id="X-M0002",
                    removed=True,
                    override_reason="member asked not to be contacted",
                ),
                PlanItem(
                    plan_id=row.id,
                    member_id="M0003",
                    offer_id="checkin_message",
                    channel="sms",
                    expected_value=0.05,
                    explanation_id="X-M0003",
                    explanation={"summary": "incomplete"},
                ),
            ]
        )
        session.commit()
        plan_id = row.id
    yield
    with Session(engine) as session:
        session.exec(delete(PlanItem).where(PlanItem.plan_id == plan_id))
        session.exec(delete(Plan).where(Plan.id == plan_id))
        session.commit()


def texts(reply, kind="plan"):
    return [e.text for e in reply.evidence if e.kind == kind]


def test_member_answers_show_plan_status(built, engine, classifier, plan):
    never = lambda _: "ok"
    with Session(engine) as session:
        reply = answer(session, "M0001 risk", role="manager", classifier=classifier, chat=never)
        assert reply.intent == "member_risk"
        lines = texts(reply)
        assert lines[0] == (
            "M0001 is in the plan for the week of 2099-01-05: "
            "Free personal training session by phone call, expected value 0.12"
        )
        assert any("Picked for a call" in t for t in lines)
        assert len([t for t in lines if "similar past case" in t]) == 2
        assert any("plan graph signal" in t for t in lines)

        out = answer(session, "M0004 risk", role="manager", classifier=classifier, chat=never)
        assert texts(out) == ["M0004 is not in the plan for the week of 2099-01-05"]

        removed = answer(session, "M0002 risk", role="manager", classifier=classifier, chat=never)
        assert any("removed" in t and "asked not to be contacted" in t for t in texts(removed))

        # A malformed stored explanation leaves just the plan line.
        broken = answer(session, "M0003 risk", role="manager", classifier=classifier, chat=never)
        assert len(texts(broken)) == 1 and "is in the plan" in texts(broken)[0]

        staff = answer(session, "M0001 risk", role="staff", classifier=classifier, chat=never)
        assert not texts(staff)
        assert [e.id for e in staff.evidence] == [f"E{i + 1}" for i in range(len(staff.evidence))]


def test_compare_one_in_one_out(built, engine, classifier, plan):
    with Session(engine) as session:
        reply = answer(
            session,
            "compare M0001 and M0004",
            role="manager",
            classifier=classifier,
            chat=lambda _: "ok",
        )
        assert reply.intent == "compare_members"
        lines = texts(reply)
        assert any(t.startswith("M0001 is in the plan") for t in lines)
        assert "M0004 is not in the plan for the week of 2099-01-05" in lines
        assert any("Picked for a call" in t for t in lines)


def test_no_plan_lines_without_a_plan(built, engine, classifier):
    with Session(engine) as session:
        reply = answer(
            session, "M0001 risk", role="manager", classifier=classifier, chat=lambda _: "ok"
        )
        assert reply.grounded and not texts(reply)
