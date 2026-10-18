"""Regenerate every probe the post cites, with the current code, into results/publish/.

Resumable: each stage writes results/publish/<stage>/.done when it finishes and is skipped next time.
Each stage's wall time is logged to results/publish/pipeline_log.tsv.

    uv run python -m mt.pipeline            # run all stages not yet done
    uv run python -m mt.pipeline set mix    # run (or re-run) only these stages
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

P = Path("results/publish")
PROBE = P / "probe400.jsonl"
EXO_C = "^(L_exo_complete|Lo_exo_complete|Lo_exo_ring)$"


def sweep(out, *extra):
    return ["uv", "run", "python", "-m", "mt.swarm_sweep", "--out", str(P / out), *extra]


STAGES = [
    # stage, command (or callable), description
    ("set", sweep("set", "--per-k", "200", "--only", "^(L_exo_|Lo_exo_|F_exo$|C1_exo_)"),
     "800-instance overwrite probe: all graphs, open/closed loop, no learning, volume-matched coupling"),
    ("subset", "subset", "derive the 400-instance subset (first 100 per rule size)"),
    ("threshold", sweep("threshold", "--instances", str(PROBE), "--edit-kind", "threshold", "--only", EXO_C),
     "threshold learners"),
    ("toggle", sweep("toggle", "--instances", str(PROBE), "--edit-kind", "toggle", "--only", EXO_C),
     "toggle learners"),
    ("append", sweep("append", "--instances", str(PROBE), "--edit-kind", "append", "--only", EXO_C),
     "constructive learners (append + overwrite)"),
    ("append_once", sweep("append_once", "--instances", str(PROBE), "--edit-kind", "append_once",
                          "--only", "^Lo_exo_complete$"), "append-once (L6 test)"),
    ("pregrown", sweep("pregrown", "--instances", str(PROBE), "--edit-kind", "append_pregrown",
                       "--only", "^Lo_exo_complete$"), "pre-grown control"),
    ("synthesis", "synthesis", "open-loop synthesis + L6 cycle test on append and append_once"),
    ("closed_serial", ["uv", "run", "python", "-m", "mt.closed_serial", str(P / "closed_serial" / "SERIAL.md")],
     "closed-loop program-level non-serialisability: learning vs coupling"),
    ("closed_loop", ["uv", "run", "python", "-m", "mt.closed_loop", str(P / "closed_loop" / "SUMMARY.md"),
                     str(P / "set"), str(P / "append")], "L7: learner dependence vs source stream variation"),
    ("mix", ["uv", "run", "python", "-m", "mt.mix_probe", str(P / "mix"), "0.25", "0.5", "0.75"],
     "designed construction/revision mix (+ §1/§9 headline numbers at 0.5), 4 rule draws per instance"),
    ("bricks", ["uv", "run", "python", "-m", "mt.brick_tapes", str(P / "bricks")],
     "new bricks: 4-tape share and distribution over 256 tapes, 4 rule draws per instance"),
    ("n3", ["uv", "run", "python", "-m", "mt.robust_probe", str(P / "n3"), "3", "400"], "3-state robustness"),
    ("endo", ["uv", "run", "python", "-m", "mt.endo_probe", str(P / "endo"), "0.5"], "endogenous order"),
    ("zeros", "reuse_zeros",
     "exception hunt for the unproven zeros (reuses results/zeros if present, else recomputes)"),
    ("verify", ["python3", "verify/verify_witness.py", "verify/witness_3f993cc102db_r1.json"],
     "independent re-check of the §1 witness"),
    ("figures", ["uv", "run", "python", "-m", "mt.figures", "verify/witness_3f993cc102db_r1.json", "figures"],
     "Figure 1 from the witness data"),
]


def run_stage(name, cmd):
    d = P / name
    d.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MT_PROBE400=str(PROBE), MT_REPS="4" if name in ("mix", "bricks") else "1")
    t0 = time.time()
    with open(d / "stage.log", "w") as log:
        if cmd == "subset":
            from .paths import make_probe400
            n = make_probe400(P / "set" / "instances.jsonl", PROBE)
            log.write(f"{n} instances (current-format ids)\n")
        elif cmd == "reuse_zeros":
            if Path("results/zeros").exists():
                import shutil
                shutil.copytree("results/zeros", d, dirs_exist_ok=True)
                log.write("reused results/zeros (same code and ids; the hunt does not depend on any later change)\n")
            else:  # fresh clone: recompute (~45 min on 10 cores)
                for m, *a in (("mt.zeros_hunt", "4000", "2000"), ("mt.l9_check",)):
                    subprocess.run(["uv", "run", "python", "-m", m, str(d), *a], check=True,
                                   stdout=log, stderr=subprocess.STDOUT, env=env)
        elif cmd == "synthesis":
            for sub in ("append", "append_once"):
                subprocess.run(["uv", "run", "python", "-m", "mt.synthesis", str(P / sub)], check=True,
                               stdout=log, stderr=subprocess.STDOUT, env=env)
        else:
            subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT, env=env)
    dt = time.time() - t0
    (d / ".done").write_text(f"{dt:.0f}s\n")
    with open(P / "pipeline_log.tsv", "a") as f:
        f.write(f"{name}\t{dt:.0f}\t{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    return dt


def main(only):
    P.mkdir(parents=True, exist_ok=True)
    for name, cmd, desc in STAGES:
        if only and name not in only:
            continue
        if not only and (P / name / ".done").exists():
            print(f"[skip] {name}: done", flush=True)
            continue
        print(f"[run ] {name}: {desc}", flush=True)
        dt = run_stage(name, cmd)
        print(f"[done] {name}: {dt / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
