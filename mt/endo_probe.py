"""Endogenous-order probe: new bricks when the AGENTS decide who moves next.

Order comes from the route field of each fired entry (keep / pass to next / pass to previous),
with hold cap 3 and wait cap 6 (mt.swarm). Learning can rewrite route fields, so in the closed
loop what agents learn also reshapes who gets to act. In the open loop agents act on their
original tables, so the order is fixed by their original routes.

Same analysis as mt.mix_probe (rule synthesis vs the two serialisations, new brick = behaves
unlike both on some of the 256 fresh tapes, feedback-required = new brick in closed but not open
loop), for the 3 start turns instead of 24 exogenous schedules. Also records whether the run's
order was actually changed by learning (closed-loop mover sequence differs from the run with route
edits masked).

    uv run python -m mt.endo_probe results/swarm_endo 0.5
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import pandas as pd

from . import transplant
from .closed_serial import canon_rules, influence, own_step, replay, serialise
from .mix_probe import PROBE, TS, rate
from .report import md
from .swarm import APPEND, M, SwarmInstance, edit_op, growth_variant, run
from .witness import new_brick, replay_open


def history_endo(inst, trace, C):
    """C's input history along an endogenous-order trace (mover = turn bit of ctrl)."""
    u = []
    for c in trace:
        X = c[-1][0]
        s, h, t, T = c[4 * X:4 * X + 4]
        u.append(("o",) if X == C else ("x", X, (s, T[4 * (2 * s + ((t >> h) & 1))])))
    return u


def movers(trace):
    return tuple(c[-1][0] for c in trace)


def analyse(args):
    iid, inst, p = args
    transplant.MAX_BEHAVIOUR_STEPS = 20_000
    rows = []
    for start in range(M):
        sched = ("endo", start)
        runs = {"closed": run(inst, "on", sched, "complete", 8, budget=200_000, keep_trace=True),
                "open": run(inst, "open", sched, "complete", 8, budget=200_000, keep_trace=True),
                "masked": run(inst, "mask_route", sched, "complete", 8, budget=200_000, keep_trace=True)}
        if any(r.kind != "cycle" for r in runs.values()):
            continue
        order_changed = movers(runs["closed"].trace) != movers(runs["masked"].trace)
        for C in range(M):
            A, B = [j for j in range(M) if j != C]
            row = dict(p_append=p, inst_id=iid, start=start, C=C, order_changed_by_learning=order_changed)
            st0 = (0, 0, 0, inst.tables[C], (inst.ns0 or (inst.n,) * M)[C], frozenset())
            for lp in ("closed", "open"):
                u = history_endo(inst, runs[lp].trace, C)
                rep = (lambda uu: replay(st0, uu, inst, "learn")) if lp == "closed" else \
                      (lambda uu: replay_open(st0, uu, inst, inst.tables[C]))
                full, ab, ba = rep(u), rep(serialise(u, A, B)), rep(serialise(u, B, A))
                syn = canon_rules(full, inst) not in (canon_rules(ab, inst), canon_rules(ba, inst))
                row[f"{lp}_synth"] = syn
                row[f"{lp}_brick"] = syn and new_brick(full[3], ab[3], ba[3], TS)
            rows.append(row)
    return rows


def main(out: Path, ps):
    out.mkdir(parents=True, exist_ok=True)
    base = [json.loads(l) for l in open(PROBE)]
    jobs = [(j["inst_id"], growth_variant(SwarmInstance.from_json(j), j["inst_id"], cap=4, p_append=p), p)
            for p in ps for j in base]
    rows, t0 = [], time.time()
    with mp.Pool() as pool:
        for i, rr in enumerate(pool.imap_unordered(analyse, jobs, chunksize=1), 1):
            rows += rr
            if i % 100 == 0 or i == len(jobs):
                pd.DataFrame(rows).to_csv(out / "endo_runs.csv", index=False)
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    tab = []
    for p, sub in df.groupby("p_append"):
        fr = sub.closed_brick & ~sub.open_brick
        tab.append({"p_append": p,
                    "runs where learning changed who moves": rate(sub.drop_duplicates(["inst_id", "start"]).order_changed_by_learning),
                    "rule synthesis (agent × start)": rate(sub.closed_synth),
                    "P(new brick | synthesis)": rate(sub[sub.closed_synth].closed_brick),
                    "instances with a new brick": rate(sub.groupby("inst_id").closed_brick.any()),
                    "feedback-required share": rate(fr[sub.closed_brick]),
                    "new bricks in runs whose order learning changed": rate(sub[sub.closed_brick].order_changed_by_learning)})
    text = ("# New bricks under endogenous order\n\nExploratory probe: 400 base instances, complete graph, order set by "
            "the agents' route fields (hold cap 3, wait cap 6), 3 start turns, new bricks on all 256 fresh tapes "
            "(20k-step cap).\n\n" + md(pd.DataFrame(tab)) + "\n")
    (out / "ENDO.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(Path(sys.argv[1]), [float(x) for x in sys.argv[2:]])
