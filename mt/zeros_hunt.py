"""Exception hunt for the unproven zeros (fresh instances, n = 2 and 3).

Learners: set (overwrite revisions as sampled) and pregrown (append rule set with all copies made
before the run, so only revisions act during it). Per instance, agent and schedule (complete graph,
24 schedules), closed and open loop:
  synth    the program after the actual history differs from both serialisations (as mt.mix_probe)
  tabset   the set of (relabelling-canonical) tables the agent holds during the cycle
An instance is exposure-order dependent if, in the open loop, some agent's tabset varies across
schedules. Every instance also gets its number of CONTESTED FIELDS: (entry, field) targets that
receive conflicting overwrites in R.

    uv run python -m mt.zeros_hunt results/zeros 4000 2000
"""
from __future__ import annotations

import hashlib
import multiprocessing as mp
import sys
import time
from pathlib import Path

import pandas as pd

from .closed_serial import canon_rules
from .relabel import canon_table
from .report import md
from .robust_probe import sample
from .swarm import APPEND, APPEND_ONCE, M, edit_op, exo_schedules, growth_variant, pregrown_variant, run
from .swarm_sweep import inst_id
from .witness import programs


def contested_fields(R):
    seen = {}
    for x in R:
        if x is None or edit_op(x) in (APPEND, APPEND_ONCE):
            continue
        seen.setdefault((x[0], x[1]), set()).add(x[2])
    return sum(1 for v in seen.values() if len(v) > 1)


def tabset(inst, cycle, j):
    S = set()
    for c in cycle:
        T = tuple(0 if i % 4 == 3 else v for i, v in enumerate(c[4 * j + 3]))
        S.add(canon_table(T, inst.n, c[4 * M + 2][j], inst.capacity))
    return hashlib.blake2b(repr(sorted(S)).encode(), digest_size=8).hexdigest()


def analyse(args):
    iid, inst, label, n = args
    rows = []
    for nm, w in exo_schedules():
        runs = {lp: run(inst, "on" if lp == "closed" else "open", ("exo", w), "complete", 8, budget=200_000,
                        keep_trace=True) for lp in ("closed", "open")}
        if any(r.kind != "cycle" for r in runs.values()):
            rows.append(dict(n=n, learner=label, inst_id=iid, sched=nm, C=-1, unresolved=True))
            continue
        for C in range(M):
            row = dict(n=n, learner=label, inst_id=iid, sched=nm, C=C, unresolved=False,
                       contested=contested_fields(inst.R))
            for lp, r in runs.items():
                full, ab, ba, _ = programs(inst, r.trace, w, C, lp)
                row[f"{lp}_synth"] = canon_rules(full, inst) not in (canon_rules(ab, inst), canon_rules(ba, inst))
                row[f"{lp}_tabset"] = tabset(inst, r.cycle, C)
            rows.append(row)
    return rows


def main(out: Path, n2: int, n3: int):
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for n, total in ((2, n2), (3, n3)):
        for b in sample(n, total, seed=7):
            iid = inst_id(b)
            jobs.append((iid, b, "set", n))
            jobs.append((iid, pregrown_variant(growth_variant(b, iid, cap=n + 2)), "pregrown", n))
    rows, t0 = [], time.time()
    with mp.Pool() as pool:
        for i, rr in enumerate(pool.imap_unordered(analyse, jobs, chunksize=2), 1):
            rows += rr
            if i % 500 == 0 or i == len(jobs):
                pd.DataFrame(rows).to_csv(out / "zeros_runs.csv", index=False)
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "zeros_runs.csv.gz", index=False)  # gzipped: the plain CSV is ~70 MB
    (out / "zeros_runs.csv").unlink()
    ok = df[~df.unresolved]
    tab = []
    for (n, lt), sub in ok.groupby(["n", "learner"]):
        N = sub.inst_id.nunique()
        inst_open_dep = sub.groupby(["inst_id", "C"]).open_tabset.nunique().gt(1).groupby("inst_id").any()
        inst_syn_c = sub.groupby("inst_id").closed_synth.any()
        inst_syn_o = sub.groupby("inst_id").open_synth.any()
        exc = set(inst_open_dep[inst_open_dep].index) | set(inst_syn_c[inst_syn_c].index) | set(inst_syn_o[inst_syn_o].index)
        cont = sub.drop_duplicates("inst_id").set_index("inst_id").contested
        fmt = lambda k: f"{k} of {N}" + (f" (95% upper bound {1 - 0.05 ** (1 / N):.2%})" if k == 0 else f" ({k / N:.2%})")
        tab.append({"states": n, "learner": lt,
                    "open-loop exposure-order dependent": fmt(int(inst_open_dep.sum())),
                    "rule synthesis, closed loop": fmt(int(inst_syn_c.sum())),
                    "rule synthesis, open loop": fmt(int(inst_syn_o.sum())),
                    "exceptions with ≥2 contested fields": f"{sum(cont[e] >= 2 for e in exc)} of {len(exc)}",
                    "instances with ≥2 contested fields": int((cont >= 2).sum())})
    unres = int(df.unresolved.sum())
    text = ("# Exception hunt for the unproven zeros\n\nFresh instances, complete graph, 24 schedules, closed and open "
            f"loop. Unresolved runs (budget 200k steps): {unres}.\n\n" + md(pd.DataFrame(tab)) + "\n")
    (out / "ZEROS.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
