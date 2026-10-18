# New bricks under endogenous order

Exploratory probe: 400 base instances, complete graph, order set by the agents' route fields (hold cap 3, wait cap 6), 3 start turns, new bricks on all 256 fresh tapes (20k-step cap).

| p_append | runs where learning changed who moves | rule synthesis (agent × start) | P(new brick | synthesis) | instances with a new brick | feedback-required share | new bricks in runs whose order learning changed |
|---|---|---|---|---|---|---|
| 0.5 | 0.198 [0.176, 0.221] (n=1200) | 0.037 [0.031, 0.044] (n=3600) | 0.271 [0.202, 0.352] (n=133) | 0.043 [0.027, 0.067] (n=400) | 0.444 [0.295, 0.604] (n=36) | 0.278 [0.158, 0.440] (n=36) |
