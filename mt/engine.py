"""Fast functional engine (bounded circular tape).

Config tuple: (sA, hA, tapeA, TA, sB, hB, tapeB, TB, ctrl)
  tapes are N-bit ints; ctrl = schedule phase (exogenous), or turn + 2*held (endogenous: turn 0=A
  1=B, held = transitions the mover has already made in its current turn; always 0 without a cap).

Run modes:
  rewrite = "mutual" | "mask_yield" | "off"
  sched   = ("exo", word) with word a string over {A,B}, or ("endo", start_turn[, hold_cap])
            hold_cap: the mover is forced to pass after this many consecutive transitions
            (None = no cap: it keeps the turn for as long as it fires yield=0 entries).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Instance, Y


@dataclass
class RunResult:
    kind: str                 # "halt" | "cycle" | "unresolved"
    transient: int            # steps before the first config of the cycle (or before halt)
    period: int               # 0 for halt / unresolved
    cycle: list               # configs of the cycle (halt: [final config]); [] if unresolved
    steps: int
    eff_edits: int            # edits that changed a table entry
    eff_yield_edits: int
    forced_passes: int = 0    # endogenous turn changes forced by the hold cap (not by a yield bit)
    trace: list | None = field(default=None, repr=False)


def _apply(T, R, q, w, mask_yield):
    """Return (new_table, changed, changed_yield)."""
    x = R[2 * q + w]
    if x is None:
        return T, False, False
    e, f, v = x
    if mask_yield and f == Y:
        return T, False, False
    i = 4 * e + f
    if T[i] == v:
        return T, False, False
    return T[:i] + (v,) + T[i + 1:], True, f == Y


def initial_config(inst: Instance, sched) -> tuple:
    ctrl = sched[1] if sched[0] == "endo" else 0
    return (0, 0, 0, inst.A, 0, 0, 0, inst.B, ctrl)


def step(cfg, inst: Instance, rewrite: str, sched, N: int):
    """Advance one step. Returns (cfg, eff, eff_yield, forced_pass)."""
    n, R = inst.n, inst.R
    sA, hA, tA, TA, sB, hB, tB, TB, ctrl = cfg
    if sched[0] == "exo":
        word = sched[1]
        X = 0 if word[ctrl] == "A" else 1
        ctrl = (ctrl + 1) % len(word)
        if (sA if X == 0 else sB) == n:      # halted machine's slot is a no-op
            return (sA, hA, tA, TA, sB, hB, tB, TB, ctrl), False, False, False
    else:
        X, held = ctrl & 1, ctrl >> 1
        if (sA if X == 0 else sB) == n:      # pass the turn to the live machine
            X, held = 1 - X, 0
    if X == 0:
        s, h, t, T = sA, hA, tA, TA
    else:
        s, h, t, T = sB, hB, tB, TB
    r = (t >> h) & 1
    b = 4 * (2 * s + r)
    w, m, nx, y = T[b], T[b + 1], T[b + 2], T[b + 3]
    t = (t | (1 << h)) if w else (t & ~(1 << h))
    h = (h + 1) % N if m else (h - 1) % N
    q, s = s, nx
    eff = effy = False
    if rewrite != "off":
        mask = rewrite == "mask_yield"
        if X == 0:
            TB, eff, effy = _apply(TB, R, q, w, mask)
        else:
            TA, eff, effy = _apply(TA, R, q, w, mask)
    forced = False
    if sched[0] == "endo":
        cap = sched[2] if len(sched) > 2 else None
        keep = y == 0 and s != n
        if keep and cap is not None and held + 1 >= cap:
            keep, forced = False, True
        ctrl = (X + 2 * (held + 1) if cap is not None else X) if keep else 1 - X
    if X == 0:
        sA, hA, tA, TA = s, h, t, T
    else:
        sB, hB, tB, TB = s, h, t, T
    return (sA, hA, tA, TA, sB, hB, tB, TB, ctrl), eff, effy, forced


def run(inst: Instance, rewrite: str, sched, N: int = 8, budget: int = 200_000,
        keep_trace: bool = False) -> RunResult:
    n = inst.n
    cfg = initial_config(inst, sched)
    seen: dict = {}
    trace: list = []
    eff_total = effy_total = forced_total = 0
    stepno = 0
    while True:
        if cfg in seen:
            start = seen[cfg]
            return RunResult("cycle", start, stepno - start, trace[start:], stepno,
                             eff_total, effy_total, forced_total, trace if keep_trace else None)
        if cfg[0] == n and cfg[4] == n:
            trace.append(cfg)
            return RunResult("halt", stepno, 0, [cfg], stepno, eff_total, effy_total, forced_total,
                             trace if keep_trace else None)
        if stepno >= budget:
            return RunResult("unresolved", stepno, 0, [], stepno, eff_total, effy_total, forced_total,
                             trace if keep_trace else None)
        seen[cfg] = stepno
        trace.append(cfg)
        cfg, eff, effy, forced = step(cfg, inst, rewrite, sched, N)
        eff_total += eff
        effy_total += effy
        forced_total += forced
        stepno += 1


# ------------------------------------------------------------ single machine (C4)

def run_single(T: tuple, R: tuple, n: int, N: int = 8, budget: int = 200_000,
               keep_trace: bool = False) -> RunResult:
    """One self-modifying machine: R(q, written) edits its own table. Config (s, h, tape, T)."""
    cfg = (0, 0, 0, T)
    seen: dict = {}
    trace: list = []
    eff_total = effy_total = 0
    stepno = 0
    while True:
        if cfg in seen:
            start = seen[cfg]
            return RunResult("cycle", start, stepno - start, trace[start:], stepno,
                             eff_total, effy_total, trace=trace if keep_trace else None)
        if cfg[0] == n:
            trace.append(cfg)
            return RunResult("halt", stepno, 0, [cfg], stepno, eff_total, effy_total,
                             trace=trace if keep_trace else None)
        if stepno >= budget:
            return RunResult("unresolved", stepno, 0, [], stepno, eff_total, effy_total,
                             trace=trace if keep_trace else None)
        seen[cfg] = stepno
        trace.append(cfg)
        s, h, t, T = cfg
        r = (t >> h) & 1
        b = 4 * (2 * s + r)
        w, m, nx = T[b], T[b + 1], T[b + 2]
        t = (t | (1 << h)) if w else (t & ~(1 << h))
        h = (h + 1) % N if m else (h - 1) % N
        T, eff, effy = _apply(T, R, s, w, False)
        cfg = (nx, h, t, T)
        eff_total += eff
        effy_total += effy
        stepno += 1
