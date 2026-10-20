import time
from datetime import date, timedelta

import pandas as pd
import pytest
from sqlmodel import Session, func, select

from anchorai import catalog
from anchorai.catalog import StaffIn
from anchorai.cbr.reasoner import load_case_base
from anchorai.db.models import Assignment, AuditLog, Outcome, Plan, PlanItem, User
from anchorai.optimisation import assignment, contacts, jobs, overrides
from anchorai.optimisation.baselines import POLICIES
from anchorai.optimisation.evaluate import Truth, evaluate
from anchorai.optimisation.exact import solve_full, solve_linear
from anchorai.optimisation.ga import build_problem, chosen, ga, objective
from anchorai.optimisation.model import Limits, plan_value, violations
from anchorai.reasoning.service import all_facts
from anchorai.schemas import PlanRequest


@pytest.fixture
def options():
    rows = [
        ("M1", "free_pt_session", 40.0, 60, "trainer", 0, 0.9, 0.30),
        ("M1", "checkin_message", 0.0, 5, "", 1, 0.9, 0.05),
        ("M2", "free_pt_session", 40.0, 60, "trainer", 0, 0.8, 0.25),
        ("M3", "class_pass", 15.0, 10, "", 0, 0.7, 0.10),
        ("M4", "discount_1m", 12.0, 15, "", 0, 0.6, 0.08),
        ("M4", "checkin_message", 0.0, 5, "", 1, 0.6, 0.02),
        ("M5", "checkin_message", 0.0, 5, "", 0, 0.5, 0.03),
    ]
    cols = ["member_id", "offer_id", "cost", "staff_minutes", "required_skill", "rank"]
    frame = pd.DataFrame(rows, columns=[*cols, "churn_prob", "est_uplift"])
    frame["monthly_value"] = 72.0
    frame["value"] = frame["est_uplift"] * frame["monthly_value"] * 6 - frame["cost"]
    return frame


TIGHT = Limits(budget=50, staff_minutes=80, trainer_minutes=60, stock={"free_pt_session": 1})
# One case per limit, each the only tight one, so dropping any check from `fill` breaks a plan.
LOOSE = {"budget": 1000.0, "staff_minutes": 1000, "trainer_minutes": 1000}
BINDING = {
    "budget": Limits(**{**LOOSE, "budget": 45}),
    "staff minutes": Limits(**{**LOOSE, "staff_minutes": 70}),
    "trainer minutes": Limits(**{**LOOSE, "trainer_minutes": 60}),
    "stock": Limits(**LOOSE, stock={"free_pt_session": 1}),
}


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("limit", BINDING)
def test_baseline_plans_are_feasible(options, policy, limit):
    plan = POLICIES[policy](options, BINDING[limit], 0)
    assert len(plan) > 0
    assert violations(plan, options, BINDING[limit]) == {}


def test_violations_name_every_broken_limit(options):
    plan = options.loc[[0, 1, 2]]  # M1 twice, two PT sessions
    assert set(violations(plan, options, TIGHT)) == {
        "members contacted twice",
        "budget ($)",
        "staff minutes",
        "trainer minutes",
        "free_pt_session stock",
    }


def test_evaluator_adds_true_uplift_to_the_no_contact_baseline(options):
    truth = Truth(
        uplift=pd.Series(
            [0.2, 0.1, -0.05],
            index=pd.MultiIndex.from_tuples(
                [("M1", "free_pt_session"), ("M3", "class_pass"), ("M4", "discount_1m")]
            ),
        ),
        stay_if_left_alone=pd.Series(
            [0.5, 0.6, 0.7, 0.8, 0.9], index=["M1", "M2", "M3", "M4", "M5"]
        ),
    )
    result = evaluate(options.loc[[0, 3, 4]], truth)
    assert result["extra_retained"] == pytest.approx(0.25)
    assert result["members_retained"] == pytest.approx(3.5 + 0.25)
    assert result["spend"] == 67.0


def test_plan_endpoint_saves_a_feasible_plan(client, login, built, engine):
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "greedy"}

    assert client.post("/api/plan", json=request, headers=login("staff1")).status_code == 403
    assert client.get("/api/plan/latest", headers=login("manager")).status_code == 404

    r = client.post("/api/plan", json=request, headers=login("manager"))
    assert r.status_code == 200, r.text
    plan = r.json()
    members = [i["member_id"] for i in plan["items"]]
    assert members and len(members) == len(set(members))
    assert plan["total_cost"] <= 100 and plan["total_staff_minutes"] <= 150
    assert plan["status"] == "draft"

    latest = client.get("/api/plan/latest", headers=login("manager")).json()
    assert latest["id"] == plan["id"] and latest["items"] == plan["items"]
    with Session(engine) as session:
        audit = session.exec(select(AuditLog).where(AuditLog.action == "plan.create")).one()
    assert audit.entity_id == str(plan["id"])

    by_ga = client.post(
        "/api/plan", json={**request, "solver": "ga"}, headers=login("manager")
    ).json()
    assert by_ga["total_cost"] <= 100 and by_ga["total_staff_minutes"] <= 150
    assert by_ga["solver_stats"]["solver"] == "ga"

    item = plan["items"][0]
    assert all("churn risk" in i["reason"] for i in plan["items"]), (
        "every row has a one-line reason"
    )
    why = client.get(f"/api/plan/explanations/{item['explanation_id']}", headers=login("manager"))
    assert why.status_code == 200, why.text
    why = why.json()
    assert why["member_id"] == item["member_id"] and why["summary"]
    assert why["rule_trace"], "the rules that allowed the offer are part of the reason"
    cases = why["similar_cases"]
    assert cases and all(c["outcome"] for c in cases)
    assert item["member_id"] not in {c["member_id"] for c in cases}
    missing = client.get("/api/plan/explanations/nope", headers=login("manager"))
    assert missing.status_code == 404

    unknown = client.post("/api/plan", json={**request, "solver": "nope"}, headers=login("manager"))
    assert unknown.status_code == 422


@pytest.mark.parametrize("limit", BINDING)
def test_ga_plans_are_feasible(options, limit):
    cohorts = pd.DataFrame(
        {
            "member_id": ["M1", "M2", "M3", "M4"],
            "class_id": ["K1", "K1", "K1", "K2"],
            "weight": 1.0,
            "instructor_id": ["I1", "I1", "I1", "I2"],
        }
    )
    plan = ga(options, BINDING[limit], seed=0, cohorts=cohorts, generations=20, pop_size=20)
    assert len(plan) > 0
    assert violations(plan, options, BINDING[limit]) == {}


@pytest.mark.parametrize("limit", BINDING)
def test_exact_plans_are_feasible_and_at_least_as_good_as_greedy(options, limit):
    plan, status, _ = solve_linear(options, BINDING[limit])
    assert status == "OPTIMAL"
    assert violations(plan, options, BINDING[limit]) == {}
    assert plan_value(plan) >= plan_value(POLICIES["greedy-uplift"](options, BINDING[limit])) - 1e-6


def test_exact_full_model_scores_its_plan_like_the_ga_objective(options):
    cohorts = pd.DataFrame(
        {
            "member_id": ["M1", "M2", "M3", "M4"],
            "class_id": ["K1", "K1", "K1", "K2"],
            "weight": 1.0,
            "instructor_id": ["I1", "I1", "I1", "I1"],
        }
    )
    limits = BINDING["staff minutes"]
    problem = build_problem(options, cohorts, limits)
    genes, status, _, bound = solve_full(problem, limits, beta=0.5, decay=0.2)
    assert status == "OPTIMAL"
    assert objective(problem, chosen(problem, genes), 0.5, 0.2) == pytest.approx(bound, abs=0.05)


def test_staff_can_read_similar_cases_and_contact_history(client, login, built):
    staff = login("staff1")
    r = client.get("/api/plan/similar-cases/M0001", headers=staff)
    assert r.status_code == 200, r.text
    evidence = r.json()
    assert evidence and all(e["cases"] for e in evidence)
    assert [e["estimate"] for e in evidence] == sorted(
        (e["estimate"] for e in evidence), reverse=True
    )
    assert "M0001" not in {c["member_id"] for e in evidence for c in e["cases"]}
    assert client.get("/api/plan/similar-cases/NOPE", headers=staff).status_code == 404

    # A draft plan is not a contact: history only lists approved plans.
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "greedy"}
    assert client.post("/api/plan", json=request, headers=login("manager")).status_code == 200
    history = client.get("/api/outcomes", params={"member_id": "M0001"}, headers=staff)
    assert history.status_code == 200 and history.json() == []
    assert (
        client.get("/api/outcomes", params={"member_id": "NOPE"}, headers=staff).status_code == 404
    )


def test_overrides_are_checked_audited_and_locked_by_approval(client, login, built, engine):
    manager = login("manager")
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "greedy"}
    plan = client.post("/api/plan", json=request, headers=manager).json()
    pid, first = plan["id"], plan["items"][0]["member_id"]

    def post(path, body):
        return client.post(f"/api/plan/{pid}{path}", json=body, headers=manager)

    removed = post(f"/items/{first}/remove", {"reason": "already called on Monday"})
    assert removed.status_code == 200, removed.text
    assert first not in {i["member_id"] for i in removed.json()["items"]}
    assert removed.json()["total_cost"] <= plan["total_cost"]

    # Guardrail (G03): discounts are for month-to-month members only.
    blocked = post(
        "/items",
        {"member_id": "M0007", "offer_id": "discount_1m", "channel": "email", "reason": "try it"},
    )
    assert blocked.status_code == 422
    assert "G03" in blocked.json()["detail"]
    # No phone on file: an SMS cannot reach them (HANDOFFS #30 guard).
    no_phone = next(m for m, f in all_facts().items() if not f.get("phone"))
    sms = post(
        "/items",
        {
            "member_id": no_phone,
            "offer_id": "checkin_message",
            "channel": "sms",
            "reason": "quick hello",
        },
    )
    assert sms.status_code == 422
    assert "no phone" in sms.json()["detail"]
    short = {"member_id": first, "offer_id": "checkin_message", "channel": "email", "reason": "x"}
    assert post("/items", short).status_code == 422, "a reason is mandatory"

    added = post(
        "/items",
        {
            "member_id": first,
            "offer_id": "checkin_message",
            "channel": "email",
            "reason": "staff asked for it",
        },
    )
    assert added.status_code == 200, added.text
    item = next(i for i in added.json()["items"] if i["member_id"] == first)
    why = client.get(f"/api/plan/explanations/{item['explanation_id']}", headers=manager).json()
    assert why["summary"].startswith("Added by the manager: staff asked for it.")

    assert post("/approve", {}).status_code == 200
    locked = post(f"/items/{first}/remove", {"reason": "too late now"})
    assert locked.status_code == 409
    with Session(engine) as session:
        actions = {a.action for a in session.exec(select(AuditLog)).all()}
    assert {"plan_item.remove", "plan_item.add", "plan.approve"} <= actions
    assert client.post(f"/api/plan/{pid}/approve", headers=login("staff1")).status_code == 403


def test_assignment_respects_skills_and_hours(engine):
    with Session(engine) as session:
        manager = session.exec(select(User).where(User.username == "manager")).one()
        staff = {s.username: s for s in catalog.list_staff(session)}
        original = {
            s.user_id: StaffIn(weekly_hours=s.weekly_hours, skills=s.skills) for s in staff.values()
        }
        # One hour each: staff1 is the only trainer, both can make calls.
        catalog.update_staff(
            session,
            manager,
            staff["staff1"].user_id,
            StaffIn(weekly_hours=1, skills=["trainer", "calls"]),
        )
        catalog.update_staff(
            session, manager, staff["staff2"].user_id, StaffIn(weekly_hours=1, skills=["calls"])
        )
        plan = Plan(week_start=date(2026, 10, 19), status="approved", request={})
        session.add(plan)
        session.flush()
        contacts = (
            [("free_pt_session", "call")] * 2
            + [("discount_1m", "call")] * 3
            + [("checkin_message", "sms")] * 4
        )
        for k, (offer, channel) in enumerate(contacts):
            session.add(
                PlanItem(
                    plan_id=plan.id,
                    member_id=f"M9{k:03d}",
                    offer_id=offer,
                    channel=channel,
                    expected_value=100 - k,
                    explanation_id=f"x{k}",
                )
            )
        session.commit()

        result = assignment.assign(session, manager, plan.id)
        by_name = {s["full_name"]: s for s in result["staff"]}
        trainer = next(s for s in result["staff"] if "trainer" in s["skills"])
        caller = next(s for s in result["staff"] if "trainer" not in s["skills"])
        assert [c["offer_id"] for c in trainer["contacts"]].count("free_pt_session") == 1
        assert all(c["offer_id"] != "free_pt_session" for c in caller["contacts"])
        # The second PT session does not fit the trainer's hour; the caller's hour holds 3 calls (45 min)
        # and 3 of the 4 SMS check-ins (15 min), so the least valuable check-in is left over too.
        assert result["unassigned"] == ["M9001", "M9008"]
        assert all(s["minutes_used"] <= s["minutes_capacity"] for s in by_name.values())
        with pytest.raises(assignment.CannotAssign):
            assignment.reassign(
                session, manager, plan.id, trainer["contacts"][0]["member_id"], caller["user_id"]
            )
        sheet = assignment.call_sheet(session, plan.id, caller["user_id"])
        assert sheet.splitlines()[0] == "priority,member_id,offer,channel,talking_point"
        assert len(sheet.splitlines()) == len(caller["contacts"]) + 1
        for user_id, profile in original.items():
            catalog.update_staff(session, manager, user_id, profile)


def test_assignment_api_needs_an_approved_plan(client, login, built):
    manager = login("manager")
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "greedy"}
    pid = client.post("/api/plan", json=request, headers=manager).json()["id"]
    assert client.post(f"/api/plan/{pid}/assign", headers=manager).status_code == 409
    assert client.post(f"/api/plan/{pid}/approve", headers=manager).status_code == 200
    assert client.post(f"/api/plan/{pid}/assign", headers=login("staff1")).status_code == 403
    assigned = client.post(f"/api/plan/{pid}/assign", headers=manager)
    assert assigned.status_code == 200, assigned.text
    assert client.get(f"/api/plan/{pid}/assignments", headers=manager).json() == assigned.json()


def test_staff_see_their_contacts_and_log_outcomes_that_feed_the_cbr(client, login, built, engine):
    manager, staff1, staff2 = login("manager"), login("staff1"), login("staff2")
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "greedy"}
    pid = client.post("/api/plan", json=request, headers=manager).json()["id"]
    client.post(f"/api/plan/{pid}/approve", headers=manager)
    client.post(f"/api/plan/{pid}/assign", headers=manager)

    mine = {
        who: client.get("/api/assignments/mine", headers=h).json()
        for who, h in [("1", staff1), ("2", staff2)]
    }
    owner, other = ("1", "2") if mine["1"] else ("2", "1")
    contact = mine[owner][0]
    assert contact["priority"] == 1 and contact["summary"] and contact["offer_name"]
    item = contact["plan_item_id"]
    headers = {"1": staff1, "2": staff2}

    def log(h, outcome, note=None):
        return client.post(
            "/api/outcomes",
            json={"plan_item_id": item, "outcome": outcome, "note": note},
            headers=h,
        )

    assert log(headers[other], "accepted").status_code == 403, "staff log only their own contacts"
    assert log(headers[owner], "maybe").status_code == 422
    assert log(headers[owner], "follow_up", "call back Friday").status_code == 200
    assert log(headers[owner], "accepted").status_code == 200

    with Session(engine) as session:
        rows = session.exec(select(Outcome).where(Outcome.plan_item_id == item)).all()
        assert [r.outcome for r in rows] == ["accepted"], (
            "one outcome per contact, updated in place"
        )
        cases = contacts.logged_cases(session)
        assert len(cases) == 1 and bool(cases["stayed"].iloc[0])
        grown = contacts.app_case_base(session)
    assert len(grown.cases) == len(load_case_base().cases) + 1
    assert (
        client.get("/api/assignments/mine", headers=headers[owner]).json()[0]["outcome"]
        == "accepted"
    )
    history = client.get(
        "/api/outcomes", params={"member_id": contact["member_id"]}, headers=staff1
    ).json()
    assert history[0]["outcomes"][0]["outcome"] == "accepted"


def test_plan_job_runs_in_the_background_and_one_at_a_time(client, login, built, monkeypatch):
    manager = login("manager")
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "ga"}
    started = client.post("/api/plan/jobs", json=request, headers=manager)
    assert started.status_code == 202, started.text
    for _ in range(300):
        state = client.get("/api/plan/jobs/current", headers=manager).json()
        if state["state"] != "running":
            break
        time.sleep(0.05)
    assert state["state"] == "done", state
    assert state["progress"] == 1.0 and state["plan_id"]
    assert (
        client.get(f"/api/plan/{state['plan_id']}", headers=manager).json()["id"]
        == state["plan_id"]
    )
    assert client.get("/api/plan/999999", headers=manager).status_code == 404

    monkeypatch.setattr(jobs, "_status", jobs.JobStatus(state="running", kind="plan"))
    assert client.post("/api/plan/jobs", json=request, headers=manager).status_code == 409
    assert client.post("/api/plan/jobs", json=request, headers=login("staff1")).status_code == 403


def test_compare_runs_every_planner_on_the_same_limits(built, engine):
    with Session(engine) as session:
        req = PlanRequest(as_of=date(2026, 10, 19), budget=100, staff_minutes=150)
        result = jobs.compare(session, req, report=lambda stage, done: None)
    rows = {r["planner"]: r for r in result["planners"]}
    assert set(rows) == {"contact-all", "risk-top-k", "greedy-uplift", "exact", "ga"}
    assert all(r["feasible"] for r in rows.values())
    assert rows["exact"]["linear_value"] >= max(r["linear_value"] for r in rows.values()) - 0.01
    assert result["ga_convergence"]


def test_options_skip_offers_missing_from_the_catalogue():
    from anchorai.catalog import OfferIn
    from anchorai.optimisation.model import build_options
    from anchorai.reasoning.models import Proposal, RuleOutcome

    allowed = [
        Proposal(offer_id="gone", channel="sms"),
        Proposal(offer_id="checkin_message", channel="sms"),
    ]
    outcome = RuleOutcome(
        member_id="M1", facts={}, firings=[], proposals=allowed, blocked={}, allowed=allowed
    )
    offers = [
        OfferIn(
            offer_id="checkin_message", name="Check-in", cost=0, staff_minutes=5, channels=["sms"]
        )
    ]
    scores = pd.DataFrame(
        {"churn_prob": [0.5], "risk_band": ["high"], "monthly_value": [72.0]}, index=["M1"]
    )
    uplift = pd.Series([0.1], index=pd.MultiIndex.from_tuples([("M1", "checkin_message")]))
    options = build_options({"M1": outcome}, offers, scores, uplift)
    assert options["offer_id"].tolist() == ["checkin_message"]
    assert options["rank"].tolist() == [0], (
        "the first available offer becomes the playbook's top offer"
    )
    assert options["cost"].notna().all()


def test_demo_seed_is_an_approved_past_week_and_is_deterministic(built, tmp_path):
    from sqlmodel import SQLModel

    from anchorai.db.seeds import run_seeds
    from anchorai.db.seeds.demo import DEMO_WEEK
    from anchorai.db.session import make_engine

    def fresh(name):
        engine = make_engine(f"sqlite:///{tmp_path / name}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            run_seeds(session, ("base", "demo"))
            run_seeds(session, ("base", "demo"))  # idempotent: the second run adds nothing
            plans = session.exec(select(Plan)).all()
            outcomes = session.exec(select(Outcome).order_by(Outcome.plan_item_id)).all()
            audit = session.exec(select(AuditLog).where(AuditLog.action.startswith("plan"))).all()
            assigned = session.exec(select(func.count()).select_from(Assignment)).one()
            result = (
                plans,
                [(o.member_id, o.outcome) for o in outcomes],
                outcomes,
                audit,
                assigned,
            )
        engine.dispose()
        return result

    plans, logged, outcomes, audit, assigned = fresh("a.db")
    assert len(plans) == 1 and plans[0].week_start == DEMO_WEEK and plans[0].status == "approved"
    assert assigned and logged
    week = {DEMO_WEEK + timedelta(days=d) for d in range(5)}
    assert all(o.logged_at.date() in week for o in outcomes)
    assert all(a.ts.date() in week for a in audit)
    assert fresh("b.db")[1] == logged, "same seed, same outcomes"


def test_reoptimise_keeps_manager_changes_and_fills_the_rest(client, login, built, engine):
    manager = login("manager")
    request = {"as_of": "2026-10-19", "budget": 100, "staff_minutes": 150, "solver": "greedy"}
    plan = client.post("/api/plan", json=request, headers=manager).json()
    pid, items = plan["id"], plan["items"]
    removed, swapped = items[0]["member_id"], items[1]["member_id"]
    client.post(
        f"/api/plan/{pid}/items/{removed}/remove",
        json={"reason": "spoke to them today"},
        headers=manager,
    )
    swap = {
        "member_id": swapped,
        "offer_id": "checkin_message",
        "channel": "email",
        "reason": "prefers email",
    }
    assert client.post(f"/api/plan/{pid}/items", json=swap, headers=manager).status_code == 200

    with Session(engine) as session:
        overrides.reoptimise(
            session, session.exec(select(User).where(User.username == "manager")).one(), pid
        )
    after = client.get(f"/api/plan/{pid}", headers=manager).json()
    members = [i["member_id"] for i in after["items"]]
    assert removed not in members, "a member removed by hand stays out"
    kept = next(i for i in after["items"] if i["member_id"] == swapped)
    assert kept["offer_id"] == "checkin_message" and kept["channel"] == "email", (
        "a hand-made swap stays"
    )
    assert len(members) == len(set(members))
    assert after["total_cost"] <= 100 and after["total_staff_minutes"] <= 150

    assert client.get(f"/api/plan/{pid}/previous", headers=manager).status_code in (200, 404)
    client.post(f"/api/plan/{pid}/approve", headers=manager)
    assert client.post(f"/api/plan/{pid}/reoptimise", headers=manager).status_code == 409
    later = client.post(
        "/api/plan", json={**request, "as_of": "2026-10-26"}, headers=manager
    ).json()
    previous = client.get(f"/api/plan/{later['id']}/previous", headers=manager).json()
    assert previous["id"] == pid, "the approved plan before a draft is last week's"
