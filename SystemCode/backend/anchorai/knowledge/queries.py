"""Parameterised, read-only Cypher templates. Values only ever go in as parameters."""

ANCHOR_SHARE = """
MATCH (m:Member)-[a:ATTENDS]->(:Class)
WITH m, sum(a.visits_per_week) AS total
WHERE total > 0
MATCH (m)-[a:ATTENDS]->(:Class)-[:TAUGHT_BY]->(i:Instructor)
WHERE EXISTS { (i)<-[:AFFECTS]-(:Event {type: 'instructor_left'}) }
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

MEMBERS_BY_INSTRUCTOR = """
MATCH (m:Member)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(i:Instructor {instructor_id: $instructor_id})
RETURN DISTINCT m.member_id AS member_id, m.churn_prob AS churn_prob, m.risk_band AS risk_band
"""

SHARE_WITH_INSTRUCTOR = """
MATCH (m:Member)-[a:ATTENDS]->(:Class)
WITH m, sum(a.visits_per_week) AS total
WHERE total > 0
MATCH (m)-[a:ATTENDS]->(:Class)-[:TAUGHT_BY]->(:Instructor {instructor_id: $instructor_id})
WITH m, total, sum(a.visits_per_week) AS lost
RETURN m.member_id AS member_id, lost / total AS share
"""

MEMBERS_BY_CLASS = """
MATCH (m:Member)-[:ATTENDS]->(k:Class {class_id: $class_id})
RETURN DISTINCT m.member_id AS member_id, m.churn_prob AS churn_prob, m.risk_band AS risk_band
"""

EGO = """
MATCH (m:Member {member_id: $member_id})
RETURN m AS root,
  COLLECT { MATCH p = (m)-[:MEMBER_OF]->(:Club) RETURN p }
  + COLLECT { MATCH p = (m)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(:Instructor) RETURN p }
  + COLLECT { MATCH p = (m)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(:Instructor)<-[:AFFECTS]-(:Event) RETURN p }
  + COLLECT { MATCH p = (m)-[:ATTENDS]->(:Class)<-[:AFFECTS]-(:Event) RETURN p }
  + COLLECT { MATCH p = (m)-[:RECEIVED]->(:Offer) RETURN p } AS paths
"""

# Busiest neighbourhoods have a few hundred members, so only the $cap highest-risk are drawn.
EGO_CLASS = """
MATCH (k:Class {class_id: $class_id})
RETURN k AS root,
  COUNT { (:Member)-[:ATTENDS]->(k) } AS member_total,
  COLLECT { MATCH p = (k)-[:TAUGHT_BY]->(:Instructor) RETURN p }
  + COLLECT { MATCH p = (k)-[:AT]->(:Club) RETURN p }
  + COLLECT { MATCH p = (k)-[:TAUGHT_BY]->(:Instructor)<-[:AFFECTS]-(:Event) RETURN p }
  + COLLECT { MATCH p = (k)<-[:AFFECTS]-(:Event) RETURN p }
  + COLLECT {
      MATCH p = (m:Member)-[:ATTENDS]->(k)
      RETURN p ORDER BY coalesce(m.churn_prob, -1) DESC LIMIT $cap
    } AS paths
"""

EGO_INSTRUCTOR = """
MATCH (i:Instructor {instructor_id: $instructor_id})
RETURN i AS root,
  size(COLLECT { MATCH (m:Member)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(i) RETURN DISTINCT m.member_id }) AS member_total,
  COLLECT { MATCH p = (:Class)-[:TAUGHT_BY]->(i) RETURN p }
  + COLLECT { MATCH p = (i)-[:WORKS_AT]->(:Club) RETURN p }
  + COLLECT { MATCH p = (i)<-[:AFFECTS]-(:Event) RETURN p }
  + COLLECT {
      MATCH (m:Member)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(i)
      WITH DISTINCT m ORDER BY coalesce(m.churn_prob, -1) DESC LIMIT $cap
      MATCH p = (m)-[:ATTENDS]->(:Class)-[:TAUGHT_BY]->(i)
      RETURN p
    } AS paths
"""
