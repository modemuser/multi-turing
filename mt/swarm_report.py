"""Report for a 3-agent swarm sweep, plus witnesses.

    uv run python -m mt.swarm_report results/swarm_N8
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

from .report import md, pct, wilson
from .swarm import GRAPHS

H = "local_ti"
G = list(GRAPHS)


def rate(s):
    s = s.dropna().astype(bool)
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}] (n={n})" if n else "–"


def witnesses(d: Path, res, runs):
    from . import swarm_repro
    insts = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        insts[j.pop("inst_id")] = j
    steps = runs.groupby(["inst_id", "condition"]).steps.sum()
    piv = res.pivot_table(index="inst_id", columns="condition", values=f"confluent_{H}", aggfunc="first")
    endo = res[res.condition == "L_endo_complete"].set_index("inst_id")
    kk = res.drop_duplicates("inst_id").set_index("inst_id").k
    picks = {
        "complete_only_nonconfluent": (piv.index[(piv["L_exo_complete"] == False) & (piv["L_exo_ring"] == True)  # noqa: E712
                                                  & (piv["L_exo_decoupled"] == True)], "L_exo_complete",  # noqa: E712
                                       "order matters with two observed sources (complete) but not in ring or decoupled"),
        "routing_matters_complete": (endo.index[endo[f"n_endo_differs_from_mask_{H}"] > 0], "L_endo_complete",
                                     "learning that rewrites who-moves-next changes the outcome (complete)"),
        "endo_unmatched_complete": (endo.index[endo[f"n_endo_matching_exo_{H}"] == 0], "L_endo_complete",
                                    "no endogenous run (any start) reaches an outcome any exogenous schedule reaches (complete)"),
    }
    out = d / "witnesses"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    lines = []
    for tag, (ids, cond, title) in picks.items():
        ids = sorted(ids, key=lambda i: (kk[i], steps.get((i, cond), 0)))[:4]
        for n_, i in enumerate(ids, 1):
            wd = out / f"{tag}_{n_:02d}_k{kk[i]}_{i}"
            wd.mkdir()
            (wd / "instance.json").write_text(json.dumps(insts[i], indent=1))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                swarm_repro.main([str(wd / "instance.json")])
            cmd = f"uv run python -m mt.swarm_repro {wd}/instance.json"
            (wd / "README.md").write_text(f"# {title}: k={kk[i]}\n\n```bash\n{cmd}\n```\n\n```\n{buf.getvalue()}```\n")
            lines.append(f"- `{wd.name}`: {title}")
    return lines


def build(d: Path) -> str:
    meta = json.loads((d / "meta.json").read_text())
    res = pd.read_parquet(d / "results.parquet")
    runs = pd.read_parquet(d / "runs.parquet")
    by = {c: res[res.condition == c].set_index("inst_id") for c in res.condition.unique()}
    L = []
    w = L.append
    w(f"# 3-agent swarm report ({d.name}): n=2 states, N={meta['N']}, no halting\n")
    w("Exploratory simulation output: counts and rates over a random sample at a finite budget. "
      "Nothing here is a proof.\n")
    w(f"- {meta['n_instances']} instances ({meta['per_k']} per rule size k=1..4), seed {meta['seed']}. "
      f"Each instance = three random 2-state tables + one shared, anonymous learning rule R.")
    w(f"- {meta['n_exo_schedules']} exogenous schedules (closed under relabelling A/B/C). Endogenous order "
      f"uses route fields, hold cap {meta['hold_cap']} and wait cap {meta['wait_cap']}. 3 start turns.")
    w(f"- Learning-rule edit kind: **{meta.get('edit_kind', 'set')}** (set = overwrite a field; toggle = advance it "
      f"cyclically, commutative but not idempotent; mixed = each edit randomly set or toggle).")
    w(f"- Graphs: ring (one observed source per agent), complete (two sources), decoupled (A↔B, C isolated).")
    w(f"- Headline projection `{H}`: each agent's cycle (state, head, tape, table without route bits), up to "
      f"a cyclic shift of that agent's own tape. Budget {meta['budget']} steps. {len(runs)} runs, "
      f"{meta['seconds']} s.\n")

    un = runs[runs.kind == "unresolved"]
    w(f"Unresolved runs: {len(un)} in {un.inst_id.nunique()} instances "
      f"({', '.join(f'{c}: {n}' for c, n in un.condition.value_counts().items()) or 'none'}).\n")

    w("## 1. Exogenous order: confluence (all schedules agree)\n")
    rows = []
    for c in [f"L_exo_{g}" for g in G] + ["F_exo"]:
        rows.append({"condition": c, **{p: rate(by[c][f"confluent_{p}"]) for p in ("local_ti", "local", "tables")},
                     "mean # distinct (local_ti)": f"{by[c][f'n_distinct_{H}'].mean():.3f}"})
    w(md(pd.DataFrame(rows)))
    w("\nDelta vs no learning (F_exo), `local_ti`, percentage points, by rule size k:\n")
    rows = []
    for k in sorted(res.k.unique()):
        f = by["F_exo"][by["F_exo"].k == k][f"confluent_{H}"].dropna().astype(float).mean()
        r = {"k": k}
        for g in G:
            x = by[f"L_exo_{g}"]
            a = x[x.k == k][f"confluent_{H}"].dropna().astype(float).mean()
            r[g] = f"{100 * a:.1f} − {100 * f:.1f} = {100 * (a - f):+.1f}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))

    w("\n## 2. Ring vs complete on the same instances (`local_ti`, exogenous)\n")
    a, b = by["L_exo_ring"][f"confluent_{H}"], by["L_exo_complete"][f"confluent_{H}"]
    ok = a.notna() & b.notna()
    x = pd.crosstab(a[ok].map({True: "ring confluent", False: "ring non-confluent"}),
                    b[ok].map({True: "complete confluent", False: "complete non-confluent"}))
    w(md(x.reset_index().rename(columns={x.index.name: ""})))
    w("\n*Ring has one observed source per agent. Complete has two, so updates from two agents can "
      "land on the same table entry in an order that depends on the schedule.*\n")

    w("**Pairwise, same instances:** count of instances that are order-dependent (`local_ti`, exogenous) "
      "under one graph but not the other.\n")
    gs = [g for g in ("ring", "alternating", "complete") if f"L_exo_{g}" in by]
    rows = []
    for i, g1 in enumerate(gs):
        for g2 in gs[i + 1:]:
            a, b = by[f"L_exo_{g1}"][f"confluent_{H}"], by[f"L_exo_{g2}"][f"confluent_{H}"]
            ok = a.notna() & b.notna()
            a, b = a[ok].astype(bool), b[ok].astype(bool)
            rows.append({"first vs second": f"{g1} vs {g2}", "only first": int((~a & b).sum()),
                         "only second": int((a & ~b).sum()), "both": int((~a & ~b).sum())})
    w(md(pd.DataFrame(rows)))

    w("\n**Edit volume and critical pairs.** Two observed sources can only *conflict* when R has a "
      "non-commuting pair of edits on the same field (\"crit. pair\"), because R is anonymous and shared. `alternating` has the same edit volume per event as "
      "`ring`, but two sources per agent, like `complete`.\n")
    rows = []
    ex = runs[runs.condition.str.startswith("L_exo_")]
    vol = (ex.eff_edits / ex.steps.clip(lower=1)).groupby(ex.condition).median()
    for g in G:
        x = by[f"L_exo_{g}"]
        e = by[f"L_endo_{g}"]
        r = {"graph": g, "effective edits / step (median)": f"{vol.get(f'L_exo_{g}', float('nan')):.4f}"}
        if "critical_pair" in x:
            for cp, lbl in ((False, "no crit. pair"), (True, "crit. pair")):
                sub = x[x.critical_pair == cp][f"confluent_{H}"].dropna().astype(bool)
                r[f"order-dependent, {lbl}"] = f"{1 - sub.mean():.3f} (n={len(sub)})"
                es = e[e.critical_pair == cp][f"n_endo_differs_from_mask_{H}"].dropna()
                r[f"routing matters, {lbl}"] = f"{(es > 0).mean():.3f}"
        rows.append(r)
    w(md(pd.DataFrame(rows)))
    w("")

    if any(f"Lo_exo_{g}" in by for g in G):
        w("## 2b. Open loop vs closed loop (exogenous)\n")
        w("**Open loop** (`Lo_exo`): agents learn, but act on their original tables, so every emitted stream is "
          "fixed. Order can only change the learned tables through the *merge order* of those fixed streams "
          "(exposure order). **Closed loop** (`L_exo`): what an agent learns changes what it emits, and so what "
          "the others learn (behavioural feedback). Projection `tables_local`: per agent, the set of learned "
          "tables it holds during the cycle. That set is comparable in both loops. (`local_ti` is not "
          "comparable in open loop, because pairing an agent's own position with a table that doesn't steer "
          "it is an interleaving artifact.)\n")
        rows = []
        for g in G:
            if f"Lo_exo_{g}" not in by:
                continue
            o, c = by[f"Lo_exo_{g}"], by[f"L_exo_{g}"]
            r = {"graph": g,
                 "open: order-dependent": rate(~o["confluent_tables_local"].dropna().astype(bool)),
                 "closed: order-dependent": rate(~c["confluent_tables_local"].dropna().astype(bool))}
            if "critical_pair" in o:
                for cp, lbl in ((False, "no crit. pair"), (True, "crit. pair")):
                    oo = o[o.critical_pair == cp]["confluent_tables_local"].dropna().astype(bool)
                    cc = c[c.critical_pair == cp]["confluent_tables_local"].dropna().astype(bool)
                    r[f"open / closed, {lbl}"] = f"{1 - oo.mean():.3f} / {1 - cc.mean():.3f}"
            rows.append(r)
        w(md(pd.DataFrame(rows)))
        if "Lo_exo_complete" in by:
            a, b = by["Lo_exo_complete"]["confluent_tables_local"], by["L_exo_complete"]["confluent_tables_local"]
            ok = a.notna() & b.notna()
            x = pd.crosstab(a[ok].astype(bool).map({True: "open: confluent", False: "open: order-dependent"}),
                            b[ok].astype(bool).map({True: "closed: confluent", False: "closed: order-dependent"}))
            w("\nComplete graph, same instances:\n")
            w(md(x.reset_index().rename(columns={x.index.name: ""})))
        w("")

    w("## 3. Endogenous order (who moves next is in the tables, and learning can rewrite it)\n")
    rows = []
    for g in G:
        e, m = by[f"L_endo_{g}"], by[f"Lm_endo_{g}"]
        rf = e.eff_route_edits > 0
        dm = e[f"n_endo_differs_from_mask_{H}"]
        rows.append({"graph": g,
                     "start-turn independent": rate(e[f"confluent_{H}"]),
                     "matches no exo (all 3 starts)": rate(e[f"n_endo_matching_exo_{H}"].dropna() == 0),
                     "route edit fired": pct(rf.mean()),
                     "routing learning changes outcome (all)": rate(dm.dropna() > 0),
                     "… (route edit fired)": rate(dm[rf].dropna() > 0)})
    f = by["F_endo"]
    rows.append({"graph": "none (F_endo)", "start-turn independent": rate(f[f"confluent_{H}"]),
                 "matches no exo (all 3 starts)": rate(f[f"n_endo_matching_exo_{H}"].dropna() == 0),
                 "route edit fired": "–", "routing learning changes outcome (all)": "–", "… (route edit fired)": "–"})
    w(md(pd.DataFrame(rows)))
    en = runs[runs.condition.str.contains("endo")]
    fr = en.groupby("condition").apply(lambda x: pd.Series({
        "starved runs": pct(x.starved.mean()),
        "forced passes / steps": f"{(x.forced / x.steps.clip(lower=1)).median():.3f}",
        "fairness overrides / steps": f"{(x.overrides / x.steps.clip(lower=1)).median():.3f}"}))
    w("\nHow much of the endogenous order is set by the caps (median per run):\n")
    w(md(fr.reset_index()))

    w("\n## 4. Periods, transients, settling (cycling runs)\n")
    cy = runs[runs.kind == "cycle"]
    rows = []
    for c in sorted(cy.condition.unique()):
        x = cy[cy.condition == c]
        rows.append({"condition": c, "period p50/p90/p99": "/".join(str(int(x.period.quantile(q))) for q in (.5, .9, .99)),
                     "transient p50/p99": f"{int(x.transient.median())}/{int(x.transient.quantile(.99))}",
                     "tables settled": pct(x.tables_settled.mean())})
    w(md(pd.DataFrame(rows)))

    w("\n## 5. Witnesses (smallest first)\n")
    for line in witnesses(d, res, runs):
        w(line)
    notes = d / "notes.md"
    if notes.exists():
        w("\n" + notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "results/swarm_N8")
    (d / "REPORT.md").write_text(build(d))
    print(f"wrote {d / 'REPORT.md'}")
