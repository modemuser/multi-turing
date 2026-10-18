"""Is the append effect a relabelling artifact? Recompute order-dependence of per-agent learned
tables up to relabelling of APPENDED states (route bits zeroed: inert under exogenous schedules).

    uv run python -m mt.relabel_check results/swarm_N8_append
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd

from .relabel import canon_table
from .swarm import M, SwarmInstance, exo_schedules, run

GRAPHS = ("complete", "alternating", "ring")


def _zero_route(T):
    return tuple(0 if i % 4 == 3 else v for i, v in enumerate(T))


def _outcome(r, inst):
    if r.kind != "cycle":
        return None
    return tuple(frozenset(canon_table(_zero_route(c[4 * j + 3]), inst.n, c[4 * M + 2][j], inst.capacity)
                           for c in r.cycle) for j in range(M))


def _job(args):
    iid, inst = args
    out = {}
    for g in GRAPHS:
        for tag, learn in (("open", "open"), ("closed", "on")):
            o = {_outcome(run(inst, learn, ("exo", w), g, 8, budget=200_000), inst) for _, w in exo_schedules()}
            o.discard(None)
            out[(g, tag)] = len(o) > 1
    return iid, out


def main(d: Path):
    res = pd.read_parquet(d / "results.parquet")
    insts = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        insts[j["inst_id"]] = SwarmInstance.from_json(j)
    with mp.Pool() as pool:
        R = dict(pool.map(_job, list(insts.items()), chunksize=4))
    rows = []
    for g in GRAPHS:
        for tag, pre in (("open", "Lo_exo_"), ("closed", "L_exo_")):
            raw = res[res.condition == f"{pre}{g}"].set_index("inst_id")["confluent_tables_local"]
            ok = raw.dropna().index
            rows.append({"graph": g, "loop": tag,
                         "order-dependent (raw)": f"{(~raw.loc[ok].astype(bool)).mean():.3f}",
                         "order-dependent (up to relabelling)": f"{sum(R[i][(g, tag)] for i in ok) / len(ok):.3f}",
                         "n": len(ok)})
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    df.to_csv(d / "relabel_check.csv", index=False)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_N8_append"))
