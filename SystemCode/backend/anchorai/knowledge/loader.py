"""Builds the knowledge graph from the data tables: idempotent, batched, parameterised."""

import json
from collections.abc import Iterator
from typing import Any

import pandas as pd
from neo4j import Driver

BATCH = 1000

NODE_KEYS = {
    "Member": "member_id",
    "Club": "club_id",
    "Instructor": "instructor_id",
    "Class": "class_id",
    "Offer": "offer_id",
    "Event": "event_id",
}
CONSTRAINTS = [
    f"CREATE CONSTRAINT {key} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
    for label, key in NODE_KEYS.items()
]

CLEAR = "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS"

CLUBS = "UNWIND $rows AS r MERGE (:Club {club_id: r.club_id})"

MEMBERS = """
UNWIND $rows AS r
MERGE (m:Member {member_id: r.member_id})
SET m += r.props
WITH m, r
MATCH (c:Club {club_id: r.club_id})
MERGE (m)-[:MEMBER_OF]->(c)
"""

INSTRUCTORS = """
UNWIND $rows AS r
MERGE (i:Instructor {instructor_id: r.instructor_id})
SET i.name = r.name
WITH i, r
MATCH (c:Club {club_id: r.club_id})
MERGE (i)-[:WORKS_AT]->(c)
"""

CLASSES = """
UNWIND $rows AS r
MERGE (k:Class {class_id: r.class_id})
SET k.name = r.name
WITH k, r
MATCH (i:Instructor {instructor_id: r.instructor_id})
MATCH (c:Club {club_id: r.club_id})
MERGE (k)-[:TAUGHT_BY]->(i)
MERGE (k)-[:AT]->(c)
"""

ATTENDANCE = """
UNWIND $rows AS r
MATCH (m:Member {member_id: r.member_id})
MATCH (k:Class {class_id: r.class_id})
MERGE (m)-[a:ATTENDS]->(k)
SET a.visits_per_week = r.visits_per_week
"""

OFFERS = """
UNWIND $rows AS r
MERGE (o:Offer {offer_id: r.offer_id})
SET o.name = r.name, o.cost = r.cost
"""

INTERVENTIONS = """
UNWIND $rows AS r
MATCH (m:Member {member_id: r.member_id})
MATCH (o:Offer {offer_id: r.offer_id})
MERGE (m)-[x:RECEIVED {intervention_id: r.intervention_id}]->(o)
SET x.week_start = date(r.week_start), x.channel = r.channel, x.stayed = r.stayed
"""

EVENTS = """
UNWIND $rows AS r
MERGE (e:Event {event_id: r.event_id})
SET e.type = r.event_type, e.week_start = date(r.week_start)
WITH e, r
OPTIONAL MATCH (i:Instructor {instructor_id: r.entity_id})
OPTIONAL MATCH (k:Class {class_id: r.entity_id})
WITH e, coalesce(i, k) AS target
WHERE target IS NOT NULL
MERGE (e)-[:AFFECTS]->(target)
"""

MEMBER_PROPS = ["segment", "churn_prob", "risk_band", "monthly_value"]


def _batches(rows: list[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), BATCH):
        yield rows[start : start + BATCH]


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    # Through JSON so the driver gets plain Python types (no numpy scalars) and NaN -> None.
    return json.loads(frame.to_json(orient="records"))


def _date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y-%m-%d")


def member_rows(members: pd.DataFrame, scores: pd.DataFrame | None) -> list[dict[str, Any]]:
    frame = members[["member_id", "club_id"]]
    if scores is not None:
        frame = frame.merge(scores[["member_id", *MEMBER_PROPS]], on="member_id", how="left")
    props = [c for c in MEMBER_PROPS if c in frame.columns]
    return [
        {"member_id": r["member_id"], "club_id": r["club_id"], "props": {p: r[p] for p in props}}
        for r in _records(frame)
    ]


def load_graph(
    driver: Driver,
    tables: dict[str, pd.DataFrame],
    scores: pd.DataFrame | None = None,
    clear: bool = True,
) -> dict[str, int]:
    """Load the data tables into Neo4j and return row counts per step."""
    treated = tables["interventions"][tables["interventions"]["treated"]].assign(
        week_start=lambda d: _date(d["week_start"])
    )
    events = tables["events"].assign(week_start=lambda d: _date(d["week_start"]))
    steps = [
        ("clubs", CLUBS, [{"club_id": c} for c in sorted(tables["members"]["club_id"].unique())]),
        ("members", MEMBERS, member_rows(tables["members"], scores)),
        ("instructors", INSTRUCTORS, _records(tables["instructors"])),
        ("classes", CLASSES, _records(tables["classes"])),
        ("attendance", ATTENDANCE, _records(tables["attendance"])),
        ("offers", OFFERS, _records(tables["offers"][["offer_id", "name", "cost"]])),
        (
            "interventions",
            INTERVENTIONS,
            _records(
                treated[
                    ["intervention_id", "member_id", "offer_id", "channel", "week_start", "stayed"]
                ]
            ),
        ),
        ("events", EVENTS, _records(events[["event_id", "event_type", "entity_id", "week_start"]])),
    ]
    counts: dict[str, int] = {}
    with driver.session() as session:
        if clear:
            session.run(CLEAR).consume()
        for statement in CONSTRAINTS:
            session.run(statement).consume()
        for name, query, rows in steps:
            for batch in _batches(rows):
                session.execute_write(lambda tx, q=query, b=batch: tx.run(q, rows=b).consume())
            counts[name] = len(rows)
    return counts
