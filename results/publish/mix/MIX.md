# Designed construction/revision mix

Exploratory probe, 400 base instances per setting, closed loop, complete graph, 24 schedules, new bricks on all 256 fresh tapes (20k-step cap).

| p_append | mean append / revision rules | rule synthesis (agent × schedule) | P(new brick | synthesis) | instances with a new brick | feedback-required share of new bricks | instances with a feedback-required brick |
|---|---|---|---|---|---|---|
| 0.25 | 0.51 / 3.49 | 0.020 [0.019, 0.021] (n=115086) | 0.313 [0.294, 0.332] (n=2331) | 0.036 [0.028, 0.046] (n=1599) | 0.379 [0.344, 0.414] (n=729) | 0.024 [0.018, 0.033] (n=1599) |
| 0.5 | 1.00 / 3.02 | 0.044 [0.043, 0.045] (n=115185) | 0.230 [0.219, 0.242] (n=5037) | 0.074 [0.062, 0.088] (n=1600) | 0.521 [0.492, 0.549] (n=1160) | 0.058 [0.047, 0.070] (n=1600) |
| 0.75 | 1.50 / 2.52 | 0.067 [0.066, 0.068] (n=115164) | 0.181 [0.172, 0.189] (n=7713) | 0.094 [0.080, 0.109] (n=1600) | 0.648 [0.623, 0.673] (n=1393) | 0.080 [0.068, 0.094] (n=1600) |
