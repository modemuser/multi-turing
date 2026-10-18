"""Re-run one swarm instance under all conditions; print per-schedule outcome digests.

    uv run python -m mt.swarm_repro <instance.json> [--N 8] [--only L_exo_complete,L_endo_complete]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .swarm import SwarmInstance, project, run
from .swarm_sweep import conditions, digest, scheds


def fmt_table(T, n):
    out = []
    for e in range(2 * n):
        w, m, nx, r = T[4 * e:4 * e + 4]
        out.append(f"{e // 2},{e % 2}:{w}{'LR'[m]}{nx}{'k+-'[r]}")
    return " ".join(out)


def fmt_rule(R, n):
    names = ("write", "move", "next", "route")
    out = []
    for t, x in enumerate(R):
        if x is not None:
            e, f, v = x[:3]
            op = x[3] if len(x) > 3 else 0
            head = f"on observing ({t // 2}, wrote {t % 2}) -> "
            if op == 1:
                out.append(head + f"toggle own entry {e // 2},{e % 2}.{names[f]}")
                continue
            if op in (3, 4):
                once = " (at most once)" if op == 4 else ""
                out.append(head + f"APPEND{once}: copy the state own entry {e // 2},{e % 2} points to into a new "
                                  f"state, redirect the entry to the copy")
                continue
            if op == 2:
                val = "LR"[v] if f == 1 else ("k+-"[v] if f == 3 else v)
                out.append(head + f"after 3 observations, set own entry {e // 2},{e % 2}.{names[f]}={val} (once)")
                continue
            val = "LR"[v] if f == 1 else ("k+-"[v] if f == 3 else v)
            out.append(f"on observing ({t // 2}, wrote {t % 2}) -> set own entry {e // 2},{e % 2}.{names[f]}={val}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--N", type=int, default=8)
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    d = json.loads(Path(a.instance).read_text())
    d.pop("inst_id", None)
    inst = SwarmInstance.from_json(d)
    print("entries q,r:WMN<route>  route k=keep, +=pass to next agent, -=pass to previous agent")
    for nm, T in zip("ABC", inst.tables):
        print(f"{nm}:", fmt_table(T, inst.n))
    print("R (applied by every observer to its own table):", *fmt_rule(inst.R, inst.n), sep="\n   ")
    conds = conditions()
    for c in (a.only.split(",") if a.only else conds):
        learn, fam, g = conds[c]
        print(f"\n{c}")
        for nm, s in scheds(fam):
            r = run(inst, learn, s, g, a.N)
            print(f"  {nm:7} {r.kind:10} trans {r.transient:5d} period {r.period:6d}  "
                  f"local_ti {digest(project(r, 'local_ti', a.N)) or '-'}")


if __name__ == "__main__":
    main()
