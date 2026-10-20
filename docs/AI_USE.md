# AI tool use log

Feeds the report's AI-use appendix. One row per meaningful use.

| Date | Member | Tool | Used for | What we changed / verified |
|---|---|---|---|---|
| 2026-10-13 | Abdulaziz | Claude Code | Course review, project plan, repo scaffold | Reviewed plan with team; adjusted scope |
| 2026-10-15 | Abdulaziz | Claude Code | SQLite app DB, Alembic migrations, seeds, auth | Reviewed and tested |
| 2026-10-16 | Mokdy | Claude Code | Stream A data-table contract, fixture and scenario v0 build | Reviewed; verify on real Kaggle CSV |
| 2026-10-16 | Mokdy | Claude Code | Stream A A2–A8: features, segmentation, churn model, scenario v1, T-learner, notebooks E1/E2, member/admin APIs, web shell and pages, docs | Reviewed results against notebooks; re-measured reported numbers |
| 2026-10-16 | Abdulaziz | Claude Code | Rule engine seeds, knowledge graph setup | Tested; thresholds pending |
| 2026-10-16 | Abdulaziz | Claude Code | WebUI redesign | Reviewed screenshots; reviewed for regressions |
| 2026-10-16 | Abdulaziz | Claude Code | Assistant chat | Reviewed and tested |
| 2026-10-16 | Abdulaziz | Claude Code | Simulated manager interviews | Chose thresholds from interview and data checks; reviewed |
| 2026-10-17 | Mokdy | Claude Code | Stream A handoffs #1–#5, #16, #18, #20: gym-event ground truth (`true_churn`), out-of-fold churn scores, signed `visit_change`, zero-visit attendance fix, phone check-ins; cross-stream review of C1–C5 (three AI review agents, each finding re-run or traced before filing); drafts of the Stream A report sections and user-guide pages | Re-measured every reported number against `notebooks/results/` and the model card (table cross-check script); mutation-tested the new regression tests; ran each commit's tests in isolation; browser check in both themes for all three roles; fresh-clone install test. Report and user-guide text is an AI draft for Mokdy to review and edit before submission |
| 2026-10-17 | Abdulaziz | Claude Code | Review finding fixes | Reviewed and tested |
| 2026-10-17 | Abdulaziz | Claude Code | Graph explorer class/instructor search + E8 prompt variant | Reviewed, queries checked on live graph |
| 2026-10-19 | Asiri | Claude Code | Stream B handoff review: #6, #12, #13, #17, #26 replies and the #30 finding (override check misses no-phone members) | Each reply checked against the running API and the rule engine; candidate-set decision mine |
| 2026-10-19 | Asiri | Claude Code | B1/B5 plan model notebook: options, objective, feasibility check, policy evaluator, baselines, first E4 grid; moved into `anchorai.optimisation` with feasibility and evaluator tests | Ran every cell and checked the outputs; tests checked by removing each limit check in turn; decisions (H = 6, baseline offer, E4 axes) mine |
| 2026-10-20 | Asiri | Claude Code | Stream B walking skeleton: POST /api/plan saving plans to SQLite, and a bare Plan builder page | Checked end to end in the browser; tests for roles, feasibility and audit |
| 2026-10-20 | Asiri | Claude Code | CBR uplift reasoner (B4) and E3: b_cbr notebook, three pre-registered variants, null test, plan quality vs T-learner | Ran the notebook; caught a flawed first version with the null test; decided to keep CBR per PLAN and flag the T-learner question to the team (HANDOFFS #33) |
| 2026-10-20 | Asiri | Claude Code | Genetic algorithm planner (B2) with spillover and diminishing returns, and E4 on CBR, T-learner and perfect-knowledge estimates | Ran the notebook; chose the spillover design (#7); reported the optimiser's-curse finding honestly |
| 2026-10-20 | Asiri | Claude Code | CP-SAT exact planner (B3), random-instance generator (B1) and E5: optimality gap, speed, seeds, sensitivity, ablations | Ran the notebook; package results checked identical to the notebook's |
| 2026-10-20 | Asiri | Claude Code | Stream B backend (B6): explanations, overrides with live rule checks, approval, assignment and call sheets, my contacts, outcome logging with CBR retain, background jobs, re-optimise, saved scenarios, health checks | Tests for each rule, several checked by breaking the rule on purpose; reviewed each change |
| 2026-10-20 | Asiri | Claude Code | Stream B pages (W14–W17, W20, W21, W45) and the demo seed layer (#8) | Tested every page in the browser by role, at tablet and phone sizes and in both themes; checked A's dashboard and C's assistant read the demo week |
