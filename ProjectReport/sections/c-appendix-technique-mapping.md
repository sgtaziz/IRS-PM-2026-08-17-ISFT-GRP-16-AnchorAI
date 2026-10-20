# Appendix: mapping to MR / RS / CGS

*Stream C. Draft table from `docs/PLAN.md` §3, checked against the code in `SystemCode/backend/anchorai/` and the notebooks in `SystemCode/notebooks/`. MR = Machine Reasoning, RS = Reasoning Systems, CGS = Cognitive Systems; D = course day.*

All four technique groups required by the module are covered: decision automation, resource optimisation, knowledge discovery and cognitive. "Built" means the code exists and a notebook result or test supports it.

## Mapping

| Component | Technique (as built) | Course / day | Module | Experiment / notebook | Status |
|---|---|---|---|---|---|
| Data prep | Stratified 80/20 split; SMOTE-NC inside CV folds only, compared with class weights; CRISP-DM | RS D2 | `scenario/`, `discovery/churn.py` (`SMOTENC`) | E2: `a_churn.ipynb`, `results/e2_resampling_cv.csv` | Built |
| Features | Trend and ratio features (`trend_ratio`, `visit_change`, `contract_progress`, `charges_per_month`), scaling, leakage check | MR D4, RS D2 | `features/` | `a_features_leakage.ipynb`, `results/a_leakage.csv` | Built |
| Segmentation | K-means, silhouette, stability (ARI), cluster profiles | MR D4 | `discovery/segments.py` | E1: `a_segmentation.ipynb` | Built (k = 4) |
| Churn model | Class-weighted logistic regression plus LightGBM ensemble, Platt calibration, CV; F1, PR-AUC, Brier | MR D2, MR D4 | `discovery/churn.py` | E2: `a_churn.ipynb` | Built |
| Driver explanations | Per-member contributions from the logistic regression and LightGBM (`pred_contrib`) averaged | MR D3, MR D4 | `discovery/churn.py` | E2: `figures/e2_shap.png` | Built; see deviations |
| Scenario layer | Synthetic clubs, classes, instructors, offers and intervention history with known effects | MR D3 | `scenario/build.py` | `a_scenario_uplift.ipynb` | Built |
| Uplift baseline | T-learner (logistic regression plus LightGBM per arm) | MR D4 (self-research) | `discovery/uplift.py` | E3: `a_scenario_uplift.ipynb`, `b_cbr.ipynb` | Built |
| Offer reasoner | Case-based reasoning: retrieve (kNN), reuse (uplift from similar treated vs untreated), retain (new cases added) | MR D2 | `cbr/reasoner.py` | E3: `b_cbr.ipynb` | Built |
| Plan optimiser | Genetic algorithm with DEAP; tournament selection, repair, penalties, elitism; spillover and diminishing returns | RS D4 | `optimisation/ga.py` | E4: `b_ga.ipynb`; E5: `b_exact.ipynb` | Built |
| Exact benchmark | CP-SAT constraint optimisation (OR-Tools) | MR D1, RS D1 | `optimisation/exact.py` | E5: `b_exact.ipynb` | Built |
| Policy evaluation | Simulation-based comparison against contact-all, risk-top-k and greedy-uplift baselines | RS D1 | `optimisation/evaluate.py`, `baselines.py` | E4: `b_plan_model.ipynb`, `results/b5_e4_baselines.csv` | Built |
| Rule engine | Forward chaining over derive, playbook and guardrail YAML rules; salience conflict resolution; traced explanations; versioned rules | MR D2, RS D1 | `reasoning/engine.py`, `reasoning/rules/` | E6: `c_e6_rules.ipynb`, `c_rules.ipynb` | Built |
| Knowledge graph | Neo4j and Cypher: member, class, instructor, event nodes; multi-hop cohort signals (lost instructor, cancelled class); read-only parameterised queries | MR D3, RS D5 | `knowledge/` (`queries.py`, `loader.py`, `signals.py`) | E7: `c_e7_kg.ipynb`, `c_kg.ipynb` | Built |
| Intent detection | Embedding similarity to labelled examples (sentence-transformers, `all-MiniLM-L6-v2`), threshold for "unknown"; slot filling | CGS D1 | `assistant/classifier.py`, `slots.py`, `intents.yaml` | E8: `c_intent_classifier.ipynb`, `c_e8_assistant.ipynb` | Built |
| Grounded generation | Deterministic tool call, then an LLM phrases the answer from tool output only; OpenAI-compatible client | CGS D1, CGS D3 | `assistant/tools.py`, `prompt.py`, `llm.py` | E8: `c_e8_assistant.ipynb`, `c_llm_smoke.ipynb` | Built |
| Evaluation of the assistant | Intent accuracy against a keyword router; static checks; LLM-as-judge faithfulness, calibrated against known sentences; latency of a hosted model vs local `qwen2.5:7b` | CGS D2, CGS D3 | `c_e8_assistant.ipynb` | E8: `results/e8_*.csv` | Built |
| Message drafts | LLM-written member messages from the plan and rule trace | CGS D1 | `assistant/drafts.py` | `c_message_drafts.ipynb` | Built |
| Overall | Hybrid ML, rules, optimisation, knowledge graph and natural-language interface, with human review (override, approve) | RS D1, CGS D1 PM | `api/`, `pipeline.py` | E4, E6, E7 | Built |

## Deviations from the proposal

The proposal and deck differ from what was built in these ways (`docs/PLAN.md` §4):

| Proposal or deck | Built | Reason |
|---|---|---|
| ANN picks who to contact (deck) | GA, with CP-SAT as exact benchmark | An ANN is a learning model, not an optimiser, and cannot enforce budget or staff limits (item 1) |
| Agent-based longitudinal simulator | Real Kaggle data plus a thin scenario layer | Lower risk; keeps the real-data story (item 2) |
| SMOTE to 50/50 | SMOTE-NC in folds, Platt calibration, class weights chosen | SMOTE inflates probabilities the optimiser consumes (item 3) |
| F1 and silhouette as the metrics | F1 plus PR-AUC, Brier, calibration, fairness gaps | The plan consumes probabilities (items 4, 15) |
| Fuzzy inference for engagement tiers | Not built | Not taught in MR, RS or CGS (item 6) |
| K-means and Gaussian mixture | K-means only | Matches the deck and MR D4 (item 7) |
| CBR and uplift as separate components | CBR is the uplift estimator; T-learner is the E3 baseline | Both estimate the same quantity (item 8) |
| Class recommendations | Not built | Stretch item; no recommender in the code (item 10) |
| Decision-tree surrogate rules (PLAN §3) | Not built | No surrogate tree in the code or notebooks |
| KG embeddings (PyKEEN) | Not built | Stretch item (PLAN risks table) |
| Censoring of active members | Dropped | Single snapshot with a binary label (item 12) |
| Interviews with managers | Simulated by an AI model | No real operator was reached; see the business-problem section |
| Assistant answers staff questions grounded on rule trace and graph | Intent router before the LLM; native tool calling not the default | Small local models are unreliable at tool calling (item 14) |
