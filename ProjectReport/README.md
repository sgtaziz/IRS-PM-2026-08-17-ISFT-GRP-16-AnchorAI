# Project report

Final file: `IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-Group-Report.pdf`, built from the LaTeX source in `latex/`:

```sh
cd ProjectReport/latex && ./build.sh        # full report (main.tex); ./build.sh main-short for the 20-page short version (main-short.pdf). LuaLaTeX + biber; needs TeX Live (texlive-luatex, -latexextra, -fontsextra, -pictures, -mathscience, -bibtexextra) and biber
cd SystemCode/backend && uv run python ../../ProjectReport/latex/scripts/figures.py   # regenerate the member-level figures after `anchorai setup`
python3 ProjectReport/latex/scripts/ai_use_table.py                                  # refresh the AI-use appendix from docs/AI_USE.md
```

`main-short.pdf` is a 20-page short version in the same style, with every required appendix in compact form. Both reports end with one page per member: their reflection (`latex/appendices/reflection-<name>.tex`) and peer review (`peer-review-<name>.tex`, else a blank form prints). The LaTeX source is now the report. The Markdown sections below are the streams' drafts it was condensed from.

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
