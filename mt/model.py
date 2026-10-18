"""Encodings, random generation and canonicalization.

Table: flat tuple of length 2n*4. Entry e = 2q + r holds fields
(write, move, next, yield) at indices 4e .. 4e+3. move: 0=L, 1=R. next == n means HALT.

Rule R: tuple of length 2n indexed by trigger t = 2q + s_written; each element is
None (no-op) or an edit (entry, field, value).
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

W, M, NX, Y = 0, 1, 2, 3
FIELD_NAMES = ("write", "move", "next", "yield")


def field_values(n: int, field: int, halt: bool = True) -> int:
    """With halt=False, HALT is never a `next` value - neither in tables nor in R's edits - so no
    machine can ever reach it."""
    return (n + 1 if halt else n) if field == NX else 2


def all_edits(n: int, halt: bool = True) -> list[tuple[int, int, int]]:
    return [(e, f, v) for e in range(2 * n) for f in range(4) for v in range(field_values(n, f, halt))]


@dataclass(frozen=True)
class Instance:
    n: int
    A: tuple
    B: tuple
    R: tuple

    @property
    def k(self) -> int:
        return sum(1 for x in self.R if x is not None)

    def key(self) -> tuple:
        return (self.n, self.A, self.B, tuple((-1, -1, -1) if x is None else x for x in self.R))

    def to_json(self) -> dict:
        return {"n": self.n, "A": list(self.A), "B": list(self.B),
                "R": [None if x is None else list(x) for x in self.R]}

    @staticmethod
    def from_json(d: dict) -> "Instance":
        return Instance(d["n"], tuple(d["A"]), tuple(d["B"]),
                        tuple(None if x is None else tuple(x) for x in d["R"]))


def has_critical_pair(R: tuple) -> bool:
    """True if two triggers set the same (entry, field) to different values."""
    seen = {}
    for x in R:
        if x is None:
            continue
        e, f, v = x
        if (e, f) in seen and seen[(e, f)] != v:
            return True
        seen[(e, f)] = v
    return False


def random_table(n: int, rng: random.Random, halt: bool = True) -> tuple:
    out = []
    for _ in range(2 * n):
        out += [rng.randrange(2), rng.randrange(2), rng.randrange(n + 1 if halt else n), rng.randrange(2)]
    return tuple(out)


def random_rule(n: int, k: int, rng: random.Random, halt: bool = True) -> tuple:
    edits = all_edits(n, halt)
    active = set(rng.sample(range(2 * n), k))
    return tuple(rng.choice(edits) if t in active else None for t in range(2 * n))


def random_instance(n: int, k: int, rng: random.Random, halt: bool = True) -> Instance:
    return Instance(n, random_table(n, rng, halt), random_table(n, rng, halt), random_rule(n, k, rng, halt))


# ---------------------------------------------------------------- symmetries
# Each symmetry maps an Instance to an Instance whose runs are the image of the
# original runs (see tests/test_canon.py for the equivariance checks).

def mirror_table(T: tuple) -> tuple:
    T = list(T)
    for i in range(M, len(T), 4):
        T[i] ^= 1
    return tuple(T)


def mirror(inst: Instance) -> Instance:
    R = tuple(None if x is None else (x[0], x[1], x[2] ^ 1 if x[1] == M else x[2]) for x in inst.R)
    return Instance(inst.n, mirror_table(inst.A), mirror_table(inst.B), R)


def swap(inst: Instance) -> Instance:
    return Instance(inst.n, inst.B, inst.A, inst.R)


def relabel_table(T: tuple, perm: tuple, n: int) -> tuple:
    """perm maps old state -> new state (perm[0] == 0, HALT fixed)."""
    out = [0] * len(T)
    for q in range(n):
        for r in range(2):
            src, dst = 4 * (2 * q + r), 4 * (2 * perm[q] + r)
            w, m, nx, y = T[src:src + 4]
            out[dst:dst + 4] = [w, m, nx if nx == n else perm[nx], y]
    return tuple(out)


def relabel(inst: Instance, perm: tuple) -> Instance:
    n = inst.n
    R = [None] * (2 * n)
    for q in range(n):
        for s in range(2):
            x = inst.R[2 * q + s]
            if x is not None:
                e, f, v = x
                q_e, r_e = divmod(e, 2)
                v2 = (v if v == n else perm[v]) if f == NX else v
                x = (2 * perm[q_e] + r_e, f, v2)
            R[2 * perm[q] + s] = x
    return Instance(n, relabel_table(inst.A, perm, n), relabel_table(inst.B, perm, n), tuple(R))


def state_perms(n: int) -> list[tuple]:
    return [(0,) + p for p in itertools.permutations(range(1, n))]


def orbit(inst: Instance) -> list[Instance]:
    out = []
    for perm in state_perms(inst.n):
        a = relabel(inst, perm)
        for b in (a, mirror(a)):
            out += [b, swap(b)]
    return out


def canonical(inst: Instance) -> Instance:
    return min(orbit(inst), key=Instance.key)
