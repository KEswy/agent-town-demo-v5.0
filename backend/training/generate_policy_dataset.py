#!/usr/bin/env python3
"""Generate actor-scoped NPC exile-policy records from deterministic games.

The generator never starts FastAPI/Godot and never calls an LLM.  Every target
distribution is the existing Python rule distribution; the resulting JSONL
contains only legal candidate features and soft targets for offline training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy import (  # noqa: E402
    NPC_POLICY_FEATURE_SCHEMA_VERSION,
    NPC_POLICY_OBSERVATION_SCHEMA_VERSION,
    NPC_POLICY_TRACE_SCHEMA_VERSION,
    NPCPolicyObservationV1,
)
from backend.app.simulation import (  # noqa: E402
    DEFAULT_MAX_DAYS,
    DEFAULT_MAX_STEPS,
    run_rule_simulation_batch,
)


DATASET_SCHEMA_VERSION = "npc_policy_dataset.v1"
RECORD_SCHEMA_VERSION = "npc_policy_training_record.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate JSONL soft-target records for the local NPC exile "
            "policy. Python rules remain the teacher."
        )
    )
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--player-role", default="random")
    parser.add_argument("--max-days", type=int, default=DEFAULT_MAX_DAYS)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSONL destination; parent directories are created",
    )
    return parser.parse_args()


def build_records(report: dict[str, object]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for game_index, game in enumerate(report["games"]):
        seed = int(game["seed"])
        for trace_index, trace in enumerate(game.get("npc_policy_trace") or []):
            if trace.get("task") != "exile_vote":
                continue
            observation = NPCPolicyObservationV1.model_validate(
                trace["observation"]
            )
            rule_targets = {
                str(target_id): float(probability)
                for target_id, probability in trace["rule_probabilities"].items()
            }
            candidate_targets = {
                str(candidate.target_id)
                for candidate in observation.candidates
            }
            if set(rule_targets) != candidate_targets:
                raise ValueError(
                    "rule target set differs from policy candidate target set"
                )
            records.append(
                {
                    "schema_version": RECORD_SCHEMA_VERSION,
                    "seed": seed,
                    "game_index": game_index,
                    "trace_index": trace_index,
                    "game_id": observation.game_id,
                    "day": observation.day,
                    "phase": observation.phase,
                    "actor_id": observation.actor_id,
                    "faction": observation.faction,
                    "reasoning_digest": observation.reasoning_digest,
                    "observation_digest": observation.observation_digest,
                    "feature_schema_version": (
                        observation.feature_schema_version
                    ),
                    "feature_names": observation.feature_names,
                    "candidates": [
                        candidate.model_dump(mode="json")
                        for candidate in observation.candidates
                    ],
                    "rule_probabilities": rule_targets,
                }
            )
    return records


def main() -> int:
    args = parse_args()
    report = run_rule_simulation_batch(
        args.seed,
        args.games,
        player_role=args.player_role,
        max_days=args.max_days,
        max_steps=args.max_steps,
        capture_beliefs=False,
        capture_stances=False,
        capture_vote_calibration=False,
        capture_event_logs=False,
        capture_npc_policy=True,
        npc_policy_mode="rule",
    )
    records = build_records(report)
    if not records:
        raise SystemExit("no NPC policy records were generated")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
    header = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "trace_schema_version": NPC_POLICY_TRACE_SCHEMA_VERSION,
        "observation_schema_version": NPC_POLICY_OBSERVATION_SCHEMA_VERSION,
        "feature_schema_version": NPC_POLICY_FEATURE_SCHEMA_VERSION,
        "start_seed": args.seed,
        "games": args.games,
        "records": len(records),
        "output": str(args.output),
        # This is the digest of the exact canonical JSONL bytes written above,
        # so it can be compared directly with later validation/training steps.
        "content_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    print(json.dumps(header, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
