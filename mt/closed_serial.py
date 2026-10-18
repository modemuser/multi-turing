"""Closed-loop serialisability, defined the same way for learning and for physical coupling.

View one agent C as a transducer of its INPUT HISTORY u: a sequence of
    ("o",)          C's own step (uses C's current table; changes C's state, head, tape)
    ("x", X, e)     an influence from agent X carrying event e = (pre-state, written symbol)
                      learn       -> rewrites C's rules (the engine's learning semantics)
                      couple_once -> writes the observed symbol onto C's tape under C's head
                                     (at most once per trigger, volume-matched to learning)
A serialisation keeps the SHAPE of u (own steps and influence slots stay where they are) and
reassigns influence contents: all of A's influences (in their original order) first, then all of
B's, or the reverse. C *synthesises* in a run if its state after u differs from both
serialisations. For learning we also compare the knowledge layer (rules) alone.

    uv run python -m mt.closed_serial results/swarm_closed/SERIAL.md
"""
from __future__ import annotations

from .paths import PROBE400

import json
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd

from .relabel import canon_table
from .report import md, wilson
from .swarm import M, SwarmInstance, exo_schedules, run
from .synthesis import learn

N = 8
GRAPH = "complete"


def own_step(st, inst):
    s, h, t, T, ns, fired = st
    r = (t >> h) & 1
    b = 4 * (2 * s + r)
    w, m, nx = T[b], T[b + 1], T[b + 2]
    t = (t | (1 << h)) if w else (t & ~(1 << h))
    h = (h + 1) % N if m else (h - 1) % N
    return (nx, h, t, T, ns, fired)


def influence(st, event, inst, mode):
    s, h, t, T, ns, fired = st
    q, w = event
    trig = 2 * q + w
    if mode == "learn":
        T, ns, fired = learn((T, ns, fired), event, inst)
        return (s, h, t, T, ns, fired)
    # couple_once
    if inst.R[trig] is None or trig in fired:
        return st
    t = (t | (1 << h)) if w else (t & ~(1 << h))
    return (s, h, t, T, ns, fired | {trig})


def history(inst, trace, word, C):
    """C's input history along an engine trace (complete graph: C observes every other agent)."""
    u = []
    for c in trace:
        X = "ABC".index(word[c[-1]])
        s, h, t, T = c[4 * X:4 * X + 4]
        if X == C:
            u.append(("o",))
        else:
            u.append(("x", X, (s, T[4 * (2 * s + ((t >> h) & 1))])))
    return u


def replay(st, u, inst, mode):
    for x in u:
        st = own_step(st, inst) if x[0] == "o" else influence(st, x[2], inst, mode)
    return st


def serialise(u, first, second):
    contents = [x for x in u if x[0] == "x" and x[1] == first] + [x for x in u if x[0] == "x" and x[1] == second]
    it = iter(contents)
    return [next(it) if x[0] == "x" else x for x in u]


def canon_state(st, inst):
    s, h, t, T, ns, _ = st
    mask = (1 << N) - 1
    ht = min((((h - d) % N), (((t >> d) | (t << (N - d))) & mask) if d else t) for d in range(N))
    Tz = tuple(0 if i % 4 == 3 else v for i, v in enumerate(T))
    return (s, ht, canon_table(Tz, inst.n, ns, inst.capacity))


def canon_rules(st, inst):
    s, h, t, T, ns, _ = st
    Tz = tuple(0 if i % 4 == 3 else v for i, v in enumerate(T))
    return canon_table(Tz, inst.n, ns, inst.capacity)


def analyse(args):
    iid, inst, mode = args
    eng = "on" if mode == "learn" else "couple_once"
    rows = []
    for nm, w in exo_schedules():
        r = run(inst, eng, ("exo", w), GRAPH, N, budget=200_000, keep_trace=True)
        if r.kind != "cycle":
            continue
        for C in range(M):
            A, B = [j for j in range(M) if j != C]
            u = history(inst, r.trace, w, C)
            st0 = (0, 0, 0, inst.tables[C], (inst.ns0 or (inst.n,) * M)[C], frozenset())
            full = replay(st0, u, inst, mode)
            ab = replay(st0, serialise(u, A, B), inst, mode)
            ba = replay(st0, serialise(u, B, A), inst, mode)
            g, sab, sba = (canon_state(x, inst) for x in (full, ab, ba))
            rows.append(dict(inst_id=iid, C=C, sched=nm, mode=mode,
                             n_infl=sum(x[0] == "x" for x in u),
                             synth_state=g not in (sab, sba),
                             serial_orders_differ=sab != sba,
                             synth_rules=(canon_rules(full, inst) not in (canon_rules(ab, inst), canon_rules(ba, inst)))
                             if mode == "learn" else None))
    return rows


def rate(s):
    s = s.dropna().astype(bool)
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}] (n={n})" if n else "–"


def main(out: Path):
    from .swarm_sweep import with_edit_kind
    probe = PROBE400
    base = [json.loads(l) for l in open(probe)]
    L = ["# Closed-loop serialisability: learning vs physical coupling\n",
         "Exploratory probe. Complete graph, closed loop, 24 exogenous schedules, 400 instances × 3 agents. "
         "*Synthesis*: the agent's state after its input history differs from both serialisations (same "
         "slots, A's influences first or B's first). Coupling is the volume-matched variant. Rates are over "
         "agent × schedule pairs (95% Wilson CI), and the instance-level rate counts any agent or schedule.\n"]
    for rs in ("set", "append"):
        insts = [(j["inst_id"], with_edit_kind(SwarmInstance.from_json(j), rs, j["inst_id"])) for j in base]
        rows = []
        for mode in ("learn", "couple_once"):
            with mp.Pool() as pool:
                out_rows = pool.map(analyse, [(i, inst, mode) for i, inst in insts], chunksize=4)
            rows += [r for rr in out_rows for r in rr]
        df = pd.DataFrame(rows)
        df.to_parquet(out.parent / f"serial_{rs}.parquet")
        L.append(f"## Rule set: {rs}\n")
        tab = []
        for mode, sub in df.groupby("mode"):
            inst_level = sub.groupby("inst_id").synth_state.any()
            tab.append({"channel": mode, "synthesis (full state)": rate(sub.synth_state),
                        "instances with any synthesis": rate(inst_level),
                        "the two serial orders differ": rate(sub.serial_orders_differ),
                        "synthesis of rules only": rate(sub.synth_rules) if mode == "learn" else "–"})
        L.append(md(pd.DataFrame(tab)))
        L.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_closed/SERIAL.md"))
