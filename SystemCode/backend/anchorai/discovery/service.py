"""Queries behind /api/members: cached Stream A artefacts plus outcome counts from the app DB."""

import io
import threading
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from anchorai.db.models import Outcome, Plan, PlanItem
from anchorai.discovery.scores import load_features, load_scores, to_member_score
from anchorai.discovery.views import (
    AttendanceRow,
    Dashboard,
    InterventionRow,
    Kpis,
    MemberDetail,
    MemberHit,
    MemberPage,
    MemberRow,
    OutcomeWeek,
    RiskBin,
    SegmentCard,
    SegmentMix,
)
from anchorai.features import LABELS
from anchorai.scenario.build import AS_OF
from anchorai.scenario.tables import generated_dir, read_tables

AT_RISK_BANDS = ("high",)
SORTABLE = {"churn_prob", "monthly_value", "lifetime", "member_id", "age", "trend_ratio"}
PROFILE_COLUMNS = [
    "age",
    "lifetime",
    "contract_period",
    "month_to_end_contract",
    "avg_class_frequency_total",
    "avg_class_frequency_current_month",
    "trend_ratio",
    "avg_additional_charges_total",
    "group_visits",
    "near_location",
    "partner",
    "promo_friends",
]
REACHED = {"reached", "accepted", "declined", "follow_up"}
RETAINED = {"accepted"}


class DataNotBuilt(RuntimeError):
    pass


@dataclass
class MemberData:
    table: pd.DataFrame
    features: pd.DataFrame
    segments: pd.DataFrame
    tables: dict[str, pd.DataFrame]
    stamp: float


_lock = threading.Lock()
_cache: MemberData | None = None


def _stamp(directory: Path) -> float:
    card = directory / "model_card.json"
    if not card.exists():
        raise DataNotBuilt("Data tables are not built yet. Run `uv run anchorai data build`.")
    return card.stat().st_mtime


def get_data() -> MemberData:
    """Load artefacts once and reload when a rebuild writes a new model card."""
    global _cache
    directory = generated_dir()
    stamp = _stamp(directory)
    with _lock:
        if _cache is None or _cache.stamp != stamp:
            tables = read_tables(directory)
            features = load_features(directory)
            scores = load_scores(directory).set_index("member_id")
            members = tables["members"].set_index("member_id")
            table = scores.join(
                members[["lifetime", "contract_period", "age", "avg_class_frequency_total"]]
            ).join(features[["trend_ratio"]])
            segments = pd.read_parquet(directory / "segments.parquet")
            _cache = MemberData(table, features, segments, tables, stamp)
        return _cache


def _filter(
    data: MemberData,
    segment: str | None = None,
    risk: str | None = None,
    club: str | None = None,
    min_tenure: int | None = None,
    max_tenure: int | None = None,
    q: str | None = None,
) -> pd.DataFrame:
    t = data.table
    mask = pd.Series(True, index=t.index)
    if segment:
        mask &= t["segment"] == segment
    if risk:
        mask &= t["risk_band"] == risk
    if club:
        mask &= t["club_id"] == club
    if min_tenure is not None:
        mask &= t["lifetime"] >= min_tenure
    if max_tenure is not None:
        mask &= t["lifetime"] <= max_tenure
    if q:
        mask &= t.index.str.contains(q.strip(), case=False, regex=False)
    return t[mask]


def _rows(frame: pd.DataFrame) -> list[MemberRow]:
    out = frame.reset_index()[list(MemberRow.model_fields)]
    return [MemberRow(**r) for r in out.to_dict("records")]


def _sorted(frame: pd.DataFrame, sort: str, order: str) -> pd.DataFrame:
    key = sort if sort in SORTABLE else "churn_prob"
    ascending = order == "asc"
    if key == "member_id":
        return frame.sort_index(ascending=ascending)
    return frame.sort_values([key], ascending=ascending, kind="stable")


def list_members(page: int, page_size: int, sort: str, order: str, **filters) -> MemberPage:
    frame = _sorted(_filter(get_data(), **filters), sort, order)
    start = (page - 1) * page_size
    return MemberPage(
        items=_rows(frame.iloc[start : start + page_size]),
        total=len(frame),
        page=page,
        page_size=page_size,
    )


def export_csv(sort: str, order: str, **filters) -> str:
    frame = _sorted(_filter(get_data(), **filters), sort, order)
    buffer = io.StringIO()
    frame.reset_index()[list(MemberRow.model_fields)].to_csv(buffer, index=False)
    return buffer.getvalue()


def search(q: str, limit: int = 10) -> list[MemberHit]:
    frame = _filter(get_data(), q=q).sort_index().head(limit)
    return [
        MemberHit(member_id=i, segment=r.segment, risk_band=r.risk_band, churn_prob=r.churn_prob)
        for i, r in frame.iterrows()
    ]


def segment_cards() -> list[SegmentCard]:
    data = get_data()
    t = data.table
    cards = []
    for s in data.segments.to_dict("records"):
        members = t[t["segment_id"] == s["segment_id"]]
        profile = {
            c: float(v)
            for c, v in s.items()
            if c not in {"segment_id", "name", "description", "size", "churn_rate"}
        }
        cards.append(
            SegmentCard(
                segment_id=s["segment_id"],
                name=s["name"],
                description=s["description"],
                size=s["size"],
                churn_rate=s["churn_rate"],
                at_risk=int(members["risk_band"].isin(AT_RISK_BANDS).sum()),
                monthly_revenue=float(members["monthly_value"].sum()),
                profile=profile,
            )
        )
    return cards


def member_detail(member_id: str) -> MemberDetail | None:
    data = get_data()
    if member_id not in data.table.index:
        return None
    row = data.table.loc[member_id]
    scores_row = row.copy()
    scores_row["member_id"] = member_id
    features = data.features.loc[member_id]
    tables = data.tables
    members = tables["members"].set_index("member_id")
    segment = data.segments.set_index("segment_id").loc[int(row["segment_id"])]
    peers = data.features[data.table["segment_id"] == row["segment_id"]]

    profile_source = members.loc[member_id].to_dict() | features.to_dict()
    attendance = (
        tables["attendance"][tables["attendance"]["member_id"] == member_id]
        .merge(tables["classes"], on="class_id")
        .merge(tables["instructors"], on="instructor_id", suffixes=("_class", "_instructor"))
    )
    history = tables["interventions"][tables["interventions"]["member_id"] == member_id]
    return MemberDetail(
        score=to_member_score(scores_row, features),
        risk_band=row["risk_band"],
        segment_id=int(row["segment_id"]),
        segment_description=segment["description"],
        club_id=row["club_id"],
        profile={c: float(profile_source[c]) for c in PROFILE_COLUMNS},
        segment_averages={c: float(peers[c].mean()) for c in peers.columns},
        feature_labels=LABELS,
        attendance=[
            AttendanceRow(
                class_id=r["class_id"],
                class_name=r["name_class"],
                instructor_id=r["instructor_id"],
                instructor_name=r["name_instructor"],
                visits_per_week=r["visits_per_week"],
            )
            for r in attendance.to_dict("records")
        ],
        interventions=[
            InterventionRow(
                week_start=r["week_start"].date(),
                offer_id=None if pd.isna(r["offer_id"]) else r["offer_id"],
                channel=None if pd.isna(r["channel"]) else r["channel"],
                treated=r["treated"],
                stayed=r["stayed"],
            )
            for r in history.sort_values("week_start", ascending=False).to_dict("records")
        ],
    )


def _week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _outcome_trend(session: Session) -> list[OutcomeWeek]:
    weeks: dict[date, list[int]] = {}
    for outcome, logged_at in session.exec(select(Outcome.outcome, Outcome.logged_at)):
        counts = weeks.setdefault(_week(logged_at.date()), [0, 0, 0])
        counts[0] += 1
        counts[1] += outcome in REACHED
        counts[2] += outcome in RETAINED
    return [
        OutcomeWeek(week_start=w, contacted=c[0], reached=c[1], retained=c[2])
        for w, c in sorted(weeks.items())
    ]


def _plan_coverage(session: Session, at_risk_ids: set[str]) -> float | None:
    plan = session.exec(
        select(Plan).where(Plan.status == "approved").order_by(Plan.week_start.desc())
    ).first()
    if plan is None or not at_risk_ids:
        return None
    planned = set(
        session.exec(
            select(PlanItem.member_id).where(PlanItem.plan_id == plan.id, ~PlanItem.removed)
        )
    )
    return len(planned & at_risk_ids) / len(at_risk_ids)


def dashboard(session: Session) -> Dashboard:
    t = get_data().table
    at_risk = t[t["risk_band"].isin(AT_RISK_BANDS)]
    trend = _outcome_trend(session)
    latest = trend[-1] if trend else None
    edges = np.linspace(0, 1, 11)
    counts, _ = np.histogram(t["churn_prob"], bins=edges)
    mix = t.groupby("segment").agg(
        size=("churn_prob", "size"),
        at_risk=("risk_band", lambda s: int(s.isin(AT_RISK_BANDS).sum())),
    )
    return Dashboard(
        as_of=AS_OF,
        kpis=Kpis(
            total_members=len(t),
            members_at_risk=len(at_risk),
            revenue_at_risk=float((t["churn_prob"] * t["monthly_value"]).sum()),
            plan_coverage=_plan_coverage(session, set(at_risk.index)),
            contacted=latest.contacted if latest else 0,
            reached=latest.reached if latest else 0,
            retained=latest.retained if latest else 0,
            outcome_week=latest.week_start if latest else None,
        ),
        risk_distribution=[
            RiskBin(start=float(a), end=float(b), count=int(c))
            for a, b, c in zip(edges[:-1], edges[1:], counts, strict=True)
        ],
        segment_mix=[
            SegmentMix(segment=name, size=int(r["size"]), at_risk=int(r["at_risk"]))
            for name, r in mix.sort_values("size", ascending=False).iterrows()
        ],
        outcome_trend=trend,
    )
