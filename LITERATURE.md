# Literature check (2026-10-17)

Positioning for the post: what is known, what we build on, and what may be new. The first section
lists what was checked against the primary source (or its abstract or full text) before citing it in
the post. Everything after it comes from the earlier search and is background only.

## Verified against the source (2026-10-17)

| source | what was checked | result |
|---|---|---|
| Agüera y Arcas et al. 2024, arXiv:2406.19108 | authors, claim | self-replicators emerge from random interaction and self-modification, no explicit fitness; no learning |
| De Marzo, Bellina, Castellano, Priesemann, Garcia 2026, arXiv:2605.10721, "Conformity Generates Collective Misalignment in AI Agents Societies" | the P(m) form | full text: P(m) = ½{tanh[β(m+h)] + 1}, β majority force, h bias; fully connected, N = 50 in the main experiments; stubborn adversarial agents discussed |
| Pan, Gonzalez, Jegelka, Broderick, Jordan 2013, arXiv:1307.8049 | serialisability claim | full text: OCC "guarantees a serializable execution"; clustering, feature learning, facility location |
| Kwong 2009, arXiv:0901.4447, "Mathematical analysis of Soros's theory of reflexivity" | claim | cognitive/manipulative functions as a discrete dynamical system; fixed points; boom-bust |
| DaemonicSigil, "The training example Lie bracket", LessWrong, 7 Apr 2026 | author, claim | updates commute to first order in the learning rate; second-order difference = the bracket; credits Dherin 2023 (arXiv:2311.00235) |
| METR, 26 Aug 2026, "Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident" (Greenblatt [Redwood, contracting], Cotra, Wijk) | incident facts used in §2 | July 2026; ExploitGym evaluation; about 1,200 agents on an unsanctioned board (Artifactory cache); exploits and reusable bundles shared; about 700 joined the attack. Norm: one agent's reasoning ends "peers doing it. We should continue."; the report also cites helping peers and usefulness of the research, so the post says "some agents' reasoning shows a norm". No participation threshold (20% → 90%) in the report; do not cite one from it. |
| Fontana & Buss 1994, PNAS 91(2), "What would be conserved if 'the tape were played twice'?" | setup | from secondary sources (2024 revisit, arXiv:2408.12137): lambda expressions applied to each other, results returned to the population, organisation levels 0–2. Primary text not read. |

Standard references cited from known bibliographic data, not re-read: Mazurkiewicz 1977 (DAIMI
PB-78); Eswaran et al. 1976 (CACM 19(11)); Papadimitriou 1979 (JACM 26(4)); AGM 1985 (JSL 50(2));
Darwiche & Pearl 1997 (AIJ 89); Soros 1987 (*The Alchemy of Finance*).

Dropped from the post: "The Order Is The Message" (arXiv 2603.25047), the Independence postulate,
Goldin–Wegner and the multi-agent LLM ordering papers (not checked; not needed for the claims).

## Closest prior art: programs that act on programs

- **Fontana & Buss, AlChemy ("algorithmic chemistry", 1994; Fontana et al. 1993 on "constructive"
  systems).** Lambda-calculus expressions are combined by application, and the results go back into
  the population. Self-maintaining "organizations" emerge. A **strongly constructive** system is one
  that can create new components which in turn change its global dynamics. That is very close in
  spirit to our "new bricks". Later work: Combinatory Chemistry (arXiv 2003.07916); a 2024 revisit
  finding stable organizations that "cannot be easily combined into higher order entities".
- **Agüera y Arcas et al., "Computational Life: How Well-formed, Self-replicating Programs Emerge
  from Simple Interaction" (arXiv 2406.19108, 2024).** Random programs (BFF, Forth) interact by
  concatenation and execution, modifying each other, and self-replicators emerge without explicit
  fitness. A 2026 follow-up argues mutation random walks suffice.
- **Difference from us (to verify):** those systems study *emergence* (self-replication, self-
  maintaining organizations) in soups where programs execute on each other. We study **learning
  agents with a fixed architecture that observe, never read, each other**, and ask about **order**:
  when do outcomes depend on interaction order, and when is the result *non-serialisable*? We
  separate exposure from feedback (open/closed loop) and test whether new programs transplant. We
  found no prior work on mutually rewriting *Turing machines* in this sense, but that search was thin.

## Order and commutation of updates

- **"The training example Lie bracket" (LessWrong).** For SGD, updates from different examples
  commute to first order in the learning rate. Their second-order difference is a Lie bracket, so
  order effects are measurable non-commutation. That is directly relevant to L5 (commutation ⇒
  order-independence) and a natural bridge for LessWrong readers to real ML.
- **"The Order Is The Message" (arXiv 2603.25047, 2026).** The training trajectory and basin depend
  on data order in non-convex losses.
- **Concurrency control for ML (Pan et al., AMPLab "CCML"; Distributed GraphLab).** ML updates are
  treated as transactions, and serialisability is preserved when operations commute. This is the
  same mathematics as our L6, but applied to *making parallel training safe*, not to *what agents
  become*.
- **Mazurkiewicz traces / partially commutative monoids:** standard concurrency theory (our L5 proof).

## Belief revision

- **AGM; Darwiche–Pearl (1997) iterated revision;** the **Independence postulate (P)** and its
  tension with DP (Aravanis, Peppas, Williams; Booth & Chandler). Order-sensitivity of sequential
  revision is a known topic. *Expansion* commutes (our C2), and revision generally does not. Our
  "overwrite washes out exposure order" (C1) should be positioned against this.

## Reflexivity, formally

- **Soros (1987):** a pair of functions, *cognitive* (perceptions depend on the situation) and
  *participating* (the situation depends on perceptions; *manipulative* is his later term, which
  the post notes). **Kwong (arXiv 0901.4447)** analyses them as
  a discrete dynamical system with fixed points. Shaikh (2013), Guala (2013): multiple equilibria,
  informational cascades. Our closed-loop decomposition (L7: stream variation = what you learned
  changes what you teach) maps onto the cognitive/manipulative pair.

## Interactive computation (expressiveness claims to stay away from)

- **Goldin & Wegner, Persistent Turing Machines:** they argue interaction is *more expressive* than
  algorithms. This is contested. Our position is the conventional one: the whole swarm is one TM,
  and what's new is *structure*, not power. Worth one sentence in the post to pre-empt the
  confusion.

## Multi-agent LLM systems (motivation: order effects are real and hard to observe)

- **Position paper (arXiv 2605.01147, 2026):** safety and fairness in agentic AI depend on
  interaction topology. It reports ordering effects across model scales (claims broader than its
  evidence).
- **Sequential public goods games with multiple LLMs (arXiv 2508.02076):** outcomes depend on agent
  ordering.
- **Network-effect games with GPT-based agents (arXiv 2510.06903):** history structure drives path
  dependence.

## What is plausibly new (to be confirmed after reading the primary sources)

1. The **open/closed-loop decomposition** of order effects in learning swarms, with exposure-only
   effects provably 0 for a single source (L1) and for commuting, stabilising updates (L5).
2. **Synthesis = non-serialisable exposure** (L6), applied to *what agents learn* rather than to
   making parallel training safe.
3. **Construction + revision** as jointly necessary for new behaviour (L8 + L5).
4. **New bricks:** learned programs that transplant to fresh situations and behave unlike any serial
   history, about half of them needing feedback (74% with 3-state machines).
5. The **coupling control**: physical interaction is *more* order-dependent than learning, so
   order-dependence is not the signature of reflexivity.
6. **Measurement designs that could be applied to real agent swarms** (freeze outputs, serialise
   message orders, transplant agents).

The closest overlap to address head-on: AlChemy's "constructive" systems (new components changing
global dynamics) and serialisability in ML systems.
