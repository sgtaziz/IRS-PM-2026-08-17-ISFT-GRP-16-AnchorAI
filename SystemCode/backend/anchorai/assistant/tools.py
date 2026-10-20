"""Deterministic tools behind each intent. Each returns evidence lines for the grounded prompt."""

import json
import math
from typing import Any

import pandas as pd
from pydantic import BaseModel, ValidationError
from sqlmodel import Session, select

from anchorai import catalog
from anchorai.assistant.slots import Slots
from anchorai.cbr.reasoner import uplift_series
from anchorai.db.models import Plan, PlanItem
from anchorai.discovery import service as member_data
from anchorai.features import LABELS
from anchorai.knowledge import queries, reload
from anchorai.knowledge.entities import effective
from anchorai.knowledge.graph import GraphUnavailable, read
from anchorai.knowledge.signals import graph_signals
from anchorai.optimisation.contacts import app_case_base
from anchorai.optimisation.exact import solve_linear
from anchorai.optimisation.model import Limits, load_instance
from anchorai.reasoning import service as reasoning
from anchorai.reasoning.engine import run
from anchorai.reasoning.models import Rule
from anchorai.scenario.offers import OFFER_CATALOG
from anchorai.schemas import Explanation

STATIC_OFFER_NAMES = {o["offer_id"]: o["name"] for o in OFFER_CATALOG}
CHANNELS = {"sms": "SMS", "email": "email", "call": "phone call", "in_person": "in person"}
TOP_AFFECTED = 5
SIMILAR_CASES_SHOWN = 2
WHAT_IF_SECONDS = 5


class Evidence(BaseModel):
    id: str
    text: str
    # What the line is about, so the UI can link it: member, rule, offer, event or plan.
    kind: str
    ref: str | None = None


class ToolResult(BaseModel):
    tool: str
    evidence: list[Evidence] = []
    # A deterministic reply when the tool can't answer (unknown member, service not ready).
    note: str | None = None


class _Lines:
    def __init__(self) -> None:
        self.items: list[Evidence] = []

    def add(self, text: str, kind: str, ref: str | None = None) -> None:
        self.items.append(Evidence(id=f"E{len(self.items) + 1}", text=text, kind=kind, ref=ref))


def probability(p: float | None) -> str:
    """Same rule as the web app (src/format.ts): a model probability never reads as 0% or 100%."""
    if p is None or math.isnan(p):
        return "unknown"
    shown = round(p * 100)
    return ">99%" if shown >= 100 else "<1%" if shown <= 0 else f"{shown}%"


def name_lookup(session: Session | None = None) -> tuple[dict[str, str], dict[str, str]]:
    eff = effective(session)
    instructors = dict(zip(eff.instructors["name"], eff.instructors["instructor_id"]))
    classes = dict(zip(eff.classes["name"], eff.classes["class_id"]))
    return instructors, classes


def _profile(member_id: str, f: dict[str, Any]) -> str:
    contract = "month-to-month" if f["contract_period"] == 1 else f"{f['contract_period']}-month"
    group = "attends group classes" if f.get("group_visits") == 1 else "no group classes"
    return (
        f"{member_id} profile: {contract} contract, {f['lifetime']} months as a member, "
        f"{f['avg_class_frequency_current_month']:.1f} visits/week this month vs "
        f"{f['avg_class_frequency_total']:.1f} usual, {group}"
    )


def _missing(session: Session, tool: str, member_ids: list[str]) -> ToolResult | None:
    unknown = [m for m in member_ids if m not in reasoning.all_facts(session)]
    if unknown:
        return ToolResult(tool=tool, note=f"I couldn't find member {', '.join(unknown)}.")
    return None


def _score_lines(lines: _Lines, session: Session, member_id: str) -> None:
    row = member_data.get_data().table.loc[member_id]
    facts = reasoning.all_facts(session)[member_id]
    lines.add(
        f"{member_id}: churn probability {probability(row['churn_prob'])} "
        f"({row['risk_band']} risk), segment '{row['segment']}'",
        "member",
        member_id,
    )
    lines.add(_profile(member_id, facts), "member", member_id)
    for name, weight in json.loads(row["top_drivers"])[:3]:
        effect = "raises" if weight > 0 else "lowers"
        lines.add(
            f"{member_id} risk driver: {LABELS.get(name, name)} ({effect} risk)",
            "member",
            member_id,
        )


def _code(rule_id: str) -> str:
    return rule_id.split("_")[0]


def _offer_names(session: Session) -> dict[str, str]:
    return STATIC_OFFER_NAMES | {o.offer_id: o.name for o in catalog.list_offers(session)}


def _offer(names: dict[str, str], offer_id: str, channel: str | None = None) -> str:
    name = names.get(offer_id, offer_id)
    return f"{name} by {CHANNELS.get(channel, channel)}" if channel else name


def _effect(rule: Rule, names: dict[str, str]) -> str:
    """What a rule does in words, for staff and the LLM ("concludes new member")."""
    then = rule.then
    if then.assert_ is not None:
        return "concludes " + ", ".join(k.replace("_", " ") for k in then.assert_)
    if then.propose is not None:
        return "proposes " + _offer(names, then.propose.offer_id, then.propose.channel)
    targets = then.block
    return "blocks " + (
        "all offers" if targets == "all" else ", ".join(_offer(names, t) for t in targets)
    )


def _rule_lines(lines: _Lines, session: Session, member_id: str, detail: bool) -> None:
    _, rules = reasoning.active_rules(session)
    by_id = {r.id: r for r in rules}
    names = _offer_names(session)
    outcome = reasoning.drop_inactive(
        session, run(rules, reasoning.all_facts(session)[member_id], member_id)
    )
    if detail:
        for f in outcome.firings:
            lines.add(
                f"{member_id} rule {_code(f.rule_id)}: {f.description}; "
                f"{_effect(by_id[f.rule_id], names)}",
                "rule",
                f.rule_id,
            )
    for p in outcome.allowed:
        lines.add(
            f"{member_id} allowed offer: {_offer(names, p.offer_id, p.channel)} (rule {_code(p.rule_id)})",
            "offer",
            p.offer_id,
        )
    for target, rule_id in outcome.blocked.items():
        what = "all offers" if target == "all" else _offer(names, target)
        lines.add(f"{member_id} blocked: {what} (guardrail {_code(rule_id)})", "rule", rule_id)
    if not outcome.allowed and "all" not in outcome.blocked:
        lines.add(f"{member_id}: no playbook rule proposes an offer", "member", member_id)
    for signal in graph_signals(outcome.facts):
        lines.add(f"{member_id} graph signal: {signal}", "member", member_id)


def _plan_lines(lines: _Lines, session: Session, member_id: str) -> None:
    """Where the member stands in the latest plan, with the stored explanation when there is one."""
    plan = session.exec(select(Plan).order_by(Plan.week_start.desc(), Plan.id.desc())).first()
    if plan is None:
        return
    names = _offer_names(session)
    week = f"{plan.week_start:%Y-%m-%d}"
    items = session.exec(
        select(PlanItem)
        .where(PlanItem.plan_id == plan.id, PlanItem.member_id == member_id)
        .order_by(PlanItem.id)
    ).all()
    kept = next((i for i in items if not i.removed), None)
    if kept is None:
        lines.add(f"{member_id} is not in the plan for the week of {week}", "plan", str(plan.id))
        for item in items:
            why = f": {item.override_reason}" if item.override_reason else ""
            lines.add(
                f"{member_id} was removed from the plan for the week of {week}{why}",
                "plan",
                str(plan.id),
            )
        return
    lines.add(
        f"{member_id} is in the plan for the week of {week}: "
        f"{_offer(names, kept.offer_id, kept.channel)}, expected value {kept.expected_value:.2f}",
        "plan",
        str(plan.id),
    )
    try:
        explanation = Explanation.model_validate(kept.explanation)
    except ValidationError:
        return
    lines.add(f"{member_id} plan explanation: {explanation.summary}", "plan", str(plan.id))
    for case in explanation.similar_cases[:SIMILAR_CASES_SHOWN]:
        if outcome := case.get("outcome"):
            lines.add(f"{member_id} similar past case: {outcome}", "plan", str(plan.id))
    for signal in explanation.graph_signals:
        lines.add(f"{member_id} plan graph signal: {signal}", "plan", str(plan.id))


def member_risk(session: Session, slots: Slots) -> ToolResult:
    member_id = slots.member_ids[0]
    if missing := _missing(session, "member_risk", [member_id]):
        return missing
    lines = _Lines()
    _score_lines(lines, session, member_id)
    for signal in graph_signals(reasoning.all_facts(session)[member_id]):
        lines.add(f"{member_id} graph signal: {signal}", "member", member_id)
    _plan_lines(lines, session, member_id)
    return ToolResult(tool="member_risk", evidence=lines.items)


def member_actions(session: Session, slots: Slots) -> ToolResult:
    member_id = slots.member_ids[0]
    if missing := _missing(session, "member_actions", [member_id]):
        return missing
    lines = _Lines()
    lines.add(_profile(member_id, reasoning.all_facts(session)[member_id]), "member", member_id)
    _rule_lines(lines, session, member_id, detail=True)
    _plan_lines(lines, session, member_id)
    return ToolResult(tool="member_actions", evidence=lines.items)


def compare_members(session: Session, slots: Slots) -> ToolResult:
    pair = slots.member_ids[:2]
    if missing := _missing(session, "compare_members", pair):
        return missing
    lines = _Lines()
    if len(slots.member_ids) > 2:
        lines.add(f"Only the first two members named are compared: {' and '.join(pair)}", "member")
    for member_id in pair:
        _score_lines(lines, session, member_id)
        _rule_lines(lines, session, member_id, detail=False)
    for member_id in pair:
        _plan_lines(lines, session, member_id)
    return ToolResult(tool="compare_members", evidence=lines.items)


def _affected(query: str, label: str, kind: str, ref: str, lines: _Lines, **params: str) -> None:
    rows = sorted(read(query, **params), key=lambda r: r["churn_prob"] or 0, reverse=True)
    high = sum(r["risk_band"] == "high" for r in rows)
    lines.add(f"{len(rows)} members attend {label}; {high} of them are high risk", kind, ref)
    for r in rows[:TOP_AFFECTED]:
        lines.add(
            f"{r['member_id']} attends {label}: churn probability {probability(r['churn_prob'])}",
            "member",
            r["member_id"],
        )


def graph_impact(session: Session, slots: Slots) -> ToolResult:
    eff = effective(session)
    instructors = eff.instructors.set_index("instructor_id")["name"]
    classes = eff.classes.set_index("class_id")
    events = eff.events
    lines = _Lines()
    targets = [("instructor", i) for i in slots.instructor_ids] + [
        ("class", c) for c in slots.class_ids
    ]
    if not targets:
        targets = [
            ("instructor" if e.event_type == "instructor_left" else "class", e.entity_id)
            for e in events.itertuples()
        ]
    if reload.status(session).stale:
        lines.add(
            "The knowledge graph is out of date: recent roster edits are not in it yet",
            "event",
            "knowledge_graph",
        )
    try:
        for kind, entity_id in targets:
            event = events[events["entity_id"] == entity_id]
            status = ""
            if len(event):
                verb = "left" if kind == "instructor" else "was cancelled"
                status = f" ({verb} in the week of {event.iloc[0]['week_start']:%Y-%m-%d})"
            if kind == "instructor":
                label = f"classes taught by {instructors[entity_id]}{status}"
                _affected(
                    queries.MEMBERS_BY_INSTRUCTOR,
                    label,
                    "event",
                    entity_id,
                    lines,
                    instructor_id=entity_id,
                )
            else:
                label = f"the {classes.loc[entity_id, 'name']} class{status}"
                _affected(
                    queries.MEMBERS_BY_CLASS, label, "event", entity_id, lines, class_id=entity_id
                )
    except GraphUnavailable:
        return ToolResult(tool="graph_impact", note="The knowledge graph is unavailable right now.")
    return ToolResult(tool="graph_impact", evidence=lines.items)


DEFAULT_LIMIT, MAX_LIMIT = 10, 25
NEW_MEMBER_MONTHS = 2


def list_members(session: Session, slots: Slots) -> ToolResult:
    table = member_data.get_data().table
    limit = min(max(slots.limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    filters = []
    if slots.risk_band:
        table = table[table["risk_band"] == slots.risk_band]
        filters.append(f"{slots.risk_band} risk")
    if slots.club_id:
        table = table[table["club_id"] == slots.club_id]
        filters.append(f"club {slots.club_id}")
    if slots.new_members:
        table = table[table["lifetime"] <= NEW_MEMBER_MONTHS]
        filters.append(f"members of {NEW_MEMBER_MONTHS} months or less")
    if slots.segment:
        names = table["segment"].str.lower().str.replace("-", " ")
        table = table[names.str.contains(slots.segment, regex=False)]
        filters.append(f"segment matching '{slots.segment}'")
    if table.empty:
        return ToolResult(tool="list_members", note="No members match those filters.")
    top = table.sort_values("churn_prob", ascending=False, kind="stable").head(limit)
    lines = _Lines()
    scope = f" ({', '.join(filters)})" if filters else ""
    lines.add(
        f"Showing the {len(top)} members with the highest churn probability out of "
        f"{len(table)} matching{scope}",
        "member",
    )
    for member_id, row in top.iterrows():
        lines.add(
            f"{member_id}: churn probability {probability(row['churn_prob'])} "
            f"({row['risk_band']} risk), segment '{row['segment']}', club {row['club_id']}, "
            f"{row['lifetime']} months as a member",
            "member",
            member_id,
        )
    return ToolResult(tool="list_members", evidence=lines.items)


def plan_summary(session: Session, slots: Slots) -> ToolResult:
    plan = session.exec(select(Plan).order_by(Plan.week_start.desc(), Plan.id.desc())).first()
    if plan is None:
        return ToolResult(tool="plan_summary", note="No weekly plan has been generated yet.")
    items = session.exec(
        select(PlanItem).where(PlanItem.plan_id == plan.id, ~PlanItem.removed)
    ).all()
    lines = _Lines()
    lines.add(
        f"Plan for the week of {plan.week_start:%Y-%m-%d} is {plan.status}: {len(items)} contacts, "
        f"total cost {plan.total_cost:.0f}, {plan.total_staff_minutes} staff minutes, "
        f"{plan.expected_members_retained:.1f} members expected to be retained",
        "plan",
        str(plan.id),
    )
    counts: dict[str, int] = {}
    for item in items:
        counts[item.offer_id] = counts.get(item.offer_id, 0) + 1
    names = _offer_names(session)
    for offer_id, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.add(f"{n} plan contacts get {names.get(offer_id, offer_id)}", "offer", offer_id)
    return ToolResult(tool="plan_summary", evidence=lines.items)


def _binding(options: pd.DataFrame, plan: pd.DataFrame, limits: Limits) -> str:
    """The limits that keep further worthwhile contacts out of the plan, by how many each blocks."""
    left = options[(options["value"] > 0) & ~options["member_id"].isin(plan["member_id"])]
    blocked = {
        "money": int((left["cost"] > limits.budget - plan["cost"].sum()).sum()),
        "staff time": int(
            (left["staff_minutes"] > limits.staff_minutes - plan["staff_minutes"].sum()).sum()
        ),
    }
    reached = [
        f"{k} (blocks {n} contact options)"
        for k, n in sorted(blocked.items(), key=lambda kv: -kv[1])
        if n
    ]
    return "limits reached: " + (
        ", ".join(reached) or "none, every worthwhile contact is in the plan"
    )


def what_if_budget(session: Session, slots: Slots) -> ToolResult:
    if slots.amount is None and slots.staff_hours is None:
        return ToolResult(
            tool="what_if_budget",
            note="Say a budget (for example $2,000) or staff hours (for example 40 staff hours).",
        )
    try:
        instance = load_instance(session, uplift=uplift_series(app_case_base(session)))
    except OSError:
        return ToolResult(
            tool="what_if_budget", note="The member data isn't built yet, so I can't plan."
        )
    minutes = None if slots.staff_hours is None else round(slots.staff_hours * 60)
    runs = [
        ("Current limits", instance.limits()),
        ("Asked limits", instance.limits(slots.amount, minutes)),
    ]
    lines = _Lines()
    results = []
    for label, limits in runs:
        plan, status, _ = solve_linear(instance.options, limits, WHAT_IF_SECONDS)
        if status not in ("OPTIMAL", "FEASIBLE"):
            return ToolResult(tool="what_if_budget", note="The planner found no feasible plan.")
        results.append((plan, limits))
        lines.add(
            f"{label}: budget ${limits.budget:,.0f}, {limits.staff_minutes / 60:g} staff hours. "
            f"Best plan: {len(plan)} members contacted, "
            f"{plan['est_uplift'].sum():.1f} extra members expected to stay, "
            f"cost ${plan['cost'].sum():,.0f}, {plan['staff_minutes'].sum() / 60:.1f} staff hours "
            f"({int(plan['staff_minutes'].sum())} minutes) used; "
            f"{_binding(instance.options, plan, limits)}",
            "plan",
        )
    (now, _), (asked, _) = results
    lines.add(
        f"Change from the current limits: {len(asked) - len(now):+d} contacts, "
        f"{asked['est_uplift'].sum() - now['est_uplift'].sum():+.1f} extra members expected to "
        f"stay, {asked['cost'].sum() - now['cost'].sum():+,.0f} dollars of cost",
        "plan",
    )
    return ToolResult(tool="what_if_budget", evidence=lines.items)


TOOLS = {
    "member_risk": member_risk,
    "member_actions": member_actions,
    "compare_members": compare_members,
    "graph_impact": graph_impact,
    "list_members": list_members,
    "plan_summary": plan_summary,
    "what_if_budget": what_if_budget,
}
