"""Re-run one instance under all conditions and print per-schedule outcomes.

    uv run python -m mt.repro results/m1/witnesses/<dir>/instance.json [--traces OUTDIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .experiment import CONDITIONS, PROJECTIONS, digest, project, run_condition
from .model import FIELD_NAMES, Instance


def fmt_table(T, n):
    """Entries as  q,r:write move next yield  e.g. '0,1:1RHy'."""
    out = []
    for e in range(2 * n):
        w, m, nx, y = T[4 * e:4 * e + 4]
        out.append(f"{e // 2},{e % 2}:{w}{'LR'[m]}{'H' if nx == n else nx}{'y' if y else '.'}")
    return " ".join(out)


def fmt_tape(t, h, N):
    return "".join(("[" + str((t >> i) & 1) + "]") if i == h else str((t >> i) & 1) for i in range(N))


def fmt_rule(R, n):
    out = []
    for t, x in enumerate(R):
        if x is not None:
            e, f, v = x
            val = "H" if (f == 2 and v == n) else ("LR"[v] if f == 1 else v)
            out.append(f"on ({t // 2},wrote {t % 2}) -> set entry {e // 2},{e % 2}.{FIELD_NAMES[f]}={val}")
    return out


def readable(cfg, n, N, single=False):
    st = lambda s: "H" if s == n else str(s)
    if single:
        s, h, t, T = cfg
        return {"state": st(s), "tape": fmt_tape(t, h, N), "table": fmt_table(T, n)}
    sA, hA, tA, TA, sB, hB, tB, TB, ctrl = cfg
    return {"A": {"state": st(sA), "tape": fmt_tape(tA, hA, N), "table": fmt_table(TA, n)},
            "B": {"state": st(sB), "tape": fmt_tape(tB, hB, N), "table": fmt_table(TB, n)},
            "ctrl": ctrl}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--N", type=int, default=8)
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--traces", help="write full per-step traces (jsonl) into this directory")
    ap.add_argument("--hold-cap", type=int, default=None)
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    a = ap.parse_args(argv)
    inst = Instance.from_json(json.loads(Path(a.instance).read_text()))
    n = inst.n
    print("A:", fmt_table(inst.A, n))
    print("B:", fmt_table(inst.B, n))
    print("R:", *fmt_rule(inst.R, n), sep="\n   ")
    for cond in a.conditions.split(","):
        single = cond == "C4_self"
        print(f"\n{cond}")
        print(f"  {'sched':8} {'kind':10} {'trans':>6} {'period':>6}  " + "  ".join(f"{p:16}" for p in PROJECTIONS[:4]))
        for name, res in run_condition(inst, cond, a.N, a.budget, keep_trace=bool(a.traces),
                                       hold_cap=a.hold_cap):
            ds = [digest(project(res, p, single, a.N)) or "-" for p in PROJECTIONS[:4]]
            print(f"  {name:8} {res.kind:10} {res.transient:6d} {res.period:6d}  " + "  ".join(f"{d:16}" for d in ds))
            if a.traces:
                d = Path(a.traces)
                d.mkdir(parents=True, exist_ok=True)
                cyc0 = res.transient if res.kind == "cycle" else None
                with open(d / f"{cond}__{name}.jsonl", "w") as f:
                    for i, c in enumerate(res.trace):
                        f.write(json.dumps({"step": i, "in_cycle": cyc0 is not None and i >= cyc0,
                                            **readable(c, n, a.N, single)}) + "\n")


if __name__ == "__main__":
    main()
