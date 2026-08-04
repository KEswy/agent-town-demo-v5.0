#!/usr/bin/env python3
"""Compare offline labels with the Python rule-teacher distribution."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy_data import load_policy_records  # noqa: E402


def cross_entropy(target: dict[str, float], reference: dict[str, float]) -> float:
    return -sum(
        float(target[action]) * math.log(max(float(reference[action]), 1e-12))
        for action in target
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    observations = {
        str(record["observation_digest"]): record
        for record in load_policy_records(args.observations)
    }
    records = load_policy_records(args.dataset, reject_duplicate_observations=False)
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if record["label_type"] == "rule_teacher":
            continue
        groups[str(record["faction"])].append(record)

    faction_reports = []
    for faction, faction_records in sorted(groups.items()):
        divergences = []
        top_matches = 0
        for record in faction_records:
            teacher_record = observations.get(str(record["observation_digest"]))
            teacher = (
                {str(key): float(value) for key, value in teacher_record["target_distribution"].items()}
                if teacher_record is not None
                else {}
            )
            if not teacher:
                divergences.append(None)
                continue
            target = {str(key): float(value) for key, value in record["target_distribution"].items()}
            teacher_top = max(teacher, key=teacher.get)
            label_top = max(target, key=target.get)
            top_matches += int(teacher_top == label_top)
            divergences.append(cross_entropy(target, teacher))
        usable = [value for value in divergences if value is not None]
        faction_reports.append(
            {
                "faction": faction,
                "records": len(faction_records),
                "teacher_comparable_records": len(usable),
                "teacher_top1_agreement": top_matches / len(usable) if usable else None,
                "mean_label_vs_teacher_cross_entropy": sum(usable) / len(usable) if usable else None,
            }
        )
    report = {
        "schema_version": "npc_teacher_label_comparison.v1",
        "observations": str(args.observations),
        "dataset": str(args.dataset),
        "records": len(records),
        "factions": faction_reports,
        "warning": "This report measures annotation divergence, not gameplay quality or balance.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
