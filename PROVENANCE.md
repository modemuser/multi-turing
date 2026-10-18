# Provenance: reproducing every number in the post

All numbers cited in [POST.md](POST.md) and [POST_LONG.md](POST_LONG.md) come from **one pipeline run with the current
code**, written to `results/publish/`, and are listed with their sources in
`results/publish/POST_NUMBERS.md`.

```bash
uv sync                                  # Python 3.13, deps pinned in uv.lock
uv run pytest -q                         # engine, lemmas-as-properties, cross-implementation checks
uv run python -m mt.pipeline             # all probes the post cites (resumable; ~2.25 h on 10 cores)
uv run python -m mt.post_numbers         # every number in the post, recomputed -> POST_NUMBERS.md
python3 verify/verify_witness.py verify/<witness>.json   # standalone check of the §1 example
```

## Stages (`mt/pipeline.py`)

| stage | what | post sections |
|---|---|---|
| set | 800 instances, overwrite learners: all graphs, open/closed loop, no learning, volume-matched coupling | §3, §4 |
| subset | the 400-instance subset (first 100 per rule size) | all matched comparisons |
| threshold, toggle, append | learner types on the subset | §4 |
| append_once, pregrown | L6 test; pre-grown control | §5 |
| synthesis | open-loop synthesis classes, L6 precedence-cycle test | §5 |
| closed_serial | program-level non-serialisability, learning vs coupling | §5 |
| closed_loop | L7: learner dependence vs source-stream variation | §4 |
| mix | designed construction/revision mix (p_append 0.25 / 0.5 / 0.75) | §1, §5, §6 |
| bricks | new bricks: 4-tape share, distribution over 256 tapes; `mt.feedback_behaviour` adds the behaviour-level check of feedback necessity (`FEEDBACK_BEHAVIOUR.md`, not a pipeline stage) | §1, §6 |
| n3 | 3-state robustness | §7 |
| endo | endogenous order | §6 |
| zeros | exception hunt (5 998 fresh instances) | §7 |
| verify | independent re-check of the §1 witness | §1 |
| figures | Figure 1, drawn from the witness data (`mt/figures.py`) | §1 |

## Instance ids

An instance id is a hash of the instance (initial programs, rule, capacity). The rules of
constructive learners are seeded by the instance id, so ids determine instances. Everything in
`results/publish/` uses the current id format consistently.

Exploratory result folders outside `results/publish/` (`results/m1`, `results/swarm_N8_*`, …) were
produced during development. Some use an earlier id format (before capacity was added to the
instance), so their constructive-learner instances differ from those in `results/publish/`. They
document how the project got here and are not included in this repository. The post cites only
`results/publish/`.

## Reused output

In the original run, the `zeros` stage copied `results/zeros/` (exception hunt, 2026-10-17, ~45 min)
instead of recomputing it. That folder came from the same code and id format, and nothing it depends
on has changed since. It is not part of this repository, so in a fresh clone the stage recomputes the
hunt (`mt.zeros_hunt` then `mt.l9_check`). The run table is stored gzipped
(`results/publish/zeros/zeros_runs.csv.gz`); `mt.l9_check` gives an identical `l9_check.csv` from it.

## What changed when the numbers were regenerated (2026-10-17)

Regenerating with consistent ids redrew the constructive learners' rules. Two corrections followed.

1. **Intervals for shares counted over agent × schedule pairs were too narrow.** Pairs from the same
   instance are correlated, so they now use a bootstrap over instances. With honest intervals the old
   and new draws agree (feedback-required share with one rule draw per instance: 74% [55, 91] old draw, 51% [29, 79] new
   draw).
2. **More independent rule draws** (4 per instance) for the §1/§5/§6 numbers. Headline numbers now:
   feedback-required 52% [42, 63] (2 states; 74% [57, 88] at 3 states); instances × draws with a new
   brick 7.4% [6.2, 8.6]; P(new brick | synthesis) falls from 31% to 18% as the append share rises
   from 25% to 75%.

Structural results were unchanged: no synthesis without a precedence cycle, 0 program-level
synthesis for overwrite learners, ring 0%, pre-grown 0%, no new brick without revision, and the
exception hunt / L9.

## The §1 witness (2026-10-18)

The §1 example is instance `3f993cc102db`, rule draw 1 (`3f993cc102db#1` in `results/publish/mix/`),
schedule ABC, learner C: a new brick on 114 of 256 fresh tapes, and a program that behaves unlike
the one C learns in the open loop at the same schedule on 114 of 256 tapes. It was chosen among the
bricks that satisfy both feedback criteria (`results/publish/bricks/FEEDBACK_BEHAVIOUR.md`) for the
shortest timeline (three lessons by step 5) and for behaviour that differs visibly on the blank tape
(the learned program inches left; the serial versions sweep right and back). The earlier witness
`5c80f863a87b` (B, BCA; 255 of 256 tapes) is kept in `verify/` as a second checkable example: it is
feedback-required by the pipeline's definition, but its closed-loop and open-loop programs behave
identically on every tape, which is why it was replaced.
