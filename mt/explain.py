"""Step-by-step narrative of an endogenous run: mover, transition fired, edit applied, turn decision.

    uv run python -m mt.explain <instances.jsonl> <inst_id> [--start A|B] [--hold-cap 3] [--N 8] [--exo WORD]
"""
from __future__ import annotations

import argparse
import json

from .engine import initial_config, run, step
from .model import FIELD_NAMES, Instance
from .repro import fmt_rule, fmt_table, fmt_tape


def load(path, iid):
    for line in open(path):
        j = json.loads(line)
        if j["inst_id"] == iid:
            return Instance.from_json(j)
    raise KeyError(iid)


def narrate(inst, sched, N, steps=None):
    res = run(inst, "mutual", sched, N=N, keep_trace=True)
    n, R = inst.n, inst.R
    lines = [f"{sched}: transient {res.transient}, period {res.period}"]
    total = steps or (res.transient + res.period)
    cfg = initial_config(inst, sched)
    for i in range(total):
        X = (cfg[8] & 1) if sched[0] == "endo" else "AB".index(sched[1][cfg[8]])
        o = 4 * X
        s, h, t, T = cfg[o:o + 4]
        r = (t >> h) & 1
        w, m, nx, y = T[4 * (2 * s + r):4 * (2 * s + r) + 4]
        edit = R[2 * s + w]
        other = cfg[4 - o + 3]
        etxt = ""
        if edit is not None:
            e, f, v = edit
            old = other[4 * e + f]
            val = ("LR"[v] if f == 1 else v)
            etxt = (f"-> {'AB'[1 - X]}[{e // 2},{e % 2}].{FIELD_NAMES[f]}={val}"
                    + ("" if old != v else " (no change)"))
        nxt, _, _, forced = step(cfg, inst, "mutual", sched, N)
        tag = "*" if i == res.transient else " "
        lines.append(f"{tag}{i:3d} {'AB'[X]} q{s} r{r}: w{w}{'LR'[m]}->q{nx} y{y}{' FORCED-PASS' if forced else ''} {etxt}"
                     f"   | A {fmt_tape(cfg[2], cfg[1], N)} q{cfg[0]}  B {fmt_tape(cfg[6], cfg[5], N)} q{cfg[4]}")
        cfg = nxt
    lines.append("(* = first step of the cycle)")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("instances")
    ap.add_argument("inst_id")
    ap.add_argument("--start", default="A")
    ap.add_argument("--hold-cap", type=int, default=None)
    ap.add_argument("--N", type=int, default=8)
    ap.add_argument("--exo", help="narrate this exogenous word instead of the endogenous run")
    ap.add_argument("--steps", type=int)
    a = ap.parse_args(argv)
    inst = load(a.instances, a.inst_id)
    print("A:", fmt_table(inst.A, inst.n))
    print("B:", fmt_table(inst.B, inst.n))
    print("R:", *fmt_rule(inst.R, inst.n), sep="\n   ")
    sched = ("exo", a.exo) if a.exo else ("endo", "AB".index(a.start), a.hold_cap)
    print(narrate(inst, sched, a.N, a.steps))


if __name__ == "__main__":
    main()
