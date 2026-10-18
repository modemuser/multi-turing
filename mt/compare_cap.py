"""Matched comparison of two sweeps on the SAME instances that differ only in the endogenous turn
rule (e.g. no hold cap vs hold cap 3). Exogenous conditions must come out identical (checked).

    uv run python -m mt.compare_cap results/nohalt_N8_cap3/CAP_COMPARE.md results/nohalt_N8 results/nohalt_N8_cap3
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .compare import rate
from .report import ENDO, md, pct

ALL = ["local_ti", "local", "joint", "tables"]


def label(d: Path) -> str:
    m = json.loads((d / "meta.json").read_text())
    return f"cap {m['hold_cap']}" if m.get("hold_cap") else "no cap"


def build(a: Path, b: Path) -> str:
    la, lb = label(a), label(b)
    ra, rb = pd.read_parquet(a / "results.parquet"), pd.read_parquet(b / "results.parquet")
    PROJ = [p for p in ALL if f"confluent_{p}" in ra and f"confluent_{p}" in rb]
    H = PROJ[0]
    ua, ub = pd.read_parquet(a / "runs.parquet"), pd.read_parquet(b / "runs.parquet")
    assert set(ra.inst_id) == set(rb.inst_id), "not the same instances"
    L = []
    w = L.append
    w(f"# Endogenous turn rule: {la} vs {lb} (same {ra.inst_id.nunique()} instances)\n")
    w("Exploratory simulation output: counts and rates over one sample. No result here is a proof.\n")

    # exogenous conditions do not depend on the turn rule: must be identical
    ex = ["C2_mutual_exo", "C3_fixed_exo", "C4_self"]
    ka = ua[ua.condition.isin(ex)].set_index(["inst_id", "condition", "sched"]).sort_index()
    kb = ub[ub.condition.isin(ex)].set_index(["inst_id", "condition", "sched"]).sort_index()
    cols = ["kind", "transient", "period", f"d_{H}"]
    same = ((ka[cols] == kb[cols]) | (ka[cols].isna() & kb[cols].isna())).all().all()   # unresolved: no digest
    w(f"- Sanity check: exogenous and C4 runs identical in both sweeps: **{same}**.\n")

    def ends(r, c):
        return r[r.condition == c].set_index("inst_id").sort_index()

    w("## 1. Starvation and forced passes\n")
    rows = []
    for c in ENDO:
        r = {"condition": c}
        for lbl, u in ((la, ua), (lb, ub)):
            cy = u[(u.condition == c) & (u.kind == "cycle")]
            r[f"starved cycles, {lbl}"] = pct(cy.starved.mean())
        x = ub[ub.condition == c]
        if "forced_passes" in x:
            r[f"runs with forced pass, {lb}"] = pct((x.forced_passes > 0).mean())
            r[f"forced/steps median, {lb}"] = f"{(x.forced_passes / x.steps.clip(lower=1)).median():.3f}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))

    w("\n## 2. Endogenous measures, matched instances\n")
    w("Start-turn independence = start A and start B give the same outcome. \"matches no exo\" = neither "
      "endogenous run's outcome is among the 14 exogenous outcomes. C1≠C1m = masking R's yield edits "
      "changes at least one start turn's outcome. That is the \"rewrites change who moves next\" measure.\n")
    rows = []
    for p in PROJ:
        for c in ENDO:
            A, B = ends(ra, c), ends(rb, c)
            ok = A[f"confluent_{p}"].notna() & B[f"confluent_{p}"].notna()
            rows.append({"proj": p, "measure": "start-turn independent", "condition": c,
                         la: rate(A[f"confluent_{p}"][ok]), lb: rate(B[f"confluent_{p}"][ok])})
            col = f"n_endo_matching_exo_{p}"
            ok = A[col].notna() & B[col].notna()
            rows.append({"proj": p, "measure": "matches no exo", "condition": c,
                         la: rate(A[col][ok] == 0), lb: rate(B[col][ok] == 0)})
        A, B = ends(ra, "C1_mutual_endo"), ends(rb, "C1_mutual_endo")
        col = f"n_endo_differs_from_mask_{p}"
        ok = A[col].notna() & B[col].notna()
        rows.append({"proj": p, "measure": "C1≠C1m (all)", "condition": "C1",
                     la: rate(A[col][ok] > 0), lb: rate(B[col][ok] > 0)})
        ya, yb = A.eff_yield_edits > 0, B.eff_yield_edits > 0
        rows.append({"proj": p, "measure": "C1≠C1m (yield edit fired)", "condition": "C1",
                     la: rate(A[col][ok & ya] > 0), lb: rate(B[col][ok & yb] > 0)})
    w(md(pd.DataFrame(rows)))
    A, B = ends(ra, "C1_mutual_endo"), ends(rb, "C1_mutual_endo")
    w(f"\nInstances where a yield edit fired in C1: {la} {pct((A.eff_yield_edits > 0).mean())}, "
      f"{lb} {pct((B.eff_yield_edits > 0).mean())}.\n")

    w(f"## 3. Per instance: does the C1≠C1m verdict ({H}) change with the turn rule?\n")
    col = f"n_endo_differs_from_mask_{H}"
    ok = A[col].notna() & B[col].notna()
    x = pd.crosstab((A[col][ok] > 0).map({True: f"yield edits matter ({la})", False: f"don't matter ({la})"}),
                    (B[col][ok] > 0).map({True: f"yield edits matter ({lb})", False: f"don't matter ({lb})"}))
    w(md(x.reset_index().rename(columns={x.index.name: ""})))
    sa = ua[(ua.condition == "C1_mutual_endo")].groupby("inst_id").starved.any()
    sub = A[ok & (B[col] > 0)].index
    w(f"\nOf the instances where yield edits matter under {lb}, {pct(sa.loc[sub].mean())} had a starved "
      f"machine under {la}.\n")

    w("## 4. Periods and transients of endogenous runs (cycling)\n")
    rows = []
    for c in ENDO:
        r = {"condition": c}
        for lbl, u in ((la, ua), (lb, ub)):
            cy = u[(u.condition == c) & (u.kind == "cycle")]
            r[f"{lbl} period p50/p90/p99"] = "/".join(str(int(cy.period.quantile(q))) for q in (.5, .9, .99))
            r[f"{lbl} transient p50/p99"] = f"{int(cy.transient.median())}/{int(cy.transient.quantile(.99))}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    notes = Path(sys.argv[1]).parent / "cap_notes.md"
    if notes.exists():
        w("\n" + notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.write_text(build(Path(sys.argv[2]), Path(sys.argv[3])))
    print(f"wrote {out}")
