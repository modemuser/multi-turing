# Reflexivity in tiny swarms: what Turing machines that learn from each other can show (long version)

This is [POST.md](POST.md) with the full methodology added in place: the setup in detail, the
physical-coupling control, the mix table, the three nulls, the exception-hunt table and L9, and the
extended related work. Section numbers are the same in both versions. Every number comes from one
pipeline run ([PROVENANCE.md](PROVENANCE.md); all numbers with their sources in
[`results/publish/POST_NUMBERS.md`](results/publish/POST_NUMBERS.md)), the findings log is
[NOTEBOOK.md](NOTEBOOK.md), and the proofs are in [PROOFS.md](PROOFS.md). Simulations give counts
and examples, not proofs; anything interpretive is labelled *Interpretation*.

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
- The central effect, feedback-dependent new programs, has no lemma yet.

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

Real swarms are hard to observe: we can't see every message, replay interactions in a different
order, or freeze an agent's learning while it keeps acting. With tiny Turing machines we can do all
three. A follow-up post takes up the other half: real models that can recognise the measurement
itself, and what that does to the same curve.

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

**Details.** Each tape starts blank with the head at cell 0 and the agent in state 0. A transition
table says, for each (state, symbol read), what to write, which way to move and which state to
enter. Programs are drawn uniformly over all tables. For overwrite rules, R has k active entries, k
uniform over 1..4, each setting one random field of one random entry. For constructive rules, R
has an entry for every (state, symbol) of the 4 possible states, learned states included, each
active with probability ½. An active entry of an initial state is an append with probability ½
(the share varied in §5), copying the state that a random entry of an initial state points to;
every other active entry overwrites one random field of one random entry, in any of the 4 states.
So a teacher moving from a learned state can deliver a lesson, which lesson 3 of the §1 example
needs. With 3-state machines the cap is 5 states. For the constructive results in §1, §5 and §6,
each of the 400 instances gets 4 independently drawn rules. The initial programs and R of the §1 example are
listed in the [annotated witness](results/publish/witness_example/README.md).

**Variants used as checks:** *threshold*, which overwrites once after three observations; *toggle*,
which flips a field on every observation; *pre-grown*, where agents get their extra states before
the run and the rule only revises them; *append-once*, where a state can be copied only once.

**Who observes whom.** In the *complete* graph each agent observes both others, in the *ring* each
observes one, and *alternating* has two sources per agent but only one observer per event. In one
variant the order of play is *endogenous*: table entries also name who acts next, and learning can
rewrite that (§6).

**Outcomes.** Two are used, and every number says which: the **learned program** (the set of
programs an agent holds during the final cycle) and the **full outcome** (the agent's whole cycle:
state, head, tape, program, up to rotation of its ring).

**Intervals.** Shares of instances use Wilson intervals. Shares counted over agent × schedule pairs
use a bootstrap over instances, because pairs from the same instance are correlated (a few instances
produce many of the cases).

**One manipulation carries the argument: open loop vs closed loop.** In the open loop, agents learn
but keep **acting** on their original programs, so what they emit can't change and only the order in
which they hear things matters. The closed loop is normal operation.

A swarm of rule-rewriting machines is still one Turing machine, and any order agents choose can be
replayed as a fixed schedule. Nothing here is about computational power. The questions are
structural: when does order matter, through which channel, and what can composition produce that no
sequential account explains?

### A control: order-dependence is cheap

A second manipulation, used only as a control: *physical coupling*. The same observation events,
instead of changing the observer's program, write the observed symbol onto the observer's tape. A
first, almost definitional, observation is that plain physical coupling makes outcomes more
order-dependent than learning does (complete graph, 400 instances, full outcome):

| interaction | order-dependent instances |
|---|---|
| none | 0% [0, 1.0] |
| physical coupling, volume-matched (at most one write per event type) | 66.9% [62.2, 71.4] |
| learning (overwrite) | 24.5% [20.5, 28.9] |

A write to your tape changes your world at once. A program change matters only when that rule is
used: it is a latent memory layer. So order-dependence alone is not a sign of learning-mediated
feedback. What learning has that coupling lacks shows up only at the level of programs (§5).

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
wins (1.5%, all in instances with conflicting lessons).

**Why overwrite shows 0% here.** Conflicting overwrites exist: 69 of 800 instances have two lessons
that set the same field to different values, and those don't commute. But when both keep arriving,
the learner never *settles* on the contested belief. In 58% of their cycles it flips back and forth
for ever, and every fair schedule visits both versions. The learned-program outcome (the set of
programs held in the cycle) is therefore the same. So the 0% is a property of overwrite with this
outcome measure, not of revision in general. Humans, LLMs and SGD revise in order-sensitive ways. A
larger search finds the rare exception and its exact mechanism (§7).

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
by design (400 instances × 4 rule draws each; intervals clustered by instance):

| append share | synthesis (agent × schedule) | of which become new behaviour (§6) | instances × draws affected |
|---|---|---|---|
| 25% | 2.0% [1.7, 2.4] | 31% [24, 39] (n = 2 331) | 3.6% [2.7, 4.4] |
| 50% | 4.4% [3.8, 5.0] | 23% [19, 28] (n = 5 037) | 7.4% [6.2, 8.6] |
| 75% | 6.7% [5.9, 7.5] | 18% [15, 22] (n = 7 713) | 9.4% [7.9, 10.9] |

More construction means more synthesis, but a smaller share of it turns into new behaviour. Between
25% and 75% appends, both trends lie outside the intervals. Overall, more instances are affected.

*Interpretation:* in belief-revision theory, plain expansion (adding a belief) commutes, and revision
generally does not. What breaks commutativity here is narrower: building new knowledge out of
existing knowledge while other lessons are still arriving.

**Synthesis.** Agent C, learning from A and B, *synthesises* if its learned program is neither the one
from all of A's lessons then all of B's, nor the reverse. Against that null alone, synthesis is cheap
to claim, so three nulls of increasing strength are used: the two serial extremes (the definition),
blockwise interleaving (A, B, A, B, … in whole blocks until stable), and feedback necessity (§6: the
program must not arise in the open loop at the same schedule), which is the null that carries weight. Among constructive learners in the open
loop, 53 of 400 instances synthesise, 52 of them among the 77 order-dependent instances (one
synthesises the same program under every schedule): 0 of 164 where all lessons commute, 41 of 71
where two constructions don't, 12 of 165 where a construction and an overwrite don't. Of the 52,
51 are also outside every blockwise interleaving, so it takes fine-grained
interleaving.

**L6 (synthesis needs a non-serialisable exposure).** If every pair of conflicting lessons arrived in
the same direction, commuting lessons can be swapped until the exposure is sequential. So synthesis
needs conflicting lessons in **both directions**: the conflict-serialisability theorem from database
concurrency control, applied to what an agent learns. Tested on 46 580 agent–schedule pairs: no
synthesis without such a cycle.

At the level of programs, only learning can be non-serialisable (physical coupling doesn't change
programs), and only constructive learning is. Closed loop, complete graph: overwrite
learners 0 of 28 800 agent–schedule pairs; constructive learners 4.5% [3.3, 5.7]. 

## 6. New bricks: taking the parts out

A synthesised program could differ from both serial versions only in rules it never uses. So each
learned program is run alone on all 256 fresh tapes of length 8:

- **23% [19, 28] of the 5 037 synthesised programs in the §1 sweep (400 instances × 4 rule draws)
  behave unlike both serial versions on at least one fresh tape** (19% with only 4 tapes, so the
  test tapes hid little). It is rarely a near miss: the median such program differs on **209 of
  256** tapes (IQR 96–255); 69% differ on at least half the
  tapes, 25% on every tape, 3% on 8 or fewer.
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
combination depends on the interleaving.

**The hunt in full.** Fresh instances, complete graph, 24 schedules, closed and open loop; runs that
hit the 200 000-step budget are excluded (542 of 287 904 instance–schedule runs).

| states | learner | open loop: exposure-order dependent | rule synthesis (closed loop) |
|---|---|---|---|
| 2 | revise by overwrite | 1 of 3 997 | 0 of 3 997 (95% upper bound 0.07%) |
| 2 | pre-grown concepts, then revision | 0 of 3 997 (95% upper bound 0.07%) | 0 of 3 997 (95% upper bound 0.07%) |
| 3 | revise by overwrite | 2 of 1 996 | 2 of 1 996 |
| 3 | pre-grown concepts, then revision | 1 of 1 997 | 0 of 1 997 (95% upper bound 0.15%) |

Three of the five exceptions have one contested belief, and they are exactly the case that the
argument for overwrite in §4 missed. **L9 (proof in PROOFS.md):** with one contested belief,
exposure order can matter only if *every* conflicting lesson about it is delivered finitely often. In
all three, each of the two conflicting lessons comes from a different teacher and occurs only in
that teacher's start-up phase, so whichever arrives last fixes the belief for good. The other two
exceptions have two contested beliefs, and which combination of winners results depends on the
interleaving. *Interpretation:* repeated lessons wash out order, but one-off conflicting impressions
are fixed by whoever spoke last.

## 8. What this shows, and what it doesn't

- **What the simulation buys:** existence (programs no serial account explains, that behave
  differently elsewhere, and about half of which need feedback) and an ordering of effects
  (coupling > learning in raw order-dependence, §3; construction ≫ overwrite in synthesis). The
  structural statements (L1, L5–L9; L6 is a proof sketch, see [PROOFS.md](PROOFS.md)) hold for any
  learners whose updates compose this way, and need no simulation. The one that transfers most
  directly is **L5 as the condition for count-based models**: a response curve P(m) is guaranteed
  to be a property of a learning agent if its
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
- Randomness: lock-in in the Pólya-urn sense as a second kind of path dependence.

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

**Reflexivity.** The concept is Soros's (1987): a cognitive function, by which the situation shapes
participants' views, and a participating function (his later term: manipulative), by which their
views shape the situation. Kwong
(2009) writes the pair as a discrete dynamical system and studies its fixed points. This post models
only the cognitive side as learning. In the closed loop, what an agent has learned changes what it
teaches (L7); that is the nearest this model gets to the manipulative side.

**Programs acting on programs.** In AlChemy (Fontana & Buss 1994), lambda-calculus expressions are
applied to each other and the results return to the population, and self-maintaining organisations
emerge. In Computational Life (Agüera y Arcas et al. 2024), random programs that interact by
concatenation and execution give rise to self-replicators without an explicit fitness function. Both
study emergence in soups where programs run on each other. Here, agents with a fixed architecture only
observe each other's actions, and the question is when the order of interactions matters and when the
result is not serialisable.

**Order of updates.** For gradient descent, updates from different examples commute to first order in
the learning rate. The second-order difference is the training-example Lie bracket (DaemonicSigil
2026, following Dherin 2023). That is the continuous analogue of the commutation condition in L5. The
tools of L5 and L6 are standard concurrency theory: Mazurkiewicz traces (1977) and conflict
serialisability via the precedence graph (Eswaran et al. 1976; Papadimitriou 1979). In machine
learning, the same notion has been used to make parallel training safe: Pan et al. (2013) run
distributed clustering and feature learning under optimistic concurrency control and guarantee a
serialisable execution. Here, non-serialisability is not a fault to prevent but the quantity
measured.

**Belief revision.** Expansion (adding beliefs) commutes. Revision in the AGM sense (Alchourrón,
Gärdenfors & Makinson 1985) and iterated revision (Darwiche & Pearl 1997) are order-sensitive in
general. L9 is a statement of that kind for one contested entry under overwrite.

**Populations of LLM agents.** De Marzo et al. (2026) put LLM agents on a fully connected network
and fit each agent's probability of an opinion as P(m) = ½{tanh[β(m + h)] + 1}, a Curie–Weiss form
with a majority force β and a bias h. L5 says when a fixed response curve of this kind is exact for
learners. The incident in §2 is documented in METR's investigation (Greenblatt, Cotra & Wijk 2026).

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
- Pan, X., Gonzalez, J. E., Jegelka, S., Broderick, T., Jordan, M. I. (2013). Optimistic
  concurrency control for distributed unsupervised learning. arXiv:1307.8049.
- Papadimitriou, C. H. (1979). The serializability of concurrent database updates. *Journal of the
  ACM* 26(4).
- Soros, G. (1987). *The Alchemy of Finance*. Simon & Schuster.

## Appendix

Lemma statements and proofs: [PROOFS.md](PROOFS.md). Code, repro commands and the independent check:
[README.md](README.md), [`verify/`](verify/). The annotated §1 example:
[`results/publish/witness_example/README.md`](results/publish/witness_example/README.md).
