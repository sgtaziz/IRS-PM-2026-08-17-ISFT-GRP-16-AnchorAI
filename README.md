## SECTION 1 : PROJECT TITLE
## AnchorAI: Retention Intelligence for Gyms

---

## SECTION 2 : EXECUTIVE SUMMARY / PAPER ABSTRACT

Gym members stop attending weeks or months before they cancel. AnchorAI uses that gap. It segments members by behaviour and predicts who is likely to leave. It then picks who to contact, with which offer and through which channel, within a fixed budget and limited staff hours. Every recommendation comes with a justification staff can challenge: the member's churn drivers, the playbook rules that fired, similar past cases, and knowledge-graph signals such as a departed instructor.

Techniques: K-means segmentation, a calibrated churn ensemble, a forward-chaining rule engine, case-based reasoning, a genetic algorithm benchmarked against CP-SAT, a Neo4j knowledge graph, and a grounded natural-language staff assistant.

---

## SECTION 3 : CREDITS / PROJECT CONTRIBUTION

| Official Full Name | Student ID | Work Items (Who Did What) | Email |
| :-- | :--: | :-- | :-- |
| Abdulaziz Ali S Hasanain | A0350856X | Project plan, work split and repo scaffold. Led knowledge and interaction, covering the rule engine with validator, guardrails and rule versioning, Neo4j knowledge graph, grounded staff assistant, app database with migrations, seeds and login by role, experiments E6 to E8, UI/UX work | abdulaziz@u.nus.edu |
| Asiri Mohammed Yahya A | A0351967N | Led decision and optimisation, covering the case-based reasoner for offer effects, genetic algorithm with an exact CP-SAT benchmark, plan, approval and call-sheet pages, demo week, experiments E3 to E5 | asiri@u.nus.edu |
| Binmaneea Khalid Waleed M | A0355712E | Led member intelligence, covering data cleaning, features and segmentation, churn ensemble, synthetic scenario layer, T-learner uplift benchmark, member and dashboard pages, experiments E1 and E2, LaTeX group report | khalid@u.nus.edu |

---

## SECTION 4 : VIDEO OF SYSTEM MODELLING & USE CASE DEMO

- Promotion video: _link_
- System design video: _link_

---

## SECTION 5 : USER GUIDE

`Refer to appendix <Installation & User Guide> in project report at Github Folder: ProjectReport`

### Quick start

```sh
git clone <repo-url> && cd AnchorAI
cp .env.example .env            # set LLM_* (Ollama, OpenAI or compatible) and ANCHORAI_JWT_SECRET (openssl rand -hex 32)
docker compose up -d neo4j
# download gym_churn_us.csv from https://www.kaggle.com/datasets/adrianvinueza/gym-customers-features-and-churn
# (CC BY-NC-SA 4.0, not redistributed here) into SystemCode/data/raw/

cd SystemCode/backend && uv sync
uv run anchorai setup           # data tables, migrated + seeded app DB, knowledge graph
uv run uvicorn anchorai.api.main:app --reload

# in a second terminal, from the repo root
cd SystemCode/frontend && npm install && npm run dev
```

Open http://localhost:5173 and log in as `admin`, `manager`, `staff1` or `staff2` with password `anchorai` (set by `ANCHORAI_DEMO_PASSWORD`). Run `uv run anchorai db reset` for a clean demo database. Alternatively, run `docker compose up --build` to start the full stack; the API container migrates and seeds the database on start.

---

## SECTION 6 : PROJECT REPORT / PAPER

`Refer to project report at Github Folder: ProjectReport`

---

## SECTION 7 : MISCELLANEOUS

`Refer to Github Folder: Miscellaneous`: project proposal, proposal deck, interview notes.

---

**This project is part of the NUS-ISS Graduate Certificate in Intelligent Reasoning Systems (IRS) practice module, covering Machine Reasoning (MR), Reasoning Systems (RS) and Cognitive Systems (CGS).**
