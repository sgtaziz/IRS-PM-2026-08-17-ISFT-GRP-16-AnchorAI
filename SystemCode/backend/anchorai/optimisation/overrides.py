"""Manager overrides on a draft plan (remove, add, swap) and approval, which locks the plan."""

import pandas as pd
from sqlmodel import Session, col, select

from anchorai import catalog
from anchorai.cbr.reasoner import uplift_series
from anchorai.db import models
from anchorai.db.audit import record_audit
from anchorai.db.models import utcnow
from anchorai.discovery.scores import load_scores
from anchorai.optimisation import service as plan_service
from anchorai.optimisation.contacts import app_case_base
from anchorai.optimisation.explain import explain_plan
from anchorai.optimisation.ga import load_cohorts
from anchorai.optimisation.model import (
    HORIZON_MONTHS,
    TRAINER,
    Limits,
    limits_for,
    load_instance,
    violations,
)
from anchorai.optimisation.service import Progress
from anchorai.reasoning import check, service
from anchorai.reasoning.engine import run
from anchorai.schemas import Channel

NEEDS_PHONE = {Channel.SMS, Channel.CALL}


class PlanNotFound(LookupError):
    pass


class PlanLocked(RuntimeError):
    pass


class OverrideRejected(ValueError):
    def __init__(self, message: str, problems: list[str]):
        super().__init__(message)
        self.problems = problems


def _draft(session: Session, plan_id: int) -> models.Plan:
    plan = session.get(models.Plan, plan_id)
    if plan is None:
        raise PlanNotFound(plan_id)
    if plan.status != "draft":
        raise PlanLocked(f"Plan {plan_id} is {plan.status} and can no longer change")
    return plan


def _kept(session: Session, plan_id: int) -> list[models.PlanItem]:
    return list(
        session.exec(
            select(models.PlanItem).where(
                models.PlanItem.plan_id == plan_id, col(models.PlanItem.removed).is_(False)
            )
        ).all()
    )


def _items_frame(session: Session, items: list[models.PlanItem]) -> pd.DataFrame:
    offers = {o.offer_id: o for o in catalog.list_offers(session)}
    return pd.DataFrame(
        [
            {
                "member_id": i.member_id,
                "offer_id": i.offer_id,
                "cost": offers[i.offer_id].cost,
                "staff_minutes": offers[i.offer_id].staff_minutes,
                "required_skill": offers[i.offer_id].required_skill,
            }
            for i in items
        ],
        columns=["member_id", "offer_id", "cost", "staff_minutes", "required_skill"],
    )


def _refresh_totals(session: Session, plan: models.Plan, uplift: pd.Series) -> None:
    items = _kept(session, plan.id)
    frame = _items_frame(session, items)
    plan.total_cost = float(frame["cost"].sum())
    plan.total_staff_minutes = int(frame["staff_minutes"].sum())
    keys = pd.MultiIndex.from_frame(frame[["member_id", "offer_id"]])
    plan.expected_members_retained = float(uplift.reindex(keys).fillna(0).sum())
    session.add(plan)


def remove_item(
    session: Session, user: models.User, plan_id: int, member_id: str, reason: str
) -> None:
    plan = _draft(session, plan_id)
    item = next((i for i in _kept(session, plan_id) if i.member_id == member_id), None)
    if item is None:
        raise OverrideRejected(f"{member_id} is not in plan {plan_id}", [])
    item.removed, item.override_reason = True, reason
    session.add(item)
    _refresh_totals(session, plan, uplift_series(app_case_base(session)))
    after = {"member_id": member_id, "offer_id": item.offer_id, "reason": reason}
    record_audit(session, user, "plan_item.remove", "plan", str(plan_id), None, after)
    session.commit()


def add_item(
    session: Session,
    user: models.User,
    plan_id: int,
    member_id: str,
    offer_id: str,
    channel: Channel,
    reason: str,
) -> models.PlanItem:
    """Add an offer for a member, or swap it in when the member is already on the plan."""
    plan = _draft(session, plan_id)
    result = check.check_items(
        session, [check.ProposedItem(member_id=member_id, offer_id=offer_id, channel=channel)]
    )[0]
    facts = service.all_facts(session)[member_id]
    problems = [f"{v.rule_id}: {v.description}" for v in result.violations]
    if not result.offer_active:
        problems.append(f"{offer_id} is not an active offer")
    if not result.channel_offered:
        problems.append(f"{offer_id} cannot be sent by {channel.value}")
    # HANDOFFS #30: the rule check does not yet stop SMS or calls to members with no phone on file.
    if channel in NEEDS_PHONE and not facts.get("phone"):
        problems.append(f"{member_id} has no phone on file, so {channel.value} cannot reach them")
    if problems:
        raise OverrideRejected("The change breaks the rules", problems)

    kept = _kept(session, plan_id)
    replaced = next((i for i in kept if i.member_id == member_id), None)
    trial = [i for i in kept if i is not replaced]
    trial.append(models.PlanItem(plan_id=plan_id, member_id=member_id, offer_id=offer_id))
    frame = _items_frame(session, trial)
    offers = catalog.list_offers(session)
    req = plan.request
    limits = limits_for(req["budget"], req["staff_minutes"], offers, catalog.list_staff(session))
    broken = violations(frame, frame, limits)
    if broken:
        raise OverrideRejected(
            "The change does not fit this week's limits",
            [f"{name} over by {amount:g}" for name, amount in broken.items()],
        )

    case_base = app_case_base(session)
    uplift = uplift_series(case_base)
    scores = load_scores().set_index("member_id")
    _, rules = service.active_rules(session)
    outcome = service.drop_inactive(session, run(rules, facts, member_id))
    proposer = next((p.rule_id for p in outcome.allowed if p.offer_id == offer_id), "")
    est = float(uplift.get((member_id, offer_id), 0.0))
    cost = next(o.cost for o in offers if o.offer_id == offer_id)
    row = pd.DataFrame(
        [
            {
                "member_id": member_id,
                "offer_id": offer_id,
                "rule_id": proposer,
                "churn_prob": scores.at[member_id, "churn_prob"],
                "risk_band": scores.at[member_id, "risk_band"],
                "est_uplift": est,
            }
        ]
    )
    # Count every item ever on the plan, removed ones too, so an id is never reused.
    total = len(
        session.exec(select(models.PlanItem.id).where(models.PlanItem.plan_id == plan_id)).all()
    )
    explanation_id = f"p{plan_id}-{member_id}-{total + 1}"
    names = {o.offer_id: o.name for o in offers}
    explanation = explain_plan(
        row, [explanation_id], {member_id: outcome}, scores, case_base, names
    )[0]
    explanation.summary = f"Added by the manager: {reason}. {explanation.summary}"

    if replaced is not None:
        replaced.removed, replaced.override_reason = True, f"Swapped for {offer_id}: {reason}"
        session.add(replaced)
    item = models.PlanItem(
        plan_id=plan_id,
        member_id=member_id,
        offer_id=offer_id,
        channel=channel.value,
        expected_value=est * float(scores.at[member_id, "monthly_value"]) * HORIZON_MONTHS - cost,
        explanation_id=explanation_id,
        explanation=explanation.model_dump(mode="json"),
        override_reason=reason,
    )
    session.add(item)
    session.flush()
    _refresh_totals(session, plan, uplift)
    after = {
        "member_id": member_id,
        "offer_id": offer_id,
        "channel": channel.value,
        "reason": reason,
    }
    if replaced is not None:
        after["replaced"] = replaced.offer_id
    action = "plan_item.swap" if replaced is not None else "plan_item.add"
    record_audit(session, user, action, "plan", str(plan_id), None, after)
    session.commit()
    return item


def approve(session: Session, user: models.User, plan_id: int) -> models.Plan:
    plan = _draft(session, plan_id)
    # One approved plan per week, so staff lists, the dashboard and "last week" have one answer.
    other = session.exec(
        select(models.Plan).where(
            models.Plan.week_start == plan.week_start,
            models.Plan.status == "approved",
            col(models.Plan.id) != plan_id,
        )
    ).first()
    if other is not None:
        raise PlanLocked(f"Plan #{other.id} is already approved for the week of {plan.week_start}")
    plan.status, plan.approved_by_id, plan.approved_at = "approved", user.id, utcnow()
    session.add(plan)
    after = {"status": "approved", "contacts": len(_kept(session, plan_id))}
    record_audit(session, user, "plan.approve", "plan", str(plan_id), {"status": "draft"}, after)
    session.commit()
    session.refresh(plan)
    return plan


def reoptimise(
    session: Session, user: models.User, plan_id: int, progress: Progress | None = None
) -> None:
    """Keep the manager's own decisions and re-plan the rest of the week's limits (W15).

    Items added or swapped by hand stay; members removed by hand stay out; every other draft item is
    replaced by what the planner now chooses with the budget, staff time and stock that are left.
    """
    report = progress or (lambda stage, done: None)
    plan = _draft(session, plan_id)
    items = list(
        session.exec(select(models.PlanItem).where(models.PlanItem.plan_id == plan_id)).all()
    )
    fixed = [i for i in items if not i.removed and i.override_reason]
    # Members the manager added, swapped or removed by hand.
    excluded = {i.member_id for i in items if i.override_reason}
    report("loading", 0.0)
    case_base = app_case_base(session)
    uplift = uplift_series(case_base)
    instance = load_instance(session, uplift=uplift)
    used = _items_frame(session, fixed)
    full = instance.limits(plan.request["budget"], plan.request["staff_minutes"])
    trainer_used = used.loc[used["required_skill"] == TRAINER, "staff_minutes"].sum()
    stock_used = used["offer_id"].value_counts()
    left = Limits(
        full.budget - float(used["cost"].sum()),
        full.staff_minutes - int(used["staff_minutes"].sum()),
        full.trainer_minutes - int(trainer_used),
        {o: s - int(stock_used.get(o, 0)) for o, s in full.stock.items()},
    )
    options = instance.options[~instance.options["member_id"].isin(excluded)]
    solver = plan.request.get("solver", "ga")
    extra = {}
    if solver == "ga":
        extra["on_generation"] = lambda gen, total: report("optimising", 0.05 + 0.85 * gen / total)
        extra["cohorts"] = load_cohorts(session)
    report("optimising", 0.05)
    chosen = plan_service.SOLVERS[solver](options, left, None, **extra)
    broken = violations(chosen, options, left)
    if broken:
        raise RuntimeError(f"Re-optimising returned an infeasible plan: {broken}")

    report("explaining", 0.9)
    replaced = [i for i in items if not i.removed and not i.override_reason]
    for item in replaced:  # a draft item is not a contact yet, so nothing is lost by dropping it
        session.delete(item)
    session.flush()
    start = len(items) + 1
    ids = [f"p{plan_id}-{m}-{start + k}" for k, m in enumerate(chosen["member_id"])]
    names = {o.offer_id: o.name for o in catalog.list_offers(session)}
    scores = load_scores().set_index("member_id")
    explanations = explain_plan(chosen, ids, instance.outcomes, scores, case_base, names)
    session.add_all(
        models.PlanItem(
            plan_id=plan_id,
            member_id=r.member_id,
            offer_id=r.offer_id,
            channel=r.channel,
            expected_value=float(r.value),
            explanation_id=e.explanation_id,
            explanation=e.model_dump(mode="json"),
        )
        for r, e in zip(chosen.itertuples(), explanations, strict=True)
    )
    session.flush()
    _refresh_totals(session, plan, uplift)
    after = {
        "kept": len(fixed),
        "replaced": len(replaced),
        "planned": len(chosen),
        "solver": solver,
    }
    report("saving", 0.97)
    record_audit(session, user, "plan.reoptimise", "plan", str(plan_id), None, after)
    session.commit()
