# Sponsor introduction, business problem and market research

*Stream C. Sources: `Miscellaneous/Gate0_AnchorAI_Project_Proposal.docx` (11 Sep 2026), `Miscellaneous/AnchorAI — Project.pptx` (27 Sep 2026), `docs/PLAN.md` §4 (drift log), `Miscellaneous/interviews/`, `docs/AI_USE.md`.*

## Sponsor

The proposal names Aramco (Dhahran, Kingdom of Saudi Arabia) as sponsor, and the deck repeats it. Aramco sponsors the studies of the team. It is **not** a client or a data provider for this project, and it has not reviewed or validated the system (PLAN.md drift item 13).

The problem is therefore framed for a **mid-market gym operator**, a business with one to five clubs. The target users are club managers, front-desk staff and trainers. No real operator was involved: we had no operator's data, and the manager interviews described below were simulated.

## Business problem

Members who stop attending cancel weeks or months later. That lag is the window AnchorAI targets. Each lost member takes dues and ancillary spend with them. The proposal and deck state two industry figures:

- 1 in 3 members leaves their gym every year.
- 1 in 2 new joiners leaves within six months.

Both figures appear in the proposal and the deck without a per-figure citation. The proposal's source list for the whole market section is: Health and Fitness Association, *2025 Fitness Industry Benchmarking Report*; Keepme and Glofox product documentation; industry buyer guides published in 2026. [TODO: confirm each of the two figures against the HFA report and cite the page or table.]

The proposal says current practice fails in three ways:

| Practice | Why it fails |
|---|---|
| Calendar campaigns | Contact everyone on a schedule, so budget goes to members who would have stayed anyway. |
| Threshold rules | Ignore trend. Twelve visits a month falling to four is a stronger warning than a steady two, but a threshold treats them alike. |
| Vendor risk scores | Give a number, not a decision. Staff cannot interrogate the flag, so they ignore it. |

AnchorAI answers with one weekly decision: segment members, predict who will leave, and produce a contact list within budget and staff hours, where each recommendation carries a reason (rule trace, similar past cases, graph signals). The Kaggle data shows the trend signal on real members: the median ratio of this month's to lifetime visits is 0.69 for members who left and 1.00 for those who stayed (`ProjectReport/sections/a-data-preparation.md`, `SystemCode/notebooks/figures/a2_trend_ratio.png`).

## Market research

The proposal's market analysis is desk research from vendor documentation and buyer guides. We did not run a survey, and we have no market-size or pricing figures of our own. [TODO: market-size figure with citation, if the team wants one; the proposal gives none.]

**Landscape (from the proposal).**

- *System of record* (membership, booking, payments, access control): ABC Fitness (including Glofox and Trainerize), Mindbody, Xplor Technologies, Perfect Gym, Virtuagym and Daxko.
- *Intelligence layer* that bolts on to the system of record: Keepme is named as the clearest example. It is known for its predictive Keepme Score, targets multi-site operators and prices by custom quote. Glofox has a built-in "At Risk" churn report. Replify is named as leading AI reception and sales.

**Four gaps (from the proposal).**

1. Competitors score risk but do not publicly expose constrained allocation: which flagged members to contact, with which offer, given a fixed budget and finite staff hours.
2. Vendor messaging centres on targeting high-risk members, although the proposal cites academic evidence that risk ranking is suboptimal. [TODO: the proposal does not name that evidence; add the citation or drop the claim.]
3. Scores trained on very large member pools are powerful but unauditable, and the proposal says mid-market operators cite staff distrust of black-box flags.
4. The intelligence layer is priced for larger chains. The proposal says Keepme is generally recommended from 5+ locations, which leaves the one-to-five-club operator underserved.

**Position.** AnchorAI is an explainable, budget-aware retention planner for mid-market chains. It differentiates on transparent decision making, not on model accuracy, where incumbents with far larger training data will win (proposal and deck slide 5).

**Limits of this evidence.** The vendor claims come from vendor material and buyer guides, which have a commercial interest. We have not tested any competitor product. Where this report compares AnchorAI with other approaches, the comparison is against baseline policies in our own experiments (E4 and later), not against a vendor.

## Interviews

The plan was to interview club managers or trainers to source the rule base (`Miscellaneous/interviews/interview_script.md`). No real interview took place. On 2026-10-16 an AI model (Claude, via Claude Code) played three personas from a written brief, answering the script without seeing the rule base: an independent owner-manager, a chain area manager and a membership and community lead (`Miscellaneous/interviews/2026-10-16_*_simulated.md`). The use is logged in `docs/AI_USE.md` ("Simulated manager interviews"). Each note carries a banner saying so.

- We treat the answers as plausible expert opinion, not evidence. Rules that changed because of them cite `simulated interview` as their source.
- The simulated answers adjusted some thresholds and offers, for example the discount rule moved to last among offers and the marketing contact cap stayed at once per 30 days (`2026-10-16_owner_simulated.md`).
- Real operator validation is future work (see Conclusions).

## Changes from the proposal that affect the business case

Full list in `docs/PLAN.md` §4. Those that a reader of the business case should know:

- **Optimiser is a genetic algorithm, not an ANN.** The deck says an ANN picks who to contact; the proposal says a GA. We built a GA benchmarked with an exact CP-SAT solver (drift item 1).
- **No longitudinal simulator.** The proposal planned an agent-based simulator. We use the 4,000 real Kaggle members plus a thin synthetic scenario layer (clubs, classes, instructors, offers, past interventions with known effects). Churn and segmentation results are on real data; plan-quality results use the scenario layer and test decision quality against a known ground truth, not real member behaviour (drift item 2).
- **Fuzzy inference and Gaussian-mixture segmentation dropped**; class recommendations are not built (drift items 6, 7, 10).
- **Interviews were simulated** (above), and the censoring step was dropped because the data is a single snapshot (drift item 12).
