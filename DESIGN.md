# Mutual-rewrite Turing machines: design notes

Exploratory tool. Nothing here is a proof. Every number this tool produces is
a count over a finite sample at a finite budget.

## Plan

- **M1 (this milestone):** 2-state machines, bounded circular tape N=8, all
  four conditions plus the matched controls below. Random sample of
  instances, stratified by rewrite-rule size. Results table, report,
  witnesses, tests.
- **M2 (done):** N=16, 32 on the same instances. Result: `results/m2/COMPARE.md`. The rates are
  N-invariant in this sample.
- M3: unbounded tape with a step budget (halted / exact repeat / UNRESOLVED).
- M4: 3-state machines. State relabeling becomes a real symmetry here.

## Model

| thing | encoding |
|---|---|
| states | `0..n-1`, start state `0`, plus an absorbing halt state `H = n` |
| alphabet | `{0,1}`, blank `0` |
| table entry `e = 2q + r` (state `q`, read `r`) | 4 fields: `write ∈{0,1}`, `move ∈{L,R}`, `next ∈{0..n-1,H}`, `yield ∈{0,1}` |
| rewrite rule R | map from trigger `(q, s_written)` (2n triggers) to either *no-op* or one edit `(entry, field, value)`. That gives `2n(n+7) + 1` options per trigger (for n=2: 36 edits + no-op) |
| tape (bounded) | circular, length N, stored as an N-bit int; head starts at 0 |
| full config | `(stateA, headA, tapeA, tableA, stateB, headB, tapeB, tableB, ctrl)`, where `ctrl` is whose turn it is (endogenous) or the schedule phase (exogenous) |

One **step** is one transition by one machine. Suppose machine X in state q
reads r. X writes, moves and changes state using its own table, then
`R(q, written)` is applied to the *other* machine's table. In self-mod mode
it is applied to X's own table instead. X never reads the other machine's
table, tape or state.

## Conditions run on every instance

| id | condition | runs |
|---|---|---|
| C1 | mutual rewrite, endogenous order | 2: start turn A, start turn B |
| C1m | **added control:** like C1, but edits that target `yield` bits are dropped | 2 |
| C2 | mutual rewrite, exogenous schedules | 14 |
| C3 | rewriting off (tables fixed), same exogenous schedules | 14 |
| C3e | rewriting off, endogenous order (yield bits fixed) | 2 |
| C4 | single self-modifying machine (A alone, B alone, same R applied to self) | 2 |

Exogenous schedule words, each repeated cyclically: `ABAB, BABA, AAB, BBA,
ABB, BAA`, plus 4 seeded random words of length 12 together with their A↔B
swaps, which makes 8 more.

## Modeling decisions you didn't specify (my choice in bold)

1. **Halting.** *Revised:* **off by default** (`--halt` turns it back on). HALT is never a
   `next` value, in tables or in R's edits, so every run cycles or is unresolved. The original
   choice, HALT drawn as one of three equally likely `next` values, made ~37% of runs halt within a
   few steps, which diluted the dynamics. `results/m1` and `results/m2_*` were sampled *with*
   halting. `results/nohalt_N8` was sampled without it. When halting is on, H is absorbing, the
   system halts when both machines are in H, a halted machine's exogenous slot is a no-op, and in
   endogenous mode the turn passes to the live machine.
2. **R's trigger.** `(q, s)` = **pre-transition state, symbol written**. R
   is **one map shared by both directions**. A shared R is required for the
   A↔B swap symmetry to hold.
3. **Edit semantics.** **Set-to-value, applied immediately** after the
   transition, before anyone moves again. Set-edits are idempotent, so
   order-dependence of the *tables* can only come from two triggers that
   target the same (entry, field) with different values. That is a
   "critical pair" in rewriting-theory terms. The report splits on this.
4. **"Smallest R."** **R size `k` = number of non-no-op triggers (1..4)**.
   Instances are stratified by k. With k=1, each table can change at most
   once.
5. **Endogenous turn rule.** After X's transition, X keeps the turn iff the fired entry has
   `yield=0` and X did not just halt. Initial yield bits are random. *Revised:* the rule now takes
   an optional **hold cap** (`--hold-cap`): X is forced to pass after that many consecutive
   transitions. Without a cap, a machine that never yields starves the other, which happened in
   ~58% of no-halt endogenous cycles. `results/nohalt_N8_cap3` uses cap 3, the smallest cap at which
   yield bits still matter (cap 1 is exactly ABAB). The cap is part of `ctrl` (turn + 2·held),
   so repeat detection stays exact. Trade-off: a cap is itself a partly exogenous rule.
6. **Yield bits in exogenous runs.** **Present and editable, but ignored for
   ordering.** This keeps C1 and C2 on literally the same state space.
7. **Initial config.** **Both tapes blank, heads at 0, both in state 0.**
   One initial config per (A, B, R).
8. **Random schedules are made periodic** (see pushback 2).
9. **Outcome equivalence is reported at three projections** (see pushback 3):
   - `joint`: the set of cycle configs with `ctrl` dropped.
   - `local`: the pair (set of A-local configs, set of B-local configs) over
     the cycle, where local = (state, head, tape, own table). **Headline.**
   - `tables`: the set of (tableA, tableB) pairs visited in the cycle.
   - plus `class`: halt vs cycle.

   A halted run's outcome is its single final config, projected the same way.
10. **Budget.** **200 000 steps per run** even on the bounded tape (see
    pushback 4). If any exogenous run of an instance is unresolved, that
    instance's confluence is *undetermined*. It is excluded from rates and
    counted separately.
11. **Sampling instead of enumeration** (see pushback 5). Machines and R are
    sampled uniformly at random (`next` uniform over {0,1,H}), canonicalized,
    and de-duplicated. Rates come with Wilson 95% intervals.
12. **Traces.** The full config is *hashed* every step for exact repeat
    detection: a dict keyed on the full config tuple, so there are no hash
    collisions. Full step-by-step traces are *written to disk* only for
    witnesses, by deterministic re-run.

## Pushback: places where the spec is ill-posed or needs a decision

1. **Endogenous order does not escape the skeptic.** With the turn bit in
   the config, C1 is one deterministic system with exactly one run per
   initial config. So "confluence rate" is undefined for C1 and for C4. What
   *is* measurable for C1:
   (a) whether its outcome matches *any* exogenous outcome,
   (b) whether it depends on who starts, and
   (c) **whether letting R edit yield bits changes the outcome compared with
       C1m.** C1m is endogenous order with the yield edits removed.
   (c) is the cleanest operationalization of "the rewrites themselves
   influence who moves next". Without C1m, any C1-vs-C2 delta mixes
   "order is state-dependent" with "order is rewrite-dependent".
2. **Seeded random schedules break exact-repeat detection.** An
   aperiodic schedule makes the system non-autonomous, so configs need not
   repeat and "the outcome" is undefined. Fix: each seed generates a
   random word, which is then repeated. The phase is part of the config.
3. **Comparing cycles across schedules is trivially "different" if done
   naively.** `ctrl` differs by construction. Even with `ctrl` dropped,
   schedules like ABAB and AAB interleave two *independent* machines
   differently, so the joint cycle sets differ with no interaction at all.
   C3 measures this: it is a pure interleaving artifact. The `local`
   projection is invariant under schedule for C3 by construction (each
   machine's own trajectory is unaffected), and there is a test for it. So
   `local` non-confluence in C2 can only come from the coupling. That is why
   `local` is the headline. `joint` is reported for completeness, next to its
   C3 baseline.
4. **"Bounded ⇒ measure exactly" is true only in principle.** The config
   space includes both tables (~10¹¹ table pairs for n=2), so the
   guaranteed repeat bound is astronomically large. In practice runs repeat
   quickly, but the budget still applies, and unresolved runs are reported.
5. **Exhaustive enumeration is out of reach even for n=2.** There are
   24⁴ ≈ 3.3·10⁵ machines (with yield bits), ≈ 10¹¹ ordered pairs, and
   37⁴ ≈ 1.9·10⁶ rules. Canonicalization is still implemented and tested, but
   for sampling it only de-duplicates.
6. **Symmetries actually available.**
   - **A↔B swap: valid only because** the schedule set is closed under swap
     (that is why BBA, BAA and the swapped random words are added) and C1
     runs from both start turns.
   - **L↔R mirror: a valid symmetry you didn't list.** The circular tape is
     mirrored about cell 0.
   - **Symbol complement: *not* a symmetry here**, because the blank-0
     initial tape is fixed. It would map onto blank-1 instances, which are
     never run.
   - **State relabeling: trivial at n=2**, because the start state is
     pinned to 0. At n=3 it is the swap of states 1 and 2. That case is
     implemented and tested.
7. **"Self-modifying machines settle into period-1 cycles."** On a circular
   tape where the head moves every step, the *full* config can never have
   period 1 unless it is halted. The claim must be about the *table*
   settling: the table is constant over the cycle. C4 reports both.
   I don't know which paper you mean. Please send the citation so I can
   match its exact setup.
8. **The rewrite-equivalence test is true by construction.** It is a
   regression test on two independent implementations, not evidence. Its
   conceptual content is still worth stating in the post: "A rewrites B"
   ≡ "B is a transducer reacting to A's output channel". So mutual rewriting
   is just two coupled finite-state transducers.

### Observability assumption (for the equivalence property)

B's self-rewrite view is identical to A rewriting B **iff**, after each
A-transition and before any other transition, B receives the pair
`(A's pre-transition state, symbol A wrote)`. Delivery must be lossless,
in order and synchronous. B needs nothing else: not A's table, tape, head
or post-state. If observation were delayed by even one step, the two views
would diverge whenever the other machine moved within that step.

## 3-agent swarm (mt/swarm.py)

Motivation: with 2 agents, each table has exactly one writer and "who moves next" is one bit, so
two plausible sources of reflexive order-dependence can't exist: conflicting updates from two
observed agents, and routing. Self-rewrite was rejected as a stand-in, because a table only its
owner rewrites folds into a larger state set and is just an ordinary machine.

Modeled as agents that **watch each other and learn**. When agent X transitions (pre-state q, writes
w), every agent that observes X applies the shared, anonymous rule R(q, w) to *its own* table. No
agent ever modifies itself on its own initiative, and none reads another's table.

Decisions (user-confirmed 2026-10-16):
- **Observation graphs, all on the same instances:** ring (one source per agent), complete (two
  sources), and decoupled (A↔B, C isolated: a sanity check that must reproduce the 2-agent model,
  enforced by a test).
- **Learning rule:** one anonymous R shared by all agents. It reacts to what is seen, not to who did it.
- **Endogenous order:** the 4th entry field is a *route* (keep / pass to next agent / pass to
  previous agent), which R can rewrite. Hold cap 3: a forced pass goes to the longest-waiting agent.
  Wait cap 6: an agent that has waited 6 moves gets the turn. This prevents two agents locking out
  the third, at the price of a partly exogenous fairness rule. How often each cap fires is reported.
- **Exogenous schedules:** ABC, AABC, ABAC and one random length-12 word, each closed under all 6
  relabellings (24 schedules). Route bits are inert there and stripped from outcomes.
- **Controls:** no learning (F_exo, F_endo); route edits masked (Lm_endo).
- **Canonicalization:** mirror only. Agent relabelling is a symmetry of ring and complete (tested),
  but not of the decoupled graph, which runs on the same instances.
