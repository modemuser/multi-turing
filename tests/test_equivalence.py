"""'A rewrites B' and 'B self-rewrites from A's observable output' give identical trajectories
(under the synchronous, lossless observability assumption documented in DESIGN.md).

The two sides are separate implementations (mt.engine vs mt.observer)."""
import itertools

from mt import observer
from mt.engine import run
from mt.schedules import exo_schedules

SCHEDS = ([("exo", w) for _, w in exo_schedules()] + [("endo", 0), ("endo", 1)]
          + [("endo", t, cap) for t in (0, 1) for cap in (1, 2, 3, 5)])


def test_rewrite_equals_self_rewrite(instances):
    for inst, rewrite, sched in itertools.product(instances, ("mutual", "mask_yield", "off"), SCHEDS):
        res = run(inst, rewrite, sched, N=8, keep_trace=True, budget=400)
        obs = observer.trajectory(inst, rewrite, sched, N=8, steps=len(res.trace) - 1)
        assert res.trace == obs, (inst, rewrite, sched)


def test_delayed_observation_breaks_equivalence(instances):
    """Sanity check that the assumption matters: if B only sees A's outputs one A-step late,
    trajectories diverge for some instances."""
    from mt.observer import Machine

    def delayed(inst, sched, steps):
        mach = [Machine(inst.A, 2, 8), Machine(inst.B, 2, 8)]
        pending = [None, None]
        out, ctrl = [], 0
        for _ in range(steps + 1):
            out.append(mach[0].snapshot() + mach[1].snapshot() + (ctrl,))
            if mach[0].halted and mach[1].halted:
                break
            X = "AB".index(sched[1][ctrl]); ctrl = (ctrl + 1) % len(sched[1])
            if mach[X].halted:
                continue
            obs, _ = mach[X].transition()
            if pending[X] is not None:
                mach[1 - X].observe(pending[X], inst.R, False)
            pending[X] = obs
        return out

    diverged = 0
    for inst in instances:
        res = run(inst, "mutual", ("exo", "AB"), N=8, keep_trace=True, budget=200)
        diverged += res.trace != delayed(inst, ("exo", "AB"), len(res.trace) - 1)
    assert diverged > 0
