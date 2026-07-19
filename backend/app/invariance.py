"""Reusable hidden-information differential checks for Agent Town V3.1-G.

M06-A compares public state and unprivileged villager-NPC decision projections
across states that differ only in hidden internals. It is an offline test tool:
live API handlers and gameplay rules do not import this module.
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from . import main as rules
from .belief import build_belief_snapshot
from .npc_decision import (
    validate_public_speech_continuity,
    validate_public_speech_plan,
)
from .stance import build_stance_snapshot


INVARIANCE_SCHEMA_VERSION = "hidden_info_invariance.v1"
INVARIANCE_PROJECTION_VERSION = "hidden_info_projection.v1"
INVARIANCE_MODE = "unprivileged_villager_npc"
ACTOR_PROJECTION_NAMES = (
    "belief",
    "stance",
    "decision_context",
    "continuity",
    "fallback_plan",
)


class HiddenInfoInvarianceError(ValueError):
    """Raised when a matrix input cannot represent the M06-A boundary."""


def build_m06a_hidden_variants(
    game_state: rules.WolfGameState,
    *,
    hidden_wolf_id: int,
    hidden_good_id: int,
    alternate_fake_seer_id: int,
) -> dict[str, rules.WolfGameState]:
    """Generate canonical hidden-only mutations and one combined variant."""

    hidden_wolf = rules.get_character(game_state, hidden_wolf_id)
    hidden_good = rules.get_character(game_state, hidden_good_id)
    alternate_fake_seer = rules.get_character(
        game_state,
        alternate_fake_seer_id,
    )
    if hidden_wolf.is_player or hidden_wolf.role != "werewolf":
        raise HiddenInfoInvarianceError(
            "hidden_wolf_id must identify an NPC werewolf"
        )
    if (
        hidden_good.is_player
        or hidden_good.camp != "good"
        or hidden_good.role == "villager"
    ):
        raise HiddenInfoInvarianceError(
            "hidden_good_id must identify an NPC good power role"
        )
    if (
        alternate_fake_seer.is_player
        or alternate_fake_seer.role != "werewolf"
        or alternate_fake_seer.id == hidden_wolf.id
    ):
        raise HiddenInfoInvarianceError(
            "alternate_fake_seer_id must identify a different NPC werewolf"
        )
    if game_state.wolf_fake_seer_id != hidden_wolf.id:
        raise HiddenInfoInvarianceError(
            "hidden_wolf_id must identify the baseline designated fake seer"
        )
    if not game_state.public_claims:
        raise HiddenInfoInvarianceError(
            "claim-source invariance requires at least one public claim"
        )

    role_truth_swap = game_state.model_copy(deep=True)
    _swap_character_truth(
        role_truth_swap,
        hidden_wolf_id,
        hidden_good_id,
    )

    fake_seer_marker = game_state.model_copy(deep=True)
    fake_seer_marker.wolf_fake_seer_id = alternate_fake_seer_id

    role_and_designation_swap = role_truth_swap.model_copy(deep=True)
    role_and_designation_swap.wolf_fake_seer_id = hidden_good_id

    claim_source = game_state.model_copy(deep=True)
    _rewrite_internal_claim_sources(claim_source)

    unpublished_night = game_state.model_copy(deep=True)
    _inject_unpublished_night_result(
        unpublished_night,
        source_actor_id=hidden_wolf_id,
        attacked_target_id=hidden_good_id,
    )

    combined = role_and_designation_swap.model_copy(deep=True)
    _rewrite_internal_claim_sources(combined)
    _inject_unpublished_night_result(
        combined,
        source_actor_id=hidden_wolf_id,
        attacked_target_id=hidden_good_id,
    )

    return {
        "claim_source_rewrite": claim_source,
        "combined_hidden_mutation": combined,
        "fake_seer_marker_change": fake_seer_marker,
        "hidden_role_truth_swap": role_truth_swap,
        "role_and_designation_swap": role_and_designation_swap,
        "unpublished_night_result": unpublished_night,
    }


def build_hidden_info_invariance_report(
    baseline: rules.WolfGameState,
    variants: dict[str, rules.WolfGameState],
    *,
    observer_ids: list[int],
) -> dict[str, object]:
    """Compare every M06-A projection and return a deterministic report."""

    normalized_observer_ids = sorted(set(int(item) for item in observer_ids))
    if not variants:
        raise HiddenInfoInvarianceError(
            "hidden-info matrix requires at least one variant"
        )
    if not normalized_observer_ids:
        raise HiddenInfoInvarianceError(
            "hidden-info matrix requires at least one observer"
        )
    _validate_unprivileged_observers(baseline, normalized_observer_ids)

    baseline_public = build_public_invariance_projection(baseline)
    baseline_actors = {
        observer_id: build_actor_invariance_projection(
            baseline,
            observer_id,
        )
        for observer_id in normalized_observer_ids
    }

    variant_results: list[dict[str, object]] = []
    total_check_count = 0
    matched_check_count = 0
    for variant_id in sorted(variants):
        if not variant_id:
            raise HiddenInfoInvarianceError("variant ids must not be empty")
        variant = variants[variant_id]
        _validate_unprivileged_observers(variant, normalized_observer_ids)
        checks = [
            _compare_projection(
                variant_id,
                "public_state",
                baseline_public,
                build_public_invariance_projection(variant),
                observer_id=None,
            )
        ]
        for observer_id in normalized_observer_ids:
            variant_actor = build_actor_invariance_projection(
                variant,
                observer_id,
            )
            for projection_name in ACTOR_PROJECTION_NAMES:
                checks.append(
                    _compare_projection(
                        variant_id,
                        projection_name,
                        baseline_actors[observer_id][projection_name],
                        variant_actor[projection_name],
                        observer_id=observer_id,
                    )
                )

        mismatches = [check for check in checks if not check["matched"]]
        matched_count = len(checks) - len(mismatches)
        total_check_count += len(checks)
        matched_check_count += matched_count
        variant_results.append(
            {
                "variant_id": variant_id,
                "check_count": len(checks),
                "matched_check_count": matched_count,
                "passed": not mismatches,
                "mismatches": mismatches,
            }
        )

    return {
        "schema_version": INVARIANCE_SCHEMA_VERSION,
        "projection_version": INVARIANCE_PROJECTION_VERSION,
        "mode": INVARIANCE_MODE,
        "variant_count": len(variant_results),
        "observer_ids": normalized_observer_ids,
        "projection_names": ["public_state", *ACTOR_PROJECTION_NAMES],
        "check_count": total_check_count,
        "matched_check_count": matched_check_count,
        "passed": matched_check_count == total_check_count,
        "variants": variant_results,
    }


def build_public_invariance_projection(
    game_state: rules.WolfGameState,
) -> dict[str, object]:
    """Build the player-visible and public-decision state used by M06-A."""

    return {
        "schema_version": INVARIANCE_PROJECTION_VERSION,
        "day": game_state.day,
        "phase": game_state.phase,
        "characters": [
            item.model_dump(mode="json")
            for item in rules.build_character_views(game_state)
        ],
        "public_logs": list(game_state.public_logs),
        "public_intel": [
            item.model_dump(mode="json")
            for item in rules.build_public_intel_views(game_state)
        ],
        "player_private_info": rules.build_player_private_info_dict(game_state),
        "meeting": rules.build_day_meeting_view(game_state).model_dump(mode="json"),
        "sheriff": rules.build_sheriff_view(game_state).model_dump(mode="json"),
        "decision_signals": [
            item.model_dump(mode="json")
            for item in rules.build_public_decision_signals(game_state)
        ],
        "winner": game_state.winner,
    }


def build_actor_invariance_projection(
    game_state: rules.WolfGameState,
    observer_id: int,
) -> dict[str, object]:
    """Build one villager NPC's complete M04-B decision projection."""

    _validate_unprivileged_observers(game_state, [observer_id])
    working_state = game_state.model_copy(deep=True)
    working_state.phase = "DAY_MEETING"
    working_state.meeting = rules.DayMeetingState(
        day=working_state.day,
        direction="clockwise",
        order=[observer_id],
    )
    observer = rules.get_character(working_state, observer_id)
    decision_context = rules.build_public_speech_decision_context(
        working_state,
        observer,
        [],
        [],
    )
    belief_snapshot = build_belief_snapshot(
        working_state,
        observer_ids=[observer_id],
    )
    stance_snapshot = build_stance_snapshot(
        working_state,
        belief_snapshot=belief_snapshot,
    )
    continuity = rules.build_public_speech_continuity_context(
        working_state,
        observer,
        decision_context,
        mandatory_response=False,
    )
    fallback_target = next(
        (
            rules.get_character(working_state, target.id)
            for target in sorted(
                decision_context.legal_targets,
                key=lambda item: item.id,
            )
        ),
        None,
    )
    fallback_v2 = rules.build_public_speech_fallback_decision(
        decision_context,
        fallback_target,
        "",
    )
    fallback_v2 = rules.enrich_rule_generated_public_speech_plan(
        working_state,
        observer,
        fallback_v2,
        [],
    )
    fallback_plan = rules.align_rule_public_speech_plan_to_continuity(
        decision_context,
        continuity,
        fallback_v2,
    )
    plan_errors = validate_public_speech_plan(
        decision_context,
        fallback_plan,
    )
    plan_errors.extend(
        validate_public_speech_continuity(
            decision_context,
            continuity,
            fallback_plan,
        )
    )
    if plan_errors:
        raise HiddenInfoInvarianceError(
            "invariance fallback plan is invalid: " + "; ".join(plan_errors)
        )

    return {
        "belief": belief_snapshot,
        "stance": stance_snapshot,
        "decision_context": decision_context.model_dump(mode="json"),
        "continuity": continuity.model_dump(mode="json"),
        "fallback_plan": fallback_plan.model_dump(mode="json"),
    }


def _validate_unprivileged_observers(
    game_state: rules.WolfGameState,
    observer_ids: list[int],
) -> None:
    player = rules.get_character(game_state, game_state.player_character_id)
    if player.role != "villager" or player.camp != "good":
        raise HiddenInfoInvarianceError(
            "M06-A public projection requires an unprivileged villager player"
        )
    for observer_id in observer_ids:
        observer = rules.get_character(game_state, observer_id)
        if (
            observer.is_player
            or not observer.alive
            or observer.role != "villager"
            or observer.camp != "good"
        ):
            raise HiddenInfoInvarianceError(
                "M06-A observers must be living NPC villagers: "
                f"{observer_id}"
            )
        if game_state.sheriff_id == observer_id:
            raise HiddenInfoInvarianceError(
                "M06-A observers must not hold the sheriff badge: "
                f"{observer_id}"
            )


def _swap_character_truth(
    game_state: rules.WolfGameState,
    left_id: int,
    right_id: int,
) -> None:
    left = rules.get_character(game_state, left_id)
    right = rules.get_character(game_state, right_id)
    left.role, right.role = right.role, left.role
    left.camp, right.camp = right.camp, left.camp


def _rewrite_internal_claim_sources(game_state: rules.WolfGameState) -> None:
    for index, claim in enumerate(game_state.public_claims, start=1):
        claim.source = f"m06a_hidden_source_{index}"


def _inject_unpublished_night_result(
    game_state: rules.WolfGameState,
    *,
    source_actor_id: int,
    attacked_target_id: int,
) -> None:
    game_state.first_night_result_pending = True
    game_state.night_resolutions.append(
        rules.NightResolutionState(
            day=game_state.day,
            attacked_target_id=attacked_target_id,
            protected_ids=[],
            saved_target_id=None,
            poisoned_target_id=None,
            dead_character_ids=[attacked_target_id],
        )
    )
    game_state.pending_first_night_eliminations.append(
        rules.EliminationState(
            day=game_state.day,
            character_id=attacked_target_id,
            cause="night_kill",
            source_action="werewolf_kill",
            source_actor_ids=[source_actor_id],
            source_target_id=attacked_target_id,
        )
    )


def _compare_projection(
    variant_id: str,
    projection_name: str,
    baseline: object,
    variant: object,
    *,
    observer_id: Optional[int],
) -> dict[str, object]:
    baseline_digest = _payload_digest(baseline)
    variant_digest = _payload_digest(variant)
    matched = baseline_digest == variant_digest
    return {
        "variant_id": variant_id,
        "projection": projection_name,
        "observer_id": observer_id,
        "matched": matched,
        "baseline_digest": baseline_digest,
        "variant_digest": variant_digest,
        "first_difference": (
            None if matched else _first_difference_path(baseline, variant)
        ),
    }


def _payload_digest(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _first_difference_path(
    baseline: object,
    variant: object,
    path: str = "$",
) -> str:
    if type(baseline) is not type(variant):
        return path
    if isinstance(baseline, dict):
        baseline_keys = set(baseline)
        variant_keys = set(variant)
        if baseline_keys != variant_keys:
            changed_key = sorted(baseline_keys.symmetric_difference(variant_keys))[0]
            return f"{path}.{changed_key}"
        for key in sorted(baseline):
            nested_path = _first_difference_path(
                baseline[key],
                variant[key],
                f"{path}.{key}",
            )
            if nested_path:
                return nested_path
        return ""
    if isinstance(baseline, list):
        if len(baseline) != len(variant):
            return f"{path}.length"
        for index, (baseline_item, variant_item) in enumerate(
            zip(baseline, variant)
        ):
            nested_path = _first_difference_path(
                baseline_item,
                variant_item,
                f"{path}[{index}]",
            )
            if nested_path:
                return nested_path
        return ""
    return path if baseline != variant else ""


__all__ = [
    "ACTOR_PROJECTION_NAMES",
    "INVARIANCE_MODE",
    "INVARIANCE_PROJECTION_VERSION",
    "INVARIANCE_SCHEMA_VERSION",
    "HiddenInfoInvarianceError",
    "build_actor_invariance_projection",
    "build_hidden_info_invariance_report",
    "build_m06a_hidden_variants",
    "build_public_invariance_projection",
]
