# multi-turing

Code and data for the LessWrong post *Reflexivity in tiny swarms: what Turing machines that learn
from each other can show*: [POST.md](POST.md) is the post, [POST_LONG.md](POST_LONG.md) the long
version with the full methodology.

Three tiny Turing machines (2 states, 2 symbols, circular tape of 8 cells, no halting) run side by
side, each on its own tape. Each one watches the others and learns from what it sees: an observation applies a
fixed rule to the observer's *own* program. The question is when the order of interactions changes
what the agents end up with, and when the result is something no serial order of the same lessons
would produce.

This is an exploratory simulation, not a proof engine. The numbers are counts over finite samples
with bounded runs. The post states what they do and do not show. The proven statements are in
[PROOFS.md](PROOFS.md).

## Reproduce

```bash
uv sync                          # Python 3.13, dependencies pinned in uv.lock
uv run pytest -q                 # 68 tests: engine, lemmas as properties, cross-implementation checks
uv run python -m mt.post_numbers # every number in the post, from results/publish/ -> POST_NUMBERS.md
```

`mt.post_numbers` reads the stored outputs in `results/publish/` and runs in about a minute. To
regenerate those outputs from scratch:

```bash
uv run python -m mt.pipeline     # all stages; resumable; ~2.25 h on 10 cores
```

The worked example in §1 of the post can be checked without this package. The script is about 140
lines of plain Python, with no dependencies:

```bash
python3 verify/verify_witness.py verify/witness_3f993cc102db_r1.json
```

## Where each number comes from

[`results/publish/POST_NUMBERS.md`](results/publish/POST_NUMBERS.md) lists every number cited in
the post, by section, with its count, denominator and 95% interval. [PROVENANCE.md](PROVENANCE.md)
maps each post section to the pipeline stage that produces it, and explains the instance ids and the
intervals.

| path | content |
|---|---|
| `results/publish/<stage>/` | outputs of one pipeline stage (CSV/parquet + a short Markdown summary) |
| `results/publish/probe400.jsonl` | the 400 instances used for all matched comparisons |
| `results/publish/witness_example/` | the §1 example, annotated step by step |
| `figures/` | Figure 1 (`mt/figures.py`, an SVG drawn from the witness data, rendered to PNG with `rsvg-convert` when installed) |
| `verify/` | standalone re-check of the §1 example (`witness_3f993cc102db_r1.json`; `witness_5c80f863a87b.json` is the earlier example, see PROVENANCE.md) |

Instance ids are hashes of the instance, so the same id means the same initial programs and rule
everywhere in `results/publish/`.

## Code

| module | role |
|---|---|
| `mt/swarm.py` | the 3-agent model: instances, observation graphs, learners (overwrite, threshold, toggle, append), open/closed loop, physical-coupling control, endogenous order |
| `mt/swarm_sweep.py` | runs one learner type over a set of instances, schedules and conditions |
| `mt/synthesis.py`, `mt/closed_serial.py` | serialisability: is the outcome reachable by some serial order of the same lessons? Precedence-cycle test (L6) |
| `mt/closed_loop.py` | L7 decomposition: learner dependence vs variation in what sources teach |
| `mt/transplant.py`, `mt/brick_tapes.py` | "new bricks": learned programs run alone on fresh tapes |
| `mt/feedback_behaviour.py` | feedback-required bricks: the pipeline's definition (no brick in the open-loop run) against a direct behavioural comparison of the learned program with its open-loop counterpart (`results/publish/bricks/FEEDBACK_BEHAVIOUR.md`) |
| `mt/mix_probe.py`, `mt/robust_probe.py`, `mt/endo_probe.py`, `mt/zeros_hunt.py`, `mt/l9_check.py` | the probes behind §5–§7 (construction/revision mix, 3-state robustness, endogenous order, exception hunt) |
| `mt/witness.py`, `mt/witness_story.py`, `mt/pick_witness.py` | finding and annotating the §1 example |
| `mt/pipeline.py`, `mt/post_numbers.py` | regenerate everything; compute the post's numbers |
| `mt/model.py`, `mt/engine.py`, `mt/sweep.py`, … | the earlier two-machine model (rewriting each other's tables directly) that the project started from |

## Documents

- [PROOFS.md](PROOFS.md): lemmas L1 and L5–L9, with proofs or proof sketches and their status.
- [DESIGN.md](DESIGN.md): model design and the decisions behind it.
- [NOTEBOOK.md](NOTEBOOK.md): the chronological lab notebook, including predictions written down
  before probes and the claims that later turned out wrong. It links to exploratory result folders
  that are not part of this repository; the post cites only `results/publish/`.
- [LITERATURE.md](LITERATURE.md): related work, with what was checked against the sources.
- [POST.md](POST.md): the post as published on LessWrong. [POST_LONG.md](POST_LONG.md): the long version with the full methodology (controls, nulls, exception hunts), which the post refers to by section.

## License

MIT, see [LICENSE](LICENSE).
