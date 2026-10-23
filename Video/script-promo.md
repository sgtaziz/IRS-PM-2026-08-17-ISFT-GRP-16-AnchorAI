# AnchorAI Promotion Video Script

> **Draft for the speakers.** Put each line into your own words while recording. Keep the facts and numbers, and keep the honest caveats.

Promotion video for AnchorAI. Covers business pain and value, a use case demo and pricing. Facts come only from the submitted report (`ProjectReport/latex/main.tex`, `chapters/pricing.tex`), `ProjectReport/user-guide.md`, `docs/PLAN.md` section 8.2 and `SystemCode/notebooks/results/`. Narration avoids semicolons, colons and dashes so it is easy to read aloud. The recurring thread is a generic gym manager's Monday, with no real people or brands in the story.

**Total target time: 5:00.** Three sections of about 1:40 each. Narration totals 699 words, about 4:49 at 145 words per minute, and about 4:40 at 150 words per minute. Rehearse at a brisk, natural pace and, if the take runs over 5:00, drop a clause from the longest beat rather than speeding up.

| Section | Speaker | Time range | Words | Estimated speaking time |
|---|---|---|---|---|
| 1 | Binmaneea Khalid Waleed M (member intelligence) | 0:00 to 1:40 | 233 | about 1:36 |
| 2 | Asiri Mohammed Yahya A (decision and optimisation) | 1:40 to 3:20 | 238 | about 1:38 |
| 3 | Abdulaziz Ali S Hasanain (knowledge and interaction) | 3:20 to 5:00 | 228 | about 1:34 |
| Total | | 0:00 to 5:00 | 699 | about 4:49 |


## Section 1. Binmaneea Khalid Waleed M, member intelligence (0:00 to 1:40)

### P1.1  (about 0:00, 13 s, 31 words)

**On screen:** Black frame. The AnchorAI logo (ProjectReport/latex/figures/logo-light.pdf) fades in centre and settles to the upper left. A lower third slides in bottom left: "Binmaneea Khalid Waleed M, member intelligence". Beneath the logo, the line "An explainable, budget aware retention planner for gyms" types on. Camera bubble stays bottom right, clear.

**Say:** Hi, I'm Binmaneea. With Asiri and Abdulaziz, I built AnchorAI. It tells a gym manager who to contact this week, with which offer, within a fixed budget, and it explains why.

### P1.2  (about 0:13, 12 s, 29 words)

**On screen:** Cut to a calm morning scene drawn as flat illustration, a gym front desk with a laptop and a coffee. A small clock chip reads "Monday, 8:30" and a caption fades in, "A gym manager's Monday". The illustration then dims to the left as a big kinetic number builds on the right, "1 in 3", with the caption "members leave every year".

**Say:** Picture a gym manager on a Monday morning. About one member in three leaves each year. They rarely cancel on impulse. They stop coming first, and cancel weeks later.

### P1.3  (about 0:25, 12 s, 30 words)

**On screen:** Split screen with two counters. Left, a ring chart fills to 66.4% with the label "median member retention, 2024, 175 operators". Right, a progress bar drains to 37% with the label "stopped before their third month, one fitness centre", that is 100 minus 63 drawn as the 63% portion in orange. Both labels carry a small source footnote.

**Say:** The median retention rate was 66.4 percent in 2024, across 175 operators. And new members are the most fragile. In one fitness centre, 63 percent stopped before their third month.

### P1.4  (about 0:37, 12 s, 30 words)

**On screen:** A calendar strip of weeks. A member icon's visit ticks shrink week by week, then a red cancel mark appears several weeks later. A bracket labelled "the window" lights up between the last visit and the cancel. A coin stack animates in below with the text "6 months of fees, about US$324 per lost member" and a small footnote "scenario assumption".

**Say:** That gap is the window where a good contact can still keep them. Each lost member costs the club six months of fees, about 324 US dollars in our scenario.

### P1.5  (about 0:50, 14 s, 33 words)

**On screen:** Three cards slide in from the right and stack, titled "Calendar campaigns", "Threshold rules", "Vendor risk scores". Each flips to show a one line failure from the report, "spend on members who would have stayed", "treat 12 falling to 4 like a steady 2", "a number, not a decision". A bold strike through lands on all three, then the text "A list or a score. Not a decision." fades up.

**Say:** Today's tools give a list or a score. Calendar campaigns spend on members who would have stayed. Threshold rules treat 12 visits falling to 4 like a steady 2. Neither is a decision.

### P1.6  (about 1:03, 14 s, 34 words)

**On screen:** Show the segments app screenshot ProjectReport/latex/figures/screens/segments-content.png in a laptop frame, slow zoom to the four cards. Four cards then pop out on a dark background with churn rates counting up, 94.6%, 17.4%, 12.6%, 1.4%. The first card, "New and slipping, 728 members", glows orange.

**Say:** I started with 4,000 real members from a public dataset, grouped into 4 segments staff can name. One group, new and slipping, is just 728 members, yet holds about two thirds of all churners.

### P1.7  (about 1:17, 19 s, 46 words)

**On screen:** Show ProjectReport/latex/figures/screens/member360-content.png in a laptop frame, pan to the risk badge and the driver bars. A counter overlay reads "193 of 212 leavers caught" and "20 false alarms", with small text "800 members the model never saw". A footnote lists "high band: 93.9% left". Last, a closing chip "misses about half of leavers aged 31+" slides in amber.

**Say:** Then I built a model that predicts who will leave. On 800 members it never saw, it caught 193 of 212 leavers, with 20 false alarms. Every flag shows its top 5 reasons. It misses about half the rare leavers aged 31 and over. Now Asiri.

*Section 1 word count: 233, about 1:36 at 145 words per minute.*


## Section 2. Asiri Mohammed Yahya A, decision and optimisation (1:40 to 3:20)

### P2.1  (about 1:40, 12 s, 28 words)

**On screen:** Back to the illustrated desk, clock chip "Monday, 9:00". Lower third slides in, "Asiri Mohammed Yahya A, decision and optimisation". Cut to ProjectReport/latex/figures/screens/scenarios-content.png in a laptop frame, zoom to the two inputs. Typing animation fills "Budget US$1,500" and "Staff hours 36", then a pulsing "Generate plan" button is clicked.

**Say:** I'm Asiri. I built the part that decides. Back to our manager on Monday. They enter this week's budget, 1,500 dollars, and 36 staff hours, and press generate.

### P2.2  (about 1:52, 13 s, 32 words)

**On screen:** Animated diagram, simplified from ProjectReport/latex/diagrams/weekly-flow.pdf. Four chips light in sequence, "Score members", "Allowed offers", "Estimate effect", "Build plan". Under the third chip, ten small member cards fan out labelled "similar past cases". A budget bar and a staff hours bar fill and stop at their limits.

**Say:** Behind that button, the system finds similar past cases to estimate what each offer would do for each member. Then it picks the best contacts that fit the budget and staff hours.

### P2.3  (about 2:05, 14 s, 34 words)

**On screen:** Show ProjectReport/latex/figures/screens/plan-content.png in a laptop frame, zoom top left to four tiles. The number "182" counts up under "members to contact". Then pan to one row and click "Why". A drawer slides open with drivers, rules that fired and similar members. A small badge reads "about 13 seconds" with a footnote.

**Say:** The plan appears in about 13 seconds in our tests. 182 contacts, each with an offer and a one line reason. Open why on any member to see similar past members and their outcomes.

### P2.4  (about 2:19, 14 s, 33 words)

**On screen:** Same plan screenshot. A row is removed, a reason box types in, and the row flashes green, amber or red in turn as the live rule check runs. Then an "Approve plan" button is pressed, a padlock closes, and member icons fly out to three staff avatars of different sizes, bigger avatars getting more.

**Say:** Our manager can remove, add or swap a contact. Each change needs a reason, and the rules check it at once. Then they approve. Calls are shared out by free hours and skills.

### P2.5  (about 2:33, 13 s, 31 words)

**On screen:** Show ProjectReport/latex/figures/screens/my-contacts-done-content.png in a tablet frame, zoom to one contact card, highlight offer, talking points and the message draft. Two tap targets pulse, then a status chip changes to "Accepted". A small stamp reads "Nothing is sent automatically".

**Say:** Staff open My contacts on a tablet. Each call shows the offer, talking points and an editable message draft. They log the result in two taps. AnchorAI never sends anything itself.

### P2.6  (about 2:45, 11 s, 27 words)

**On screen:** A loop arrow animation over the weekly flow diagram. Outcome chips "Accepted" and "Declined" travel along the dashed arrow back to a box named "Past cases", and a second arrow feeds a box named "Contact limits". The dashboard screenshot ProjectReport/latex/figures/screens/dashboard.png fades behind, blurred, showing outcomes by week.

**Say:** Those outcomes come back next week. Accepted and declined offers become new past cases. And every contact counts toward the limits, so nobody gets chased too often.

### P2.7  (about 2:57, 20 s, 53 words)

**On screen:** Comparison bars on a dark panel, drawn from the E4 table (genetic algorithm on case-based estimates, 36 h and US$1,500, simulated gym). Three bars grow, "Contact everyone 10.4", "Contact by risk 13.7", "AnchorAI default (genetic algorithm) 16.7". A separate card shows the "AnchorAI quick planner" (greedy) at 21.0 for US$432. A spend row shows US$1,076, US$1,280, US$1,500 and US$432 as proportional bars. Then a large kinetic text, "22% to 138%", captioned as the default planner against contacting by risk or schedule, with a small "simulated gym" badge. The 22 to 138 percent is never shown next to the quick planner figure.

**Say:** Does it pay? In our simulated gym at 36 staff hours, the default planner keeps 16.7 extra members against 13.7 for contacting by risk. The quick planner keeps 21.0 for 432 dollars. Across settings, the default keeps 22 to 138 percent more than risk or schedule. It shows the method, not your gain.

*Section 2 word count: 238, about 1:38 at 145 words per minute.*


## Section 3. Abdulaziz Ali S Hasanain, knowledge and interaction (3:20 to 5:00)

### P3.1  (about 3:20, 12 s, 27 words)

**On screen:** Illustrated desk once more, clock chip "Monday, 10:00". Lower third slides in, "Abdulaziz Ali S Hasanain, knowledge and interaction". Cut to ProjectReport/latex/figures/screens/rules-test-content.png in a laptop frame, zoom to the rule trace. Rule chips light one after another from the real trace for member M1460, "Guardrail G01 blocks all offers", "Derived fact D03", "Derived fact D05".

**Say:** I'm Abdulaziz. A plan only helps if staff trust it. Every contact shows the rules that fired. Managers can edit, test and roll back all 29 rules.

### P3.2  (about 3:32, 12 s, 30 words)

**On screen:** Funnel animation. 3,448 proposal dots fall in, a gate labelled "Guardrails" removes some in orange, and 1,080 dots drop away. The count "31.3% blocked" appears. Beside it, three guardrail chips, "max one contact per 30 days", "no paid offers at low risk", "no repeat training session".

**Say:** Five guardrails block unsafe offers, and they always win. They removed 31.3 percent of proposals in our tests, mostly repeat contacts within 30 days. We claim safety, not extra members.

### P3.3  (about 3:44, 14 s, 33 words)

**On screen:** Show ProjectReport/latex/figures/screens/graph-content.png in a laptop frame, zoom into the neighbourhood graph as an instructor node turns grey and drops out. Counters build on the right, "312 members affected" and "54 at high risk". A tag fades in, "243 low risk members the churn score missed".

**Say:** A knowledge graph sees what a churn score cannot. If an instructor leaves, it shows the 312 members affected, 54 at high risk. It also reached 243 low risk members the score missed.

### P3.4  (about 3:58, 13 s, 32 words)

**On screen:** Show ProjectReport/latex/figures/screens/assistant-content.png in a laptop frame, zoom to a typed question and the answer with numbered citation chips. One chip is hovered and the evidence line expands. Below, a second question gets the reply "I don't know based on the data I have". A bar fills to 96.2% labelled "judged sentences supported by evidence".

**Say:** Staff can ask. The assistant answers only from the system's own evidence, and cites it. If nothing supports an answer, it says I don't know. 96.2 percent of judged sentences were supported.

### P3.5  (about 4:11, 15 s, 37 words)

**On screen:** A pricing card slides in centre on a clean light background. Big kinetic numbers count up, "US$199" per month for the first club and "US$149" for each further club, up to 5. Icons below, a computer with a chip and the note "runs on your own machine, language model included" and a crossed out meter, "no fee per question".

**Say:** AnchorAI sits beside your membership system. It costs 199 US dollars a month for the first club, and 149 for each extra club, up to 5. It runs on your own machine, with no fee per question.

### P3.6  (about 4:26, 14 s, 35 words)

**On screen:** Break even animation. A balance scale tips as "0.6 members a month" appears for one club and "1.8" for three clubs at US$497 a month. Next, a horizontal bar chart of monthly prices, "AnchorAI 199", "Keepme about 750, 2020 figure", "PushPress 159 to 229", "Gymdesk 75 to 240". The AnchorAI bar is highlighted.

**Say:** One club breaks even when AnchorAI keeps 0.6 members a month who would have left. Three clubs need 1.8. A retention layer for chains was quoted at about 750 dollars a month for one site.

### P3.7  (about 4:41, 14 s, 34 words)

**On screen:** Slow pull back to the full dashboard screenshot ProjectReport/latex/figures/screens/dashboard.png in a laptop frame, with the AnchorAI logo and the three names in the lower third. Final card text, "Explainable, budget aware retention", then "Thanks for watching." Fade to black.

**Say:** Our results come from a simulated gym, so we claim the method, not the size of the win. AnchorAI helps a manager decide who to call, with the reason in hand. Thanks for watching.

*Section 3 word count: 228, about 1:34 at 145 words per minute.*


## Fact sheet

Every number spoken or shown in this video, with where it comes from. Paths are relative to the repository root.

| Fact | Source |
|---|---|
| About 1 member in 3 leaves each year; most stop attending weeks before they cancel | ProjectReport/latex/main.tex (abstract) |
| 66.4% median member retention in 2024, across 175 operators | ProjectReport/latex/main.tex section 1 (hfa2025benchmarking) |
| 63% stopped before their third month, in one fitness centre | ProjectReport/latex/main.tex section 1 (sperandei2016adherence) |
| Kept member valued at 6 months of fees; US$54 middle fee, 6 month contract, so US$324 (an assumption of the scenario layer, not a market figure) | ProjectReport/latex/chapters/pricing.tex |
| Calendar campaigns, threshold rules and vendor risk scores; 12 visits a month falling to 4 versus a steady 2 | ProjectReport/latex/main.tex section 1, Table practice |
| 4,000 real members from a public dataset | ProjectReport/latex/main.tex section 3 (Data and the scenario layer) |
| 4 segments; New and slipping = 728 members and about two thirds of all churners; churn rates 94.6%, 17.4%, 12.6%, 1.4% | SystemCode/notebooks/results/e1_segment_profiles.csv; ProjectReport/latex/main.tex E1 |
| 800 unseen test members; 193 of 212 churners flagged; 20 false alarms; high band churns at 93.9% | ProjectReport/latex/main.tex E2 results |
| 5 drivers per member (LR term + TreeSHAP) | ProjectReport/latex/main.tex Methods, Member intelligence |
| Recall 0.522 for ages 31+; the model misses about half of those churners | ProjectReport/latex/main.tex E2 results |
| Budget US$1,500 and 36 staff hours are the defaults | ProjectReport/latex/main.tex user guide paragraph (starts from US$1,500 and 36 hours); ProjectReport/latex/main.tex E4 |
| 200 nearest past cases; 10 similar past cases shown in the why panel | ProjectReport/latex/main.tex Methods, Decision and optimisation; System design |
| Plan of 182 contacts at 36 h, US$1,500 (GA on CBR); about 13 seconds (13.06 to 13.72 s over three seeds) | SystemCode/notebooks/results/e4_estimates.csv (GA rows, CBR, 36 h, 1500); ProjectReport/latex/main.tex Figure screens caption (182 approved contacts) |
| Plan approval locks the plan, one per week; calls shared by free hours and skills; override needs a reason and is rule-checked at once; staff log outcomes in two taps; drafts never sent | ProjectReport/latex/main.tex user guide paragraphs, System design |
| Accepted/declined outcomes become new past cases; contacts count toward limits | ProjectReport/latex/main.tex System design, weekly cycle |
| 36 h, US$1,500 (simulated gym, estimates from case-based reasoning): contact-all 10.4 extra members kept (spend US$1,076), risk-top-k 13.7 (US$1,280), default planner = genetic algorithm 16.7 (US$1,500, 182 contacts), quick planner = greedy 21.0 (US$432, 360 contacts) | SystemCode/notebooks/results/e4_estimates.csv (mean over seeds); ProjectReport/latex/main.tex Table e4 |
| 22% to 138% more members kept by the default planner than by contacting by risk or schedule across the settings tested (36 h and US$1,500: 16.7 against 13.7 is +22%; 120 h and US$4,000: 48.1 against 20.2 is +138%). Never quoted for the quick planner | ProjectReport/latex/main.tex abstract, E4 verdict; e4_estimates.csv |
| Guardrails: 5; 3,448 proposals, 1,080 removed = 31.3%; by guardrail: G01 contact cap 1,029, G05 PT eligibility 44, G04 low risk no paid offers 7, G02 and G03 0 | ProjectReport/latex/main.tex E6 figure caption and results; SystemCode/notebooks/results/e6_guardrail_bites.csv |
| 29 rules | ProjectReport/latex/main.tex Methods, Decision automation |
| Simulated instructor leaving: 312 members affected, 54 at high risk | ProjectReport/latex/main.tex Figure kgsim caption |
| 243 low risk members reached via graph signals; helps only when staff time is spare (about +7 members at 120 h, nothing at 36 h) | ProjectReport/latex/main.tex E7 results |
| 96.2% of 80 judged sentences supported by evidence; assistant says it does not know when unsupported | ProjectReport/latex/main.tex E8 results; user guide |
| US$199 a month first club, US$149 each further club up to 5; 3 clubs = US$497; runs on operator's own machine incl. local LLM, no fee per question | ProjectReport/latex/chapters/pricing.tex |
| Break even 0.6 members a month for one club, 1.8 for three clubs | ProjectReport/latex/chapters/pricing.tex |
| Keepme quoted US$9,000 a year for one site in 2020, about US$750 a month; PushPress membership system 159 to 229; Gymdesk 75 to 240 | ProjectReport/latex/chapters/pricing.tex, Table pricing |
| Results are on a simulated scenario, so the method is shown, not the real size | ProjectReport/latex/main.tex Findings, Limitations, Recommendations |
| Mid-market positioning: one to five club operators underserved | ProjectReport/latex/main.tex section 1, Market and positioning |
| Why drawer for M0106: 99% churn risk, drivers (change in weekly visits, months as a member, age, visit trend, extra spend per month), rules D05, D02, P01, P06, P05, 10 similar past members with 3 of 4 staying with the offer and 4 of 6 with no offer | SystemCode/data/app.db, plan_items row for M0106 (explanation JSON) |
| Staff assignment: Sam Staff 20 h, trainer and calls, 98 contacts; Jordan Staff 16 h, calls, 84 contacts; 182 in all | SystemCode/data/app.db, staff_profiles and assignments |
| Rule trace for M1460: G01 blocks all offers, D03 concludes Disengaged, D05 concludes High value at risk | SystemCode/frontend screenshot rules-test-content.png; anchorai/reasoning/rules/*.yaml |
| Mock dialog wording (remove with reason, add or swap with live rule check, approve, draft message note) | SystemCode/frontend/src/pages/PlanBuilder.vue, components/AddContactDialog.vue, components/MessageDraftDialog.vue |
