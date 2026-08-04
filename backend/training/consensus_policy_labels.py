#!/usr/bin/env python3
"""Build consensus labels from independent reviewer JSONL files.

Only public candidate IDs are combined.  Rows without a clear majority are
reported as conflicts and omitted from the consensus training output.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy_data import (  # noqa: E402
    NPCPolicyLabelV1,
    label_distribution,
    load_policy_records,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--labels", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--min-reviewers", type=int, default=2)
    parser.add_argument("--min-agreement", type=float, default=0.67)
    args = parser.parse_args()
    if args.min_reviewers < 2 or not 0.5 <= args.min_agreement <= 1.0:
        raise SystemExit("min-reviewers must be >=2 and min-agreement must be in [0.5,1]")

    observations = {
        str(record["observation_digest"]): record
        for record in load_policy_records(args.observations)
    }
    grouped: dict[str, list[NPCPolicyLabelV1]] = defaultdict(list)
    seen_sources: set[tuple[str, str]] = set()
    for path in args.labels:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            label = NPCPolicyLabelV1.model_validate(json.loads(line))
            key = (label.observation_digest, label.source_id)
            if key in seen_sources:
                raise ValueError(f"duplicate reviewer label: {key}")
            seen_sources.add(key)
            if label.observation_digest not in observations:
                raise ValueError(f"unknown observation digest in {path}:{line_number}")
            grouped[label.observation_digest].append(label)

    consensus: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    for observation_digest, labels in sorted(grouped.items()):
        record = observations[observation_digest]
        candidates = list(record["candidates"])
        action_ids = [str(candidate["action_id"]) for candidate in candidates]
        distributions = [label_distribution(label, candidates) for label in labels]
        top_actions = [max(distribution, key=distribution.get) for distribution in distributions]
        counts = Counter(top_actions)
        winner, winner_count = counts.most_common(1)[0]
        agreement = winner_count / len(labels)
        if len(labels) < args.min_reviewers or agreement < args.min_agreement:
            conflicts.append({
                "observation_digest": observation_digest,
                "reviewers": len(labels),
                "agreement": agreement,
                "top_actions": dict(counts),
            })
            continue
        averaged = {
            action_id: sum(distribution[action_id] for distribution in distributions) / len(distributions)
            for action_id in action_ids
        }
        consensus.append(
            NPCPolicyLabelV1(
                observation_digest=observation_digest,
                target_distribution=averaged,
                label_type="expert_preference",
                confidence=agreement,
                weight=float(len(labels)),
                source_id="consensus_v1",
                rationale=f"{len(labels)} reviewers; top-action agreement={agreement:.3f}; winner={winner}",
                tags=["consensus", "logic_conflict_review"],
            ).model_dump(mode="json")
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for label in consensus:
            stream.write(json.dumps(label, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "schema_version": "npc_policy_consensus_report.v1",
        "reviewed_observations": len(grouped),
        "consensus_labels": len(consensus),
        "conflicts": len(conflicts),
        "conflict_items": conflicts,
        "min_reviewers": args.min_reviewers,
        "min_agreement": args.min_agreement,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"consensus_labels": len(consensus), "conflicts": len(conflicts), "output": str(args.output), "report": str(args.report)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
