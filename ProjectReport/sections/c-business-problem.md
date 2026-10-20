# Business problem and market research

*Stream C. Sources: `Miscellaneous/Gate0_AnchorAI_Project_Proposal.docx` (11 Sep 2026), `Miscellaneous/AnchorAI — Project.pptx` (27 Sep 2026), `docs/PLAN.md` §4 (drift log), `Miscellaneous/interviews/`, `docs/AI_USE.md`.*

## Target user

AnchorAI is framed for a **mid-market gym operator**, a business with one to five clubs. The users are club managers, front-desk staff and trainers. No real operator was involved: we had no operator's data, and the manager interviews described below were simulated. Aramco, named in the proposal, sponsors the team's studies; it is not a client or data provider for this project and has not reviewed the system (PLAN.md drift item 13).

## Business problem

Members who stop attending cancel weeks or months later. That lag is the window AnchorAI targets. Each lost member takes dues and ancillary spend with them. The scale of the problem:

- **About one member in three leaves each year.** The Health & Fitness Association's *2025 Fitness Industry Benchmarking Report* puts the median member retention rate at 66.4% in 2024, from 175 companies running more than 17,000 facilities in 27 countries [1].
- **New members are the most fragile.** In a study of one fitness centre's members, 63% stopped before their third month and fewer than 4% stayed continuously active beyond twelve months [2]. It is a single facility, so it shows the shape of early attrition rather than an industry rate. Our data agrees: the Kaggle members in the "New and slipping" segment, under a month into membership on average, churn at 94.6% (`ProjectReport/sections/a-knowledge-discovery.md`).

The proposal and deck quoted "1 in 2 new joiners leave within six months"; we could not trace that figure to a primary source, so this report uses [2] instead.

The proposal says current practice fails in three ways:

| Practice | Why it fails |
|---|---|
| Calendar campaigns | Contact everyone on a schedule, so budget goes to members who would have stayed anyway. |
| Threshold rules | Ignore trend. Twelve visits a month falling to four is a stronger warning than a steady two, but a threshold treats them alike. |
| Vendor risk scores | Give a number, not a decision. Staff cannot interrogate the flag, so they ignore it. |

AnchorAI answers with one weekly decision: segment members, predict who will leave, and produce a contact list within budget and staff hours, where each recommendation carries a reason (rule trace, similar past cases, graph signals). The Kaggle data shows the trend signal on real members: the median ratio of this month's to lifetime visits is 0.69 for members who left and 1.00 for those who stayed (`ProjectReport/sections/a-data-preparation.md`, `SystemCode/notebooks/figures/a2_trend_ratio.png`).

## Market research

The proposal's market analysis is desk research from vendor documentation and buyer guides. We did not run a survey, and we have no pricing figures of our own.

**Market growth.** The *2025 HFA Global Report* finds that in 2024 health-club memberships rose 6% year on year, revenue rose 8% on average and the number of facilities grew nearly 4% [3]; it gives no absolute market size, and we do not quote one. More members and more facilities mean more members to keep, and the retention rate in [1] says a third of them leave each year.

**Landscape (from the proposal).**

- *System of record* (membership, booking, payments, access control): ABC Fitness (including Glofox and Trainerize), Mindbody, Xplor Technologies, Perfect Gym, Virtuagym and Daxko.
- *Intelligence layer* that bolts on to the system of record: Keepme is named as the clearest example. It is known for its predictive Keepme Score, targets multi-site operators and prices by custom quote. Glofox has a built-in "At Risk" churn report. Replify is named as leading AI reception and sales.

**Four gaps (from the proposal).**

1. Competitors score risk but do not publicly expose constrained allocation: which flagged members to contact, with which offer, given a fixed budget and finite staff hours.
2. Vendor messaging centres on targeting high-risk members, but the members most likely to leave are not always the ones a contact keeps. Ascarza showed on field data from a wireless provider and a membership organisation that targeting by expected response to the intervention (lift) reduces churn more than targeting by risk of leaving [4]. AnchorAI plans on estimated uplift for this reason (Stream B's planner, E3 and E4).
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

## References

1. Health & Fitness Association (2025). *2025 Fitness Industry Benchmarking Report*. https://www.healthandfitness.org/2025-fitness-industry-benchmarking-report/
2. Sperandei, S., Vieira, M. C. and Reis, A. C. (2016). Adherence to physical activity in an unsupervised setting: explanatory variables for high attrition rates among fitness center members. *Journal of Science and Medicine in Sport*, 19(11), 916–920. https://doi.org/10.1016/j.jsams.2015.12.522
3. Health & Fitness Association (2025). *2025 Global Fitness Industry Report Shows Record Growth and What's Next for the Market* (summary of the 2025 HFA Global Report), 18 August 2025. https://www.healthandfitness.org/2025-global-fitness-industry-report-shows-record-growth-and-whats-next-for-the-market/
4. Ascarza, E. (2018). Retention futility: targeting high-risk customers might be ineffective. *Journal of Marketing Research*, 55(1), 80–98.
