"""Compare sweeps of the SAME instances at different tape lengths N.

    uv run python -m mt.compare results/m2/COMPARE.md results/m1 results/m2_N16 results/m2_N32

Confluence rates are computed on the *matched* set: instances whose relevant runs are resolved at
every N, so that rising unresolved counts at larger N cannot shift the rates by selection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .report import ORDER, md, pct, wilson
from .schedules import exo_schedules

PROJ = ["local", "joint", "tables", "class"]


def rate(s: pd.Series) -> str:
    s = s.astype(bool)
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}]" if n else "–"


def load(d: Path):
    meta = json.loads((d / "meta.json").read_text())
    return meta["N"], pd.read_parquet(d / "results.parquet"), pd.read_parquet(d / "runs.parquet")


def build(dirs: list[Path]) -> str:
    data = {}
    for d in dirs:
        N, res, runs = load(d)
        data[N] = (res, runs)
    Ns = sorted(data)
    L = []
    w = L.append
    w(f"# Cross-N comparison: N = {', '.join(map(str, Ns))} (same instances)\n")
    w("Exploratory simulation output. These are counts and rates over one random sample of instances at "
      "a fixed budget of 200k steps per run. No result here is a proof or a convergence claim.\n")
    n_inst = {N: data[N][0].inst_id.nunique() for N in Ns}
    assert len(set(n_inst.values())) == 1, n_inst
    ids = [set(data[N][0].inst_id) for N in Ns]
    assert all(x == ids[0] for x in ids), "sweeps are not on the same instances"
    w(f"- {n_inst[Ns[0]]} instances, identical across N (checked).\n")

    # ------------------------------------------------------------------ unresolved
    w("## 1. Run outcomes and unresolved runs\n")
    rows = []
    for c in ORDER:
        r = {"condition": c}
        for N in Ns:
            k = data[N][1][data[N][1].condition == c].kind.value_counts(normalize=True)
            r[f"N={N} halt/cycle/unres"] = (f"{pct(k.get('halt', 0))} / {pct(k.get('cycle', 0))} / "
                                            f"{100 * k.get('unresolved', 0):.2f}%")
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    rows = []
    for N in Ns:
        u = data[N][1][data[N][1].kind == "unresolved"]
        rows.append({"N": N, "unresolved runs": len(u), "instances affected": u.inst_id.nunique(),
                     **{c: int((u.condition == c).sum()) for c in ORDER}})
    w("\nUnresolved runs at budget, per condition:\n")
    w(md(pd.DataFrame(rows)))

    # ------------------------------------------------------------------ matched set
    def determined(N, cond, col):
        r = data[N][0]
        r = r[r.condition == cond].set_index("inst_id")[col]
        return r

    def matched(cond, col):
        ss = [determined(N, cond, col) for N in Ns]
        ok = pd.concat([s.notna() for s in ss], axis=1).all(axis=1)
        return {N: s[ok] for N, s in zip(Ns, ss)}, int(ok.sum())

    w("\n## 2. Confluence across N (matched instances)\n")
    w("Exogenous rows (C2, C3): all 14 schedules agree. Endogenous rows (C1, C1m, C3e): start A and start "
      "B agree (start-turn independence). That is a different quantity, kept in separate rows. "
      "`n` = instances determined at every N.\n")
    rows = []
    for c in ["C2_mutual_exo", "C3_fixed_exo", "C1_mutual_endo", "C1m_mutual_endo_maskyield", "C3e_fixed_endo"]:
        for p in PROJ:
            m, n = matched(c, f"confluent_{p}")
            rows.append({"condition": c, "proj": p, "n": n, **{f"N={N}": rate(m[N]) for N in Ns}})
    w(md(pd.DataFrame(rows)))

    w("\n## 3. Delta C2 − C3 (percentage points), by rule size k, matched instances\n")
    rows = []
    for p in ["local", "joint"]:
        m2, _ = matched("C2_mutual_exo", f"confluent_{p}")
        m3, _ = matched("C3_fixed_exo", f"confluent_{p}")
        kk = data[Ns[0]][0].drop_duplicates("inst_id").set_index("inst_id").k
        for k in sorted(kk.unique()):
            r = {"proj": p, "k": k}
            for N in Ns:
                common = m2[N].index.intersection(m3[N].index)
                common = common[kk.loc[common] == k]
                a, b = m2[N].loc[common].astype(float).mean(), m3[N].loc[common].astype(float).mean()
                r[f"N={N}"] = f"{100 * a:.1f} − {100 * b:.1f} = {100 * (a - b):+.1f}"
            rows.append(r)
    w(md(pd.DataFrame(rows)))

    w("\n## 4. Same instance, different N: does C2 `local` confluence change?\n")
    m, n = matched("C2_mutual_exo", "confluent_local")
    df = pd.DataFrame({N: m[N].astype(bool) for N in Ns})
    pat = df.apply(lambda r: "".join("C" if v else "x" for v in r), axis=1)
    vc = pat.value_counts()
    w(f"Pattern over N={'/'.join(map(str, Ns))} (C = confluent, x = not), {n} matched instances:\n")
    w(md(pd.DataFrame({"pattern": vc.index, "instances": vc.values, "share": [pct(v / n) for v in vc.values]})))
    for a, b in zip(Ns[:-1], Ns[1:]):
        x = pd.crosstab(df[a].map({True: f"conf @N={a}", False: f"nonconf @N={a}"}),
                        df[b].map({True: f"conf @N={b}", False: f"nonconf @N={b}"}))
        w(f"\nN={a} → N={b}:\n")
        w(md(x.reset_index().rename(columns={x.index.name or "row_0": ""})))

    # ------------------------------------------------------------------ endogenous
    w("\n## 5. Endogenous order across N\n")
    rows = []
    for N in Ns:
        res, runs = data[N]
        c1 = res[res.condition == "C1_mutual_endo"]
        y = c1.eff_yield_edits > 0
        dm = c1.n_endo_differs_from_mask_local.dropna()
        dmy = c1[y].n_endo_differs_from_mask_local.dropna()
        um = c1.n_endo_matching_exo_local.dropna()
        st = runs[runs.kind == "cycle"].groupby("condition").starved.mean()
        umids = c1.inst_id[c1.n_endo_matching_exo_local == 0]
        sv = runs[(runs.condition == "C1_mutual_endo") & runs.inst_id.isin(umids)].groupby("inst_id").starved.any()
        rows.append({"N": N,
                     "yield edit fired": pct(y.mean()),
                     "C1≠C1m (all)": rate(dm > 0),
                     "C1≠C1m (yield fired)": rate(dmy > 0),
                     "C1 matches no exo": rate(um == 0),
                     "…of which starved": pct(sv.mean()) if len(sv) else "–",
                     "starved cycles C1 / C3e": f"{pct(st.get('C1_mutual_endo', 0))} / {pct(st.get('C3e_fixed_endo', 0))}"})
    w("All projections are `local`. C1≠C1m = at least one start turn's outcome changes when yield edits are "
      "masked. Each N uses the instances determined at that N.\n")
    w(md(pd.DataFrame(rows)))

    # ------------------------------------------------------------------ first mover
    w("\n## 6. First-mover share of C2 non-confluence (local)\n")
    first = {nm: wd[0] for nm, wd in exo_schedules()}
    rows = []
    for N in Ns:
        res, runs = data[N]
        c2 = res[res.condition == "C2_mutual_exo"]
        nc = c2.inst_id[c2.confluent_local == False]  # noqa: E712
        r2 = runs[(runs.condition == "C2_mutual_exo") & runs.inst_id.isin(nc)]
        g = r2.assign(first=r2.sched.map(first)).groupby(["inst_id", "first"]).d_local.nunique().unstack()
        fm = (g.A == 1) & (g.B == 1)
        rows.append({"N": N, "non-confluent": len(nc), "explained by first mover alone": f"{int(fm.sum())} ({pct(fm.mean())})"})
    w(md(pd.DataFrame(rows)))

    # ------------------------------------------------------------------ periods
    w("\n## 7. Periods and transients (cycling runs)\n")
    rows = []
    for c in ORDER:
        r = {"condition": c}
        for N in Ns:
            cy = data[N][1]
            cy = cy[(cy.condition == c) & (cy.kind == "cycle")]
            r[f"N={N} period p50/p90/p99/max"] = "/".join(str(int(cy.period.quantile(q))) for q in (.5, .9, .99)) + f"/{int(cy.period.max())}"
            r[f"N={N} transient p50/p99"] = f"{int(cy.transient.median())}/{int(cy.transient.quantile(.99))}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    w("\nPeriod divided by N: median and share of cycling runs whose period is an exact multiple of N:\n")
    rows = []
    for c in ORDER:
        r = {"condition": c}
        for N in Ns:
            cy = data[N][1]
            cy = cy[(cy.condition == c) & (cy.kind == "cycle")]
            r[f"N={N}"] = f"{(cy.period / N).median():.2f} | {pct((cy.period % N == 0).mean())}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    w("\nTables settled over the cycle (yield-stripped), % of cycling runs:\n")
    rows = []
    for c in ORDER:
        r = {"condition": c}
        for N in Ns:
            cy = data[N][1]
            r[f"N={N}"] = pct(cy[(cy.condition == c) & (cy.kind == "cycle")].tables_settled.mean())
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    notes = Path(sys.argv[1]).parent / "notes.md" if len(sys.argv) > 1 else None
    if notes and notes.exists():
        w("\n" + notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build([Path(p) for p in sys.argv[2:]]))
    print(f"wrote {out}")
