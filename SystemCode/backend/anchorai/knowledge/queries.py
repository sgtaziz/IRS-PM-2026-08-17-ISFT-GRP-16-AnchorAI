"""Parameterised, read-only Cypher templates. Values only ever go in as parameters."""

ANCHOR_SHARE = """
MATCH (m:Member)-[a:ATTENDS]->(:Class)
WITH m, sum(a.visits_per_week) AS total
WHERE total > 0
MATCH (m)-[a:ATTENDS]->(:Class)-[:TAUGHT_BY]->(:Instructor)<-[:AFFECTS]-(:Event {type: 'instructor_left'})
WITH m, total, sum(a.visits_per_week) AS lost
RETURN m.member_id AS member_id, lost / total AS anchor_instructor_share
"""

CLASS_CANCELLED = """
MATCH (m:Member)-[:ATTENDS]->(:Class)<-[:AFFECTS]-(:Event {type: 'class_cancelled'})
RETURN DISTINCT m.member_id AS member_id
"""

COHORT_RISK = """
MATCH (m:Member)-[:ATTENDS]->(:Class)<-[:ATTENDS]-(peer:Member)
WHERE peer <> m AND peer.churn_prob IS NOT NULL
WITH m, collect(DISTINCT peer) AS peers
RETURN m.member_id AS member_id, reduce(s = 0.0, p IN peers | s + p.churn_prob) / size(peers) AS cohort_risk
"""

EGO = """
MATCH (m:Member {member_id: $member_id})
OPTIONAL MATCH club = (m)-[:MEMBER_OF]->(:Club)
OPTIONAL MATCH taught = (m)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(:Instructor)
OPTIONAL MATCH left = (m)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(:Instructor)<-[:AFFECTS]-(:Event)
OPTIONAL MATCH cancelled = (m)-[:ATTENDS]->(:Class)<-[:AFFECTS]-(:Event)
OPTIONAL MATCH offered = (m)-[:RECEIVED]->(:Offer)
RETURN m,
       collect(DISTINCT club) + collect(DISTINCT taught) + collect(DISTINCT left)
       + collect(DISTINCT cancelled) + collect(DISTINCT offered) AS paths
"""
