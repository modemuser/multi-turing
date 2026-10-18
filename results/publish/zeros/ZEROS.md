# Exception hunt for the unproven zeros

Fresh instances, complete graph, 24 schedules, closed and open loop. Unresolved runs (budget 200k steps): 542.

| states | learner | open-loop exposure-order dependent | rule synthesis, closed loop | rule synthesis, open loop | exceptions with ≥2 contested fields | instances with ≥2 contested fields |
|---|---|---|---|---|---|---|
| 2 | pregrown | 0 of 3997 (95% upper bound 0.07%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 0 | 3 |
| 2 | set | 1 of 3997 (0.03%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 1 | 1 |
| 3 | pregrown | 1 of 1997 (0.05%) | 0 of 1997 (95% upper bound 0.15%) | 0 of 1997 (95% upper bound 0.15%) | 0 of 1 | 6 |
| 3 | set | 2 of 1996 (0.10%) | 2 of 1996 (0.10%) | 1 of 1996 (0.05%) | 2 of 3 | 14 |
