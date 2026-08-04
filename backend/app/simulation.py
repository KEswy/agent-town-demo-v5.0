"""Deterministic, no-HTTP game simulation for Agent Town V4.

The driver calls the existing rule entry points directly. It never starts an
ASGI server, enables an LLM, initializes vector RAG, or writes town-chat
memory. The automated player policy consumes only the player's own role and
role knowledge plus public state.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections import Counter
from typing import Optional

from . import main as rules
from .llm_fingerprinting import (
    EXPERIMENT_FINGERPRINT_SCHEMA_VERSION,
    RULE_ONLY_EXECUTION_MODE,
    build_experiment_fingerprint,
    build_llm_config_fingerprint,
)
from .belief import (
    BELIEF_SCHEMA_VERSION,
    BeliefTraceRecorder,
    aggregate_belief_traces,
)
from .simulation_metrics import (
    METRICS_SCHEMA_VERSION,
    PLAYER_PERFORMANCE_SCHEMA_VERSION,
    aggregate_batch_metrics,
    aggregate_player_benchmark_metrics,
    build_game_metrics,
)
from .player_strategy import (
    BENCHMARK_PLAYER_ROLES,
    DEFAULT_PLAYER_STRATEGY,
    PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION,
    PLAYER_STRATEGY_POLICY_VERSIONS,
    PLAYER_STRATEGY_SCHEMA_VERSION,
    PLAYER_STRATEGY_TIERS,
    best_candidate_ids,
    build_player_strategy_context,
    build_player_strategy_descriptor,
    choose_witch_action,
    lawful_target_constraints,
    normalize_player_strategy,
    should_run_for_sheriff,
)
from .npc_decision import (
    PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION,
    PUBLIC_SPEECH_PLAN_SCHEMA_VERSION,
    SpeechContinuityReason,
)
from .npc_policy import (
    NPC_POLICY_ENTROPY_GUARD_VERSION,
    NPC_POLICY_FEATURE_SCHEMA_VERSION,
    NPC_POLICY_OBSERVATION_SCHEMA_VERSION,
    NPC_POLICY_TRACE_SCHEMA_VERSION,
    capture_policy_traces,
)
from .stance import (
    STANCE_SCHEMA_VERSION,
    StanceTraceRecorder,
    aggregate_stance_traces,
)
from .speech_quality import (
    NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION,
    NPC_SPEECH_QUALITY_SCHEMA_VERSION,
    aggregate_npc_speech_quality,
    build_npc_speech_quality,
)
from .vote_calibration import (
    VOTE_CALIBRATION_SCHEMA_VERSION,
    VOTE_CALIBRATION_SUMMARY_VERSION,
    VoteCalibrationTraceRecorder,
    aggregate_vote_calibration_traces,
)


SIMULATION_SCHEMA_VERSION = "agent_town_simulation.v18"
BATCH_SCHEMA_VERSION = "agent_town_simulation_batch.v18"
GAMEPLAY_DIGEST_PROJECTION_VERSION = "agent_town_simulation.v15"
PLAYER_BENCHMARK_SCHEMA_VERSION = "agent_town_player_benchmark.v1"
PLAYER_DECISION_TRACE_SCHEMA_VERSION = "player_decision_trace.v1"
PLAYER_POLICY_VERSION = PLAYER_STRATEGY_POLICY_VERSIONS[
    DEFAULT_PLAYER_STRATEGY
]
SPEECH_CONTINUITY_METRICS_VERSION = "speech_continuity_metrics.v1"
DEFAULT_MAX_DAYS = 20
DEFAULT_MAX_STEPS = 5_000
NPC_POLICY_MODES = ("rule", "shadow", "local")


class SimulationError(RuntimeError):
    """Raised when a headless game cannot reach a legal terminal state."""


def run_rule_simulation(
    seed: int,
    *,
    player_role: str = "random",
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
    max_days: int = DEFAULT_MAX_DAYS,
    max_steps: int = DEFAULT_MAX_STEPS,
    capture_beliefs: bool = True,
    capture_stances: bool = True,
    capture_vote_calibration: bool = True,
    capture_event_log: bool = True,
    capture_npc_policy: bool = False,
    npc_policy_mode: str = "rule",
) -> dict[str, object]:
    """Run one complete rule-only game and return a normalized result."""

    if seed < 0 or seed > rules.MAX_GAME_RANDOM_SEED:
        raise ValueError(
            f"seed must be between 0 and {rules.MAX_GAME_RANDOM_SEED}"
        )
    if max_days < 1 or max_steps < 1:
        raise ValueError("max_days and max_steps must be positive")

    normalized_strategy = normalize_player_strategy(player_strategy)
    game_id = f"simulation_{seed}_{normalized_strategy}"
    request = rules.GameStartRequest(
        player_name="模拟玩家",
        player_role=player_role,
        enable_llm=False,
        enable_rag=False,
        npc_policy_mode=npc_policy_mode,
    )
    game_state = rules.create_wolf_game_state(
        request,
        game_id=game_id,
        random_seed=seed,
    )

    with rules.GAME_LOCK:
        if game_id in rules.GAME_STORE:
            raise SimulationError(f"simulation game id is already active: {game_id}")
        rules.GAME_STORE[game_id] = game_state

    phase_trace: list[str] = []
    npc_policy_trace: list[dict[str, object]] = []
    belief_recorder = BeliefTraceRecorder() if capture_beliefs else None
    stance_recorder = (
        StanceTraceRecorder()
        if capture_beliefs and capture_stances
        else None
    )
    vote_calibration_recorder = (
        VoteCalibrationTraceRecorder()
        if capture_vote_calibration
        else None
    )
    if belief_recorder is not None:
        belief_snapshot = belief_recorder.capture(game_state)
        if stance_recorder is not None and belief_snapshot is not None:
            stance_recorder.capture(game_state, belief_snapshot)
    try:
        for _step in range(max_steps):
            phase_trace.append(f"day:{game_state.day}:{game_state.phase}")
            if game_state.day > max_days:
                raise SimulationError(
                    f"seed {seed} exceeded max_days={max_days} in {game_state.phase}"
                )
            if game_state.phase == "GAME_OVER":
                break
            pending_vote_capture = (
                vote_calibration_recorder.capture_before_vote(game_state)
                if vote_calibration_recorder is not None
                else None
            )
            if capture_npc_policy:
                with capture_policy_traces(npc_policy_trace.append):
                    _advance_one_phase(game_state, normalized_strategy)
            else:
                _advance_one_phase(game_state, normalized_strategy)
            if vote_calibration_recorder is not None:
                vote_calibration_recorder.capture_after_vote(
                    game_state,
                    pending_vote_capture,
                )
            if belief_recorder is not None:
                belief_snapshot = belief_recorder.capture(game_state)
                if stance_recorder is not None and belief_snapshot is not None:
                    stance_recorder.capture(game_state, belief_snapshot)
        else:
            raise SimulationError(
                f"seed {seed} exceeded max_steps={max_steps} in {game_state.phase}"
            )

        validate_completed_simulation(game_state)
        event_log = rules.build_game_rule_event_log(game_state)
        replay_report = rules.replay_game_rule_events(
            game_id=game_state.game_id,
            events=event_log.events,
            expected_projection=rules.build_rule_replay_projection(game_state),
        )
        return build_simulation_result(
            game_state,
            phase_trace,
            belief_trace=(
                belief_recorder.build_result()
                if belief_recorder is not None
                else None
            ),
            stance_trace=(
                stance_recorder.build_result()
                if stance_recorder is not None
                else None
            ),
            vote_calibration_trace=(
                vote_calibration_recorder.build_result()
                if vote_calibration_recorder is not None
                else None
            ),
            player_strategy=normalized_strategy,
            event_log=event_log,
            replay_report=replay_report,
            capture_event_log=capture_event_log,
            npc_policy_trace=(
                npc_policy_trace if capture_npc_policy else None
            ),
        )
    finally:
        with rules.GAME_LOCK:
            rules.GAME_STORE.pop(game_id, None)


def run_rule_simulation_batch(
    start_seed: int,
    games: int,
    *,
    player_role: str = "random",
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
    max_days: int = DEFAULT_MAX_DAYS,
    max_steps: int = DEFAULT_MAX_STEPS,
    capture_beliefs: bool = True,
    capture_stances: bool = True,
    capture_vote_calibration: bool = True,
    capture_event_logs: bool = False,
    capture_npc_policy: bool = False,
    npc_policy_mode: str = "rule",
) -> dict[str, object]:
    """Run sequential seeds and return deterministic per-game and aggregate data."""

    if games < 1:
        raise ValueError("games must be positive")
    final_seed = start_seed + games - 1
    if start_seed < 0 or final_seed > rules.MAX_GAME_RANDOM_SEED:
        raise ValueError(
            f"seed range must stay between 0 and {rules.MAX_GAME_RANDOM_SEED}"
        )

    normalized_strategy = normalize_player_strategy(player_strategy)
    results = [
        run_rule_simulation(
            start_seed + offset,
            player_role=player_role,
            player_strategy=normalized_strategy,
            max_days=max_days,
            max_steps=max_steps,
            capture_beliefs=capture_beliefs,
            capture_stances=capture_stances,
            capture_vote_calibration=capture_vote_calibration,
            capture_event_log=capture_event_logs,
            capture_npc_policy=capture_npc_policy,
            npc_policy_mode=npc_policy_mode,
        )
        for offset in range(games)
    ]
    winner_counts = Counter(str(result["winner"]) for result in results)
    total_days = sum(int(result["total_days"]) for result in results)
    continuity_reason_counts: Counter[str] = Counter()
    for result in results:
        continuity_reason_counts.update(
            {
                str(reason): int(count)
                for reason, count in result["speech_continuity"][
                    "reason_counts"
                ].items()
            }
        )
    controlled_speech_count = sum(
        int(result["speech_continuity"]["controlled_speech_count"])
        for result in results
    )
    experiment_fingerprint = results[0]["experiment_fingerprint"]
    if any(
        result["experiment_fingerprint"] != experiment_fingerprint
        for result in results
    ):
        raise SimulationError(
            "one batch cannot mix experiment configuration fingerprints"
        )
    report: dict[str, object] = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
        "metrics_schema_version": METRICS_SCHEMA_VERSION,
        "belief_schema_version": BELIEF_SCHEMA_VERSION,
        "stance_schema_version": STANCE_SCHEMA_VERSION,
        "speech_continuity_schema_version": SPEECH_CONTINUITY_METRICS_VERSION,
        "npc_speech_quality_schema_version": NPC_SPEECH_QUALITY_SCHEMA_VERSION,
        "npc_speech_quality_batch_schema_version": (
            NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION
        ),
        "vote_calibration_schema_version": VOTE_CALIBRATION_SCHEMA_VERSION,
        "vote_calibration_summary_version": VOTE_CALIBRATION_SUMMARY_VERSION,
        "npc_policy_trace_schema_version": NPC_POLICY_TRACE_SCHEMA_VERSION,
        "npc_policy_observation_schema_version": (
            NPC_POLICY_OBSERVATION_SCHEMA_VERSION
        ),
        "npc_policy_feature_schema_version": NPC_POLICY_FEATURE_SCHEMA_VERSION,
        "player_strategy_schema_version": PLAYER_STRATEGY_SCHEMA_VERSION,
        "player_strategy_context_schema_version": (
            PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION
        ),
        "event_schema_version": rules.GAME_EVENT_SCHEMA_VERSION,
        "event_log_schema_version": rules.GAME_EVENT_LOG_SCHEMA_VERSION,
        "replay_schema_version": rules.GAME_REPLAY_SCHEMA_VERSION,
        "ruleset_version": rules.GAME_RULESET_VERSION,
        "experiment_fingerprint_schema_version": (
            EXPERIMENT_FINGERPRINT_SCHEMA_VERSION
        ),
        "experiment_fingerprint": experiment_fingerprint,
        "player_strategy": build_player_strategy_descriptor(
            normalized_strategy
        ),
        "player_policy_version": PLAYER_STRATEGY_POLICY_VERSIONS[
            normalized_strategy
        ],
        "npc_policy_mode": npc_policy_mode,
        "npc_policy_descriptors": results[0]["npc_policy_descriptors"],
        "trace_capture": {
            "beliefs": capture_beliefs,
            "stances": capture_beliefs and capture_stances,
            "vote_calibration": capture_vote_calibration,
            "event_logs": capture_event_logs,
            "npc_policy": capture_npc_policy,
        },
        "start_seed": start_seed,
        "games_requested": games,
        "games_completed": len(results),
        "player_role": player_role,
        "summary": {
            "winner_counts": {
                "good": winner_counts.get("good", 0),
                "werewolf": winner_counts.get("werewolf", 0),
            },
            "average_days": round(total_days / len(results), 4),
            "replays_verified": sum(
                1 for result in results if result["replay"]["verified"]
            ),
            "events_recorded": sum(
                int(result["event_summary"]["event_count"])
                for result in results
            ),
        },
        "metrics": aggregate_batch_metrics(results),
        "belief_summary": (
            aggregate_belief_traces(results)
            if capture_beliefs
            else None
        ),
        "stance_summary": (
            aggregate_stance_traces(results)
            if capture_beliefs and capture_stances
            else None
        ),
        "speech_continuity_summary": {
            "schema_version": SPEECH_CONTINUITY_METRICS_VERSION,
            "continuity_schema_version": PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION,
            "plan_schema_version": PUBLIC_SPEECH_PLAN_SCHEMA_VERSION,
            "controlled_speech_count": controlled_speech_count,
            "reason_counts": {
                reason.value: continuity_reason_counts.get(reason.value, 0)
                for reason in SpeechContinuityReason
            },
        },
        "npc_speech_quality_summary": aggregate_npc_speech_quality(
            [result["npc_speech_quality"] for result in results]
        ).model_dump(mode="json"),
        "vote_calibration_summary": (
            aggregate_vote_calibration_traces(results)
            if capture_vote_calibration
            else None
        ),
        "event_logs_included": capture_event_logs,
        "games": results,
    }
    report["artifact_digest"] = _payload_digest(report)
    return report


def run_player_strategy_benchmark(
    start_seed: int,
    seeds_per_role: int,
    *,
    strategies: Optional[list[str]] = None,
    player_roles: Optional[list[str]] = None,
    max_days: int = DEFAULT_MAX_DAYS,
    max_steps: int = DEFAULT_MAX_STEPS,
    capture_beliefs: bool = False,
    capture_stances: bool = False,
    capture_vote_calibration: bool = False,
    capture_event_logs: bool = False,
) -> dict[str, object]:
    """Run identical seed/role cohorts across two or more player strategies."""

    if seeds_per_role < 1:
        raise ValueError("seeds_per_role must be positive")
    final_seed = start_seed + seeds_per_role - 1
    if start_seed < 0 or final_seed > rules.MAX_GAME_RANDOM_SEED:
        raise ValueError(
            f"seed range must stay between 0 and {rules.MAX_GAME_RANDOM_SEED}"
        )

    strategy_order = [
        normalize_player_strategy(strategy)
        for strategy in (
            list(PLAYER_STRATEGY_TIERS)
            if strategies is None
            else strategies
        )
    ]
    if len(strategy_order) < 2 or len(set(strategy_order)) != len(
        strategy_order
    ):
        raise ValueError("benchmark requires at least two unique strategies")
    role_order = (
        list(BENCHMARK_PLAYER_ROLES)
        if player_roles is None
        else [str(role) for role in player_roles]
    )
    if (
        not role_order
        or len(set(role_order)) != len(role_order)
        or any(role not in BENCHMARK_PLAYER_ROLES for role in role_order)
    ):
        raise ValueError("benchmark player roles must be unique fixed roles")

    results: list[dict[str, object]] = []
    cohort_layouts: dict[tuple[int, str], str] = {}
    for player_role in role_order:
        for offset in range(seeds_per_role):
            seed = start_seed + offset
            for strategy in strategy_order:
                result = run_rule_simulation(
                    seed,
                    player_role=player_role,
                    player_strategy=strategy,
                    max_days=max_days,
                    max_steps=max_steps,
                    capture_beliefs=capture_beliefs,
                    capture_stances=capture_stances,
                    capture_vote_calibration=capture_vote_calibration,
                    capture_event_log=capture_event_logs,
                )
                cohort_key = (seed, player_role)
                layout_digest = str(result["initial_layout_digest"])
                expected_layout = cohort_layouts.setdefault(
                    cohort_key,
                    layout_digest,
                )
                if layout_digest != expected_layout:
                    raise SimulationError(
                        "player strategies changed the initial role layout "
                        f"for seed={seed}, role={player_role}"
                    )
                results.append(result)

    metrics = aggregate_player_benchmark_metrics(
        results,
        strategy_order=strategy_order,
    )
    report: dict[str, object] = {
        "schema_version": PLAYER_BENCHMARK_SCHEMA_VERSION,
        "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
        "metrics_schema_version": METRICS_SCHEMA_VERSION,
        "player_performance_schema_version": (
            PLAYER_PERFORMANCE_SCHEMA_VERSION
        ),
        "player_strategy_schema_version": PLAYER_STRATEGY_SCHEMA_VERSION,
        "player_strategy_context_schema_version": (
            PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION
        ),
        "event_schema_version": rules.GAME_EVENT_SCHEMA_VERSION,
        "event_log_schema_version": rules.GAME_EVENT_LOG_SCHEMA_VERSION,
        "replay_schema_version": rules.GAME_REPLAY_SCHEMA_VERSION,
        "ruleset_version": rules.GAME_RULESET_VERSION,
        "start_seed": start_seed,
        "seeds_per_role": seeds_per_role,
        "player_roles": role_order,
        "strategies": [
            build_player_strategy_descriptor(strategy)
            for strategy in strategy_order
        ],
        "cohorts_requested": seeds_per_role * len(role_order),
        "cohorts_completed": len(cohort_layouts),
        "games_requested": (
            seeds_per_role * len(role_order) * len(strategy_order)
        ),
        "games_completed": len(results),
        "trace_capture": {
            "beliefs": capture_beliefs,
            "stances": capture_beliefs and capture_stances,
            "vote_calibration": capture_vote_calibration,
            "event_logs": capture_event_logs,
        },
        "metrics": metrics,
        "games": results,
    }
    report["benchmark_digest"] = _payload_digest(report)
    return report


def _advance_one_phase(
    game_state: rules.WolfGameState,
    player_strategy: str,
) -> None:
    phase = game_state.phase
    if phase == "NIGHT":
        _submit_player_night_action(game_state, player_strategy)
        rules.resolve_night(rules.NightResolveRequest(game_id=game_state.game_id))
        return
    if phase == "HUNTER_SHOT":
        target_id = _choose_public_player_target(
            game_state,
            "hunter_shot",
            player_strategy=player_strategy,
        )
        rules.resolve_hunter_shot(
            rules.HunterShotRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                target_id=target_id,
            )
        )
        return
    if phase == "SHERIFF_SIGNUP":
        player = _player(game_state)
        context = build_player_strategy_context(game_state)
        rules.submit_sheriff_signup(
            rules.SheriffSignupRequest(
                game_id=game_state.game_id,
                character_id=player.id,
                run_for_sheriff=should_run_for_sheriff(
                    context,
                    player_strategy,
                ),
            )
        )
        return
    if phase in {"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"}:
        speaker_id = rules.get_current_sheriff_speaker_id(game_state)
        if speaker_id is None:
            raise SimulationError(f"{phase} has no current speaker")
        speaker = rules.get_character(game_state, speaker_id)
        request = rules.SheriffSpeechRequest(
            game_id=game_state.game_id,
            character_id=speaker.id,
            speech=(
                _build_player_sheriff_speech(
                    game_state,
                    player_strategy,
                )
                if speaker.is_player
                else ""
            ),
            badge_flow=(
                _build_player_sheriff_badge_flow(
                    game_state,
                    player_strategy,
                )
                if speaker.is_player
                else None
            ),
        )
        if speaker.is_player:
            rules.submit_player_sheriff_speech(request)
        else:
            rules.generate_npc_sheriff_campaign_speech(request)
        return
    if phase == "SHERIFF_WITHDRAWAL":
        rules.submit_sheriff_withdrawal(
            rules.SheriffWithdrawalRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                withdraw=False,
            )
        )
        return
    if phase in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"}:
        rules.submit_and_resolve_sheriff_vote(
            rules.SheriffVoteRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                target_id=_choose_player_sheriff_vote(
                    game_state,
                    player_strategy,
                ),
            )
        )
        return
    if phase == "MEETING_ORDER":
        side = rules.deterministic_game_choice(
            game_state,
            ["left", "right"],
            (
                "simulation_player_meeting_side"
                if player_strategy == DEFAULT_PLAYER_STRATEGY
                else f"simulation_player_meeting_side:{player_strategy}"
            ),
        )
        rules.submit_sheriff_meeting_order(
            rules.SheriffMeetingOrderRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                side=side,
            )
        )
        return
    if phase == "DAY_MEETING":
        speaker_id = rules.get_current_meeting_speaker_id(game_state)
        if speaker_id is None:
            raise SimulationError("DAY_MEETING has no current speaker")
        speaker = rules.get_character(game_state, speaker_id)
        if speaker.is_player:
            target_id = _choose_public_player_target(
                game_state,
                "day_speech",
                player_strategy=player_strategy,
            )
            rules.submit_player_speech(
                rules.PlayerSpeechRequest(
                    game_id=game_state.game_id,
                    character_id=speaker.id,
                    speech=_build_player_day_speech(
                        game_state,
                        target_id,
                    ),
                    temporary_nomination_target_id=(
                        target_id if game_state.sheriff_id == speaker.id else None
                    ),
                )
            )
        else:
            rules.generate_npc_speech(
                rules.NpcSpeechRequest(
                    game_id=game_state.game_id,
                    character_id=speaker.id,
                )
            )
        return
    if phase == "SHERIFF_NOMINATION":
        target_id = _choose_public_player_target(
            game_state,
            "sheriff_nomination",
            player_strategy=player_strategy,
        )
        if target_id is None:
            raise SimulationError("player sheriff has no legal nomination target")
        rules.submit_sheriff_nomination(
            rules.SheriffNominationRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                target_id=target_id,
            )
        )
        return
    if phase == "FREE_ACTIVITY":
        rules.end_free_activity(
            rules.EndFreeActivityRequest(game_id=game_state.game_id)
        )
        return
    if phase == "VOTE":
        player = _player(game_state)
        target_id = (
            _choose_public_player_target(
                game_state,
                "exile_vote",
                player_strategy=player_strategy,
            )
            if player.alive
            else None
        )
        rules.submit_and_resolve_all_votes(
            rules.PlayerVoteRequest(
                game_id=game_state.game_id,
                character_id=player.id,
                target_id=target_id,
                reason=(
                    "模拟玩家依据当前公开发言、动作与票型作出选择。"
                    if target_id is not None
                    else ""
                ),
            )
        )
        return
    if phase == "BADGE_TRANSFER":
        target_id = _choose_public_player_target(
            game_state,
            "badge_transfer",
            player_strategy=player_strategy,
        )
        rules.submit_badge_transfer(
            rules.BadgeTransferRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                target_id=target_id,
            )
        )
        return
    raise SimulationError(f"unsupported simulation phase: {phase}")


def _submit_player_night_action(
    game_state: rules.WolfGameState,
    player_strategy: str,
) -> None:
    player = _player(game_state)
    if not player.alive:
        return
    action_type, target_id = _choose_player_night_action(
        game_state,
        player,
        player_strategy,
    )
    rules.submit_night_action(
        rules.NightActionRequest(
            game_id=game_state.game_id,
            character_id=player.id,
            action_type=action_type,
            target_id=target_id,
        )
    )


def _choose_player_night_action(
    game_state: rules.WolfGameState,
    player: rules.CharacterState,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
) -> tuple[str, Optional[int]]:
    normalized_strategy = normalize_player_strategy(player_strategy)
    context = build_player_strategy_context(game_state)
    alive_ids = [
        character.id
        for character in game_state.characters
        if character.alive and character.id != player.id
    ]
    if player.role == "werewolf":
        teammate_ids, _priority_ids = lawful_target_constraints(context)
        target_ids = [
            character_id
            for character_id in alive_ids
            if character_id not in teammate_ids
        ]
        best_ids = best_candidate_ids(
            context,
            target_ids,
            strategy=normalized_strategy,
            purpose="night_werewolf_kill",
        )
        return "werewolf_kill", _policy_choice(
            game_state,
            best_ids,
            "night_werewolf_kill",
            player_strategy=normalized_strategy,
        )
    if player.role == "seer":
        checked_ids = {
            int(action.target_id)
            for action in game_state.night_actions
            if action.actor_id == player.id
            and action.action_type == "seer_check"
            and action.target_id is not None
        }
        target_ids = alive_ids
        if normalized_strategy != "beginner":
            target_ids = [
                character_id
                for character_id in alive_ids
                if character_id not in checked_ids
            ] or alive_ids
        best_ids = best_candidate_ids(
            context,
            target_ids,
            strategy=normalized_strategy,
            purpose="night_seer_check",
        )
        return "seer_check", _policy_choice(
            game_state,
            best_ids,
            "night_seer_check",
            player_strategy=normalized_strategy,
        )
    if player.role == "guard":
        resources = rules.get_role_resources(game_state, player.id)
        last_target_id = resources.get("last_protected_target_id")
        last_day = int(resources.get("last_protected_day", 0))
        target_ids = [
            character.id
            for character in game_state.characters
            if character.alive
            and not (
                character.id == last_target_id
                and last_day == game_state.day - 1
            )
        ]
        best_ids = best_candidate_ids(
            context,
            target_ids,
            strategy=normalized_strategy,
            purpose="night_guard_protect",
        )
        return "guard_protect", _policy_choice(
            game_state,
            best_ids,
            "night_guard_protect",
            player_strategy=normalized_strategy,
        )
    if player.role == "witch":
        poison_candidate_ids = [
            character_id
            for character_id in alive_ids
            if character_id != player.id
        ]
        action_type, fixed_target_id, ranked_ids = choose_witch_action(
            context,
            strategy=normalized_strategy,
            poison_candidate_ids=poison_candidate_ids,
        )
        if fixed_target_id is not None:
            return action_type, fixed_target_id
        if ranked_ids:
            return action_type, _policy_choice(
                game_state,
                ranked_ids,
                "night_witch_poison",
                player_strategy=normalized_strategy,
            )
    return "none", None


def _choose_player_sheriff_vote(
    game_state: rules.WolfGameState,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
) -> Optional[int]:
    election = game_state.sheriff_election
    if election is None:
        raise SimulationError("sheriff vote has no election state")
    player = _player(game_state)
    if not player.alive or player.id in set(election.candidates):
        return None
    candidate_ids = rules.get_active_sheriff_candidates(game_state)
    if not candidate_ids:
        return None
    normalized_strategy = normalize_player_strategy(player_strategy)
    context = build_player_strategy_context(game_state)
    best_ids = best_candidate_ids(
        context,
        candidate_ids,
        strategy=normalized_strategy,
        purpose="sheriff_vote",
    )
    return _policy_choice(
        game_state,
        best_ids,
        "sheriff_vote",
        player_strategy=normalized_strategy,
    )


def _choose_public_player_target(
    game_state: rules.WolfGameState,
    purpose: str,
    *,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
) -> Optional[int]:
    normalized_strategy = normalize_player_strategy(player_strategy)
    player = _player(game_state)
    if (
        purpose == "exile_vote"
        and game_state.sheriff_id == player.id
        and game_state.meeting is not None
        and game_state.meeting.nomination_target_id is not None
    ):
        return game_state.meeting.nomination_target_id

    candidates = [
        character
        for character in game_state.characters
        if character.alive and character.id != player.id
    ]
    if not candidates:
        return None

    context = build_player_strategy_context(game_state)
    excluded_ids, priority_ids = lawful_target_constraints(context)
    if normalized_strategy == "expert" and purpose == "badge_transfer":
        lawful_private = context["lawful_private"]
        if not isinstance(lawful_private, dict):
            raise SimulationError("player strategy context is invalid")
        if player.role == "werewolf":
            teammate_ids = {
                int(item)
                for item in lawful_private["wolf_teammate_ids"]
            }
            priority_ids = teammate_ids
            excluded_ids = set()
        elif player.role == "seer":
            priority_ids = {
                int(check["target_id"])
                for check in lawful_private["seer_checks"]
                if isinstance(check, dict) and check["result"] == "good"
            }
            excluded_ids = {
                int(check["target_id"])
                for check in lawful_private["seer_checks"]
                if isinstance(check, dict)
                and check["result"] == "werewolf"
            }
        else:
            excluded_ids = set()
            priority_ids = set()

    eligible = [
        character
        for character in candidates
        if character.id not in excluded_ids
    ] or candidates
    prioritized = [
        character for character in eligible if character.id in priority_ids
    ]
    if prioritized:
        eligible = prioritized

    best_ids = best_candidate_ids(
        context,
        [character.id for character in eligible],
        strategy=normalized_strategy,
        purpose=purpose,
    )
    return _policy_choice(
        game_state,
        best_ids,
        purpose,
        player_strategy=normalized_strategy,
    )


def _build_player_sheriff_speech(
    game_state: rules.WolfGameState,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
) -> str:
    player = _player(game_state)
    latest_check = rules.get_latest_seer_check(game_state, player.id)
    if player.role == "seer" and latest_check is not None:
        target = rules.get_character(game_state, int(latest_check["target_id"]))
        result = "狼人" if latest_check["result"] == "werewolf" else "好人"
        return (
            f"我是预言家，我查验了{target.id}号{target.name}，结果是{result}。"
            "我会继续用公开发言和票型验证判断。"
        )
    target_id = _choose_public_player_target(
        game_state,
        "sheriff_speech",
        player_strategy=player_strategy,
    )
    if target_id is None:
        return "我上警是为了整理公开信息，会对后续发言和票型负责。"
    target = rules.get_character(game_state, target_id)
    return f"我上警是为了整理信息，目前重点观察{target.id}号{target.name}的后续发言。"


def _build_player_sheriff_badge_flow(
    game_state: rules.WolfGameState,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
) -> Optional[rules.BadgeFlowInput]:
    player = _player(game_state)
    if player.role != "seer" or rules.get_active_badge_flow(game_state, player.id):
        return None

    checked_ids = {
        target_id
        for _day, target_id, _result in rules.get_character_seer_checks(
            game_state,
            player.id,
        )
    }
    candidates = [
        character
        for character in game_state.characters
        if character.alive
        and character.id != player.id
        and character.id not in checked_ids
    ]
    if not candidates:
        return None
    normalized_strategy = normalize_player_strategy(player_strategy)
    context = build_player_strategy_context(game_state)
    primary_ids = best_candidate_ids(
        context,
        [character.id for character in candidates],
        strategy=normalized_strategy,
        purpose="player_sheriff_badge_flow_primary",
    )
    primary_id = _policy_choice(
        game_state,
        primary_ids,
        "player_sheriff_badge_flow_primary",
        player_strategy=normalized_strategy,
    )
    secondary_ids = [
        character.id
        for character in candidates
        if character.id != primary_id
    ]
    secondary_id = (
        _policy_choice(
            game_state,
            best_candidate_ids(
                context,
                secondary_ids,
                strategy=normalized_strategy,
                purpose="player_sheriff_badge_flow_secondary",
            ),
            "player_sheriff_badge_flow_secondary",
            player_strategy=normalized_strategy,
        )
        if secondary_ids
        else None
    )
    return rules.BadgeFlowInput(
        primary_target_id=primary_id,
        secondary_target_id=secondary_id,
    )


def _build_player_day_speech(
    game_state: rules.WolfGameState,
    target_id: Optional[int],
) -> str:
    player = _player(game_state)
    latest_check = rules.get_latest_seer_check(game_state, player.id)
    parts: list[str] = []
    if player.role == "seer" and latest_check is not None:
        checked = rules.get_character(game_state, int(latest_check["target_id"]))
        result = "狼人" if latest_check["result"] == "werewolf" else "好人"
        parts.append(
            f"我是预言家，我查验了{checked.id}号{checked.name}，结果是{result}"
        )
    if target_id is not None:
        target = rules.get_character(game_state, target_id)
        parts.append(
            f"结合当前公开发言和动作，我重点观察{target.id}号{target.name}，"
            f"暂时想投给{target.id}号{target.name}"
        )
    if not parts:
        parts.append("我会继续根据公开发言、动作和票型更新判断")
    return "。".join(parts) + "。"


def _policy_choice(
    game_state: rules.WolfGameState,
    candidate_ids: list[int],
    purpose: str,
    *,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
) -> Optional[int]:
    if not candidate_ids:
        return None
    normalized_strategy = normalize_player_strategy(player_strategy)
    salt = f"simulation_player:{purpose}"
    if normalized_strategy != DEFAULT_PLAYER_STRATEGY:
        salt += f":{normalized_strategy}"
    return int(
        rules.deterministic_game_choice(
            game_state,
            sorted(set(candidate_ids)),
            salt,
        )
    )


def _player(game_state: rules.WolfGameState) -> rules.CharacterState:
    return rules.get_character(game_state, game_state.player_character_id)


def validate_completed_simulation(game_state: rules.WolfGameState) -> None:
    """Check terminal and audit invariants before accepting a result."""

    if game_state.phase != "GAME_OVER" or game_state.winner not in {
        "good",
        "werewolf",
    }:
        raise SimulationError("simulation did not reach a valid GAME_OVER state")
    role_counts = Counter(character.role for character in game_state.characters)
    if dict(role_counts) != rules.DEFAULT_WOLF_ROLES:
        raise SimulationError(f"role pool changed during simulation: {dict(role_counts)}")
    if len({character.id for character in game_state.characters}) != 12:
        raise SimulationError("simulation character ids are not unique")

    for elimination in game_state.eliminations:
        if elimination.source_target_id != elimination.character_id:
            raise SimulationError("elimination source target does not match its character")
        expected_action = rules.VALID_ELIMINATION_SOURCES.get(elimination.cause)
        if elimination.source_action != expected_action:
            raise SimulationError("elimination source action is invalid")
        if not elimination.source_actor_ids:
            raise SimulationError("elimination has no source actor")

    for vote in game_state.votes:
        voter = rules.get_character(game_state, vote.voter_id)
        target = rules.get_character(game_state, vote.target_id)
        if voter.id == target.id:
            raise SimulationError("simulation produced a self vote")


def build_simulation_result(
    game_state: rules.WolfGameState,
    phase_trace: list[str],
    *,
    player_strategy: str = DEFAULT_PLAYER_STRATEGY,
    belief_trace: Optional[dict[str, object]] = None,
    stance_trace: Optional[dict[str, object]] = None,
    vote_calibration_trace: Optional[dict[str, object]] = None,
    event_log: Optional[rules.GameRuleEventLogV1] = None,
    replay_report: Optional[rules.GameRuleReplayV1] = None,
    capture_event_log: bool = True,
    npc_policy_trace: Optional[list[dict[str, object]]] = None,
) -> dict[str, object]:
    """Build a timestamp- and game-id-free result suitable for exact replay."""

    normalized_strategy = normalize_player_strategy(player_strategy)
    strategy_descriptor = build_player_strategy_descriptor(
        normalized_strategy
    )
    controlled_plans = [
        speech.decision_plan
        for speech in game_state.speeches
        if not speech.is_player
        and speech.phase == "DAY_MEETING"
        and speech.decision_plan.get("schema_version")
        == PUBLIC_SPEECH_PLAN_SCHEMA_VERSION
    ]
    continuity_reason_counts = Counter(
        str(plan.get("continuity_reason", ""))
        for plan in controlled_plans
    )
    unknown_reasons = set(continuity_reason_counts).difference(
        reason.value for reason in SpeechContinuityReason
    )
    if unknown_reasons:
        raise SimulationError(
            "controlled public speech has unknown continuity reason: "
            + ", ".join(sorted(unknown_reasons))
        )

    result: dict[str, object] = {
        "schema_version": SIMULATION_SCHEMA_VERSION,
        "metrics_schema_version": METRICS_SCHEMA_VERSION,
        "belief_schema_version": BELIEF_SCHEMA_VERSION,
        "player_strategy_schema_version": PLAYER_STRATEGY_SCHEMA_VERSION,
        "player_strategy_context_schema_version": (
            PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION
        ),
        "player_strategy": strategy_descriptor,
        "player_policy_version": strategy_descriptor["policy_version"],
        "player_performance_schema_version": (
            PLAYER_PERFORMANCE_SCHEMA_VERSION
        ),
        "event_schema_version": rules.GAME_EVENT_SCHEMA_VERSION,
        "event_log_schema_version": rules.GAME_EVENT_LOG_SCHEMA_VERSION,
        "replay_schema_version": rules.GAME_REPLAY_SCHEMA_VERSION,
        "ruleset_version": rules.GAME_RULESET_VERSION,
        "npc_policy_mode": game_state.npc_policy_mode,
        "npc_policy_descriptors": game_state.npc_policy_descriptors,
        "seed": game_state.random_seed,
        "winner": game_state.winner,
        "winner_reason": game_state.winner_reason,
        "total_days": game_state.day,
        "roles": [
            {
                "character_id": character.id,
                "name": character.name,
                "is_player": character.is_player,
                "role": character.role,
                "camp": character.camp,
            }
            for character in game_state.characters
        ],
        "initial_layout_digest": _initial_layout_digest(game_state),
        "sheriff_ballots": [
            {
                "day": event.day,
                "round": _sheriff_event_round(event.context),
                "voter_id": event.actor_id,
                "target_id": event.target_id,
            }
            for event in game_state.sheriff_events
            if event.event_type == "sheriff_vote"
        ],
        "exile_ballots": [
            {
                "day": vote.day,
                "voter_id": vote.voter_id,
                "target_id": vote.target_id,
                "weight": vote.weight,
            }
            for vote in game_state.votes
        ],
        "eliminations": [elimination.model_dump() for elimination in game_state.eliminations],
        "phase_trace": phase_trace,
        "llm_validation_failure_count": len(game_state.llm_validation_failures),
        "metrics": build_game_metrics(game_state),
        "player_decision_trace": _build_player_decision_trace(game_state),
        "speech_continuity": {
            "schema_version": SPEECH_CONTINUITY_METRICS_VERSION,
            "continuity_schema_version": PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION,
            "plan_schema_version": PUBLIC_SPEECH_PLAN_SCHEMA_VERSION,
            "controlled_speech_count": len(controlled_plans),
            "reason_counts": {
                reason.value: continuity_reason_counts.get(reason.value, 0)
                for reason in SpeechContinuityReason
            },
        },
    }
    gameplay_payload = dict(result)
    gameplay_payload["schema_version"] = GAMEPLAY_DIGEST_PROJECTION_VERSION
    for metadata_key in (
        "event_schema_version",
        "event_log_schema_version",
        "replay_schema_version",
        "ruleset_version",
    ):
        gameplay_payload.pop(metadata_key, None)
    result["gameplay_digest"] = _payload_digest(gameplay_payload)
    result["gameplay_digest_projection_version"] = (
        GAMEPLAY_DIGEST_PROJECTION_VERSION
    )
    result["experiment_fingerprint_schema_version"] = (
        EXPERIMENT_FINGERPRINT_SCHEMA_VERSION
    )
    result["experiment_fingerprint"] = (
        _build_rule_only_experiment_fingerprint(
            normalized_strategy,
            npc_policy_mode=game_state.npc_policy_mode,
            npc_policy_descriptors=game_state.npc_policy_descriptors,
        )
    )
    result["npc_policy_trace_schema_version"] = NPC_POLICY_TRACE_SCHEMA_VERSION
    result["npc_policy_observation_schema_version"] = (
        NPC_POLICY_OBSERVATION_SCHEMA_VERSION
    )
    result["npc_policy_feature_schema_version"] = (
        NPC_POLICY_FEATURE_SCHEMA_VERSION
    )
    result["npc_policy_trace"] = npc_policy_trace
    result["npc_speech_quality_schema_version"] = (
        NPC_SPEECH_QUALITY_SCHEMA_VERSION
    )
    result["npc_speech_quality"] = build_npc_speech_quality(
        game_state
    ).model_dump(mode="json")
    event_type_counts = Counter(
        event.event_type for event in (event_log.events if event_log else [])
    )
    visibility_counts = Counter(
        event.visibility for event in (event_log.events if event_log else [])
    )
    result["event_summary"] = {
        "event_count": event_log.event_count if event_log else 0,
        "chain_valid": event_log.chain_valid if event_log else False,
        "replay_supported": event_log.replay_supported if event_log else False,
        "event_type_counts": dict(sorted(event_type_counts.items())),
        "visibility_counts": dict(sorted(visibility_counts.items())),
    }
    result["event_log"] = (
        event_log.model_dump(mode="json")
        if capture_event_log and event_log is not None
        else None
    )
    result["replay"] = (
        replay_report.model_dump(mode="json")
        if replay_report is not None
        else None
    )
    result["belief_trace"] = belief_trace
    result["stance_schema_version"] = STANCE_SCHEMA_VERSION
    result["stance_trace"] = stance_trace
    result["vote_calibration_schema_version"] = VOTE_CALIBRATION_SCHEMA_VERSION
    result["vote_calibration_trace"] = vote_calibration_trace
    result["result_digest"] = _payload_digest(result)
    return result


def _build_rule_only_experiment_fingerprint(
    player_strategy: str,
    *,
    npc_policy_mode: str = "rule",
    npc_policy_descriptors: Optional[dict[str, dict[str, str]]] = None,
) -> dict[str, object]:
    """Seal active rule inputs and inactive LLM provenance as digests only."""

    prompt_function_names = (
        "generate_resident_chat_reply",
        "generate_structured_public_speech_plan",
        "generate_structured_speech_voice_prefix",
        "generate_public_speech_llm_text",
        "generate_private_chat_llm_text",
        "generate_validated_llm_rewrite",
    )
    prompt_sources = {
        name: inspect.getsource(getattr(rules, name))
        for name in prompt_function_names
    }
    npc_profiles = {
        name: profile.model_dump(mode="json")
        for name, profile in sorted(rules.NPC_PROFILES.items())
    }
    knowledge_base = [
        item.model_dump(mode="json") for item in rules.KNOWLEDGE_BASE
    ]
    npc_tuning = (
        rules.NPC_TUNING_CONFIG.model_dump(mode="json")
        if rules.NPC_TUNING_CONFIG is not None
        else None
    )
    llm_settings = getattr(rules.LLM_CLIENT, "settings", None)
    if llm_settings is None:
        status_method = getattr(rules.LLM_CLIENT, "status", None)
        llm_settings = status_method() if callable(status_method) else {}
    components: dict[str, tuple[object, bool]] = {
        "knowledge_base": (
            {
                "ordering": "configured_list_order",
                "items": knowledge_base,
            },
            False,
        ),
        "llm_request_config": (
            {
                "fingerprint": build_llm_config_fingerprint(
                    llm_settings
                )
            },
            False,
        ),
        "npc_profiles": (npc_profiles, True),
        "npc_tuning": (npc_tuning, True),
        "output_schemas": (
            {
                "simulation": SIMULATION_SCHEMA_VERSION,
                "batch": BATCH_SCHEMA_VERSION,
                "gameplay_projection": GAMEPLAY_DIGEST_PROJECTION_VERSION,
                "metrics": METRICS_SCHEMA_VERSION,
                "belief": BELIEF_SCHEMA_VERSION,
                "stance": STANCE_SCHEMA_VERSION,
                "speech_continuity": SPEECH_CONTINUITY_METRICS_VERSION,
                "public_speech_plan": PUBLIC_SPEECH_PLAN_SCHEMA_VERSION,
                "npc_speech_quality": NPC_SPEECH_QUALITY_SCHEMA_VERSION,
                "npc_speech_quality_batch": (
                    NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION
                ),
                "vote_calibration": VOTE_CALIBRATION_SCHEMA_VERSION,
                "event": rules.GAME_EVENT_SCHEMA_VERSION,
                "event_log": rules.GAME_EVENT_LOG_SCHEMA_VERSION,
                "replay": rules.GAME_REPLAY_SCHEMA_VERSION,
            },
            True,
        ),
        "player_policy": (
            build_player_strategy_descriptor(player_strategy),
            True,
        ),
        "npc_policy": (
            {
                "mode": npc_policy_mode,
                "descriptors": npc_policy_descriptors or {},
                "observation_schema_version": (
                    NPC_POLICY_OBSERVATION_SCHEMA_VERSION
                ),
                "feature_schema_version": NPC_POLICY_FEATURE_SCHEMA_VERSION,
                "trace_schema_version": NPC_POLICY_TRACE_SCHEMA_VERSION,
                "entropy_guard_version": (
                    NPC_POLICY_ENTROPY_GUARD_VERSION
                ),
            },
            True,
        ),
        "prompt_catalog": (
            {
                "catalog_version": "agent_town_prompt_source_catalog.v1",
                "validator_version": rules.LLM_VALIDATOR_VERSION,
                "max_validation_attempts": (
                    rules.MAX_LLM_VALIDATION_ATTEMPTS
                ),
                "public_speech_max_chars": (
                    rules.PUBLIC_SPEECH_LLM_MAX_CHARS
                ),
                "functions": prompt_sources,
            },
            False,
        ),
        "rag_config": (
            {
                "execution_mode": "disabled_in_rule_simulation",
                "model_name": rules.HYBRID_INDEX.model_name,
            },
            False,
        ),
        "rules_and_roles": (
            {
                "ruleset_version": rules.GAME_RULESET_VERSION,
                "roles": rules.DEFAULT_WOLF_ROLES,
                "npc_names": rules.NPC_NAMES,
                "npc_personalities": rules.NPC_PERSONALITIES,
            },
            True,
        ),
    }
    return build_experiment_fingerprint(
        execution_mode=RULE_ONLY_EXECUTION_MODE,
        components=components,
    )


def _initial_layout_digest(game_state: rules.WolfGameState) -> str:
    payload = {
        "player_character_id": game_state.player_character_id,
        "roles": [
            {
                "character_id": character.id,
                "is_player": character.is_player,
                "role": character.role,
                "camp": character.camp,
            }
            for character in sorted(
                game_state.characters,
                key=lambda item: item.id,
            )
        ],
    }
    return _payload_digest(payload)


def _build_player_decision_trace(
    game_state: rules.WolfGameState,
) -> dict[str, object]:
    player_id = game_state.player_character_id
    return {
        "schema_version": PLAYER_DECISION_TRACE_SCHEMA_VERSION,
        "night_actions": [
            action.model_dump(mode="json")
            for action in game_state.night_actions
            if action.actor_id == player_id
        ],
        "sheriff_events": [
            event.model_dump(mode="json")
            for event in game_state.sheriff_events
            if event.actor_id == player_id
        ],
        "public_speeches": [
            {
                "day": speech.day,
                "phase": speech.phase,
                "speech": speech.speech,
                "focus_target_id": speech.focus_target_id,
            }
            for speech in game_state.speeches
            if speech.character_id == player_id
        ],
        "exile_ballots": [
            {
                "day": vote.day,
                "target_id": vote.target_id,
                "weight": vote.weight,
            }
            for vote in game_state.votes
            if vote.voter_id == player_id
        ],
        "hunter_shots": [
            shot.model_dump(mode="json")
            for shot in game_state.hunter_shots
            if shot.hunter_id == player_id
        ],
    }


def _sheriff_event_round(context: str) -> int:
    if not context.startswith("round:"):
        return 0
    try:
        return max(0, int(context.split(":", 1)[1]))
    except ValueError:
        return 0


def _payload_digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


__all__ = [
    "BATCH_SCHEMA_VERSION",
    "BENCHMARK_PLAYER_ROLES",
    "BELIEF_SCHEMA_VERSION",
    "DEFAULT_PLAYER_STRATEGY",
    "DEFAULT_MAX_DAYS",
    "DEFAULT_MAX_STEPS",
    "METRICS_SCHEMA_VERSION",
    "NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION",
    "NPC_SPEECH_QUALITY_SCHEMA_VERSION",
    "PLAYER_BENCHMARK_SCHEMA_VERSION",
    "PLAYER_DECISION_TRACE_SCHEMA_VERSION",
    "PLAYER_POLICY_VERSION",
    "PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION",
    "PLAYER_STRATEGY_SCHEMA_VERSION",
    "PLAYER_STRATEGY_TIERS",
    "SIMULATION_SCHEMA_VERSION",
    "STANCE_SCHEMA_VERSION",
    "VOTE_CALIBRATION_SCHEMA_VERSION",
    "VOTE_CALIBRATION_SUMMARY_VERSION",
    "SimulationError",
    "build_simulation_result",
    "run_player_strategy_benchmark",
    "run_rule_simulation",
    "run_rule_simulation_batch",
    "validate_completed_simulation",
]
