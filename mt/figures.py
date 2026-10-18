"""The post's Figure 1, generated from the witness data (no hand-drawn numbers).

    uv run python -m mt.figures verify/witness_3f993cc102db_r1.json figures/

SVG, plus PNG when rsvg-convert is installed. Lane timeline of the learner's first steps in the
closed loop (top) and the open loop (bottom), with the lessons that change its program; on the
right, the learner's final program alone on a fresh tape, as the head's path over 20 steps (the ring
unrolled), against the two serial versions of the same lessons.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .closed_serial import history, influence, own_step, replay, serialise
from .swarm import M, SwarmInstance, run
from .transplant import behaviour
from .witness import replay_open

NAMES = "ABC"


def load(path):
    d = json.loads(Path(path).read_text())
    inst = SwarmInstance(d["n"], tuple(tuple(t) for t in d["tables"]),
                         tuple(None if x is None else tuple(x) for x in d["R"]), d["cap"])
    return inst, d["schedule"], d["learner"], d


# ---------------------------------------------------------------- Figure 1 (SVG, lane design)

BLUE, GREY, RED, LGREY = "#2a6f97", "#9aa7b3", "#c0392b", "#b8b8b8"
LANE_Y = {0: 30, 1: 80, 2: 130}                 # lane y of agents A, B, C within a panel


def program_lessons(inst, u, C):
    st = (0, 0, 0, inst.tables[C], inst.n, frozenset())
    out = []
    for i, x in enumerate(u):
        before = st
        st = own_step(st, inst) if x[0] == "o" else influence(st, x[2], inst, "learn")
        if x[0] == "x" and st[3:5] != before[3:5]:
            q, w = x[2]
            e = inst.R[2 * q + w][0]
            if st[4] > before[4]:                               # APPEND: new state = copy of the state entry e pointed to
                out.append((i, x[1], q, "append", before[3][4 * e + 2], st[4] - 1))
            else:                                               # SET on entry e of state e // 2
                out.append((i, x[1], q, "set", e // 2, None))
    return out


def path(T, tape, steps=20, N=8):
    """Program T alone on `tape`: the head's position relative to its start after each step (the ring
    unrolled, right = +1), so a walk shows as a slope and a shuttle as a flat zigzag."""
    s, h, t, d, out = 0, 0, tape, 0, []
    for _ in range(steps):
        r = (t >> h) & 1
        b = 4 * (2 * s + r)
        w, m, nx = T[b], T[b + 1], T[b + 2]
        t = (t | (1 << h)) if w else (t & ~(1 << h))
        d += 1 if m else -1
        h = (h + 1) % N if m else (h - 1) % N
        s = nx
        out.append(d)
    return out


def _box(bx, by, bw, bh, title, series, yrange, notes, steps):
    """Outcome box: each program's head path (series: (positions, colour, width, dash)) and notes."""
    out = f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="6" fill="#fafbfc" stroke="#ccc"/>'
    out += f'<text x="{bx + 10}" y="{by + 16}" class="note" font-weight="600">{_esc(title)}</text>'
    px, py, pw, ph = bx + 40, by + 28, bw - 54, 80
    lo, hi = yrange
    Y = lambda v: py + ph - (v - lo) * ph / (hi - lo)
    every = 1 if hi - lo <= 10 else 2 if hi - lo <= 20 else 4
    for v in range(lo, hi + 1):
        if v % every == 0:
            out += f'<line x1="{px}" y1="{Y(v):.1f}" x2="{px + pw}" y2="{Y(v):.1f}" stroke="{"#ddd" if v == 0 else "#eee"}"/>'
    out += f'<text x="{px - 4}" y="{Y(0) + 4:.1f}" text-anchor="end" class="small">start</text>'
    for v in (lo, hi):
        if v != 0 and abs(Y(v) - Y(0)) >= 12:
            out += f'<text x="{px - 4}" y="{Y(v) + 4:.1f}" text-anchor="end" class="small">{v:+d}</text>'
    for vals, col, width, dash in series:
        pts = f"{px:.1f},{Y(0):.1f} " + " ".join(f"{px + (i + 1) * pw / len(vals):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        out += (f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{width}" stroke-linejoin="round" '
                f'stroke-linecap="round"{" stroke-dasharray=%s" % repr(dash) if dash else ""}/>')
    out += f'<text x="{px}" y="{py + ph + 16}" class="small">head: cells from its start, {steps} steps</text>'
    for i, line in enumerate(notes):
        out += f'<text x="{bx + 10}" y="{by + bh - 28 + 13 * i}" class="small">{_esc(line)}</text>'
    return out


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _panel(title, movers, lessons, ghosts, C, H, sched_line, box, ox, X0=80, DX=54):
    sx = lambda step: X0 + DX * (step - 1)
    L = NAMES[C]
    s = f'<text x="20" y="-6" class="title">{_esc(title)}</text>'
    for k in range(M):
        y = LANE_Y[k]
        s += (f'<text x="22" y="{y + 4}" class="lanelbl">{NAMES[k]}</text>'
              f'<line x1="60" y1="{y}" x2="{sx(H) + 30}" y2="{y}" class="lane"/>')
    for step in range(1, H + 1):
        s += f'<text x="{sx(step)}" y="158" text-anchor="middle" class="step">{step}</text>'
    s += f'<text x="{sx(1)}" y="172" class="step" font-style="italic">{_esc(sched_line)}</text>'
    for step, (X, q, learned) in enumerate(movers, 1):
        y = LANE_Y[X]
        s += f'<circle cx="{sx(step)}" cy="{y}" r="6.5" fill="{BLUE if learned else GREY}"/>'
        if learned:
            if X == M - 1:                                            # bottom lane: beside the dot, clear of the step axis
                s += f'<text x="{sx(step) + 10}" y="{y + 4}" class="small" fill="{BLUE}">state {q}</text>'
            else:                                                     # label above the dot
                s += f'<text x="{sx(step)}" y="{y - 11}" text-anchor="middle" class="small" fill="{BLUE}">state {q}</text>'
    # lessons: (number, step, teacher, label lines, ghost?)
    for num, step, X, label, ghost in lessons + ghosts:
        x, y1, y2 = sx(step), LANE_Y[X], LANE_Y[C]
        up = y1 > y2                                            # teacher below the learner: arrow goes up
        a, b = (y1 - 7, y2 + 8) if up else (y1 + 7, y2 - 8)
        c1, c2 = (y1 - 25, y2 + 22) if up else (y1 + 25, y2 - 22)
        cls = "ghost" if ghost else "lesson"
        s += f'<path d="M{x},{a} C{x},{c1} {x + 8},{c2} {x + 10},{b}" class="{cls}"/>'
        ym = (y1 + y2) / 2
        s += f'<text x="{x + 14}" y="{ym + 4}" class="{"tagg" if ghost else "tag"}">{num}</text>'
        # notes sit in the lane gap next to the teacher, on the learner's side, clear of every dot
        y_note = (y1 - 18 - 13 * (len(label) - 1)) if up else (y1 + 18)
        for li, ln in enumerate(label):
            s += f'<text x="{x + 26}" y="{y_note + li * 13}" class="{"noteg" if ghost else "note"}">{_esc(ln)}</text>'
    s += _box(ox, 0, 220, 170, *box)
    return s


def figure1(inst, word, C, out: Path, horizon=None, trace_steps=20):
    """Figure 1 (SVG; PNG via rsvg-convert when available). Lane timeline of the learner's first steps,
    closed loop on top and open loop below, with the lessons that change its program; on the right,
    the learner's final program alone on a fresh tape as a head trace, against the two serial versions.
    Every number is computed from the witness data."""
    L = NAMES[C]
    A, B = [j for j in range(M) if j != C]
    runs = {lp: run(inst, "on" if lp == "closed" else "open", ("exo", word), "complete", 8,
                    budget=200_000, keep_trace=True).trace for lp in ("closed", "open")}
    hist = {lp: history(inst, tr, word, C) for lp, tr in runs.items()}
    les = {lp: program_lessons(inst, u, C) for lp, u in hist.items()}
    st0 = (0, 0, 0, inst.tables[C], inst.n, frozenset())
    Tc = replay(st0, hist["closed"], inst, "learn")[3]
    Tab, Tba = (replay(st0, serialise(hist["closed"], A, B), inst, "learn")[3],
                replay(st0, serialise(hist["closed"], B, A), inst, "learn")[3])
    To = replay_open(st0, hist["open"], inst, inst.tables[C])[3]
    Toab, Toba = (replay_open(st0, serialise(hist["open"], A, B), inst, inst.tables[C])[3],
                  replay_open(st0, serialise(hist["open"], B, A), inst, inst.tables[C])[3])
    brick = lambda T, P1, P2: [tp for tp in range(256) if behaviour(T, tp) != behaviour(P1, tp) and behaviour(T, tp) != behaviour(P2, tp)]
    nb_closed, nb_open = brick(Tc, Tab, Tba), brick(To, Toab, Toba)
    n_diff = sum(1 for tp in range(256) if behaviour(Tc, tp) != behaviour(To, tp))
    tape = 0 if 0 in nb_closed else (nb_closed[0] if nb_closed else 0)
    tape_name = "blank tape" if tape == 0 else "tape " + "".join(str((tape >> i) & 1) for i in range(8))
    if horizon is None:
        last = max([l[0] for l in les["closed"]] + [l[0] for l in les["open"]], default=0)
        horizon = max(9, last + 3)
    DX = min(54, int((500 - 80) / max(1, horizon - 1)))

    def movers(lp):
        out = []
        for c in runs[lp][:horizon]:
            X = "ABC".index(word[c[-1]])
            q = c[4 * X]
            out.append((X, q, q >= inst.n))
        return out

    def label(l):
        i, X, q, kind, target, new = l
        T = NAMES[X]
        if kind == "append":
            return [f"{T}: new state {new}", f"(copy of state {target})"]
        if q >= inst.n:
            return [f"{T}, in state {q} (which it learned):", f"rewires {L}'s state {target}"]
        return [f"{T}: rewires {L}'s state {target}"]

    closed_lessons = [(n, l[0] + 1, l[1], label(l), False) for n, l in enumerate(les["closed"], 1)]
    num_of = {(l[0], l[1]): n for n, l in enumerate(les["closed"], 1)}
    open_lessons, ghosts = [], []
    for l in les["open"]:
        n = num_of.get((l[0], l[1]), len(num_of) + 1)
        open_lessons.append((n, l[0] + 1, l[1], label(l), False))
    open_steps = {(l[0], l[1]) for l in les["open"]}
    for n, l in enumerate(les["closed"], 1):
        if (l[0], l[1]) not in open_steps and l[0] < horizon:
            q_open = runs["open"][l[0]][4 * l[1]]
            ghosts.append((n, l[0] + 1, l[1], [f"{NAMES[l[1]]} is in state {q_open}:", f"lesson {n} never happens"], True))
    sched_line = f"step; schedule {' '.join(word)} repeating"
    T = trace_steps
    hc, hab, hba, ho, hoab, hoba = (path(x, tape, T) for x in (Tc, Tab, Tba, To, Toab, Toba))
    allv = hc + hab + hba + ho + hoab + hoba
    yrange = (min(min(allv), -3), max(max(allv), 3))
    title = f"{L} alone on a {tape_name}"
    closed_box = (title, [(hab, LGREY, 4.5, ""), (hba, LGREY, 4.5, "" if hab == hba else "7 5"), (hc, BLUE, 2.2, "")], yrange,
                  [f"Blue: {L}'s program. Grey: " + ("the serial versions." if hab == hba else "the two serial versions."),
                   f"Unlike both on {len(nb_closed)} / 256 tapes."], T)
    open_box = (title, [(hoab, LGREY, 4.5, ""), (hoba, LGREY, 4.5, "" if hoab == hoba else "7 5"), (ho, BLUE, 2.2, "")], yrange,
                ([f"Same as a serial version on all 256 tapes."] if not nb_open else [f"Unlike both serial versions on {len(nb_open)} / 256 tapes."])
                + [f"Differs from the closed-loop {L} on {n_diff} / 256."], T)
    closed = _panel("Closed loop: agents act on what they learned", movers("closed"),
                    [x for x in closed_lessons if x[1] <= horizon], [], C, horizon, sched_line, closed_box, 560, DX=DX)
    openp = _panel("Open loop: agents learn, but act on their original programs", movers("open"),
                   [x for x in open_lessons if x[1] <= horizon], ghosts, C, horizon, sched_line, open_box, 560, DX=DX)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 520" width="800" height="520" font-family="Helvetica, Arial, sans-serif" font-size="13">
<defs>
<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>
<marker id="arrg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LGREY}"/></marker>
</defs>
<style>
.lane{{stroke:#ddd;stroke-width:1}} .lanelbl{{font-weight:600;fill:#333}} .step{{fill:#777;font-size:11px}}
.lesson{{stroke:{RED};stroke-width:2;fill:none;marker-end:url(#arr)}} .ghost{{stroke:{LGREY};stroke-width:2;stroke-dasharray:5 4;fill:none;marker-end:url(#arrg)}}
.tag{{fill:{RED};font-weight:700;font-size:12px}} .tagg{{fill:#999;font-weight:700;font-size:12px}}
.title{{font-weight:700;font-size:14px;fill:#222}} .note{{fill:#444;font-size:11.5px}} .noteg{{fill:#999;font-size:11.5px}} .small{{fill:#666;font-size:10.5px}}
</style>
<rect width="800" height="520" fill="white"/>
<g transform="translate(0,28)">{closed}</g>
<g transform="translate(0,258)">{openp}</g>
<g transform="translate(20,466)" class="small">
<circle cx="6" cy="-4" r="6" fill="{GREY}"/><text x="18" y="0">move from an original state (0 or 1)</text>
<circle cx="6" cy="14" r="6" fill="{BLUE}"/><text x="18" y="18">move from a state the agent learned (2 or 3)</text>
<line x1="290" y1="-4" x2="320" y2="-4" stroke="{RED}" stroke-width="2"/><text x="328" y="0">lesson that changes {L}'s program</text>
<line x1="290" y1="14" x2="320" y2="14" stroke="{LGREY}" stroke-width="4.5" stroke-linecap="round"/><text x="328" y="18">right: {L}'s program after the same lessons in a serial order</text>
</g>
</svg>"""
    (out / "fig1_witness.svg").write_text(svg)
    import shutil
    import subprocess
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-w", "1600", str(out / "fig1_witness.svg"), "-o", str(out / "fig1_witness.png")], check=True)
    else:
        print("rsvg-convert not found: fig1_witness.png not rendered (the SVG is the source)")
    return [(l[0], l[1], l[2], l[3], l[4]) for l in les["closed"]], len(nb_closed), n_diff, tape_name


def main(witness, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    inst, word, C, d = load(witness)
    lessons, nb, nd, tape_name = figure1(inst, word, C, out)
    print("lessons changing the learner's program (step, teacher, teacher's state, kind, target state):", lessons)
    print(f"new brick on {nb} / 256 tapes; differs from the open-loop program on {nd} / 256; traces drawn on the {tape_name}")
    print("wrote", *sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "verify/witness_3f993cc102db_r1.json",
         sys.argv[2] if len(sys.argv) > 2 else "figures")
