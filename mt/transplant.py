"""Transplant test: does a synthesised PROGRAM carry its new shape into fresh situations?

For each agent C and closed-loop run (complete graph, 24 exogenous schedules):
  P_full, P_AB, P_BA = C's program after its actual input history and after the two serialisations
  (same definition as mt.closed_serial); P_orig = C's initial program.
Each program is placed alone on FRESH tapes (blank + 3 random, head 0, state 0), runs without any
learning, and its eventual behaviour is recorded as the cyclic sequence of (head, tape), up to
translation and choice of starting point. State labels do not enter, so relabelling is no difference.

  generalises = on some fresh tape, P_full behaves differently from BOTH P_AB and P_BA
  (i.e. the synthesis is not just a different table but a different machine elsewhere too)

Physical coupling never changes programs, so its transplanted agents are always P_orig: the
control is 0 by construction, and is reported as such.

    uv run python -m mt.transplant results/swarm_closed/TRANSPLANT.md
"""
from __future__ import annotations

from .paths import PROBE400

import json
import multiprocessing as mp
from functools import lru_cache
import random
import sys
from pathlib import Path

import pandas as pd

from .closed_serial import canon_rules, history, replay, serialise
from .report import md, wilson
from .swarm import M, SwarmInstance, exo_schedules, run

N = 8
GRAPH = "complete"
FRESH = [0] + [random.Random(f"fresh-{i}").randrange(1 << N) for i in range(3)]


MAX_BEHAVIOUR_STEPS = None     # set by callers that need a cap; None = exact, unbounded


@lru_cache(maxsize=200_000)
def behaviour(T, tape, N=N):
    """Eventual behaviour of program T alone on `tape`: canonical cyclic sequence of (head, tape).
    Returns the string "unresolved" if MAX_BEHAVIOUR_STEPS is set and exceeded."""
    s, h, t = 0, 0, tape
    seen, seq = {}, []
    while (s, h, t) not in seen:
        if MAX_BEHAVIOUR_STEPS is not None and len(seq) >= MAX_BEHAVIOUR_STEPS:
            return "unresolved"
        seen[(s, h, t)] = len(seq)
        seq.append((h, t))
        r = (t >> h) & 1
        b = 4 * (2 * s + r)
        w, m, nx = T[b], T[b + 1], T[b + 2]
        t = (t | (1 << h)) if w else (t & ~(1 << h))
        h = (h + 1) % N if m else (h - 1) % N
        s = nx
    cyc = seq[seen[(s, h, t)]:]
    mask = (1 << N) - 1
    best = None
    for d in range(N):
        shifted = [((hh - d) % N, (((tt >> d) | (tt << (N - d))) & mask) if d else tt) for hh, tt in cyc]
        k = least_rotation(shifted)
        cand = tuple(shifted[k:] + shifted[:k])
        if best is None or cand < best:
            best = cand
    return best


def least_rotation(S) -> int:
    """Booth's algorithm: start index of the lexicographically least rotation of S, in O(len(S)).
    Gives the same result as trying every rotation (tests/test_swarm.py checks this)."""
    S2 = list(S) + list(S)
    f = [-1] * len(S2)
    k = 0
    for j in range(1, len(S2)):
        sj = S2[j]
        i = f[j - k - 1]
        while i != -1 and sj != S2[k + i + 1]:
            if sj < S2[k + i + 1]:
                k = j - i - 1
            i = f[i]
        if sj != S2[k + i + 1]:
            if sj < S2[k]:
                k = j
            f[j - k] = -1
        else:
            f[j - k] = i + 1
    return k


def analyse(args):
    iid, inst = args
    rows = []
    for nm, w in exo_schedules():
        r = run(inst, "on", ("exo", w), GRAPH, N, budget=200_000, keep_trace=True)
        if r.kind != "cycle":
            continue
        for C in range(M):
            A, B = [j for j in range(M) if j != C]
            u = history(inst, r.trace, w, C)
            st0 = (0, 0, 0, inst.tables[C], (inst.ns0 or (inst.n,) * M)[C], frozenset())
            full = replay(st0, u, inst, "learn")
            ab = replay(st0, serialise(u, A, B), inst, "learn")
            ba = replay(st0, serialise(u, B, A), inst, "learn")
            rules_synth = canon_rules(full, inst) not in (canon_rules(ab, inst), canon_rules(ba, inst))
            beh = {k: [behaviour(x[3], tp) for tp in FRESH] for k, x in (("full", full), ("ab", ab), ("ba", ba), ("orig", st0))}
            generalises = any(beh["full"][i] != beh["ab"][i] and beh["full"][i] != beh["ba"][i] for i in range(len(FRESH)))
            changed = any(beh["full"][i] != beh["orig"][i] for i in range(len(FRESH)))
            rows.append(dict(inst_id=iid, C=C, sched=nm, rules_synth=rules_synth,
                             generalises=generalises, learned_changes_behaviour=changed))
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
    L = ["# Transplant test: do synthesised programs carry into fresh situations?\n",
         "Exploratory probe. Closed loop, complete graph, 24 schedules, 400 instances × 3 agents. Each agent's "
         "learned program (actual history vs the two serialisations) runs alone on 4 fresh tapes (blank + 3 "
         "random) without learning. *generalises*: on some fresh tape it behaves differently from both "
         "serialised programs. Physical coupling never changes programs, so its transplant rate is 0 by "
         "construction.\n"]
    for rs in ("set", "append"):
        insts = [(j["inst_id"], with_edit_kind(SwarmInstance.from_json(j), rs, j["inst_id"])) for j in base]
        with mp.Pool() as pool:
            rows = [r for rr in pool.map(analyse, insts, chunksize=4) for r in rr]
        df = pd.DataFrame(rows)
        df.to_parquet(out.parent / f"transplant_{rs}.parquet")
        syn = df[df.rules_synth]
        L.append(f"## Rule set: {rs}\n")
        L.append(md(pd.DataFrame([{
            "agent × schedule pairs": len(df),
            "learned program behaves differently from original (fresh tapes)": rate(df.learned_changes_behaviour),
            "rules synthesised": rate(df.rules_synth),
            "… of those, synthesis generalises to fresh tapes": rate(syn.generalises),
            "generalising synthesis, all pairs": rate(df.generalises),
            "instances with any generalising synthesis": rate(df.groupby("inst_id").generalises.any()),
        }]).T.reset_index().rename(columns={"index": "measure", 0: "value"})))
        L.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_closed/TRANSPLANT.md"))
