"""Behaviour-level check of "feedback-required" for the new bricks of the mix probe (p_append 0.5).

The pipeline's definition (mt.mix_probe, mt.post_numbers): a closed-loop new brick is
*feedback-required* if the open-loop run at the same schedule does not yield a new brick. That
compares each program with the serial versions of its OWN loop's streams, so a brick can be
feedback-required while the learned program behaves exactly like the open-loop program.

This module compares, for every closed-loop brick, the learned program with the open-loop program
of the same run directly: by table, by canonical rules, and by eventual behaviour on all 256 fresh
tapes (mt.transplant.behaviour, the measure every brick number uses). It writes one row per brick and
a summary with instance-clustered intervals for the alternative definitions.

    uv run python -m mt.feedback_behaviour results/publish/bricks
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import pandas as pd

from .closed_serial import canon_rules
from .mix_probe import rule_seed
from .paths import PROBE400
from .swarm import SwarmInstance, exo_schedules, growth_variant, run
from .transplant import behaviour
from .witness import programs

SCHED = dict(exo_schedules())
BASE = {j["inst_id"]: j for j in map(json.loads, open(PROBE400))}


def job(args):
    iid, sched, C = args
    base_id, _, rep = iid.partition("#")
    inst = growth_variant(SwarmInstance.from_json(BASE[base_id]), rule_seed(base_id, int(rep or 0)), cap=4, p_append=0.5)
    w = SCHED[sched]
    rc = run(inst, "on", ("exo", w), "complete", 8, budget=200_000, keep_trace=True)
    ro = run(inst, "open", ("exo", w), "complete", 8, budget=200_000, keep_trace=True)
    fc, abc, bac, nuc = programs(inst, rc.trace, w, C, "closed")
    fo, abo, bao, nuo = programs(inst, ro.trace, w, C, "open")
    Tc, To = fc[3], fo[3]
    brick_tapes = sum(1 for tp in range(256)
                      if behaviour(Tc, tp) != behaviour(abc[3], tp) and behaviour(Tc, tp) != behaviour(bac[3], tp))
    diff_tapes = sum(1 for tp in range(256) if behaviour(Tc, tp) != behaviour(To, tp))
    return dict(inst_id=iid, sched=sched, C=C, table_differs=Tc != To,
                rules_differ=canon_rules(fc, inst) != canon_rules(fo, inst),
                behaviour_differs_tapes=diff_tapes, brick_tapes=brick_tapes, n_states=fc[4], history_len=nuc)


def main(out: Path):
    from .post_numbers import cboot
    out.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(Path("results/publish/mix/mix_runs.csv"), low_memory=False)
    for col in ("closed_brick", "open_brick"):
        m[col] = m[col].astype(str).eq("True")
    m = m[(m.p_append == 0.5) & m.closed_brick]
    jobs = [(r.inst_id, r.sched, int(r.C)) for r in m.itertuples()]
    print(len(jobs), "closed-loop new bricks", flush=True)
    rows, t0 = [], time.time()
    with mp.Pool() as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=4), 1):
            rows.append(r)
            if i % 200 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows).merge(m[["inst_id", "sched", "C", "open_brick"]], on=["inst_id", "sched", "C"])
    df["fb_pipeline"] = ~df.open_brick
    df["fb_behaviour"] = df.behaviour_differs_tapes > 0
    df["fb_both"] = df.fb_pipeline & df.fb_behaviour
    df.sort_values(["inst_id", "sched", "C"]).to_csv(out / "feedback_behaviour.csv", index=False)
    lines = ["# Feedback-required new bricks: pipeline definition vs behaviour-level comparison\n",
             f"All {len(df)} closed-loop new bricks of the mix probe at p_append 0.5 (400 instances x 4 rule draws, "
             "24 schedules). Intervals 95%, bootstrap clustered by instance.\n",
             "| definition | bricks | share |", "|---|---|---|",
             f"| pipeline: no new brick in the open-loop run at the same schedule | {int(df.fb_pipeline.sum())} | {cboot(df, 'fb_pipeline')} |",
             f"| behaviour: learned program behaves unlike the open-loop program on >= 1 of 256 fresh tapes | {int(df.fb_behaviour.sum())} | {cboot(df, 'fb_behaviour')} |",
             f"| both | {int(df.fb_both.sum())} | {cboot(df, 'fb_both')} |",
             "",
             f"- bricks that are feedback-required by the pipeline definition but behave exactly like their open-loop program on all 256 tapes: {int((df.fb_pipeline & ~df.fb_behaviour).sum())}",
             f"- bricks that are NOT feedback-required by the pipeline definition but behave unlike their open-loop program: {int((~df.fb_pipeline & df.fb_behaviour).sum())}",
             f"- closed-loop table differs from the open-loop table: {int(df.table_differs.sum())}; canonical rules differ: {int(df.rules_differ.sum())}",
             f"- among behaviour-level feedback-required bricks, tapes on which the two programs differ: median {int(df[df.fb_behaviour].behaviour_differs_tapes.median())} of 256, "
             f"IQR {int(df[df.fb_behaviour].behaviour_differs_tapes.quantile(.25))}-{int(df[df.fb_behaviour].behaviour_differs_tapes.quantile(.75))}",
             ""]
    (out / "FEEDBACK_BEHAVIOUR.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/publish/bricks"))
