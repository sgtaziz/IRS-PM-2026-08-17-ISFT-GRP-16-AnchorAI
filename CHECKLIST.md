# Submission checklist

Due **Sun 25 Oct 2026, 23:59**. Requirements are from the practice module brief (v2.16).

## Group report

- [x] Business case and market research, with pricing and business value (section 1)
- [x] System design, development and implementation
- [x] Experiments E1 to E8, findings and discussion
- [x] Appendix with the project proposal
- [x] Appendix mapping system functions to MR, RS and CGS
- [x] Appendix with the installation and user guide
- [x] Appendix on AI use
- [x] One page of individual reflection per member
  - [x] Abdulaziz (`ProjectReport/latex/appendices/reflection-abdulaziz.tex`)
  - [x] Asiri writes `ProjectReport/latex/appendices/reflection-asiri.tex`
  - [x] Binmaneea writes `ProjectReport/latex/appendices/reflection-khalid.tex`
  - [x] Rebuild both reports once all three are in (`ProjectReport/latex/build.sh main` and `main-full`) and copy the PDFs to `ProjectReport/`
- [x] Report named `IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-Group-Report.pdf`

## Repository

- [x] Runnable system in the IRS-PM template layout
- [x] `member-github.txt` with group name, official names, student IDs and repo link
- [ ] Make the GitHub repo public, or give the graders access (it is private now)
- [x] README section 3, who did what
- [x] README section 3, member emails
- [x] README section 4, the two video links
- [x] Replace `<repo-url>` with the real URL in the README quick start, `ProjectReport/installation-guide.md` and the report's install appendix

## Videos

- [x] Promotion video recorded, edited and uploaded (https://youtu.be/opfahkYKg6U), 4:59
- [x] System design video recorded, edited and uploaded (https://youtu.be/t8pL02oRPBU), 5:13
- [ ] Both MP4 files (`IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-promotion.mp4`, `-system.mp4`, in `Video/editing/`) go into the final zip

## Peer reviews

Each member uploads their own PDF to Canvas, **[Individual] Project Peer Evaluation**. See `ProjectReport/peer-review/template.toml`.

- [x] Abdulaziz built
- [ ] Abdulaziz uploaded
- [ ] Asiri filled in, built and uploaded
- [ ] Binmaneea filled in, built and uploaded

## Final package

The group leader uploads it to Canvas, **[Group Leader] Project Deliverables (zip)**.

- [ ] GitHub repo zip named `IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI.zip`, downloaded after the last push
- [ ] Outer zip with the same name, holding `member-github.txt`, both videos, the repo zip and the report PDF

## Before submitting

- [ ] **Fresh clone test.** Clone the repo into a new folder and follow the README quick start exactly (`.env`, `docker compose up -d neo4j`, `uv sync`, `uv run anchorai setup`, API and web app). Confirm every step works with no files from the working copy, then run `uv run pytest -q` and `npm run build`.
- [ ] **Demo dry run (usability pass).** Each member walks through the weekly workflow in `docs/PLAN.md` §8.2 on another member's pages, starting from a freshly reset database (`uv run anchorai db reset`).
  - Log in as each role (admin, manager, staff1) and check that each one sees only its own pages.
  - Every page loads and handles its empty and error states. Stop Neo4j and the LLM once and check the app still works, with the graph and assistant panels saying they are unavailable.
  - Step 8 in particular. Trigger "Instructor Sam leaves" in the graph explorer, check the affected members appear, re-run the plan and confirm it picks them up. Note how long it takes and what it shows, so the videos can follow the same path.
  - Write down confusing labels, slow pages and wording problems, and fix them before recording the videos.
