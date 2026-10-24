# Implementation: data pipeline, member pages and testing

*Backend code in `SystemCode/backend/anchorai/` (`pipeline.py`, `scenario/`, `features/`, `discovery/`, `catalog.py`, `api/routers/members.py`, `admin_data.py`, `admin_offers.py`); web pages in `SystemCode/frontend/src/`. How to use each page is in the user guide.*

This section covers how the member-intelligence results reach the application: the build that produces them, the API that serves them, the pages that show them, and how they are tested.

## From raw CSV to served scores

`uv run anchorai data build` runs `anchorai/pipeline.py`. It takes about 20 seconds.

1. Read the one Kaggle CSV in `SystemCode/data/raw/`. Fail with the download link if there is none, or more than one.
2. Build the data tables and the scenario layer (`scenario/build.py`), check them against the contract (`scenario/tables.py`) and write them as parquet.
3. Build the 17 features (`features/`).
4. Fit the segmentation (`discovery/segments.py`), the churn model with out-of-fold training scores (`discovery/churn.py`) and the T-learner (`discovery/uplift.py`).
5. Write `features`, `segments`, `member_scores` and `uplift_tlearner`, then `model_card.json` with every metric, then the fitted models.

`anchorai setup` runs this build, resets the app database and loads the knowledge graph: one command from a fresh clone to a working demo.

**Serving.** `discovery/service.py` loads the build output once and keeps it in memory. Each request checks the modification time of `model_card.json`, so a rebuild takes effect on the next request without restarting the API. If nothing has been built, every member endpoint returns HTTP 503 with "Data tables are not built yet. Run `uv run anchorai data build`", and the pages show that message in their error state.

**Rebuilding from the app.** An admin can upload a new Kaggle CSV and rebuild with any seed on the Data & models page (W42). The upload must be at most 20 MB, have all 14 Kaggle columns and at least 100 rows; otherwise the current file is kept and the page says why. The rebuild runs in a background thread (`discovery/jobs.py`) while the API keeps serving the old build. The page polls its status (running, done or failed with the error), and a second rebuild while one is running is refused with HTTP 409. After a rebuild the knowledge graph is reloaded through the knowledge graph's `sync_graph`, which never fails the rebuild: if Neo4j is down, the graph is marked stale instead. Upload and rebuild are both written to the audit log, with the row count and the seed.

## API (member-intelligence endpoints)

All endpoints require a signed-in user. Roles are checked on the server by the shared role dependency; the web app's route guards only hide what a role cannot use.

| Endpoint | Roles | Returns |
|---|---|---|
| `GET /api/members` | manager, admin | one page of members (25 by default, up to 200), filtered by segment, risk band, club, tenure range and ID text, sorted by risk, value, tenure, ID, age or visit trend |
| `GET /api/members/export.csv` | manager, admin | every member that matches the same filters, as CSV |
| `GET /api/members/facets` | manager, admin | the clubs and segment names for the filter lists |
| `GET /api/members/search?q=` | any | members whose ID contains the text (10 by default), with their band and probability |
| `GET /api/members/segments` | manager, admin | one card per segment: name, description, size, churn rate, members at high risk, monthly revenue, centre |
| `GET /api/members/dashboard` | manager, admin | KPIs, risk distribution, segment mix and outcomes by week |
| `GET /api/members/{member_id}` | any | Member 360: the `MemberScore`, band, segment, profile against the segment average, classes attended, past retention contacts; 404 for an unknown ID |
| `GET /api/admin/data` | admin | the model card, the build status and the raw file |
| `POST /api/admin/data/upload`, `POST /api/admin/data/rebuild` | admin | replace the CSV; start a rebuild (202) |
| `GET /api/admin/offers` | admin | offer catalogue, staff roster and planning constraints |
| `POST /api/admin/offers/offers`; `PUT`, `DELETE .../offers/{id}`; `PUT .../staff/{user_id}`; `PUT .../constraints` | admin | create, edit and delete offers; set a staff member's weekly hours and skills; set the default budget, staff minutes and contact caps |

Every write records an audit entry with the user, the time and the before and after values (`data.upload`, `data.rebuild`, `offer.create`, `offer.update`, `offer.delete`, `staff.update`, `constraints.update`). Staff can read Member 360 and use the search, which their contact list links to. Everything else that ranks or counts members is limited to managers and admins.

The dashboard combines the churn scores with the planner's tables in the app database. Plan coverage is the share of high-risk members in the latest approved plan. Contacted, reached and retained come from the outcomes staff log, grouped by week. "Reached" counts every outcome except no answer, and "retained" counts accepted offers.

**Seeds.** The catalogue seed rows give a fresh database a working offer catalogue, staff roster and constraints (`catalog.seed`). They are the four scenario offers; staff1 with 20 hours a week (trainer and calls) and staff2 with 16 (calls), 36 staff hours in all; a $1,500 weekly budget; and caps of one contact per member per 30 days and two offers per 90 days. The API container seeds on every start, so offers are seeded only into an empty catalogue; otherwise a restart would bring back an offer an admin had deleted, with no audit entry. A regression test covers this.

## Web pages

The member-intelligence work built the app shell, the shared components and six pages. The app was later restyled the whole app and added the light and dark themes (`a4384fd`, `9792d93`).

| ID | Page | Roles | What it shows |
|---|---|---|---|
| W02 | App shell | all | role-aware sidebar grouped by task; global member search (Ctrl+K or ⌘K; Enter on an exact ID opens the member); toasts and confirmation dialogs; a skip-to-content link; collapsible sidebar on desktop and a menu button on narrow screens |
| W03 | Shared components | — | `KpiTile`, `RiskBadge`, `DataTableX` (sort, filter, CSV export), `ConfirmAction`, `ChartCard` (ECharts), `PageState` (loading, error with retry, empty), `MemberSearch`, and the `useAsync` composable, which drops a response that arrives after a newer request |
| W10 | Dashboard | manager, admin | members at high risk; monthly revenue at risk (the sum of churn probability × monthly fee); plan coverage; contacted, reached and retained in the latest week; risk distribution; segment mix; outcomes by week |
| W11 | Segments | manager, admin | one card per segment with its description, size, churn rate, members at high risk now, monthly revenue and a profile chart against all members; a card opens the member list filtered to it |
| W12 | Members | manager, admin | server-side paged table (25, 50 or 100 rows); filters kept in the page address so a filtered list can be bookmarked; CSV export of every matching member, not just the page |
| W13 | Member 360 | all (staff read-only) | header with risk badge; tiles; "Why this risk score" driver chart; profile against the segment; classes attended; past retention contacts; segment; plus the panels from the other parts of the system listed below |
| W41 | Offers & constraints | admin | offer catalogue (create, edit, deactivate, delete), staff roster (weekly hours and skills), planning constraints (default budget and staff minutes, contact caps) |
| W42 | Data & models | admin | source file and upload; rebuild with a seed; rebuild the knowledge graph; the model card: F1, PR-AUC, Brier, silhouette and fairness gaps, the model against its baselines and against the version without suspect features, calibration and silhouette charts, fairness tables |

**Member 360 brings the whole system together.** Besides the member's scores and profile, it shows the rule trace (with "Draft message" on each allowed offer) and knowledge-graph neighbourhood, and the case-based reasoner's similar past cases and contact and outcome history. A button opens the assistant with the member as context. Each panel calls its own endpoint and has its own loading and error state. If Neo4j or the planner's data are unavailable, only that panel says so and the rest of the page works.

**Usability and accessibility.**
- **Risk** is always shown as text and colour ("High risk · 82%"), never colour alone. A probability is never printed as 0% or 100%; the extremes read "<1%" and ">99%" (`format.probability`), because a model is never certain.
- **States.** Every page has a loading, an empty and an error state, and the error state offers "Try again".
- **Keyboard.** The member search opens from the keyboard, segment cards are focusable and open with Enter, and inputs are labelled.
- **Exports.** Tables export to CSV; the members export runs on the server, so it includes every filtered row.

## Testing

Tests are fast and offline (AGENTS.md). These tests guard against the errors that would quietly invalidate a result rather than crash:

| Test file | Guards against |
|---|---|
| `test_discovery.py` | test labels reaching the churn model: flipping every test label must leave every score unchanged; a training member's score depending on its own label: flipping one label must not change that member's out-of-fold score |
| `test_build.py` | a build that is not deterministic for a seed, or a test split missing one of the classes |
| `test_tables.py` | the fixture drifting from the contract; a dangling foreign key; an attendance row with no visits |
| `test_events.py` | an event's exposure not being the share of visits it hits; members untouched by an event getting riskier; events changing outcomes before the week they happen |
| `test_api_stream_a.py` | broken paging, sorting or filters; a role reaching an endpoint it should not; a 500 instead of a clear 503 when nothing is built; offer writes that are not admin-only or not audited; re-seeding bringing back a deleted offer; deactivated staff staying on the roster |

Beyond the unit tests:
- **Experiments as checks.** The notebooks import from `anchorai` and do not copy its logic. The numbers in this report were re-measured against `notebooks/results/` and the model card. The regression tests added on 17 October were mutation-tested: each fails when the guard it tests is removed (`docs/AI_USE.md`).
- **Installation.** A fresh clone was installed with the installation guide's commands, and the pages were checked in the browser in both themes for all three roles (2026-10-17, `docs/AI_USE.md`).
- **Peer review across the team.** The member-intelligence developer reviewed the authentication, app database, rule engine, rule base and knowledge graph (`docs/reviews/c1-c5.md`). The review filed 32 findings (1 high, 8 medium, 23 low), each reproduced with a script or traced in the code. Three were fixed by the reviewer and the rest by the knowledge-and-interaction developer.
