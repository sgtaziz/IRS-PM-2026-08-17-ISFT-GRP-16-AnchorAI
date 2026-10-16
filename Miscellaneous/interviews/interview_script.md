# Club manager interview: retention playbook

**Goal:** validate or correct the rule base (`SystemCode/backend/anchorai/reasoning/rules/`). Every rule we keep after an interview gets `source: interview (<date>, <role>)`; rules the interviewee disagrees with are changed or keep `source: team assumption` with a note.

**Format:** 30–40 minutes, video call or in person. Ask for consent to take notes. Record no names of members or staff. Save notes as `YYYY-MM-DD_<role>.md` in this folder, using the template at the end.

## Opening (5 min)

1. What is your role, and how many members does your club or chain serve?
2. How do you find out today that a member is about to leave? What do you do about it?

## Warning signs: derive rules (10 min)

3. A regular who came twice a week drops by a fifth or more this month. Would you act on that? After how long? *(D01: `avg_class_frequency_total >= 2`, `trend_ratio <= 0.8`)*
4. When are new members most at risk: the first month, the first three months, or later? *(D02: `lifetime <= 1`)*
5. How low does attendance have to fall before you treat someone as disengaged? *(D03)*
6. Do members on 6- or 12-month contracts leave at renewal? How far ahead of the end date would you reach out? *(No rule yet: the Kaggle data shows no renewal risk, so a contract-ending rule was dropped. An interview could bring it back.)*
7. When an instructor leaves, do their regulars follow them out? Can you give an example? How long after does it show? *(D07, KG `lost_anchor_instructor`)*
8. Same question for a cancelled class or time slot. *(D08)*

## What you offer, and to whom: playbook rules (10 min)

9. For a new member who is slipping, what works best: a call, a free PT session, something else? *(P01)*
10. For a long-time regular who is fading? *(P02, P06)*
11. Do social offers (bring a friend, group challenges) work for members who joined with a friend? *(P04)*
12. When do you give discounts, and to whom do you never give them? *(P05, G03)*
13. Which channel gets answered: SMS, email, phone or in person? Does that depend on age or offer?

## Limits: guardrails (5 min)

14. How often can you contact the same member before it backfires? *(G01: once per 30 days; G02: two offers per 90 days)*
15. Are there members you would never spend a paid offer on? *(G04: low-risk members)*
16. Any rule you must follow: data protection, head office policy, contract terms?

## Close (5 min)

17. If a tool gave your staff a weekly call list with reasons, what would make you trust it, and what would make you ignore it?
18. Anything we should have asked?

---

## Notes template

```markdown
# Interview: <role>, <date>

- Club type and size:
- Consent to notes: yes / no

| Q | Answer (paraphrase) | Rule affected | Change |
|---|---|---|---|
| 3 | | D01 | |

Quotes we may use in the report (anonymous):
-
```
