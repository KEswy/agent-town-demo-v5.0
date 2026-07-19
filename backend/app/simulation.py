"""Deterministic, no-HTTP game simulation for Agent Town V3.

The driver calls the existing rule entry points directly. It never starts an
ASGI server, enables an LLM, initializes vector RAG, or writes town-chat
memory. The automated player policy consumes only the player's own role and
role knowledge plus public state.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Optional

from . import main as rules
from .belief import (
    BELIEF_SCHEMA_VERSION,
    BeliefTraceRecorder,
    aggregate_belief_traces,
)
from .simulation_metrics import (
    METRICS_SCHEMA_VERSION,
    aggregate_batch_metrics,
    build_game_metrics,
)
from .npc_decision import (
    PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION,
    PUBLIC_SPEECH_PLAN_SCHEMA_VERSION,
    SpeechContinuityReason,
)
from .stance import (
    STANCE_SCHEMA_VERSION,
    StanceTraceRecorder,
    aggregate_stance_traces,
)
from .vote_calibration import (
    VOTE_CALIBRATION_SCHEMA_VERSION,
    VOTE_CALIBRATION_SUMMARY_VERSION,
    VoteCalibrationTraceRecorder,
    aggregate_vote_calibration_traces,
)


SIMULATION_SCHEMA_VERSION = "agent_town_simulation.v9"
BATCH_SCHEMA_VERSION = "agent_town_simulation_batch.v9"
PLAYER_POLICY_VERSION = "legal_public_baseline.v1"
SPEECH_CONTINUITY_METRICS_VERSION = "speech_continuity_metrics.v1"
DEFAULT_MAX_DAYS = 20
DEFAULT_MAX_STEPS = 5_000


class SimulationError(RuntimeError):
    """Raised when a headless game cannot reach a legal terminal state."""


def run_rule_simulation(
    seed: int,
    *,
    player_role: str = "random",
    max_days: int = DEFAULT_MAX_DAYS,
    max_steps: int = DEFAULT_MAX_STEPS,
    capture_beliefs: bool = True,
    capture_stances: bool = True,
    capture_vote_calibration: bool = True,
) -> dict[str, object]:
    """Run one complete rule-only game and return a normalized result."""

    if seed < 0 or seed > rules.MAX_GAME_RANDOM_SEED:
        raise ValueError(
            f"seed must be between 0 and {rules.MAX_GAME_RANDOM_SEED}"
        )
    if max_days < 1 or max_steps < 1:
        raise ValueError("max_days and max_steps must be positive")

    game_id = f"simulation_{seed}"
    request = rules.GameStartRequest(
        player_name="模拟玩家",
        player_role=player_role,
        enable_llm=False,
        enable_rag=False,
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
            _advance_one_phase(game_state)
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
        )
    finally:
        with rules.GAME_LOCK:
            rules.GAME_STORE.pop(game_id, None)


def run_rule_simulation_batch(
    start_seed: int,
    games: int,
    *,
    player_role: str = "random",
    max_days: int = DEFAULT_MAX_DAYS,
    max_steps: int = DEFAULT_MAX_STEPS,
    capture_beliefs: bool = True,
    capture_stances: bool = True,
    capture_vote_calibration: bool = True,
) -> dict[str, object]:
    """Run sequential seeds and return deterministic per-game and aggregate data."""

    if games < 1:
        raise ValueError("games must be positive")
    final_seed = start_seed + games - 1
    if start_seed < 0 or final_seed > rules.MAX_GAME_RANDOM_SEED:
        raise ValueError(
            f"seed range must stay between 0 and {rules.MAX_GAME_RANDOM_SEED}"
        )

    results = [
        run_rule_simulation(
            start_seed + offset,
            player_role=player_role,
            max_days=max_days,
            max_steps=max_steps,
            capture_beliefs=capture_beliefs,
            capture_stances=capture_stances,
            capture_vote_calibration=capture_vote_calibration,
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
    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
        "metrics_schema_version": METRICS_SCHEMA_VERSION,
        "belief_schema_version": BELIEF_SCHEMA_VERSION,
        "stance_schema_version": STANCE_SCHEMA_VERSION,
        "speech_continuity_schema_version": SPEECH_CONTINUITY_METRICS_VERSION,
        "vote_calibration_schema_version": VOTE_CALIBRATION_SCHEMA_VERSION,
        "vote_calibration_summary_version": VOTE_CALIBRATION_SUMMARY_VERSION,
        "player_policy_version": PLAYER_POLICY_VERSION,
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
        "vote_calibration_summary": (
            aggregate_vote_calibration_traces(results)
            if capture_vote_calibration
            else None
        ),
        "games": results,
    }


def _advance_one_phase(game_state: rules.WolfGameState) -> None:
    phase = game_state.phase
    if phase == "NIGHT":
        _submit_player_night_action(game_state)
        rules.resolve_night(rules.NightResolveRequest(game_id=game_state.game_id))
        return
    if phase == "HUNTER_SHOT":
        target_id = _choose_public_player_target(game_state, "hunter_shot")
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
        rules.submit_sheriff_signup(
            rules.SheriffSignupRequest(
                game_id=game_state.game_id,
                character_id=player.id,
                run_for_sheriff=player.role == "seer",
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
            speech=_build_player_sheriff_speech(game_state) if speaker.is_player else "",
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
                target_id=_choose_player_sheriff_vote(game_state),
            )
        )
        return
    if phase == "MEETING_ORDER":
        side = rules.deterministic_game_choice(
            game_state,
            ["left", "right"],
            "simulation_player_meeting_side",
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
            target_id = _choose_public_player_target(game_state, "day_speech")
            rules.submit_player_speech(
                rules.PlayerSpeechRequest(
                    game_id=game_state.game_id,
                    character_id=speaker.id,
                    speech=_build_player_day_speech(game_state, target_id),
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
        target_id = _choose_public_player_target(game_state, "sheriff_nomination")
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
            _choose_public_player_target(game_state, "exile_vote")
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
        target_id = _choose_public_player_target(game_state, "badge_transfer")
        rules.submit_badge_transfer(
            rules.BadgeTransferRequest(
                game_id=game_state.game_id,
                character_id=game_state.player_character_id,
                target_id=target_id,
            )
        )
        return
    raise SimulationError(f"unsupported simulation phase: {phase}")


def _submit_player_night_action(game_state: rules.WolfGameState) -> None:
    player = _player(game_state)
    if not player.alive:
        return
    action_type, target_id = _choose_player_night_action(game_state, player)
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
) -> tuple[str, Optional[int]]:
    alive_ids = [
        character.id
        for character in game_state.characters
        if character.alive and character.id != player.id
    ]
    if player.role == "werewolf":
        teammate_ids = _player_wolf_teammate_ids(game_state)
        target_ids = [
            character_id
            for character_id in alive_ids
            if character_id not in teammate_ids
        ]
        return "werewolf_kill", _policy_choice(
            game_state,
            target_ids,
            "night_werewolf_kill",
        )
    if player.role == "seer":
        checked_ids = {
            int(action.target_id)
            for action in game_state.night_actions
            if action.actor_id == player.id
            and action.action_type == "seer_check"
            and action.target_id is not None
        }
        target_ids = [
            character_id
            for character_id in alive_ids
            if character_id not in checked_ids
        ] or alive_ids
        return "seer_check", _policy_choice(game_state, target_ids, "night_seer_check")
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
        return "guard_protect", _policy_choice(
            game_state,
            target_ids,
            "night_guard_protect",
        )
    if player.role == "witch":
        resources = rules.get_role_resources(game_state, player.id)
        attacked_target_id = rules.get_current_wolf_target(game_state)
        can_self_save = attacked_target_id != player.id or game_state.day == 1
        if (
            attacked_target_id is not None
            and bool(resources.get("antidote_available", False))
            and can_self_save
        ):
            return "witch_save", attacked_target_id
    return "none", None


def _choose_player_sheriff_vote(
    game_state: rules.WolfGameState,
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
    strengths = {
        candidate_id: rules.get_public_persuasion_strength(
            game_state,
            rules.get_character(game_state, candidate_id),
        )
        for candidate_id in candidate_ids
    }
    highest = max(strengths.values())
    best_ids = sorted(
        candidate_id
        for candidate_id, strength in strengths.items()
        if strength == highest
    )
    return _policy_choice(game_state, best_ids, "sheriff_vote")


def _choose_public_player_target(
    game_state: rules.WolfGameState,
    purpose: str,
) -> Optional[int]:
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

    excluded_ids: set[int] = set()
    priority_ids: set[int] = set()
    if player.role == "werewolf":
        excluded_ids = _player_wolf_teammate_ids(game_state)
    elif player.role == "seer":
        for _day, target_id, result in rules.get_character_seer_checks(
            game_state,
            player.id,
        ):
            if result == "werewolf":
                priority_ids.add(target_id)
            elif result == "good":
                excluded_ids.add(target_id)

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

    public_scores = {
        character.id: rules.get_public_suspicion_score(game_state, character.id)
        for character in eligible
    }
    highest_score = max(public_scores.values())
    best_ids = sorted(
        character_id
        for character_id, score in public_scores.items()
        if score == highest_score
    )
    return _policy_choice(game_state, best_ids, purpose)


def _build_player_sheriff_speech(game_state: rules.WolfGameState) -> str:
    player = _player(game_state)
    latest_check = rules.get_latest_seer_check(game_state, player.id)
    if player.role == "seer" and latest_check is not None:
        target = rules.get_character(game_state, int(latest_check["target_id"]))
        result = "狼人" if latest_check["result"] == "werewolf" else "好人"
        return (
            f"我是预言家，我查验了{target.id}号{target.name}，结果是{result}。"
            "我会继续用公开发言和票型验证判断。"
        )
    target_id = _choose_public_player_target(game_state, "sheriff_speech")
    if target_id is None:
        return "我上警是为了整理公开信息，会对后续发言和票型负责。"
    target = rules.get_character(game_state, target_id)
    return f"我上警是为了整理信息，目前重点观察{target.id}号{target.name}的后续发言。"


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


def _player_wolf_teammate_ids(game_state: rules.WolfGameState) -> set[int]:
    private_info = rules.build_player_private_info_dict(game_state)
    return {
        int(item["id"])
        for item in private_info.get("wolf_teammates", [])
        if isinstance(item, dict) and "id" in item
    }


def _policy_choice(
    game_state: rules.WolfGameState,
    candidate_ids: list[int],
    purpose: str,
) -> Optional[int]:
    if not candidate_ids:
        return None
    return int(
        rules.deterministic_game_choice(
            game_state,
            sorted(set(candidate_ids)),
            f"simulation_player:{purpose}",
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
    belief_trace: Optional[dict[str, object]] = None,
    stance_trace: Optional[dict[str, object]] = None,
    vote_calibration_trace: Optional[dict[str, object]] = None,
) -> dict[str, object]:
    """Build a timestamp- and game-id-free result suitable for exact replay."""

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
        "player_policy_version": PLAYER_POLICY_VERSION,
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
    result["gameplay_digest"] = _payload_digest(result)
    result["belief_trace"] = belief_trace
    result["stance_schema_version"] = STANCE_SCHEMA_VERSION
    result["stance_trace"] = stance_trace
    result["vote_calibration_schema_version"] = VOTE_CALIBRATION_SCHEMA_VERSION
    result["vote_calibration_trace"] = vote_calibration_trace
    result["result_digest"] = _payload_digest(result)
    return result


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
    "BELIEF_SCHEMA_VERSION",
    "DEFAULT_MAX_DAYS",
    "DEFAULT_MAX_STEPS",
    "METRICS_SCHEMA_VERSION",
    "PLAYER_POLICY_VERSION",
    "SIMULATION_SCHEMA_VERSION",
    "STANCE_SCHEMA_VERSION",
    "VOTE_CALIBRATION_SCHEMA_VERSION",
    "VOTE_CALIBRATION_SUMMARY_VERSION",
    "SimulationError",
    "build_simulation_result",
    "run_rule_simulation",
    "run_rule_simulation_batch",
    "validate_completed_simulation",
]
