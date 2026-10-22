# Project report

Final file: `IRS-PM-<date>-<batch>-GRP-<team>-AnchorAI-Group-Report.pdf`

| Section | Owner | Source |
|---|---|---|
| Executive summary | all (last) | |
| Business problem and market research | C | `sections/c-business-problem.md` |
| Project objectives and success measures | B | `sections/b-objectives.md` |
| Data collection and preparation, scenario layer | A | `sections/a-data-preparation.md` |
| System design and architecture | B | `sections/b-architecture.md` (figures in `figures/`) |
| Knowledge discovery: segmentation, churn, uplift baseline | A | `sections/a-knowledge-discovery.md` |
| Implementation: data pipeline, member pages and testing | A | `sections/a-implementation.md` |
| Decision automation: rules, knowledge acquisition | C | `sections/c-decision-automation.md` |
| Optimisation: CBR, GA, CP-SAT | B | `sections/b-optimisation.md` |
| Cognitive: knowledge graph, assistant | C | `sections/c-cognitive.md` |
| Experiments E1–E8 and findings | A, B, C (own experiments) | `sections/a-experiments-e1-e2.md`, `sections/b-experiments-e3-e5.md`, `sections/c-experiments-e6-e8.md` |
| Conclusions and future work | all | Stream A input: `sections/a-conclusions-input.md` |
| Appendix: proposal | — | `Miscellaneous/Gate0_AnchorAI_Project_Proposal.docx` |
| Appendix: mapping to MR / RS / CGS | C (from docs/PLAN.md §3) | `sections/c-appendix-technique-mapping.md` |
| Appendix: installation guide | A | `installation-guide.md` |
| Appendix: user guide | C | `user-guide.md` |
| Appendix: scenario layer parameters | A | `sections/a-appendix-scenario-layer.md` |
| Appendix: AI-use note | all (from docs/AI_USE.md) | `docs/AI_USE.md` |
| Appendix: individual reflections | each member | |

Section sources live next to this file in `sections/`, named by stream (`a-*.md`, `b-*.md`, `c-*.md`). Figures are embedded with paths relative to `sections/` (`../../SystemCode/notebooks/figures/…`), so convert from that folder or pass it as the resource path, for example `pandoc --resource-path=ProjectReport/sections …`.
