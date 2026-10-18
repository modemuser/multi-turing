"""Analyse endogenous runs whose `local` outcome no exogenous schedule in the standard set reaches.

For each such (instance, start turn), extract the realized mover sequence of the endogenous run and
ask which exogenous schedules DO reach the same outcome:
  (a) any periodic word of length <= MAXLEN (all words containing both letters, phase 0),
  (b) the endogenous run's own cycle rhythm, used as a periodic schedule (every rotation),
  (c) the realized sequence itself (prefix + repeated cycle rhythm). This one must match by
      determinism and is only a sanity check.
Every test is done twice: on the `local` outcome, and on `local` up to translation. A machine's
dynamics never see absolute position (R reads only (state, written symbol)), so the same cycle
shifted along the ring is arguably the same behaviour.

    uv run python -m mt.unmatched results/nohalt_N8_cap3
"""
from __future__ import annotations

import itertools
import json
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd

from .engine import initial_config, run, step
from .experiment import project
from .model import Instance
from .schedules import exo_schedules

MAXLEN = 8
WORDS = ["".join(w) for L in range(2, MAXLEN + 1) for w in itertools.product("AB", repeat=L)
         if "A" in w and "B" in w]


def min_period(seq: str) -> str:
    for p in range(1, len(seq) + 1):
        if len(seq) % p == 0 and seq[:p] * (len(seq) // p) == seq:
            return seq[:p]
    return seq


def realized(inst: Instance, start: int, cap, N: int):
    res = run(inst, "mutual", ("endo", start, cap), N=N, keep_trace=True)
    movers = "".join("AB"[c[8] & 1] for c in res.trace)   # no halting: mover = turn bit
    prefix, cyc = movers[:res.transient], movers[res.transient:]
    return res, prefix, min_period(cyc)


def replay_local(inst: Instance, prefix: str, rhythm: str, N: int):
    """Run with an arbitrary eventually-periodic mover sequence; return the local outcome."""
    cfg = initial_config(inst, ("exo", "A"))
    for ch in prefix:
        cfg = step(cfg, inst, "mutual", ("exo", ch), N)[0]
    # the state at the start of the rhythm repeats with period len(rhythm) * m for some m
    seen, trace = {}, []
    i = 0
    while True:
        key = (cfg[:8], i % len(rhythm))
        if key in seen:
            cyc = trace[seen[key]:]
            return ("cycle", frozenset(c[0:4] for c in cyc), frozenset(c[4:8] for c in cyc))
        seen[key] = len(trace)
        trace.append(cfg)
        cfg = step(cfg, inst, "mutual", ("exo", rhythm[i % len(rhythm)]), N)[0]
        i += 1


def translation_invariant(local, N: int):
    """Canonicalize each machine's local cycle set under a common cyclic shift of tape + head."""
    def rot(t, d):
        return ((t >> d) | (t << (N - d))) & ((1 << N) - 1) if d else t

    def canon(S):
        return min(tuple(sorted((q, (h - d) % N, rot(t, d), T) for q, h, t, T in S)) for d in range(N))
    kind, a, b = local
    return (kind, canon(a), canon(b))


def strip_local(o):
    """Same yield-stripping as mt.experiment.project for the `local` projection."""
    def s(T):
        return tuple(v for i, v in enumerate(T) if i % 4 != 3)
    kind, a, b = o
    return (kind, frozenset(c[:3] + (s(c[3]),) for c in a), frozenset(c[:3] + (s(c[3]),) for c in b))


def analyse(args):
    inst_id, inst, start, cap, N = args
    res, prefix, rhythm = realized(inst, start, cap, N)
    target = project(res, "local")
    target_ti = translation_invariant(target, N)
    std = {wd for _, wd in exo_schedules()}
    hits, hits_ti, std_ti = [], [], False
    for wd in sorted(set(WORDS) | std, key=lambda x: (len(x), x)):
        o = project(run(inst, "mutual", ("exo", wd), N=N), "local")
        if wd in WORDS and o == target:
            hits.append(wd)
        if translation_invariant(o, N) == target_ti:
            if wd in WORDS:
                hits_ti.append(wd)
            if wd in std:
                std_ti = True
    rot = [rhythm[i:] + rhythm[:i] for i in range(len(rhythm))]
    rot_hit = rot_hit_ti = None
    for r in rot:
        o = project(run(inst, "mutual", ("exo", r), N=N), "local")
        if rot_hit is None and o == target:
            rot_hit = r
        if rot_hit_ti is None and translation_invariant(o, N) == target_ti:
            rot_hit_ti = r
    replay_ok = strip_local(replay_local(inst, prefix, rhythm, N)) == target
    a_moves = rhythm.count("A")
    return {"inst_id": inst_id, "start": "AB"[start], "k": inst.k, "transient": res.transient,
            "period": res.period, "prefix": prefix, "rhythm": rhythm, "rhythm_len": len(rhythm),
            "rhythm_A_share": a_moves / len(rhythm),
            "n_short_words_matching": len(hits), "short_words_matching": " ".join(hits[:8]),
            "own_rhythm_matches": rot_hit is not None, "own_rhythm_rotation": rot_hit,
            "std_set_matches_ti": std_ti,
            "n_short_words_matching_ti": len(hits_ti), "short_words_matching_ti": " ".join(hits_ti[:8]),
            "own_rhythm_matches_ti": rot_hit_ti is not None,
            "replay_matches": replay_ok, "eff_edits": res.eff_edits,
            "tables_in_cycle": len({(c[3], c[7]) for c in res.cycle})}


def main(d: Path):
    meta = json.loads((d / "meta.json").read_text())
    N, cap = meta["N"], meta.get("hold_cap")
    res = pd.read_parquet(d / "results.parquet")
    c1 = res[res.condition == "C1_mutual_endo"]
    col = "n_endo_matching_exo_local_ti" if "n_endo_matching_exo_local_ti" in c1 else "n_endo_matching_exo_local"
    ids = set(c1.inst_id[c1[col] == 0])
    print(f"selecting by {col}: {len(ids)} instances")
    insts = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        if j["inst_id"] in ids:
            insts[j.pop("inst_id")] = Instance.from_json(j)
    jobs = [(i, inst, s, cap, N) for i, inst in insts.items() for s in (0, 1)]
    with mp.Pool() as pool:
        rows = pool.map(analyse, jobs, chunksize=4)
    out = d / "unmatched"
    out.mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out / "runs.parquet")
    df.drop(columns=["prefix"]).to_csv(out / "runs.csv", index=False)
    print(f"{len(df)} endogenous runs over {len(insts)} instances -> {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/nohalt_N8_cap3"))
