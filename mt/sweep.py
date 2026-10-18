"""Sample instances, canonicalize + dedupe, evaluate all conditions in parallel.

    uv run python -m mt.sweep --out results/m1 --per-k 10000 --N 8
    uv run python -m mt.sweep --out results/m2_N16 --N 16 --instances results/m1/instances.jsonl
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import time
from pathlib import Path

import pandas as pd

from .experiment import evaluate, instance_id
from .model import Instance, canonical, random_instance


def sample(n: int, per_k: int, seed: int, halt: bool = False):
    rng = random.Random(seed)
    seen, out = set(), []
    for k in range(1, 2 * n + 1):
        got = tries = 0
        while got < per_k and tries < per_k * 20:
            tries += 1
            c = canonical(random_instance(n, k, rng, halt))
            if c in seen:
                continue
            seen.add(c)
            out.append(c)
            got += 1
    return out


def _work(args):
    inst, N, budget, hold_cap = args
    return evaluate(inst, N, budget, hold_cap)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/m1")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--N", type=int, default=8)
    ap.add_argument("--per-k", type=int, default=10_000)
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--halt", action="store_true",
                    help="allow HALT as a `next` value (off by default: halting short-circuits the dynamics)")
    ap.add_argument("--hold-cap", type=int, default=None,
                    help="endogenous order: force a pass after this many consecutive transitions")
    ap.add_argument("--instances", help="reuse an instances.jsonl (e.g. from another N) instead of sampling")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.instances:
        insts = [Instance.from_json(json.loads(line)) for line in open(a.instances)]
        print(f"{len(insts)} instances loaded from {a.instances}")
    else:
        insts = sample(a.n, a.per_k, a.seed, a.halt)
        print(f"{len(insts)} canonical instances sampled in {time.time() - t0:.1f}s")
    with open(out / "instances.jsonl", "w") as f:
        for i in insts:
            f.write(json.dumps({"inst_id": instance_id(i), **i.to_json()}) + "\n")

    run_rows, cond_rows = [], []
    with mp.Pool() as pool:
        for j, (rr, cr) in enumerate(pool.imap(_work, [(i, a.N, a.budget, a.hold_cap) for i in insts], chunksize=64)):
            run_rows += rr
            cond_rows += cr
            if (j + 1) % 5000 == 0:
                print(f"  {j + 1}/{len(insts)}  {time.time() - t0:.0f}s", flush=True)
    pd.DataFrame(run_rows).to_parquet(out / "runs.parquet")
    pd.DataFrame(cond_rows).to_parquet(out / "results.parquet")
    pd.DataFrame(cond_rows).to_csv(out / "results.csv", index=False)
    meta = {**vars(a), "n_instances": len(insts), "seconds": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"done in {meta['seconds']}s")


if __name__ == "__main__":
    main()
