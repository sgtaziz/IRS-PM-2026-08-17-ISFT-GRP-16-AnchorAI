# Decision and optimisation: case-based reasoning, genetic algorithm and CP-SAT

This part of AnchorAI makes the weekly decision. It takes the members the rules allow us to contact, estimates what each offer would achieve for each of them, and chooses the most valuable plan within the week's limits: the value of the members it keeps, net of offer costs. Three techniques do the work: **case-based reasoning** estimates the effect of each offer, a **genetic algorithm** searches for the best plan, and **CP-SAT constraint optimisation** gives an exact benchmark and a fast exact planner. The settings below were chosen in the notebooks `b_plan_model`, `b_cbr`, `b_ga` and `b_exact`, and the code is in `anchorai/cbr/` and `anchorai/optimisation/`.

## The planning problem

**Options.** The rule engine lists, for each member, the offers and channels they may receive. Each allowed pair becomes an *option*. In the experiments, 1,045 members had 2,025 options, at most four each. Not contacting a member is always possible and is worth nothing.

**The offers** (editable by the admin):

| Offer | Cost | Staff minutes | Weekly stock |
|---|---|---|---|
| Personal check-in message | $0 | 5 | unlimited |
| Bring-a-friend class pass | $15 | 10 | 100 |
| One month at 20% off | $12 | 15 | unlimited |
| Free personal training session | $40 | 60, by a trainer | 40 |

**Value of an option.** A member kept pays their monthly fee for several more months. The planner values an option as

> value = estimated uplift × monthly fee × 6 months − offer cost

where *uplift* is the extra probability that the member stays because of the offer [1]. Six months is a deliberately cautious horizon. An option with a negative value is never worth taking.

**Limits.** A plan is feasible only if it contacts each member at most once, keeps within the week's budget and staff minutes, gives free PT sessions only within trainers' minutes, and does not exceed any offer's stock. Contact limits (for example, no more than one contact in 30 days) and eligibility are already enforced by the rules, so a blocked option never reaches the planner.

**Two objectives.** The *linear* objective is the sum of the chosen options' values. In this form the problem is a multiple-choice knapsack (choose at most one option per member within shared limits), which an exact solver handles quickly. The *full* objective adds two effects between members, using the class groups from the knowledge graph:

- **Spillover.** Members who train together influence each other, so a contacted member's value is multiplied by (1 + β × the share of their classmates also contacted), with β = 0.5. A member whose classmates are all contacted is worth 50% more.
- **Diminishing returns.** Many contacts aimed at one instructor's classes overlap, so the n-th most valuable contact among one instructor's members counts 1 / (1 + d·(n − 1)) of its value (d = 0.02).

These two effects make the problem non-linear, which is why a genetic algorithm is justified. They are planning assumptions: the scenario's true effects include neither, so experiment E5 checks that the genetic algorithm's advantage holds across a range of β and d.

## Case-based reasoning: what would each offer achieve?

A **case** is one past contact decision: a member (the problem), the offer they received or none (the solution), and whether they stayed (the outcome). The case base starts with 2,400 cases from the scenario's simulated contact history, in which offers were given at random: 1,416 members who received one of the four offers and 984 who were not contacted.

| CBR step | How AnchorAI does it |
|---|---|
| **Retrieve** | Describe every member by the same 17 standardised features the churn model uses, weighted equally. For a member and an offer, find the 200 nearest cases among those who received that offer and those who received nothing, in one shared neighbourhood. A member never retrieves their own case. |
| **Reuse** | Treat the neighbourhood as a small A/B test. The local uplift is the stay rate of neighbours who received the offer minus the stay rate of neighbours who received nothing, with closer cases weighted more (a Gaussian kernel scaled to each member's neighbourhood). |
| **Revise** | A local estimate from a few dozen cases is noisy, so it is shrunk toward the offer's average effect (empirical-Bayes shrinkage [2]). The weight on the local estimate is the estimated real variation between members divided by that variation plus the noise, both measured from the cases. Where members barely differ, the estimate falls back to the average. |
| **Retain** | When staff log an outcome, an accepted offer becomes a case where the member stayed and a declined offer one where they left. This is a stand-in: whether the member really stays is known only weeks later. Other outcomes (reached, follow-up, no answer) are not cases. |

**The explanation comes for free.** The same neighbours that produce the estimate are shown as precedents: the ten most similar members who received the offer or nothing, nearest first, each with what happened to them, for example: M0123 got Free personal training session in the week of 2026-08-03 and stayed. They appear in every plan item's explanation.

**Design decisions that came from testing.**

- *One neighbourhood, not two.* A first version took the nearest treated and the nearest untreated cases separately. It scored much better against the truth, but a **null test**, with offers shuffled so the true effect is zero, showed it was measuring churn risk rather than the offer's effect: treated and untreated neighbours were not equally similar. The shared neighbourhood passes the null test.
- *Settings fixed by rule.* On the history, every weighting, every k and every variant scored within the noise of a random ranking. The score used was the Qini coefficient [1], which measures how much more the top-ranked cases responded to an offer than the rest, computed on cases held out from fitting. The data cannot choose between them, so we fixed equal weights, k = 200 and distance weighting before grading against the truth.
- *Logged outcomes do not change the offer averages.* The planner chooses whom to contact, so the members in its plans are not a random sample. If their outcomes fed the offer averages, a week of high-risk contacts would make the offers look weaker than they are. Logged cases therefore join the neighbourhoods and the explanations, but each offer's average effect is taken from the simulated randomised history only. Learning reliable averages from live use would need a small random control group.

## Genetic algorithm: searching for the best plan

| Element | Choice |
|---|---|
| Chromosome | One gene per member with at least one option; the gene's value picks one of that member's options, and 0 means no contact |
| Fitness | The full objective (value with spillover and diminishing returns) |
| Initial population | 100 plans: the greedy plan and 49 mutated copies of it, plus 50 sparse random plans for diversity |
| Selection | Tournament of 3 |
| Crossover | Uniform, probability 0.7 |
| Mutation | About two genes changed per child |
| Constraint handling | A **repair operator** drops the chosen options with the least value per share of budget and staff time until every limit holds |
| Elitism | The 2 best plans pass unchanged to the next generation |
| Stopping | 300 generations, or 60 generations without improvement |

The genetic algorithm uses DEAP and a fixed random seed, so the same inputs give the same plan. It is the default planner and takes about 25 seconds for the gym's 1,045 candidate members, run as a background job with a progress bar.

Repair was chosen over penalties because a penalty lets infeasible plans breed and wastes generations on them. Experiment E5 confirms both design choices: penalties instead of repair end 2.4% lower, and starting without the greedy plan ends 2.9% lower.

## CP-SAT: the exact benchmark

CP-SAT (Google OR-Tools) is a constraint solver: we state what a valid plan is and what to maximise, and it returns either a proven optimum or its best plan with an upper bound on what any plan could reach.

- **Linear model.** One yes/no variable per option, at most one per member, and the budget, staff, trainer and stock limits. For the gym's 4,000 members, of whom 1,045 have options, it proves the optimum in about a second (9.5 s when all 4,000 have options, E5). Managers can choose it as the "exact" planner, and the assistant uses it to answer what-if questions about the budget.
- **Full model.** Spillover is added as products of yes/no variables (member contacted × classmate contacted). Diminishing returns are modelled by giving each contacted member in an instructor's group one rank slot, with weights that fall by rank. Because the weights fall, the solver's best assignment of slots is the sorted one, so the model is exact rather than approximate. It proves the optimum only for small groups of members, up to about 50, and is used to measure how close the genetic algorithm gets.

## Baselines and the policy evaluator

Three simple policies show what the planner adds. All fill the plan the same way, taking options in order while they fit every limit; they differ only in the order:

- **Contact-all:** each member's top offer from the playbook, in random order (as a calendar campaign would).
- **Risk-top-k:** each member's top offer, highest churn risk first (as a vendor risk score would).
- **Greedy-uplift:** any option worth more than it costs, highest value per share of budget and staff time first.

The **policy evaluator** grades any plan against the scenario's true effects: each member left alone stays with their true probability, and each contacted member gains the offer's true uplift. It is used only to grade, never to choose, so no planner can learn the answer.

## From plan to action

The plan becomes a working list through the manager's review:

- **Explanation.** Each plan item stores the member's churn probability and top drivers, the rules that fired, any graph signals, the ten most similar past cases and a one-line summary.
- **Overrides.** A manager can remove a member or add one with a chosen offer and channel. Each change needs a reason and is checked against the rules immediately, including whether the member has a phone for an SMS or a call.
- **Re-optimise.** This keeps every change the manager made by hand and re-plans the rest of the week's budget, staff time and stock.
- **Approval.** Approval locks the plan. Only one plan per week can be approved, so each week has a single official plan.
- **Assignment.** Contacts are shared out, most valuable first, each to the eligible staff member with the most free minutes. Free PT sessions need a trainer and phone calls need staff with the calls skill. Managers can then move contacts by drag and drop and print a call sheet per staff member.
- **Outcomes.** Staff log one outcome per contact (reached, no answer, accepted, declined or follow-up) and can log only their own. Logged outcomes return to the case base and count toward the contact limits for the following weeks.

## References

1. Radcliffe, N. J. (2007). Using control groups to target on predicted lift: building and assessing uplift models. *Direct Marketing Analytics Journal*, 1(3), 14–21.
2. Efron, B. and Morris, C. (1975). Data analysis using Stein's estimator and its generalizations. *Journal of the American Statistical Association*, 70(350), 311–319. https://doi.org/10.1080/01621459.1975.10479864
