"""Pick the smallest interesting instances and write them out with full traces + repro command.

    uv run python -m mt.witnesses results/m1

"Smallest" = lowest rule size k, then the fewest total steps over the relevant runs.
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

from . import repro


def kinds(h: str):
    return {
        "nonconfluent": ("C2_mutual_exo", f"C2: exogenous schedules disagree ({h})",
                         lambda r: r[f"confluent_{h}"] == False, 8),  # noqa: E712
        "yieldmatters": ("C1_mutual_endo", f"C1 ≠ C1m: yield edits changed the outcome ({h})",
                         lambda r: r[f"n_endo_differs_from_mask_{h}"] > 0, 4),
        "endo_unmatched": ("C1_mutual_endo", f"C1: endogenous outcome matches no exogenous outcome ({h}, both starts)",
                           lambda r: r[f"n_endo_matching_exo_{h}"] == 0, 4),
    }


def main(d: Path):
    res = pd.read_parquet(d / "results.parquet")
    runs = pd.read_parquet(d / "runs.parquet")
    insts = {}
    for line in open(d / "instances.jsonl"):
        j = json.loads(line)
        insts[j.pop("inst_id")] = j
    out = d / "witnesses"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    meta = json.loads((d / "meta.json").read_text())
    head = "local_ti" if "confluent_local_ti" in res else "local"
    for tag, (cond, title, pred, count) in kinds(head).items():
        sub = res[res.condition == cond]
        sub = sub[sub.apply(pred, axis=1)]
        steps = runs[runs.condition == cond].groupby("inst_id").steps.sum()
        sub = sub.assign(total_steps=sub.inst_id.map(steps)).sort_values(["k", "total_steps"])
        for i, r in enumerate(sub.head(count).itertuples(), 1):
            wd = out / f"{tag}_{i:02d}_k{r.k}_{r.inst_id}"
            wd.mkdir()
            (wd / "instance.json").write_text(json.dumps(insts[r.inst_id], indent=1))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cap = ["--hold-cap", str(meta["hold_cap"])] if meta.get("hold_cap") else []
                repro.main([str(wd / "instance.json"), "--N", str(meta["N"]), "--traces", str(wd / "traces"), *cap])
            cmd = (f"uv run python -m mt.repro {wd}/instance.json --N {meta['N']} "
                   f"{' '.join(cap)} --traces /tmp/traces").replace("  ", " ")
            (wd / "README.md").write_text(
                f"# {title}: k={r.k}, {r.total_steps} steps over {cond} runs\n\n"
                f"Repro (prints the per-schedule outcome table below; `--traces` dumps every step):\n\n"
                f"```bash\n{cmd}\n```\n\n"
                "Table entry notation: `q,r:WMNy` = in state q reading r, write W, move M, go to N "
                "(H=halt), y=yield / .=keep turn. Outcome columns are digests of the projected "
                "outcome; equal digest = equal outcome.\n\n"
                f"```\n{buf.getvalue()}```\n")
    print(f"wrote {sum(1 for _ in out.iterdir())} witnesses to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results/m1"))
