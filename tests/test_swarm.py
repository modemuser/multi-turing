"""3-agent swarm engine."""
import random

import pytest

from mt import engine
from mt.model import Instance
from mt.swarm import (GRAPHS, M, ROUTE, SwarmInstance, exo_schedules, growth_variant, initial_config, mirror,
                      random_instance, rotate, run, starved, step)
from mt.swarm_sweep import evaluate
from tests.test_repeat import brent

N = 8


@pytest.fixture
def swarms():
    rng = random.Random(777)
    return [random_instance(2, k, rng) for k in (1, 2, 3, 4) for _ in range(15)]


def ab(c):
    return c[0:8]


def test_decoupled_reduces_to_two_agent_model(swarms):
    """C isolated: A and B must follow the 2-agent engine on the schedule with C's slots deleted."""
    for inst in swarms:
        two = Instance(2, inst.tables[0], inst.tables[1], inst.R)
        for _, w in exo_schedules():
            sw = run(inst, "on", ("exo", w), "decoupled", N, budget=600, keep_trace=True).trace
            seq = [ab(sw[0])]
            for c in sw[1:]:
                if ab(c) != seq[-1]:
                    seq.append(ab(c))
            ref = [c[:8] for c in engine.run(two, "mutual", ("exo", w.replace("C", "")), N,
                                             budget=600, keep_trace=True).trace]
            m = min(len(seq), len(ref))
            assert m > 5 and seq[:m] == ref[:m]


def rot_cfg(c, s=1):
    ag = [c[4 * ((j - s) % M):4 * ((j - s) % M) + 4] for j in range(M)]
    ctrl = c[-1]
    if isinstance(ctrl, tuple):
        t, held, waits = ctrl
        ctrl = ((t + s) % M, held, tuple(waits[(j - s) % M] for j in range(M)))
    mids = tuple(tuple(m[(j - s) % M] for j in range(M)) for m in c[4 * M:-1])   # per-agent extras
    return tuple(x for a in ag for x in a) + mids + (ctrl,)


def relabel_word(w, s=1):
    return "".join("ABC"[("ABC".index(ch) + s) % M] for ch in w)


@pytest.mark.parametrize("graph", ["ring", "complete", "alternating"])
def test_rotation_equivariance(swarms, graph):
    for inst in swarms:
        g = rotate(inst)
        for w in ("AABC", "ABAC"):
            a = run(inst, "on", ("exo", w), graph, N, budget=400, keep_trace=True).trace
            b = run(g, "on", ("exo", relabel_word(w)), graph, N, budget=400, keep_trace=True).trace
            assert [rot_cfg(c) for c in a] == b
        for s in range(M):
            a = run(inst, "on", ("endo", s), graph, N, budget=400, keep_trace=True).trace
            b = run(g, "on", ("endo", (s + 1) % M), graph, N, budget=400, keep_trace=True).trace
            assert [rot_cfg(c) for c in a] == b


def test_mirror_equivariance(swarms):
    def mcfg(c):
        from mt.model import mirror_table
        mt = lambda t: sum(((t >> i) & 1) << ((-i) % N) for i in range(N))
        out = []
        for j in range(M):
            s, h, t, T = c[4 * j:4 * j + 4]
            out += [s, (-h) % N, mt(t), mirror_table(T)]
        return tuple(out) + tuple(c[4 * M:])
    for inst in swarms:
        for g in GRAPHS:
            a = run(inst, "on", ("endo", 0), g, N, budget=400, keep_trace=True).trace
            b = run(mirror(inst), "on", ("endo", 0), g, N, budget=400, keep_trace=True).trace
            assert [mcfg(c) for c in a] == b


def test_repeat_detection_matches_brent(swarms):
    n = 0
    for inst in swarms:
        for sched in (("exo", "AABC"), ("endo", 1)):
            res = run(inst, "on", sched, "complete", N)
            if res.kind != "cycle":
                continue
            mu, lam = brent(lambda c: step(c, inst, "on", sched, "complete", N)[0], initial_config(inst, sched))
            assert (res.transient, res.period) == (mu, lam)
            n += 1
    assert n > 50


def test_wait_cap_prevents_lockout(swarms):
    for inst in swarms:
        for g in GRAPHS:
            for s in range(M):
                r = run(inst, "on", ("endo", s), g, N)
                assert not starved(r)


def test_mask_route_equals_on_without_route_edits(swarms):
    for inst in swarms:
        R = tuple(None if (x is not None and x[1] == ROUTE) else x for x in inst.R)
        i2 = SwarmInstance(inst.n, inst.tables, R)
        for g in GRAPHS:
            a = run(i2, "on", ("endo", 0), g, N, keep_trace=True).trace
            b = run(i2, "mask_route", ("endo", 0), g, N, keep_trace=True).trace
            assert a == b


def test_fixed_tables_order_cannot_matter(swarms):
    """No learning + no lockout: each agent's own trajectory ignores the order entirely."""
    for inst in swarms[::3]:
        rows = {r["condition"]: r for r in evaluate(inst, N, budget=100_000)[1]}
        assert rows["F_exo"]["confluent_local_ti"] is True
        assert rows["F_endo"]["confluent_local_ti"] is True
        assert rows["F_endo"]["n_endo_matching_exo_local_ti"] == M


def test_alternating_one_observer_per_event_two_sources_per_agent(swarms):
    from mt.swarm import observers
    for X in range(M):
        seen = {observers("alternating", X, p) for p in (0, 1)}
        assert seen == {((X + 1) % M,), ((X + 2) % M,)}
    # edit attempts per event: alternating == ring (1), complete == 2
    for inst in swarms[:20]:
        for g, per_event in (("ring", 1), ("alternating", 1), ("complete", 2)):
            cfg = initial_config(inst, ("exo", "ABC"))
            attempts = 0
            for _ in range(60):
                X = "ABC".index("ABC"[cfg[-1]])
                attempts += len(observers(g, X, cfg[4 * M][X]))
                cfg = step(cfg, inst, "on", ("exo", "ABC"), g, N)[0]
            assert attempts == 60 * per_event


def test_open_loop_behaviour_equals_no_learning(swarms):
    """Open loop: agents act on their original tables, so (state, head, tape) of every agent
    follows the no-learning trajectory exactly."""
    beh = lambda c: tuple(c[4 * j:4 * j + 3] for j in range(M))
    for inst in swarms:
        for g in GRAPHS:
            for _, w in exo_schedules()[:6]:
                a = run(inst, "open", ("exo", w), g, N, budget=500, keep_trace=True).trace
                b = run(inst, "off", ("exo", w), g, N, budget=500, keep_trace=True).trace
                m = min(len(a), len(b))
                assert [beh(c) for c in a[:m]] == [beh(c) for c in b[:m]]


@pytest.mark.parametrize("graph", ["ring", "decoupled"])
def test_open_loop_single_source_is_order_invariant(swarms, graph):
    """One source + fixed behaviour: an agent's learned tables are a fold of R over one fixed
    stream, so the per-agent learned-table outcome cannot depend on the schedule."""
    from mt.swarm import project
    for inst in swarms:
        outs = {project(run(inst, "open", ("exo", w), graph, N, budget=50_000), "tables_local", N)
                for _, w in exo_schedules()}
        outs.discard(None)                      # unresolved at budget: no outcome to compare
        assert len(outs) <= 1


def test_toggle_semantics():
    from mt.swarm import TOGGLE, _apply, noncommuting_pair
    T = (0, 1, 1, 2) * 4
    R = ((0, 0, 0, TOGGLE), (0, 1, 0, TOGGLE), (0, 2, 0, TOGGLE), (0, 3, 0, TOGGLE))
    assert _apply(T, R, 0, 0, False)[0][:4] == (1, 1, 1, 2)      # write 0 -> 1
    assert _apply(T, R, 0, 1, False)[0][:4] == (0, 0, 1, 2)      # move 1 -> 0
    assert _apply(T, R, 1, 0, False)[0][:4] == (0, 1, 0, 2)      # next 1 -> 0 (n=2)
    assert _apply(T, R, 1, 1, False)[0][:4] == (0, 1, 1, 0)      # route 2 -> 0 (cycles mod 3)
    assert not noncommuting_pair(((0, 1, 0, TOGGLE), (0, 1, 1, TOGGLE), None, None))   # toggles commute
    assert noncommuting_pair(((0, 1, 0, TOGGLE), (0, 1, 1), None, None))              # set vs toggle
    assert noncommuting_pair(((0, 1, 0), (0, 1, 1), None, None))                      # conflicting sets
    assert not noncommuting_pair(((0, 1, 1), (0, 1, 1), None, None))


def _with_ops(inst, op_of):
    return SwarmInstance(inst.n, inst.tables,
                         tuple(None if x is None else tuple(x[:3]) + (op_of(t),) for t, x in enumerate(inst.R)))


def test_mirror_and_rotation_equivariance_with_toggles(swarms):
    from mt.swarm import TOGGLE
    for inst in swarms[:30]:
        ti = _with_ops(inst, lambda t: TOGGLE if t % 2 else 0)
        g = rotate(ti)
        a = run(ti, "on", ("exo", "AABC"), "complete", N, budget=400, keep_trace=True).trace
        b = run(g, "on", ("exo", relabel_word("AABC")), "complete", N, budget=400, keep_trace=True).trace
        assert [rot_cfg(c) for c in a] == b
        assert mirror(mirror(ti)) == ti


def test_threshold_learner_revises_once_after_k_observations():
    from mt.swarm import K_EVIDENCE, THRESHOLD
    # A always fires (q0, wrote 1); B watches A; the rule sets B's entry 1,1.move := L (0) by threshold
    a = (1, 1, 0, 0) * 4                                  # write 1, move R, stay q0, keep turn
    b = (0, 1, 0, 0) * 4
    R = (None, (3, 1, 0, THRESHOLD), None, None)
    inst = SwarmInstance(2, (a, b, b), R)
    tr = run(inst, "on", ("exo", "ABC"), "ring", N, budget=60, keep_trace=True).trace
    moves = [c[4 + 3][4 * 3 + 1] for c in tr]          # B's entry (1,1).move over time
    counts = [c[4 * M + 1][1][1] for c in tr]          # B's evidence counter for trigger (0, wrote 1)
    flip = moves.index(0)
    assert counts[flip] == K_EVIDENCE and all(m == 1 for m in moves[:flip]) and all(m == 0 for m in moves[flip:])
    assert max(counts) == K_EVIDENCE


def test_threshold_learning_always_settles(swarms):
    """Every edit fires at most once per observer, so tables are constant on every cycle."""
    from mt.swarm import THRESHOLD
    for inst in swarms:
        ti = _with_ops(inst, lambda t: THRESHOLD)
        for g in GRAPHS:
            for sched in (("exo", "AABC"), ("endo", 0)):
                r = run(ti, "on", sched, g, N, budget=50_000)
                if r.kind == "cycle":
                    assert len({tuple(c[4 * j + 3] for j in range(M)) for c in r.cycle}) == 1


def test_rotation_equivariance_threshold(swarms):
    from mt.swarm import THRESHOLD
    for inst in swarms[:30]:
        ti = _with_ops(inst, lambda t: THRESHOLD)
        g = rotate(ti)
        for sched_a, sched_b in ((("exo", "ABAC"), ("exo", relabel_word("ABAC"))), (("endo", 2), ("endo", 0))):
            a = run(ti, "on", sched_a, "alternating", N, budget=400, keep_trace=True).trace
            b = run(g, "on", sched_b, "alternating", N, budget=400, keep_trace=True).trace
            assert [rot_cfg(c) for c in a] == b


def test_append_copies_and_redirects():
    from mt.swarm import APPEND, _append
    T = tuple(range(8)) + tuple(range(10, 18)) + (0,) * 16      # 2 real states, room for 2 more
    T = T[:2] + (1,) + T[3:]                                    # entry 0 (q0,r0) points to state 1
    T2, ns, ch = _append(T, 0, 2, 4)
    assert (ns, ch) == (3, 1)
    assert T2[16:24] == T[8:16]                                 # state 2 is a copy of state 1
    assert T2[2] == 2                                           # entry 0 now points to the copy
    assert _append(T2, 0, 4, 4)[1:] == (4, 0)                   # at capacity: no-op
    assert _append(T, 5, 2, 4)[1:] == (2, 0)                    # entry of an absent state: no-op


def test_append_alone_is_behaviour_neutral(swarms):
    """With a rule of only APPENDs, heads and tapes follow the no-growth run exactly
    (a copied state behaves like its original)."""
    from mt.swarm import APPEND
    for inst in swarms[:30]:
        g = growth_variant(inst, "t", cap=4)
        R = tuple(None if x is None else (x[0], 2, 0, APPEND) for x in g.R)
        grow = SwarmInstance(g.n, g.tables, R, 4)
        fixed = SwarmInstance(g.n, g.tables, R, 2)
        ht = lambda c: tuple(c[4 * j + 1:4 * j + 3] for j in range(M))
        for gr in ("complete", "alternating"):
            a = run(grow, "on", ("exo", "AABC"), gr, N, budget=300, keep_trace=True).trace
            b = run(fixed, "on", ("exo", "AABC"), gr, N, budget=300, keep_trace=True).trace
            m = min(len(a), len(b))
            assert [ht(c) for c in a[:m]] == [ht(c) for c in b[:m]]
            assert max(max(c[4 * M + 2]) for c in a) <= 4


def test_growth_pair_shares_rule_and_respects_cap(swarms):
    for inst in swarms[:20]:
        on, off = growth_variant(inst, "s"), growth_variant(inst, "s", appends=False)
        assert on.R == off.R and on.tables == off.tables and (on.capacity, off.capacity) == (4, 2)
        r = run(off, "on", ("exo", "ABC"), "complete", N, budget=2000, keep_trace=True)
        assert all(c[4 * M + 2] == (2, 2, 2) for c in r.trace)
        assert all(c[4 * j] < 2 for c in r.trace for j in range(M))      # never enters an absent state


def test_rotation_equivariance_with_growth(swarms):
    for inst in swarms[:20]:
        g0 = growth_variant(inst, "r")
        g1 = rotate(g0)
        a = run(g0, "on", ("exo", "ABAC"), "alternating", N, budget=400, keep_trace=True).trace
        b = run(g1, "on", ("exo", relabel_word("ABAC")), "alternating", N, budget=400, keep_trace=True).trace
        assert [rot_cfg(c) for c in a] == b


def test_relabel_canon_merges_swapped_copies():
    from mt.relabel import canon_table
    s0, s1 = (1, 0, 2, 0, 0, 1, 3, 0), (0, 1, 1, 0, 1, 1, 0, 0)       # states 0,1 point into 2 and 3
    a, b = (0, 0, 0, 0, 1, 1, 1, 0), (1, 0, 0, 0, 0, 1, 1, 0)
    T = s0 + s1 + a + b
    swap = lambda row: tuple({2: 3, 3: 2}.get(v, v) if i % 4 == 2 else v for i, v in enumerate(row))
    T_sw = swap(s0) + swap(s1) + b + a                                  # same machine, copies in swapped slots
    assert T != T_sw and canon_table(T, 2, 4, 4) == canon_table(T_sw, 2, 4, 4)
    assert canon_table(T, 2, 4, 4) != canon_table(s0 + s1 + a + a, 2, 4, 4)


def test_append_once_makes_at_most_one_copy_per_rule(swarms):
    from mt.swarm import APPEND_ONCE, append_once_variant, edit_op
    for inst in swarms[:30]:
        g = append_once_variant(growth_variant(inst, "o"))
        n_rules = sum(1 for x in g.R if x is not None and edit_op(x) == APPEND_ONCE)
        for gr in ("complete", "alternating"):
            r = run(g, "on", ("exo", "AABC"), gr, N, budget=5000, keep_trace=True)
            assert all(max(c[4 * M + 2]) <= min(4, 2 + n_rules) for c in r.trace)


def test_pregrown_has_copies_from_start_and_never_appends(swarms):
    from mt.swarm import APPEND, edit_op, pregrown_variant
    for inst in swarms[:30]:
        base = growth_variant(inst, "p")
        g = pregrown_variant(base)
        assert not any(x is not None and edit_op(x) == APPEND for x in g.R)
        if any(x is not None and edit_op(x) == APPEND for x in base.R):
            assert sum(g.ns0) >= sum(initial_config(base, ("exo", "ABC"))[4 * M + 2])
        r = run(g, "on", ("exo", "ABAC"), "complete", N, budget=3000, keep_trace=True)
        assert all(c[4 * M + 2] == (g.ns0 or (2, 2, 2)) for c in r.trace)
        # rotation equivariance carries the per-agent initial sizes
        gr = rotate(g)
        a = run(g, "on", ("exo", "ABAC"), "alternating", N, budget=300, keep_trace=True).trace
        b = run(gr, "on", ("exo", relabel_word("ABAC")), "alternating", N, budget=300, keep_trace=True).trace
        assert [rot_cfg(c) for c in a] == b


@pytest.mark.parametrize("op", [0, 2])          # SET, THRESHOLD
def test_L5_commuting_stabilising_learning_is_order_invariant_in_open_loop(swarms, op):
    """PROOFS.md L5: if all learning operations commute and learning stabilises, the per-agent learned
    tables in open loop cannot depend on the schedule, in ANY graph (here: two-source graphs)."""
    from mt.swarm import noncommuting_pair, project
    tested = 0
    for inst in swarms:
        R = tuple(None if x is None else tuple(x[:3]) + (op,) for x in inst.R)
        if noncommuting_pair(R):
            continue                                    # (C) fails: not covered by the lemma
        i2 = SwarmInstance(inst.n, inst.tables, R)
        for g in ("complete", "alternating"):
            outs = {project(run(i2, "open", ("exo", w), g, N, budget=50_000), "tables_local", N)
                    for _, w in exo_schedules()}
            outs.discard(None)
            assert len(outs) <= 1
        tested += 1
    assert tested > 30


def test_synthesis_fold_reproduces_engine_open_loop(swarms):
    """mt.synthesis.learn/event_stream must give exactly the engine's learned tables when fed the
    merge that the engine actually delivered (open loop, complete graph)."""
    from mt.synthesis import event_stream, learn
    for inst in swarms[:25]:
        g = growth_variant(inst, "syn")
        for w in ("ABC", "AABC", "ABAC"):
            tr = run(g, "open", ("exo", w), "complete", N, budget=400, keep_trace=True).trace
            states = [(g.tables[Y], g.n, frozenset()) for Y in range(M)]
            streams = [event_stream(g.tables[j]) for j in range(M)]
            emitted = [[] for _ in range(M)]
            for i in range(len(tr) - 1):
                c = tr[i]
                X = "ABC".index(w[c[-1]])
                s, h, t = c[4 * X:4 * X + 3]
                wr = g.tables[X][4 * (2 * s + ((t >> h) & 1))]
                emitted[X].append((s, wr))
                for Y in range(M):
                    if Y != X:
                        states[Y] = learn(states[Y], (s, wr), g)
                nxt = tr[i + 1]
                assert [(nxt[4 * Y + 3], nxt[4 * M + 2][Y]) for Y in range(M)] == [x[:2] for x in states]
            for j in range(M):                      # emitted events == precomputed fixed stream
                pre, per = streams[j]
                expand = pre + per * (len(emitted[j]) // max(1, len(per)) + 1)
                assert emitted[j] == expand[:len(emitted[j])]


def test_synthesis_fold_matches_engine_append_once(swarms):
    from mt.swarm import append_once_variant
    from mt.synthesis import initial_state, learn
    for inst in swarms[:25]:
        g = append_once_variant(growth_variant(inst, "syn1"))
        for w in ("AABC", "ABAC"):
            tr = run(g, "open", ("exo", w), "complete", N, budget=400, keep_trace=True).trace
            states = [initial_state(g, Y) for Y in range(M)]
            for i in range(len(tr) - 1):
                c = tr[i]
                X = "ABC".index(w[c[-1]])
                s, h, t = c[4 * X:4 * X + 3]
                wr = g.tables[X][4 * (2 * s + ((t >> h) & 1))]
                for Y in range(M):
                    if Y != X:
                        states[Y] = learn(states[Y], (s, wr), g)
                nxt = tr[i + 1]
                assert [(nxt[4 * Y + 3], nxt[4 * M + 2][Y]) for Y in range(M)] == [x[:2] for x in states]


def test_has_sandwich():
    from mt.synthesis import has_sandwich
    assert not has_sandwich([0, 0, 1, 1]) and not has_sandwich([1, 0]) and not has_sandwich([])
    assert has_sandwich([0, 1, 0]) and has_sandwich([1, 1, 0, 1])


def test_precedence_cycle_needs_both_orders():
    """Two conflicting pairs in opposite orders form a cycle even without a shared middle lesson."""
    from mt import synthesis as S
    # fake inst/learn: events are (q,w); conflict iff the two events are in CONF
    CONF = {((0, 0), (1, 1)), ((0, 1), (1, 0))}
    orig = S.learn
    S.learn = lambda st, e, inst: st + (e,) if any({e, x} == set(p) for p in CONF for x in st) else tuple(sorted(st + (e,)))
    try:
        # A=0 delivers (0,0) before B's (1,1); B=1 delivers (1,0) before A's (0,1): cycle, no single pivot
        merge = [(1, (1, 0)), (0, (0, 0)), (1, (1, 1)), (0, (0, 1))]
        visited = [()]
        assert S.precedence_cycle(merge, visited, None)
        merge2 = [(0, (0, 0)), (0, (0, 1)), (1, (1, 0)), (1, (1, 1))]       # serial: no cycle
        assert not S.precedence_cycle(merge2, visited, None)
    finally:
        S.learn = orig


def test_coupling_changes_tapes_never_tables(swarms):
    for inst in swarms[:30]:
        for g in ("complete", "alternating"):
            tr = run(inst, "couple", ("exo", "AABC"), g, N, budget=400, keep_trace=True).trace
            assert all(tuple(c[4 * j + 3] for j in range(M)) == inst.tables for c in tr)
        noR = SwarmInstance(inst.n, inst.tables, (None,) * len(inst.R))
        assert run(noR, "couple", ("exo", "ABC"), "complete", N, budget=300, keep_trace=True).trace == \
            run(noR, "off", ("exo", "ABC"), "complete", N, budget=300, keep_trace=True).trace


def test_coupling_rotation_equivariance(swarms):
    for inst in swarms[:20]:
        g = rotate(inst)
        a = run(inst, "couple", ("exo", "ABAC"), "alternating", N, budget=300, keep_trace=True).trace
        b = run(g, "couple", ("exo", relabel_word("ABAC")), "alternating", N, budget=300, keep_trace=True).trace
        assert [rot_cfg(c) for c in a] == b


def test_couple_once_perturbs_at_most_once_per_trigger(swarms):
    for inst in swarms[:20]:
        tr = run(inst, "couple_once", ("exo", "AABC"), "complete", N, budget=2000, keep_trace=True).trace
        assert all(tuple(c[4 * j + 3] for j in range(M)) == inst.tables for c in tr)
        assert all(v <= 1 for c in tr for per in c[4 * M + 1] for v in per)


def test_normalise_eventually_periodic_words():
    from mt.closed_loop import normalise
    w = normalise((1, 2), (3, 4))
    assert normalise((1, 2, 3, 4), (3, 4)) == w                 # one extra period in the prefix
    assert normalise((1, 2, 3), (4, 3)) == w                    # split inside the period
    assert normalise((1, 2), (3, 4, 3, 4)) == w                 # non-primitive period
    assert normalise((1,), (3, 4)) != w


@pytest.mark.parametrize("mode,engine_mode", [("learn", "on"), ("couple_once", "couple_once")])
def test_closed_loop_transducer_reproduces_engine(swarms, mode, engine_mode):
    from mt.closed_serial import history, influence, own_step
    for inst0 in swarms[:20]:
        for inst in (inst0, growth_variant(inst0, "cs")):
            for w in ("AABC", "ABAC"):
                tr = run(inst, engine_mode, ("exo", w), "complete", N, budget=400, keep_trace=True).trace
                for C in range(M):
                    u = history(inst, tr, w, C)
                    st = (0, 0, 0, inst.tables[C], inst.n, frozenset())
                    for i, x in enumerate(u):
                        st = own_step(st, inst) if x[0] == "o" else influence(st, x[2], inst, mode)
                        nxt = tr[i + 1] if i + 1 < len(tr) else None
                        if nxt is None:
                            break
                        assert st[:4] == nxt[4 * C:4 * C + 4] and st[4] == nxt[4 * M + 2][C]


def test_transplant_behaviour_invariant_under_state_relabelling(swarms):
    """Two programs that differ only by relabelling appended states behave identically on any tape."""
    from mt.transplant import FRESH, behaviour
    T = (1, 1, 2, 0, 0, 0, 3, 0) + (0, 1, 1, 0, 1, 0, 0, 0) + (1, 0, 0, 0, 0, 1, 1, 0) + (0, 0, 2, 0, 1, 1, 0, 0)
    sw = lambda row: tuple({2: 3, 3: 2}.get(v, v) if i % 4 == 2 else v for i, v in enumerate(row))
    T2 = sw(T[:8]) + sw(T[8:16]) + sw(T[24:32]) + sw(T[16:24])
    for tp in FRESH:
        assert behaviour(T, tp) == behaviour(T2, tp)


def test_transplant_behaviour_translation_invariant():
    from mt.transplant import behaviour
    walker = (0, 1, 0, 0) * 4                      # write 0, move R, stay: walks the ring
    assert behaviour(walker, 0b00000001) == behaviour(walker, 0b00000010)


def test_open_loop_replay_reproduces_engine(swarms):
    from mt.closed_serial import history, influence
    from mt.witness import own_step_open
    for inst0 in swarms[:20]:
        inst = growth_variant(inst0, "wo")
        for w in ("AABC", "ABAC"):
            tr = run(inst, "open", ("exo", w), "complete", N, budget=400, keep_trace=True).trace
            for C in range(M):
                u = history(inst, tr, w, C)
                st = (0, 0, 0, inst.tables[C], inst.n, frozenset())
                for i, x in enumerate(u[:-1]):
                    st = own_step_open(st, inst.tables[C]) if x[0] == "o" else influence(st, x[2], inst, "learn")
                    nxt = tr[i + 1]
                    assert st[:4] == nxt[4 * C:4 * C + 4] and st[4] == nxt[4 * M + 2][C]


def test_growth_variant_p_append_extremes(swarms):
    from mt.swarm import APPEND, edit_op
    for inst in swarms[:20]:
        g0 = growth_variant(inst, "m", p_append=0.0)
        g1 = growth_variant(inst, "m", p_append=1.0)
        assert not any(x is not None and edit_op(x) == APPEND for x in g0.R)
        assert all(edit_op(x) == APPEND for t, x in enumerate(g1.R) if x is not None and t < 2 * inst.n)


def test_endo_history_reproduces_engine(swarms):
    from mt.closed_serial import influence, own_step
    from mt.endo_probe import history_endo
    for inst0 in swarms[:15]:
        inst = growth_variant(inst0, "en")
        for start in range(M):
            tr = run(inst, "on", ("endo", start), "complete", N, budget=400, keep_trace=True).trace
            for C in range(M):
                u = history_endo(inst, tr, C)
                st = (0, 0, 0, inst.tables[C], inst.n, frozenset())
                for i, x in enumerate(u[:-1]):
                    st = own_step(st, inst) if x[0] == "o" else influence(st, x[2], inst, "learn")
                    nxt = tr[i + 1]
                    assert st[:4] == nxt[4 * C:4 * C + 4] and st[4] == nxt[4 * M + 2][C]


def test_least_rotation_matches_brute_force():
    import random
    from mt.transplant import least_rotation
    rng = random.Random(11)
    for _ in range(3000):
        L = rng.randrange(1, 25)
        base = [(rng.randrange(3), rng.randrange(3)) for _ in range(rng.randrange(1, 5))]
        S = (base * (L // len(base) + 1))[:L] if rng.random() < 0.4 else [(rng.randrange(3), rng.randrange(3)) for _ in range(L)]
        k = least_rotation(S)
        assert S[k:] + S[:k] == min(S[i:] + S[:i] for i in range(len(S)))
