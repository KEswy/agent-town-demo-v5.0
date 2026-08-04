#!/usr/bin/env python3
"""Select high-value policy observations for human decision review.

This produces a review-only JSONL queue.  It never invents a label and never
copies hidden roles or game outcomes; a reviewer fills ``preferred_action_id``
or ``target_distribution`` before the queue is converted to label JSONL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy_data import load_policy_records  # noqa: E402


SCHEMA_VERSION = "npc_policy_review_queue.v1"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_queue(records: list[dict[str, object]]) -> list[dict[str, object]]:
    queue: list[dict[str, object]] = []
    for record in records:
        names = list(record["feature_names"])
        candidates = []
        has_logic_signal = False
        for candidate in record["candidates"]:
            values = list(candidate["feature_values"])
            features = dict(zip(names, values))
            logic_conflict = features.get("candidate_logic_conflict", 0.0)
            sole_consistent = features.get("candidate_sole_consistent_seer", 0.0)
            has_logic_signal = has_logic_signal or logic_conflict > 0.0 or sole_consistent > 0.0
            candidates.append(
                {
                    "action_id": candidate["action_id"],
                    "target_id": candidate["target_id"],
                    "logic_conflict": logic_conflict,
                    "sole_consistent_seer": sole_consistent,
                }
            )
        if not candidates or not has_logic_signal:
            continue
        item = {
            "schema_version": SCHEMA_VERSION,
            "review_id": digest(
                {"observation_digest": record["observation_digest"], "candidates": candidates}
            ),
            "observation_digest": record["observation_digest"],
            "game_id": record["game_id"],
            "day": record["day"],
            "phase": record["phase"],
            "actor_id": record["actor_id"],
            "faction": record["faction"],
            "candidates": candidates,
            "preferred_action_id": None,
            "target_distribution": None,
            "confidence": 1.0,
            "weight": 1.0,
            "source_id": "human_review_pending",
            "rationale": "",
            "tags": ["logic_conflict_review"],
        }
        queue.append(item)
    return queue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    queue = build_queue(load_policy_records(args.input))
    if not queue:
        raise SystemExit("no logic-conflict observations found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for item in queue:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"schema_version": SCHEMA_VERSION, "items": len(queue), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
