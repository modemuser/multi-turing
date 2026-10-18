# Feedback-required new bricks: pipeline definition vs behaviour-level comparison

All 1160 closed-loop new bricks of the mix probe at p_append 0.5 (400 instances x 4 rule draws, 24 schedules). Intervals 95%, bootstrap clustered by instance.

| definition | bricks | share |
|---|---|---|
| pipeline: no new brick in the open-loop run at the same schedule | 604 | 604/1160 = 52.1% [41.7, 62.6] (110 instances, clustered) |
| behaviour: learned program behaves unlike the open-loop program on >= 1 of 256 fresh tapes | 679 | 679/1160 = 58.5% [48.2, 69.1] (110 instances, clustered) |
| both | 493 | 493/1160 = 42.5% [32.8, 53.1] (110 instances, clustered) |

- bricks that are feedback-required by the pipeline definition but behave exactly like their open-loop program on all 256 tapes: 111
- bricks that are NOT feedback-required by the pipeline definition but behave unlike their open-loop program: 186
- closed-loop table differs from the open-loop table: 848; canonical rules differ: 785
- among behaviour-level feedback-required bricks, tapes on which the two programs differ: median 247 of 256, IQR 124-256
