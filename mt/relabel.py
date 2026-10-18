"""Canonical form of a table under relabelling of APPENDED states (states >= n0 keep no identity:
two copies created in a different order land in swapped slots but are the same behaviour)."""
from itertools import permutations


def canon_table(T, n0: int, ns: int, cap: int):
    best = None
    extra = list(range(n0, ns))
    for p in permutations(extra):
        perm = {q: q for q in range(n0)} | dict(zip(extra, p))
        out = [0] * len(T)
        for q in range(ns):
            for r in range(2):
                src, dst = 4 * (2 * q + r), 4 * (2 * perm[q] + r)
                w, m, nx, y = T[src:src + 4]
                out[dst:dst + 4] = [w, m, perm.get(nx, nx), y]
        cand = tuple(out)
        if best is None or cand < best:
            best = cand
    return best
