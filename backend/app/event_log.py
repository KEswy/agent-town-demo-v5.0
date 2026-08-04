"""Versioned append-only rule events and deterministic replay contracts.

The event module deliberately knows nothing about werewolf rules.  Python rule
entry points mutate the game state, then use these helpers to seal the command,
the before/after state digests, and the previous event digest into one chain.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


GAME_EVENT_SCHEMA_VERSION = "game_rule_event.v1"
GAME_EVENT_LOG_SCHEMA_VERSION = "game_rule_event_log.v1"
GAME_REPLAY_SCHEMA_VERSION = "game_rule_replay.v1"
GAME_RULESET_VERSION = "agent_town_rules.v4.2"
GENESIS_EVENT_DIGEST = "0" * 64

EventVisibility = Literal["public", "player_private", "system_private"]
RuleEventType = Literal[
    "game_created",
    "night_action_submitted",
    "night_resolved",
    "hunter_shot_resolved",
    "sheriff_signup_submitted",
    "player_sheriff_speech_submitted",
    "npc_sheriff_speech_generated",
    "sheriff_withdrawal_submitted",
    "sheriff_vote_resolved",
    "sheriff_meeting_order_submitted",
    "sheriff_nomination_submitted",
    "badge_transfer_submitted",
    "player_day_speech_submitted",
    "npc_day_speech_generated",
    "npc_day_speeches_generated",
    "free_activity_ended",
    "private_chat_completed",
    "npc_vote_decisions_generated",
    "player_vote_submitted",
    "exile_vote_resolved",
    "all_votes_submitted_and_resolved",
]


class GameRuleEventV1(BaseModel):
    """One immutable command boundary in the authoritative rule history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["game_rule_event.v1"] = GAME_EVENT_SCHEMA_VERSION
    sequence: int = Field(ge=1)
    event_id: str
    command_id: str
    game_id: str
    ruleset_version: Literal["agent_town_rules.v4.2"] = GAME_RULESET_VERSION
    event_type: RuleEventType
    visibility: EventVisibility
    actor_id: Optional[int] = None
    day_before: int = Field(ge=0)
    day_after: int = Field(ge=0)
    phase_before: str
    phase_after: str
    command: dict[str, object] = Field(default_factory=dict)
    state_digest_before: str = Field(min_length=64, max_length=64)
    state_digest_after: str = Field(min_length=64, max_length=64)
    previous_event_digest: str = Field(min_length=64, max_length=64)
    replayable: bool
    event_digest: str = Field(min_length=64, max_length=64)


class GameRuleEventLogV1(BaseModel):
    """Terminal-only API view of one complete, chain-verified event log."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["game_rule_event_log.v1"] = (
        GAME_EVENT_LOG_SCHEMA_VERSION
    )
    game_id: str
    ruleset_version: Literal["agent_town_rules.v4.2"] = GAME_RULESET_VERSION
    event_count: int = Field(ge=0)
    chain_valid: bool
    replay_supported: bool
    events: list[GameRuleEventV1] = Field(default_factory=list)


class GameRuleReplayV1(BaseModel):
    """Outcome of replaying a sealed command log through the rule engine."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["game_rule_replay.v1"] = GAME_REPLAY_SCHEMA_VERSION
    game_id: str
    ruleset_version: Literal["agent_town_rules.v4.2"] = GAME_RULESET_VERSION
    supported: bool
    verified: bool
    event_count: int = Field(ge=0)
    checked_event_count: int = Field(ge=0)
    first_mismatch_sequence: Optional[int] = Field(default=None, ge=1)
    reason: str = ""
    expected_final_state_digest: str = ""
    actual_final_state_digest: str = ""
    expected_projection_digest: str = ""
    actual_projection_digest: str = ""


@dataclass(frozen=True)
class GameCommandCheckpoint:
    """State captured immediately before a rule command mutates the game."""

    day: int
    phase: str
    state_digest: str
    state_snapshot: Optional[dict[str, object]] = None


def canonical_payload_digest(payload: object) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def normalized_rule_state_payload(game_state: BaseModel) -> dict[str, object]:
    """Return the deterministic rule state represented by an event digest.

    Storage identity, wall-clock timestamps, and the event chain itself are
    deliberately excluded.  Everything that can affect later rule behavior is
    retained, including hidden roles and lawful private state.
    """

    payload = game_state.model_dump(mode="json")
    payload.pop("game_id", None)
    payload.pop("created_at", None)
    payload.pop("updated_at", None)
    payload.pop("rule_events", None)
    payload.pop("command_results", None)
    payload.pop("recovery_config_fingerprint", None)
    # NPC reasoning is a derived, actor-scoped cache. It is recomputed from
    # lawful public/private facts and must not create an unlogged state change
    # between two authoritative rule commands.
    payload.pop("npc_reasoning_states", None)
    # V4 saves did not carry policy-mode fields.  The default rule mode has no
    # model artifact as an authority input, so omitting its empty defaults keeps
    # the V4 state digest stable while still sealing descriptors for shadow or
    # local games where they can affect later actions.
    if payload.get("npc_policy_mode", "rule") == "rule":
        payload.pop("npc_policy_mode", None)
        payload.pop("npc_policy_descriptors", None)
    # V4 public claims predate V5.4 sheriff-window provenance.  Pydantic fills
    # those three fields with inert defaults when an old snapshot is restored.
    # Omitting only the exact all-default triple keeps the historic rule digest
    # and event-chain boundary stable; any real provenance remains sealed.
    public_claims = payload.get("public_claims")
    if isinstance(public_claims, list):
        for claim in public_claims:
            if (
                isinstance(claim, dict)
                and claim.get("phase") == ""
                and claim.get("window_day") is None
                and claim.get("event_sequence") == 0
            ):
                claim.pop("phase", None)
                claim.pop("window_day", None)
                claim.pop("event_sequence", None)
    # The Idiot flip flag defaults to False.  Old snapshots predate the field,
    # and an all-default False never affects later rule behavior, so it is
    # omitted from the authoritative digest exactly like the provenance triple
    # above.  A real flip (True) stays sealed in the digest.
    characters = payload.get("characters")
    if isinstance(characters, list):
        for character in characters:
            if (
                isinstance(character, dict)
                and character.get("idiot_flipped", False) is False
            ):
                character.pop("idiot_flipped", None)
    return payload


def rule_state_digest(game_state: BaseModel) -> str:
    return canonical_payload_digest(normalized_rule_state_payload(game_state))


def begin_game_command(game_state: BaseModel) -> GameCommandCheckpoint:
    return GameCommandCheckpoint(
        day=int(getattr(game_state, "day")),
        phase=str(getattr(game_state, "phase")),
        state_digest=rule_state_digest(game_state),
        state_snapshot=game_state.model_dump(mode="json"),
    )


def build_game_rule_event(
    game_state: BaseModel,
    *,
    event_type: str,
    visibility: EventVisibility,
    command: dict[str, object],
    checkpoint: GameCommandCheckpoint,
    actor_id: Optional[int] = None,
) -> GameRuleEventV1:
    existing_events = list(getattr(game_state, "rule_events"))
    sequence = len(existing_events) + 1
    previous_digest = (
        existing_events[-1].event_digest
        if existing_events
        else GENESIS_EVENT_DIGEST
    )
    replayable = not bool(getattr(game_state, "llm_enabled")) and not bool(
        getattr(game_state, "rag_enabled")
    )
    command_payload = json.loads(
        json.dumps(command, ensure_ascii=False)
    )
    state_digest_after = rule_state_digest(game_state)
    command_id = "command:{sequence}:{suffix}".format(
        sequence=sequence,
        suffix=canonical_payload_digest(
            {
                "event_type": event_type,
                "command": command_payload,
                "previous_event_digest": previous_digest,
            }
        )[:16],
    )
    unsigned = {
        "schema_version": GAME_EVENT_SCHEMA_VERSION,
        "sequence": sequence,
        "command_id": command_id,
        "game_id": str(getattr(game_state, "game_id")),
        "ruleset_version": GAME_RULESET_VERSION,
        "event_type": event_type,
        "visibility": visibility,
        "actor_id": actor_id,
        "day_before": checkpoint.day,
        "day_after": int(getattr(game_state, "day")),
        "phase_before": checkpoint.phase,
        "phase_after": str(getattr(game_state, "phase")),
        "command": command_payload,
        "state_digest_before": checkpoint.state_digest,
        "state_digest_after": state_digest_after,
        "previous_event_digest": previous_digest,
        "replayable": replayable,
    }
    event_digest = canonical_payload_digest(unsigned)
    return GameRuleEventV1(
        **unsigned,
        event_id=f"event:{sequence}:{event_digest[:16]}",
        event_digest=event_digest,
    )


def append_game_rule_event(
    game_state: BaseModel,
    *,
    event_type: str,
    visibility: EventVisibility,
    command: dict[str, object],
    checkpoint: GameCommandCheckpoint,
    actor_id: Optional[int] = None,
) -> GameRuleEventV1:
    event = build_game_rule_event(
        game_state,
        event_type=event_type,
        visibility=visibility,
        command=command,
        checkpoint=checkpoint,
        actor_id=actor_id,
    )
    getattr(game_state, "rule_events").append(event)
    return event


def expected_event_digest(event: GameRuleEventV1) -> str:
    payload = event.model_dump(mode="json", exclude={"event_id", "event_digest"})
    return canonical_payload_digest(payload)


def validate_game_rule_event_chain(events: list[GameRuleEventV1]) -> bool:
    previous_digest = GENESIS_EVENT_DIGEST
    previous_state_digest = canonical_payload_digest({})
    for sequence, event in enumerate(events, start=1):
        if event.sequence != sequence:
            return False
        if event.previous_event_digest != previous_digest:
            return False
        if event.event_digest != expected_event_digest(event):
            return False
        if event.event_id != f"event:{sequence}:{event.event_digest[:16]}":
            return False
        if event.state_digest_before != previous_state_digest:
            return False
        previous_digest = event.event_digest
        previous_state_digest = event.state_digest_after
    return True
