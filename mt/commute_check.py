"""Static test of the append lemma: does an instance contain a pair of learning operations that
do NOT commute on some agent's initial table? Compare with observed open-loop order-dependence.

Ops considered (per agent, on its initial table): APPEND(e) and SET revisions from R.
Two ops commute on T iff applying them in either order gives the same table up to relabelling
of appended states.

    uv run python -m mt.commute_check results/swarm_N8_append
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .relabel import canon_table
from .swarm import APPEND, M, SwarmInstance, _append, _apply, edit_op


def _op(T, ns, x, cap):
    if edit_op(x) == APPEND:
        T2, ns2, _ = _append(T, x[0], ns, cap)
        return T2, ns2
    # apply SET revision x as if its trigger fired (single-entry rule)
    T2, _, _ = _apply(T, (x,), 0, 0, False, ns)
    return T2, ns


def noncommuting_ops(inst: SwarmInstance):
    """Returns ('append-append' | 'append-revise' | None) for the strongest kind found."""
    ops = [x for x in inst.R if x is not None]
    apps = [x for x in ops if edit_op(x) == APPEND]
    found = None
    for T in inst.tables:
        for a in apps:
            for b in ops:
                if a is b:
                    continue
                r1 = _op(*_op(T, inst.n, a, inst.capacity), b, inst.capacity)
                r2 = _op(*_op(T, inst.n, b, inst.capacity), a, inst.capacity)
                c1 = canon_table(r1[0], inst.n, r1[1], inst.capacity)
                c2 = canon_table(r2[0], inst.n, r2[1], inst.capacity)
                if (c1, r1[1]) != (c2, r2[1]):
                    if edit_op(b) == APPEND:
                        return "append-append"
                    found = "append-revise"
    return found


def main(d: Path):
    res = pd.read_parquet(d / "results.parquet")
    kinds = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        kinds[j["inst_id"]] = noncommuting_ops(SwarmInstance.from_json(j)) or "all commute"
    rows = []
    for g in ("complete", "alternating"):
        for loop, pre in (("open", "Lo_exo_"), ("closed", "L_exo_")):
            x = res[res.condition == f"{pre}{g}"].assign(kind=lambda z: z.inst_id.map(kinds))
            for k, sub in x.groupby("kind"):
                s = sub.confluent_tables_local.dropna().astype(bool)
                rows.append({"graph": g, "loop": loop, "non-commuting pair on an initial table": k,
                             "instances": len(s), "order-dependent": f"{(~s).mean():.3f}"})
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    df.to_csv(d / "commute_check.csv", index=False)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_N8_append"))
