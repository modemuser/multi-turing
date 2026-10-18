"""Synthesis probe (open loop, complete graph, append instances).

For each learner Y with sources A, B (the other two agents):
  interleaved  = Y's learned table in the cycle of the real open-loop run, per exogenous schedule
  seq_AB       = fold Y over A's event stream until stable, then over B's until stable
  seq_BA       = the reverse
  blocks_AB/BA = repeat whole stabilised blocks A, B, A, B, ... until a fixed point (coarse interleaving)
Y *synthesises* (strict) under a schedule if its stabilised interleaved table is neither seq_AB nor
seq_BA. *fine*: also not equal to either block fixed point. Tables are compared up to relabelling of
appended states (route bits zeroed: inert under exogenous schedules).

    uv run python -m mt.synthesis results/swarm_N8_append
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd

from .commute_check import noncommuting_ops
from .relabel import canon_table
from .swarm import APPEND, APPEND_ONCE, M, SwarmInstance, _append, _apply, edit_op, exo_schedules, run

N = 8
MAX_PERIODS = 2000


def event_stream(T, N=N):
    """Fixed emission of an agent acting on table T alone (open loop): (prefix, period) of
    (pre-state, written) events."""
    s = h = t = 0
    seen, ev = {}, []
    while (s, h, t) not in seen:
        seen[(s, h, t)] = len(ev)
        r = (t >> h) & 1
        b = 4 * (2 * s + r)
        w, m, nx = T[b], T[b + 1], T[b + 2]
        ev.append((s, w))
        t = (t | (1 << h)) if w else (t & ~(1 << h))
        h = (h + 1) % N if m else (h - 1) % N
        s = nx
    k = seen[(s, h, t)]
    return ev[:k], ev[k:]


def learn(state, event, inst: SwarmInstance):
    """One observation, with exactly the engine's SET / APPEND / APPEND_ONCE semantics.
    state = (T, ns, fired): fired = triggers whose APPEND_ONCE rule has already been used here
    (marked even if the append itself was a no-op, as in the engine)."""
    T, ns, fired = state
    q, w = event
    trig = 2 * q + w
    x = inst.R[trig]
    if x is None:
        return state
    if edit_op(x) in (APPEND, APPEND_ONCE):
        if edit_op(x) == APPEND_ONCE:
            if trig in fired:
                return state
            fired = fired | {trig}
        T, ns, _ = _append(T, x[0], ns, inst.capacity)
        return (T, ns, fired)
    T, _, _ = _apply(T, inst.R, q, w, False, ns)
    return (T, ns, fired)


def initial_state(inst, Y):
    return (inst.tables[Y], (inst.ns0 or (inst.n,) * M)[Y], frozenset())


def fold_until_stable(state, stream, inst):
    """Feed prefix, then whole periods until the state at a period boundary repeats.
    Returns (state, stable?) where stable = fixed point under one period."""
    prefix, period = stream
    for e in prefix:
        state = learn(state, e, inst)
    seen = []
    for _ in range(MAX_PERIODS):
        if state in seen:
            return state, seen[-1] == state
        seen.append(state)
        for e in period:
            state = learn(state, e, inst)
    return state, False


def canon(state, inst):
    T, ns = state[0], state[1]
    T = tuple(0 if i % 4 == 3 else v for i, v in enumerate(T))
    return canon_table(T, inst.n, ns, inst.capacity), ns


def analyse(args):
    iid, inst = args
    streams = [event_stream(inst.tables[j]) for j in range(M)]
    rows = []
    interleaved = {}
    merges = {}
    for nm, w in exo_schedules():
        r = run(inst, "open", ("exo", w), "complete", N, budget=200_000, keep_trace=True)
        interleaved[nm] = r
        if r.kind == "cycle":
            merges[nm] = effective_lessons(inst, r.trace, w)
        r.trace = None
    for Y in range(M):
        A, B = [j for j in range(M) if j != Y]
        s0 = initial_state(inst, Y)
        ab, ok1 = fold_until_stable(s0, streams[A], inst)
        ab, ok2 = fold_until_stable(ab, streams[B], inst)
        ba, ok3 = fold_until_stable(s0, streams[B], inst)
        ba, ok4 = fold_until_stable(ba, streams[A], inst)
        seq_stable = ok1 and ok2 and ok3 and ok4

        def blocks(first, second):
            st = s0
            seen = []
            for _ in range(200):
                if st in seen:
                    return st, seen[-1] == st
                seen.append(st)
                st, _ = fold_until_stable(st, streams[first], inst)
                st, _ = fold_until_stable(st, streams[second], inst)
            return st, False
        bab, okb1 = blocks(A, B)
        bba, okb2 = blocks(B, A)
        seq = {canon(ab, inst), canon(ba, inst)}
        blk = seq | {canon(bab, inst), canon(bba, inst)}
        for nm, r in interleaved.items():
            if r.kind != "cycle":
                continue
            tabs = {(c[4 * Y + 3], c[4 * M + 2][Y]) for c in r.cycle}
            if len(tabs) != 1:
                rows.append(dict(inst_id=iid, Y=Y, sched=nm, stable=False))
                continue
            g = canon(next(iter(tabs)), inst)
            src, merge, visited = merges[nm][Y]                  # effective-lesson sources, full merge
            nA, nB = src.count(A), src.count(B)
            csand = conflict_sandwich(merge, visited, inst)
            cyc = precedence_cycle(merge, visited, inst)
            rows.append(dict(inst_id=iid, Y=Y, sched=nm, stable=True, seq_stable=seq_stable,
                             blocks_stable=okb1 and okb2, seq_differ=len(seq) > 1,
                             strict=g not in seq, fine=g not in blk,
                             eff_A=nA, eff_B=nB, sandwich=has_sandwich(src), conflict_sandwich=csand,
                             precedence_cycle=cyc))
    return rows


def effective_lessons(inst, trace, word):
    """For each learner Y: (effective, merge, visited).
    effective = source labels of lessons that changed Y's learned state, in delivery order;
    merge = all delivered lessons as (source, event); visited = distinct states Y passed through."""
    states = [initial_state(inst, Y) for Y in range(M)]
    out = [[] for _ in range(M)]
    merge = [[] for _ in range(M)]
    visited = [{states[Y]} for Y in range(M)]
    for c in trace:
        X = "ABC".index(word[c[-1]])
        s, h, t = c[4 * X:4 * X + 3]
        wr = inst.tables[X][4 * (2 * s + ((t >> h) & 1))]
        for Y in range(M):
            if Y == X:
                continue
            new = learn(states[Y], (s, wr), inst)
            if new[:2] != states[Y][:2]:
                out[Y].append(X)
            merge[Y].append((X, (s, wr)))
            states[Y] = new
            visited[Y].add(new)
    return [(out[Y], merge[Y], visited[Y]) for Y in range(M)]


def conflict_sandwich(merge, visited, inst) -> bool:
    """Exact-conflict sandwich over ALL delivered lessons: positions i < j < k, i and k from one
    source, j from the other, with (e_i, e_j) and (e_j, e_k) conflicting. Two lessons conflict if
    they fail to commute on some state Y actually visited."""
    events = sorted({e for _, e in merge})
    vis = list(visited)
    conf = {}
    for a in events:
        for b in events:
            if a < b:
                c = any(learn(learn(T, a, inst), b, inst)[:2] != learn(learn(T, b, inst), a, inst)[:2] for T in vis)
                conf[(a, b)] = conf[(b, a)] = c
    src = [x for x, _ in merge]
    ev = [e for _, e in merge]
    n = len(merge)
    # linear scan: prefix[j] / suffix[j] = set of (source, event) seen before / after position j
    prefix, seen = [], set()
    for j in range(n):
        prefix.append(frozenset(seen))
        seen.add((src[j], ev[j]))
    suffix, seen = [None] * n, set()
    for j in range(n - 1, -1, -1):
        suffix[j] = frozenset(seen)
        seen.add((src[j], ev[j]))
    for j in range(n):
        for (si, ei) in prefix[j]:
            if si == src[j] or ei == ev[j] or not conf.get((ei, ev[j]), False):
                continue
            if any(sk == si and ek != ev[j] and conf.get((ev[j], ek), False) for sk, ek in suffix[j]):
                return True
    return False


def precedence_cycle(merge, visited, inst) -> bool:
    """L6's actual condition: the precedence graph A<->B has a cycle, i.e. some conflicting pair is
    delivered A-before-B AND some (possibly different) conflicting pair is delivered B-before-A.
    Conflict = fail to commute on some state in `visited`."""
    events = sorted({e for _, e in merge})
    vis = list(visited)
    conf = {}
    for a in events:
        for b in events:
            if a < b:
                c = any(learn(learn(T, a, inst), b, inst)[:2] != learn(learn(T, b, inst), a, inst)[:2] for T in vis)
                conf[(a, b)] = conf[(b, a)] = c
    srcs = sorted({x for x, _ in merge})
    if len(srcs) < 2:
        return False
    S0 = srcs[0]
    seen = {x: set() for x in srcs}           # events delivered so far, per source
    fwd = bwd = False                         # S0-before-other / other-before-S0 conflicting pair seen
    for x, e in merge:
        for y in srcs:
            if y == x:
                continue
            if any(e2 != e and conf.get((e2, e), False) for e2 in seen[y]):
                if y == S0:
                    fwd = True
                else:
                    bwd = True
        seen[x].add(e)
        if fwd and bwd:
            return True
    return False


def has_sandwich(src) -> bool:
    """Effective lessons x .. y .. x' with x, x' from one source and y from the other."""
    runs = [k for i, k in enumerate(src) if i == 0 or src[i - 1] != k]   # collapse consecutive repeats
    return len(runs) >= 3


def main(d: Path):
    insts = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        insts[j["inst_id"]] = SwarmInstance.from_json(j)
    with mp.Pool() as pool:
        rows = [r for rs in pool.map(analyse, list(insts.items()), chunksize=4) for r in rs]
    df = pd.DataFrame(rows)
    out = d / "synthesis"
    out.mkdir(exist_ok=True)
    df.to_parquet(out / "runs.parquet")
    kind = {i: (noncommuting_ops(inst) or "all commute") for i, inst in insts.items()}
    res = pd.read_parquet(d / "results.parquet")
    dep = res[res.condition == "Lo_exo_complete"].set_index("inst_id").confluent_tables_local == False  # noqa: E712
    st = df[df.stable & df.seq_stable]
    inst_level = st.groupby("inst_id").agg(strict=("strict", "any"), fine=("fine", "any"),
                                           seq_differ=("seq_differ", "any"))
    inst_level["kind"] = inst_level.index.map(kind)
    inst_level["order_dependent"] = inst_level.index.map(dep)
    summary = {
        "learner-schedule pairs": len(df),
        "pairs with stabilised interleaved table": int(df.stable.sum()),
        "…and stabilised sequential folds": len(st),
        "instances analysed": len(inst_level),
    }
    print(summary)
    print("\nby commutation class (instance-level: any learner, any schedule):")
    print(inst_level.groupby("kind")[["strict", "fine", "seq_differ"]].agg(["mean", "sum", "size"]).round(3))
    st2 = df[df.stable & df.seq_stable].copy()
    st2["case"] = st2.apply(lambda r: "sandwich" if r.sandwich else
                            ("each source <=1 effective lesson" if max(r.eff_A, r.eff_B) <= 1 else
                             "no sandwich (one source's lessons all before the other's)"), axis=1)
    print("\nL6 test, precedence-graph cycle (the theorem's actual condition):")
    print(st2.groupby("precedence_cycle").agg(pairs=("strict", "size"), synthesis=("strict", "sum"),
                                              rate=("strict", "mean")).round(4))
    st2.groupby("precedence_cycle").agg(pairs=("strict", "size"), synthesis=("strict", "sum")).to_csv(out / "L6_cycle.csv")
    print("\nL6 test with exact conflicts over all lessons (single-pivot sandwich):")
    print(st2.groupby("conflict_sandwich").agg(pairs=("strict", "size"), synthesis=("strict", "sum"),
                                               rate=("strict", "mean")).round(4))
    st2.groupby("conflict_sandwich").agg(pairs=("strict", "size"), synthesis=("strict", "sum")).to_csv(out / "L6_exact.csv")
    print("\nL6 test, learner-schedule pairs:")
    print(st2.groupby("case").agg(pairs=("strict", "size"), synthesis=("strict", "sum"),
                                  rate=("strict", "mean")).round(4))
    st2.groupby("case").agg(pairs=("strict", "size"), synthesis=("strict", "sum")).to_csv(out / "L6_test.csv")
    print("\namong open-loop order-dependent instances:")
    od = inst_level[inst_level.order_dependent == True]  # noqa: E712
    print(od[["strict", "fine", "seq_differ"]].agg(["mean", "sum"]).round(3), "n =", len(od))
    inst_level.to_csv(out / "instances.csv")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_N8_append"))
