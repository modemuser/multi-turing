"""Independent, object-oriented implementation of the *self-rewriting* view.

Here no machine ever touches another machine's table. Each machine emits an observation
(pre-transition state, symbol written) on a channel after every transition; the other
machine observes it and applies R to ITS OWN table.

Observability assumption (see DESIGN.md): each observation is delivered losslessly, in
order, and synchronously - before any further transition by either machine. Nothing else
about the emitter (table, tape, head, post-state) is visible to the observer.

Used only to cross-check mt.engine (tests/test_equivalence.py); deliberately written
without sharing code with it.
"""
from __future__ import annotations

from .model import Instance


class Machine:
    def __init__(self, table, n, N):
        self.n, self.N = n, N
        self.state, self.head = 0, 0
        self.cells = [0] * N
        self.table = list(table)

    @property
    def halted(self):
        return self.state == self.n

    def transition(self):
        """Perform own transition. Returns (observation, yield_bit)."""
        read = self.cells[self.head]
        base = 4 * (2 * self.state + read)
        write, move, nxt, yld = self.table[base:base + 4]
        self.cells[self.head] = write
        self.head = (self.head + (1 if move else -1)) % self.N
        obs = (self.state, write)
        self.state = nxt
        return obs, yld

    def observe(self, obs, R, mask_yield):
        """Self-rewrite in response to the other machine's observable output."""
        q, w = obs
        edit = R[2 * q + w]
        if edit is None:
            return
        entry, fld, val = edit
        if mask_yield and fld == 3:
            return
        self.table[4 * entry + fld] = val

    def snapshot(self):
        tape = sum(b << i for i, b in enumerate(self.cells))
        return (self.state, self.head, tape, tuple(self.table))


def trajectory(inst: Instance, rewrite: str, sched, N: int, steps: int) -> list:
    """First `steps`+1 configs, in mt.engine's tuple format, computed via observation."""
    mach = [Machine(inst.A, inst.n, N), Machine(inst.B, inst.n, N)]
    ctrl = sched[1] if sched[0] == "endo" else 0
    cap = sched[2] if sched[0] == "endo" and len(sched) > 2 else None
    turn, held = ctrl, 0
    out = []
    for _ in range(steps + 1):
        if sched[0] == "endo":
            ctrl = turn + 2 * held
        out.append(mach[0].snapshot() + mach[1].snapshot() + (ctrl,))
        if mach[0].halted and mach[1].halted:
            break
        if sched[0] == "exo":
            X = "AB".index(sched[1][ctrl])
            ctrl = (ctrl + 1) % len(sched[1])
            if mach[X].halted:
                continue
        else:
            if mach[turn].halted:
                turn, held = 1 - turn, 0
            X = turn
        obs, yld = mach[X].transition()
        if rewrite != "off":
            mach[1 - X].observe(obs, inst.R, rewrite == "mask_yield")   # the channel
        if sched[0] == "endo":
            wants_to_keep = yld == 0 and not mach[X].halted
            if wants_to_keep and (cap is None or held + 1 < cap):
                held = held + 1 if cap is not None else 0
            else:
                turn, held = 1 - X, 0
    return out
