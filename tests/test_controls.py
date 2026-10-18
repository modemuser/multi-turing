"""Controls behave as the design says they must."""
from mt.engine import run
from mt.experiment import evaluate
from mt.model import Instance, Y
from mt.schedules import exo_schedules


def by_cond(cond_rows):
    return {r["condition"]: r for r in cond_rows}


def test_fixed_tables_local_outcome_is_schedule_invariant(instances):
    """C3: without rewriting each machine's own trajectory ignores the schedule, so the
    `local` projection must be confluent. `joint` need not be (interleaving artifact)."""
    for inst in instances:
        rows = by_cond(evaluate(inst, budget=50_000)[1])
        c3 = rows["C3_fixed_exo"]
        assert c3["n_unresolved"] == 0
        assert c3["confluent_local"] is True
        assert c3["confluent_tables"] is True


def test_noop_rule_equals_fixed(instances):
    for inst in instances[:40]:
        noop = Instance(inst.n, inst.A, inst.B, (None,) * len(inst.R))
        for _, w in exo_schedules():
            a = run(noop, "mutual", ("exo", w), keep_trace=True)
            b = run(noop, "off", ("exo", w), keep_trace=True)
            assert a.trace == b.trace


def test_mask_yield_equals_mutual_without_yield_edits(instances):
    for inst in instances:
        R = tuple(None if (x is not None and x[1] == Y) else x for x in inst.R)
        i2 = Instance(inst.n, inst.A, inst.B, R)
        for s in (("endo", 0), ("endo", 1)):
            assert run(i2, "mask_yield", s, keep_trace=True).trace == run(i2, "mutual", s, keep_trace=True).trace


def test_mutual_exo_ignores_yield_bits(instances):
    """Yield bits are inert under exogenous schedules: flipping them changes nothing but the
    stored yield fields."""
    flip = lambda T: tuple(v ^ 1 if i % 4 == Y else v for i, v in enumerate(T))
    strip = lambda T: tuple(v for i, v in enumerate(T) if i % 4 != Y)
    nostrip = lambda c: c[:3] + (strip(c[3]),) + c[4:7] + (strip(c[7]), c[8])
    for inst in instances[:40]:
        i2 = Instance(inst.n, flip(inst.A), flip(inst.B), inst.R)
        for _, w in exo_schedules()[:4]:
            a = run(inst, "mutual", ("exo", w), keep_trace=True, budget=500)
            b = run(i2, "mutual", ("exo", w), keep_trace=True, budget=500)
            m = min(len(a.trace), len(b.trace))
            assert [nostrip(c) for c in a.trace[:m]] == [nostrip(c) for c in b.trace[:m]]


def test_no_halt_instances_never_halt():
    import random

    from mt.experiment import evaluate
    from mt.model import random_instance
    rng = random.Random(99)
    for k in (1, 2, 3, 4):
        for _ in range(25):
            inst = random_instance(2, k, rng, halt=False)
            assert all(inst.A[i] != 2 and inst.B[i] != 2 for i in range(2, 16, 4))
            assert all(x is None or not (x[1] == 2 and x[2] == 2) for x in inst.R)
            run_rows, _ = evaluate(inst, budget=50_000)
            assert all(r["kind"] != "halt" for r in run_rows)


def test_hold_cap_prevents_starvation():
    import random

    from mt.experiment import evaluate
    from mt.model import random_instance
    rng = random.Random(5)
    for k in (1, 4):
        for _ in range(30):
            inst = random_instance(2, k, rng, halt=False)
            run_rows, _ = evaluate(inst, budget=50_000, hold_cap=3)
            assert not any(r["starved"] for r in run_rows)
