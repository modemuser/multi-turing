"""Every number the post cites, recomputed from results/publish/ (produced by mt.pipeline).

    uv run python -m mt.post_numbers            # writes results/publish/POST_NUMBERS.md

Each line: post section, quantity, value (95% Wilson CI where the post gives one).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .report import wilson
from .swarm import SwarmInstance, noncommuting_pair

P = Path("results/publish")
L: list[str] = []


def emit(sec, what, val):
    L.append(f"| {sec} | {what} | {val} |")


def ci(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def cboot(df, num, B=4000, seed=0):
    """Share of `num` over rows, with a 95% CI from a bootstrap over BASE instances (rows of the same
    instance, including its rule replicates "id#r", are correlated). Returns a formatted string."""
    import numpy as np
    if len(df) == 0:
        return "–"
    cl = df["inst_id"].astype(str).str.split("#").str[0]
    g = df.assign(_c=cl, _n=df[num].astype(bool)).groupby("_c")
    a, b = g["_n"].sum().values.astype(float), g.size().values.astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (B, len(a)))
    bs = a[idx].sum(1) / b[idx].sum(1)
    return (f"{int(a.sum())}/{int(b.sum())} = {100 * a.sum() / b.sum():.1f}% "
            f"[{100 * np.quantile(bs, .025):.1f}, {100 * np.quantile(bs, .975):.1f}] ({len(a)} instances, clustered)")


def dep(res, cond, col, ids=None):
    x = res[res.condition == cond]
    if ids is not None:
        x = x[x.base_id.isin(ids) if "base_id" in x else x.inst_id.isin(ids)]
    s = x[col].dropna().astype(bool)
    return ci(int((~s).sum()), len(s))


def load(name):
    r = pd.read_parquet(P / name / "results.parquet")
    if "base_id" not in r:
        r["base_id"] = r["inst_id"]
    return r


def main():
    probe_ids = {json.loads(l)["inst_id"] for l in open(P / "probe400.jsonl")}
    st = load("set")
    # §3 coupling vs learning (full outcome, complete, probe subset)
    emit("§3", "no interaction, order-dependent (full outcome)", dep(st, "F_exo", "confluent_local_ti", probe_ids))
    emit("§3", "physical coupling, volume-matched", dep(st, "C1_exo_complete", "confluent_local_ti", probe_ids))
    emit("§3", "learning (overwrite)", dep(st, "L_exo_complete", "confluent_local_ti", probe_ids))
    # §4 ring, open loop, learned program
    for nm in ("set", "threshold", "toggle", "append"):
        r = st if nm == "set" else load(nm)
        emit("§4", f"ring, open loop, {nm}", dep(r, "Lo_exo_ring", "confluent_tables_local", probe_ids if nm == "set" else None))
    # §4 table
    for nm in ("set", "threshold", "toggle", "append"):
        r = st if nm == "set" else load(nm)
        ids = probe_ids if nm == "set" else None
        emit("§4", f"{nm}: open loop", dep(r, "Lo_exo_complete", "confluent_tables_local", ids))
        emit("§4", f"{nm}: closed loop", dep(r, "L_exo_complete", "confluent_tables_local", ids))
    # §4 conflicts and ping-pong (800-instance overwrite probe)
    cp = {}
    for l in open(P / "set" / "instances.jsonl"):
        j = json.loads(l)
        cp[j["inst_id"]] = noncommuting_pair(SwarmInstance.from_json(j).R)
    runs = pd.read_parquet(P / "set" / "runs.parquet")
    lo = runs[(runs.condition == "Lo_exo_complete") & runs.inst_id.map(cp)]
    emit("§4", "instances with conflicting overwrites", f"{sum(cp.values())} of {len(cp)}")
    emit("§4", "share of their cycles that keep changing", f"{(lo.tables_settled == False).mean():.1%}")  # noqa: E712
    for nm in ("set", "append"):
        c = pd.read_csv(P / nm / "closed_loop.csv")
        d = c[c.tab_dep]
        emit("§4 L7", f"{nm}: order-dependent learners with a varying source stream",
             f"{int(d.source_stream_varies.sum())} of {len(d)}")
    # §5 pre-grown + mix table
    emit("§5", "pre-grown, open loop order-dependent", dep(load("pregrown"), "Lo_exo_complete", "confluent_tables_local"))
    m = pd.read_csv(P / "mix" / "mix_runs.csv", low_memory=False)
    for col in ("closed_synth", "closed_brick", "open_brick"):
        m[col] = m[col].astype(str).eq("True")
    for p, sub in m.groupby("p_append"):
        syn = sub[sub.closed_synth]
        inst = sub.groupby("inst_id").closed_brick.any()
        emit("§5", f"p_append {p}: synthesis (agent x schedule)", cboot(sub, "closed_synth"))
        emit("§5", f"p_append {p}: P(new brick | synthesis)", cboot(syn, "closed_brick"))
        units = inst.rename("x").reset_index()          # one row per (instance, rule draw)
        emit("§5", f"p_append {p}: instances (x rule draws) with a new brick", cboot(units, "x"))
        if p == 0.5:
            br = sub[sub.closed_brick]
            fr = br[~br.open_brick]
            emit("§1/§6", "new bricks (agent x schedule) / feedback-required",
                 f"{len(br)} / {cboot(br.assign(fb=~br.open_brick), 'fb')}")
            emit("§1", "instances (x rule draws) with a new brick", cboot(units, "x"))
            fbb = pd.read_csv(P / "bricks" / "feedback_behaviour.csv")
            emit("§1", "new bricks feedback-required at the behaviour level / by both definitions",
                 f"{cboot(fbb, 'fb_behaviour')} / {cboot(fbb, 'fb_both')}")
    # §5 synthesis (open loop, append) and L6
    si = pd.read_csv(P / "append" / "synthesis" / "instances.csv")
    for kind, sub in si.groupby("kind"):
        emit("§5", f"synthesis instances, class '{kind}'", f"{int(sub.strict.sum())} of {len(sub)}")
    od = si[si.order_dependent == True]  # noqa: E712
    emit("§5", "order-dependent instances that synthesise (strict / fine)",
         f"{int(od.strict.sum())} / {int(od.fine.sum())} of {len(od)}")
    tot_no = tot_syn = 0
    for nm in ("append", "append_once"):
        c = pd.read_csv(P / nm / "synthesis" / "L6_cycle.csv")
        no = c[c.precedence_cycle == False]  # noqa: E712
        tot_no += int(no.pairs.sum())
        tot_syn += int(no.synthesis.sum())
    emit("§5 L6", "pairs without a precedence cycle / synthesis among them", f"{tot_no} / {tot_syn}")
    for rs in ("set", "append"):
        sp = pd.read_parquet(P / "closed_serial" / f"serial_{rs}.parquet")
        s = sp[sp["mode"] == "learn"].synth_rules.astype(bool)
        emit("§5", f"closed loop, program-level non-serialisable, {rs}",
             cboot(sp[sp["mode"] == "learn"].assign(x=s.values), "x"))
    # §6 bricks
    b = pd.read_csv(P / "bricks" / "brick_tapes.csv")
    br = b[b.tapes_differ > 0]
    emit("§6", "synthesised programs that are new bricks (256 tapes)", cboot(b.assign(x=b.tapes_differ > 0), "x"))
    emit("§6", "... on the 4 FRESH tapes", cboot(b, "fresh4"))
    x = br.tapes_differ
    emit("§6", "tapes differing: median / IQR / >=128 / all 256 / <=8",
         f"{x.median():.0f} / {x.quantile(.25):.0f}-{x.quantile(.75):.0f} / {(x >= 128).mean():.1%} / "
         f"{(x == 256).mean():.1%} / {int((x <= 8).sum())} bricks")
    e = pd.read_csv(P / "endo" / "endo_runs.csv")
    for col in ("closed_synth", "closed_brick", "order_changed_by_learning"):
        e[col] = e[col].astype(str).eq("True")
    rr = e.drop_duplicates(["inst_id", "start"])
    emit("§6", "endogenous: runs where learning changed who moves", cboot(rr, "order_changed_by_learning"))
    syn = e[e.closed_synth]
    emit("§6", "endogenous: P(new brick | synthesis)", cboot(syn, "closed_brick"))
    # §7
    n3 = pd.read_csv(P / "n3" / "robust_runs.csv", low_memory=False)
    for col in ("closed_synth", "closed_brick", "open_brick"):
        n3[col] = n3[col].astype(str).eq("True")
    a = n3[n3.learner == "append"]
    inst = a.groupby("inst_id").closed_brick.any()
    br = a[a.closed_brick]
    emit("§7", "3-state: instances with a new brick", ci(int(inst.sum()), len(inst)))
    emit("§7", "3-state: feedback-required share", cboot(br.assign(fb=~br.open_brick), "fb"))
    emit("§7", "3-state: P(new brick | synthesis)", cboot(a[a.closed_synth], "closed_brick"))
    emit("§7", "3-state: new bricks without revision rules", int(a[(a.n_revise == 0)].closed_brick.sum()))
    z = (P / "zeros" / "ZEROS.md").read_text()
    L.append("\n### §7 exception hunt (verbatim)\n")
    L.append(z[z.index("|"):])
    out = P / "POST_NUMBERS.md"
    out.write_text("# Numbers cited in the post, recomputed by mt.pipeline\n\n| section | quantity | value |\n|---|---|---|\n"
                   + "\n".join(L) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
