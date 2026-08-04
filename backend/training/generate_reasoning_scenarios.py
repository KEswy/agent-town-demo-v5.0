#!/usr/bin/env python3
"""Generate high-value, actor-scoped NPC reasoning scenarios.

The scenarios are deliberately small and synthetic: they test public-logic
contracts without putting hidden role assignments into the model-facing
observation.  The output is JSONL and can be reviewed or extended manually.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_reasoning import (
    NPCReasoningObservationV1,
    ReasoningClaimV1,
    ReasoningPlayerV1,
    ReasoningTuningV1,
)


def player(character_id: int, **kwargs: object) -> ReasoningPlayerV1:
    return ReasoningPlayerV1(
        character_id=character_id,
        alive=True,
        suspicion=20,
        trust=0.5,
        public_pressure=0,
        public_seer_credibility=0.5,
        **kwargs,
    )


def claim(
    evidence_id: str,
    *,
    day: int,
    actor_id: int,
    sequence: int,
    target_id: int | None = None,
    result: str | None = None,
    window_day: int | None = None,
) -> ReasoningClaimV1:
    if target_id is None:
        return ReasoningClaimV1(
            evidence_id=evidence_id,
            day=day,
            actor_id=actor_id,
            claim_type="role",
            claimed_role="seer",
            window_day=window_day,
            observed_event_sequence=sequence,
        )
    return ReasoningClaimV1(
        evidence_id=evidence_id,
        day=day,
        actor_id=actor_id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=target_id,
        result=result,
        window_day=window_day,
        observed_event_sequence=sequence,
    )


def observation(
    *,
    scenario_id: str,
    day: int,
    claims: list[ReasoningClaimV1],
    players: list[ReasoningPlayerV1],
    withdrawal_resolved: bool,
    sheriff_window_day: int | None,
    phase: str = "SHERIFF_SPEECH",
) -> dict[str, object]:
    result = NPCReasoningObservationV1(
        random_seed_commitment=(scenario_id.encode().hex() + "0" * 64)[:64],
        day=day,
        phase=phase,
        public_event_sequence=max([item.observed_event_sequence for item in claims] or [0]),
        actor_id=1,
        actor_role="villager",
        actor_camp="good",
        tuning=ReasoningTuningV1(
            reasoning_skill=0.85,
            social_susceptibility=0.2,
            deception_susceptibility=0.2,
            plan_consistency=0.85,
        ),
        players=players,
        claims=claims,
        withdrawal_resolved=withdrawal_resolved,
        sheriff_window_day=sheriff_window_day,
    )
    return {
        "schema_version": "npc_reasoning_scenario.v1",
        "scenario_id": scenario_id,
        "observation": result.model_dump(mode="json"),
    }


def build_scenarios() -> list[dict[str, object]]:
    a = player(2, claimed_role="seer", continued_campaign=True)
    b = player(3, claimed_role="seer", continued_campaign=True)
    both_claims = [
        claim("s1:a:role", day=1, actor_id=2, sequence=1, window_day=1),
        claim("s1:b:role", day=1, actor_id=3, sequence=2, window_day=1),
    ]
    scenarios = [
        observation(
            scenario_id="same_window_gold_persistent_counterclaim",
            day=1,
            claims=both_claims + [
                claim("s1:b:gold:a", day=1, actor_id=3, sequence=3,
                      target_id=2, result="good", window_day=1),
            ],
            players=[player(1), a, b],
            withdrawal_resolved=True,
            sheriff_window_day=1,
        )
        | {
            "expect": {
                "required_signal_kinds": [
                    "seer_golded_persistent_counterclaim",
                    "sole_consistent_seer_claimant",
                ],
                "supported_seer_id": 2,
                "hidden_world_consistent": False,
                "min_seer_probability": {"2": 0.99},
                "max_seer_probability": {"3": 0.01},
            }
        },
        observation(
            scenario_id="single_claimant_keeps_unclaimed_world",
            day=1,
            claims=[claim("s2:a:role", day=1, actor_id=2, sequence=1, window_day=1)],
            players=[player(1), a],
            withdrawal_resolved=False,
            sheriff_window_day=1,
        )
        | {
            "expect": {
                "forbidden_signal_kinds": ["sole_consistent_seer_claimant"],
                "hidden_world_consistent": True,
            }
        },
        observation(
            scenario_id="withdrawn_claimant_against_persistent_claimant",
            day=1,
            claims=both_claims,
            players=[
                player(1),
                player(2, claimed_role="seer", withdrew=True),
                b,
            ],
            withdrawal_resolved=True,
            sheriff_window_day=1,
        )
        | {
            "expect": {
                "required_signal_kinds": [
                    "seer_claim_withdrawn_against_persistent_counterclaim",
                    "sole_consistent_seer_claimant",
                ],
                "supported_seer_id": 3,
                "hidden_world_consistent": False,
            }
        },
        observation(
            scenario_id="post_window_gold_does_not_backflow",
            day=2,
            claims=both_claims + [
                claim("s4:b:post_window_gold", day=2, actor_id=3, sequence=4,
                      target_id=2, result="good"),
            ],
            players=[player(1), a, b],
            withdrawal_resolved=True,
            sheriff_window_day=1,
            phase="DAY_MEETING",
        )
        | {
            "expect": {
                "forbidden_signal_kinds": ["seer_golded_persistent_counterclaim"],
                "hidden_world_consistent": False,
            }
        },
        observation(
            scenario_id="known_role_conflicts_with_claim",
            day=1,
            claims=[claim("s5:a:role", day=1, actor_id=2, sequence=1, window_day=1)],
            players=[player(1), player(2, claimed_role="seer", known_role="villager")],
            withdrawal_resolved=False,
            sheriff_window_day=1,
        )
        | {
            "expect": {
                "required_signal_kinds": ["known_role_conflicts_with_seer_claim"],
                "max_seer_probability": {"2": 0.01},
            }
        },
        observation(
            scenario_id="seer_changes_check_result",
            day=2,
            claims=[
                claim("s6:a:role", day=1, actor_id=2, sequence=1, window_day=1),
                claim("s6:a:good", day=1, actor_id=2, sequence=2, target_id=3,
                      result="good", window_day=1),
                claim("s6:a:wolf", day=2, actor_id=2, sequence=3, target_id=3,
                      result="werewolf"),
            ],
            players=[player(1), player(2, claimed_role="seer"), player(3)],
            withdrawal_resolved=False,
            sheriff_window_day=1,
            phase="DAY_MEETING",
        )
        | {
            "expect": {
                "required_signal_kinds": ["seer_check_result_changed"],
            }
        },
    ]
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "examples" / "reasoning_scenarios.v1.jsonl",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for item in build_scenarios():
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(build_scenarios())} reasoning scenarios to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
