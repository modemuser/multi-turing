"""New bricks and on which fresh tapes they differ (append rule set, p_append = 0.5, complete graph,
closed loop, 24 schedules). For every synthesised program, the set of the 256 fresh tapes on which it
behaves unlike both serial versions is stored as a bitmask, so the 4-tape share (mt.transplant.FRESH)
and the distribution over all 256 tapes come from one run.

    uv run python -m mt.brick_tapes results/publish/bricks
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import pandas as pd

from . import transplant
from .closed_serial import canon_rules
from .paths import PROBE400
from .swarm import M, SwarmInstance, exo_schedules, growth_variant, run
from .transplant import FRESH, behaviour
from .mix_probe import rule_seed
from .witness import programs


def job(args):
    iid, inst = args
    transplant.MAX_BEHAVIOUR_STEPS = 20_000
    out = []
    for nm, w in exo_schedules():
        r = run(inst, "on", ("exo", w), "complete", 8, budget=200_000, keep_trace=True)
        if r.kind != "cycle":
            continue
        for C in range(M):
            full, ab, ba, _ = programs(inst, r.trace, w, C, "closed")
            if canon_rules(full, inst) in (canon_rules(ab, inst), canon_rules(ba, inst)):
                continue
            mask = skipped = 0
            for tp in range(256):
                b, x, y = behaviour(full[3], tp, 8), behaviour(ab[3], tp, 8), behaviour(ba[3], tp, 8)
                if "unresolved" in (b, x, y):
                    skipped += 1
                elif b != x and b != y:
                    mask |= 1 << tp
            out.append(dict(inst_id=iid, sched=nm, C=C, mask=str(mask), tapes_differ=bin(mask).count("1"),
                            fresh4=any((mask >> tp) & 1 for tp in FRESH), skipped=skipped))
    return out


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    reps = int(os.environ.get("MT_REPS", "1"))
    jobs = [(j["inst_id"] if r == 0 else f"{j['inst_id']}#{r}",
             growth_variant(SwarmInstance.from_json(j), rule_seed(j["inst_id"], r), cap=4, p_append=0.5))
            for j in map(json.loads, open(PROBE400)) for r in range(reps)]
    rows, t0 = [], time.time()
    with mp.Pool() as pool:
        for i, rr in enumerate(pool.imap_unordered(job, jobs, chunksize=2), 1):
            rows += rr
            if i % 50 == 0 or i == len(jobs):
                pd.DataFrame(rows).to_csv(out / "brick_tapes.csv", index=False)
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(out / "brick_tapes.csv", index=False)
    br = d[d.tapes_differ > 0]
    print(f"synthesised programs {len(d)}; new bricks (256 tapes) {len(br)} = {len(br) / len(d):.1%}; "
          f"on the 4 FRESH tapes {d.fresh4.mean():.1%}; median tapes {br.tapes_differ.median():.0f}/256")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/publish/bricks"))
