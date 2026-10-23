# AnchorAI System Design Video Script

> **Draft for the speakers.** Put each line into your own words while recording. Keep the facts and numbers, and keep the honest caveats.

System design video for AnchorAI. Covers the high level system design and a technical explanation of the use cases, including where results were mixed. Facts come only from the submitted report (`ProjectReport/latex/main.tex`), `chapters/03-architecture.tex` and `SystemCode/notebooks/results/`. Narration avoids semicolons, colons and dashes so it is easy to read aloud.

**Total target time: 5:00.** Three sections of about 1:40 each. Narration totals 711 words, about 4:54 at 145 words per minute, and about 4:44 at 150 words per minute. Rehearse at a brisk, natural pace and, if the take runs over 5:00, drop a clause from the longest beat rather than speeding up.

| Section | Speaker | Time range | Words | Estimated speaking time |
|---|---|---|---|---|
| 1 | Binmaneea Khalid Waleed M (member intelligence) | 0:00 to 1:40 | 236 | about 1:38 |
| 2 | Asiri Mohammed Yahya A (decision and optimisation) | 1:40 to 3:20 | 240 | about 1:39 |
| 3 | Abdulaziz Ali S Hasanain (knowledge and interaction) | 3:20 to 5:00 | 235 | about 1:37 |
| Total | | 0:00 to 5:00 | 711 | about 4:54 |


## Section 1. Binmaneea Khalid Waleed M, member intelligence (0:00 to 1:40)

### T1.1  (about 0:00, 10 s, 24 words)

**On screen:** Black frame, the AnchorAI logo (ProjectReport/latex/figures/logo-light.pdf) fades in and a lower third slides in bottom left, "Binmaneea Khalid Waleed M, member intelligence". Title text types on, "System design". Three small circles labelled with the three part names drift in and orbit the logo.

**Say:** Hi, I'm Binmaneea. This is the system design of AnchorAI, an explainable, budget aware gym retention planner. Each of us built one reasoning part.

### T1.2  (about 0:10, 13 s, 32 words)

**On screen:** Show ProjectReport/latex/figures/diagrams/architecture.pdf redrawn full screen on dark. Layers build from top to bottom, with one line of tech in each. "Vue 3 web app", "FastAPI service", three reasoning boxes, and four stores "data tables", "SQLite", "Neo4j", "LLM via OpenAI compatible endpoint". Arrows animate along the data flow, and the dashed learning loop pulses last.

**Say:** One Vue 3 web app serves three roles. One FastAPI service checks every role, audits every change, and runs background jobs. State sits in SQLite, Neo4j, and any OpenAI compatible language model.

### T1.3  (about 0:23, 15 s, 36 words)

**On screen:** Three contract cards slide between the reasoning boxes, "Data tables", "Allowed offer list", "Explanation record". For the third, a plan item splits into four chips, "drivers", "rule trace", "graph signals", "10 similar cases", with two arrows to "Why panel" and "Assistant".

**Say:** Three contracts connect the parts. Data tables written once. An allowed offer list, so the optimiser never sees a blocked offer. And an explanation record per plan item, read by the why panel and the assistant.

### T1.4  (about 0:38, 13 s, 31 words)

**On screen:** Table style build. A Kaggle badge appears with "4,000 real members, 14 columns, 26.5% churners, split 3,200 and 800". Beneath it a second layer stacks on labelled "scenario layer, synthetic" with counters "3 clubs, 9 instructors, 18 classes", "16,000 member offer pairs, true uplift", "2,400 randomised past contacts". A lock icon marks the ground truth "used only to grade".

**Say:** I start with 4,000 real members from a public Kaggle dataset. It has no clubs or offers, so I added a scenario layer with known true effects, used only to grade.

### T1.5  (about 0:51, 15 s, 37 words)

**On screen:** Show the E1 chart. Left, a silhouette line over k from 2 to 10 with a dashed orange line landing on k = 4. Right, four horizontal bars grow for the segments, 94.6%, 17.4%, 12.6%, 1.4%, with a counter "adjusted Rand index 1.00" below. Optionally overlay ProjectReport/latex/figures/screens/segments-content.png as a small inset.

**Say:** Segmentation is K means on 7 behaviour features. A fixed rule on the silhouette picks 4 segments, stable at 1.00 across seeds. Churn runs from 94.6 percent in the worst segment to 1.4 percent in the best.

### T1.6  (about 1:06, 12 s, 29 words)

**On screen:** The churn pipeline from the report animates left to right. "17 features" splits into "logistic regression" and "LightGBM", merges as "mean", passes through "Platt calibration" and ends in "risk band" and "five drivers". Beside it, ProjectReport/latex/figures/generated/shap.pdf fades in as a small inset.

**Say:** Churn is the mean of a logistic regression and LightGBM over 17 features, then Platt calibrated, because the planner multiplies them by uplift. SHAP gives each member's 5 drivers.

### T1.7  (about 1:18, 19 s, 47 words)

**On screen:** Results table counts up on screen, three rows. "AnchorAI ensemble F1 0.908, PR AUC 0.973, Brier 0.035", "Logistic regression 0.862, 0.953, 0.056", "Visit rule 0.549, 0.390, 0.336". Then two amber callouts slide in, "without 5 suspect columns, F1 0.817" and "recall 0.522 for ages 31+".

**Say:** On 800 unseen members, F1 is 0.908, against 0.862 for logistic regression and 0.549 for a visit rule. Two same month columns may leak the label. Without them F1 is 0.817, the honest lower bound. Recall is only 0.522 for members aged 31 and over. Now Asiri.

*Section 1 word count: 236, about 1:38 at 145 words per minute.*


## Section 2. Asiri Mohammed Yahya A, decision and optimisation (1:40 to 3:20)

### T2.1  (about 1:40, 12 s, 29 words)

**On screen:** Lower third, "Asiri Mohammed Yahya A, decision and optimisation". An equation builds on screen in large type, "value = uplift x monthly fee x 6 months, minus offer cost", each term highlighting as it is spoken.

**Say:** I'm Asiri. I built decision and optimisation. Each offer for each member is valued as estimated uplift, times monthly fee over a cautious 6 months, minus the offer's cost.

### T2.2  (about 1:52, 16 s, 39 words)

**On screen:** The case based reasoning cycle from ProjectReport/latex/figures/diagrams/cbr-cycle.tex redrawn as four steps in a circle, "Retrieve 200 nearest", "Reuse as a local A/B test", "Revise by shrinkage", "Retain as evidence only". The last step has a small barrier icon between it and the averages.

**Say:** Uplift comes from case based reasoning. Retrieve the 200 nearest cases. Reuse them as an A/B test. Revise by shrinking towards the offer's average. Retain outcomes as evidence only, never in the averages, so the planner cannot bias them.

### T2.3  (about 2:08, 14 s, 34 words)

**On screen:** E3 chart. Grouped bars for Spearman with true uplift, CBR against T learner, for "Free PT 0.64 vs 0.61" and "Discount 0.48 vs 0.27". A flat bar for "Check-in" and "Class pass" carries the label "returns the average". A badge "E3, partly met" appears.

**Say:** Experiment 3. CBR ties the T learner at a Spearman of 0.39, and wins on the two large effect offers. For the small effect offers the noise is larger, so it returns the average.

### T2.4  (about 2:22, 11 s, 26 words)

**On screen:** The planning constraints appear as four filling gauges, "budget", "staff minutes", "trainer minutes", "stock". Two members link with a line labelled "spillover" and a curve labelled "diminishing returns per instructor". The word "non linear" stamps over them.

**Say:** The plan maximises value within the budget, staff minutes, trainer minutes and stock. Spillover and diminishing returns between members who train together make it non linear.

### T2.5  (about 2:33, 19 s, 44 words)

**On screen:** E5 visuals. Left, ProjectReport/latex/figures/generated/ga_convergence.pdf as a line chart climbing from the greedy start. Right, a bar "GA within 0.24% of the optimum" and a timing strip at the same size, "CP-SAT linear 3.8 s" against "GA 33 s for 2,000 members", with the 30 s target tick shown from the start. Badge "E5, partly met".

**Say:** A genetic algorithm searches it. CP SAT is exact on the linear case, 3.8 seconds for 2,000 members, so it wins there. On the full one the genetic algorithm matches the optimum on 8 of 9 small instances, but takes 33 seconds, over target.

### T2.6  (about 2:52, 11 s, 29 words)

**On screen:** E4 chart on estimated effects as the system runs, grouped bars for three staff hour and budget settings, four planners each (contact all, risk top k, greedy, genetic algorithm as the default) with values labelled. A big number counts up, "22% to 138%", and a smaller one, "0 of 198 plans broke a limit".

**Say:** Experiment 4. On estimated effects, the default genetic algorithm keeps 22 to 138 percent more members than contacting by risk or schedule. None of 198 plans broke a limit.

### T2.7  (about 3:02, 15 s, 39 words)

**On screen:** A range chart of GA minus greedy: "true effects known, plus 2.2% to plus 9.2%", "T learner estimates, minus 1.5% to plus 0.4%" and "case based estimates, minus 33.8% to minus 1.0%" in red. The text "optimiser's curse" fades in. A badge "E4, met" and a note "default stays GA, the quick greedy planner is the safer pick on today's estimates".

**Say:** But on noisy estimates the genetic algorithm can lose to greedy, by up to 33.8 percent. That is the optimiser's curse. Estimates limit the planner more than search does, so greedy is the safer pick today. Over to Abdulaziz.

*Section 2 word count: 240, about 1:39 at 145 words per minute.*


## Section 3. Abdulaziz Ali S Hasanain, knowledge and interaction (3:20 to 5:00)

### T3.1  (about 3:20, 14 s, 34 words)

**On screen:** Lower third, "Abdulaziz Ali S Hasanain, knowledge and interaction". Three rule kind columns build, "8 derive", "16 playbooks", "5 guardrails", totalling 29 YAML rules. An arrow runs through the engine and a final "blocks applied after the loop" step in orange sits at the end.

**Say:** I'm Abdulaziz. I built knowledge and interaction. A forward chaining engine runs 29 versioned rules. 8 derive patterns, 16 playbooks propose offers, and 5 guardrails block them. Blocks apply last, so guardrails always win.

### T3.2  (about 3:34, 13 s, 32 words)

**On screen:** Show ProjectReport/latex/figures/screens/rules-test-content.png in a laptop frame, zoom to the validation banner and then the Versions tab. Result chips count up for E6, "0 validator issues", "29 of 29 cases", "31.3% of proposals removed". An amber note reads "no fatigue effect in the scenario".

**Say:** In experiment 6 the validator found no issues, all 29 cases matched, and guardrails removed 31.3 percent of proposals. With no contact fatigue in the scenario, we claim safety, not extra members.

### T3.3  (about 3:47, 13 s, 32 words)

**On screen:** Show ProjectReport/latex/figures/screens/graph-content.png in a laptop frame. A node and edge animation draws member, class, instructor, club, offer and event nodes. A Cypher box shows a template with a parameter placeholder and a "read only" badge. A cache icon feeds the rule engine, with a note "works without Neo4j".

**Say:** A Neo4j graph links members, classes, instructors, clubs, offers and events, through read only Cypher templates. Flags such as an instructor leaving are cached as rule facts, so rules work without Neo4j.

### T3.4  (about 4:01, 17 s, 41 words)

**On screen:** E7 visuals. Left, two bars "hazard x1.80 after instructor leaves" and "x1.32 after class cancelled". Centre, a forest plot with intervals all crossing zero, labelled "no ranking gain". Right, counters "243 low risk members reached" and "plus 7 members at 120 hours, nothing at 36". Badge "E7, partly met".

**Say:** Experiment 7. The flags pick out hazard rises of 1.80 and 1.32 times, but add no reliable ranking gain. They do reach 243 low risk members the score misses, worth about 7 members at 120 staff hours, and nothing at 36.

### T3.5  (about 4:18, 14 s, 33 words)

**On screen:** The assistant pipeline from the report animates as six chips, "question", "intent, threshold 0.35", "slots", "one tool", "numbered evidence", "LLM phrases and cites". The LLM chip is orange with a fence icon and the text "never chooses a tool". Inset ProjectReport/latex/figures/screens/assistant-content.png.

**Say:** The assistant routes a question to one of 7 intents, fills slots, and runs one deterministic tool. The language model only phrases the numbered evidence with citations, or says it does not know.

### T3.6  (about 4:31, 16 s, 38 words)

**On screen:** E8 results. A bar fills to 96.2% "80 judged sentences supported, none contradicted", then two bars "local 7B 95.1%" and "hosted 95.1%". Then a table builds, "AI written questions, 62, classifier 91.9, keywords 77.4" and "held out, 24, classifier 50.0, keywords 54.2" with the second row in red. Badge "E8, partly met".

**Say:** Experiment 8. 96.2 percent of 80 judged sentences were supported and none contradicted. A local 7B model matched the hosted one. Routing is weak. On 24 held out questions the classifier scored 50 percent against 54.2 for keywords.

### T3.7  (about 4:47, 10 s, 25 words)

**On screen:** A switchboard graphic with two toggles, "Neo4j" and "LLM", switched off one at a time. With each off, a green "Planner still runs" tag stays lit and a note appears, "rules use cached graph facts" and "assistant returns cited evidence". Then "195 offline tests" counts up, and the logo returns with "Thanks for watching", the three names and the line "NUS-ISS Intelligent Reasoning Systems, Group 16".

**Say:** Without Neo4j, the rules use cached graph facts. Without the language model, the assistant returns the cited evidence. The planner needs neither. Thanks for watching.

*Section 3 word count: 235, about 1:37 at 145 words per minute.*


## Fact sheet

Every number spoken or shown in this video, with where it comes from. Paths are relative to the repository root.

| Fact | Source |
|---|---|
| Vue 3 + TypeScript web app; FastAPI service (role check every request, audit, background jobs); SQLite via SQLModel; Neo4j 5; OpenAI compatible LLM client | ProjectReport/latex/main.tex section 2 (System design); chapters/03-architecture.tex Table technology |
| 3 contracts: data tables, allowed offer list, explanation record (drivers, rule trace, graph signals, 10 similar cases) | ProjectReport/latex/main.tex System design |
| 4,000 real members, 14 columns, 26.5% churners, 3,200/800 split; 4 derived features | ProjectReport/latex/main.tex Data and the scenario layer |
| Scenario layer: 3 clubs, 9 instructors, 18 classes, 4 offers, 16,000 member-offer pairs with true uplift (mean +5.8 points), 2,400 randomised past contacts; truth used only to grade | ProjectReport/latex/main.tex Data and the scenario layer |
| K-means on 7 behavioural features; k = 4 by silhouette rule; ARI 1.00 (min 0.998); churn 94.6% to 1.4% | ProjectReport/latex/main.tex Methods and E1; SystemCode/notebooks/results/e1_segment_profiles.csv |
| Churn: mean of class-weighted logistic regression and LightGBM, 17 features, Platt calibration, 5 drivers (LR + TreeSHAP) | ProjectReport/latex/main.tex Methods, Member intelligence |
| Test (800 members): ensemble F1 0.908, PR-AUC 0.973, Brier 0.035; logistic 0.862 / 0.953 / 0.056; visit rule 0.549 / 0.390 / 0.336 | ProjectReport/latex/main.tex E2 Table; SystemCode/notebooks/results/e2_model_vs_baselines.csv |
| Without the five suspect same-month columns F1 0.817; recall 0.522 for ages 31+ | ProjectReport/latex/main.tex E2 Table and results; SystemCode/notebooks/results/a_leakage.csv |
| Value = uplift x monthly fee x 6 month horizon minus offer cost | ProjectReport/latex/main.tex Methods, Decision and optimisation |
| CBR: 200 nearest cases, shrinkage (empirical Bayes), retain as evidence not in averages; null test with shuffled offers | ProjectReport/latex/main.tex Methods, Decision and optimisation |
| E3: Spearman 0.39 for CBR and T learner; Free PT 0.64 vs 0.61; discount 0.48 vs 0.27; verdict partly | ProjectReport/latex/main.tex E3; SystemCode/notebooks/results/e3_uplift_vs_truth.csv |
| Plan limits: budget, staff minutes, trainer minutes, stock; spillover and diminishing returns make it non linear | ProjectReport/latex/main.tex Methods, Decision and optimisation |
| E5: CP SAT linear 3.8 s at 2,000 members (e5_speed.csv; 1.2 to 1.4 s on the full gym linear gap runs); GA within 0.24% at 50 members; matches proven optimum on 8 of 9 instances of 20 to 40 members; 18 s for 1,000 and 33 s for 2,000 members; missed the 30 s target by about 10%; verdict partly | ProjectReport/latex/main.tex E5; SystemCode/notebooks/results/e5_speed.csv |
| E4: default GA on CBR estimates keeps 22% to 138% more members than risk or schedule (36 h and US$1,500: 16.7 against 13.7 risk, 21.0 greedy; 72 h: 35.5, 21.0, 36.6; 120 h and US$4,000: 48.1, 21.4, 51.9, contact all 20.2; results/e4_estimates.csv); 0 of 198 plans infeasible; GA vs greedy +2.2% to +9.2% with perfect knowledge, -1.5% to +0.4% on T learner, -33.8% to -1.0% on CBR (optimiser's curse); greedy recommended on today's estimates; verdict met | ProjectReport/latex/main.tex E4 and recommendations; SystemCode/notebooks/results/e4_optimiser.csv |
| Rule engine: 29 YAML rules = 8 derive, 16 playbooks, 5 guardrails; blocks applied after the loop; edit, test, version, roll back | ProjectReport/latex/main.tex Methods, Decision automation |
| E6: 0 validator issues; 29 of 29 cases; guardrails remove 31.3% of 3,448 proposals; no fatigue effect in scenario so no retention claim | ProjectReport/latex/main.tex E6; SystemCode/notebooks/results/e6_guardrail_bites.csv |
| Knowledge graph: Neo4j, read only parameterised Cypher, flags cached as rule facts, works without Neo4j | ProjectReport/latex/main.tex Methods, Knowledge graph and staff assistant |
| E7: hazard x1.80 after anchor instructor leaves, x1.32 after class cancelled; no ranking gain (intervals include zero); 243 low risk members reached; about +7 members (+17%) at 120 h, nothing at 36 h; verdict partly | ProjectReport/latex/main.tex E7; SystemCode/notebooks/results/e7_signal_lift.csv |
| Assistant: 7 intents via sentence embedding centroids, unknown threshold 0.35, one deterministic tool, LLM only phrases numbered evidence with citations | ProjectReport/latex/main.tex Methods and Figure assistantpipe |
| E8: 96.2% of 80 judged sentences supported, none contradicted; local qwen2.5:7b and hosted model both 95.1%; intent accuracy AI-written (62) 91.9% vs keywords 77.4%; held out (24) 50.0% vs 54.2%; verdict partly | ProjectReport/latex/main.tex E8 |
| Graceful degradation: without Neo4j rules use cached graph facts; without LLM assistant returns cited evidence; planner needs neither; 195 offline tests | ProjectReport/latex/main.tex System design principles, Implementation |
