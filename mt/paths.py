"""Shared paths. The 400-instance probe subset (results/publish/probe400.jsonl) is derived from the 800-instance set probe (first 100
instances per rule size k, in file order); see make_probe400. Override with MT_PROBE400."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

PROBE400 = Path(os.environ.get("MT_PROBE400", "results/publish/probe400.jsonl"))


def make_probe400(instances_jsonl: Path, out: Path, per_k: int = 100) -> int:
    cnt, lines = Counter(), []
    for line in open(instances_jsonl):
        j = json.loads(line)
        k = sum(x is not None for x in j["R"])
        if cnt[k] < per_k:
            cnt[k] += 1
            lines.append(line)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(lines))
    return len(lines)
