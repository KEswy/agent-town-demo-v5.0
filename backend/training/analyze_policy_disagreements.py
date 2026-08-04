#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify large policy disagreements against smart-agent invariants."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def candidate_for(row: dict[str, object], action_id: str) -> dict[str, object]:
    target_id = int(str(action_id).split(":")[-1])
    return next(candidate for candidate in row["candidates"] if candidate["target_id"] == target_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    rows = report["items"]
    categories = Counter()
    details = []
    for row in rows:
        model = candidate_for(row, row["model_top_action"])
        rule = candidate_for(row, row["rule_top_action"])
        model_values = model["feature_values"]
        rule_values = rule["feature_values"]
        if row["faction"] == "werewolf" and model_values[9] > 0 and model_values[17] <= 0:
            category = "smart_wolf_targets_stable_core_without_teammate"
        elif row["faction"] == "good" and model_values[8] > 0:
            category = "smart_good_targets_public_logic_conflict"
        elif model_values[17] > 0:
            category = "model_targets_wolf_teammate_review"
        else:
            category = "unclassified_disagreement"
        categories[category] += 1
        details.append({
            "observation_digest": row["observation_digest"],
            "faction": row["faction"],
            "category": category,
            "rule_top_action": row["rule_top_action"],
            "model_top_action": row["model_top_action"],
            "model_top_candidate": {
                "target_id": model["target_id"],
                "logic_conflict": model_values[8],
                "sole_consistent_seer": model_values[9],
                "is_wolf_teammate": model_values[17],
            },
            "rule_top_candidate": {
                "target_id": rule["target_id"],
                "logic_conflict": rule_values[8],
                "sole_consistent_seer": rule_values[9],
                "is_wolf_teammate": rule_values[17],
            },
            "kl_divergence": row["kl_divergence"],
        })
    output = {
        "schema_version": "npc_policy_disagreement_analysis.v1",
        "input": str(args.input),
        "items": len(rows),
        "categories": dict(categories),
        "details": details,
        "interpretation": "smart_wolf_targets_stable_core_without_teammate is an expected strategic divergence; unclassified and teammate-target rows need manual review before local deployment.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(rows), "categories": dict(categories), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
