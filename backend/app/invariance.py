"""Reusable hidden-information differential checks for Agent Town V3.1-G/H.

M06-A compares public state and unprivileged villager-NPC decision projections
across states that differ only in hidden internals. M06-B verifies that legal
role-private changes reach only authorized NPC projections. This is an offline
test tool: live API handlers and gameplay rules do not import this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
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
AUTHORIZATION_SCHEMA_VERSION = "hidden_info_authorization.v1"
AUTHORIZATION_MODE = "role_scoped_private_npc"
ACTOR_PROJECTION_NAMES = (
    "belief",
    "stance",
    "decision_context",
    "continuity",
    "fallback_plan",
)


class HiddenInfoInvarianceError(ValueError):
    """Raised when a matrix input cannot represent an M06 boundary."""


@dataclass(frozen=True)
class AuthorizedPrivateCase:
    """One hidden mutation plus its exact role-scoped actor expectations."""

    state: rules.WolfGameState
    authorization_kind: str
    required_changed_by_observer: dict[int, tuple[str, ...]]
    allowed_changed_by_observer: dict[int, tuple[str, ...]]
    excluded_observer_ids: tuple[int, ...] = ()


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


def build_m06b_authorized_cases(
    game_state: rules.WolfGameState,
    *,
    seer_id: int,
    seer_new_target_id: int,
    witch_id: int,
    witch_new_attack_target_id: int,
    wolf_member_out_id: int,
    wolf_member_in_id: int,
) -> dict[str, AuthorizedPrivateCase]:
    """Generate canonical private-fact changes for M06-B authorization checks."""

    _validate_unprivileged_player(game_state)
    seer = rules.get_character(game_state, seer_id)
    witch = rules.get_character(game_state, witch_id)
    seer_new_target = rules.get_character(game_state, seer_new_target_id)
    witch_new_target = rules.get_character(
        game_state,
        witch_new_attack_target_id,
    )
    wolf_member_out = rules.get_character(game_state, wolf_member_out_id)
    wolf_member_in = rules.get_character(game_state, wolf_member_in_id)
    if seer.is_player or seer.role != "seer":
        raise HiddenInfoInvarianceError("seer_id must identify the NPC seer")
    if witch.is_player or witch.role != "witch":
        raise HiddenInfoInvarianceError("witch_id must identify the NPC witch")
    if (
        seer_new_target.id == seer.id
        or not seer_new_target.alive
        or seer_new_target.role != "werewolf"
    ):
        raise HiddenInfoInvarianceError(
            "seer_new_target_id must identify a living werewolf target"
        )
    if witch_new_target.id == witch.id or not witch_new_target.alive:
        raise HiddenInfoInvarianceError(
            "witch_new_attack_target_id must identify another living character"
        )
    if (
        wolf_member_out.is_player
        or wolf_member_out.role != "werewolf"
        or wolf_member_out.id == game_state.wolf_fake_seer_id
    ):
        raise HiddenInfoInvarianceError(
            "wolf_member_out_id must identify a non-designated NPC werewolf"
        )
    if (
        wolf_member_in.is_player
        or wolf_member_in.role not in {"guard", "hunter"}
        or wolf_member_in.camp != "good"
    ):
        raise HiddenInfoInvarianceError(
            "wolf_member_in_id must identify an NPC guard or hunter"
        )

    seer_action_index = next(
        (
            index
            for index in range(len(game_state.night_actions) - 1, -1, -1)
            if game_state.night_actions[index].actor_id == seer.id
            and game_state.night_actions[index].action_type == "seer_check"
            and game_state.night_actions[index].target_id is not None
        ),
        None,
    )
    if seer_action_index is None:
        raise HiddenInfoInvarianceError(
            "M06-B requires one existing private NPC seer check"
        )
    baseline_seer_target = rules.get_character(
        game_state,
        int(game_state.night_actions[seer_action_index].target_id),
    )
    if (
        baseline_seer_target.camp != "good"
        or not baseline_seer_target.alive
        or baseline_seer_target.id == seer.id
        or baseline_seer_target.id == seer_new_target.id
    ):
        raise HiddenInfoInvarianceError(
            "the baseline seer check must target a different good character"
        )
    if baseline_seer_target.id == wolf_member_in.id:
        raise HiddenInfoInvarianceError(
            "wolf membership swap must not alter the canonical seer check truth"
        )

    witch_resolution_index = next(
        (
            index
            for index in range(len(game_state.night_resolutions) - 1, -1, -1)
            if game_state.night_resolutions[index].attacked_target_id is not None
        ),
        None,
    )
    if witch_resolution_index is None:
        raise HiddenInfoInvarianceError(
            "M06-B requires one unpublished witch-visible attack target"
        )
    baseline_attack_target_id = game_state.night_resolutions[
        witch_resolution_index
    ].attacked_target_id
    baseline_attack_target = rules.get_character(
        game_state,
        int(baseline_attack_target_id),
    )
    if (
        not baseline_attack_target.alive
        or baseline_attack_target.id == witch.id
        or baseline_attack_target.id == witch_new_target.id
    ):
        raise HiddenInfoInvarianceError(
            "the baseline and new witch attack targets must be living and distinct"
        )

    seer_change = game_state.model_copy(deep=True)
    seer_change.night_actions[seer_action_index].target_id = seer_new_target.id

    witch_change = game_state.model_copy(deep=True)
    witch_change.night_resolutions[
        witch_resolution_index
    ].attacked_target_id = witch_new_target.id

    wolf_change = game_state.model_copy(deep=True)
    _swap_character_truth(
        wolf_change,
        wolf_member_out.id,
        wolf_member_in.id,
    )
    remaining_wolf_ids = sorted(
        character.id
        for character in game_state.characters
        if (
            not character.is_player
            and character.alive
            and character.role == "werewolf"
            and character.id != wolf_member_out.id
        )
    )
    if not remaining_wolf_ids:
        raise HiddenInfoInvarianceError(
            "wolf-team authorization requires an unchanged NPC wolf observer"
        )

    all_actor_projections = tuple(ACTOR_PROJECTION_NAMES)
    return {
        "seer_private_check_change": AuthorizedPrivateCase(
            state=seer_change,
            authorization_kind="seer_private_check",
            required_changed_by_observer={
                seer.id: ("belief", "decision_context"),
            },
            allowed_changed_by_observer={seer.id: all_actor_projections},
        ),
        "witch_private_attack_change": AuthorizedPrivateCase(
            state=witch_change,
            authorization_kind="witch_private_attack",
            required_changed_by_observer={witch.id: ("belief",)},
            allowed_changed_by_observer={
                witch.id: (
                    "belief",
                    "stance",
                    "continuity",
                    "fallback_plan",
                ),
            },
        ),
        "wolf_team_membership_change": AuthorizedPrivateCase(
            state=wolf_change,
            authorization_kind="wolf_team_membership",
            required_changed_by_observer={
                observer_id: ("belief", "decision_context")
                for observer_id in remaining_wolf_ids
            },
            allowed_changed_by_observer={
                observer_id: all_actor_projections
                for observer_id in remaining_wolf_ids
            },
            excluded_observer_ids=(
                wolf_member_out.id,
                wolf_member_in.id,
            ),
        ),
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


def build_hidden_info_authorization_report(
    baseline: rules.WolfGameState,
    cases: dict[str, AuthorizedPrivateCase],
) -> dict[str, object]:
    """Verify that private fact changes affect only their authorized NPC roles."""

    if not cases:
        raise HiddenInfoInvarianceError(
            "hidden-info authorization requires at least one case"
        )
    _validate_unprivileged_player(baseline)
    baseline_observer_ids = sorted(
        character.id
        for character in baseline.characters
        if (
            not character.is_player
            and character.alive
            and character.id != baseline.sheriff_id
        )
    )
    if not baseline_observer_ids:
        raise HiddenInfoInvarianceError(
            "hidden-info authorization requires living NPC observers"
        )
    baseline_public = build_public_invariance_projection(baseline)
    baseline_actors = {
        observer_id: build_authorized_actor_projection(
            baseline,
            observer_id,
        )
        for observer_id in baseline_observer_ids
    }

    case_results: list[dict[str, object]] = []
    total_check_count = 0
    satisfied_check_count = 0
    for case_id in sorted(cases):
        if not case_id:
            raise HiddenInfoInvarianceError("authorization case ids must not be empty")
        case = cases[case_id]
        if not case.authorization_kind:
            raise HiddenInfoInvarianceError(
                "authorization kinds must not be empty"
            )
        _validate_unprivileged_player(case.state)
        excluded_observer_ids = sorted(set(case.excluded_observer_ids))
        if len(excluded_observer_ids) != len(case.excluded_observer_ids):
            raise HiddenInfoInvarianceError(
                "excluded authorization observers must be unique"
            )
        unknown_excluded_ids = sorted(
            set(excluded_observer_ids).difference(baseline_observer_ids)
        )
        if unknown_excluded_ids:
            raise HiddenInfoInvarianceError(
                "excluded authorization observers must exist in the baseline"
            )
        checked_observer_ids = [
            observer_id
            for observer_id in baseline_observer_ids
            if observer_id not in excluded_observer_ids
        ]
        required_changes = _normalize_projection_expectations(
            case.required_changed_by_observer,
            checked_observer_ids,
            "required",
        )
        allowed_changes = _normalize_projection_expectations(
            case.allowed_changed_by_observer,
            checked_observer_ids,
            "allowed",
        )
        if not required_changes:
            raise HiddenInfoInvarianceError(
                "each authorization case requires an authorized observer"
            )
        for observer_id, required_names in required_changes.items():
            if not required_names:
                raise HiddenInfoInvarianceError(
                    "authorized observers require at least one changed projection"
                )
            if not set(required_names).issubset(
                allowed_changes.get(observer_id, ())
            ):
                raise HiddenInfoInvarianceError(
                    "required projection changes must also be allowed"
                )

        checks = [
            _compare_authorization_projection(
                case_id,
                "public_state",
                baseline_public,
                build_public_invariance_projection(case.state),
                observer_id=None,
                expectation="unchanged",
            )
        ]
        observed_changed_by_observer: dict[str, list[str]] = {}
        for observer_id in checked_observer_ids:
            baseline_observer = rules.get_character(baseline, observer_id)
            variant_observer = rules.get_character(case.state, observer_id)
            if (
                baseline_observer.role != variant_observer.role
                or baseline_observer.camp != variant_observer.camp
            ):
                raise HiddenInfoInvarianceError(
                    "checked authorization observers must retain role and camp: "
                    f"{observer_id}"
                )
            variant_actor = build_authorized_actor_projection(
                case.state,
                observer_id,
            )
            observed_changed_names: list[str] = []
            for projection_name in ACTOR_PROJECTION_NAMES:
                if projection_name in required_changes.get(observer_id, ()):
                    expectation = "changed"
                elif projection_name in allowed_changes.get(observer_id, ()):
                    expectation = "optional_change"
                else:
                    expectation = "unchanged"
                check = _compare_authorization_projection(
                    case_id,
                    projection_name,
                    baseline_actors[observer_id][projection_name],
                    variant_actor[projection_name],
                    observer_id=observer_id,
                    expectation=expectation,
                )
                checks.append(check)
                if check["changed"]:
                    observed_changed_names.append(projection_name)
            if observer_id in allowed_changes:
                observed_changed_by_observer[str(observer_id)] = (
                    observed_changed_names
                )

        violations = [check for check in checks if not check["satisfied"]]
        satisfied_count = len(checks) - len(violations)
        total_check_count += len(checks)
        satisfied_check_count += satisfied_count
        case_results.append(
            {
                "case_id": case_id,
                "authorization_kind": case.authorization_kind,
                "authorized_observer_ids": sorted(allowed_changes),
                "excluded_observer_ids": excluded_observer_ids,
                "checked_observer_count": len(checked_observer_ids),
                "check_count": len(checks),
                "satisfied_check_count": satisfied_count,
                "observed_changed_by_observer": observed_changed_by_observer,
                "passed": not violations,
                "violations": violations,
            }
        )

    return {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "projection_version": INVARIANCE_PROJECTION_VERSION,
        "mode": AUTHORIZATION_MODE,
        "case_count": len(case_results),
        "baseline_observer_ids": baseline_observer_ids,
        "projection_names": ["public_state", *ACTOR_PROJECTION_NAMES],
        "check_count": total_check_count,
        "satisfied_check_count": satisfied_check_count,
        "passed": satisfied_check_count == total_check_count,
        "cases": case_results,
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
    return _build_actor_decision_projection(game_state, observer_id)


def build_authorized_actor_projection(
    game_state: rules.WolfGameState,
    observer_id: int,
) -> dict[str, object]:
    """Build one living NPC's role-aware M04-B decision projection."""

    _validate_role_scoped_observer(game_state, observer_id)
    return _build_actor_decision_projection(game_state, observer_id)


def _build_actor_decision_projection(
    game_state: rules.WolfGameState,
    observer_id: int,
) -> dict[str, object]:
    working_state = game_state.model_copy(deep=True)
    working_state.phase = "DAY_MEETING"
    working_state.meeting = rules.DayMeetingState(
        day=working_state.day,
        direction="clockwise",
        order=[observer_id],
    )
    observer = rules.get_character(working_state, observer_id)
    planned_claims = rules.plan_npc_public_claims(
        working_state,
        observer,
    )
    decision_context = rules.build_public_speech_decision_context(
        working_state,
        observer,
        [],
        planned_claims,
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
        mandatory_response=bool(
            rules.get_required_received_seer_check_signals(decision_context)
            or rules.get_wolf_teammate_black_check_sources(
                working_state,
                observer.id,
            )
        ),
    )
    fallback_target = rules.get_primary_claim_target(
        working_state,
        planned_claims,
    )
    if fallback_target is None:
        fallback_target = rules.choose_speech_focus_target(
            working_state,
            observer,
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
        planned_claims,
    )
    fallback_v2 = rules.enforce_wolf_story_fallback_plan(
        working_state,
        observer,
        decision_context,
        fallback_v2,
    )
    fallback_v2 = rules.enforce_received_seer_check_response_plan(
        working_state,
        observer,
        decision_context,
        fallback_v2,
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
        rules.validate_wolf_story_plan(
            working_state,
            observer,
            decision_context,
            fallback_plan,
        )
    )
    plan_errors.extend(
        rules.validate_wolf_coordination_plan(
            working_state,
            observer,
            fallback_plan,
        )
    )
    plan_errors.extend(
        rules.validate_received_seer_check_response_plan(
            decision_context,
            fallback_plan,
        )
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
    _validate_unprivileged_player(game_state)
    for observer_id in observer_ids:
        observer = rules.get_character(game_state, observer_id)
        if observer.role != "villager" or observer.camp != "good":
            raise HiddenInfoInvarianceError(
                "M06-A observers must be living NPC villagers: "
                f"{observer_id}"
            )
        _validate_living_non_sheriff_npc(game_state, observer_id)


def _validate_role_scoped_observer(
    game_state: rules.WolfGameState,
    observer_id: int,
) -> None:
    _validate_unprivileged_player(game_state)
    _validate_living_non_sheriff_npc(game_state, observer_id)


def _validate_unprivileged_player(game_state: rules.WolfGameState) -> None:
    player = rules.get_character(game_state, game_state.player_character_id)
    if player.role != "villager" or player.camp != "good":
        raise HiddenInfoInvarianceError(
            "hidden-info projections require an unprivileged villager player"
        )


def _validate_living_non_sheriff_npc(
    game_state: rules.WolfGameState,
    observer_id: int,
) -> None:
    observer = rules.get_character(game_state, observer_id)
    if observer.is_player or not observer.alive:
        raise HiddenInfoInvarianceError(
            "hidden-info observers must be living NPCs: "
            f"{observer_id}"
        )
    if game_state.sheriff_id == observer_id:
        raise HiddenInfoInvarianceError(
            "hidden-info observers must not hold the sheriff badge: "
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


def _normalize_projection_expectations(
    expectations: dict[int, tuple[str, ...]],
    checked_observer_ids: list[int],
    label: str,
) -> dict[int, tuple[str, ...]]:
    checked_observer_id_set = set(checked_observer_ids)
    normalized: dict[int, tuple[str, ...]] = {}
    for raw_observer_id, raw_projection_names in expectations.items():
        observer_id = int(raw_observer_id)
        if observer_id not in checked_observer_id_set:
            raise HiddenInfoInvarianceError(
                f"{label} authorization observer is not checkable: {observer_id}"
            )
        projection_names = tuple(sorted(set(raw_projection_names)))
        if len(projection_names) != len(raw_projection_names):
            raise HiddenInfoInvarianceError(
                f"{label} authorization projections must be unique"
            )
        unknown_names = sorted(
            set(projection_names).difference(ACTOR_PROJECTION_NAMES)
        )
        if unknown_names:
            raise HiddenInfoInvarianceError(
                f"unknown {label} authorization projections: "
                + ", ".join(unknown_names)
            )
        normalized[observer_id] = projection_names
    return normalized


def _compare_authorization_projection(
    case_id: str,
    projection_name: str,
    baseline: object,
    variant: object,
    *,
    observer_id: Optional[int],
    expectation: str,
) -> dict[str, object]:
    baseline_digest = _payload_digest(baseline)
    variant_digest = _payload_digest(variant)
    changed = baseline_digest != variant_digest
    if expectation == "changed":
        satisfied = changed
    elif expectation == "unchanged":
        satisfied = not changed
    elif expectation == "optional_change":
        satisfied = True
    else:
        raise HiddenInfoInvarianceError(
            f"unknown authorization expectation: {expectation}"
        )
    return {
        "case_id": case_id,
        "projection": projection_name,
        "observer_id": observer_id,
        "expectation": expectation,
        "changed": changed,
        "satisfied": satisfied,
        "baseline_digest": baseline_digest,
        "variant_digest": variant_digest,
        "first_difference": (
            _first_difference_path(baseline, variant) if changed else None
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
    "AUTHORIZATION_MODE",
    "AUTHORIZATION_SCHEMA_VERSION",
    "INVARIANCE_MODE",
    "INVARIANCE_PROJECTION_VERSION",
    "INVARIANCE_SCHEMA_VERSION",
    "AuthorizedPrivateCase",
    "HiddenInfoInvarianceError",
    "build_actor_invariance_projection",
    "build_authorized_actor_projection",
    "build_hidden_info_authorization_report",
    "build_hidden_info_invariance_report",
    "build_m06a_hidden_variants",
    "build_m06b_authorized_cases",
    "build_public_invariance_projection",
]
