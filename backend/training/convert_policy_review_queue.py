#!/usr/bin/env python3
"""Convert completed review-queue rows into strict policy label JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy_data import (  # noqa: E402
    NPCPolicyLabelV1,
    load_policy_records,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    observations = {
        record["observation_digest"]: {
            candidate["action_id"] for candidate in record["candidates"]
        }
        for record in load_policy_records(args.observations)
    }
    labels: list[dict[str, object]] = []
    for line_number, line in enumerate(
        args.queue.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        item = json.loads(line)
        digest = item["observation_digest"]
        if digest not in observations:
            raise ValueError(f"queue line {line_number}: unknown observation_digest")
        allowed = observations[digest]
        preferred = item.get("preferred_action_id")
        distribution = item.get("target_distribution")
        if (preferred is None) == (distribution is None):
            raise ValueError(
                f"queue line {line_number}: fill exactly one of preferred_action_id or target_distribution"
            )
        if preferred is not None and preferred not in allowed:
            raise ValueError(f"queue line {line_number}: preferred action is not legal")
        if distribution is not None and set(distribution) != allowed:
            raise ValueError(
                f"queue line {line_number}: target_distribution must cover legal actions exactly"
            )
        label = NPCPolicyLabelV1(
            observation_digest=digest,
            preferred_action_id=preferred,
            target_distribution=distribution,
            label_type=item.get("label_type", "human_preference"),
            confidence=item.get("confidence", 1.0),
            weight=item.get("weight", 1.0),
            source_id=item.get("source_id", "human_review"),
            rationale=item.get("rationale") or None,
            tags=item.get("tags", []),
        )
        labels.append(label.model_dump(mode="json"))
    if not labels:
        raise ValueError("review queue contains no labels")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for label in labels:
            stream.write(json.dumps(label, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"labels": len(labels), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
