"""Exact repeat detection: hand-computed cases plus an independent Brent cross-check."""
from mt.engine import initial_config, run, run_single, step
from mt.model import Instance

H = 2  # halt state for n=2


def entry(w, m, nx, y=1):
    return (w, m, nx, y)


def table(*entries):
    return tuple(x for e in entries for x in e)


# A: always write 0, move R, stay in state 0 -> head walks the blank ring.
WALKER = table(entry(0, 1, 0), entry(0, 1, 0), entry(0, 1, 0), entry(0, 1, 0))
# B: halts on its first move.
HALTER = table(entry(0, 1, H), entry(0, 1, H), entry(0, 1, H), entry(0, 1, H))
NOOP_R = (None,) * 4


def test_walker_with_halter_ABAB():
    # step0: A moves (h=1); step1: B halts; afterwards B's slots are no-ops, so A moves
    # every other step: configs repeat when (A.head, phase) recurs -> transient 2, period 16.
    res = run(Instance(2, WALKER, HALTER, NOOP_R), "off", ("exo", "AB"), N=8)
    assert (res.kind, res.transient, res.period) == ("cycle", 2, 16)


def test_both_halt():
    res = run(Instance(2, HALTER, HALTER, NOOP_R), "off", ("exo", "AB"), N=8)
    assert (res.kind, res.transient, res.period) == ("halt", 2, 0)


def test_single_filler():
    # write 1, move R, stay: fills the ring in 8 steps, then the head circles a full tape.
    filler = table(entry(1, 1, 0), entry(1, 1, 0), entry(1, 1, 0), entry(1, 1, 0))
    res = run_single(filler, NOOP_R, 2, N=8)
    assert (res.kind, res.transient, res.period) == ("cycle", 8, 8)


def test_endo_never_yield_starves_other():
    # A never yields: B never moves. A walks the ring with period 8 from step 0.
    a = table(*[entry(0, 1, 0, y=0)] * 4)
    res = run(Instance(2, a, WALKER, NOOP_R), "off", ("endo", 0), N=8)
    assert (res.kind, res.transient, res.period) == ("cycle", 0, 8)
    assert {c[5] for c in res.cycle} == {0}          # B's head never moved


def brent(f, x0, cap=10**6):
    power = lam = 1
    tort, hare = x0, f(x0)
    while tort != hare:
        if power == lam:
            tort, power, lam = hare, power * 2, 0
        hare = f(hare)
        lam += 1
        assert lam < cap
    tort = hare = x0
    for _ in range(lam):
        hare = f(hare)
    mu = 0
    while tort != hare:
        tort, hare, mu = f(tort), f(hare), mu + 1
    return mu, lam


def test_matches_brent(instances):
    checked = 0
    for inst in instances[:80]:
        for rewrite in ("mutual", "off"):
            for sched in (("exo", "AB"), ("exo", "AAB"), ("endo", 0)):
                res = run(inst, rewrite, sched, N=8)
                if res.kind != "cycle":
                    continue
                mu, lam = brent(lambda c: step(c, inst, rewrite, sched, 8)[0], initial_config(inst, sched))
                assert (res.transient, res.period) == (mu, lam)
                checked += 1
    assert checked > 50


def test_hold_cap_turns_never_yield_into_fixed_rhythm():
    # A never yields; with cap 3 it moves exactly 3 times, then B (always yields) moves once:
    # the machine part of the trajectory equals the exogenous schedule AAAB.
    a = table(*[entry(0, 1, 0, y=0)] * 4)
    b = table(entry(1, 1, 1), entry(0, 0, 0), entry(1, 0, 0), entry(0, 1, 1))
    inst = Instance(2, a, b, NOOP_R)
    endo = run(inst, "off", ("endo", 0, 3), N=8, keep_trace=True, budget=400)
    exo = run(inst, "off", ("exo", "AAAB"), N=8, keep_trace=True, budget=400)
    m = min(len(endo.trace), len(exo.trace))
    assert [c[:8] for c in endo.trace[:m]] == [c[:8] for c in exo.trace[:m]]
    assert endo.forced_passes > 0


def test_no_cap_matches_legacy_two_tuple_schedule(instances):
    for inst in instances[:40]:
        assert run(inst, "mutual", ("endo", 0), keep_trace=True).trace == \
            run(inst, "mutual", ("endo", 0, None), keep_trace=True).trace
