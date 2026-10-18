# Numbers cited in the post, recomputed by mt.pipeline

| section | quantity | value |
|---|---|---|
| §3 | no interaction, order-dependent (full outcome) | 0/400 = 0.0% [0.0, 1.0] |
| §3 | physical coupling, volume-matched | 267/399 = 66.9% [62.2, 71.4] |
| §3 | learning (overwrite) | 98/400 = 24.5% [20.5, 28.9] |
| §4 | ring, open loop, set | 0/400 = 0.0% [0.0, 1.0] |
| §4 | ring, open loop, threshold | 0/400 = 0.0% [0.0, 1.0] |
| §4 | ring, open loop, toggle | 0/398 = 0.0% [0.0, 1.0] |
| §4 | ring, open loop, append | 0/400 = 0.0% [0.0, 1.0] |
| §4 | set: open loop | 0/400 = 0.0% [0.0, 1.0] |
| §4 | set: closed loop | 31/400 = 7.8% [5.5, 10.8] |
| §4 | threshold: open loop | 6/400 = 1.5% [0.7, 3.2] |
| §4 | threshold: closed loop | 42/400 = 10.5% [7.9, 13.9] |
| §4 | toggle: open loop | 54/398 = 13.6% [10.5, 17.3] |
| §4 | toggle: closed loop | 158/394 = 40.1% [35.4, 45.0] |
| §4 | append: open loop | 77/400 = 19.2% [15.7, 23.4] |
| §4 | append: closed loop | 140/400 = 35.0% [30.5, 39.8] |
| §4 | instances with conflicting overwrites | 69 of 800 |
| §4 | share of their cycles that keep changing | 58.0% |
| §4 L7 | set: order-dependent learners with a varying source stream | 49 of 49 |
| §4 L7 | append: order-dependent learners with a varying source stream | 263 of 276 |
| §5 | pre-grown, open loop order-dependent | 0/400 = 0.0% [0.0, 1.0] |
| §5 | p_append 0.25: synthesis (agent x schedule) | 2331/115086 = 2.0% [1.7, 2.4] (400 instances, clustered) |
| §5 | p_append 0.25: P(new brick | synthesis) | 729/2331 = 31.3% [23.8, 39.0] (126 instances, clustered) |
| §5 | p_append 0.25: instances (x rule draws) with a new brick | 57/1599 = 3.6% [2.7, 4.4] (400 instances, clustered) |
| §5 | p_append 0.5: synthesis (agent x schedule) | 5037/115185 = 4.4% [3.8, 5.0] (400 instances, clustered) |
| §5 | p_append 0.5: P(new brick | synthesis) | 1160/5037 = 23.0% [18.5, 27.5] (206 instances, clustered) |
| §5 | p_append 0.5: instances (x rule draws) with a new brick | 118/1600 = 7.4% [6.2, 8.6] (400 instances, clustered) |
| §1/§6 | new bricks (agent x schedule) / feedback-required | 1160 / 604/1160 = 52.1% [41.7, 62.6] (110 instances, clustered) |
| §1 | instances (x rule draws) with a new brick | 118/1600 = 7.4% [6.2, 8.6] (400 instances, clustered) |
| §1 | new bricks feedback-required at the behaviour level / by both definitions | 679/1160 = 58.5% [48.2, 69.1] (110 instances, clustered) / 493/1160 = 42.5% [32.8, 53.1] (110 instances, clustered) |
| §5 | p_append 0.75: synthesis (agent x schedule) | 7713/115164 = 6.7% [5.9, 7.5] (400 instances, clustered) |
| §5 | p_append 0.75: P(new brick | synthesis) | 1393/7713 = 18.1% [14.9, 21.5] (253 instances, clustered) |
| §5 | p_append 0.75: instances (x rule draws) with a new brick | 150/1600 = 9.4% [7.9, 10.9] (400 instances, clustered) |
| §5 | synthesis instances, class 'all commute' | 0 of 164 |
| §5 | synthesis instances, class 'append-append' | 41 of 71 |
| §5 | synthesis instances, class 'append-revise' | 12 of 165 |
| §5 | order-dependent instances that synthesise (strict / fine) | 52 / 51 of 77 |
| §5 L6 | pairs without a precedence cycle / synthesis among them | 46580 / 0 |
| §5 | closed loop, program-level non-serialisable, set | 0/28800 = 0.0% [0.0, 0.0] (400 instances, clustered) |
| §5 | closed loop, program-level non-serialisable, append | 1294/28800 = 4.5% [3.3, 5.7] (400 instances, clustered) |
| §6 | synthesised programs that are new bricks (256 tapes) | 1160/5037 = 23.0% [18.5, 27.5] (206 instances, clustered) |
| §6 | ... on the 4 FRESH tapes | 959/5037 = 19.0% [14.9, 23.3] (206 instances, clustered) |
| §6 | tapes differing: median / IQR / >=128 / all 256 / <=8 | 209 / 96-255 / 69.0% / 24.5% / 37 bricks |
| §6 | endogenous: runs where learning changed who moves | 237/1200 = 19.8% [16.0, 23.7] (400 instances, clustered) |
| §6 | endogenous: P(new brick | synthesis) | 36/133 = 27.1% [15.1, 39.9] (47 instances, clustered) |
| §7 | 3-state: instances with a new brick | 40/395 = 10.1% [7.5, 13.5] |
| §7 | 3-state: feedback-required share | 353/477 = 74.0% [56.6, 88.3] (40 instances, clustered) |
| §7 | 3-state: P(new brick | synthesis) | 477/2018 = 23.6% [16.7, 31.2] (108 instances, clustered) |
| §7 | 3-state: new bricks without revision rules | 0 |

### §7 exception hunt (verbatim)

| states | learner | open-loop exposure-order dependent | rule synthesis, closed loop | rule synthesis, open loop | exceptions with ≥2 contested fields | instances with ≥2 contested fields |
|---|---|---|---|---|---|---|
| 2 | pregrown | 0 of 3997 (95% upper bound 0.07%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 0 | 3 |
| 2 | set | 1 of 3997 (0.03%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 3997 (95% upper bound 0.07%) | 0 of 1 | 1 |
| 3 | pregrown | 1 of 1997 (0.05%) | 0 of 1997 (95% upper bound 0.15%) | 0 of 1997 (95% upper bound 0.15%) | 0 of 1 | 6 |
| 3 | set | 2 of 1996 (0.10%) | 2 of 1996 (0.10%) | 1 of 1996 (0.05%) | 2 of 3 | 14 |

