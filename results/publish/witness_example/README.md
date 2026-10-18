# New-brick witness: instance 3f993cc102db#1, schedule ABC (ABC), learner C

Entry notation `q,r:WMN<route>` (route k = keep, + = pass to next agent, − = previous). States ≥ 2 are concepts appended during the run.

```
A initial: 0,0:1L1+ 0,1:0R0+ 1,0:0L1+ 1,1:1L1+
B initial: 0,0:1L0- 0,1:1L0+ 1,0:1R0+ 1,1:0L0+
C initial: 0,0:1R0+ 0,1:1R1k 1,0:0L0+ 1,1:0L1-
R (applied by every observer to its OWN table):
   on observing (0, wrote 0) -> APPEND: copy the state own entry 0,1 points to into a new state, redirect the entry to the copy
   on observing (0, wrote 1) -> APPEND: copy the state own entry 0,0 points to into a new state, redirect the entry to the copy
   on observing (1, wrote 0) -> APPEND: copy the state own entry 1,1 points to into a new state, redirect the entry to the copy
   on observing (2, wrote 0) -> set own entry 3,1.write=1
   on observing (2, wrote 1) -> set own entry 3,0.move=L
```

## C's closed-loop input history (lessons that changed its program)

```
step    0: lesson from A (it was in state 0, wrote 1) -> C now has 3 states: 0,0:1R2+ 0,1:1R1k 1,0:0L0+ 1,1:0L1- 2,0:1R0+ 2,1:1R1k
step    1: lesson from B (it was in state 0, wrote 1) -> C now has 4 states: 0,0:1R3+ 0,1:1R1k 1,0:0L0+ 1,1:0L1- 2,0:1R0+ 2,1:1R1k 3,0:1R0+ 3,1:1R1k
step    4: lesson from B (it was in state 2, wrote 1) -> C now has 4 states: 0,0:1R3+ 0,1:1R1k 1,0:0L0+ 1,1:0L1- 2,0:1R0+ 2,1:1R1k 3,0:1L0+ 3,1:1R1k **[teacher was in a concept it had LEARNED: impossible without feedback]**
```

## Final programs

```
actual (interleaved)     : 0,0:1R3+ 0,1:1R1k 1,0:0L0+ 1,1:0L1- 2,0:1R0+ 2,1:1R1k 3,0:1L0+ 3,1:1R1k
all of A first, then B : 0,0:1R2+ 0,1:1R1k 1,0:0L0+ 1,1:0L3- 2,0:1R0+ 2,1:1R1k 3,0:0L0+ 3,1:0L1-
all of B first, then A : 0,0:1R3+ 0,1:1R1k 1,0:0L0+ 1,1:0L1- 2,0:1R0+ 2,1:1R1k 3,0:1R0+ 3,1:1R1k
```

## Transplanted alone onto fresh tapes

The actual program behaves unlike both serial programs on **114 of 256** fresh tapes of length 8. Example, tape `00000000` (cell 0 first):

```
actual   : cycle of 24 steps; tapes visited ['00000000', '00000010', '00000011', '00001000'] …
A first  : cycle of 18 steps; tapes visited ['00000000', '00100000', '00110000', '00111000'] …
B first  : cycle of 18 steps; tapes visited ['00000000', '00100000', '00110000', '00111000'] …
```

## Open-loop counterpart (same schedule; agents learn but act on their original programs)

Rule level: the open-loop program equals both serial alternatives' one. **Behaviour level: it behaves unlike both serial programs on 0 of 256 fresh tapes**, so it is not a new brick without feedback. (Teachers acting on their original programs can never send lessons from learned concepts.)

```
open-loop actual : 0,0:1R3+ 0,1:1R1k 1,0:0L0+ 1,1:0L1- 2,0:1R0+ 2,1:1R1k 3,0:1R0+ 3,1:1R1k
```

Repro: `uv run python -m mt.witness_story 3f993cc102db#1 ABC 2`
