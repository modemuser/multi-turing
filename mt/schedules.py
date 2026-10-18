"""Exogenous schedule set. Closed under A<->B swap, which is what makes A/B swap a valid
canonicalization symmetry. Random words are periodic (repeated) so runs stay autonomous
and exact repeats remain guaranteed on bounded tapes."""
from __future__ import annotations

import random

FIXED = ["AB", "BA", "AAB", "BBA", "ABB", "BAA"]
FIXED_NAMES = {"AB": "ABAB", "BA": "BABA"}
RANDOM_SEEDS = (0, 1, 2, 3)
RANDOM_LEN = 12


def swap_word(w: str) -> str:
    return w.translate(str.maketrans("AB", "BA"))


def random_word(seed: int, length: int = RANDOM_LEN) -> str:
    rng = random.Random(f"sched-{seed}")
    while True:
        w = "".join(rng.choice("AB") for _ in range(length))
        if "A" in w and "B" in w:
            return w


def exo_schedules() -> list[tuple[str, str]]:
    """List of (name, word)."""
    out = [(FIXED_NAMES.get(w, w), w) for w in FIXED]
    for s in RANDOM_SEEDS:
        w = random_word(s)
        out += [(f"rnd{s}", w), (f"rnd{s}~", swap_word(w))]
    return out


def swap_sched_name(name: str) -> str:
    """Name of the schedule that is the A<->B image of `name`."""
    table = {"ABAB": "BABA", "BABA": "ABAB", "AAB": "BBA", "BBA": "AAB", "ABB": "BAA", "BAA": "ABB",
             "endoA": "endoB", "endoB": "endoA"}
    if name in table:
        return table[name]
    return name[:-1] if name.endswith("~") else name + "~"
