"""Pick the smallest feedback-required new brick from the pipeline's mix run (p_append = 0.5),
annotate it (mt.witness_story) and export it as plain data for verify/verify_witness.py.

"Smallest" = fewest active rules in R, then the shortest closed-loop run.

    uv run python -m mt.pick_witness
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

from .paths import PROBE400
from .swarm import SwarmInstance, exo_schedules, run
from .swarm_sweep import with_edit_kind

P = Path("results/publish")


def main():
    m = pd.read_csv(P / "mix" / "mix_runs.csv", low_memory=False)
    for col in ("closed_brick", "open_brick"):
        m[col] = m[col].astype(str).eq("True")
    cand = m[(m.p_append == 0.5) & m.closed_brick & ~m.open_brick].copy()
    insts = {j["inst_id"]: j for j in map(json.loads, open(PROBE400))}
    words = dict(exo_schedules())
    cand["k"] = cand.n_append + cand.n_revise

    def steps(r):
        inst = with_edit_kind(SwarmInstance.from_json(insts[r.inst_id.partition("#")[0]]), "append", r.inst_id)
        return run(inst, "on", ("exo", words[r.sched]), "complete", 8, budget=200_000).steps
    cand = cand.sort_values("k").head(60)
    cand["steps"] = cand.apply(steps, axis=1)
    w = cand.sort_values(["k", "steps"]).iloc[0]
    print(f"witness: {w.inst_id} schedule {w.sched} learner {int(w.C)} (rules {int(w.k)}, run {int(w.steps)} steps)")
    subprocess.run(["uv", "run", "python", "-m", "mt.witness_story", w.inst_id, w.sched, str(int(w.C)),
                    "--out", str(P / "witness_example")], check=True, stdout=subprocess.DEVNULL)
    g = with_edit_kind(SwarmInstance.from_json(insts[w.inst_id.partition("#")[0]]), "append", w.inst_id)
    data = {"n": g.n, "cap": g.capacity, "tables": [list(t) for t in g.tables],
            "R": [None if x is None else list(x) for x in g.R], "schedule": words[w.sched],
            "learner": int(w.C), "tape_length": 8, "instance_id": w.inst_id, "schedule_name": w.sched,
            "notes": "R entries: [entry, field, value] = SET field (0 write, 1 move, 2 next, 3 route) of own entry; "
                     "[entry, 2, 0, 3] = APPEND (copy the state the entry points to, redirect the entry to the copy)."}
    out = Path("verify") / f"witness_{w.inst_id.replace('#', '_r')}.json"
    out.write_text(json.dumps(data, indent=1))
    print("exported", out)
    subprocess.run(["python3", "verify/verify_witness.py", str(out)], check=True)


if __name__ == "__main__":
    main()
