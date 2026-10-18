"""Append mechanism: order-dependence (per-agent learned tables, `tables_local`) by number of
append rules, for the append variants on the same rules.

    uv run python -m mt.append_mech results/swarm_growth/MECHANISM.md results/swarm_N8_append \
        results/swarm_N8_append_once results/swarm_N8_append_pregrown results/swarm_N8_append_off
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .report import md, wilson
from .swarm import APPEND, APPEND_ONCE, SwarmInstance, edit_op


def n_append_rules(path: Path) -> dict:
    out = {}
    for line in open(path):
        j = json.loads(line)
        R = SwarmInstance.from_json(j).R
        out[j.get("base_id", j["inst_id"])] = sum(1 for x in R if x is not None and edit_op(x) in (APPEND, APPEND_ONCE))
    return out


def cell(s: pd.Series) -> str:
    s = s.dropna().astype(bool)
    k, n = int((~s).sum()), len(s)
    if not n:
        return "–"
    lo, hi = wilson(k, n)
    return f"{k / n:.2f} [{lo:.2f}, {hi:.2f}]"


def build(dirs):
    napp = n_append_rules(Path(dirs[0]) / "instances.jsonl")      # rules of the dynamic-append variant
    data = {}
    for d in dirs:
        d = Path(d)
        kind = json.loads((d / "meta.json").read_text()).get("edit_kind")
        res = pd.read_parquet(d / "results.parquet")
        res["n_app"] = res.base_id.map(napp)
        data[kind] = res
    L = []
    w = L.append
    w("# Append mechanism probe\n")
    w("Exploratory, 400 matched instances (same tables and rules). Share of instances whose per-agent "
      "learned tables are **order-dependent** across the 24 exogenous schedules, by the number of append "
      "rules in R (95% Wilson CI).\n")
    w("- **append**: every observation of an append trigger copies a concept while there is room "
      "(2 free slots).")
    w("- **append_once**: each append rule copies at most once per agent. With ≤ 2 rules there is no "
      "capacity race.")
    w("- **append_pregrown**: all copies are made before the run (round-robin), and no appends happen "
      "during it. Same revisions.")
    w("- **append_off**: appends and revisions of absent states are no-ops. This is the weak control from "
      "the first probe.\n")
    counts = pd.Series(napp).value_counts().sort_index()
    w("Instances by number of append rules: " + ", ".join(f"{k}: {v}" for k, v in counts.items()) + "\n")
    for g in ("complete", "alternating", "ring"):
        for loop, pre in (("open", "Lo_exo_"), ("closed", "L_exo_")):
            rows = []
            for kind, res in data.items():
                x = res[res.condition == f"{pre}{g}"]
                r = {"variant": kind}
                for k in sorted(counts.index):
                    r[f"{k} rules"] = cell(x[x.n_app == k]["confluent_tables_local"])
                r["all"] = cell(x["confluent_tables_local"])
                rows.append(r)
            w(f"## {g}, {loop} loop\n")
            w(md(pd.DataFrame(rows)))
            w("")
    notes = Path(sys.argv[1]).parent / "mechanism_notes.md"
    if notes.exists():
        w(notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(sys.argv[2:]))
    print(f"wrote {out}")
