"""Matched comparison of swarm probes that differ only in the learning rule's edit kind
(set / toggle / mixed), joined on base_id (same tables, triggers and targets).

    uv run python -m mt.compare_edits results/swarm_edits/COMPARE.md results/swarm_N8_probe \
        results/swarm_N8_toggle results/swarm_N8_mixed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .report import md, wilson

GRAPHS = ("decoupled", "ring", "alternating", "complete")


def rate_dep(s: pd.Series) -> str:
    """Share order-dependent (= not confluent), with Wilson CI."""
    s = s.dropna().astype(bool)
    k, n = int((~s).sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}]" if n else "–"


def load(d: Path):
    meta = json.loads((d / "meta.json").read_text())
    res = pd.read_parquet(d / "results.parquet")
    if "base_id" not in res:
        res["base_id"] = res["inst_id"]
    runs = pd.read_parquet(d / "runs.parquet")
    return meta.get("edit_kind", "set"), res, runs


def build(dirs) -> str:
    data = {}
    for d in dirs:
        kind, res, runs = load(Path(d))
        data[kind] = (res, runs)
    kinds = list(data)
    common = set.intersection(*(set(r.base_id) for r, _ in data.values()))
    L = []
    w = L.append
    w(f"# Learning-rule edit kind: {' vs '.join(kinds)} ({len(common)} matched instances)\n")
    w("Exploratory probe. Same tables, triggers and targets in every column. Only the edit operation "
      "differs. **set** overwrites a field: idempotent, non-commuting on conflicts. **toggle** advances it: "
      "commutative, not idempotent. **mixed**: each edit is randomly set or toggle, so the rule is "
      "non-commuting and non-idempotent. Rates are the share of instances that are *order-dependent* "
      "across the 24 exogenous schedules (95% Wilson CI), on instances resolved in that cell.\n")

    def cell(kind, cond, proj):
        res = data[kind][0]
        x = res[(res.condition == cond) & res.base_id.isin(common)]
        return rate_dep(x[f"confluent_{proj}"])

    w("## 1. Open loop vs closed loop (`tables_local`: per-agent set of learned tables in the cycle)\n")
    rows = []
    for g in GRAPHS:
        r = {"graph": g}
        for kd in kinds:
            r[f"{kd}: open"] = cell(kd, f"Lo_exo_{g}", "tables_local")
            r[f"{kd}: closed"] = cell(kd, f"L_exo_{g}", "tables_local")
        rows.append(r)
    w(md(pd.DataFrame(rows)))

    w("\n## 2. Closed loop, headline projection (`local_ti`: behaviour + table, up to translation)\n")
    rows = []
    for g in GRAPHS:
        rows.append({"graph": g, **{kd: cell(kd, f"L_exo_{g}", "local_ti") for kd in kinds},
                     **{f"no learning ({kd})": cell(kd, "F_exo", "local_ti") for kd in kinds[:1]}})
    w(md(pd.DataFrame(rows)))

    w("\n## 3. Endogenous order: does learning that rewrites who-moves-next change the outcome? (`local_ti`)\n")
    rows = []
    for g in GRAPHS:
        r = {"graph": g}
        for kd in kinds:
            res = data[kd][0]
            x = res[(res.condition == f"L_endo_{g}") & res.base_id.isin(common)]
            s = x["n_endo_differs_from_mask_local_ti"].dropna()
            k, n = int((s > 0).sum()), len(s)
            lo, hi = wilson(k, n)
            r[kd] = f"{k / n:.3f} [{lo:.3f}, {hi:.3f}]" if n else "–"
        rows.append(r)
    w(md(pd.DataFrame(rows)))

    w("\n## 4. Dynamics: unresolved runs, periods, tables still changing in the cycle\n")
    rows = []
    for kd in kinds:
        runs = data[kd][1]
        lx = runs[runs.condition.str.match(r"Lo?_exo_")]
        cy = lx[lx.kind == "cycle"]
        rows.append({"edit kind": kd, "unresolved runs": int((lx.kind == "unresolved").sum()),
                     "period p50/p90/p99": "/".join(str(int(cy.period.quantile(q))) for q in (.5, .9, .99)),
                     "tables still changing in cycle": f"{100 * (cy.tables_settled == False).mean():.1f}%",  # noqa: E712
                     "effective edits per run (median)": int(lx.eff_edits.median())})
    w(md(pd.DataFrame(rows)))
    w("\n## 5. Split by whether learning keeps going (`tables_local`, order-dependent share)\n")
    w("\"Live\" = in at least one closed-loop exogenous run of the instance, tables keep changing inside "
      "the cycle. This is an outcome-based split (a selection caveat applies), except for `threshold`, where "
      "settling is guaranteed by design.\n")
    rows = []
    for g in ("ring", "complete"):
        for loop, pre in (("closed", "L_exo_"), ("open", "Lo_exo_")):
            for live_flag in (False, True):
                r = {"graph": g, "loop": loop, "tables keep changing": live_flag}
                for kd in kinds:
                    res, runs = data[kd]
                    lv = runs[runs.condition == f"L_exo_{g}"].groupby("inst_id").tables_settled.apply(
                        lambda z: bool((z == False).any()))  # noqa: E712
                    closed = res[res.condition == f"L_exo_{g}"]
                    live_by_base = {b: bool(lv.get(i, False)) for b, i in zip(closed.base_id, closed.inst_id)}
                    x = res[(res.condition == f"{pre}{g}") & res.base_id.isin(common)]
                    x = x[x.base_id.map(live_by_base) == live_flag]
                    z = x["confluent_tables_local"].dropna().astype(bool)
                    r[kd] = f"{1 - z.mean():.3f} (n={len(z)})" if len(z) else "–"
                rows.append(r)
    w(md(pd.DataFrame(rows)))
    notes = Path(sys.argv[1]).parent / "notes.md"
    if notes.exists():
        w("\n" + notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(sys.argv[2:]))
    print(f"wrote {out}")
