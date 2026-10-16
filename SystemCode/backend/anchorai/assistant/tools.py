"""Deterministic tools behind each intent. Each returns evidence lines for the grounded prompt."""

import json
import math
from typing import Any

from pydantic import BaseModel
from sqlmodel import Session, select

from anchorai.assistant.slots import Slots
from anchorai.db.models import Plan, PlanItem
from anchorai.discovery import service as member_data
from anchorai.features import LABELS
from anchorai.knowledge import queries
from anchorai.knowledge.graph import GraphUnavailable, read
from anchorai.knowledge.signals import graph_signals
from anchorai.reasoning import service as reasoning
from anchorai.reasoning.engine import run
from anchorai.reasoning.models import Rule
from anchorai.scenario.offers import OFFER_CATALOG

OFFER_NAMES = {o["offer_id"]: o["name"] for o in OFFER_CATALOG}
CHANNELS = {"sms": "SMS", "email": "email", "call": "phone call", "in_person": "in person"}
TOP_AFFECTED = 5


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


def name_lookup() -> tuple[dict[str, str], dict[str, str]]:
    tables = member_data.get_data().tables
    instructors = dict(zip(tables["instructors"]["name"], tables["instructors"]["instructor_id"]))
    classes = dict(zip(tables["classes"]["name"], tables["classes"]["class_id"]))
    return instructors, classes


def _profile(member_id: str, f: dict[str, Any]) -> str:
    contract = "month-to-month" if f["contract_period"] == 1 else f"{f['contract_period']}-month"
    group = "attends group classes" if f.get("group_visits") == 1 else "no group classes"
    return (
        f"{member_id} profile: {contract} contract, {f['lifetime']} months as a member, "
        f"{f['avg_class_frequency_current_month']:.1f} visits/week this month vs "
        f"{f['avg_class_frequency_total']:.1f} usual, {group}"
    )


def _missing(tool: str, member_ids: list[str]) -> ToolResult | None:
    unknown = [m for m in member_ids if m not in reasoning.all_facts()]
    if unknown:
        return ToolResult(tool=tool, note=f"I couldn't find member {', '.join(unknown)}.")
    return None


def _score_lines(lines: _Lines, member_id: str) -> None:
    row = member_data.get_data().table.loc[member_id]
    facts = reasoning.all_facts()[member_id]
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


def _offer(offer_id: str, channel: str | None = None) -> str:
    name = OFFER_NAMES.get(offer_id, offer_id)
    return f"{name} by {CHANNELS.get(channel, channel)}" if channel else name


def _effect(rule: Rule) -> str:
    """What a rule does in words, for staff and the LLM ("concludes new member")."""
    then = rule.then
    if then.assert_ is not None:
        return "concludes " + ", ".join(k.replace("_", " ") for k in then.assert_)
    if then.propose is not None:
        return "proposes " + _offer(then.propose.offer_id, then.propose.channel)
    targets = then.block
    return "blocks " + ("all offers" if targets == "all" else ", ".join(map(_offer, targets)))


def _rule_lines(lines: _Lines, session: Session, member_id: str, detail: bool) -> None:
    _, rules = reasoning.active_rules(session)
    by_id = {r.id: r for r in rules}
    outcome = run(rules, reasoning.all_facts()[member_id], member_id)
    if detail:
        for f in outcome.firings:
            lines.add(
                f"{member_id} rule {_code(f.rule_id)}: {f.description}; "
                f"{_effect(by_id[f.rule_id])}",
                "rule",
                f.rule_id,
            )
    for p in outcome.allowed:
        lines.add(
            f"{member_id} allowed offer: {_offer(p.offer_id, p.channel)} (rule {_code(p.rule_id)})",
            "offer",
            p.offer_id,
        )
    for target, rule_id in outcome.blocked.items():
        what = "all offers" if target == "all" else _offer(target)
        lines.add(f"{member_id} blocked: {what} (guardrail {_code(rule_id)})", "rule", rule_id)
    if not outcome.allowed and "all" not in outcome.blocked:
        lines.add(f"{member_id}: no playbook rule proposes an offer", "member", member_id)
    for signal in graph_signals(outcome.facts):
        lines.add(f"{member_id} graph signal: {signal}", "member", member_id)


def member_risk(session: Session, slots: Slots) -> ToolResult:
    member_id = slots.member_ids[0]
    if missing := _missing("member_risk", [member_id]):
        return missing
    lines = _Lines()
    _score_lines(lines, member_id)
    for signal in graph_signals(reasoning.all_facts()[member_id]):
        lines.add(f"{member_id} graph signal: {signal}", "member", member_id)
    return ToolResult(tool="member_risk", evidence=lines.items)


def member_actions(session: Session, slots: Slots) -> ToolResult:
    member_id = slots.member_ids[0]
    if missing := _missing("member_actions", [member_id]):
        return missing
    lines = _Lines()
    lines.add(_profile(member_id, reasoning.all_facts()[member_id]), "member", member_id)
    _rule_lines(lines, session, member_id, detail=True)
    return ToolResult(tool="member_actions", evidence=lines.items)


def compare_members(session: Session, slots: Slots) -> ToolResult:
    pair = slots.member_ids[:2]
    if missing := _missing("compare_members", pair):
        return missing
    lines = _Lines()
    if len(slots.member_ids) > 2:
        lines.add(f"Only the first two members named are compared: {' and '.join(pair)}", "member")
    for member_id in pair:
        _score_lines(lines, member_id)
        _rule_lines(lines, session, member_id, detail=False)
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
    tables = member_data.get_data().tables
    instructors = tables["instructors"].set_index("instructor_id")["name"]
    classes = tables["classes"].set_index("class_id")
    events = tables["events"]
    lines = _Lines()
    targets = [("instructor", i) for i in slots.instructor_ids] + [
        ("class", c) for c in slots.class_ids
    ]
    if not targets:
        targets = [
            ("instructor" if e.event_type == "instructor_left" else "class", e.entity_id)
            for e in events.itertuples()
        ]
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
    for offer_id, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.add(f"{n} plan contacts get {OFFER_NAMES.get(offer_id, offer_id)}", "offer", offer_id)
    return ToolResult(tool="plan_summary", evidence=lines.items)


def what_if_budget(session: Session, slots: Slots) -> ToolResult:
    return ToolResult(
        tool="what_if_budget",
        note="What-if budgets need the plan optimiser, which isn't connected yet.",
    )


TOOLS = {
    "member_risk": member_risk,
    "member_actions": member_actions,
    "compare_members": compare_members,
    "graph_impact": graph_impact,
    "plan_summary": plan_summary,
    "what_if_budget": what_if_budget,
}
