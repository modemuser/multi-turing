"""Reflexive vs merely coupled: same instances, same observation events, same schedules.
  none      F_exo   (no interaction)
  couple    C_exo_g (an observation that would teach writes the observed symbol onto your tape)
  learn     L_exo_g (the observation rewrites your rules)
Order-dependence under `local_ti` (behaviour + table, up to translation), matched on base_id.

    uv run python -m mt.compare_coupling results/swarm_coupling/COMPARE.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .report import md, wilson

PAIRS = {   # rule set -> (coupling probe dir, learning probe dir)
    "set": ("results/swarm_N8_couple_set", "results/swarm_N8_probe"),
    "append": ("results/swarm_N8_couple_append", "results/swarm_N8_append"),
}
GRAPHS = ("decoupled", "ring", "alternating", "complete")


def load(d):
    r = pd.read_parquet(Path(d) / "results.parquet")
    if "base_id" not in r:
        r["base_id"] = r["inst_id"]
    return r


def dep(x: pd.Series):
    s = x.dropna().astype(bool)
    k, n = int((~s).sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.3f}, {hi:.3f}]" if n else "–"


def build():
    L = []
    w = L.append
    w("# Reflexive vs merely coupled (level-1 control)\n")
    w("Exploratory probe, 400 matched instances per rule set. Share of instances whose outcome "
      "(`local_ti`) depends on the schedule (24 exogenous schedules, 95% Wilson CI). **couple**: the same "
      "observation events (those R would react to) write the observed symbol onto the observer's tape, and "
      "rules never change. **learn**: the observation rewrites the observer's rules.\n")
    for rs, (cdir, ldir) in PAIRS.items():
        c, l = load(cdir), load(ldir)
        ids = set(c.base_id) & set(l.base_id)
        c, l = c[c.base_id.isin(ids)], l[l.base_id.isin(ids)]
        rows = []
        for g in GRAPHS:
            rows.append({"graph": g,
                         "none": dep(c[c.condition == "F_exo"]["confluent_local_ti"]),
                         "couple": dep(c[c.condition == f"C_exo_{g}"]["confluent_local_ti"]),
                         "couple once": dep(c[c.condition == f"C1_exo_{g}"]["confluent_local_ti"]),
                         "learn": dep(l[l.condition == f"L_exo_{g}"]["confluent_local_ti"])})
        w(f"## Rule set: {rs} ({len(ids)} instances)\n")
        w(md(pd.DataFrame(rows)))
        cc = c[c.condition == "C_exo_complete"].set_index("base_id")["confluent_local_ti"]
        ll = l[l.condition == "L_exo_complete"].set_index("base_id")["confluent_local_ti"]
        ok = cc.dropna().index.intersection(ll.dropna().index)
        x = pd.crosstab(cc.loc[ok].astype(bool).map({True: "couple: invariant", False: "couple: order-dependent"}),
                        ll.loc[ok].astype(bool).map({True: "learn: invariant", False: "learn: order-dependent"}))
        w("\nComplete graph, same instances:\n")
        w(md(x.reset_index().rename(columns={x.index.name: ""})))
        w("")
    notes = Path(sys.argv[1]).parent / "notes.md"
    if notes.exists():
        w(notes.read_text())
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    print(f"wrote {out}")
