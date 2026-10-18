"""New-brick witnesses (append rule set, complete graph, 24 schedules, 400 instances x 3 agents).

For every agent C and schedule sigma, in CLOSED loop and in OPEN loop (same instance, same schedule):
  P_full, P_AB, P_BA = C's program after its actual input history and after the two serialisations
  rules_synth        = P_full differs (up to relabelling) from both serial programs
  new brick (on a tape set) = on some fresh tape of that set, P_full alone behaves differently from
                              BOTH P_AB and P_BA
Tape sets: 4 fresh tapes (as in mt.transplant), ALL 256 tapes of length 8 (exhaustive), and 64
tapes of length 16 (blank + 63 random); a program doesn't depend on tape length.

A witness is *feedback-required* if it is a new brick in the closed loop but not in the open loop
at the same (instance, schedule, agent): the new program exists only because what agents learned
fed back into what they taught each other.

    uv run python -m mt.witness results/swarm_closed/WITNESS.md
"""
from __future__ import annotations

from .paths import PROBE400

import json
import multiprocessing as mp
import random
import sys
from pathlib import Path

import pandas as pd

from .closed_serial import canon_rules, history, influence, replay, serialise
from .report import md, wilson
from .swarm import M, SwarmInstance, exo_schedules, run
from .transplant import FRESH, behaviour

GRAPH = "complete"
TAPESETS = {
    "4 tapes (N=8)": (8, tuple(FRESH)),
    "all 256 tapes (N=8)": (8, tuple(range(256))),
    "64 tapes (N=16)": (16, (0,) + tuple(random.Random("fresh16").randrange(1 << 16) for _ in range(63))),
}


def own_step_open(st, orig_T, N=8):
    """Open loop: the agent acts on its ORIGINAL table; its learned table is carried along."""
    s, h, t, T, ns, fired = st
    r = (t >> h) & 1
    b = 4 * (2 * s + r)
    w, m, nx = orig_T[b], orig_T[b + 1], orig_T[b + 2]
    t = (t | (1 << h)) if w else (t & ~(1 << h))
    h = (h + 1) % N if m else (h - 1) % N
    return (nx, h, t, T, ns, fired)


def replay_open(st, u, inst, orig_T):
    for x in u:
        st = own_step_open(st, orig_T) if x[0] == "o" else influence(st, x[2], inst, "learn")
    return st


def new_brick(P, Pab, Pba, tapeset):
    """True if some fresh tape shows a difference; tapes where any of the three programs is
    unresolved (only possible with a step cap) are skipped and counted in UNRESOLVED_TAPES."""
    N, tapes = tapeset
    for tp in tapes:
        b, bab, bba = behaviour(P, tp, N), behaviour(Pab, tp, N), behaviour(Pba, tp, N)
        if "unresolved" in (b, bab, bba):
            UNRESOLVED_TAPES[0] += 1
            continue
        if b != bab and b != bba:
            return True
    return False


UNRESOLVED_TAPES = [0]


def programs(inst, trace, w, C, loop):
    A, B = [j for j in range(M) if j != C]
    u = history(inst, trace, w, C)
    st0 = (0, 0, 0, inst.tables[C], (inst.ns0 or (inst.n,) * M)[C], frozenset())
    if loop == "closed":
        rep = lambda uu: replay(st0, uu, inst, "learn")
    else:
        rep = lambda uu: replay_open(st0, uu, inst, inst.tables[C])
    return rep(u), rep(serialise(u, A, B)), rep(serialise(u, B, A)), len(u)


def analyse(args):
    iid, inst = args[:2]
    if len(args) > 2:
        from . import transplant
        transplant.MAX_BEHAVIOUR_STEPS = args[2]
    UNRESOLVED_TAPES[0] = 0
    rows = []
    for nm, w in exo_schedules():
        runs = {loop: run(inst, "on" if loop == "closed" else "open", ("exo", w), GRAPH, 8, budget=200_000,
                          keep_trace=True) for loop in ("closed", "open")}
        if any(r.kind != "cycle" for r in runs.values()):
            continue
        for C in range(M):
            row = dict(inst_id=iid, k=inst.k, sched=nm, C=C, steps=runs["closed"].steps)
            for loop, r in runs.items():
                full, ab, ba, n_u = programs(inst, r.trace, w, C, loop)
                syn = canon_rules(full, inst) not in (canon_rules(ab, inst), canon_rules(ba, inst))
                row[f"{loop}_rules_synth"] = syn
                for name, ts in TAPESETS.items():
                    if loop == "open" and name != "all 256 tapes (N=8)":
                        continue
                    row[f"{loop}_brick[{name}]"] = syn and new_brick(full[3], ab[3], ba[3], ts)
            row["unresolved_tapes_so_far"] = UNRESOLVED_TAPES[0]
            rows.append(row)
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
    insts = [(j["inst_id"], with_edit_kind(SwarmInstance.from_json(j), "append", j["inst_id"])) for j in base]
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else None
    rows = []
    with mp.Pool(procs) as pool:
        for i, rr in enumerate(pool.imap_unordered(analyse, [(a, b, cap) for a, b in insts], chunksize=1), 1):
            rows += rr
            if i % 25 == 0:
                print(f"  {i}/{len(insts)} instances", flush=True)
    df = pd.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out.parent / f"{out.stem}_runs.parquet")
    syn = df[df.closed_rules_synth]
    L = ["# New-brick witnesses: detection limit and the role of feedback\n",
         "Exploratory probe: append rule set, complete graph, 24 schedules, 400 instances × 3 agents. "
         "*New brick*: the synthesised program, transplanted alone onto a fresh tape, behaves differently "
         "from both serial alternatives on at least one tape of the set.\n",
         "## 1. Detection limit (closed loop)\n"]
    rows = []
    for name in TAPESETS:
        col = f"closed_brick[{name}]"
        rows.append({"fresh tapes": name, "of synthesised programs": rate(syn[col]),
                     "instances with ≥1 new brick": rate(df.groupby("inst_id")[col].any())})
    L.append(md(pd.DataFrame(rows)))
    if cap:
        L.append(f"\nStep cap {cap} per transplanted run: "
                 f"{int(df.groupby('inst_id').unresolved_tapes_so_far.max().sum())} program × tape evaluations "
                 "hit the cap and were skipped (counted as no difference: this makes the rates lower bounds).\n")
    ex = "closed_brick[all 256 tapes (N=8)]"
    df["feedback_required"] = df[ex] & ~df["open_brick[all 256 tapes (N=8)]"]
    df["exposure_suffices"] = df[ex] & df["open_brick[all 256 tapes (N=8)]"]
    L.append("\n## 2. Does the new brick need feedback? (same instance, schedule and agent; all 256 tapes)\n")
    L.append(md(pd.DataFrame([{
        "closed-loop new bricks (agent × schedule)": int(df[ex].sum()),
        "also a new brick in open loop": int(df.exposure_suffices.sum()),
        "only in closed loop (feedback-required)": int(df.feedback_required.sum()),
        "open-loop-only new bricks": int((~df[ex] & df["open_brick[all 256 tapes (N=8)]"]).sum()),
        "instances with a feedback-required brick": int(df.groupby("inst_id").feedback_required.any().sum()),
    }]).T.reset_index().rename(columns={"index": "", 0: "count"})))
    smallest = df[df.feedback_required].sort_values(["k", "steps"]).head(5)
    L.append("\nSmallest feedback-required witnesses (rule size k, run length):\n")
    L.append(md(smallest[["inst_id", "k", "sched", "C", "steps"]]))
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_closed/WITNESS.md"))
