#!/usr/bin/env python3
"""Fill a review queue with an explicit, auditable heuristic baseline.

This is a bootstrap label source, not ground truth.  Every row is marked
``imported`` and asks for later human review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def fill(item: dict[str, object]) -> dict[str, object]:
    candidates = list(item["candidates"])
    faction = str(item["faction"])
    conflict = [c for c in candidates if float(c["logic_conflict"]) > 0.0]
    stable = [c for c in candidates if float(c["sole_consistent_seer"]) > 0.0]
    if len(candidates) == 1:
        distribution = {str(candidates[0]["action_id"]): 1.0}
        rationale = "合法候选只有一个；该标签仅作管线基线，仍需人工复核。"
    elif faction == "good" and conflict:
        preferred = {str(c["action_id"]) for c in conflict}
        fallback = [c for c in candidates if str(c["action_id"]) not in preferred]
        distribution = {
            str(candidate["action_id"]): (
                1.0 / len(preferred)
                if not fallback and str(candidate["action_id"]) in preferred
                else 0.8 / len(preferred)
                if str(candidate["action_id"]) in preferred
                else 0.2 / len(fallback)
            )
            for candidate in candidates
        }
        rationale = "启发式：好人优先处理公开逻辑冲突候选；需人工复核。"
    elif faction == "werewolf" and stable:
        preferred = {str(c["action_id"]) for c in stable}
        fallback = [c for c in candidates if str(c["action_id"]) not in preferred]
        distribution = {
            str(candidate["action_id"]): (
                1.0 / len(preferred)
                if not fallback and str(candidate["action_id"]) in preferred
                else 0.8 / len(preferred)
                if str(candidate["action_id"]) in preferred
                else 0.2 / len(fallback)
            )
            for candidate in candidates
        }
        rationale = "启发式：狼人优先施压稳定的公开核心候选；需人工复核。"
    else:
        distribution = {str(candidate["action_id"]): 1.0 / len(candidates) for candidate in candidates}
        rationale = "启发式：没有足够公开冲突证据，候选均分；需人工复核。"
    item["preferred_action_id"] = None
    item["target_distribution"] = distribution
    item["confidence"] = 0.8 if len(candidates) > 1 else 1.0
    item["weight"] = 0.5
    item["source_id"] = "codex_logic_review"
    item["rationale"] = rationale
    item["label_type"] = "imported"
    item["tags"] = list(dict.fromkeys([*item.get("tags", []), "heuristic_bootstrap", "needs_human_review"]))
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("review queue is empty")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(fill(row), ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"labels": len(rows), "output": str(args.output), "source_id": "codex_logic_review", "warning": "heuristic bootstrap; needs human review"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
