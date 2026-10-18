"""M-agent swarm (built for M=3): agents watch each other and learn from what they see.

Written directly in the self-update view: when agent X makes a transition (pre-state q, writes w),
every agent that OBSERVES X applies the shared, anonymous learning rule R(q, w) to its OWN table.
No agent ever reads another agent's table, tape or head (same observability assumption as
mt.observer: observations are delivered losslessly and synchronously, before the next transition).

Table entry e = 2q + r: (write, move, next, route). No HALT state.
  route: 0 = keep the turn, j in 1..M-1 = pass the turn to agent (self + j) % M. Relative offsets,
  so the dynamics are equivariant under cyclic relabelling of the agents.
  Under exogenous schedules route is inert (like yield in the 2-agent model) and is stripped from
  all outcome projections.

Observation graphs (observers[X] = agents that watch X):
  ring       A watches C, B watches A, C watches B  (one source per agent)
  complete   everyone watches everyone              (two sources per agent: updates can conflict)
  decoupled  A <-> B watch each other, C isolated   (sanity: A,B must reproduce the 2-agent model)
  alternating  each event is seen by exactly ONE observer, alternating per emitter: X's 1st, 3rd, ...
             transition is seen by X+1, its 2nd, 4th, ... by X+2. Every agent still has two sources
             over time, but the edit volume per event matches ring (volume-matched control for
             complete). The per-agent parity is part of the config (`aux`).

Config: (s, h, tape, T) per agent, then aux (per-agent parity, used only by `alternating`;
constant 0 otherwise), then cnt (per-agent evidence counters, one per trigger, used only by
THRESHOLD edits; constant 0 otherwise), then ctrl.

Endogenous order (hold cap HOLD, wait cap WAIT):
  after X fires an entry with route r:
    r = 0 and X has held < HOLD consecutive moves  -> X keeps the turn
    r = 0 otherwise                                 -> forced pass to the longest-waiting other agent
    r > 0                                           -> turn goes to (X + r) % M
  fairness override: if some other agent has now waited >= WAIT moves, it gets the turn instead
  (longest-waiting first). Ties break by smallest offset from X.
  ctrl = (turn, held, waits) with waits capped at WAIT, so the config space stays finite and
  repeat detection stays exact.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import permutations

M = 3
ROUTE = 3
HOLD, WAIT = 3, 6
GRAPHS = {
    "ring": ((1,), (2,), (0,)),
    "complete": ((1, 2), (0, 2), (0, 1)),
    "decoupled": ((1,), (0,), ()),
    "alternating": None,     # dynamic: see observers()
}


def observers(graph: str, X: int, parity: int):
    if graph == "alternating":
        return ((X + 1 + parity) % M,)
    return GRAPHS[graph][X]


# ------------------------------------------------------------------ instances

def field_values(n: int, f: int) -> int:
    return {0: 2, 1: 2, 2: n, 3: M}[f]


def all_edits(n: int):
    return [(e, f, v) for e in range(2 * n) for f in range(4) for v in range(field_values(n, f))]


@dataclass(frozen=True)
class SwarmInstance:
    n: int                   # initial number of states per agent
    tables: tuple            # one flat table per agent, padded to `cap` states (absent states = zeros)
    R: tuple                 # indexed by trigger 2q + w, for q < cap
    cap: int = 0             # max states per agent (APPEND); 0 = no growth (cap == n)
    ns0: tuple = ()          # initial number of states per agent; () = n for every agent (pre-grown variant)

    @property
    def capacity(self) -> int:
        return self.cap or self.n

    @property
    def k(self) -> int:
        return sum(x is not None for x in self.R)

    def key(self):
        return (self.n, self.cap, self.ns0, self.tables, tuple((-1, -1, -1) if x is None else x for x in self.R))

    def to_json(self):
        d = {"n": self.n, "tables": [list(t) for t in self.tables],
             "R": [None if x is None else list(x) for x in self.R]}
        if self.ns0:
            d["ns0"] = list(self.ns0)
        if self.cap:
            d["cap"] = self.cap
        return d

    @staticmethod
    def from_json(d):
        return SwarmInstance(d["n"], tuple(tuple(t) for t in d["tables"]),
                             tuple(None if x is None else tuple(x) for x in d["R"]), d.get("cap", 0),
                             tuple(d.get("ns0", ())))


def random_table(n, rng):
    out = []
    for _ in range(2 * n):
        out += [rng.randrange(2), rng.randrange(2), rng.randrange(n), rng.randrange(M)]
    return tuple(out)


def random_instance(n, k, rng):
    edits = all_edits(n)
    active = set(rng.sample(range(2 * n), k))
    R = tuple(rng.choice(edits) if t in active else None for t in range(2 * n))
    return SwarmInstance(n, tuple(random_table(n, rng) for _ in range(M)), R)


def growth_variant(inst: SwarmInstance, seed: str, cap: int = 4, appends: bool = True,
                   p_active: float = 0.5, p_append: float = 0.5) -> SwarmInstance:
    """Same initial tables, padded to `cap` states. A fresh rule over all 2*cap triggers: each trigger
    is active with p_active. An active trigger of an INITIAL state is an APPEND with p_append, targeting
    an entry of an initial state, so it can fire from the start. Every other active trigger is a SET
    revision that may address any of the cap states (so copies can be specialised). The rule depends only on `seed` and `cap`, so the
    appends=True / appends=False pair shares it exactly. appends=False keeps the agent at its initial
    size: APPENDs are no-ops and revisions of absent states are no-ops (revision-only control)."""
    n = inst.n
    rng = random.Random(f"growth-{seed}-{cap}")
    pad = lambda T: tuple(T) + (0,) * (8 * (cap - n))
    R = []
    for t in range(2 * cap):
        if rng.random() >= p_active:
            R.append(None)
        elif t < 2 * n and rng.random() < p_append:
            R.append((rng.randrange(2 * n), 2, 0, APPEND))
        else:
            f = rng.randrange(4)
            v = rng.randrange(cap if f == 2 else field_values(n, f))
            R.append((rng.randrange(2 * cap), f, v))
    return SwarmInstance(n, tuple(pad(T) for T in inst.tables), tuple(R), cap if appends else n)


def append_once_variant(inst: SwarmInstance) -> SwarmInstance:
    """Same rule, but every APPEND becomes APPEND_ONCE."""
    R = tuple(x[:3] + (APPEND_ONCE,) if x is not None and edit_op(x) == APPEND else x for x in inst.R)
    return SwarmInstance(inst.n, inst.tables, R, inst.cap, inst.ns0)


def pregrown_variant(inst: SwarmInstance) -> SwarmInstance:
    """Same rule, but each agent performs its append rules BEFORE the run (round-robin over the
    append rules in trigger order, as often as room allows), and appends are disabled during the
    run. Revisions are unchanged. Only the act of appending during the run is removed."""
    apps = [x for x in inst.R if x is not None and edit_op(x) in (APPEND, APPEND_ONCE)]
    tables, ns0 = [], []
    for T in inst.tables:
        ns = inst.n
        changed = True
        while changed and apps:
            changed = False
            for x in apps:
                T, ns2, ch = _append(T, x[0], ns, inst.capacity)
                changed |= bool(ch)
                ns = ns2
        tables.append(T)
        ns0.append(ns)
    R = tuple(None if x is not None and edit_op(x) in (APPEND, APPEND_ONCE) else x for x in inst.R)
    return SwarmInstance(inst.n, tuple(tables), R, inst.capacity, tuple(ns0))


def mirror(inst: SwarmInstance) -> SwarmInstance:
    """L<->R mirror: a symmetry under every graph (tapes start blank, heads at 0)."""
    mt = lambda T: tuple(v ^ 1 if i % 4 == 1 else v for i, v in enumerate(T))
    R = tuple(None if x is None else (x[0], x[1], x[2] ^ 1 if x[1] == 1 else x[2]) + tuple(x[3:])
              for x in inst.R)
    return SwarmInstance(inst.n, tuple(mt(T) for T in inst.tables), R, inst.cap, inst.ns0)


def rotate(inst: SwarmInstance, s: int = 1) -> SwarmInstance:
    """Relabel agent i -> i+s. A symmetry for ring and complete (not decoupled)."""
    ns0 = tuple(inst.ns0[(i - s) % M] for i in range(M)) if inst.ns0 else ()
    return SwarmInstance(inst.n, tuple(inst.tables[(i - s) % M] for i in range(M)), inst.R, inst.cap, ns0)


def canonical(inst: SwarmInstance) -> SwarmInstance:
    """Only the mirror is used: agent relabelling is not a symmetry of the decoupled graph,
    which is run on the same instances."""
    return min((inst, mirror(inst)), key=SwarmInstance.key)


# ------------------------------------------------------------------ schedules

def _perms(word):
    out = []
    for p in permutations("ABC"):
        w = word.translate(str.maketrans("ABC", "".join(p)))
        if w not in out:
            out.append(w)
    return out


def random_word(seed, length=12):
    rng = random.Random(f"swarm-sched-{seed}")
    while True:
        w = "".join(rng.choice("ABC") for _ in range(length))
        if set(w) == set("ABC"):
            return w


def exo_schedules(n_random: int = 1):
    """Closed under all relabellings of A, B, C."""
    out = []
    for base in ("ABC", "AABC", "ABAC"):
        out += _perms(base)
    for s in range(n_random):
        out += _perms(random_word(s))
    return [(w if len(w) <= 4 else f"rnd{i}", w) for i, w in enumerate(out)]


# ------------------------------------------------------------------ engine

@dataclass
class SwarmResult:
    kind: str
    transient: int
    period: int
    cycle: list
    steps: int
    eff_edits: int = 0
    eff_route_edits: int = 0
    forced: int = 0
    overrides: int = 0
    trace: list | None = field(default=None, repr=False)


def initial_config(inst: SwarmInstance, sched):
    agents = tuple(x for T in inst.tables for x in (0, 0, 0, T))
    aux = (0,) * M
    cnt = ((0,) * (2 * inst.capacity),) * M
    ns = inst.ns0 or (inst.n,) * M
    if sched[0] == "endo":
        return agents + (aux, cnt, ns, (sched[1], 0, (0,) * M))
    return agents + (aux, cnt, ns, 0)


SET, TOGGLE, THRESHOLD, APPEND, APPEND_ONCE = 0, 1, 2, 3, 4
K_EVIDENCE = 3      # THRESHOLD: a belief is revised once, after this many observations of its trigger


def edit_op(x) -> int:
    """R entries are (entry, field, value) = set, or (entry, field, value, op) with op
    SET / TOGGLE / THRESHOLD.
    SET       overwrite on every observation (revision by overwrite; idempotent).
    TOGGLE    ignore value, advance the field cyclically on every observation (flip-flopping;
              commutative, not idempotent, never settles while the trigger keeps firing).
    THRESHOLD evidence accumulation that converges: the observer counts observations of the
              trigger (saturating at K_EVIDENCE) and performs the set exactly once, when the count
              reaches K_EVIDENCE. Counting commutes; every agent's table changes finitely often.
    APPEND_ONCE  like APPEND, but each rule makes at most one copy per observer (no capacity race
              while #append rules <= free slots).
    APPEND    (entry e, field 2, value 0, APPEND): "differentiate a concept". If the observer has room
              (states < cap) and entry e belongs to an existing state, copy the state that e points to
              into a new state and redirect e to the copy. Behaviour is unchanged at that moment;
              later revisions can specialise the copy without touching the original.
    Revisions never address absent states, and never point `next` at a state that doesn't exist yet
    (no-op instead)."""
    return x[3] if len(x) > 3 else SET


def noncommuting_pair(R) -> bool:
    """Two edits on the same (entry, field) whose order matters. Two edits commute iff both are
    toggles, or both are sets to the same value."""
    edits = [x for x in R if x is not None]
    for a in range(len(edits)):
        for b in range(a + 1, len(edits)):
            x, y = edits[a], edits[b]
            if x[:2] != y[:2]:
                continue
            if {APPEND, APPEND_ONCE} & {edit_op(x), edit_op(y)}:
                continue
            ox, oy = (SET if o == THRESHOLD else o for o in (edit_op(x), edit_op(y)))
            if ox == oy == TOGGLE or (ox == oy == SET and x[2] == y[2]):
                continue
            return True
    return False


def _append(T, e, ns_y, cap):
    """Copy the state entry e points to into slot ns_y; redirect e there. Returns (T, ns, changed)."""
    if ns_y >= cap or e // 2 >= ns_y:
        return T, ns_y, 0
    src = T[4 * e + 2]
    row = T[8 * src:8 * src + 8]
    T = T[:8 * ns_y] + row + T[8 * ns_y + 8:]
    i = 4 * e + 2
    T = T[:i] + (ns_y,) + T[i + 1:]
    return T, ns_y + 1, 1


def _apply(T, R, q, w, mask_route, n=2):
    """n = number of states the observer currently has."""
    x = R[2 * q + w]
    if x is None:
        return T, 0, 0
    e, f, v = x[0], x[1], x[2]
    if mask_route and f == ROUTE:
        return T, 0, 0
    if e // 2 >= n or (f == 2 and edit_op(x) != TOGGLE and v >= n):
        return T, 0, 0                                    # absent state / pointer to absent state
    i = 4 * e + f
    if edit_op(x) == TOGGLE:
        v = (T[i] + 1) % field_values(n, f)
    if T[i] == v:
        return T, 0, 0
    return T[:i] + (v,) + T[i + 1:], 1, int(f == ROUTE)


def _longest_waiting(waits, X, exclude):
    best = None
    for off in range(1, M):
        j = (X + off) % M
        if j in exclude:
            continue
        if best is None or waits[j] > waits[best]:
            best = j
    return best


def step(cfg, inst: SwarmInstance, learn: str, sched, graph: str, N: int):
    """learn: "on" | "mask_route" | "open" | "couple" | "off". Returns (cfg, eff, eff_route, forced, override).

    "couple" = physical coupling control: an observation that WOULD teach (R has an entry for the
    trigger) instead writes the observed symbol onto the observer's tape under its head.

    "open" = open loop: agents learn (observed events still update their stored table), but
    every agent ACTS on its original table, so what anyone emits never depends on what was
    learned. Order can then only affect the learned tables through the merge order of fixed
    streams; behavioural feedback ("what you learned changes what you teach") is cut."""
    ag = list(cfg[:4 * M])
    aux = cfg[4 * M]
    cnt = cfg[4 * M + 1]
    ns = cfg[4 * M + 2]
    ctrl = cfg[-1]
    if sched[0] == "exo":
        word = sched[1]
        X = "ABC".index(word[ctrl])
        new_ctrl = (ctrl + 1) % len(word)
    else:
        X, held, waits = ctrl
    o = 4 * X
    s, h, t, T = ag[o:o + 4]
    r = (t >> h) & 1
    b = 4 * (2 * s + r)
    A = inst.tables[X] if learn == "open" else T          # table the agent acts on
    w, m, nx, route = A[b], A[b + 1], A[b + 2], A[b + 3]
    t = (t | (1 << h)) if w else (t & ~(1 << h))
    h = (h + 1) % N if m else (h - 1) % N
    ag[o:o + 4] = [nx, h, t, T]
    eff = effr = 0
    if learn in ("couple", "couple_once"):
        # physical coupling (level-1 control): same observers, same triggering events, but the
        # observation changes the observer's WORLD, not its rules. The observer writes the observed
        # symbol into its own tape cell under its head. Tables never change.
        # couple_once: each trigger perturbs each observer at most once (volume-matched to learning,
        # which settles); tracked in the evidence counters.
        trig = 2 * s + w
        if inst.R[trig] is not None:
            for Y in observers(graph, X, aux[X]):
                if learn == "couple_once":
                    if cnt[Y][trig]:
                        continue
                    cnt = cnt[:Y] + (cnt[Y][:trig] + (1,) + cnt[Y][trig + 1:],) + cnt[Y + 1:]
                tY, hY = ag[4 * Y + 2], ag[4 * Y + 1]
                tY2 = (tY | (1 << hY)) if w else (tY & ~(1 << hY))
                if tY2 != tY:
                    ag[4 * Y + 2] = tY2
                    eff += 1
    elif learn != "off":
        mask = learn == "mask_route"
        trig = 2 * s + w
        x = inst.R[trig]
        for Y in observers(graph, X, aux[X]):
            if x is not None and edit_op(x) in (APPEND, APPEND_ONCE):
                if edit_op(x) == APPEND_ONCE:
                    if cnt[Y][trig]:
                        continue                           # this rule already made its copy here
                    cnt = cnt[:Y] + (cnt[Y][:trig] + (1,) + cnt[Y][trig + 1:],) + cnt[Y + 1:]
                TY, nsy, e1 = _append(ag[4 * Y + 3], x[0], ns[Y], inst.capacity)
                ns = ns[:Y] + (nsy,) + ns[Y + 1:]
                e2 = 0
            elif x is not None and edit_op(x) == THRESHOLD and not (mask and x[1] == ROUTE):
                c = cnt[Y][trig]
                if c >= K_EVIDENCE:
                    continue                               # already revised: evidence saturated
                cnt = cnt[:Y] + (cnt[Y][:trig] + (c + 1,) + cnt[Y][trig + 1:],) + cnt[Y + 1:]
                if c + 1 < K_EVIDENCE:
                    continue
                TY, e1, e2 = _apply(ag[4 * Y + 3], inst.R[:trig] + (tuple(x[:3]),) + inst.R[trig + 1:],
                                    s, w, mask, ns[Y])
            else:
                TY, e1, e2 = _apply(ag[4 * Y + 3], inst.R, s, w, mask, ns[Y])
            ag[4 * Y + 3] = TY
            eff += e1
            effr += e2
    forced = override = 0
    if sched[0] == "endo":
        waits = tuple(0 if j == X else min(waits[j] + 1, WAIT) for j in range(M))
        if route == 0 and held + 1 < HOLD:
            nxt, held = X, held + 1
        else:
            if route == 0:
                forced = 1
                nxt = _longest_waiting(waits, X, ())
            else:
                nxt = (X + route) % M
            held = 0
        starving = [j for j in range(M) if j != nxt and j != X and waits[j] >= WAIT]
        if starving:
            j = _longest_waiting(waits, X, {k for k in range(M) if k not in starving})
            nxt, held, override = j, 0, 1
        new_ctrl = (nxt, held, waits)
    if graph == "alternating":
        aux = aux[:X] + (aux[X] ^ 1,) + aux[X + 1:]
    return tuple(ag) + (aux, cnt, ns, new_ctrl), eff, effr, forced, override


def run(inst: SwarmInstance, learn: str, sched, graph: str, N: int = 8, budget: int = 200_000,
        keep_trace: bool = False) -> SwarmResult:
    cfg = initial_config(inst, sched)
    seen, trace = {}, []
    tot = [0, 0, 0, 0]
    i = 0
    while True:
        if cfg in seen:
            st = seen[cfg]
            return SwarmResult("cycle", st, i - st, trace[st:], i, *tot, trace if keep_trace else None)
        if i >= budget:
            return SwarmResult("unresolved", i, 0, [], i, *tot, trace if keep_trace else None)
        seen[cfg] = i
        trace.append(cfg)
        cfg, *d = step(cfg, inst, learn, sched, graph, N)
        for j in range(4):
            tot[j] += d[j]
        i += 1


# ------------------------------------------------------------------ outcomes

def strip(T):
    return tuple(v for i, v in enumerate(T) if i % 4 != ROUTE)


def translation_canon(S, N):
    mask = (1 << N) - 1
    best = None
    for d in range(N):
        cand = tuple(sorted((q, (h - d) % N, (((t >> d) | (t << (N - d))) & mask) if d else t, T)
                            for q, h, t, T in S))
        if best is None or cand < best:
            best = cand
    return best


def project(res: SwarmResult, proj: str, N: int):
    if res.kind == "unresolved":
        return None
    parts = [[(c[4 * j], c[4 * j + 1], c[4 * j + 2], strip(c[4 * j + 3])) for c in res.cycle] for j in range(M)]
    if proj == "local_ti":
        return tuple(translation_canon(set(p), N) for p in parts)
    if proj == "local":
        return tuple(frozenset(p) for p in parts)
    if proj == "tables_local":
        # per agent: the set of (learned) tables it holds during the cycle
        return tuple(frozenset(x[3] for x in p) for p in parts)
    if proj == "tables":
        return frozenset(tuple(parts[j][i][3] for j in range(M)) for i in range(len(res.cycle)))
    raise ValueError(proj)


def starved(res: SwarmResult) -> bool:
    return res.kind == "cycle" and any(len({c[4 * j:4 * j + 3] for c in res.cycle}) == 1 for j in range(M))
