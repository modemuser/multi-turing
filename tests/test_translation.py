"""Translation-invariant `local_ti` projection."""
import random

from mt.engine import run
from mt.experiment import evaluate, project, translation_canon


def shift(S, d, N):
    rot = lambda t: ((t << d) | (t >> (N - d))) & ((1 << N) - 1) if d else t
    return {(q, (h + d) % N, rot(t), T) for q, h, t, T in S}


def test_canon_is_shift_invariant():
    rng = random.Random(3)
    for N in (8, 16):
        for _ in range(200):
            S = {(rng.randrange(2), rng.randrange(N), rng.randrange(1 << N), (rng.randrange(3),))
                 for _ in range(rng.randrange(1, 6))}
            c = translation_canon(S, N)
            for d in range(N):
                assert translation_canon(shift(S, d, N), N) == c


def test_canon_separates_unshifted_differences():
    N = 8
    a = {(0, 0, 0b1, ()), (1, 1, 0b1, ())}          # head on the 1, then right of it
    b = {(0, 0, 0b1, ()), (1, 7, 0b1, ())}          # head on the 1, then left of it
    assert translation_canon(a, N) != translation_canon(b, N)


def test_local_ti_is_coarser_than_local(instances):
    for inst in instances[:60]:
        outs = [run(inst, "mutual", ("exo", w), N=8) for w in ("AB", "AAB", "ABB", "BA")]
        for x in outs:
            for y in outs:
                if project(x, "local") == project(y, "local"):
                    assert project(x, "local_ti", N=8) == project(y, "local_ti", N=8)


def test_c3_local_ti_confluent(instances):
    for inst in instances[:40]:
        rows = {r["condition"]: r for r in evaluate(inst, budget=50_000)[1]}
        assert rows["C3_fixed_exo"]["confluent_local_ti"] is True
