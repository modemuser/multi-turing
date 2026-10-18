# Lemmas with proofs

These are statements about the **open loop**: agents learn, but act on their original tables, so
every agent's emitted event stream is fixed and doesn't depend on the schedule. They concern the
outcome `tables_local`: the set of tables an agent holds during the eventual cycle. Simulation
counts in [NOTEBOOK.md](NOTEBOOK.md) are evidence; the counts quoted below are from the published run
(`results/publish/`, see [PROVENANCE.md](PROVENANCE.md)) unless marked exploratory. What follows are
proofs, within this model only.

## Setup

- Learner Y has sources X₁, …, X_s. Source Xᵢ emits a fixed, eventually periodic stream
  wᵢ = aᵢ₁ aᵢ₂ … of events (pre-state, symbol written). In open loop wᵢ depends only on Xᵢ's own
  table, never on the schedule.
- A schedule σ induces a **merge** m_σ: the sequence of events Y receives, an interleaving of the
  wᵢ (or of the sub-streams routed to Y, for `alternating`). Within each source the order is preserved.
- Each event a acts on Y's learned table by a map f_a : 𝒯 → 𝒯 (𝒯 finite; for threshold learners
  the evidence counters are part of the state). After k received events,
  T_k = f_{m_k} ∘ … ∘ f_{m_1}(T₀).
- **Fairness:** every source delivers infinitely often under every schedule we use. Exogenous words
  contain every letter; the wait cap guarantees it for endogenous order.
- **Outcome:** O_σ(Y) = { T_k : k in the periodic regime of the joint run }.

## L1, single source: invariance (always)

*If s = 1, O_σ(Y) is the same for every schedule σ.*

**Proof.** With one source, m_σ = w₁ for every σ: only the timing of deliveries changes, not their
order. So the sequence (T_k) is the same sequence for every σ, and the set of its values in the
eventual period is a property of that sequence alone. ∎

This needs no assumption on the f_a. That's why toggles, appends and conflicting sets all give
exactly 0% on `ring` and `decoupled` in open loop.

## L5, commutation + stabilisation ⇒ invariance (corrected 2026-10-17)

Let 𝓡 ⊆ 𝒯 be the set of tables Y can reach under some merge.

*If (C) events from different sources commute on 𝓡, i.e. f_a f_b (T) = f_b f_a (T) for all T ∈ 𝓡
and a, b from different sources, and (S) the learning stabilises, i.e. there is a table G\* with
T = G\* once every source has delivered "enough" events, then O_σ(Y) = {G\*} for every fair schedule σ.*

**Proof.**
1. *Counts determine the table (by C).* Two merges of the same prefixes with the same per-source
   counts (n₁, …, n_s) are related by a finite series of adjacent swaps of events from different
   sources. This is the standard fact behind Mazurkiewicz traces: shuffles with equal Parikh vectors
   are equivalent under the independence relation "different source". Each swap leaves the table
   unchanged by (C), since all intermediate tables lie in 𝓡. So T_k = G(n₁(k), …, n_s(k)) for a
   function G of the counts alone.
2. *Fair schedules drive all counts to ∞.* Then (S) gives T_k = G\* for all large k.
3. Hence the periodic regime holds only G\*, so O_σ(Y) = {G\*}, independent of σ. ∎

**Both conditions are needed. Counterexamples from our probes:**
- *(C) holds, (S) fails: toggles.* Toggles commute, so T_k = G(n₁, n₂), but G depends on count
  parities and never becomes constant. Different schedules trace different monotone paths through
  the (n₁, n₂) grid and visit different sets of G-values. Observed: 13.6% order-dependent (complete).
- *(S) holds, (C) fails: appends that don't commute, and conflicting thresholds.* Learning stops,
  but the table it stops at depends on the order of the non-commuting pair. Observed: 69% (49 of 71 instances)
  where two appends don't commute; the race to conviction (L2) gives 1.5%.
- *Neither holds, yet invariance is observed: conflicting set-edits.* They ping-pong forever and don't
  commute, but with one contested field every fair path visits both "last writer" variants. So
  L5 is **sufficient, not necessary** (conjecture C1 covers this case).

**Check against the data.** Instances where all operations commute on the *initial* tables, with
set + append learners (which stabilise: sets are idempotent, appends stop at the cap): 0 of 164
order-dependent in complete. An exploratory run found 1 of 166 in alternating, which fits the lemma:
(C) is required on *reachable* tables, and the static check only inspected initial ones.

## L2, race to conviction (threshold learners)

*Threshold learners with one contested field. Suppose (C) holds for all other pairs. Then O_σ(Y) is
determined by which of the two conflicting lessons reaches its K-th observation last under m_σ.*

**Proof sketch.** Each threshold revision fires once, at its K-th observation, so (S) holds. By
the argument of L5, all revisions except the contested pair commute. The contested field ends with
the value of whichever revision fired last, so G\* is a function of that single comparison. ∎

## L6, synthesis = non-serialisable exposure (proof sketch, 2026-10-17)

Same setup, learner Y with two sources A, B. Call two events a (from A) and b (from B)
**conflicting** if f_a f_b ≠ f_b f_a on the relevant table, and form the *precedence graph* of a merge:
an edge A→B if some a precedes a conflicting b, and an edge B→A if some b precedes a conflicting a.

*If the precedence graph of a (finite) merge has no cycle, Y's table after it equals Y's table after
one of the two sequential exposures (all of A's events then all of B's, or the reverse).*

**Proof.** This is the conflict-serialisability theorem of database concurrency control, with A's
and B's lessons as the two "transactions" on Y's table. Without a cycle, every conflicting pair is
ordered the same way, say a before b. Then any b that precedes a later a' commutes with it, and
repeated adjacent swaps of commuting cross-source events (the trace argument of L5, step 1) move all
of A's events in front of B's without changing the table. ∎

**Consequences.**
- Synthesis (an outcome outside both serialisations) **requires a cycle**: some conflicting pair
  must be delivered A-before-B, *and* some (possibly different) conflicting pair B-before-A.
  *Correction (2026-10-17):* an earlier version said this means a "sandwich" (a lesson landing
  between two conflicting lessons of the other source). That is only a special case. The two pairs
  need not share a lesson, and the first test missed exactly those cycles.
- So if all conflicting pairs are delivered in the same direction, synthesis is impossible.
- **Tested** ([mt/synthesis.py](mt/synthesis.py), open loop, complete, 400 instances × 3 learners ×
  24 schedules). No cycle: 0 synthesis in 23 856 (append-once) and 22 724 (append) learner–schedule
  pairs. With a cycle: 145 of 4 920 (2.9%) and 1 092 of 6 052 (18.0%). "Conflict" was checked on the tables the merge visited, and
  the synthesis baseline was whole-stream sequential exposure, so the test is somewhat stronger
  than the theorem as stated.
- Caveat: the theorem is about conflict-equivalence, which is sufficient for equal outcomes but not
  necessary. Measured synthesis is outcome-level, so a cycle is necessary for synthesis but not
  sufficient. The extension from finite merges to the stabilised periodic regime is not written out.

## L7, closed-loop reduction (2026-10-17)

*In the closed loop, if the emitted streams of Y's sources (as infinite words in each source's own
step time) do not depend on the schedule, then Y's learned outcome obeys L1, L5 and L6 exactly as in
the open loop.*

**Proof.** Y's learned state evolves only through the events it receives (the update rule has no
other input), so it is a function of the merge of its sources' streams. The open-loop setup assumed
nothing about *why* those streams are fixed, only that they are. ∎

**Consequence.** Closed-loop order-dependence of a learner splits into (i) the open-loop effect of
merging the realised streams (governed by L5/L6) and (ii) variation of the streams themselves.
(ii) is where feedback ("what you learned changes what you teach") enters. Measured: (ii) is present
in 100% of order-dependent overwrite learners and 95% of append learners
([summary](results/publish/closed_loop/SUMMARY.md)).

## L8, construction alone is behaviourally inert (2026-10-17)

*If the only learning operations an agent ever receives are APPENDs (copy the state an entry points
to, redirect the entry to the copy), then on every tape its program behaves exactly like its
original program: same head and tape trajectory.*

**Proof.** Define the map π from states to original states: π(q) = q for original states, and
π(copy) = π(source it was copied from). An APPEND copies a state's two rows verbatim and redirects
one pointer to the copy, so every entry keeps the same write and move, and its `next` field
satisfies π(next) = the original next. By induction on the number of APPENDs, the program is a
*refinement* of the original: running both from the same configuration, the states correspond
under π, and they write, move and read identically at every step. ∎ (Property-tested:
`test_append_alone_is_behaviour_neutral`.)

**Consequence with L5.** Revision alone (overwrite) never synthesises rules in our probes. L5
explains why exposure order washes out for commuting, stabilising revisions, though conflicting
overwrites are only covered by conjecture C1. Construction alone can synthesise *structure* but never
new behaviour (L8). **A new brick therefore needs both.** Measured (mix run at p_append ½): among synthesised programs,
the new-brick share is 0 of 79 with no revision rules and 33% (186 of 565) with five.

## L9, one contested belief under overwrite (open loop), correcting conjecture C1 (2026-10-17)

Setup as in L5: open loop, fixed eventually-periodic source streams, fair schedules. The learner uses
overwrite revisions only (no appends), and exactly one (entry, field) is **contested**: it is the
target of lessons that set different values. All other lessons commute with each other and with
these (they target other fields, or set the same value).

*The set of programs the learner holds during the cycle can depend on the schedule only if every
conflicting lesson about the contested field is delivered finitely often, i.e. none of the triggers
setting that field occurs in its source's periodic phase.*

**Proof.** By L5's argument, all non-contested fields reach schedule-independent final values. For
the contested field, consider the lessons that set it.
(i) If some value v is set by a lesson delivered infinitely often, while no other value is, then
after the last delivery of any other-valued lesson the field equals v for ever. The cycle holds only
v, for every schedule.
(ii) If lessons setting two or more different values are each delivered infinitely often, the field
changes forever. Every fair schedule visits every value in that set during the cycle, and only
those, because finitely-delivered values stop occurring. So the cycle's set of values is the same.
(iii) Otherwise all conflicting lessons are delivered finitely often. The field ends with the value of
whichever was delivered **last**, and that depends on the merge. ∎

**Data.** In the exception hunt all three one-contested-field exceptions (`84fa2804d1b9`, 2 states;
`9f1fbb84d2b6`, 3 states, pre-grown; `2a4af7ba6bbe`, 3 states) are case (iii): two conflicting lessons, one per source, each
occurring only in its source's transient. Which teacher moves first decides the belief for good.
C1 (one contested field ⇒ invariant) was wrong exactly in case (iii).
