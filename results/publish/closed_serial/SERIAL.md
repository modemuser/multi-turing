# Closed-loop serialisability: learning vs physical coupling

Exploratory probe. Complete graph, closed loop, 24 exogenous schedules, 400 instances × 3 agents. *Synthesis*: the agent's state after its input history differs from both serialisations (same slots, A's influences first or B's first). Coupling is the volume-matched variant. Rates are over agent × schedule pairs (95% Wilson CI), and the instance-level rate counts any agent or schedule.

## Rule set: set

| channel | synthesis (full state) | instances with any synthesis | the two serial orders differ | synthesis of rules only |
|---|---|---|---|---|
| couple_once | 0.225 [0.221, 0.230] (n=28788) | 0.790 [0.747, 0.827] (n=400) | 0.369 [0.363, 0.374] (n=28788) | – |
| learn | 0.046 [0.044, 0.048] (n=28800) | 0.305 [0.262, 0.352] (n=400) | 0.142 [0.138, 0.146] (n=28800) | 0.000 [0.000, 0.000] (n=28800) |

## Rule set: append

| channel | synthesis (full state) | instances with any synthesis | the two serial orders differ | synthesis of rules only |
|---|---|---|---|---|
| couple_once | 0.183 [0.178, 0.187] (n=28779) | 0.705 [0.659, 0.748] (n=400) | 0.318 [0.312, 0.323] (n=28779) | – |
| learn | 0.078 [0.075, 0.081] (n=28800) | 0.347 [0.302, 0.395] (n=400) | 0.230 [0.225, 0.235] (n=28800) | 0.045 [0.043, 0.047] (n=28800) |

