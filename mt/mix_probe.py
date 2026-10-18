"""Designed-mix probe: vary the construction/revision mix of R (p_append) on the same base
instances and measure rule synthesis, new bricks (all 256 fresh tapes, N=8) and the
feedback-required share. Closed vs open loop, complete graph, 24 schedules. Capped
(20k steps per transplanted run), progress output, results written per instance.

    uv run python -m mt.mix_probe results/swarm_mix 0.25 0.5 0.75
"""
from __future__ import annotations

from .paths import PROBE400

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import pandas as pd

from . import transplant
from .closed_serial import canon_rules
from .report import md, wilson
from .swarm import APPEND, M, SwarmInstance, edit_op, exo_schedules, growth_variant, run
from .witness import TAPESETS, new_brick, programs

PROBE = PROBE400
TS = TAPESETS["all 256 tapes (N=8)"]


def rule_seed(iid: str, rep: int) -> str:
    """Seed for the constructive rule of replicate `rep` of a base instance. Replicate 0 uses the
    instance id itself, as in every run before replicates were added."""
    return iid if rep == 0 else f"{iid}#{rep}"


def analyse(args):
    iid, inst, p = args
    transplant.MAX_BEHAVIOUR_STEPS = 20_000
    n_app = sum(1 for x in inst.R if x is not None and edit_op(x) == APPEND)
    n_rev = sum(1 for x in inst.R if x is not None and edit_op(x) != APPEND)
    rows = []
    for nm, w in exo_schedules():
        runs = {lp: run(inst, "on" if lp == "closed" else "open", ("exo", w), "complete", 8, budget=200_000,
                        keep_trace=True) for lp in ("closed", "open")}
        if any(r.kind != "cycle" for r in runs.values()):
            continue
        for C in range(M):
            row = dict(p_append=p, inst_id=iid, sched=nm, C=C, n_append=n_app, n_revise=n_rev)
            for lp, r in runs.items():
                full, ab, ba, _ = programs(inst, r.trace, w, C, lp)
                syn = canon_rules(full, inst) not in (canon_rules(ab, inst), canon_rules(ba, inst))
                row[f"{lp}_synth"] = syn
                row[f"{lp}_brick"] = syn and new_brick(full[3], ab[3], ba[3], TS)
            rows.append(row)
    return rows


def rate(s):
    s = s.dropna().astype(bool)
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}] (n={n})" if n else "–"


def main(out: Path, ps):
    out.mkdir(parents=True, exist_ok=True)
    base = [json.loads(l) for l in open(PROBE)]
    reps = int(os.environ.get("MT_REPS", "1"))
    jobs = [(j["inst_id"] if r == 0 else f"{j['inst_id']}#{r}",
             growth_variant(SwarmInstance.from_json(j), rule_seed(j["inst_id"], r), cap=4, p_append=p), p)
            for p in ps for j in base for r in range(reps)]
    rows, t0 = [], time.time()
    with mp.Pool() as pool:
        for i, rr in enumerate(pool.imap_unordered(analyse, jobs, chunksize=1), 1):
            rows += rr
            if i % 100 == 0 or i == len(jobs):
                pd.DataFrame(rows).to_csv(out / "mix_runs.csv", index=False)
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "mix_runs.csv", index=False)
    tab = []
    for p, sub in df.groupby("p_append"):
        syn = sub[sub.closed_synth]
        fr = sub.closed_brick & ~sub.open_brick
        tab.append({"p_append": p,
                    "mean append / revision rules": f"{sub.drop_duplicates('inst_id').n_append.mean():.2f} / "
                                                    f"{sub.drop_duplicates('inst_id').n_revise.mean():.2f}",
                    "rule synthesis (agent × schedule)": rate(sub.closed_synth),
                    "P(new brick | synthesis)": rate(syn.closed_brick),
                    "instances with a new brick": rate(sub.groupby("inst_id").closed_brick.any()),
                    "feedback-required share of new bricks": rate(fr[sub.closed_brick]),
                    "instances with a feedback-required brick": rate(fr.groupby(sub.inst_id).any())})
    text = ("# Designed construction/revision mix\n\nExploratory probe, 400 base instances per setting, closed loop, "
            "complete graph, 24 schedules, new bricks on all 256 fresh tapes (20k-step cap).\n\n" + md(pd.DataFrame(tab)) + "\n")
    (out / "MIX.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(Path(sys.argv[1]), [float(x) for x in sys.argv[2:]])
