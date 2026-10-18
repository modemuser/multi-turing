"""Closed-loop decomposition: does a learner's order-dependence come with order-dependence of
what its sources EMIT?

For each instance (closed loop, complete graph, 24 exogenous schedules) and each agent X:
  beh(X, σ) = X's emitted event stream as a normalised eventually-periodic word (prefix, period),
              so the same behaviour at a different speed counts as equal
  tab(X, σ) = X's set of learned tables in the cycle (up to relabelling of appended states)
Then per learner Y with sources S(Y):
  tab-dependent  = tab(Y, ·) varies across schedules
  stream-varying = beh(X, ·) varies for some source X of Y
Hypothesis (fixed-point shape of reflexivity): for learners whose open-loop exposure effect is ~0
(overwrite), closed-loop tab-dependence occurs only together with source stream variation.

    uv run python -m mt.closed_loop results/swarm_closed/SUMMARY.md results/swarm_N8_probe results/swarm_N8_append
"""
from __future__ import annotations

from .paths import PROBE400

import json
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd

from .relabel import canon_table
from .report import md
from .swarm import GRAPHS, M, SwarmInstance, exo_schedules, run

N = 8
GRAPH = "complete"


def normalise(prefix, period):
    """Canonical form of the infinite word prefix·period^ω."""
    prefix, period = list(prefix), list(period)
    for p in range(1, len(period) + 1):                     # primitive root of the period
        if len(period) % p == 0 and period[:p] * (len(period) // p) == period:
            period = period[:p]
            break
    while prefix and prefix[-1] == period[-1]:              # roll the period left into the prefix
        prefix.pop()
        period = [period[-1]] + period[:-1]
    return tuple(prefix), tuple(period)


def emissions(inst, trace, transient, word):
    """Per agent: normalised emitted word over the run (trace = transient + one joint period)."""
    ev = [[] for _ in range(M)]
    k = [0] * M
    for i, c in enumerate(trace):
        X = "ABC".index(word[c[-1]])
        s, h, t, T = c[4 * X:4 * X + 4]
        if i == transient:
            k = [len(e) for e in ev]
        ev[X].append((s, T[4 * (2 * s + ((t >> h) & 1))]))
    if transient >= len(trace):
        k = [len(e) for e in ev]
    return [normalise(ev[j][:k[j]], ev[j][k[j]:]) if ev[j][k[j]:] else (tuple(ev[j]), ()) for j in range(M)]


def tables(inst, cycle):
    out = []
    for j in range(M):
        S = set()
        for c in cycle:
            T = tuple(0 if i % 4 == 3 else v for i, v in enumerate(c[4 * j + 3]))
            S.add(canon_table(T, inst.n, c[4 * M + 2][j], inst.capacity))
        out.append(frozenset(S))
    return out


def analyse(args):
    iid, inst = args
    beh = [set() for _ in range(M)]
    tab = [set() for _ in range(M)]
    for _, w in exo_schedules():
        r = run(inst, "on", ("exo", w), GRAPH, N, budget=200_000, keep_trace=True)
        if r.kind != "cycle":
            return None
        for j, e in enumerate(emissions(inst, r.trace, r.transient, w)):
            beh[j].add(e)
        for j, tb in enumerate(tables(inst, r.cycle)):
            tab[j].add(tb)
    rows = []
    for Y in range(M):
        srcs = [X for X in range(M) if Y in GRAPHS[GRAPH][X]]          # agents that Y observes
        rows.append(dict(inst_id=iid, Y=Y, tab_dep=len(tab[Y]) > 1, own_beh_dep=len(beh[Y]) > 1,
                         source_stream_varies=any(len(beh[X]) > 1 for X in srcs)))
    return rows


def run_dir(d: Path, ids=None):
    insts = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        if ids is None or j["inst_id"] in ids:
            insts[j["inst_id"]] = SwarmInstance.from_json(j)
    with mp.Pool() as pool:
        out = pool.map(analyse, list(insts.items()), chunksize=4)
    return pd.DataFrame([r for rs in out if rs for r in rs]), sum(o is None for o in out)


def main(out_path: Path, dirs):
    probe400 = PROBE400
    keep = {json.loads(l)["inst_id"] for l in open(probe400)} if probe400.exists() else None
    L = ["# Closed loop: learned-table dependence vs source stream variation\n",
         "Exploratory probe (complete graph, closed loop, 24 exogenous schedules). One row per learner "
         "(agent × instance). *tab-dependent*: the learner's learned tables depend on the schedule. "
         "*source stream varies*: what at least one of its sources emits depends on the schedule.\n"]
    for d in dirs:
        d = Path(d)
        kind = json.loads((d / "meta.json").read_text()).get("edit_kind", "set")
        df, unresolved = run_dir(d, keep if kind == "set" else None)
        df.to_csv(d / "closed_loop.csv", index=False)
        x = pd.crosstab(df.source_stream_varies.map({True: "source stream varies", False: "source streams fixed"}),
                        df.tab_dep.map({True: "learner tab-dependent", False: "learner tab-invariant"}))
        L.append(f"## Rule set: {kind} ({df.inst_id.nunique()} instances; {unresolved} skipped as unresolved)\n")
        L.append(md(x.reset_index().rename(columns={x.index.name: ""})))
        both = pd.crosstab(df.own_beh_dep.map({True: "own behaviour varies", False: "own behaviour fixed"}),
                           df.tab_dep.map({True: "own tables vary", False: "own tables fixed"}))
        L.append("\nThe learner's own behaviour vs its own learned tables:\n")
        L.append(md(both.reset_index().rename(columns={both.index.name: ""})))
        L.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
