# Reflexivity in tiny swarms: what Turing machines that learn from each other can show

Code, data and the long version with the full methodology (controls, nulls, exception hunts, every
number with its source): [github.com/modemuser/multi-turing](https://github.com/modemuser/multi-turing).
Simulations give counts and examples, not proofs; anything interpretive is labelled *Interpretation*.

## TL;DR

- Three tiny Turing machines watch each other and rewrite their **own** rules from what they see.
  Everything can be observed exactly, replayed in any order, and frozen. This isolates **the learning
  half of reflexivity**: agents whose rules change through interaction. The machines know nothing
  about their situation, so the other half is out of reach here by construction.
- **Learners that build new concepts out of old ones can end up as programs that no sequential
  account of their lessons produces**, and that behave differently when taken out and run elsewhere.
  Roughly half of these exist only because of **feedback**: what the teachers had learned changed
  what they taught. Learners that only overwrite beliefs almost never do this.
- The mathematics behind this is known (commuting interleavings, serialisability). One lemma gives
  a sufficient condition for a count-based, physics-style description of learners to hold. The
  simulation adds existence and an ordering of effects, not rates that carry over to real systems.

## 1. A learner that ends up with something nobody taught it

Three machines, A, B and C. Each is a 2-state Turing machine on its own small circular tape. Whenever
one of them makes a move, the others apply a fixed learning rule to **their own** program (§3). Here
is the smallest case I found of something worth showing.

![Figure 1](https://raw.githubusercontent.com/modemuser/multi-turing/main/figures/fig1_witness.png)

**Figure 1.** The swarm's first nine steps, schedule ABC, closed loop (top) and open loop (bottom).
Three lessons change C's program: (1) A's move gives C a new state, a copy of an old one, (2) B's
move gives C a second new state, a copy of the first, (3) B, acting from a state it only has because
it learned, rewires that second new state. In the open loop B never reaches its learned state and
lesson 3 never happens. Right: C's final program alone on a blank tape, as the head's path over 20
steps (the ring unrolled). Blue is C's program; grey, C's program after the same lessons in a serial
order (the two serial orders give different programs but the same path on this tape).

1. Early on, C forms two **new concepts** (new internal states). Each starts as a copy of an
   existing state, triggered by a lesson from A and then one from B.
2. Then B teaches C a lesson **from a concept B had itself just learned**. B is in a state it only
   has because it learned. That lesson rewires one of C's new concepts.
3. Take C's final program out of the swarm and run it **alone on fresh tapes**. On 114 of all 256
   possible tapes it behaves differently from the program C would have ended up with had it heard
   all of A's lessons first and then B's, *and* differently from the reverse order. On a blank tape
   it inches to the left, rocking three times over each pair of cells before moving on; both serial
   versions run nine cells to the right, turn, and run back.
4. Rerun the same swarm with one change: everyone still learns, but keeps *acting* on their original
   programs. Now B can never be in its learned state, lesson 3 never happens, and C's program behaves
   like one of the two sequential versions on all 256 tapes. The closed-loop C behaves differently
   from this one on 114 of 256 tapes.

So C ends up with a program that is neither "what A taught, then what B taught" nor the reverse, and
not what it would have become without feedback. It exists only because a teacher's learning changed
what that teacher could teach. A standalone script sharing no code with the main engine reproduces
every number above ([`verify/verify_witness.py`](https://github.com/modemuser/multi-turing/blob/main/verify/verify_witness.py), instance
[`verify/witness_3f993cc102db_r1.json`](https://github.com/modemuser/multi-turing/blob/main/verify/witness_3f993cc102db_r1.json)).

**How common is this?** Over 400 randomly drawn swarms, each with 4 independently drawn learning
rules, 118 of 1 600 (7.4% [6.2, 8.6]) produce at least one such program under some order of play. Of
the 1 160 cases (agent × schedule × rule draw) where it happens, **604 (52% [42, 63]) need feedback**: the
open-loop run at the same schedule produces no such program. Compared directly with the program the
same agent learns in the open loop, 679 (58% [48, 69]) behave differently on at least one fresh tape,
as the example does on 114; 493 (42% [33, 53]) meet both criteria. With 3-state machines: 74% [57, 88]
(§7).

## 2. Why look at this at all

**Reflexivity** is the two-way loop between an agent's picture of its situation and the situation
itself: in Soros's terms, a *cognitive* function (the situation shapes what the agent takes it to be)
and a *participating* function (what the agent takes it to be shapes the situation; in his later
writing, the *manipulative* function). The loop has two components: agents **learn from
interaction** (their rules change), and agents **know their situation** (a model of it enters
their response). This post isolates the first. The second is the
subject of a follow-up post. Reflexivity proper is both at once, and neither post reaches it.

Agent swarms learn from each other, and it is hard to see how. In the OpenAI / Hugging Face incident
of July 2026, agents in an evaluation found an unsanctioned shared message board and joined an attack
(Greenblatt, Cotra & Wijk 2026). On that board they shared **know-how** (exploits and progress), and some
agents' reasoning shows **a norm** (continuing because peers were doing it). *Interpretation (analogy,
not a model of the incident):* know-how corresponds to lessons that change what an agent can do. The
norm corresponds to influence by counts, which this model does not represent.

Influence by counts is what population models in the style of statistical physics describe: each
agent's probability of a choice is a fixed response curve P(m) of the share m of its peers making that
choice, a property of the agent. For learners, one lemma gives a condition that guarantees it. **L5 (§4):**
if lessons from different sources commute and learning eventually settles, what an agent ends up
with depends only on **how many** lessons came from each source. Then a count-based description is a
property of the agent. Outside that condition, the order of past interactions can enter the response,
and P(m) then stops being a property of the agent alone. This is the precise sense in which learning
agents are not magnets, and the rest of the post is about what happens outside the condition.

## 3. Setup

**Agents.** Three 2-state, 2-symbol Turing machines, each on its own circular tape of 8 cells,
starting blank. An agent's **program** is its transition table. No halting.

**Learning.** When agent X moves (it was in state q and wrote w), every agent observing X applies the
learning rule R(q, w) to its **own** program. Agents never read each other's programs, tapes or heads;
they see only the event (q, w). R is shared. Each entry of R is one of:
- **overwrite**: set one field of one entry ("revise by overwrite");
- **append**: copy the state an entry points to into a new state, and redirect the entry to the copy
  ("differentiate a concept"; up to 4 states).

**Instance.** One draw of the three initial programs (uniform over tables) and the rule R. In the
*complete* observation graph each agent observes both others. A **schedule** is a fixed periodic
word saying who moves (24 words: ABC, AABC, ABAC, one seeded random word of length 12, and all their
relabellings). A **run** is one instance
under one schedule; everything is finite and deterministic, so every run ends in an exact cycle. The
**learned program** is the set of programs an agent holds in that cycle. An instance is
**order-dependent** if some agent's outcome differs between schedules. Intervals are 95%, clustered
by instance where cases are counted per agent × schedule.

**One manipulation carries the argument: open loop vs closed loop.** In the open loop, agents learn
but keep **acting** on their original programs, so what they emit can't change and only the order in
which they hear things matters. The closed loop is normal operation.

A swarm of rule-rewriting machines is still one Turing machine, and any order agents choose can be
replayed as a fixed schedule. Nothing here is about computational power. The questions are
structural: when does order matter, through which channel, and what can composition produce that no
sequential account explains?

## 4. What you hear vs what you teach

Two agents are not enough. **L1:** in the open loop, an agent with a single source learns the
same program under every schedule (its program is a fold of the rule over one fixed stream). So the
order of *what you hear* needs an agent with two sources: three agents are the minimum. The ring
graph (one source each) is a free check: 0% order-dependent for every learner type.

The open loop isolates exposure order. Complete graph, learned-program outcome, 400 matched instances:

| learner | open loop: exposure only | closed loop: + feedback |
|---|---|---|
| revise by overwrite | 0% [0, 1.0] | 7.8% [5.5, 10.8] |
| threshold (overwrite once, after 3 observations) | 1.5% [0.7, 3.2] | 10.5% [7.9, 13.9] |
| toggle (flip on every observation) | 13.6% [10.5, 17.3] | 40.1% [35.4, 45.0] |
| **append + overwrite** (construct new concepts) | **19.2% [15.7, 23.4]** | **35.0% [30.5, 39.8]** |

**L5 (commutation + stabilisation).** If lessons from different sources commute and learning
eventually stops changing the program, exposure order cannot matter: adjacent commuting lessons can
be swapped until the order is gone, and the program depends only on how many lessons came from each
source. Both conditions are needed. Toggles commute but never settle (13.6%). Threshold learners
settle, but conflicting lessons don't commute, and the one that reaches its third observation last
wins (1.5%). Overwrite's 0% is a property of the outcome measure, not of revision: with conflicting
lessons the learner flips for ever and every fair schedule visits both versions ([long version](https://github.com/modemuser/multi-turing/blob/main/POST_LONG.md) §4; §7
for the rare exceptions and L9).

**L7 (closed-loop reduction).** A learner's program depends only on the streams it receives. If its
sources' streams don't change with the schedule, L1 and L5 apply as in the open loop. So extra
order-dependence in the closed loop has to come from **the streams themselves varying**: teachers
teach differently because they learned differently. Measured: all 49 order-dependent overwrite
learners, and 263 of 276 (95%) order-dependent append learners, have a source whose emitted stream
varies. That is where feedback enters.

## 5. Construction, and synthesis

*Interpretation:* appending is the most primitive form of learning something new: a copy of an
existing concept, then specialised. Two controls show the effect comes from **forming** concepts
during the interaction, not from having more of them:
- **Pre-grown:** give agents their extra concepts before the run. Open loop: 0% order-dependent,
  down from 19.2%.
- **Copies alone are inert (L8):** a freshly copied concept behaves exactly like its original, so
  construction alone creates new structure but never new behaviour.

New behaviour therefore needs **construction and then revision**. Varying the share of append rules
from 25% to 75%, synthesis rises (2.0% → 6.7% of agent × schedule pairs) while the share of it that
becomes new behaviour, in the sense of §6, falls (31% → 18%); both trends lie outside the intervals
(table in the long version, §5).

**Synthesis.** Agent C, learning from A and B, *synthesises* if its learned program is neither the one
from all of A's lessons then all of B's, nor the reverse. Among constructive learners in the open
loop, 53 of 400 instances synthesise, 52 of them among the 77 order-dependent instances (one
synthesises the same program under every schedule): 0 of 164 where all lessons commute, 41 of 71
where two constructions don't, 12 of 165 where a construction and an overwrite don't. Of the 52,
51 are also outside every blockwise interleaving (A, B, A, B, … in whole blocks), so it takes
fine-grained interleaving.

**L6 (synthesis needs a non-serialisable exposure).** If every pair of conflicting lessons arrived in
the same direction, commuting lessons can be swapped until the exposure is sequential. So synthesis
needs conflicting lessons in **both directions**: the conflict-serialisability theorem from database
concurrency control, applied to what an agent learns. Tested on 46 580 agent–schedule pairs: no
synthesis without such a cycle.

At the level of programs, only constructive learning is non-serialisable. Closed loop: overwrite
learners 0 of 28 800 agent–schedule pairs; constructive learners 4.5% [3.3, 5.7]. 

## 6. New bricks: taking the parts out

A synthesised program could differ from both serial versions only in rules it never uses. So each
learned program is run alone on all 256 fresh tapes of length 8:

- **23% [19, 28] of the 5 037 synthesised programs in the §1 sweep (400 instances × 4 rule draws)
  behave unlike both serial versions on at least one fresh tape.** It is rarely a near miss: the
  median such program differs on **209 of 256** tapes (IQR 96–255); 25% differ on every tape, 3% on
  8 or fewer.
- **Feedback necessity:** of the 1 160 new bricks, 604 (52% [42, 63]) do not arise in the open loop
  at the same schedule. This is the null that carries weight: not "neither serial extreme", but
  "not produced by the same order of play without feedback".

**Agents that choose who moves next.** When table entries also name who acts next and learning can
rewrite that, learning changes the order of play in 19.8% [16.0, 23.7] of 1 200 runs, and new bricks
still arise at a similar conversion rate (27% [15, 40] of 133 synthesised programs).

## 7. Robustness

With **3-state machines** (395 instances), new bricks arise in 10.1% [7.5, 13.5] of instances, 74%
[57, 88] of 477 need feedback, and none arise without revision rules. An **exception hunt** over
5 998 fresh instances, each run with both revision-only learner types (about 12 000 instance–learner
pairs), found 5 cases of exposure-order dependence or synthesis, all explained: three by a one-off conflicting lesson in a teacher's start-up phase, where
whoever spoke last fixes the belief for good (**L9**), two by two contested beliefs whose winning
combination depends on the interleaving. Full table in the long version, §7.

## 8. What this shows, and what it doesn't

- **What the simulation buys:** existence (programs no serial account explains, that behave
  differently elsewhere, and about half of which need feedback) and an ordering of effects
  (construction ≫ overwrite in synthesis; the physical-coupling control is in the long version, §3). The
  structural statements (L1, L5–L9; L6 is a proof sketch, see
  [PROOFS.md](https://github.com/modemuser/multi-turing/blob/main/PROOFS.md)) hold for any learners
  whose updates compose this way, and need no simulation. The one that transfers most directly is
  **L5 as the condition for count-based models**: a response curve P(m) is guaranteed to be a
  property of a learning agent if its
  lessons commute and its learning settles. The condition is sufficient, not necessary (§4).
- **What it doesn't:** the rates belong to this toy and its uniform prior. The agents react; they
  don't model anything. This is the learning half of reflexivity only. The central effect,
  feedback-dependent new bricks, has no lemma yet: L7 says where it must come from, not when it
  happens.
- **Measurement designs** for real multi-agent systems: open vs closed loop (record agents' outputs
  and replay them unchanged while they learn; the design the follow-up post applies to an LLM);
  serialised replays of recorded messages; transplanting a learned agent into a fresh context.

## 9. Open questions

- **Agents that model each other.** This is where the two halves of reflexivity meet: what an agent
  knows about its situation is itself learned.
- A lemma for the closed loop: when do learned programs change what agents teach?
- Under what conditions on learning (L5) is a count-based description exact, and how large a
  minority then tips a population?

## Related work

Reflexivity is Soros's (1987); Kwong (2009) writes it as a dynamical system. Programs acting on
programs: AlChemy (Fontana & Buss 1994), Computational Life (Agüera y Arcas et al. 2024) study
emergence in soups where programs run on each other; here agents only observe each other's actions,
and the question is serialisability. Order of updates: the training-example Lie bracket
(DaemonicSigil 2026, after Dherin 2023) is the continuous analogue of L5's commutation condition;
L5 and L6 use Mazurkiewicz traces (1977) and conflict serialisability (Eswaran et al. 1976;
Papadimitriou 1979). Belief revision: expansion commutes, AGM revision (1985) and iterated revision
(Darwiche & Pearl 1997) do not; L9 is a statement of that kind. Population models of LLM agents:
De Marzo et al. (2026), whose Curie–Weiss fit is what L5 conditions. Full notes:
[LITERATURE.md](https://github.com/modemuser/multi-turing/blob/main/LITERATURE.md).

## References

- Agüera y Arcas, B., Alakuijala, J., Evans, J., Laurie, B., Mordvintsev, A., Niklasson, E.,
  Randazzo, E., Versari, L. (2024). Computational Life: How Well-formed, Self-replicating Programs
  Emerge from Simple Interaction. arXiv:2406.19108.
- Alchourrón, C., Gärdenfors, P., Makinson, D. (1985). On the logic of theory change. *Journal of
  Symbolic Logic* 50(2).
- DaemonicSigil (2026). The training example Lie bracket. LessWrong, 7 April 2026.
- Darwiche, A., Pearl, J. (1997). On the logic of iterated belief revision. *Artificial
  Intelligence* 89.
- De Marzo, G., Bellina, A., Castellano, C., Priesemann, V., Garcia, D. (2026). Conformity Generates Collective
  Misalignment in AI Agents Societies. arXiv:2605.10721.
- Dherin, B. (2023). Implicit biases in multitask and continual learning from a backward error
  analysis perspective. arXiv:2311.00235.
- Eswaran, K. P., Gray, J. N., Lorie, R. A., Traiger, I. L. (1976). The notions of consistency and
  predicate locks in a database system. *Communications of the ACM* 19(11).
- Fontana, W., Buss, L. W. (1994). What would be conserved if "the tape were played twice"? *PNAS*
  91(2).
- Greenblatt, R., Cotra, A., Wijk, H. (2026). Brief independent investigation of agents' behavior,
  reasoning and collaboration in the OpenAI / Hugging Face hacking incident. METR, 26 August 2026.
- Kwong, C. P. (2009). Mathematical analysis of Soros's theory of reflexivity. arXiv:0901.4447.
- Mazurkiewicz, A. (1977). Concurrent program schemes and their interpretations. DAIMI PB-78,
  Aarhus University.
- Papadimitriou, C. H. (1979). The serializability of concurrent database updates. *Journal of the
  ACM* 26(4).
- Soros, G. (1987). *The Alchemy of Finance*. Simon & Schuster.
