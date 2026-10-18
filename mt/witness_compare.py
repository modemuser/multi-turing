"""Cross-check the witness runs: quick (subset, 20k cap), capped (all, 200k cap), original (all,
uncapped). Matched on (instance, schedule, agent). Differences can only come from the step caps
(capped runs skip tapes where a transplanted program exceeds the cap).

    uv run python -m mt.witness_compare
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

D = Path("results/swarm_closed")
RUNS = {"quick (20k cap)": D / "witness_quick.csv",
        "capped (200k cap)": D / "WITNESS_capped_runs.parquet",
        "original (uncapped)": D / "witness_runs.parquet"}
COLS = ["closed_rules_synth", "closed_brick[4 tapes (N=8)]", "closed_brick[all 256 tapes (N=8)]",
        "closed_brick[64 tapes (N=16)]", "open_brick[all 256 tapes (N=8)]"]
KEY = ["inst_id", "sched", "C"]


def load(p):
    if not p.exists():
        return None
    return pd.read_csv(p) if p.suffix == ".csv" else pd.read_parquet(p)


def main():
    data = {k: load(p) for k, p in RUNS.items()}
    avail = {k: v for k, v in data.items() if v is not None}
    print("available:", ", ".join(f"{k} ({v.inst_id.nunique()} instances)" for k, v in avail.items()))
    names = list(avail)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            m = avail[a][KEY + COLS].merge(avail[b][KEY + COLS], on=KEY, suffixes=("_a", "_b"))
            print(f"\n{a} vs {b}: {len(m)} matched agent × schedule pairs "
                  f"({m.inst_id.nunique()} instances)")
            for c in COLS:
                diff = int((m[f"{c}_a"].astype(bool) != m[f"{c}_b"].astype(bool)).sum())
                print(f"  {c:40s} disagreements: {diff}")
    for k, v in avail.items():
        ex, op = "closed_brick[all 256 tapes (N=8)]", "open_brick[all 256 tapes (N=8)]"
        fr = v[ex].astype(bool) & ~v[op].astype(bool)
        print(f"\n{k}: new bricks {int(v[ex].sum())}, feedback-required {int(fr.sum())} "
              f"in {int(fr.groupby(v.inst_id).any().sum())} instances")


if __name__ == "__main__":
    main()
