# Lab notebook

## Origin of the idea (Thomas, from an earlier session; recorded 2026-10-17)

Turing machines are like simple Lego blocks. Every attempt to compose them ends up as a union of
machines, which is just one bigger Turing machine. The hunch: they *can* be composed into something
else, and the only way is to let them **rewrite each other's rules**, which are normally sacrosanct
and never changeable from outside. That intuitively feels the same as an agent swarm, and it is
why this project exists.

*Where the results stand on this (interpretation):* rule rewriting does not escape "one bigger
machine" (the swarm still folds into one TM). What it changes is what the **parts** become.
Revision learning keeps the composite decomposable (serialisable). Constructive learning can
create programs that no part, and no sequence of the parts, would produce (non-serialisable
program change, ≥3 agents by L1). The transplant test checks whether such new "bricks" carry their
new shape into fresh situations.

---

Chronological log of findings. All numbers are counts over random samples at a finite budget,
**not proofs**. *Interpretation* is labelled. Reports hold the full tables. Working agreements are in
the model in [DESIGN.md](DESIGN.md).

---

## 2026-10-16: two agents

**M1, 2-state, N=8, with halting** ([report](results/m1/REPORT.md)). 40k instances.
- Mutual rewrite (C2) is `local`-confluent in 80.5% of instances. Fixed tables (C3): 100% by construction.
- About a third of the non-confluence is a first-mover race. Non-confluence grows with rule size k.
- *Interpretation:* endogenous order looked different from exogenous order mainly because of
  **starvation** (a machine that never yields).

**M2, N = 8 / 16 / 32, same instances** ([compare](results/m2/COMPARE.md)). Rates are identical to 3
decimals. Transients are 3–5 steps. *Interpretation:* the uniform prior gives shallow machines.

**Halting removed** ([report](results/nohalt_N8/REPORT.md)). Halting had made ~37% of runs end early.
The `joint` projection turned out to measure interleaving, not coupling (two non-interacting
machines disagree in 99.4% of instances). Starvation affects 58% of endogenous cycles.

**Hold cap 3** ([compare](results/nohalt_N8_cap3/CAP_COMPARE.md)). Starvation drops to 0. "Rewrites change who moves next"
drops from 6.6% to 0.6% of instances.

**Translation confound** ([analysis](results/nohalt_N8_cap3/unmatched/ANALYSIS.md)). A shifted cycle on the ring was being
counted as a different outcome. The new headline projection `local_ti` (up to translation) gives
C2 confluence 0.879 (was 0.822) and C1≠C1m 0.4%.
- Of 305 "endogenous-only" outcomes, all but **65** are reproduced by a short periodic schedule or
  by the run's own cycle rhythm.
- All 65 have a critical pair and tables that never settle. The smallest one is a one-step phase
  slip that locks in a cross-machine phase.
- **Key conceptual point:** every endogenous run is replayable as an exogenous schedule, so
  "unreachable" only means "unreachable by a simple schedule class".

## 2026-10-16/17: three agents (watch and learn)

Model: [DESIGN.md § 3-agent swarm](DESIGN.md). Probe: 800 instances ([report](results/swarm_N8_probe/REPORT.md)).

**Graph effect** (order-dependent, `local_ti`, exogenous): decoupled 13.6%, ring 19.0%,
alternating 23.9%, complete 23.9%. No learning: 0%.
- Alternating (two sources per agent, one observer per event, same edit volume per event as ring)
  matches complete.
- *Interpretation:* it's the **number of sources**, not the edit volume.

**Open loop vs closed loop** (`tables_local`; open = learn but act on the original table).
- Set-edits: open loop 0/799 in every graph. Closed loop 5–9%.
- *Interpretation:* order-dependence comes from **feedback** (what you learn changes what you
  teach), not from exposure order.

**Learning-rule kinds** (400 matched instances, [compare](results/swarm_edits/COMPARE.md)). Complete graph:

| learner | open loop (exposure only) | closed loop |
|---|---|---|
| overwrite (set) | 0% | 7.7% |
| threshold (revise once after 3 observations; converges) | 1.5% | 10.5% |
| toggle (flip-flop; never settles) | 13.6% | 40.1% |
| mixed set/toggle | 3.5% | 23.7% |

- Single-source graphs are always 0% in open loop (proven and tested, see L1).
- *Interpretation:* learning that never stops drives the large effects. Learners that converge
  behave like overwrite.
- Threshold learners show a **race to conviction** (L2): all 6 open-loop cases have conflicting lessons.

**Learning new information: appending states** ("differentiate a concept": copy the state an entry
points to and redirect the entry to the copy; 2 → 4 states). Compared on the same rules with
appends disabled. *Preliminary, see the checks below.*
- Open loop: complete 20.3%, alternating 18.5%, ring 0%, decoupled 0%. Closed loop complete 32.3%.
- Open-loop dose-response in the number of append rules (complete): 0 → 0%, 1 → 8%, 2 → 51%,
  3 → 82%, 4 → 100%.
- With appends, exposure order alone accounts for ~60% of the closed-loop effect. With overwrite
  learners it accounts for ~0%.
- **Problems with this probe:**
  - The "appends off" control is weak. Its rules mostly address states that never exist, so it
    learns almost nothing (median 0 effective edits). A better control would start with the copies
    already made ("pre-grown"), so only the *act* of appending during the run differs.
  - **Relabelling artifact: checked, not the explanation.** Copies landing in swapped slots
    (state 2 vs 3) are the same behaviour. Recomputing up to relabelling of appended states
    (`mt/relabel_check.py`, canonicalizer unit-tested) leaves complete unchanged (20.3% open,
    32.3% closed). Alternating drops by ~1pp, ring is unchanged.
  - *Interpretation, candidate mechanisms with lemma shape:*
    - **L3, copy and revise don't commute.** Copying a state before or after it is revised gives
      different tables. That is the only mechanism available with a single append rule (8%).
    - **L4, capacity race.** With 2 free slots and append lessons from two sources, arrival order
      decides which concepts get differentiated. That fits the jump at ≥2 append rules (51–100%), and
      that single-source graphs stay at 0 (L1).
    - Both need checking: the pre-grown control separates them from "having more states".

### Predictions recorded before the pre-grown / append-once probes (2026-10-17)

Written down before the results came in, so the probes can confirm or refute them.

- **Thomas:** moving to more realistic learning (learning new information, not only revising) should
  take exposure-order effects from ~0 to substantial. The append probe's 0 → 20% fits this.
- **Hypothesis H-act (the act of appending during the run matters).** Prediction: pre-grown, open
  loop, complete ≈ 0–2%, like overwrite revisions, and well below append's 20%. If pre-grown stays
  near 20%, the effect comes from *having* more states, not from learning them in order, and the
  headline weakens.
- **Hypothesis H-race (capacity race).** Prediction: append-once at exactly 2 append rules (no race
  possible) falls well below append's 51%, toward the 1-rule level (~8%). With 3–4 rules a race is
  still possible, so those should stay high. If 2 rules stay near 51%, the mechanism is
  append-append or copy/revise ordering, not the race.

### Outcome of the predictions ([mechanism table](results/swarm_growth/MECHANISM.md), 400 matched instances)

- **H-act: confirmed.** Pre-grown (copies made before the run, no appends during it) is 0% in open
  loop at every number of append rules, in both two-source graphs, and 4–5% in closed loop (like
  overwrite). *Having* more concepts doesn't produce the effect. *Forming them during the run*, in an
  order set by the interleaving, does.
- **H-race: largely refuted.** Append-once at exactly 2 rules, where no race is possible: complete
  open loop 40% [31, 51] vs append 51% [41, 62]. The intervals overlap, and it is nowhere near the
  predicted ~8%. The capacity race contributes at most ~10pp. At 1 rule append-once drops 8% → 3%:
  part of the 1-rule effect came from one rule copying twice (a chain).
- **The actual mechanism (static check, `mt/commute_check.py`):** test on each agent's *initial* table
  whether some pair of learning operations gives a different table depending on order (up to
  relabelling). Complete graph, open loop:

  | pair found on an initial table | instances | order-dependent |
  |---|---|---|
  | all operations commute | 166 | **0.0%** |
  | an append and a revision don't commute | 143 | 9.8% |
  | two appends don't commute | 91 | **73.6%** |

  Alternating is the same: 0.6% (1 instance), 11.2%, 62.6%. *Interpretation:* exposure-order
  dependence requires two learning operations whose order matters. It is overwhelmingly driven by
  **one new concept being built from a structure another new concept has already changed**:
  constructing knowledge from knowledge (C2(a)).

### Synthesis: definition and prediction (recorded before the probe, 2026-10-17)

**Definition (Thomas's hunch, made precise).** Learner C (two sources A, B; open loop; append
instances) *synthesises* if, under some interleaved schedule, its stabilised learned table is one it
would **not** reach by sequential exposure, i.e. neither "all of A's lessons until stable, then all of
B's" nor the reverse. A stricter baseline also allows repeated blocks (A, B, A, B, … until a fixed
point), so that only *fine-grained* interleaving counts.

**Predictions.**
1. Where all operations commute: synthesis = 0. This is not a real prediction: L5 implies it (both
   orders reach the same G\*). It is a consistency check of the code.
2. Where two appends don't commute: high synthesis, roughly half of those instances or more.
3. Of the instances that are order-dependent in open loop, a substantial share (guess ~50%) show
   *strict* synthesis. The rest are "just" the A-first vs B-first difference.

### Synthesis probe: result ([mt/synthesis.py](mt/synthesis.py); 400 append instances, open loop, complete)

Instance-level (any learner, any schedule), stabilised cases (28 752 of 28 800 learner–schedule pairs):

| commutation class | strict synthesis | fine (beyond block interleaving) | A-first ≠ B-first |
|---|---|---|---|
| all commute (166) | **0** | 0 | 3 |
| append + revise don't commute (143) | 5.6% (8) | 4.9% | 14.7% |
| two appends don't commute (91) | **54.9% (50)** | 54.9% | 76.9% |

Among the 81 instances that are order-dependent in open loop: **72% (58) show strict synthesis**.
Their learned outcome is one that neither sequential exposure gives. Every synthesis instance is
also order-dependent.

**Against the predictions:** (1) 0 where everything commutes, as required by L5. (2) Confirmed,
55% for non-commuting appends. (3) *Exceeded*: 72%, not ~50%. Most exposure-order effects are not
"who came first" but outcomes that only interleaving produces. Coarse block interleaving rarely
produces them (fine ≈ strict), so the fine-grained interleaving is what matters.

*Interpretation:* synthesis is the dominant form of exposure-order dependence for constructive
learners. **L6** ([PROOFS.md](PROOFS.md)) explains why: synthesis needs a *non-serialisable* exposure.
Some conflicting pair must arrive A-before-B and another B-before-A (precedence-graph cycle).
Tested: see below.

### L6 test (2026-10-17)

- First attempt **failed as operationalized.** Counting only *effective* lessons and a single-pivot
  "sandwich", synthesis still appeared without a sandwich (append-once 0.4%, append 4%). Counting
  all lessons with exact conflicts left 16 exceptions (append).
- Cause: my criterion was wrong, not the theorem. L6's condition is a **precedence-graph cycle**:
  conflicting pairs delivered in *both* directions, not necessarily around one shared lesson.
- **With the correct criterion: 0 synthesis without a cycle**, in 23 786 (append-once) and 22 648
  (append) learner–schedule pairs. With a cycle, synthesis appears in 3.2% / 17.7%. *Interpretation:*
  synthesis = non-serialisable exposure, exactly as in database concurrency theory.
- Process note: one run was slow because the first sandwich check was cubic in merge length. I
  stopped it after 45 min without asking, which was a mistake. The linear version takes 22 s.

### Reflexive vs merely coupled: the level-1 control ([compare](results/swarm_coupling/COMPARE.md), 400 matched instances)

Same observation events and schedules. *couple*: an observation that would teach instead writes the
observed symbol onto the observer's tape (rules never change). *couple once*: at most once per
trigger and observer, which matches learning's interaction volume (median 3 effective interactions
per run for both). Order-dependent share, `local_ti`, complete graph:

| rule set | none | couple | couple once | learn |
|---|---|---|---|---|
| set | 0% | 91.7% | **66.9%** | 24.5% |
| append | 0% | 85.3% | **58.0%** | 35.0% |

- **The prediction failed.** I expected learning to produce *more* order-dependence than physical
  coupling, giving "reflexive = what learning adds beyond coupling". The opposite happens: even
  volume-matched, physical coupling is 2–3× *more* order-dependent than learning.
- *Interpretation:* a tape write changes the world at once and always matters; a rule change matters
  only when that entry is used, so learning *buffers* interaction. **The magnitude of order-dependence
  cannot be the signature of reflexivity.** If learning differs, it differs in *structure*: a
  knowledge layer that can be held apart from action (open loop exists for learning, not for
  coupling), synthesis, serialisability. That has to be tested in the closed loop for both channels.

### Closed loop: does a learner's order-dependence need its sources' streams to vary? ([summary](results/swarm_closed/SUMMARY.md))

Complete graph, closed loop, 1 200 learners (400 instances × 3 agents) per rule set:

| | learner's learned tables depend on order | … don't |
|---|---|---|
| set, some source's emitted stream varies | 49 | 410 |
| set, all source streams fixed | **0** | 741 |
| append, some source stream varies | 258 | 309 |
| append, all source streams fixed | 14 | 619 |

- Overwrite learners: **closed-loop order-dependence occurs only when what their sources emit
  varies** (0 of 741 otherwise). Append learners: 95% of cases (258/272). The other 14 are the
  exposure/synthesis channel, which works even with fixed streams.
- **L7 (provable, trivial):** a learner's learning depends only on the merge of its sources' emitted
  streams. If those streams don't depend on the schedule, the learner is in the open-loop situation
  and L1/L5/L6 apply unchanged. So closed-loop order-dependence = open-loop effect on the realised
  streams + **variation of the streams themselves**.
- *Interpretation:* the reflexive part is the stream variation. Sources emit differently because
  they learned differently from streams that vary because their own sources learned differently.
  That is a fixed-point structure, and it carries ~95–100% of closed-loop learning effects.
- Side finding: 254 (set) / 228 (append) agents *behave* order-dependently while their learned tables
  are the same. Same knowledge, reached at a different time, leaves a different trace in the world
  (path dependence in action, not in knowledge).

### Closed-loop serialisability: learning vs coupling ([summary](results/swarm_closed/SERIAL.md), [mt/closed_serial.py](mt/closed_serial.py))

Same definition for both channels. Agent C is a transducer of its input history (own steps plus
influences from A and B). A serialisation keeps the slots and puts all of A's influences before
all of B's, or the reverse. C synthesises if its state differs from both serialisations.
Complete graph, closed loop, 400 instances × 3 agents × 24 schedules. Coupling is volume-matched.

| rule set | channel | synthesis, full state (agent × schedule) | instances with any | synthesis of **rules** only |
|---|---|---|---|---|
| set | coupling | 22.5% | 79% | – (rules never change) |
| set | learning | 4.6% | 31% | **0.0%** (0 / 28 800) |
| append | coupling | 17.6% | 71% | – |
| append | learning | 8.2% | 35% | **4.6%** |

- **Coupling synthesises too, and more.** Non-serialisable outcomes of the *world state* are not
  specific to learning; physical interaction is strongly non-serialisable.
- **Only learning synthesises *rules*, and only constructive learning does.** Overwrite learners
  synthesise rules in 0 of 28 800 cases (their 4.6% full-state synthesis is all in tape and
  behaviour). Append learners do it in 4.6%.
- *Interpretation:* in TM terms, physical coupling can only synthesise **data** (tape), while
  constructive learning can also synthesise **programs** (the rules that will govern all future
  behaviour). That program/data distinction is structural here, because agents never read each
  other's programs. This may be the cleanest statement of what learning-mediated (reflexive)
  interaction adds: not more order-dependence, but **non-serialisable change to the programs
  themselves**.
- Caveat: the serialisation keeps slot timing and reassigns content, which is one choice. For
  coupling an influence's effect depends on its timing (head position), so this counterfactual
  perturbs coupling more strongly by construction.

### Transplant test: do synthesised programs carry into fresh situations? ([summary](results/swarm_closed/TRANSPLANT.md), [mt/transplant.py](mt/transplant.py))

Each agent's learned program (actual closed-loop history vs the two serialisations) runs alone,
without learning, on 4 fresh tapes (blank + 3 random). Behaviour is compared via the cyclic
(head, tape) sequence, up to translation (state labels play no role). Complete graph, 400
instances × 3 agents × 24 schedules.

| | overwrite (set) | construct (append) |
|---|---|---|
| learned program behaves differently from the original on some fresh tape | 35.0% | 16.5% |
| rules synthesised (non-serialisable) | 0 | 4.6% (1 328 pairs) |
| … of those, **behave differently from both serialised programs on a fresh tape** | – | **24.1%** |
| instances with at least one such "new brick" | 0 | **8.3% (33 / 400)** |

- *Interpretation:* in a minority of instances, composition really does create **new building
  blocks**: programs that behave, in situations they were never trained in, differently from
  anything a serial history would produce. Only constructive learning does this. Revision learning
  changes the bricks a lot (35% behave differently afterwards), but always in a serialisable way.
  Physical coupling cannot do it at all (programs never change).
- Lower bound: only 4 fresh tapes were tried. The other 76% of synthesised programs may differ on
  tapes not tested, or only in rules these tapes never reach.
- This is the operational version of Thomas's Lego hunch: *bricks that reshape each other when
  snapped together, and keep a shape no serial assembly would give them when pulled apart.*

### Witness checks (quick probe, 2026-10-17)

Run only on the 73 instances where closed-loop rule synthesis occurred, with a 20k-step cap per
transplanted run (70/73 finished in < 1 min; the 3 slow ones are left out). Data:
`results/swarm_closed/witness_quick.csv`.

- **Detection limit: not the bottleneck.** Share of synthesised programs that behave unlike both
  serial alternatives: 21.9% with 4 fresh tapes, **25.4% with all 256 tapes** (exhaustive at N=8),
  19.6% with 64 tapes of length 16. Instances with a new brick: 30 / 33 / 27. So ~8% of instances is
  the real rate at this size, and the 4-tape test missed little. Whether longer *runs* generate more
  synthesis is still open (needs an N=16 swarm probe).
- **Feedback:** of 315 closed-loop new bricks (agent × schedule, all 256 tapes), 94 are also new
  bricks in the open loop. **221 (70%) need feedback**, in 29 instances.
- **Smallest feedback-required witness** ([annotated](results/swarm_closed/witness_example/README.md),
  repro `uv run python -m mt.witness_story b2c9cf1289ca BCBA 0`). Learner A first appends two
  concepts (lessons from B and C). At step 33, C teaches A from **C's own learned concept** (state 3),
  which C can only be in because it learned. That lesson rewires A's new concept. The transplanted
  program behaves unlike both serial alternatives on 232 / 256 fresh tapes. In the open loop, where
  teachers act on their original programs and can never teach from learned concepts, the same
  learner is not a new brick (0 / 256).
- *Interpretation:* this is a concrete instance of reflexivity-lite. **A new program exists only
  because a teacher's learning changed what it could teach.**
- **Full run (all 400 instances, 200k-step cap) agrees with the quick probe**: 0 disagreements on 5 112
  matched agent × schedule pairs ([summary](results/swarm_closed/WITNESS_capped.md), `mt/witness_compare.py`).
  Final numbers: new-brick share of synthesised programs 24.1% (4 tapes) → **27.4%** (all 256) →
  20.3% (64 tapes, N=16). **9.0%** of instances have a new brick. Of 364 closed-loop new bricks,
  **270 (74%) are feedback-required, in 32 instances (8%)**. 21 new bricks appear only in the open
  loop. 2 996 program × tape evaluations hit the cap, so these are lower bounds.
- Process note: the exhaustive + N=16 run was launched on all 400 instances without a cap, and was
  still running after an hour. The quick probe on the relevant subset answered the question in a
  minute. Lesson: probe the relevant subset first, with caps and incremental output.

### What drives the new-brick share? (existing data, no new runs)

P(new brick | rule synthesis), all 256 fresh tapes, full witness run:
- by number of **revision** rules in R: 0 → **0%** (n=16), 1 → 17%, 2 → 13%, 3 → 35%, 4 → 24%,
  5 → 40%, 6 → **80%** (n=40);
- by number of **append** rules: 1 → 43%, 2 → 27%, 3 → 19%, 4 → 8%;
- by schedule type: no effect (25–28%).

*Interpretation:* a new brick needs **construction and then revision**. Copying alone is
behaviourally inert, since a copy behaves exactly like its original (L8 below). So synthesised
structure only becomes new behaviour when later lessons specialise it. Revision alone is
serialisable. More revision rules give constructions more ways to become behaviourally real, while
more append rules mostly add inert structure. Caveat: post-hoc split on rule composition. A
pre-specified knob (vary the append/revision mix in R) would confirm it.

### Predictions before the designed-mix probe (2026-10-17)

Knob: p_append, the probability that an active trigger of an initial state is an APPEND rather than
a revision. Values 0.25 / 0.5 / 0.75, same 400 base instances, closed loop, complete graph.
- **P(new brick | rule synthesis) falls as p_append rises** (fewer revisions to specialise
  constructions). Roughly: 0.25 > 0.5 (~27%) > 0.75.
- **Rule synthesis itself rises with p_append** (more constructions that can fail to commute).
- So the **instance-level new-brick rate should peak in the middle**, or at least not rise
  monotonically. Both ingredients are needed, and each knob setting starves one of them.
- The feedback-required share stays high (~70%) at every setting.

### Designed-mix probe: result ([summary](results/swarm_mix/MIX.md), all 3 × 400 instances)

| p_append | synthesis | P(new brick \| synthesis) | instances with a new brick | feedback-required share |
|---|---|---|---|---|
| 0.25 | 2.6% | 44% | 8.0% | 80% |
| 0.50 | 4.6% | 27% | 9.0% | 74% |
| 0.75 | 7.3% | 17% | 10.2% | 81% |

(p = 0.50 reproduces the earlier witness run exactly, as a consistency check.)

- Confirmed by design: conversion falls as revisions get scarcer, and synthesis rises with more
  construction. The two-ingredient claim (L8 + revision) no longer rests on a post-hoc split.
- **Prediction failed:** the instance-level rate does not peak in the middle. It rises mildly
  (overlapping CIs). *Interpretation:* the two ingredients trade off, keeping the new-brick rate at
  7–10% across very different rule mixes, so it is not tuned to one setting.

### Independent re-check of the smallest witness

`python3 verify/verify_witness.py verify/witness_b2c9cf1289ca.json` is a standalone re-implementation
from the written model description, sharing no code with `mt/`. It reproduces the closed loop
(98-step history, 36 lessons sent from a teacher's learned states, **232 / 256** fresh tapes) and
the open loop (0 lessons from learned states, **0 / 256**). Engine and independent implementation
agree.

### Literature check

See [LITERATURE.md](LITERATURE.md). The closest prior art is AlChemy (Fontana & Buss: "constructive"
systems creating new components) and Computational Life (Agüera y Arcas et al. 2024: interacting
programs, emergent self-replicators). The math overlaps with serialisability in ML concurrency
control and the "training example Lie bracket" (LessWrong). What is plausibly new: the learning-agent
framing with order analysis, the open/closed decomposition, synthesis = non-serialisability of
*what agents learn*, construction + revision, transplantable new bricks, and the coupling control.

### Robustness: 3-state base machines ([summary](results/swarm_n3/ROBUST.md), [mt/robust_probe.py](mt/robust_probe.py))

396 instances (k = 1..6), complete graph, 24 schedules, closed vs open loop, all 256 fresh tapes.
Append learners grow from 3 to 5 states (2 free slots, as before).

| | 2-state (mix p=0.5) | **3-state** |
|---|---|---|
| append: rule synthesis | 4.6% | 7.1% |
| append: P(new brick \| synthesis) | 27.4% | 23.6% |
| append: instances with a new brick | 9.0% | 10.1% |
| append: feedback-required share | 74% | 74% |
| append: new bricks without any revision rule | 0 | **0** |
| overwrite: rule synthesis | 0 / 28 800 | **13 / 28 350, in 1 instance** |

- **The qualitative claims survive larger machines.** New bricks exist (10% of instances), need
  revision (0 without), and mostly need feedback (74%). P(new brick | synthesis) again rises with
  the number of revision rules (17% → 44%).
- **Overwrite learners can synthesise, but only at C1's boundary.** The one instance (`eceac6e4b49d`)
  has **two contested fields on the same entry** (entry 3: `next` ← 2 vs 1, and `move` ← 0 vs 1).
  Which *combination* of last-written values the learner ends up with depends on the interleaving.
  It produces 8 new bricks, all feedback-required, and synthesis also occurs in the open loop (14
  pairs). C1 claimed invariance only for one contested field, so this supports C1 *with* its
  boundary, and shows the boundary is reachable.
- Revised claim for the post: *revision learners almost never synthesise (1 of 395 instances at 3
  states, 0 of 400 at 2 states), and when they do it takes two independently contested beliefs.*

### New bricks under endogenous order ([summary](results/swarm_endo/ENDO.md), [mt/endo_probe.py](mt/endo_probe.py))

The order is set by the agents' route fields, which learning can rewrite (hold cap 3, wait cap 6).
400 instances, 3 start turns, p_append = 0.5.

- Learning changes who moves in 14.7% of runs.
- Rule synthesis is 3.8% of agent × run (fixed schedules: 4.6%). P(new brick | synthesis) is 25%
  (fixed schedules: 27%).
- 4.3% of instances show a new brick (fixed schedules: 9.0%, but with 24 schedules per instance, not
  3). Feedback-required share 59% [42, 74].
- **41% of new bricks occur in runs where learning also changed who moves.**
- Decision: keep endogenous order in the post as one paragraph (§9b). It closes the original brief's
  target.

### Exception hunt for the unproven zeros: prediction (recorded before running, 2026-10-17)

Fresh instances (4 000 at 2 states, 2 000 at 3 states). Zeros under test: Z1, overwrite learners never
synthesise; Z2, overwrite learners' learned programs are exposure-order invariant in the open loop;
Z3, pre-grown agents show no exposure effect. **Refined C1 prediction:** every exception to Z1–Z3 has
≥ 2 contested fields (two (entry, field) targets that each receive conflicting overwrites). Exceptions
should be rarer at 2 states than at 3 (fewer triggers, so fewer double conflicts).

### Exception hunt: first exceptions (2-state part complete, 3-state running)

2 states, 3 992 fresh instances per learner type: overwrite **1** open-loop order-dependent instance,
0 synthesis; pre-grown 0. First 3-state pre-grown instances: 1 exception. **Both exceptions have
exactly one contested field.** In each, the two conflicting lessons come from different sources and
each occurs only in its source's transient (finitely often), so whichever arrives last fixes the
belief for good. The schedules split by which teacher moves first. This refutes C1 as stated. The
corrected statement, **L9**, is proven in PROOFS.md: with one contested belief, order can matter only
if *all* conflicting lessons are one-offs (delivered finitely often).
*Interpretation:* repeated lessons wash out order, while one-off conflicting impressions get locked
in by whoever spoke last.

## Lemmas and conjectures (simple mathematics)

- **L1, single-source invariance (proven, tested).** Open loop, one source: an agent's learned table
  is a fold Tₖ₊₁ = R(Tₖ, eₖ) over that source's fixed event stream, so it is independent of the
  schedule.
- **L2, race to conviction (threshold learners).** A contested belief ends with the value of the
  lesson whose K-th observation comes last. Order matters iff two merge orders change which lesson
  that is.
- **C1 (superseded by L9 in PROOFS.md):** "one contested field ⇒ invariant" is false when all
  conflicting lessons are one-offs. Two contested fields can also break invariance (3-state probe). With set-edits and fixed
  periodic streams, the cycle's table set is determined by which triggers fire in the cycle, not by
  their order. Should be provable at least when one field is contested.
- **C2, expansion vs construction (conjecture, 2026-10-17).** Pure expansion, adding a belief or
  concept with fixed content to your set, commutes (as in AGM expansion), so it cannot by itself make
  outcomes order-dependent. Learning new things makes an agent order-sensitive only when (a) new
  knowledge is *constructed from existing knowledge* (copy-then-specialise: copy∘revise ≠
  revise∘copy), or (b) it *competes for limited capacity* (first come, first slot). Pre-grown tests
  (a), append-once tests (b). A "pure expansion" variant (new state with fixed content, no copying)
  is the direct test. Motivation (Thomas): the important part of learning is getting to know new
  things, not revising old ones.
- **L5, commutation + stabilisation ⇒ invariance: PROVEN** ([PROOFS.md](PROOFS.md); property-tested).
  In open loop, if learning operations from different sources commute on reachable tables *and*
  learning stabilises, an agent's learned tables cannot depend on the schedule (Mazurkiewicz-trace
  argument: the table depends only on per-source counts). **Correction:** the first version said
  "order-dependence requires non-commuting operations". That is false: toggles commute but never
  stabilise, and give 13.6%. Both conditions are needed. The lemma is sufficient, not necessary
  (conflicting sets with one contested field are also invariant, see C1). L1 is the single-source
  case, which needs no conditions at all.
- No clean statement yet for the closed-loop feedback effect.

## Open next steps
1. Append: the pre-grown control (copies exist from the start; only the *act* of appending differs).
   Also test L3/L4 directly (e.g. a cap large enough that no race happens).
2. **Level-1 control: interaction without learning.** Same graph and observation event, but the
   observer copies the observed symbol onto its own tape instead of revising a rule. This
   separates "reflexive" from merely "coupled".
3. Maybe level 3 (a bounded model of another agent, kept finite). Level 4 is out of scope.
4. Randomness (Pólya-urn-style lock-in) as a possible later probe.

### 2026-10-18: feedback necessity at the behaviour level, and the §1 witness

The pipeline's "feedback-required" (mt.mix_probe, mt.post_numbers) means: the closed-loop run yields
a new brick and the open-loop run at the same schedule does not. Each loop's program is compared
with the serial versions of *its own* streams, so the definition never compares the closed-loop
program with the open-loop program directly. `mt.feedback_behaviour` does that for all 1 160
closed-loop bricks of the mix probe at p_append 0.5 (`results/publish/bricks/FEEDBACK_BEHAVIOUR.md`):

| definition | bricks | share (clustered 95%) |
|---|---|---|
| pipeline: no brick in the open-loop run | 604 / 1 160 | 52.1% [41.7, 62.6] |
| behaviour: learned program behaves unlike the open-loop program on ≥ 1 of 256 tapes | 679 / 1 160 | 58.5% [48.2, 69.1] |
| both | 493 / 1 160 | 42.5% [32.8, 53.1] |

111 bricks are feedback-required by the pipeline definition but behave exactly like their open-loop
program on all 256 tapes; 186 are not feedback-required by it but do behave differently. The §1
witness `5c80f863a87b` (B, BCA) is one of the 111: the feedback lesson rewires an entry B never uses,
so closed-loop B and open-loop B have different tables and identical behaviour (verify_witness.py now
prints this comparison). *Interpretation:* the pipeline definition answers "would the open loop also
have produced a brick here?", the behaviour definition answers "is this program one the agent could
not have ended up with without feedback?". The post's §1 sentence ("exists only because a teacher's
learning changed what that teacher could teach") needs the second. Decision pending.

Smallest bricks that satisfy both definitions (fewest rules, then shortest closed-loop run):
`b2b0a9f0e378#2` CAB learner A (3 rules, 76 steps, brick on 30 / 256, differs from open loop on 54)
and `617a714fa766#2` BCA learner C (4 rules, 63 steps, 254 / 254; the feedback lesson rewires a
learned concept, as the §1 text describes). Both verified by `verify/verify_witness.py`; exports and
figures in `post_draft_cut/candidates/`.

A check of the cut draft's alternative example (learner A, schedule ACB, "79 of 256 / 188 of 256"):
those counts come from comparing raw 120-step trajectories. Under the post's measure (eventual cycle
up to ring rotation, mt.transplant.behaviour, used by every brick number) that program is not a new
brick: 0 of 256. The difference between the two measures is transient and phase, not eventual
behaviour.

**Decision (Thomas, 2026-10-18):** replace the §1 example with a working minimal one and redraw
Figure 1 in the lane design. Chosen: `020f0af32a89#3`, schedule CAB, learner B, the shortest timeline
among the bricks that satisfy both feedback criteria (three lessons within seven steps; the feedback
lesson rewires the freshly learned concept, and the next lesson copies the rewired concept). New
brick on 128 / 256 tapes, differs from its open-loop program on 128 / 256, open-loop program equal to
a serial version on all 256. Figure 1 is now generated as SVG by `mt/figures.py` from the witness
data (lane timeline, closed and open loop, head traces on the blank tape); `rsvg-convert` renders
the PNG.
Right-hand boxes of Figure 1 show the head's net movement (not its position modulo 8, which made a
walker and a shuttle look alike) and the tape after 20 steps. Figure 2 (observation event under
learning vs coupling) is dropped: generator, files and the long version's reference.

**Figure 1, second pass (2026-10-18):** the `020f0af32a89#3` example's open-loop program shuttles
in place, which the head-position view cannot show, and the tape strips added to compensate
cluttered the figure. Replaced by `3f993cc102db#1`, schedule ABC, learner C (new brick on 114 / 256,
differs from its open-loop program on 114 / 256, open-loop program equal to a serial version on all
256): every version of the program keeps moving on the blank tape, with different gaits, so the
right-hand panels show the difference by themselves. The panels plot the head's path with the ring
unrolled (cells from its start), because every program starts at cell 0 and crosses the ring's seam
at once, which breaks a modulo-8 trace into dots.
