"""Annotate one new-brick witness step by step.

    uv run python -m mt.witness_story <inst_id> <schedule> <agent C> [--out DIR]

Shows: the three agents and the learning rule; agent C's input history in the closed loop (who
taught what, and what changed in C's program); C's final program vs the two serialised
alternatives; a fresh tape on which the actual program behaves unlike both; and the open-loop
counterpart at the same schedule, which is not a new brick if the witness is feedback-required.
"""
from __future__ import annotations

from .paths import PROBE400

import argparse
import json
from pathlib import Path

from .closed_serial import canon_rules, history, influence, own_step, replay, serialise
from .swarm import M, exo_schedules, run
from .swarm_repro import fmt_rule, fmt_table
from .transplant import behaviour
from .witness import TAPESETS, replay_open

PROBE = PROBE400


def load(iid):
    from .swarm import SwarmInstance
    from .swarm_sweep import with_edit_kind
    base = iid.partition("#")[0]          # "iid#r" = rule draw r of base instance iid (mt.mix_probe)
    for line in open(PROBE):
        j = json.loads(line)
        if j["inst_id"] == base:
            return with_edit_kind(SwarmInstance.from_json(j), "append", iid)
    raise KeyError(iid)


def fmt_ns(T, ns, n):
    return fmt_table(T[:8 * ns], ns)


def story(iid, sched, C):
    inst = load(iid)
    w = dict(exo_schedules())[sched]
    A, B = [j for j in range(M) if j != C]
    name = "ABC"
    out = [f"# New-brick witness: instance {iid}, schedule {sched} ({w}), learner {name[C]}\n"]
    out.append("Entry notation `q,r:WMN<route>` (route k = keep, + = pass to next agent, − = previous). States "
               "≥ 2 are concepts appended during the run.\n")
    out.append("```")
    for j in range(M):
        out.append(f"{name[j]} initial: {fmt_table(inst.tables[j][:8 * inst.n], inst.n)}")
    out.append("R (applied by every observer to its OWN table):")
    out += ["   " + x for x in fmt_rule(inst.R, inst.n)]
    out.append("```\n")

    r = run(inst, "on", ("exo", w), "complete", 8, budget=200_000, keep_trace=True)
    u = history(inst, r.trace, w, C)
    st = (0, 0, 0, inst.tables[C], inst.n, frozenset())
    out.append(f"## {name[C]}'s closed-loop input history (lessons that changed its program)\n")
    out.append("```")
    for i, x in enumerate(u):
        before = st
        st = own_step(st, inst) if x[0] == "o" else influence(st, x[2], inst, "learn")
        if x[0] == "x" and st[3:5] != before[3:5]:
            learned_src = " **[teacher was in a concept it had LEARNED: impossible without feedback]**" \
                if x[2][0] >= inst.n else ""
            out.append(f"step {i:4d}: lesson from {name[x[1]]} (it was in state {x[2][0]}, wrote {x[2][1]}) "
                       f"-> {name[C]} now has {st[4]} states: {fmt_ns(st[3], st[4], inst.n)}{learned_src}")
    out.append("```\n")

    st0 = (0, 0, 0, inst.tables[C], inst.n, frozenset())
    full, ab, ba = (replay(st0, x, inst, "learn") for x in (u, serialise(u, A, B), serialise(u, B, A)))
    out.append("## Final programs\n")
    out.append("```")
    out.append(f"actual (interleaved)     : {fmt_ns(full[3], full[4], inst.n)}")
    out.append(f"all of {name[A]} first, then {name[B]} : {fmt_ns(ab[3], ab[4], inst.n)}")
    out.append(f"all of {name[B]} first, then {name[A]} : {fmt_ns(ba[3], ba[4], inst.n)}")
    out.append("```\n")
    N8, tapes = TAPESETS["all 256 tapes (N=8)"]
    diff = [tp for tp in tapes if behaviour(full[3], tp, N8) != behaviour(ab[3], tp, N8)
            and behaviour(full[3], tp, N8) != behaviour(ba[3], tp, N8)]
    out.append(f"## Transplanted alone onto fresh tapes\n\nThe actual program behaves unlike both serial programs "
               f"on **{len(diff)} of 256** fresh tapes of length 8. Example, tape `{format(diff[0], '08b')[::-1]}` "
               f"(cell 0 first):\n" if diff else "No differing tape found.\n")
    if diff:
        out.append("```")
        for lbl, P in (("actual", full), (f"{name[A]} first", ab), (f"{name[B]} first", ba)):
            beh = behaviour(P[3], diff[0], N8)
            out.append(f"{lbl:9}: cycle of {len(beh)} steps; tapes visited "
                       f"{sorted({format(t, '08b')[::-1] for _, t in beh})[:4]}{' …' if len({t for _, t in beh}) > 4 else ''}")
        out.append("```\n")

    ro = run(inst, "open", ("exo", w), "complete", 8, budget=200_000, keep_trace=True)
    uo = history(inst, ro.trace, w, C)
    fo, abo, bao = (replay_open(st0, x, inst, inst.tables[C]) for x in (uo, serialise(uo, A, B), serialise(uo, B, A)))
    same = canon_rules(fo, inst) in (canon_rules(abo, inst), canon_rules(bao, inst))
    ob = sum(1 for tp in tapes if behaviour(fo[3], tp, N8) != behaviour(abo[3], tp, N8)
             and behaviour(fo[3], tp, N8) != behaviour(bao[3], tp, N8))
    out.append("## Open-loop counterpart (same schedule; agents learn but act on their original programs)\n")
    out.append(f"Rule level: the open-loop program {'equals' if same else 'differs from'} both serial alternatives' "
               f"{'one' if same else 'rules'}. **Behaviour level: it behaves unlike both serial programs on {ob} of 256 "
               f"fresh tapes**, so it is {'not ' if ob == 0 else ''}a new brick without feedback. "
               "(Teachers acting on their original programs can never send lessons from learned concepts.)\n")
    out.append("```")
    out.append(f"open-loop actual : {fmt_ns(fo[3], fo[4], inst.n)}")
    out.append("```\n")
    out.append(f"Repro: `uv run python -m mt.witness_story {iid} {sched} {C}`\n")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inst_id")
    ap.add_argument("sched")
    ap.add_argument("C", type=int)
    ap.add_argument("--out", default="results/swarm_closed/witness_example")
    a = ap.parse_args(argv)
    text = story(a.inst_id, a.sched, a.C)
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    (d / "README.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
