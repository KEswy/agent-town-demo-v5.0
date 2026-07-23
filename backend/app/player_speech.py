"""Versioned, public-safe contracts for player-speech preview.

The rule engine builds these models from its existing deterministic parser.
They intentionally contain only the player's submitted public wording,
public character references, and the rule effects that would be committed.
Hidden role truth is never part of this contract.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


PLAYER_SPEECH_UNDERSTANDING_SCHEMA_VERSION = "player_speech_understanding.v1"
PLAYER_SPEECH_PREVIEW_SCHEMA_VERSION = "player_speech_preview.v1"

PlayerSpeechKind = Literal["day", "sheriff"]
PlayerSpeechTone = Literal["neutral", "suspicious", "claiming"]
PlayerSpeechClaimType = Literal["role", "seer_check"]
PlayerSpeechRole = Literal[
    "werewolf",
    "seer",
    "witch",
    "hunter",
    "guard",
    "villager",
]
PlayerSpeechCheckResult = Literal["good", "werewolf"]
PlayerSpeechEffectKind = Literal[
    "public_claim",
    "temporary_nomination",
    "badge_flow",
    "accusation",
    "support",
    "opposition",
    "vote_intent",
    "witch_directive",
    "mention",
]


class StrictSpeechModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlayerSpeechClaimV1(StrictSpeechModel):
    claim_type: PlayerSpeechClaimType
    claimed_role: Optional[PlayerSpeechRole] = None
    target_id: Optional[int] = Field(default=None, gt=0)
    result: Optional[PlayerSpeechCheckResult] = None
    display_text: str


class PlayerSpeechAccusationV1(StrictSpeechModel):
    target_id: int = Field(gt=0)
    reason: str
    intensity: float = Field(ge=0.0, le=1.0)


class PlayerSpeechWitchDirectiveV1(StrictSpeechModel):
    action: Literal["hold", "poison"]
    target_id: Optional[int] = Field(default=None, gt=0)
    reason_kind: str
    confidence: int = Field(ge=0, le=100)


class PlayerSpeechUnderstandingV1(StrictSpeechModel):
    schema_version: Literal["player_speech_understanding.v1"] = (
        PLAYER_SPEECH_UNDERSTANDING_SCHEMA_VERSION
    )
    mentioned_character_ids: list[int] = Field(default_factory=list)
    claims: list[PlayerSpeechClaimV1] = Field(default_factory=list)
    accusations: list[PlayerSpeechAccusationV1] = Field(default_factory=list)
    supported_character_ids: list[int] = Field(default_factory=list)
    opposed_character_ids: list[int] = Field(default_factory=list)
    vote_intent_target_id: Optional[int] = Field(default=None, gt=0)
    witch_directive: Optional[PlayerSpeechWitchDirectiveV1] = None
    tone: PlayerSpeechTone = "neutral"


class PlayerSpeechPreviewEffectV1(StrictSpeechModel):
    kind: PlayerSpeechEffectKind
    summary: str
    target_id: Optional[int] = Field(default=None, gt=0)


class PlayerSpeechBadgeFlowPreviewV1(StrictSpeechModel):
    primary_target_id: int = Field(gt=0)
    secondary_target_id: Optional[int] = Field(default=None, gt=0)
    claimed_good_anchor_id: Optional[int] = Field(default=None, gt=0)
    revision_reason: str
    canonical_text: str


class PlayerSpeechPreviewResponseV1(StrictSpeechModel):
    schema_version: Literal["player_speech_preview.v1"] = (
        PLAYER_SPEECH_PREVIEW_SCHEMA_VERSION
    )
    understanding_schema_version: Literal[
        "player_speech_understanding.v1"
    ] = PLAYER_SPEECH_UNDERSTANDING_SCHEMA_VERSION
    accepted: bool
    errors: list[str] = Field(default_factory=list)
    game_id: str
    character_id: int = Field(gt=0)
    speech_kind: PlayerSpeechKind
    original_speech: str
    canonical_speech: str
    understanding: PlayerSpeechUnderstandingV1
    public_facts_to_write: list[PlayerSpeechPreviewEffectV1] = Field(
        default_factory=list
    )
    strategic_signals_to_apply: list[PlayerSpeechPreviewEffectV1] = Field(
        default_factory=list
    )
    text_only_notes: list[str] = Field(default_factory=list)
    normalized_badge_flow: Optional[PlayerSpeechBadgeFlowPreviewV1] = None
    preview_fingerprint: str = ""


__all__ = [
    "PLAYER_SPEECH_PREVIEW_SCHEMA_VERSION",
    "PLAYER_SPEECH_UNDERSTANDING_SCHEMA_VERSION",
    "PlayerSpeechAccusationV1",
    "PlayerSpeechBadgeFlowPreviewV1",
    "PlayerSpeechClaimV1",
    "PlayerSpeechPreviewEffectV1",
    "PlayerSpeechPreviewResponseV1",
    "PlayerSpeechUnderstandingV1",
    "PlayerSpeechWitchDirectiveV1",
]
