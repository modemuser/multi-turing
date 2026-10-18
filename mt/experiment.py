"""Run all conditions on one instance and turn the results into table rows."""
from __future__ import annotations

import hashlib
import statistics

from .engine import RunResult, run, run_single
from .model import Instance, has_critical_pair
from .schedules import exo_schedules

# Projections strip the yield bits from tables (they are inert under exogenous schedules, and
# C1 vs C1m would otherwise differ trivially whenever a yield edit fired). `local_y` keeps them.
# `local_ti` = `local` up to translation: each machine's cycle set is canonicalized under a cyclic
# shift of its own tape + head. Machines never see absolute position (R reads only (state, symbol
# written); tapes start blank), so a shifted cycle is the same behaviour at another place. Headline.
PROJECTIONS = ("local_ti", "local", "joint", "tables", "class", "local_y")
HEADLINE = "local_ti"


def _strip(T):
    return T[0:3] + T[4:7] + T[8:11] + T[12:15] if len(T) == 16 else tuple(
        v for i, v in enumerate(T) if i % 4 != 3)

# condition id -> (rewrite mode, schedule family)
CONDITIONS = {
    "C1_mutual_endo": ("mutual", "endo"),
    "C1m_mutual_endo_maskyield": ("mask_yield", "endo"),
    "C2_mutual_exo": ("mutual", "exo"),
    "C3_fixed_exo": ("off", "exo"),
    "C3e_fixed_endo": ("off", "endo"),
    "C4_self": ("self", "self"),
}


def schedules_for(family: str, hold_cap: int | None = None):
    if family == "exo":
        return [(name, ("exo", w)) for name, w in exo_schedules()]
    if family == "endo":
        return [("endoA", ("endo", 0, hold_cap)), ("endoB", ("endo", 1, hold_cap))]
    return [("selfA", None), ("selfB", None)]


def translation_canon(S, N: int) -> tuple:
    """Canonical form of a set of (state, head, tape, table) under a common cyclic shift by d."""
    mask = (1 << N) - 1
    best = None
    for d in range(N):
        rot = (lambda t: ((t >> d) | (t << (N - d))) & mask) if d else (lambda t: t)
        cand = tuple(sorted((q, (h - d) % N, rot(t), T) for q, h, t, T in S))
        if best is None or cand < best:
            best = cand
    return best


def project(res: RunResult, proj: str, single: bool = False, N: int | None = None):
    """Outcome of a run under a projection. None if unresolved. `local_ti` needs the tape length N."""
    if res.kind == "unresolved":
        return None
    if proj == "class":
        return res.kind
    cyc = res.cycle
    ti = proj == "local_ti"
    if ti:
        if N is None:
            raise ValueError("local_ti needs N")
        proj = "local"
    if proj == "local_y":
        proj = "local"
    elif single:
        cyc = [c[:3] + (_strip(c[3]),) for c in cyc]
    else:
        cyc = [c[:3] + (_strip(c[3]),) + c[4:7] + (_strip(c[7]), c[8]) for c in cyc]
    if single:                                   # C4 configs are (s, h, tape, T)
        if proj == "tables":
            return (res.kind, frozenset(c[3] for c in cyc))
        if ti:
            return (res.kind, translation_canon(set(cyc), N))
        return (res.kind, frozenset(cyc))
    if proj == "joint":
        return (res.kind, frozenset(c[:8] for c in cyc))
    if proj == "local":
        a, b = {c[0:4] for c in cyc}, {c[4:8] for c in cyc}
        if ti:
            return (res.kind, translation_canon(a, N), translation_canon(b, N))
        return (res.kind, frozenset(a), frozenset(b))
    if proj == "tables":
        return (res.kind, frozenset((c[3], c[7]) for c in cyc))
    raise ValueError(proj)


def digest(outcome) -> str | None:
    if outcome is None:
        return None

    def canon(x):
        if isinstance(x, frozenset):
            return sorted(canon(y) for y in x)
        if isinstance(x, tuple):
            return tuple(canon(y) for y in x)
        return x
    return hashlib.blake2b(repr(canon(outcome)).encode(), digest_size=8).hexdigest()


def instance_id(inst: Instance) -> str:
    return hashlib.blake2b(repr(inst.key()).encode(), digest_size=6).hexdigest()


def run_condition(inst: Instance, cond: str, N: int, budget: int, keep_trace=False,
                  hold_cap: int | None = None):
    """Returns list of (sched_name, RunResult)."""
    rewrite, family = CONDITIONS[cond]
    out = []
    for name, sched in schedules_for(family, hold_cap):
        if family == "self":
            T = inst.A if name == "selfA" else inst.B
            out.append((name, run_single(T, inst.R, inst.n, N, budget, keep_trace)))
        else:
            out.append((name, run(inst, rewrite, sched, N, budget, keep_trace)))
    return out


def evaluate(inst: Instance, N: int = 8, budget: int = 200_000, hold_cap: int | None = None):
    """Returns (run_rows, condition_rows) for one instance."""
    iid = instance_id(inst)
    base = {"inst_id": iid, "n": inst.n, "N": N, "k": inst.k, "critical_pair": has_critical_pair(inst.R)}
    results = {c: run_condition(inst, c, N, budget, hold_cap=hold_cap) for c in CONDITIONS}
    outcomes = {}   # (cond, sched, proj) -> outcome
    run_rows = []
    for cond, rs in results.items():
        single = cond == "C4_self"
        for name, res in rs:
            row = dict(base, condition=cond, sched=name, kind=res.kind, transient=res.transient,
                       period=res.period, steps=res.steps, eff_edits=res.eff_edits,
                       eff_yield_edits=res.eff_yield_edits, forced_passes=res.forced_passes)
            tabs = {_strip(c[3]) for c in res.cycle} if single else {(_strip(c[3]), _strip(c[7])) for c in res.cycle}
            row["n_tables_in_cycle"] = len(tabs) if res.cycle else None
            row["tables_settled"] = (len(tabs) == 1) if res.cycle else None
            # a live machine whose (state, head, tape) never changes over the cycle never moves
            row["starved"] = (not single and res.kind == "cycle" and any(
                len({c[o:o + 3] for c in res.cycle}) == 1 and res.cycle[0][o] != inst.n for o in (0, 4)))
            for p in PROJECTIONS:
                o = project(res, p, single, N)
                outcomes[(cond, name, p)] = o
                row[f"d_{p}"] = digest(o)
            run_rows.append(row)

    cond_rows = []
    for cond, rs in results.items():
        names = [nm for nm, _ in rs]
        kinds = [r.kind for _, r in rs]
        periods = [r.period for _, r in rs if r.kind == "cycle"]
        row = dict(base, condition=cond, n_runs=len(rs), n_unresolved=kinds.count("unresolved"),
                   n_halt=kinds.count("halt"), n_cycle=kinds.count("cycle"),
                   median_period=statistics.median(periods) if periods else None,
                   max_period=max(periods) if periods else None,
                   max_transient=max(r.transient for _, r in rs),
                   frac_tables_settled=(sum(1 for _, r in rs if r.cycle and len(
                       {_strip(c[3]) for c in r.cycle} if cond == "C4_self" else {(_strip(c[3]), _strip(c[7])) for c in r.cycle}) == 1)
                       / len(rs)),
                   eff_edits=sum(r.eff_edits for _, r in rs),
                   eff_yield_edits=sum(r.eff_yield_edits for _, r in rs))
        resolved = row["n_unresolved"] == 0
        for p in PROJECTIONS:
            os_ = [outcomes[(cond, nm, p)] for nm in names]
            if cond == "C4_self":       # two different machines: confluence undefined
                row[f"n_distinct_{p}"] = None
                row[f"confluent_{p}"] = None
            else:
                row[f"n_distinct_{p}"] = len(set(os_)) if resolved else None
                row[f"confluent_{p}"] = (len(set(os_)) == 1) if resolved else None
        # endogenous rows: compare against the matching exogenous / masked condition
        ref = {"C1_mutual_endo": ("C2_mutual_exo", "C1m_mutual_endo_maskyield"),
               "C1m_mutual_endo_maskyield": ("C2_mutual_exo", None),
               "C3e_fixed_endo": ("C3_fixed_exo", None)}.get(cond)
        if ref:
            exo_cond, mask_cond = ref
            exo_names = [nm for nm, _ in results[exo_cond]]
            exo_ok = all(r.kind != "unresolved" for _, r in results[exo_cond])
            for p in PROJECTIONS:
                exo_set = {outcomes[(exo_cond, nm, p)] for nm in exo_names}
                if resolved and exo_ok:
                    row[f"n_endo_matching_exo_{p}"] = sum(outcomes[(cond, nm, p)] in exo_set for nm in names)
                else:
                    row[f"n_endo_matching_exo_{p}"] = None
                if mask_cond:
                    mres = dict(results[mask_cond])
                    ok = resolved and all(r.kind != "unresolved" for r in mres.values())
                    row[f"n_endo_differs_from_mask_{p}"] = (
                        sum(outcomes[(cond, nm, p)] != outcomes[(mask_cond, nm, p)] for nm in names)
                        if ok else None)
        cond_rows.append(row)
    return run_rows, cond_rows
