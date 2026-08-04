#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit review rows with explicit smart-good-v2/smart-wolf-v1 rubrics.

This is a reasoned offline annotation, not hidden-role ground truth.  The
weights are kept in this file so every generated label is reproducible and
auditable.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


GOOD_SOURCE_ID = "codex_smart_good_audit_v2"
WEREWOLF_SOURCE_ID = "codex_smart_audit_v1"
GOOD_TEACHER_WEIGHT = 0.85
GOOD_SOLE_SEER_MASS_CAP = 0.02
FEATURE_NAMES = [
    "candidate_suspicion", "candidate_public_pressure", "candidate_distrust",
    "candidate_wolf_belief", "candidate_good_belief", "candidate_seer_belief",
    "candidate_reasoning_confidence", "candidate_claimed_seer",
    "candidate_logic_conflict", "candidate_sole_consistent_seer",
    "candidate_is_sheriff_nomination", "candidate_is_provisional_vote",
    "candidate_in_suspected_set", "candidate_in_trusted_set", "candidate_is_sheriff",
    "candidate_is_known_good", "candidate_is_known_wolf", "candidate_is_wolf_teammate",
    "actor_reasoning_skill", "actor_social_susceptibility", "actor_deception_susceptibility",
    "actor_plan_consistency", "actor_team_coordination", "day_progress", "alive_ratio",
]


def softmax(scores: dict[str, float], temperature: float = 1.35) -> dict[str, float]:
    scaled = {key: value / temperature for key, value in scores.items()}
    pivot = max(scaled.values())
    weights = {key: math.exp(value - pivot) for key, value in scaled.items()}
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def normalize(distribution: dict[str, float]) -> dict[str, float]:
    canonical = {
        action_id: max(0.0, float(value))
        for action_id, value in distribution.items()
    }
    total = sum(canonical.values())
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("distribution requires positive finite mass")
    return {
        action_id: value / total
        for action_id, value in canonical.items()
    }


def teacher_distribution(observation: dict[str, object]) -> dict[str, float]:
    """Read either a raw V1 teacher row or a canonical V2 teacher row."""

    candidates = list(observation["candidates"])
    if "rule_probabilities" in observation:
        probabilities = dict(observation["rule_probabilities"])
        return normalize(
            {
                str(candidate["action_id"]): float(
                    probabilities[str(candidate["target_id"])]
                )
                for candidate in candidates
            }
        )
    return normalize(
        {
            str(candidate["action_id"]): float(
                observation["target_distribution"][str(candidate["action_id"])]
            )
            for candidate in candidates
        }
    )


def score_werewolf(features: dict[str, float]) -> tuple[float, list[str]]:
    """Keep the smart-werewolf v1 scorer byte-for-byte equivalent."""

    def f(name: str) -> float:
        return float(features.get(name, 0.0))

    value = (
        4.0 * f("candidate_sole_consistent_seer")
        + 2.0 * f("candidate_seer_belief")
        + 1.8 * f("candidate_logic_conflict")
        + 1.4 * f("candidate_public_pressure")
        + 0.8 * f("candidate_suspicion")
        + 0.8 * f("candidate_is_known_good")
        - 5.5 * f("candidate_is_wolf_teammate")
        - 3.2 * f("candidate_is_known_wolf")
        - 0.8 * f("candidate_in_trusted_set")
    )
    reasons = [
        (f("candidate_sole_consistent_seer"), "稳定核心/预言家威胁"),
        (f("candidate_logic_conflict"), "公开冲突可被狼队利用"),
        (f("candidate_public_pressure"), "公开压力与归票收益"),
        (-f("candidate_is_wolf_teammate"), "保护狼队友"),
    ]
    reasons.sort(key=lambda item: abs(item[0]), reverse=True)
    return value, [label for magnitude, label in reasons if abs(magnitude) > 0.05][:3]


def smart_good_distribution(
    teacher: dict[str, float],
    features_by_action: dict[str, dict[str, float]],
) -> tuple[dict[str, float], dict[str, object]]:
    """Apply the smallest explicit correction justified by hard public logic.

    ``sole_consistent_seer`` is itself emitted only after the public
    contradiction constraints isolate one surviving claimant, so it counts as
    a hard-conflict observation even when the contradictory claimant is no
    longer a legal exile target.
    """

    teacher = normalize(teacher)
    conflict_actions = [
        action_id
        for action_id, features in features_by_action.items()
        if float(features["candidate_logic_conflict"]) > 0.0
    ]
    sole_seer_actions = [
        action_id
        for action_id, features in features_by_action.items()
        if float(features["candidate_sole_consistent_seer"]) > 0.0
    ]
    hard_public_logic_conflict = bool(conflict_actions or sole_seer_actions)
    if not hard_public_logic_conflict:
        return dict(teacher), {
            "hard_public_logic_conflict": False,
            "correction_action_id": None,
            "conflict_action_ids": [],
            "sole_consistent_seer_action_ids": [],
            "teacher_weight": 1.0,
            "sole_seer_mass": sum(
                teacher[action_id] for action_id in sole_seer_actions
            ),
        }

    protected = set(sole_seer_actions)
    eligible = [
        action_id for action_id in teacher if action_id not in protected
    ]
    if not eligible:
        return dict(teacher), {
            "hard_public_logic_conflict": True,
            "correction_action_id": None,
            "conflict_action_ids": conflict_actions,
            "sole_consistent_seer_action_ids": sole_seer_actions,
            "teacher_weight": 1.0,
            "sole_seer_mass": sum(
                teacher[action_id] for action_id in sole_seer_actions
            ),
        }

    conflict_targets = [
        action_id for action_id in conflict_actions if action_id in eligible
    ]
    if conflict_targets:
        correction_pool = conflict_targets
    else:
        provisional_targets = [
            action_id
            for action_id in eligible
            if float(
                features_by_action[action_id]["candidate_is_provisional_vote"]
            )
            > 0.0
        ]
        nomination_targets = [
            action_id
            for action_id in eligible
            if float(
                features_by_action[action_id]["candidate_is_sheriff_nomination"]
            )
            > 0.0
        ]
        correction_pool = provisional_targets or nomination_targets or eligible
    correction_action_id = max(
        correction_pool,
        key=lambda action_id: (teacher[action_id], action_id),
    )

    corrected = {
        action_id: GOOD_TEACHER_WEIGHT * probability
        for action_id, probability in teacher.items()
    }
    corrected[correction_action_id] += 1.0 - GOOD_TEACHER_WEIGHT

    sole_mass = sum(corrected[action_id] for action_id in sole_seer_actions)
    if sole_mass > GOOD_SOLE_SEER_MASS_CAP:
        scale = GOOD_SOLE_SEER_MASS_CAP / sole_mass
        removed_mass = 0.0
        for action_id in sole_seer_actions:
            previous = corrected[action_id]
            corrected[action_id] *= scale
            removed_mass += previous - corrected[action_id]
        corrected[correction_action_id] += removed_mass
    corrected = normalize(corrected)
    return corrected, {
        "hard_public_logic_conflict": True,
        "correction_action_id": correction_action_id,
        "conflict_action_ids": conflict_actions,
        "sole_consistent_seer_action_ids": sole_seer_actions,
        "teacher_weight": GOOD_TEACHER_WEIGHT,
        "sole_seer_mass": sum(
            corrected[action_id] for action_id in sole_seer_actions
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    observations = {}
    for line in args.observations.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            observations[item["observation_digest"]] = item
    rows = [json.loads(line) for line in args.queue.read_text(encoding="utf-8").splitlines() if line.strip()]
    audited = []
    report_rows = []
    for row in rows:
        observation = observations.get(row["observation_digest"])
        if observation is None:
            raise ValueError(f"unknown observation digest: {row['observation_digest']}")
        by_action = {candidate["action_id"]: candidate for candidate in observation["candidates"]}
        features_by_action = {}
        for candidate in row["candidates"]:
            source = by_action[candidate["action_id"]]
            features_by_action[candidate["action_id"]] = dict(
                zip(FEATURE_NAMES, source["feature_values"])
            )
        scores: dict[str, float] = {}
        reasons_by_action: dict[str, list[str]] = {}
        good_audit: dict[str, object] | None = None
        if row["faction"] == "good":
            rule_teacher = teacher_distribution(observation)
            distribution, good_audit = smart_good_distribution(
                rule_teacher,
                features_by_action,
            )
            source_id = GOOD_SOURCE_ID
        else:
            for action_id, features in features_by_action.items():
                scores[action_id], reasons_by_action[action_id] = (
                    score_werewolf(features)
                )
            distribution = softmax(scores)
            source_id = WEREWOLF_SOURCE_ID
        ordered = sorted(distribution, key=distribution.get, reverse=True)
        winner = ordered[0]
        margin = distribution[winner] - (distribution[ordered[1]] if len(ordered) > 1 else 0.0)
        row["preferred_action_id"] = None
        row["target_distribution"] = distribution
        row["confidence"] = round(min(0.95, max(0.55, 0.55 + margin), 2), 2)
        row["weight"] = 1.0
        row["source_id"] = source_id
        row["label_type"] = "expert_preference"
        if row["faction"] == "good":
            assert good_audit is not None
            if good_audit["hard_public_logic_conflict"]:
                rationale = (
                    "聪明好人审计 v2：以 rule teacher 为主体，仅因硬公开逻辑冲突"
                    f"把票型向 {good_audit['correction_action_id']} 收拢，并保护唯一一致预言家；"
                    f"首选 {winner}。该标签来自公开/合法特征，不使用赛后真值。"
                )
            else:
                rationale = (
                    "聪明好人审计 v2：未出现硬公开逻辑冲突，逐项保持 rule teacher；"
                    f"首选 {winner}。该标签来自公开/合法特征，不使用赛后真值。"
                )
            row["rationale"] = rationale
            row["tags"] = [
                "codex_smart_good_audit_v2",
                "teacher_anchored",
                "logic_conflict_review",
            ]
        else:
            row["rationale"] = (
                "聪明狼人审计：优先考虑"
                f"{'、'.join(reasons_by_action[winner]) or '整体公开候选比较'}；"
                f"首选 {winner}，但保留其他合法候选概率。该标签来自公开/合法特征，不使用赛后真值。"
            )
            row["tags"] = ["codex_smart_audit", "logic_conflict_review"]
        audited.append(row)
        report_rows.append(
            {
                "observation_digest": row["observation_digest"],
                "faction": row["faction"],
                "winner": winner,
                "confidence": row["confidence"],
                "scores": scores,
                "good_audit": good_audit,
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for row in audited:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "schema_version": "npc_smart_audit_report.v2",
        "source_ids": {
            "good": GOOD_SOURCE_ID,
            "werewolf": WEREWOLF_SOURCE_ID,
        },
        "rows": len(audited),
        "rubric": "teacher_anchored_smart_good_v2_smart_wolf_v1",
        "items": report_rows,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "rows": len(audited),
                "output": str(args.output),
                "report": str(args.report),
                "source_ids": {
                    "good": GOOD_SOURCE_ID,
                    "werewolf": WEREWOLF_SOURCE_ID,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
