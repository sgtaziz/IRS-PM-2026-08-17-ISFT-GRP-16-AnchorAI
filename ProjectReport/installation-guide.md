# Installation guide

Source for the report appendix "Installation guide". It takes a fresh clone to a running, seeded AnchorAI with data, models and demo users.

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Git | any recent | cloning |
| [uv](https://docs.astral.sh/uv/) | 0.13 or newer | the backend's Python 3.12 environment and dependencies; uv downloads Python 3.12 itself if it is missing |
| Node.js and npm | Node 20 or newer | the web app (its CSS build needs Node 20; the Docker image uses Node 22) |
| Docker with Compose | any recent | Neo4j (knowledge graph); optional full-stack run |
| An OpenAI-compatible LLM endpoint | Ollama, OpenAI or similar | staff assistant and message drafts (optional) |

The data pipeline, API and web app run without Neo4j and without an LLM. The graph panels and the assistant are then shown as unavailable.

## 1. Get the code and configure it

```sh
git clone <repo-url> AnchorAI && cd AnchorAI
cp .env.example .env
```

Edit `.env`:

- `ANCHORAI_JWT_SECRET`: set a random value (`openssl rand -hex 32`). The server warns at start-up while the published default is in use.
- `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`: your LLM endpoint. The defaults point at a local Ollama server (`http://localhost:11434/v1`, model `qwen2.5:7b-instruct`; run `ollama pull qwen2.5:7b-instruct` once). For OpenAI, use `https://api.openai.com/v1` with your key and a model name.
- `ANCHORAI_SEED`: leave at `42` to reproduce the reported results.

## 2. Get the dataset

1. Download *Gym Customers Features and Churn* from Kaggle: <https://www.kaggle.com/datasets/adrianvinueza/gym-customers-features-and-churn>.
2. Unzip it and put `gym_churn_us.csv` in `SystemCode/data/raw/`.

The dataset is CC BY-NC-SA 4.0. It is not included in the repository.

## 3. Start Neo4j

```sh
docker compose up -d neo4j
```

The Neo4j browser is at <http://localhost:7474> (user `neo4j`, password `NEO4J_PASSWORD` from `.env`, `anchorai-dev` by default).

## 4. Install and set up the backend

```sh
cd SystemCode/backend
uv sync
uv run anchorai setup
```

`anchorai setup` runs three steps:

1. **`data build`** (about 20 s). It builds the data tables from the Kaggle CSV, segments members, trains the calibrated churn model and the T-learner, then writes the outputs to `SystemCode/data/generated/`.
2. **`db reset`**. It creates `SystemCode/data/app.db`, applies migrations, and seeds demo users, the rule base, offers, the staff roster and constraints, plus the demo layer (one approved week with logged outcomes).
3. **`kg load`**. It loads the knowledge graph into Neo4j and caches the graph signals (lost instructor, cancelled class, cohort risk) to `SystemCode/data/generated/kg_facts.parquet` for the rule engine. If Neo4j is not running, this step is skipped with a warning: the app still works, but rules on graph signals don't fire and graph panels show as unavailable. Start Neo4j and run `uv run anchorai kg load` to add them.

You can run each step on its own:

| Command | Does |
|---|---|
| `uv run anchorai data build` | Regenerate data tables and models from `data/raw/` |
| `uv run anchorai db upgrade` | Apply database migrations |
| `uv run anchorai db seed [--demo]` | Load seed data |
| `uv run anchorai db reset` | Fresh, seeded demo database |
| `uv run anchorai kg load` | Reload the knowledge graph |

### Staff assistant

The assistant needs an OpenAI-compatible LLM endpoint (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` in `.env`). It also downloads the `all-MiniLM-L6-v2` embedding model (about 90 MB) for intent detection, the first time the API starts (or at the first question, with `ASSISTANT_WARMUP=false`); after that it runs offline. If the LLM is unreachable, the assistant still answers, straight from the evidence lines.

## 5. Run

```sh
# terminal 1, in SystemCode/backend
uv run uvicorn anchorai.api.main:app --reload      # API on :8000, docs at /docs

# terminal 2, in SystemCode/frontend
npm install
npm run dev                                       # web app on :5173
```

Open <http://localhost:5173> and sign in with a demo user. The password for every demo user is `anchorai`, or the value of `ANCHORAI_DEMO_PASSWORD`.

| User | Role | Lands on |
|---|---|---|
| `admin` | Admin | Dashboard; also Rules, Offers & constraints, Data & models, Users, Audit log, Settings |
| `manager` | Manager | Dashboard, Segments, Members, Weekly plan, Scenarios, Knowledge graph, Events & roster |
| `staff1`, `staff2` | Staff | My contacts, Member 360, Assistant |

## Alternative: Docker for everything

```sh
cd SystemCode/backend && uv sync && uv run anchorai data build   # once, on the host
cd ../.. && docker compose up --build -d                         # follow with: docker compose logs -f api
cd SystemCode/backend && uv run anchorai kg load                 # once the stack is up
```

The API container mounts `SystemCode/data`, migrates and seeds the database on start, and serves on port 8000. The web app is on <http://localhost:5173>. Build the data on the host first, because the demo seed needs the data tables. The container does not load the knowledge graph: run `kg load` from the host as above, or sign in as a manager and select **Reload knowledge graph** on the Events & roster page.

## Checking the install

```sh
cd SystemCode/backend && uv run pytest -q      # backend tests, offline, ~15 s
cd SystemCode/frontend && npm run build        # type-check and production build
```

In the app, sign in as `admin` and open **Settings**. It shows whether the language model, Neo4j, the models and data, and the database are working, and **Test connection** checks the LLM endpoint.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Expected exactly one Kaggle CSV in …/data/raw` | Put exactly one CSV, `gym_churn_us.csv`, in `SystemCode/data/raw/` |
| Pages show "Data tables are not built yet" (HTTP 503) | Run `uv run anchorai data build` |
| Login fails for demo users | Run `uv run anchorai db reset` |
| Graph panels or assistant show "unavailable" | Start Neo4j or the LLM endpoint; the rest of the app keeps working |
| `npm run build` or `npm run dev` fails with an engine or native-binding error | Upgrade to Node 20 or newer, then delete `node_modules` and run `npm install` again |
| `docker compose up` fails with "failed to add the host <=> sandbox pair interfaces: operation not supported" | The kernel was updated but not rebooted, so Docker's network module is missing. Reboot |
| Port 8000 or 5173 is in use | Stop the other process, or pass `--port` to uvicorn and change `vite.config.ts` |
