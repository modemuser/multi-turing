"""Robustness probe: do the qualitative claims survive larger base machines?

n-state base machines (default n=3), sampled like the 2-state ones (uniform tables, no halting,
rule size k = 1..2n, mirror-canonicalised). Two learner types on the same instances:
  set     overwrite revisions only (R as sampled)                   -> expect no rule synthesis
  append  growth_variant: construction + revision, cap = n + 2      -> expect new bricks, needing
                                                                       revision and mostly feedback
Same analysis as mt.mix_probe (closed vs open loop, complete graph, 24 schedules, new bricks on all
256 fresh tapes, 20k-step cap per transplanted run), progress output, incremental results.

    uv run python -m mt.robust_probe results/swarm_n3 3 400
"""
from __future__ import annotations

import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

import pandas as pd

from .mix_probe import analyse, rate
from .report import md
from .swarm import canonical, growth_variant, random_instance
from .swarm_sweep import inst_id


def sample(n, total, seed=2026):
    rng = random.Random(f"robust-{n}-{seed}")
    out, seen = [], set()
    per_k = total // (2 * n)
    for k in range(1, 2 * n + 1):
        got = 0
        while got < per_k:
            c = canonical(random_instance(n, k, rng))
            if c not in seen:
                seen.add(c)
                out.append(c)
                got += 1
    return out


def main(out: Path, n: int, total: int):
    out.mkdir(parents=True, exist_ok=True)
    base = sample(n, total)
    jobs = []
    for b in base:
        iid = inst_id(b)
        jobs.append((iid, b, "set"))
        jobs.append((iid, growth_variant(b, iid, cap=n + 2, p_append=0.5), "append"))
    rows, t0 = [], time.time()
    with mp.Pool() as pool:
        for i, rr in enumerate(pool.imap_unordered(analyse, jobs, chunksize=1), 1):
            rows += rr
            if i % 50 == 0 or i == len(jobs):
                pd.DataFrame(rows).to_csv(out / "robust_runs.csv", index=False)
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows).rename(columns={"p_append": "learner"})
    df.to_csv(out / "robust_runs.csv", index=False)
    tab = []
    for lt, sub in df.groupby("learner"):
        syn = sub[sub.closed_synth]
        fr = sub.closed_brick & ~sub.open_brick
        norev = sub[sub.n_revise == 0]
        tab.append({"learner": lt, "instances": sub.inst_id.nunique(),
                    "rule synthesis": rate(sub.closed_synth),
                    "P(new brick | synthesis)": rate(syn.closed_brick),
                    "instances with a new brick": rate(sub.groupby("inst_id").closed_brick.any()),
                    "feedback-required share": rate(fr[sub.closed_brick]),
                    "new bricks with NO revision rules": int(norev.closed_brick.sum())})
    text = (f"# Robustness: {n}-state base machines\n\nExploratory probe: {len(base)} instances, complete graph, "
            f"24 schedules, closed vs open loop, new bricks on all 256 fresh tapes (20k-step cap). Append "
            f"learners grow to {n + 2} states.\n\n" + md(pd.DataFrame(tab)) + "\n")
    (out / "ROBUST.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
