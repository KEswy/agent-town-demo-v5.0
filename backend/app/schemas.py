"""Pydantic request/response schemas and persisted game-state models.

Extracted from ``main.py``; imports config constants and app contracts only,
never ``main`` itself, so ``main`` can import these schemas freely.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, RLock
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import (
    DEFAULT_WOLF_ROLES,
    FIXED_NPC_COUNT,
    MAX_GAME_RANDOM_SEED,
    MAX_LLM_VALIDATION_ATTEMPTS,
    WITCH_DIRECTIVE_SCHEMA_VERSION,
    WITCH_STRATEGY_SCHEMA_VERSION,
)
from .event_log import GameRuleEventV1
from .game_persistence import (
    GameRecoveryReportV1,
    GameSaveStore,
)
from .idempotency import (
    GameCommandResultV1,
    IdempotentGameCommandRequest,
)
from .npc_decision import PublicPositionV1
from .npc_policy import policy_mode_from_environment
from .npc_reasoning import NPCBeliefStateV1
from .npc_tuning import NPC_TUNING_SCHEMA_VERSION, NPCTuningConfigV1
from .player_speech import PlayerSpeechPreviewResponseV1
from .post_game_review import PostGameExplainableReviewV1
from .public_evidence import (
    PublicEvidenceAnalysisV1,
    PublicEvidenceTimelineV1,
)

class TriggerEasterEgg(BaseModel):
    egg_id: str
    triggers: list[str]
    reply: str
    repeat_reply: str
    reveal_self_role: bool = False


class NPCProfile(BaseModel):
    npc_name: str
    role: str
    personality: str
    knowledge: list[str]
    speech_style: str = ""
    catchphrases: list[str] = Field(default_factory=list)
    easter_eggs: list[str] = Field(default_factory=list)
    trigger_easter_eggs: list[TriggerEasterEgg] = Field(default_factory=list)
    use_llm_for_chat: bool = False


class KnowledgeItem(BaseModel):
    npc_name: str
    title: str
    content: str
    keywords: list[str]


class ScoredKnowledgeItem(BaseModel):
    score: int
    keyword_score: int = 0
    vector_score: float = 0.0
    item: KnowledgeItem


class KnowledgeSearchResponse(BaseModel):
    npc_name: str
    message: str
    matched: bool
    score: int
    item: Optional[KnowledgeItem] = None
    results: list[ScoredKnowledgeItem] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    vector_model: str = ""


class ChatRequest(BaseModel):
    npc_name: str = "Guide"
    message: str = "你好"
    player_id: str = "player"
    game_phase: str = "TOWN"


class ChatResponse(BaseModel):
    npc_name: str
    reply: str
    memory_count: int
    relationship_level: str
    knowledge_title: str = ""
    knowledge_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""


class ClearMemoryResponse(BaseModel):
    deleted_count: int
    message: str


class ReloadConfigResponse(BaseModel):
    npc_count: int
    knowledge_count: int
    tuning_schema_version: str = NPC_TUNING_SCHEMA_VERSION
    applies_to: str = "new_games"
    message: str


class MemoryItem(BaseModel):
    player_id: str
    npc_name: str
    player_message: str
    npc_reply: str
    created_at: str


class ApiHealthResponse(BaseModel):
    status: str
    llm_enabled: bool
    rag_enabled: bool
    provider: str


class LLMStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    configured: bool
    base_url: str = ""
    config_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class RagStatusResponse(BaseModel):
    mode: str
    model_name: str
    dependency_available: bool
    initialized: bool
    document_count: int
    error: str = ""


class GameStartRequest(BaseModel):
    player_name: str = "玩家"
    npc_count: int = FIXED_NPC_COUNT
    roles: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_WOLF_ROLES))
    player_role: str = "random"
    variant: str = "classic"
    enable_llm: bool = False
    enable_llm_validation: bool = True
    enable_rag: bool = False
    npc_policy_mode: Literal["rule", "shadow", "local"] = Field(
        default_factory=policy_mode_from_environment
    )


class CharacterState(BaseModel):
    id: int
    name: str
    is_player: bool
    role: str
    camp: str
    alive: bool = True
    idiot_flipped: bool = False
    personality: dict[str, float] = Field(default_factory=dict)
    emotion: dict[str, float] = Field(default_factory=dict)
    suspicion: dict[str, int] = Field(default_factory=dict)
    relationships: dict[str, dict[str, object]] = Field(default_factory=dict)
    memory_summary: str = ""
    strategy_tuning: dict[str, object] = Field(default_factory=dict)


class CharacterView(BaseModel):
    id: int
    name: str
    is_player: bool
    alive: bool
    idiot_flipped: bool = False
    role_visible_to_player: Optional[str] = None
    suspicion_score: int = 0
    suspicion_level: str = "无"
    trust_to_player: Optional[float] = None
    trust_level: str = ""
    memory_count: int = 0
    private_question_used_today: bool = False
    claimed_role: Optional[str] = None
    public_claims: list[str] = Field(default_factory=list)
    is_sheriff: bool = False
    sheriff_campaign_status: str = ""


class PlayerPrivateInfo(BaseModel):
    role: str
    camp: str
    idiot_flipped: bool = False
    last_check_result: Optional[dict[str, object]] = None
    wolf_teammates: list[dict[str, object]] = Field(default_factory=list)
    witch_attacked_target: Optional[dict[str, object]] = None
    witch_antidote_available: bool = False
    witch_poison_available: bool = False
    hunter_can_shoot: bool = False
    action_history: list[str] = Field(default_factory=list)


class NightActionState(BaseModel):
    day: int
    actor_id: int
    action_type: str
    target_id: Optional[int] = None


class VoteState(BaseModel):
    day: int
    voter_id: int
    target_id: int
    reason: str = ""
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    weight: float = 1.0


class WitchDirectiveState(BaseModel):
    """A public, structured suggestion that contains no role truth."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["witch_directive.v1"] = WITCH_DIRECTIVE_SCHEMA_VERSION
    action: Literal["poison", "hold"]
    target_id: Optional[int] = Field(default=None, gt=0)
    reason_kind: Literal["target_suspected", "public_uncertainty", "unspecified"]
    confidence: int = Field(default=50, ge=0, le=100)

    @model_validator(mode="after")
    def validate_action_target(self) -> "WitchDirectiveState":
        if self.action == "poison" and self.target_id is None:
            raise ValueError("a poison directive requires one target")
        if self.action == "hold" and self.target_id is not None:
            raise ValueError("a hold directive must not name a poison target")
        return self


class WitchStrategyDecisionState(BaseModel):
    """Internal audit record for one NPC-witch choice from its legal view."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["witch_strategy_decision.v1"] = (
        WITCH_STRATEGY_SCHEMA_VERSION
    )
    day: int = Field(ge=1)
    actor_id: int = Field(gt=0)
    action_type: Literal["witch_save", "witch_poison", "none"]
    target_id: Optional[int] = Field(default=None, gt=0)
    reason: Literal[
        "first_night_self_save",
        "first_night_save_99",
        "first_night_save_skip",
        "accepted_hold",
        "accepted_poison",
        "own_suspicion",
        "poison_unavailable",
        "no_legal_target",
    ]
    directive_actor_id: Optional[int] = Field(default=None, gt=0)
    directive_action: Optional[Literal["poison", "hold"]] = None
    directive_target_id: Optional[int] = Field(default=None, gt=0)
    directive_accepted: bool = False
    acceptance_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_action_target(self) -> "WitchStrategyDecisionState":
        has_target = self.target_id is not None
        if self.action_type == "none" and has_target:
            raise ValueError("a no-action witch decision must not name a target")
        if self.action_type != "none" and not has_target:
            raise ValueError("a potion action requires one target")
        return self


class SpeechState(BaseModel):
    day: int
    character_id: int
    name: str
    speech: str
    is_player: bool
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""
    phase: str = "DAY_MEETING"
    round: int = 0
    llm_validation_failure_id: str = ""
    decision_intent: str = ""
    focus_target_id: Optional[int] = None
    decision_signal_ids: list[str] = Field(default_factory=list)
    claim_count: int = 0
    decision_plan: dict[str, object] = Field(default_factory=dict)
    public_position: Optional[PublicPositionV1] = None
    witch_directive: Optional[WitchDirectiveState] = None


class PrivateBeliefInfluenceState(BaseModel):
    evidence_id: str = Field(min_length=1)
    target_id: int = Field(gt=0)
    direction: Literal["suspect", "trust"]


class PrivateConversationState(BaseModel):
    day: int
    npc_character_id: int
    question: str
    reply: str
    effective: bool
    llm_validation_failure_id: str = ""
    easter_egg_id: str = ""
    easter_egg_first_time: bool = False
    revealed_role: Optional[str] = None
    belief_influences: list[PrivateBeliefInfluenceState] = Field(
        default_factory=list
    )


class EliminationState(BaseModel):
    day: int
    character_id: int
    cause: str
    source_action: str
    source_actor_ids: list[int] = Field(default_factory=list)
    source_target_id: int


class LLMValidationAttemptState(BaseModel):
    attempt: int
    raw_text: str
    display_text: str
    rejection_reason: str
    passed: bool = False
    sensitive: bool = False


class LLMValidationFailureState(BaseModel):
    failure_id: str
    day: int
    character_id: int
    context_kind: str
    attempts: list[LLMValidationAttemptState] = Field(default_factory=list)


class LLMValidationAttemptView(BaseModel):
    attempt: int
    text: str
    rejection_reason: str
    sensitive: bool = False


class LLMValidationFailureView(BaseModel):
    failure_id: str
    character_id: int
    context_kind: str
    attempts: list[LLMValidationAttemptView] = Field(default_factory=list)


class NightResolutionState(BaseModel):
    day: int
    attacked_target_id: Optional[int] = None
    protected_ids: list[int] = Field(default_factory=list)
    saved_target_id: Optional[int] = None
    poisoned_target_id: Optional[int] = None
    dead_character_ids: list[int] = Field(default_factory=list)


class HunterShotState(BaseModel):
    day: int
    hunter_id: int
    target_id: Optional[int] = None
    trigger: str


class PublicClaimState(BaseModel):
    day: int
    character_id: int
    claim_type: str
    claimed_role: Optional[str] = None
    target_id: Optional[int] = None
    result: str = ""
    source: str = "speech"
    # V5.4 public provenance.  Older V4 snapshots leave these at their
    # defaults; such records remain displayable but are not used to infer
    # sheriff-window chronology.
    phase: str = ""
    window_day: Optional[int] = Field(default=None, ge=1)
    event_sequence: int = Field(default=0, ge=0)


class BadgeFlowState(BaseModel):
    """One public, versioned seer badge-flow promise.

    The shape deliberately contains no truth marker or private role source, so
    a true seer and a fake seer produce indistinguishable public records.
    """

    day: int
    effective_night_day: int
    character_id: int
    version: int
    phase: str
    primary_target_id: int
    secondary_target_id: Optional[int] = None
    claimed_good_anchor_id: Optional[int] = None
    revision_reason: str = "initial"
    reason_target_id: Optional[int] = None
    active: bool = True


class BadgeFlowView(BaseModel):
    day: int
    effective_night_day: int
    character_id: int
    character_name: str
    version: int
    phase: str
    primary_target_id: int
    primary_target_name: str
    secondary_target_id: Optional[int] = None
    secondary_target_name: str = ""
    claimed_good_anchor_id: Optional[int] = None
    claimed_good_anchor_name: str = ""
    good_result_badge_target_id: int
    good_result_badge_target_name: str
    werewolf_result_badge_target_id: Optional[int] = None
    werewolf_result_badge_target_name: str = ""
    werewolf_result_destroys_badge: bool = False
    revision_reason: str
    reason_target_id: Optional[int] = None
    reason_target_name: str = ""
    active: bool = True
    display_text: str


class PublicIntelView(BaseModel):
    """Public-safe key information for the compact in-game accordion.

    This projection intentionally has no internal ``source`` or truth flag.
    A fake seer claim and a real seer claim therefore have the same shape.
    """

    day: int
    category: str
    kind: str
    actor_id: int
    actor_name: str
    target_id: Optional[int] = None
    target_name: str = ""
    claimed_role: Optional[str] = None
    result: str = ""
    display_text: str


class DayMeetingState(BaseModel):
    day: int
    direction: str
    order: list[int] = Field(default_factory=list)
    current_index: int = 0
    completed: bool = False
    order_source: str = "random"
    anchor_character_id: Optional[int] = None
    sheriff_id: Optional[int] = None
    temporary_nomination_target_id: Optional[int] = None
    nomination_target_id: Optional[int] = None


class DayMeetingView(BaseModel):
    active: bool
    direction: str = ""
    order: list[int] = Field(default_factory=list)
    current_speaker_id: Optional[int] = None
    current_position: int = 0
    total_speakers: int = 0
    completed: bool = False
    order_source: str = "random"
    anchor_character_id: Optional[int] = None
    sheriff_id: Optional[int] = None
    temporary_nomination_target_id: Optional[int] = None
    nomination_target_id: Optional[int] = None


class SheriffElectionState(BaseModel):
    day: int = 1
    candidates: list[int] = Field(default_factory=list)
    withdrawn: list[int] = Field(default_factory=list)
    speech_order: list[int] = Field(default_factory=list)
    current_index: int = 0
    runoff_round: int = 0
    runoff_candidates: list[int] = Field(default_factory=list)
    votes: list[VoteState] = Field(default_factory=list)
    completed: bool = False


class SheriffEventState(BaseModel):
    day: int
    event_type: str
    actor_id: Optional[int] = None
    target_id: Optional[int] = None
    context: str = ""
    badge_flow_version: Optional[int] = None
    detail: str = ""


class SheriffView(BaseModel):
    sheriff_id: Optional[int] = None
    badge_destroyed: bool = False
    candidates: list[int] = Field(default_factory=list)
    active_candidates: list[int] = Field(default_factory=list)
    withdrawn: list[int] = Field(default_factory=list)
    current_speaker_id: Optional[int] = None
    speech_order: list[int] = Field(default_factory=list)
    current_position: int = 0
    runoff_round: int = 0
    runoff_candidates: list[int] = Field(default_factory=list)
    player_can_vote: bool = False
    player_vote_ineligible_reason: str = ""
    vote_targets: list[int] = Field(default_factory=list)
    order_anchor_id: Optional[int] = None
    order_anchor_type: str = ""
    order_options: list[str] = Field(default_factory=list)
    temporary_nomination_target_id: Optional[int] = None
    nomination_target_id: Optional[int] = None
    pending_transfer_from_id: Optional[int] = None
    badge_flows: list[BadgeFlowView] = Field(default_factory=list)


class WolfGameState(BaseModel):
    game_id: str
    random_seed: int = Field(default=0, ge=0, le=MAX_GAME_RANDOM_SEED)
    day: int
    phase: str
    player_character_id: int
    characters: list[CharacterState]
    night_actions: list[NightActionState] = Field(default_factory=list)
    votes: list[VoteState] = Field(default_factory=list)
    speeches: list[SpeechState] = Field(default_factory=list)
    private_conversations: list[PrivateConversationState] = Field(default_factory=list)
    eliminations: list[EliminationState] = Field(default_factory=list)
    pending_first_night_eliminations: list[EliminationState] = Field(default_factory=list)
    first_night_result_pending: bool = False
    night_resolutions: list[NightResolutionState] = Field(default_factory=list)
    hunter_shots: list[HunterShotState] = Field(default_factory=list)
    public_claims: list[PublicClaimState] = Field(default_factory=list)
    badge_flows: list[BadgeFlowState] = Field(default_factory=list)
    meeting: Optional[DayMeetingState] = None
    sheriff_id: Optional[int] = None
    sheriff_election: Optional[SheriffElectionState] = None
    sheriff_events: list[SheriffEventState] = Field(default_factory=list)
    badge_destroyed: bool = False
    meeting_order_anchor_id: Optional[int] = None
    meeting_order_anchor_type: str = ""
    pending_badge_transfer_from_id: Optional[int] = None
    pending_badge_continuation: str = ""
    wolf_checked_wolf_used: bool = False
    public_logs: list[str] = Field(default_factory=list)
    player_private_info: dict[str, object] = Field(default_factory=dict)
    role_resources: dict[str, dict[str, object]] = Field(default_factory=dict)
    pending_hunter_id: Optional[int] = None
    pending_hunter_trigger: str = ""
    pending_hunter_continuation: str = ""
    wolf_fake_seer_id: Optional[int] = None
    witch_strategy_decisions: list[WitchStrategyDecisionState] = Field(
        default_factory=list
    )
    llm_validation_failures: list[LLMValidationFailureState] = Field(default_factory=list)
    rule_events: list[GameRuleEventV1] = Field(default_factory=list)
    command_results: dict[str, GameCommandResultV1] = Field(default_factory=dict)
    recovery_config_fingerprint: str = ""
    winner: Optional[str] = None
    winner_reason: str = ""
    llm_enabled: bool = False
    rag_enabled: bool = False
    npc_policy_mode: Literal["rule", "shadow", "local"] = "rule"
    npc_policy_descriptors: dict[str, dict[str, str]] = Field(
        default_factory=dict
    )
    npc_reasoning_states: list[NPCBeliefStateV1] = Field(default_factory=list)
    created_at: str
    updated_at: str


class GameStartResponse(BaseModel):
    game_id: str
    day: int
    phase: str
    player_character_id: int
    characters: list[CharacterView]
    message: str
    llm_enabled: bool = False
    llm_validation_enabled: bool = False
    npc_policy_mode: Literal["rule", "shadow", "local"] = "local"


class GameStateResponse(BaseModel):
    game_id: str
    day: int
    phase: str
    characters: list[CharacterView]
    public_logs: list[str]
    public_intel: list[PublicIntelView] = Field(default_factory=list)
    public_evidence_timeline: PublicEvidenceTimelineV1
    public_evidence_analysis: PublicEvidenceAnalysisV1
    player_private_info: PlayerPrivateInfo
    meeting: DayMeetingView
    sheriff: SheriffView
    winner: Optional[str] = None
    llm_enabled: bool = False
    llm_validation_enabled: bool = False
    npc_policy_mode: Literal["rule", "shadow", "local"] = "local"


class SpectateCharacter(BaseModel):
    """Public-safe character projection for the live spectator page."""

    id: int
    name: str
    is_player: bool
    alive: bool
    is_sheriff: bool = False
    idiot_flipped: bool = False
    claimed_role: Optional[str] = None


class SpectateGameSummary(BaseModel):
    game_id: str
    day: int
    phase: str
    player_name: str = ""
    updated_at: str = ""


class SpectateResponse(BaseModel):
    """Live public snapshot: no hidden roles, private info, or strategy state."""

    game_id: str
    day: int
    phase: str
    winner: Optional[str] = None
    updated_at: str
    characters: list[SpectateCharacter]
    public_logs: list[str]
    public_intel: list[PublicIntelView]
    public_evidence_timeline: PublicEvidenceTimelineV1
    meeting: DayMeetingView
    sheriff: SheriffView


def is_llm_validation_enabled(game_state: WolfGameState) -> bool:
    """Return the creation-sealed per-game semantic validation preference."""

    if not game_state.llm_enabled:
        return False
    if not game_state.rule_events:
        return True

    creation_event = game_state.rule_events[0]
    if creation_event.event_type != "game_created":
        return True
    start_request = creation_event.command.get("start_request")
    if not isinstance(start_request, dict):
        return True
    requested = start_request.get("enable_llm_validation", True)
    return requested if isinstance(requested, bool) else True


def get_llm_validation_attempt_limit(game_state: WolfGameState) -> int:
    return (
        MAX_LLM_VALIDATION_ATTEMPTS
        if is_llm_validation_enabled(game_state)
        else 0
    )


class GameSummaryEvent(BaseModel):
    day: int
    phase: str
    character_ids: list[int] = Field(default_factory=list)
    text: str
    is_private: bool = False


class CharacterGameSummary(BaseModel):
    character_id: int
    name: str
    role: str
    role_label: str
    camp: str
    camp_label: str
    outcome: str
    actions: list[GameSummaryEvent] = Field(default_factory=list)


class GameSummaryResponse(BaseModel):
    game_id: str
    total_days: int
    winner: str
    winner_label: str
    winner_message: str
    characters: list[CharacterGameSummary]
    timeline: list[GameSummaryEvent]
    explainable_review: PostGameExplainableReviewV1
    llm_validation_failures: list[LLMValidationFailureView] = Field(default_factory=list)


class NightActionRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    action_type: str
    target_id: Optional[int] = None


class NightActionResponse(BaseModel):
    success: bool
    message: str


class NightResolveRequest(IdempotentGameCommandRequest):
    game_id: str


class NightResolveResponse(BaseModel):
    game_id: str
    day: int
    dead_characters: list[int]
    is_peaceful_night: Optional[bool]
    result_pending: bool = False
    public_message: str
    player_private_result: dict[str, object] = Field(default_factory=dict)


class HunterShotRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    target_id: Optional[int] = None


class HunterShotResponse(BaseModel):
    success: bool
    hunter_id: int
    target_id: Optional[int] = None
    message: str
    phase: str
    is_game_over: bool
    winner: Optional[str] = None


class ParsedPlayerSpeech(BaseModel):
    mentioned_characters: list[int] = Field(default_factory=list)
    accusations: list[dict[str, object]] = Field(default_factory=list)
    claims: list[dict[str, object]] = Field(default_factory=list)
    supported_ids: list[int] = Field(default_factory=list)
    opposed_ids: list[int] = Field(default_factory=list)
    vote_intent_target_id: Optional[int] = None
    witch_directive: Optional[WitchDirectiveState] = None
    tone: str = "neutral"


class BadgeFlowInput(BaseModel):
    primary_target_id: int = Field(gt=0)
    secondary_target_id: Optional[int] = Field(default=None, gt=0)
    claimed_good_anchor_id: Optional[int] = Field(default=None, gt=0)
    revision_reason: str = "initial"
    reason_target_id: Optional[int] = Field(default=None, gt=0)


class PlayerSpeechRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    speech: str
    temporary_nomination_target_id: Optional[int] = None
    badge_flow: Optional[BadgeFlowInput] = None
    preview_fingerprint: Optional[str] = None


class PlayerSpeechPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game_id: str
    character_id: int
    speech_kind: Literal["day", "sheriff"]
    speech: str
    temporary_nomination_target_id: Optional[int] = None
    badge_flow: Optional[BadgeFlowInput] = None


class PlayerSpeechResponse(BaseModel):
    parsed: ParsedPlayerSpeech
    public_log: str
    state_updates: dict[str, object] = Field(default_factory=dict)


class SheriffSignupRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    run_for_sheriff: bool


class SheriffSignupResponse(BaseModel):
    success: bool
    message: str
    candidates: list[int]
    next_speaker_id: Optional[int] = None


class SheriffSpeechRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    speech: str = ""
    badge_flow: Optional[BadgeFlowInput] = None
    preview_fingerprint: Optional[str] = None


@dataclass(frozen=True)
class PreparedPlayerSpeech:
    preview: PlayerSpeechPreviewResponseV1
    parsed: ParsedPlayerSpeech
    planned_claims: list[PublicClaimState]
    temporary_target_id: Optional[int] = None


class SheriffWithdrawalRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    withdraw: bool = False


class SheriffWithdrawalResponse(BaseModel):
    success: bool
    message: str
    active_candidates: list[int]
    phase: str


class SheriffVoteRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    target_id: Optional[int] = None


class SheriffBallot(BaseModel):
    voter_id: int
    target_id: int


class SheriffVoteResponse(BaseModel):
    ballots: list[SheriffBallot]
    winner_id: Optional[int] = None
    tied_candidate_ids: list[int] = Field(default_factory=list)
    phase: str
    message: str


class SheriffMeetingOrderRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    side: str


class SheriffNominationRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    target_id: int


class BadgeTransferRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    target_id: Optional[int] = None


class SheriffActionResponse(BaseModel):
    success: bool
    message: str
    phase: str


class NpcSpeechItem(BaseModel):
    character_id: int
    name: str
    speech: str
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""
    llm_validation_failure: Optional[LLMValidationFailureView] = None


class SheriffSpeechResponse(BaseModel):
    speech: NpcSpeechItem
    next_speaker_id: Optional[int] = None
    speeches_completed: bool = False


class NpcMemoryUpdate(BaseModel):
    owner_character_id: int
    content: str


class NpcSpeechesRequest(IdempotentGameCommandRequest):
    game_id: str
    day: Optional[int] = None
    respond_to_player: bool = True


class NpcSpeechesResponse(BaseModel):
    speeches: list[NpcSpeechItem]
    memory_updates: list[NpcMemoryUpdate] = Field(default_factory=list)


class NpcSpeechRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int


class NpcSpeechResponse(BaseModel):
    speech: NpcSpeechItem
    memory_update: NpcMemoryUpdate
    next_speaker_id: Optional[int] = None
    meeting_completed: bool = False


class EndFreeActivityRequest(IdempotentGameCommandRequest):
    game_id: str


class EndFreeActivityResponse(BaseModel):
    success: bool
    message: str


class PrivateChatRequest(IdempotentGameCommandRequest):
    game_id: str
    npc_character_id: int
    question: str


class PrivateChatResponse(BaseModel):
    npc_character_id: int
    npc_name: str
    reply: str
    effective: bool
    can_influence_again: bool = False
    knowledge_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""
    llm_validation_failure: Optional[LLMValidationFailureView] = None
    easter_egg_triggered: bool = False
    easter_egg_first_time: bool = False


class NpcVoteDecision(BaseModel):
    character_id: int
    target_id: int
    reason: str
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"


class NpcVoteDecisionsRequest(IdempotentGameCommandRequest):
    game_id: str


class NpcVoteDecisionsResponse(BaseModel):
    npc_votes: list[NpcVoteDecision]


class PlayerVoteRequest(IdempotentGameCommandRequest):
    game_id: str
    character_id: int
    target_id: Optional[int] = None
    reason: str = ""


class PlayerVoteResponse(BaseModel):
    success: bool
    message: str


class VoteResolveRequest(IdempotentGameCommandRequest):
    game_id: str


class VoteResolveResponse(BaseModel):
    exiled_character_id: Optional[int]
    vote_result: dict[str, int]
    public_message: str
    is_game_over: bool
    winner: Optional[str] = None


class VoteBallotDetail(BaseModel):
    voter_id: int
    voter_name: str
    target_id: int
    target_name: str
    reason: str
    weight: float = 1.0
    is_sheriff: bool = False
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"


class SubmitAndResolveVoteResponse(BaseModel):
    exiled_character_id: Optional[int]
    ballots: list[VoteBallotDetail]
    vote_totals: dict[str, float]
    public_message: str
    is_game_over: bool
    phase: str
    winner: Optional[str] = None


DEFAULT_NPC_PROFILE = NPCProfile(
    npc_name="Guide",
    role="小镇向导",
    personality="友好、耐心，喜欢用简单的话解释新系统。",
    knowledge=[
        "这个 Demo 使用 Godot 4 负责 2D 交互。",
        "Python FastAPI 后端负责 NPC 对话、记忆和未来的 RAG。",
        "后续会加入知识库，让 NPC 能回答更多小镇相关问题。",
    ],
)
