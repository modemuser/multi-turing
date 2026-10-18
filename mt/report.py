"""Build the markdown summary report from a sweep directory.

    uv run python -m mt.report results/m1
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

ALL_P = ["local_ti", "local", "joint", "tables", "class", "local_y"]
EXO = ["C2_mutual_exo", "C3_fixed_exo"]
ENDO = ["C1_mutual_endo", "C1m_mutual_endo_maskyield", "C3e_fixed_endo"]
ORDER = ["C1_mutual_endo", "C1m_mutual_endo_maskyield", "C2_mutual_exo", "C3_fixed_exo",
         "C3e_fixed_endo", "C4_self"]


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def rate(s: pd.Series) -> str:
    s = s.dropna().astype(bool)
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}] (n={n})" if n else "–"


def pct(x):
    return f"{100 * x:.1f}%"


def md(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(lines)


def hist(s: pd.Series, edges) -> str:
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        out.append(f"{((s >= lo) & (s < hi)).mean() * 100:.1f}")
    return " / ".join(out)


def build(d: Path) -> str:
    meta = json.loads((d / "meta.json").read_text())
    res = pd.read_parquet(d / "results.parquet")
    runs = pd.read_parquet(d / "runs.parquet")
    by = {c: res[res.condition == c] for c in ORDER}
    H = "local_ti" if "confluent_local_ti" in res else "local"          # headline projection
    P = [p for p in ALL_P if f"confluent_{p}" in res]
    PP = [p for p in P if p != "local_y"]
    L = []
    w = L.append
    w(f"# Report ({d.name}): n={meta['n']} states, bounded circular tape N={meta['N']}\n")
    w("Exploratory simulation output. Every number here is a count over a random sample at a finite "
      "budget. Nothing below is a proof or a claim of (un)decidability.\n")
    w(f"- {meta['n_instances']} canonical (A, B, R) instances: {meta['per_k']} per rule size k=1..4, "
      f"seed {meta['seed']}, canonicalized under A↔B swap × L↔R mirror and de-duplicated.")
    w(f"- HALT available as a `next` value: {'yes' if meta.get('halt', True) else 'no'}. "
      f"Endogenous hold cap: {meta.get('hold_cap') or 'none'}.")
    w(f"- Budget {meta['budget']} steps per run. Total {len(runs)} runs, {meta['seconds']} s wall time.")
    w("- 14 exogenous schedules per instance. Endogenous runs start once with A and once with B.")
    w("- Rates are shown as `p [95% Wilson CI] (n)`. n excludes instances with any unresolved run.")
    w(f"- **Headline projection: `{H}`.**" + (" `local_ti` = each machine's cycle (state, head, tape, "
      "table), compared up to a cyclic shift of that machine's tape and head. Machines never see "
      "absolute position, so a shifted cycle counts as the same outcome. `local` (shift-sensitive) "
      "is kept alongside." if H == "local_ti" else "") + "\n")

    w("## 1. Run outcomes per condition\n")
    t = runs.groupby("condition").kind.value_counts(normalize=True).unstack().fillna(0).reindex(ORDER)
    t = (t * 100).round(2).astype(str) + "%"
    t.insert(0, "runs", runs.groupby("condition").size().reindex(ORDER).values)
    w(md(t.reset_index()))
    un = runs[runs.kind == "unresolved"]
    w(f"\nUnresolved at budget: {len(un)} runs in {un.inst_id.nunique()} instances "
      f"({', '.join(f'{c}: {n}' for c, n in un.condition.value_counts().items())}).\n")

    w("## 2. Confluence\n")
    w("Exogenous conditions: an instance is **confluent** under a projection if all 14 schedules give "
      "the same outcome. Endogenous conditions have one deterministic run per start turn, so the analogous "
      "number is **start-turn independence** (start A vs start B). It is shown separately because it is "
      "a different quantity. Projections strip the inert yield bits, except `local_y`.\n")
    rows = []
    for c in EXO + ENDO:
        rows.append({"condition": c, **{p: rate(by[c][f"confluent_{p}"]) for p in P}})
    w(md(pd.DataFrame(rows)))
    w("\nAverage number of distinct outcomes across the 14 schedules:\n")
    rows = [{"condition": c, **{p: f"{by[c][f'n_distinct_{p}'].mean():.3f}" for p in P}} for c in EXO]
    w(md(pd.DataFrame(rows)))

    w("\n## 3. Delta: mutual rewrite (C2) vs fixed tables (C3), same schedules\n")
    w("Confluence rate difference C2 − C3 in percentage points, by rule size k.\n")
    c2, c3 = by["C2_mutual_exo"].set_index("inst_id"), by["C3_fixed_exo"].set_index("inst_id")
    rows = []
    for k in sorted(res.k.unique()):
        r = {"k": k}
        for p in PP:
            a = c2[c2.k == k][f"confluent_{p}"].dropna().astype(float).mean()
            b = c3[c3.k == k][f"confluent_{p}"].dropna().astype(float).mean()
            r[p] = f"{100 * a:.1f} − {100 * b:.1f} = {100 * (a - b):+.1f}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    w(f"\nC2 `{H}` confluence split by whether R contains a *critical pair* (two triggers setting the "
      "same field to different values):\n")
    g = c2.groupby(["k", "critical_pair"])[f"confluent_{H}"]
    rows = [{"k": k, "critical_pair": cp, f"confluent_{H}": rate(s)} for (k, cp), s in g]
    w(md(pd.DataFrame(rows)))
    w(f"\nC2 `{H}` confluence split by outcome class (all 14 C2 runs halt / all cycle / mixed):\n")
    cls = c2.apply(lambda r: "all halt" if r.n_halt == r.n_runs else ("all cycle" if r.n_cycle == r.n_runs
                                                                       else "mixed/unresolved"), axis=1)
    rows = [{"class": k, "instances": len(s), f"confluent_{H}": rate(s)}
            for k, s in c2.groupby(cls)[f"confluent_{H}"]]
    w(md(pd.DataFrame(rows)))

    from .schedules import exo_schedules
    first = {nm: wd[0] for nm, wd in exo_schedules()}
    r2 = runs[runs.condition == "C2_mutual_exo"].assign(first=lambda x: x.sched.map(first))
    g = r2.groupby(["inst_id", "first"])[f"d_{H}"].nunique().unstack()
    nc = c2.index[c2[f"confluent_{H}"] == False]  # noqa: E712
    fm = ((g.loc[nc].A == 1) & (g.loc[nc].B == 1))
    w(f"\n**First-mover diagnostic.** Of the {len(nc)} C2 instances that are non-confluent ({H}), "
      f"{int(fm.sum())} ({pct(fm.mean())}) are confluent *within* the A-first schedules and *within* the "
      "B-first schedules separately. For those instances, the whole schedule dependence is "
      "\"who moves first\".\n")

    w("\n## 4. Endogenous order\n")
    c1, c1m = by["C1_mutual_endo"], by["C1m_mutual_endo_maskyield"]
    w("**(a) Does the endogenous run's outcome match *any* of the 14 exogenous outcomes?** "
      "(count of the 2 endogenous runs whose outcome is in the exogenous set)\n")
    rows = []
    for c in ENDO:
        for p in PP:
            vc = by[c][f"n_endo_matching_exo_{p}"].value_counts(normalize=True)
            rows.append({"condition": c, "proj": p, **{f"{int(i)}/2 match": pct(vc.get(i, 0)) for i in (0, 1, 2)}})
    w(md(pd.DataFrame(rows)))
    um = c1.inst_id[c1[f"n_endo_matching_exo_{H}"] == 0]
    sv = runs[(runs.condition == "C1_mutual_endo") & runs.inst_id.isin(um)].groupby("inst_id").starved.any()
    w(f"\nOf the {len(um)} C1 instances where neither endogenous run matches any exogenous outcome "
      f"({H}), {pct(sv.mean())} have a starved machine in at least one endogenous run. Exogenous "
      "schedules cannot produce starvation by construction.\n")
    w("\n**(b) Do yield edits by R change the outcome? (C1 vs C1m, same start turn)** This is the "
      "operationalization of \"rewrites influence who moves next\".\n")
    y = c1.eff_yield_edits > 0
    w(f"- Instances where at least one yield edit actually changed a yield bit in C1: "
      f"{int(y.sum())} / {len(c1)} ({pct(y.mean())}).\n")
    rows = []
    for p in PP:
        col = f"n_endo_differs_from_mask_{p}"
        for lbl, sub in (("all instances", c1), ("yield edit fired", c1[y])):
            s = sub[col].dropna()
            rows.append({"proj": p, "subset": lbl, "≥1 start differs": rate(s > 0), "both starts differ": rate(s == 2)})
    w(md(pd.DataFrame(rows)))
    st = runs[runs.kind == "cycle"].groupby("condition").starved.mean().reindex(ORDER)
    w("\n**(c) Starvation.** Fraction of cycling runs in which a live machine never moves during the "
      "cycle:\n")
    w(md(pd.DataFrame({"condition": st.index, "starved": [pct(v) for v in st.values]})))
    if "forced_passes" in runs and meta.get("hold_cap"):
        en = runs[runs.condition.isin(ENDO)]
        fr = en.groupby("condition").apply(lambda x: pd.Series({
            "runs with ≥1 forced pass": pct((x.forced_passes > 0).mean()),
            "forced passes / steps (median)": f"{(x.forced_passes / x.steps.clip(lower=1)).median():.3f}"}))
        w(f"\nHold cap {meta['hold_cap']}: turn changes forced by the cap rather than a yield bit:\n")
        w(md(fr.reset_index()))

    w("\n## 5. Period and transient distributions (cycling runs)\n")
    cy = runs[runs.kind == "cycle"]
    q = cy.groupby("condition")[["period", "transient"]].describe(percentiles=[.5, .9, .99])
    rows = []
    for c in ORDER:
        rows.append({"condition": c, "cycles": int(q.loc[c, ("period", "count")]),
                     **{f"period {s}": int(q.loc[c, ("period", s)]) for s in ["min", "50%", "90%", "99%", "max"]},
                     **{f"transient {s}": int(q.loc[c, ("transient", s)]) for s in ["50%", "99%", "max"]}})
    w(md(pd.DataFrame(rows)))
    edges = [0, 2, 3, 5, 9, 17, 33, 65, 129, 1025, 10 ** 9]
    w("\nPeriod histogram (% of cycling runs), bins "
      + " / ".join(f"[{a},{b})" for a, b in zip(edges[:-1], edges[1:])) + ":\n")
    for c in ORDER:
        w(f"- {c}: {hist(cy[cy.condition == c].period, edges)}")
    w("\nTables settled (yield-stripped table pair constant over the cycle), % of cycling runs:\n")
    ts = cy.groupby("condition").tables_settled.mean().reindex(ORDER)
    w(md(pd.DataFrame({"condition": ts.index, "tables settled": [pct(v) for v in ts.values]})))

    w("\n## 6. Control C4: single self-modifying machine\n")
    c4 = runs[runs.condition == "C4_self"]
    c4c = c4[c4.kind == "cycle"]
    w(f"- {len(c4)} runs (machine A and machine B of every instance, each alone with R applied to itself).")
    w(f"- Halt: {pct((c4.kind == 'halt').mean())}. Cycle: {pct((c4.kind == 'cycle').mean())}. "
      f"Unresolved: {(c4.kind == 'unresolved').sum()}.")
    w(f"- Of the cycles, the table is constant over the cycle (\"table period 1\") in {pct(c4c.tables_settled.mean())}.")
    w(f"- Full-config period: median {int(c4c.period.median())}. Exactly N={meta['N']}: "
      f"{pct((c4c.period == meta['N']).mean())}. ≤ 2N: {pct((c4c.period <= 2 * meta['N']).mean())}. "
      f"Max {int(c4c.period.max())}. A full-config period of 1 is impossible here because the head moves every step.")
    w(f"- Transient: median {int(c4c.transient.median())}, max {int(c4c.transient.max())}.")

    w("\n## 7. Witnesses\n")
    wd = d / "witnesses"
    if wd.exists():
        for sub in sorted(wd.iterdir()):
            if (sub / "README.md").exists():
                first = (sub / "README.md").read_text().splitlines()[0].lstrip("# ")
                w(f"- `{sub.name}`: {first}")
    notes = d / "notes.md"
    if notes.exists():
        w("\n" + notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "results/m1")
    (d / "REPORT.md").write_text(build(d))
    print(f"wrote {d / 'REPORT.md'}")
