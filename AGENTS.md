# AGENTS.md

Rules for everyone working in this repo, human or AI agent. Read this before making changes.

## Project

AnchorAI is an explainable, budget-aware gym retention planner. It is an NUS-ISS Intelligent Reasoning Systems practice-module project.

- The final submission is due **Sun 25 Oct 2026, 23:59**.

## Layout

```
SystemCode/
  backend/              Python 3.12 package `anchorai` (uv)
    anchorai/
      schemas.py        shared contracts between streams (see "Contracts")
      config.py         all runtime settings (env / .env)
      scenario/         data tables: Kaggle members + synthetic scenario layer   (Stream A)
      features/         feature engineering                                       (A)
      discovery/        segmentation, churn model, uplift baseline                (A)
      cbr/              case-based offer reasoner                                 (B)
      optimisation/     GA, CP-SAT, baselines, policy evaluator                   (B)
      reasoning/        forward-chaining rule engine + rules/*.yaml               (C)
      knowledge/        Neo4j knowledge graph                                     (C)
      assistant/        staff assistant + LLM client                              (C)
      api/              FastAPI app; one router per stream
    tests/
  frontend/             Vue 3 + Vite + TypeScript
  notebooks/            experiments E1–E8
  data/                 raw/ and generated/ (git-ignored)
ProjectReport/          report PDF + sources
Video/                  video links (files are not committed)
Miscellaneous/          proposal, deck, interview notes
docs/                   supporting docs
```

## Setup and commands

```sh
cp .env.example .env                         # then edit LLM_* and NEO4J_*
docker compose up -d neo4j                   # knowledge graph

cd SystemCode/backend
uv sync                                      # install (creates .venv, Python 3.12)
uv run anchorai setup                        # fresh clone -> data, migrated + seeded DB, KG loaded
uv run anchorai db reset                     # back to a clean seeded demo DB
uv run anchorai kg load                      # reload the knowledge graph (data tables + admin edits) and cache its rule facts
uv run anchorai data build                   # regenerate data tables, segments, churn scores, uplift (~20 s)
uv run uvicorn anchorai.api.main:app --reload   # API on :8000, docs at /docs
uv run pytest -q                             # tests
uv run ruff check . && uv run ruff format .  # lint + format

cd SystemCode/frontend
npm install
npm run dev                                  # web on :5173, proxies /api to :8000
npm run build                                # type-check + build
```

- Kaggle data: download [Gym Customers Features and Churn](https://www.kaggle.com/datasets/adrianvinueza/gym-customers-features-and-churn) into `SystemCode/data/raw/`.
- Everything in `data/generated/` must be reproducible from code with `ANCHORAI_SEED`.

## Before you commit

1. `uv run ruff check . && uv run ruff format .` and `uv run pytest -q` pass (backend).
2. `npm run build` passes (frontend, if touched).
3. No secrets, data files, notebook checkpoints, `node_modules`, `.venv` or large binaries are staged.

## Commits and branches

- **One-line subject only. No body, no trailers.** Use [Conventional Commits](https://www.conventionalcommits.org):

  ```
  feat(optimisation): add repair operator to GA
  fix(api): return 404 for unknown member
  docs: add installation guide
  ```

- **Types:** `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `build`, `ci`, `style`, `exp`. Use `exp` for experiment notebooks and results.
- **Scope:** the package or area, e.g. `scenario`, `discovery`, `cbr`, `optimisation`, `reasoning`, `knowledge`, `assistant`, `api`, `web`, `report`.
- Write the subject in the imperative, lowercase, with no trailing period, at most 72 characters.
- Make small, focused commits. One logical change per commit.
- **Branches:** short-lived `<stream>/<topic>` branches (e.g. `b/ga-repair`), merged to `main` by PR.
  - At least one review from a member of another stream.
  - Squash-merge, with a PR title in the same commit format.
  - Never force-push to `main`.

## Code style

### General

- Match the surrounding code. Keep it simple: the smallest change that does the job.
- **Comments only where code is complex or hard to read.** Explain *why*, not *what*.
  - No comments that restate the code.
  - No commented-out code.
  - No banner or section comments.
  - No TODO notes in place of work. Track open work in the PR or the issue instead.
- Docstrings only for non-obvious public functions. One line is usually enough.
- Clear names over comments.
- Don't add dependencies without agreement from the team. Add them via `uv add` / `npm install` so the lockfiles stay in sync.

### Python

- Type hints on public functions. Use pydantic models for anything that crosses a stream boundary.
- Keep logic in plain functions or modules. **API routers stay thin**: parse the request, call the package, return a schema.
- App state (users, plans, outcomes, rule versions, audit) lives in SQLite via SQLModel. Every write endpoint records an audit entry and requires a role dependency.
- Make code deterministic: every random process takes a seed, defaulting to `settings.anchorai_seed`.
- Read paths and settings through `anchorai.config.get_settings()`. Never hard-code absolute paths.
- Use pandas / numpy vectorised operations over Python loops on member-sized data.
- Notebooks import from `anchorai`. They do not copy logic. If a notebook cell is needed by the app, move it into the package.

### Frontend

- Use Vue 3 `<script setup lang="ts">` and the composition API.
- Call the backend only through `src/api/client.ts`. Keep TypeScript types in step with `schemas.py`.
- UI kit: PrimeVue. Charts: ECharts (`vue-echarts`). Graphs: Cytoscape.js. State: Pinia. Don't add other UI libraries without agreement.
- Every page handles loading, empty and error states. Role access is declared in `router.ts` `meta.roles` and enforced again server-side.
- Every page and feature has an ID and an owning stream. Put shared components in `src/components/`.

## Database

- SQLite + SQLModel. The schema is managed **only** by Alembic migrations in `SystemCode/backend/migrations/`.
- A model change and its migration go in the same PR. Review autogenerated migrations before committing, and keep batch mode on for SQLite.
- Never edit a migration that is already on `main`. Add a new one. If `main` gained a migration while you worked, rebase and run `alembic merge heads`.
- Never commit `.db` files, and never fix data by hand. Change the seeds (idempotent, deterministic, in `anchorai/db/seeds/`) and run `anchorai db reset`.
- When you add a table your feature needs, add its seed rows too, so a fresh clone shows a working page.

## Contracts

- `anchorai/schemas.py` and the data-table columns (`anchorai/scenario/tables.py`) are shared between streams.
  - Change them only with agreement from all three streams.
  - Make the change in its own commit, e.g. `feat(schemas): add channel to PlanItem`, and update every consumer in the same PR.
- Until real data exists, build against the fixtures in `tests/fixtures/`, which have the same columns.

## Tests

- Add a test only when it guards against a real regression or a likely error. Examples:
  - leakage checks
  - constraint feasibility of a plan
  - rule-engine firing order
  - API contract shape
- Don't write tests for trivial code, framework behaviour or one-off notebooks.
- Keep tests fast (whole suite in seconds) and offline. Mock the LLM and Neo4j.

## LLM and knowledge graph

- All LLM calls go through `anchorai/assistant/llm.py`. The provider is set only by `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`, so it can be Ollama, OpenAI or any OpenAI-compatible API.
- **Grounding:** the assistant answers only from tool output (plan, explanation, rule trace, Cypher results) and says when it doesn't know.
- Cypher queries are parameterised templates; never string-format user input into queries. Use a read-only path for assistant queries.
- The pipeline must still run, degraded, when the LLM or Neo4j is unavailable.

## Notebook first for AI work

Any AI or ML setup or testing starts in a notebook in `SystemCode/notebooks/` before it goes into `SystemCode/backend/`. This covers LLM prompts and endpoints, embeddings and intent classifiers, model training and tuning, KG queries and rule thresholds.

1. **Prototype in a notebook.** Name it `<stream>_<topic>.ipynb`, e.g. `c_intent_classifier.ipynb`.
2. **Test it live with the owner.** The owner runs the cells and inspects the outputs. AI agents guide them cell by cell (what to run, what to look for, what to tweak) rather than writing the whole thing unseen.
3. **Move the final version into the package.** Once the behaviour is agreed, put the logic in `anchorai/`, add tests where they guard a real regression, and change the notebook to import it.

## Secrets and data

- Secrets live only in `.env`, which is git-ignored. Never hard-code keys.
  - Some course workshop notebooks contain hard-coded API keys. Do not copy code from them verbatim.
- Do not commit datasets or generated data. The Kaggle dataset is CC BY-NC-SA 4.0: cite it and don't redistribute it.
- No real personal data. Member IDs are pseudonymous.

## Academic integrity

- Keep a running log of meaningful AI-tool use in `docs/AI_USE.md`: what the tool was, what it was used for, and what we changed. It feeds the report's AI-use appendix.
- **Video narration must be our own voices.** AI-generated speech is not allowed.
- Every claim in the report must be reproducible from a notebook in `SystemCode/notebooks/` or from a script.

## Definition of done (per task)

- Works end to end from the API (and its page, if it has one) on the current data.
- Lint, tests and build pass, and the change has been reviewed by another stream.
- If it changes how to install, configure or run the system (new command, env var, service or seed), the README quick start and the "Setup and commands" section above are updated in the same change, and the user-guide notes for the report when a user-facing step changes.
- Experiment results, if any, are saved as figures and tables under `SystemCode/notebooks/` and referenced in the report.
