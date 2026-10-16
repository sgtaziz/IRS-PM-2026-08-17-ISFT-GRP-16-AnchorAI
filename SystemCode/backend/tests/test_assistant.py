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


def test_shipped_intents_load():
    specs, threshold = load_intents()
    assert {s.name for s in specs} == {
        "member_risk",
        "member_actions",
        "compare_members",
        "graph_impact",
        "plan_summary",
        "what_if_budget",
    }
    assert 0 < threshold < 1 and all(len(s.examples) >= 10 for s in specs)


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


def test_chat_endpoint(client, login, built, monkeypatch, classifier):
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
