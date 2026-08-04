#!/usr/bin/env python3
"""Evaluate sealed local policy artifacts on strict offline JSONL."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy import (  # noqa: E402
    NPCPolicyObservationV1,
    load_local_policy,
)
from backend.app.npc_policy_data import load_policy_records  # noqa: E402


EPSILON = 1e-9


def _observation(record: dict[str, object]) -> NPCPolicyObservationV1:
    return NPCPolicyObservationV1.model_validate(
        {
            "schema_version": "npc_policy_observation.v1",
            "feature_schema_version": record["feature_schema_version"],
            "game_id": record["game_id"],
            "day": record["day"],
            "phase": record["phase"],
            "task": "exile_vote",
            "actor_id": record["actor_id"],
            "faction": record["faction"],
            "reasoning_digest": record["reasoning_digest"],
            "feature_names": record["feature_names"],
            "candidates": record["candidates"],
            "observation_digest": record["observation_digest"],
        }
    )


def evaluate_faction(
    faction: str,
    records: list[dict[str, object]],
    artifact_root: Path,
) -> dict[str, object]:
    faction_records = [
        record for record in records if record["faction"] == faction
    ]
    if not faction_records:
        raise ValueError(f"dataset has no {faction} records")
    artifact_dir = artifact_root / (
        "good_policy_v1" if faction == "good" else "wolf_policy_v1"
    )
    policy = load_local_policy(artifact_dir)
    losses: list[float] = []
    agreements: list[float] = []
    weights: list[float] = []
    scored_records = 0
    finite_scores = 0
    expected_scores = 0
    legal_predictions = 0
    failures: list[str] = []
    for record in faction_records:
        try:
            observation = _observation(record)
            expected_scores += len(observation.candidates)
            result = policy.score(observation)
            scores = [float(item.score) for item in result.scores]
            finite_scores += sum(math.isfinite(score) for score in scores)
            logits = np.asarray(scores, dtype=np.float64)
            if not np.isfinite(logits).all():
                raise ValueError("non-finite score returned")
            logits -= np.max(logits)
            probabilities = np.exp(np.clip(logits, -60.0, 60.0))
            probabilities /= probabilities.sum()
            target_distribution = record["target_distribution"]
            targets = np.asarray(
                [
                    float(target_distribution[candidate.action_id])  # type: ignore[index]
                    for candidate in observation.candidates
                ],
                dtype=np.float64,
            )
            targets /= targets.sum()
            sample_weight = float(record.get("weight", 1.0))
            weights.append(sample_weight)
            losses.append(
                float(
                    -(targets * np.log(np.maximum(probabilities, EPSILON))).sum()
                )
            )
            target_max = float(np.max(targets))
            best_actions = {
                candidate.action_id
                for candidate, value in zip(observation.candidates, targets)
                if math.isclose(float(value), target_max, abs_tol=1e-12)
            }
            predicted_index = int(np.argmax(probabilities))
            predicted_action = observation.candidates[predicted_index].action_id
            legal_predictions += int(
                predicted_action
                in {candidate.action_id for candidate in observation.candidates}
            )
            agreements.append(float(predicted_action in best_actions))
            scored_records += 1
        except Exception as exc:
            failures.append(
                f"{record.get('game_id', '?')}:{record.get('trace_index', '?')}: "
                f"{type(exc).__name__}: {exc}"
            )
    if not losses:
        raise ValueError(
            f"no valid {faction} records could be scored"
        )
    total_weight = sum(weights)
    return {
        "faction": faction,
        "artifact_schema_version": policy.manifest.schema_version,
        "model_id": policy.manifest.model_id,
        "model_digest": policy.model_digest,
        "records": len(faction_records),
        "scored_records": scored_records,
        "failed_records": len(failures),
        "failures": failures[:10],
        "weighted_cross_entropy": sum(
            value * weight for value, weight in zip(losses, weights)
        )
        / total_weight,
        "weighted_top1_agreement": sum(
            value * weight for value, weight in zip(agreements, weights)
        )
        / total_weight,
        "candidate_coverage": scored_records / len(faction_records),
        "finite_score_rate": (
            finite_scores / expected_scores if expected_scores else 0.0
        ),
        "legality_rate": (
            legal_predictions / scored_records if scored_records else 0.0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate good/werewolf policy artifacts on strict JSONL."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=ROOT_DIR / "backend" / "policy_artifacts",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records = load_policy_records(
        args.dataset,
        reject_duplicate_observations=False,
    )
    faction_reports = [
        evaluate_faction(faction, records, args.artifact_dir)
        for faction in ("good", "werewolf")
    ]
    legality_rate = min(
        float(faction_reports[0]["legality_rate"]),
        float(faction_reports[1]["legality_rate"]),
    )
    report = {
        "schema_version": "npc_policy_evaluation.v1",
        "dataset": str(args.dataset),
        "records": len(records),
        "factions": faction_reports,
        "legality_rate": legality_rate,
    }
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
