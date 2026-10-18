"""Independent re-check of the smallest feedback-required new-brick witness.

Standalone: imports nothing from the project (`mt`). Re-implements the model from its written
description (DESIGN.md / NOTEBOOK.md) so that a reader can check the claim without trusting the
engine.

    python3 verify/verify_witness.py verify/witness_b2c9cf1289ca.json

Model, in words:
- 3 agents A, B, C; each has a table of 4*cap entries (state q, read r) -> (write, move, next, route),
  a circular tape of 8 cells (blank), head at 0, state 0. Route is ignored (fixed schedule).
- Fixed schedule word, repeated: the named agent makes one transition.
- Every OTHER agent observes the transition (pre-state q, written symbol w) and applies rule R[2q+w]
  to its OWN table:
    SET (e, f, v):   own entry e, field f := v   (skipped if entry e belongs to a state the observer
                     doesn't have yet, or if it would point `next` at a state it doesn't have)
    APPEND (e):      if room: copy the state that own entry e points to into a new state, and
                     redirect entry e to the copy
- Closed loop: agents act on their current (learned) table. Open loop: agents act on their
  ORIGINAL table while still learning.
"""
import json
import sys

L = 8


def step_agent(state, T):
    s, h, t = state
    r = (t >> h) & 1
    b = 4 * (2 * s + r)
    w, m, nx = T[b], T[b + 1], T[b + 2]
    t = t | (1 << h) if w else t & ~(1 << h)
    h = (h + 1) % L if m else (h - 1) % L
    return (nx, h, t), (s, w)


def learn(T, ns, event, R, cap):
    q, w = event
    x = R[2 * q + w]
    if x is None:
        return T, ns
    T = list(T)
    if len(x) == 4 and x[3] == 3:                      # APPEND
        e = x[0]
        if ns < cap and e // 2 < ns:
            src = T[4 * e + 2]
            T[8 * ns:8 * ns + 8] = T[8 * src:8 * src + 8]
            T[4 * e + 2] = ns
            ns += 1
        return tuple(T), ns
    e, f, v = x[0], x[1], x[2]                         # SET
    if e // 2 >= ns or (f == 2 and v >= ns):
        return tuple(T), ns
    T[4 * e + f] = v
    return tuple(T), ns


def simulate(inst, closed):
    """Run until the joint configuration repeats. Returns the learner's input history:
    list of ('own',) or ('lesson', source, event)."""
    tables0 = [tuple(t) for t in inst["tables"]]
    tables, ns = list(tables0), [inst["n"]] * 3
    states = [(0, 0, 0)] * 3
    word, C = inst["schedule"], inst["learner"]
    seen, hist, phase = set(), [], 0
    while True:
        key = (tuple(states), tuple(tables), tuple(ns), phase)
        if key in seen:
            return hist
        seen.add(key)
        X = "ABC".index(word[phase])
        phase = (phase + 1) % len(word)
        states[X], ev = step_agent(states[X], tables[X] if closed else tables0[X])
        hist.append(("own",) if X == C else ("lesson", X, ev))
        for Y in range(3):
            if Y != X:
                tables[Y], ns[Y] = learn(tables[Y], ns[Y], ev, inst["R"], inst["cap"])


def replay(inst, hist, closed):
    """Learner alone, fed its input history."""
    C = inst["learner"]
    T0 = tuple(inst["tables"][C])
    T, ns, st = T0, inst["n"], (0, 0, 0)
    for x in hist:
        if x[0] == "own":
            st, _ = step_agent(st, T if closed else T0)
        else:
            T, ns = learn(T, ns, x[2], inst["R"], inst["cap"])
    return T, ns


def serialise(hist, first, second):
    contents = [x for x in hist if x[0] == "lesson" and x[1] == first] + \
               [x for x in hist if x[0] == "lesson" and x[1] == second]
    it = iter(contents)
    return [next(it) if x[0] == "lesson" else x for x in hist]


def behaviour(T, tape):
    """Eventual (head, tape) cycle of program T alone on `tape`, up to rotation of the ring and
    choice of starting point (state labels do not enter)."""
    s, h, t = 0, 0, tape
    seen, seq = {}, []
    while (s, h, t) not in seen:
        seen[(s, h, t)] = len(seq)
        seq.append((h, t))
        (s, h, t), _ = step_agent((s, h, t), T)
    cyc = seq[seen[(s, h, t)]:]
    best = None
    for d in range(L):
        rot = [((hh - d) % L, ((tt >> d) | (tt << (L - d))) & 0xFF if d else tt) for hh, tt in cyc]
        for k in range(len(rot)):
            cand = tuple(rot[k:] + rot[:k])
            best = cand if best is None or cand < best else best
    return best


def check(inst, closed):
    C = inst["learner"]
    A, B = [j for j in range(3) if j != C]
    hist = simulate(inst, closed)
    P = replay(inst, hist, closed)[0]
    PA = replay(inst, serialise(hist, A, B), closed)[0]
    PB = replay(inst, serialise(hist, B, A), closed)[0]
    differ = sum(1 for tp in range(256)
                 if behaviour(P, tp) != behaviour(PA, tp) and behaviour(P, tp) != behaviour(PB, tp))
    lessons_from_learned_states = sum(1 for x in hist if x[0] == "lesson" and x[2][0] >= inst["n"])
    return differ, lessons_from_learned_states, len(hist), P


if __name__ == "__main__":
    inst = json.load(open(sys.argv[1]))
    progs = {}
    for closed in (True, False):
        d, ll, n, progs[closed] = check(inst, closed)
        print(f"{'closed' if closed else 'open  '} loop: history of {n} steps, "
              f"{ll} lessons sent from a teacher's LEARNED state; "
              f"actual program behaves unlike both serial programs on {d} of 256 fresh tapes")
    same_table = progs[True] == progs[False]
    d = sum(1 for tp in range(256) if behaviour(progs[True], tp) != behaviour(progs[False], tp))
    print(f"closed-loop program vs open-loop program: {'same' if same_table else 'different'} table; "
          f"behave differently on {d} of 256 fresh tapes")
