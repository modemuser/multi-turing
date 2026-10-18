"""Check every exception from the exception hunt against L9 (PROOFS.md).

For each (instance, learner) that is open-loop order-dependent or synthesises:
  - count its contested fields (targets of conflicting overwrites)
  - for one contested field: L9 says order can matter only if EVERY conflicting lesson about it is
    delivered finitely often (its trigger never occurs in the source's periodic phase). Verify.

    uv run python -m mt.l9_check results/zeros
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .robust_probe import sample
from .swarm import APPEND, APPEND_ONCE, GRAPHS, edit_op, growth_variant, pregrown_variant
from .swarm_sweep import inst_id
from .synthesis import event_stream


def build(n, total, iid, learner):
    base = {inst_id(b): b for b in sample(n, total, seed=7)}[iid]
    return base if learner == "set" else pregrown_variant(growth_variant(base, iid, cap=n + 2))


def contested(inst):
    by = {}
    for t, x in enumerate(inst.R):
        if x is None or edit_op(x) in (APPEND, APPEND_ONCE):
            continue
        by.setdefault((x[0], x[1]), []).append((t, x[2]))
    return {k: v for k, v in by.items() if len({val for _, val in v}) > 1}


def main(d: Path, n2=4000, n3=2000):
    f = d / "zeros_runs.csv.gz"
    df = pd.read_csv(f if f.exists() else d / "zeros_runs.csv", low_memory=False)
    ok = df[df.unresolved == False]  # noqa: E712
    rows = []
    for (n, lt), sub in ok.groupby(["n", "learner"]):
        dep = sub.groupby(["inst_id", "C"]).open_tabset.nunique().gt(1)
        syn = sub.groupby(["inst_id", "C"]).apply(lambda g: bool(g.closed_synth.astype(str).eq("True").any()
                                                               or g.open_synth.astype(str).eq("True").any()))
        cases = sorted(set(dep[dep].index) | set(syn[syn].index))
        for iid, C in cases:
            inst = build(n, n2 if n == 2 else n3, iid, lt)
            cf = contested(inst)
            srcs = [X for X in range(3) if C in GRAPHS["complete"][X]]
            periodic = set()
            for X in srcs:
                _, per = event_stream(inst.tables[X])
                periodic |= {2 * q + w for q, w in per}
            all_oneoff = None
            if len(cf) == 1:
                (_, lessons), = cf.items()
                all_oneoff = all(t not in periodic for t, _ in lessons)
            rows.append(dict(n=n, learner=lt, inst_id=iid, agent=C,
                             open_order_dependent=bool(dep.get((iid, C), False)),
                             synthesises=bool(syn.get((iid, C), False)),
                             contested_fields=len(cf), L9_case_iii=all_oneoff))
    out = pd.DataFrame(rows)
    out.to_csv(d / "l9_check.csv", index=False)
    print(out.to_string(index=False) if len(out) else "no exceptions")
    one = out[out.contested_fields == 1]
    if len(one):
        print(f"\none contested field: {int(one.L9_case_iii.sum())} of {len(one)} are L9 case (iii) "
              f"(all conflicting lessons one-offs); L9 violations: {int((~one.L9_case_iii.astype(bool)).sum())}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/zeros"))
