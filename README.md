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
| Abdulaziz Ali S Hasanain | A0350856X | | |
| Asiri Mohammed Yahya A | A0351967N | | |
| Binmaneea Khalid Waleed M | A0355712E | | |

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
cp .env.example .env            # set LLM_BASE_URL / LLM_API_KEY / LLM_MODEL (Ollama, OpenAI or compatible)
docker compose up -d neo4j

cd SystemCode/backend && uv sync && uv run uvicorn anchorai.api.main:app --reload
cd SystemCode/frontend && npm install && npm run dev
```

Open http://localhost:5173. Alternatively, run `docker compose up --build` to start the full stack.

---

## SECTION 6 : PROJECT REPORT / PAPER

`Refer to project report at Github Folder: ProjectReport`

---

## SECTION 7 : MISCELLANEOUS

`Refer to Github Folder: Miscellaneous`: project proposal, proposal deck, interview notes.

---

**This project is part of the NUS-ISS Graduate Certificate in Intelligent Reasoning Systems (IRS) practice module, covering Machine Reasoning (MR), Reasoning Systems (RS) and Cognitive Systems (CGS).**
