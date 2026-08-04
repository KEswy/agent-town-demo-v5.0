#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan softmax temperatures over recorded shadow policy scores."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def probabilities(scores: dict[str, float], temperature: float) -> dict[str, float]:
    by_target = {str(action_id).split(":")[-1]: float(score) for action_id, score in scores.items()}
    maximum = max(by_target.values())
    weights = {target: math.exp(max(-60.0, (score - maximum) / temperature)) for target, score in by_target.items()}
    total = sum(weights.values())
    return {target: weight / total for target, weight in weights.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temperatures", default="0.35,0.5,0.65,0.8,1.0")
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    traces = [
        trace
        for game in report["games"]
        for trace in game.get("npc_policy_trace", [])
        if trace.get("task") == "exile_vote" and trace.get("local_scores")
    ]
    if not traces:
        raise SystemExit("no local policy scores found")
    rows = []
    for temperature in [float(value) for value in args.temperatures.split(",")]:
        if temperature <= 0.0:
            raise SystemExit("temperature must be positive")
        entropy = []
        divergence = []
        top_changed = 0
        for trace in traces:
            teacher = {str(key): float(value) for key, value in trace["rule_probabilities"].items()}
            local = probabilities(trace["local_scores"], temperature)
            entropy.append(-sum(value * math.log(max(value, 1e-12)) for value in local.values()))
            divergence.append(sum(teacher[key] * math.log(max(teacher[key], 1e-12) / max(local.get(key, 1e-12), 1e-12)) for key in teacher))
            top_changed += int(max(local, key=local.get) != max(teacher, key=teacher.get))
        rows.append({
            "temperature": temperature,
            "policy_traces": len(traces),
            "top1_change_rate": top_changed / len(traces),
            "mean_entropy": sum(entropy) / len(entropy),
            "mean_rule_to_local_kl": sum(divergence) / len(divergence),
        })
    output = {
        "schema_version": "npc_policy_temperature_calibration.v1",
        "input": str(args.input),
        "rows": rows,
        "recommendation": "Select a temperature only after reviewing entropy/divergence and gameplay shadow metrics; this report does not change runtime configuration.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
