# Cognitive: knowledge graph and staff assistant

*Code: `SystemCode/backend/anchorai/knowledge/` and `anchorai/assistant/`. Notebooks: `c_kg.ipynb`, `c_intent_classifier.ipynb`, `c_llm_smoke.ipynb`, `c_message_drafts.ipynb` (experiments E7 and E8 are in the experiments section).*

The cognitive layer does two jobs. The knowledge graph (KG) finds who is hit by a gym event, such as a favourite instructor leaving, and feeds that to the rule base. The assistant lets staff ask why a member is flagged, in plain English, and answers only from evidence the system already computed. Both are built to keep working when Neo4j or the LLM is down (last section).

## Knowledge graph

### Schema

The graph lives in Neo4j. `knowledge/loader.py` builds it from the member-intelligence data tables, in batches of 1,000 rows with parameterised `UNWIND ... MERGE` statements, so a reload is idempotent. A uniqueness constraint is created on each node's id.

| Node | Key | Notes |
|---|---|---|
| `Member` | `member_id` | also carries `segment`, `churn_prob`, `risk_band`, `monthly_value` from the member scores |
| `Club` | `club_id` | |
| `Instructor` | `instructor_id` | `name` |
| `Class` | `class_id` | `name` |
| `Offer` | `offer_id` | `name`, `cost` |
| `Event` | `event_id` | `type` (`instructor_left`, `class_cancelled`), `week_start` |

| Relationship | Meaning |
|---|---|
| `(Member)-[:MEMBER_OF]->(Club)` | home club |
| `(Instructor)-[:WORKS_AT]->(Club)` | |
| `(Class)-[:TAUGHT_BY]->(Instructor)`, `(Class)-[:AT]->(Club)` | |
| `(Member)-[:ATTENDS {visits_per_week}]->(Class)` | the cohort link |
| `(Member)-[:RECEIVED {intervention_id, week_start, channel, stayed}]->(Offer)` | treated interventions only |
| `(Event)-[:AFFECTS]->(Instructor or Class)` | which entity the event hit |

On the demo data the graph has 4,000 members, 3 clubs, 9 instructors, 18 classes, 4 offers and 2 events (`c_kg.ipynb`, section 0). The two events are an instructor leaving (Maya Chen, who taught Core and Zumba) and a cancelled HIIT class, both in the week of 5 Oct 2026.

### Loading, including admin edits

`uv run anchorai kg load` (also part of `anchorai setup`) calls `knowledge/reload.py`. It does not read the raw generated tables. It reads the *effective* tables from `knowledge/entities.py`: the generated instructors, classes and events with the admin roster edits from SQLite applied on top.

- Added instructors and classes get `IX` / `KX` ids, so they cannot clash with generated `I` / `K` ids.
- A class override says who teaches a class now.
- An added event adds an event row. A row with `suppresses` hides a generated event. A suppression matches the event id, entity and type, because after a rebuild the same id may be a different event.
- The overlay never changes attendance, so an added class has no members until the data is rebuilt (module docstring).
- Offers come from the live catalogue, with inactive offers kept so past interventions still link to their `Offer` node.

A data rebuild overwrites the generated tables, which is why edits live in SQLite and are merged on read, not written into the tables.

### Read-only Cypher templates

All queries are fixed templates in `knowledge/queries.py`. Values go in only as parameters, and `knowledge/graph.py` runs them in a `READ` transaction, which Neo4j enforces by rejecting writes. A test checks that the loader sends values only as parameters (`tests/test_knowledge.py::test_loader_only_sends_values_as_parameters`).

| Template | Used for |
|---|---|
| `ANCHOR_SHARE` | share of a member's class visits taught by instructors who have left |
| `CLASS_CANCELLED` | members who attend a cancelled class |
| `COHORT_RISK` | mean churn probability of the people a member shares classes with |
| `MEMBERS_BY_INSTRUCTOR`, `MEMBERS_BY_CLASS` | assistant `graph_impact` answers |
| `SHARE_WITH_INSTRUCTOR` | what-if simulation |
| `EGO`, `EGO_CLASS`, `EGO_INSTRUCTOR` | graph explorer neighbourhoods |

### Signals as rule facts

`knowledge/signals.py` runs the first three templates and writes one row per member with any signal to `data/generated/kg_facts.parquet`.

| Fact | Meaning |
|---|---|
| `anchor_instructor_share` | share of weekly class visits taught by instructors who left |
| `lost_anchor_instructor` | true when that share is at least `ANCHOR_SHARE_THRESHOLD` = 0.5 |
| `class_cancelled` | the member attends a cancelled class |
| `cohort_risk` | mean churn probability of class peers |

The rule engine (see the decision-automation section) reads these facts from the parquet file (`reasoning/service.py::all_facts`), not from Neo4j. So the rules fire the same with Neo4j stopped.

Decisions from `c_kg.ipynb`:
- The 0.5 threshold flags 186 members. The sweep over 0.25 to 1.00 flags 256 down to 100 (section 1). 170 members attend the cancelled class (section 2).
- `cohort_risk` is kept as a fact but not shown to staff. On the real data it sits between 0.15 and 0.21 for everyone, and its correlation with a member's own churn probability is -0.04 (section 3), so it does not tell one member from another.
- Against the Kaggle label the KG flags show no lift (lift 0.63 and 0.72, section 4). That is expected, because the label knows nothing about the synthetic gym events. E7 measures them against the scenario's event effect instead.

### Staleness and reload

`reload.py` keeps the graph honest after edits.
- A reload takes about a second on the demo data, so the API waits for it instead of queueing a job (module docstring). While it runs, reads that use the default driver fail fast with "Knowledge graph is reloading", rather than seeing a half-loaded graph (`graph.py`).
- The facts file is written to a temporary name and renamed, so a request never reads a half-written file (`signals.py::save_kg_facts`).
- The status is **stale** when the facts file is missing, when it is older than the last data build (`model_card.json`), or when a `gym.*` audit entry is newer than the facts file. The last check reads the audit log, so it survives a restart.
- `sync_graph` never raises. If Neo4j is down, the edit is saved, the status is marked stale with the reason, and the manager can reload later. `POST /api/admin/kg/reload` returns 503 in that case and records `kg.reload_failed` in the audit log. `GET /api/admin/kg/status` reports the state. Both need the manager role.
- Pages that depend on the graph show a warning while the status is stale (`Simulation.graph_out_of_date`, and a line in the assistant's `graph_impact` evidence).

### Class cohorts for the optimiser

`entities.class_cohorts()` gives the genetic algorithm one row per member and class: `member_id`, `class_id`, `weight` and `instructor_id`. The weight is the member's share of their own class visits, and the instructor is whoever teaches the class now. It is computed from the effective tables, so a reassigned class counts for its new instructor. It does not need Neo4j.

### What-if event simulation

`knowledge/simulate.py` answers "what if this instructor left, or this class were cancelled?" without changing anything.
1. It reads the affected members and, for an instructor, their share of visits with that person from the graph.
2. It adds the share to the member's existing `anchor_instructor_share` (capped at 1.0, and not added twice if the event already happened), or sets `class_cancelled`.
3. It reruns the rule engine on those altered facts and compares the rules fired before and after.

The result lists the affected members, how many are high risk, how many newly trigger a rule, and the offers now allowed. Only the in-memory facts change.

### Graph explorer (W18)

`api/routers/graph.py` serves the explorer page. `knowledge/ego.py` returns a neighbourhood in Cytoscape's elements format.

| Endpoint | Shows | Roles |
|---|---|---|
| `GET /api/graph/ego/{member_id}` | club, classes, instructors, events that hit them, offers received | any |
| `GET /api/graph/ego/class/{id}` and `.../instructor/{id}` | instructor or classes, club, events, and members | manager, admin |
| `GET /api/graph/entities` | instructors and classes to pick from | manager, admin |
| `POST /api/graph/simulate` | the what-if above | manager, admin |

Busy classes and instructors have a few hundred members, so only the 40 highest-risk are drawn (`MEMBER_CAP`), and `member_total` gives the full count. A missing id returns 404 and a down graph 503.

## Staff assistant

The assistant is a pipeline with the LLM at the end (`assistant/service.py`):

**question → intent → slots → deterministic tool → evidence lines → grounded LLM rewrite**

The LLM never chooses a tool and never sees data the tool did not return.

### Intents and classifier

`assistant/intents.yaml` defines seven intents, each with example questions, plus a similarity threshold of 0.35 and a list of out-of-scope questions used only to tune it.

| Intent | Question it answers | Member ids needed |
|---|---|---|
| `member_risk` | why a member is at risk | 1 |
| `member_actions` | what to offer and why (rule trace) | 1 |
| `compare_members` | why one member ranks above another | 2 to 9 |
| `graph_impact` | who an instructor leaving or class cancelling affects | none |
| `list_members` | ranked list by risk, band, segment, club or new members | none |
| `plan_summary` | what is in the weekly plan | none |
| `what_if_budget` | how the plan changes with another budget or staff hours | none |

`assistant/classifier.py` embeds each example with `all-MiniLM-L6-v2` (`config.py`) after slot placeholders replace ids, amounts and names, then averages them into one centroid per intent. A question goes to the closest centroid by cosine similarity. Three rules sit on top:
- **Unknown threshold.** If the best score is below 0.35, the intent is `unknown` and the assistant says it doesn't know.
- **Slot rule.** An intent whose member-id count is not met cannot win (`member_slots`), so a single-member question is never read as a comparison. When the question names no member, the member open on the page fills in.
- **Read-only.** Questions that start with "delete", "update", "change" and similar are `unknown`, however close they sound to a member question.

`c_intent_classifier.ipynb` compared the design options on 69 AI-written questions kept out of the training examples (section 6): the plain centroid reached 0.928 accuracy, kNN 0.826 and a keyword baseline 0.725, and adding the slot rule gave 0.986. These numbers chose the design; they are not the result. The questions share their author with the training examples, and the 0.35 threshold was chosen after seeing them (section 7). On questions written by Stream B, which the classifier's author never saw, accuracy falls to 55.6%, below the keyword baseline's 77.8%, mostly because off-topic questions get an answer instead of a refusal (E8, `c-experiments-e6-e8.md`).

### Slot filling

`assistant/slots.py` uses regular expressions and name lookups. Each slot is removed from the text before the next one is matched, so one number cannot be read twice.

| Slot | Examples |
|---|---|
| Member ids | `M0155`, `member 155`, a bare `1043`. A bare number is not an id when it is a year, or follows or precedes words like "top", "weeks", "months", "%" |
| Amounts | `$2,000`, `2k`, `500 dollars`, "budget drops to 1000" |
| Extra amounts | "another $1,500", "$1,000 more", "10 extra staff hours" are added to the current limit, not used instead of it (`extra_amount`, `extra_hours`) |
| Staff hours | "40 staff hours", "50 hours of staff time" |
| Instructors, classes | by name from the live roster. A first name needs a capital letter. A class name needs "class" next to it or a capital after the first word, because names like "Core" and "Step" are common words |
| List filters | "top 10", "first five", "high risk", "club C2", "new members", segment words |

The order mattered: money is taken out before member ids, which stopped "budget drops to 1000" becoming member M1000. Tests: `tests/test_assistant.py` (`test_money_never_becomes_a_member`, `test_what_if_reads_extra_limits_as_on_top`).

### Deterministic tools

`assistant/tools.py` has one function per intent. Each returns numbered evidence lines (`[E1]`, `[E2]`, ...) built from services the API already uses, or a fixed note when it cannot answer.

- `member_risk`: churn probability and band, segment, profile, top risk drivers, KG signals, and the member's plan status.
- `member_actions`: profile, the rules that fired, the offers they allow and block, and plan status.
- `compare_members`: score and rule lines for two members, side by side. Only the first two are compared and the evidence says so.
- `graph_impact`: counts of members behind an instructor or class, how many are high risk, and the five riskiest. With no name given, it uses the events that have happened. Out-of-date graph and unreachable graph are both reported.
- `list_members`: the top members by churn probability, with optional filters, 10 by default and at most 25.
- `plan_summary`: the latest plan's contacts, cost, staff minutes, expected extra members retained, and contacts per offer.
- `what_if_budget`: runs the exact linear planner (`optimisation/exact.solve_linear`, 5-second limit) twice, on the current limits and on the asked limits, without saving anything. It reports contacts, expected extra members retained, cost, staff hours and which limits block further contacts, then the difference. With no amount or hours in the question it asks for one.

The planner behind `what_if_budget` is the same code that produces the saved plan, and a test checks the two agree (`test_what_if_budget_plans_read_only_and_matches_saved_plan_summary`).

### Grounded prompt

`assistant/prompt.py` is the prompt agreed in `c_llm_smoke.ipynb`. The system message says:
- Answer **only** from the evidence lines in the latest message.
- End every sentence and bullet with the ids it relies on, such as `[E1][E3]`.
- If the evidence does not answer the question, reply exactly: `I don't know based on the data I have.`
- Never invent numbers, names, offers or reasons. No advice or comments that no evidence line makes. At most 80 words, plain English.

The last three question-and-answer pairs go in as history so "they" and "that offer" resolve. Old answers have their citations stripped, because the latest message reuses the same ids for different lines. The notebook ran three checks: an answerable question, an empty evidence list, and evidence that does not cover the question. The last two both returned the exact "don't know" sentence.

### LLM client

`assistant/llm.py` is the only place that calls an LLM. It uses the OpenAI client with `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`, so the provider can be a hosted API or a local Ollama server with no code change. Defaults (`config.py`): Ollama at `http://localhost:11434/v1`, model `qwen2.5:7b-instruct`, temperature 0.1, timeout 30 seconds, one retry. Streaming (`chat_stream`) is used by `POST /api/assistant/chat/stream`, which sends server-sent events: `meta` (intent, slots, evidence), then text `delta`s, then `done`. On a trivial prompt the hosted `claude-haiku-5-5` endpoint answered in about 0.7 to 0.95 s (`c_llm_smoke.ipynb`, section 1); on real assistant questions the LLM call takes a median 4.6 s (E8). E8 compares the hosted model with local `qwen2.5:7b` (`notebooks/results/e8_model_comparison.csv`; see the E8 section).

### Roles, follow-ups and feedback

- **Role gating.** `plan_summary` and `what_if_budget` are manager-only. A staff user gets "Plan details are only available to managers." and the tool is not run. Plan lines are also removed from the evidence of every other tool for staff (`service.py`), matching the API rule that plan figures are manager-only.
- **Follow-ups.** The browser keeps up to 10 earlier turns and sends them with each question. The server stores no chat. A message with no intent of its own, such as "what about M0002?" or "explain that more simply", continues the previous turn's intent when it names new members or uses a follow-up cue word. Only the last turn counts, and the ids the client sends back are checked against the real roster.
- **Feedback.** `POST /api/assistant/feedback` stores a thumbs up or down with an optional comment and writes an audit entry.

## Message drafts (W22)

`assistant/drafts.py` writes a ready-to-edit message for one member, one allowed offer and one channel (SMS, email, call or in person). **Nothing is sent**: staff copy the text into their own tool.

1. **Guardrails first.** The request goes through the same check as the plan. It is refused if the offer is inactive, not offered on that channel, or blocked for that member by a rule (for example, one contact per 30 days). `c_message_drafts.ipynb` section 2 shows both refusals. The API answers 404, 409 or 422.
2. **Template always works.** A deterministic template uses only facts from the evidence lines: the offer, who it is for, the channel, tenure, and the member's plan signals.
3. **LLM rewrite.** If the LLM is up, it rewrites the same evidence with its own prompt (temperature 0.4). The output is rejected, and the template used instead, if it mentions churn, risk, scores or "leaving"; has a placeholder like `[Name]`; contains a number not in the evidence; lacks an email subject; or exceeds 300 characters for SMS.

Each draft says whether it came from `llm` or `template`. Tests in `tests/test_drafts.py` cover clean LLM text, unsafe output falling back, blocked offers and roles.

## Degradation without Neo4j or the LLM

AGENTS.md requires the pipeline to keep running when either service is down. This is how, and which test covers it.

| If this is down | What still works | What is lost |
|---|---|---|
| Neo4j | Churn scores, rules (from the cached `kg_facts.parquet`), plans, optimiser cohorts, assistant intents `member_risk`, `member_actions`, `compare_members`, `list_members`, `plan_summary`, `what_if_budget`, message drafts | Graph explorer and simulation return 503 "Knowledge graph unavailable". `graph_impact` answers "The knowledge graph is unavailable right now." Edits are saved but the graph stays stale until `kg load` or `POST /api/admin/kg/reload` |
| Neo4j, never loaded | Rule base runs with no KG facts (`build_facts` joins them only when the file exists and is newer than the last data build) | The KG facts (lost instructor, cancelled class) are absent from the rule facts (`reasoning/facts.py` joins them only when given) |
| LLM | Intent, slots and tools are unaffected. The reply is the evidence lines, each ending in its `[E#]`, joined as a bullet list (`service._template`); `llm_used` is false | No natural phrasing. A follow-up that only the LLM could rephrase gets "I can't answer follow-up questions while the language model is offline." |
| LLM output on drafts | The deterministic template | Natural wording |
| Embedding model not downloaded | Rest of the API | The assistant returns 503 "Intent model unavailable" |

The fallback is the same evidence the LLM would have used, so a fallback answer is still grounded and cited. Tests: `tests/test_knowledge.py::test_ego_endpoint_degrades_when_graph_is_down`, `tests/test_kg_reload.py::test_sync_graph_marks_stale_instead_of_raising`, `tests/test_assistant.py::test_answer_is_grounded_and_degrades`. Tests mock the LLM and Neo4j, as AGENTS.md requires.

## Experiments

E7 (does the KG help the rules?) and E8 (assistant: intent accuracy, faithfulness, latency, model comparison) are reported in the experiments section (`c-experiments-e6-e8.md`). Their notebooks are `c_e7_kg.ipynb` and `c_e8_assistant.ipynb`, with results in `SystemCode/notebooks/results/e7_*.csv` and `e8_*.csv`.
