"""3-agent swarm: evaluate all conditions per instance, sweep in parallel.

    uv run python -m mt.swarm_sweep --out results/swarm_N8 --per-k 2500

Conditions (same instances, same schedules):
  L_exo_<g>    learning on, observation graph g, exogenous schedules     (confluence test)
  L_endo_<g>   learning on, endogenous order (route field + caps)        (target)
  Lm_endo_<g>  like L_endo, but edits to route fields are dropped        (does learning change who moves next?)
  Lo_exo_<g>   open loop: learning on, but agents act on their original tables (exposure-order
               effect alone, no behavioural feedback)
  F_exo        learning off (fixed tables), exogenous schedules          (control)
  F_endo       learning off, endogenous order                            (control)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import random
import statistics
import time
from pathlib import Path

import pandas as pd


from .swarm import (GRAPHS, append_once_variant, growth_variant, pregrown_variant, HOLD, M, THRESHOLD, TOGGLE, WAIT, SwarmInstance, canonical, exo_schedules,
                    noncommuting_pair, project, random_instance, run, starved)

PROJ = ("local_ti", "local", "tables", "tables_local")


def conditions():
    out = {}
    for g in GRAPHS:
        out[f"L_exo_{g}"] = ("on", "exo", g)
        out[f"L_endo_{g}"] = ("on", "endo", g)
        out[f"Lm_endo_{g}"] = ("mask_route", "endo", g)
        out[f"Lo_exo_{g}"] = ("open", "exo", g)          # open loop: learn, but act on original table
        out[f"C_exo_{g}"] = ("couple", "exo", g)         # physical coupling: observation writes tape, not rules
        out[f"C1_exo_{g}"] = ("couple_once", "exo", g)   # ... at most once per trigger and observer
    out["F_exo"] = ("off", "exo", "ring")        # graph irrelevant without learning
    out["F_endo"] = ("off", "endo", "ring")
    return out


def scheds(family):
    if family == "exo":
        return [(nm, ("exo", w)) for nm, w in exo_schedules()]
    return [(f"endo{'ABC'[i]}", ("endo", i)) for i in range(M)]


def inst_id(inst):
    return hashlib.blake2b(repr(inst.key()).encode(), digest_size=6).hexdigest()


def digest(o):
    if o is None:
        return None
    def canon(x):
        if isinstance(x, frozenset):
            return sorted(canon(y) for y in x)
        if isinstance(x, tuple):
            return tuple(canon(y) for y in x)
        return x
    return hashlib.blake2b(repr(canon(o)).encode(), digest_size=8).hexdigest()


def evaluate(inst: SwarmInstance, N=8, budget=200_000, base_id=None, only=None):
    iid = inst_id(inst)
    base = {"inst_id": iid, "base_id": base_id or iid, "k": inst.k, "N": N,
            "critical_pair": noncommuting_pair(inst.R)}     # = some pair of edits that don't commute
    conds = conditions()
    if only:
        import re
        conds = {c: v for c, v in conds.items() if re.search(only, c)}
    results = {c: [(nm, run(inst, learn, s, g, N, budget)) for nm, s in scheds(fam)]
               for c, (learn, fam, g) in conds.items()}
    out = {(c, nm, p): project(r, p, N) for c, rs in results.items() for nm, r in rs for p in PROJ}
    run_rows, cond_rows = [], []
    for c, rs in results.items():
        for nm, r in rs:
            tabs = {tuple(c_[4 * j + 3] for j in range(M)) for c_ in r.cycle}
            gained = differentiated = None
            if r.cycle:
                c0 = r.cycle[0]
                ns = c0[4 * M + 2]
                gained = sum(ns) - M * inst.n
                # copies whose rows no longer match ANY other state of the same agent = new concepts
                differentiated = 0
                for j in range(M):
                    T = c0[4 * j + 3]
                    rows = [T[8 * q:8 * q + 8] for q in range(ns[j])]
                    differentiated += sum(rows[q] not in rows[:q] + rows[q + 1:] for q in range(inst.n, ns[j]))
            run_rows.append(dict(base, condition=c, sched=nm, kind=r.kind, transient=r.transient,
                                 states_gained=gained, new_concepts=differentiated,
                                 period=r.period, steps=r.steps, eff_edits=r.eff_edits,
                                 eff_route_edits=r.eff_route_edits, forced=r.forced, overrides=r.overrides,
                                 starved=starved(r), tables_settled=(len(tabs) == 1) if r.cycle else None,
                                 d_local_ti=digest(out[(c, nm, "local_ti")])))
    for c, rs in results.items():
        learn, fam, g = conds[c]
        names = [nm for nm, _ in rs]
        resolved = all(r.kind != "unresolved" for _, r in rs)
        periods = [r.period for _, r in rs if r.kind == "cycle"]
        row = dict(base, condition=c, graph=g if learn != "off" else "none", family=fam,
                   n_runs=len(rs), n_unresolved=sum(r.kind == "unresolved" for _, r in rs),
                   median_period=statistics.median(periods) if periods else None,
                   n_starved=sum(starved(r) for _, r in rs),
                   eff_edits=sum(r.eff_edits for _, r in rs), eff_route_edits=sum(r.eff_route_edits for _, r in rs),
                   forced=sum(r.forced for _, r in rs), overrides=sum(r.overrides for _, r in rs),
                   steps=sum(r.steps for _, r in rs))
        for p in PROJ:
            os_ = {out[(c, nm, p)] for nm in names}
            row[f"n_distinct_{p}"] = len(os_) if resolved else None
            row[f"confluent_{p}"] = (len(os_) == 1) if resolved else None
        if fam == "endo":
            exo_c = f"L_exo_{g}" if learn != "off" else "F_exo"
            exo_ok = all(r.kind != "unresolved" for _, r in results[exo_c])
            for p in PROJ:
                ex = {out[(exo_c, nm, p)] for nm, _ in results[exo_c]}
                row[f"n_endo_matching_exo_{p}"] = (sum(out[(c, nm, p)] in ex for nm in names)
                                                   if resolved and exo_ok else None)
            if learn == "on":
                mc = f"Lm_endo_{g}"
                ok = resolved and all(r.kind != "unresolved" for _, r in results[mc])
                for p in PROJ:
                    row[f"n_endo_differs_from_mask_{p}"] = (
                        sum(out[(c, nm, p)] != out[(mc, nm, p)] for nm in names) if ok else None)
        cond_rows.append(row)
    return run_rows, cond_rows


def sample(n, per_k, seed):
    rng = random.Random(seed)
    seen, out = set(), []
    for k in range(1, 2 * n + 1):
        got = 0
        while got < per_k:
            c = canonical(random_instance(n, k, rng))
            if c not in seen:
                seen.add(c)
                out.append(c)
                got += 1
    return out


def with_edit_kind(inst: SwarmInstance, kind: str, seed: str) -> SwarmInstance:
    """Same tables, triggers and targets; only the edit operation changes.
    set: as sampled. toggle: every edit toggles. mixed: each edit is set or toggle (fair coin).
    threshold: every edit is an evidence-threshold revision (see mt.swarm.edit_op)."""
    if kind == "set":
        return inst
    if kind in ("append", "append_off"):
        return growth_variant(inst, seed, cap=4, appends=kind == "append")
    if kind == "append_once":
        return append_once_variant(growth_variant(inst, seed, cap=4))
    if kind == "append_pregrown":
        return pregrown_variant(growth_variant(inst, seed, cap=4))
    rng = random.Random(f"edit-kind-{seed}")
    R = []
    for x in inst.R:
        if x is None:
            R.append(None)
            continue
        op = {"toggle": TOGGLE, "threshold": THRESHOLD}.get(kind) or rng.choice((0, TOGGLE))
        R.append(tuple(x[:3]) + (op,))
    return SwarmInstance(inst.n, inst.tables, tuple(R))


def _work(a):
    return evaluate(*a)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/swarm_N8")
    ap.add_argument("--N", type=int, default=8)
    ap.add_argument("--per-k", type=int, default=2500)
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--only", help="regex: run only conditions whose name matches")
    ap.add_argument("--instances", help="reuse instances.jsonl (matched comparison) instead of sampling")
    ap.add_argument("--edit-kind", default="set",
                    choices=("set", "toggle", "mixed", "threshold", "append", "append_off",
                             "append_once", "append_pregrown"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.instances:
        src = []
        for line in open(a.instances):
            j = json.loads(line)
            bid = j.pop("base_id", None) or j.pop("inst_id")
            j.pop("inst_id", None)
            src.append((bid, SwarmInstance.from_json(j)))
    else:
        src = [(inst_id(i), i) for i in sample(2, a.per_k, a.seed)]
    pairs = [(bid, with_edit_kind(i, a.edit_kind, bid)) for bid, i in src]
    insts = [i for _, i in pairs]
    with open(out / "instances.jsonl", "w") as f:
        for bid, i in pairs:
            f.write(json.dumps({"inst_id": inst_id(i), "base_id": bid, **i.to_json()}) + "\n")
    rr, cr = [], []
    with mp.Pool() as pool:
        for j, (x, y) in enumerate(pool.imap(_work, [(i, a.N, a.budget, bid, a.only) for bid, i in pairs], chunksize=4)):
            rr += x
            cr += y
            if (j + 1) % 2500 == 0:
                print(f"  {j + 1}/{len(insts)}  {time.time() - t0:.0f}s", flush=True)
    pd.DataFrame(rr).to_parquet(out / "runs.parquet")
    pd.DataFrame(cr).to_parquet(out / "results.parquet")
    pd.DataFrame(cr).to_csv(out / "results.csv", index=False)
    meta = {**vars(a), "M": M, "hold_cap": HOLD, "wait_cap": WAIT, "n_instances": len(insts),
            "n_exo_schedules": len(exo_schedules()), "seconds": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"done in {meta['seconds']}s")


if __name__ == "__main__":
    main()
