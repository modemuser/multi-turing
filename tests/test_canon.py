"""Canonicalization: the group action is a genuine symmetry of the dynamics."""
import random

from mt.engine import run
from mt.experiment import evaluate
from mt.model import Instance, canonical, mirror, orbit, random_instance, relabel, swap
from mt.schedules import exo_schedules, swap_word


def test_canonical_is_orbit_invariant(instances):
    for inst in instances:
        c = canonical(inst)
        assert canonical(c) == c
        for g in orbit(inst):
            assert canonical(g) == c


def test_involutions(instances):
    for inst in instances:
        assert mirror(mirror(inst)) == inst
        assert swap(swap(inst)) == inst


def mirror_cfg(c, N):
    def mtape(t):
        return sum(((t >> i) & 1) << ((-i) % N) for i in range(N))
    from mt.model import mirror_table
    sA, hA, tA, TA, sB, hB, tB, TB, ctrl = c
    return (sA, (-hA) % N, mtape(tA), mirror_table(TA), sB, (-hB) % N, mtape(tB), mirror_table(TB), ctrl)


def swap_cfg(c, word=None):
    sA, hA, tA, TA, sB, hB, tB, TB, ctrl = c
    return (sB, hB, tB, TB, sA, hA, tA, TA, ctrl if word else ctrl ^ 1)   # endo: flip turn bit only


def test_mirror_trajectory_is_image(instances):
    for inst in instances:
        for sched in (("exo", "AAB"), ("endo", 0), ("endo", 0, 3)):
            a = run(inst, "mutual", sched, keep_trace=True, budget=500).trace
            b = run(mirror(inst), "mutual", sched, keep_trace=True, budget=500).trace
            assert [mirror_cfg(c, 8) for c in a] == b


def test_swap_trajectory_is_image(instances):
    for inst in instances:
        for _, w in exo_schedules():
            a = run(inst, "mutual", ("exo", w), keep_trace=True, budget=500).trace
            b = run(swap(inst), "mutual", ("exo", swap_word(w)), keep_trace=True, budget=500).trace
            assert [swap_cfg(c, w) for c in a] == b
        for cap in (None, 3):
            a = run(inst, "mutual", ("endo", 0, cap), keep_trace=True, budget=500).trace
            b = run(swap(inst), "mutual", ("endo", 1, cap), keep_trace=True, budget=500).trace
            assert [swap_cfg(c) for c in a] == b


def summary(inst):
    """Symmetry-invariant summary of all conditions."""
    _, cond_rows = evaluate(inst, budget=20_000)
    keep = [k for k in cond_rows[0] if k.startswith(("confluent_", "n_distinct_", "n_endo_", "n_halt",
                                                       "max_period", "max_transient"))]
    return [(r["condition"], tuple(r.get(k) for k in keep)) for r in cond_rows]


def test_condition_summary_invariant_under_group(instances):
    for inst in instances[::8]:
        s = summary(inst)
        for g in orbit(inst):
            assert summary(g) == s


def test_relabel_n3():
    rng = random.Random(7)
    for _ in range(20):
        inst = random_instance(3, 3, rng)
        g = relabel(inst, (0, 2, 1))
        assert relabel(g, (0, 2, 1)) == inst
        for sched in (("exo", "AB"), ("endo", 0)):
            a = run(inst, "mutual", sched, budget=2000)
            b = run(g, "mutual", sched, budget=2000)
            assert (a.kind, a.transient, a.period) == (b.kind, b.transient, b.period)
        assert canonical(g) == canonical(inst)
