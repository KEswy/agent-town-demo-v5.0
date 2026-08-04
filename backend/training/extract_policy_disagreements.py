#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract the largest rule-vs-model policy disagreements from shadow traces."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    rows = []
    for game in source["games"]:
        for trace in game.get("npc_policy_trace", []):
            if trace.get("task") != "exile_vote" or not trace.get("local_probabilities"):
                continue
            rule = {str(key): float(value) for key, value in trace["rule_probabilities"].items()}
            guarded = {
                str(key): float(value)
                for key, value in trace["local_probabilities"].items()
            }
            raw_model = {
                str(key): float(value)
                for key, value in (
                    trace.get("model_probabilities") or guarded
                ).items()
            }
            guarded_kl = sum(
                rule[key]
                * math.log(
                    max(rule[key], 1e-12)
                    / max(guarded.get(key, 1e-12), 1e-12)
                )
                for key in rule
            )
            raw_model_kl = sum(
                rule[key]
                * math.log(
                    max(rule[key], 1e-12)
                    / max(raw_model.get(key, 1e-12), 1e-12)
                )
                for key in rule
            )
            rows.append({
                "game_id": trace["game_id"],
                "day": trace["day"],
                "phase": trace["phase"],
                "actor_id": trace["actor_id"],
                "faction": trace["faction"],
                "observation_digest": trace["observation"]["observation_digest"],
                "reasoning_digest": trace["observation"]["reasoning_digest"],
                "policy_temperature": trace.get("policy_temperature"),
                "rule_top_action": max(rule, key=rule.get),
                "guarded_top_action": max(guarded, key=guarded.get),
                "model_top_action": max(raw_model, key=raw_model.get),
                "top1_changed": (
                    max(rule, key=rule.get) != max(guarded, key=guarded.get)
                ),
                "raw_model_top1_changed": (
                    max(rule, key=rule.get) != max(raw_model, key=raw_model.get)
                ),
                "rule_probabilities": rule,
                "guarded_probabilities": guarded,
                "model_probabilities": raw_model,
                "policy_entropy_guard": trace.get("policy_entropy_guard"),
                "kl_divergence": guarded_kl,
                "raw_model_kl_divergence": raw_model_kl,
                "guarded_entropy": -sum(
                    value * math.log(max(value, 1e-12))
                    for value in guarded.values()
                ),
                "model_entropy": -sum(
                    value * math.log(max(value, 1e-12))
                    for value in raw_model.values()
                ),
                "candidates": trace["observation"]["candidates"],
            })
    rows.sort(key=lambda row: (row["kl_divergence"], row["observation_digest"]), reverse=True)
    output = {
        "schema_version": "npc_policy_disagreement_report.v2",
        "input": str(args.input),
        "traces": len(rows),
        "top1_changed": sum(1 for row in rows if row["top1_changed"]),
        "raw_model_top1_changed": sum(
            1 for row in rows if row["raw_model_top1_changed"]
        ),
        "items": rows[: max(1, args.limit)],
        "warning": "Rows contain only actor-scoped observation and legal candidates; KL divergence is not a gameplay quality score.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"traces": len(rows), "top1_changed": output["top1_changed"], "exported": len(output["items"]), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
