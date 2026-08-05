"""Typed contracts for actor-scoped NPC decisions.

The rule engine builds these contexts and remains the source of truth.  An LLM
may only select identifiers exposed by a context; it never creates game facts.
This module intentionally does not import ``main.py`` so it can be reused by
the API layer and by small tests without creating an import cycle.
"""

from __future__ import annotations

from collections.abc import Hashable
from enum import Enum
from typing import Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CONTEXT_SCHEMA_VERSION = "npc_decision_context.v1"
PUBLIC_SPEECH_SCHEMA_VERSION = "public_speech.v1"
LEGACY_PUBLIC_SPEECH_PLAN_SCHEMA_VERSION = "public_speech_plan.v2"
PUBLIC_SPEECH_PLAN_SCHEMA_VERSION = "public_speech_plan.v3"
PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION = "public_speech_continuity.v1"
PUBLIC_POSITION_SCHEMA_VERSION = "public_position.v1"
HashableValue = TypeVar("HashableValue", bound=Hashable)


class StrictDecisionModel(BaseModel):
    """Base configuration shared by every decision contract."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class PublicSpeechIntent(str, Enum):
    """Small, stable intent vocabulary for the first decision milestone."""

    OBSERVE = "observe"
    PRESSURE = "pressure"
    DEFEND = "defend"
    COUNTERCLAIM = "counterclaim"
    REVEAL = "reveal"


class SpeechStance(str, Enum):
    """The actor's public-facing attitude toward one selected focus."""

    SUPPORT = "support"
    OPPOSE = "oppose"
    UNDECIDED = "undecided"


class SignalRead(str, Enum):
    """A bounded interpretation of the selected public action signals."""

    RAISES_SUSPICION = "raises_suspicion"
    REDUCES_SUSPICION = "reduces_suspicion"
    NEEDS_EXPLANATION = "needs_explanation"
    UNCERTAIN = "uncertain"
    MIXED = "mixed"
    NONE = "none"


class QuestionTopic(str, Enum):
    """Topics an NPC may ask about without generating free-form strategy text."""

    CLAIM_BASIS = "claim_basis"
    ACTION_MOTIVE = "action_motive"
    STANCE = "stance"
    VOTE_INTENT = "vote_intent"
    TIMELINE = "timeline"
    CONTRADICTION = "contradiction"
    ROLE_RESULT = "role_result"
    RESPONSE_TO_PRESSURE = "response_to_pressure"


class VerificationCriterion(str, Enum):
    """Observable follow-up facts that may confirm or weaken a read."""

    NEXT_SPEECH_CONSISTENCY = "next_speech_consistency"
    CLAIM_CONSISTENCY = "claim_consistency"
    VOTE_ALIGNMENT = "vote_alignment"
    RESPONSE_QUALITY = "response_quality"
    ROLE_RESULT = "role_result"
    NIGHT_RESULT = "night_result"
    BADGE_ACTION = "badge_action"
    FOLLOW_UP_ACTION = "follow_up_action"


class SpeechTactic(str, Enum):
    """Allowlisted public tactics; ``wolf_*`` values are faction restricted."""

    INFORMATION_PROBE = "information_probe"
    ACTION_AUDIT = "action_audit"
    DIRECT_PRESSURE = "direct_pressure"
    CONDITIONAL_DEFENSE = "conditional_defense"
    CONSISTENCY_CHECK = "consistency_check"
    VOTE_TEST = "vote_test"
    ROLE_REVEAL = "role_reveal"
    ROLE_COUNTERCLAIM = "role_counterclaim"

    WOLF_DISTANCE_TEAMMATE = "wolf_distance_teammate"
    WOLF_BUS_TEAMMATE = "wolf_bus_teammate"
    WOLF_FAKE_CHECK_TEAMMATE = "wolf_fake_check_teammate"
    WOLF_RESCUE_TEAMMATE = "wolf_rescue_teammate"
    WOLF_FRAME_GOOD = "wolf_frame_good"
    WOLF_COUNTERPUSH_GOOD = "wolf_counterpush_good"
    WOLF_FAKE_SEER = "wolf_fake_seer"
    WOLF_FAKE_GOD_CLAIM = "wolf_fake_god_claim"
    WOLF_DEEP_COVER = "wolf_deep_cover"
    WOLF_MISDIRECTION = "wolf_misdirection"


class SpeechContinuityReason(str, Enum):
    """Auditable reason why a plan follows or departs from its stance card."""

    STANCE_ALIGNED = "stance_aligned"
    NEW_PUBLIC_EVIDENCE = "new_public_evidence"
    DETERMINISTIC_VARIANCE = "deterministic_variance"
    AUTHORIZED_CLAIM = "authorized_claim"
    MANDATORY_RULE_RESPONSE = "mandatory_rule_response"
    UNSCORED = "unscored"


class DecisionActorV1(StrictDecisionModel):
    """The private identity and voice information of the acting NPC."""

    id: int = Field(gt=0)
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    faction: str = Field(min_length=1)
    personality: dict[str, float] = Field(default_factory=dict)
    strategy_tuning: dict[str, float] = Field(default_factory=dict)
    speech_style: str = ""
    catchphrases: list[str] = Field(default_factory=list)


class DecisionPublicLogV1(StrictDecisionModel):
    """One log entry that every living participant is allowed to know."""

    id: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DecisionKnowledgeV1(StrictDecisionModel):
    """A fact the actor may use while reasoning.

    Private items may influence strategy, but must not be cited as public
    evidence unless the rule engine later exposes a separate public item.
    """

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    visibility: Literal["public", "private"]


class DecisionEvidenceV1(DecisionKnowledgeV1):
    """A selectable evidence item, with the same visibility rules as knowledge."""


class DecisionSignalV1(StrictDecisionModel):
    """One public action fact or conservative rule-derived assessment."""

    id: str = Field(min_length=1)
    kind: Literal[
        "sheriff_signup",
        "sheriff_skip_signup",
        "sheriff_withdraw",
        "sheriff_continue",
        "sheriff_vote",
        "sheriff_elected",
        "badge_transfer",
        "badge_destroyed",
        "badge_flow",
        "badge_flow_revised",
        "badge_flow_consistency",
        "public_position",
        "seer_check_claim",
        "seer_claim_logic_conflict",
        "seer_claim_logic_support",
        "exile_vote",
        "public_elimination",
        "low_information_speech",
    ]
    category: Literal["fact", "assessment"]
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    actor_id: Optional[int] = Field(default=None, gt=0)
    target_id: Optional[int] = Field(default=None, gt=0)


class LegalTargetV1(StrictDecisionModel):
    """A character the rule engine permits as the speech focus."""

    id: int = Field(gt=0)
    name: str = Field(min_length=1)
    actor_suspicion: int = 0
    public_pressure: int = 0
    trust: float = Field(default=0.5, ge=0.0, le=1.0)
    claimed_role: Optional[str] = Field(default=None, min_length=1)
    is_sheriff: bool = False


class ClaimFactV1(StrictDecisionModel):
    """One atomic public fact approved by the rule engine."""

    claim_type: str = Field(min_length=1)
    claimed_role: Optional[str] = Field(default=None, min_length=1)
    target_id: Optional[int] = Field(default=None, gt=0)
    result: str = ""


class ClaimOptionV1(StrictDecisionModel):
    """An all-or-nothing bundle of public claim facts.

    Bundling lets the rule engine keep related facts together.  For example, a
    seer option can contain both the role claim and its check result so the LLM
    cannot select only half of the approved statement.
    """

    id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    required: bool = False
    facts: list[ClaimFactV1] = Field(min_length=1)


class NPCDecisionContextV1(StrictDecisionModel):
    """Complete actor-scoped input for one public-speech decision."""

    schema_version: Literal["npc_decision_context.v1"]
    task: Literal["public_speech"]
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    actor: DecisionActorV1
    public_logs: list[DecisionPublicLogV1] = Field(default_factory=list)
    legal_knowledge: list[DecisionKnowledgeV1] = Field(default_factory=list)
    private_memory: list[DecisionKnowledgeV1] = Field(default_factory=list)
    evidence: list[DecisionEvidenceV1] = Field(default_factory=list)
    decision_signals: list[DecisionSignalV1] = Field(default_factory=list)
    legal_targets: list[LegalTargetV1] = Field(default_factory=list)
    claim_options: list[ClaimOptionV1] = Field(default_factory=list)
    allowed_intents: list[PublicSpeechIntent] = Field(min_length=1)

    @field_validator("allowed_intents", mode="before")
    @classmethod
    def parse_allowed_intents(cls, value: object) -> object:
        """Accept enum values from decoded LLM JSON while keeping strict IDs."""

        if not isinstance(value, list):
            return value
        return [
            PublicSpeechIntent(item) if isinstance(item, str) else item
            for item in value
        ]


class PublicSpeechDecisionV1(StrictDecisionModel):
    """Private-context strategy selection expected from the first LLM call.

    It deliberately contains no publishable prose.  A separate public-only
    expression call turns the validated selection into character dialogue.
    """

    schema_version: Literal["public_speech.v1"]
    intent: PublicSpeechIntent
    target_id: Optional[int] = Field(default=None, gt=0)
    claim_option_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    signal_ids: list[str] = Field(default_factory=list, max_length=2)

    @field_validator("intent", mode="before")
    @classmethod
    def parse_intent(cls, value: object) -> object:
        """Accept an enum string without weakening strict numeric validation."""

        if isinstance(value, str):
            return PublicSpeechIntent(value)
        return value


class SpeechQuestionV2(StrictDecisionModel):
    """A bounded question aimed at one of the plan's selected targets."""

    target_id: int = Field(gt=0)
    topic: QuestionTopic

    @field_validator("topic", mode="before")
    @classmethod
    def parse_topic(cls, value: object) -> object:
        if isinstance(value, str):
            return QuestionTopic(value)
        return value


class SpeechVerificationV2(StrictDecisionModel):
    """A future public observation used to revisit the current read."""

    target_id: int = Field(gt=0)
    criterion: VerificationCriterion

    @field_validator("criterion", mode="before")
    @classmethod
    def parse_criterion(cls, value: object) -> object:
        if isinstance(value, str):
            return VerificationCriterion(value)
        return value


class PublicSpeechPlanV2(StrictDecisionModel):
    """A complete strategy plan that contains no publishable prose.

    Every nullable field is still required in JSON.  This makes an LLM state
    explicitly that it has no secondary focus, question, or provisional vote,
    instead of silently omitting parts of the strategy contract.
    """

    schema_version: Literal["public_speech_plan.v2"]
    intent: PublicSpeechIntent
    primary_target_id: Optional[int] = Field(gt=0)
    secondary_target_id: Optional[int] = Field(gt=0)
    stance: SpeechStance
    stance_target_id: Optional[int] = Field(gt=0)
    confidence: int = Field(ge=0, le=100)
    signal_read: SignalRead
    question: Optional[SpeechQuestionV2]
    verification: Optional[SpeechVerificationV2]
    provisional_vote_target_id: Optional[int] = Field(gt=0)
    tactic: SpeechTactic
    claim_option_ids: list[str] = Field(max_length=3)
    evidence_ids: list[str] = Field(max_length=3)
    signal_ids: list[str] = Field(max_length=3)

    @field_validator("intent", mode="before")
    @classmethod
    def parse_plan_intent(cls, value: object) -> object:
        if isinstance(value, str):
            return PublicSpeechIntent(value)
        return value

    @field_validator("stance", mode="before")
    @classmethod
    def parse_stance(cls, value: object) -> object:
        if isinstance(value, str):
            return SpeechStance(value)
        return value

    @field_validator("signal_read", mode="before")
    @classmethod
    def parse_signal_read(cls, value: object) -> object:
        if isinstance(value, str):
            return SignalRead(value)
        return value

    @field_validator("tactic", mode="before")
    @classmethod
    def parse_tactic(cls, value: object) -> object:
        if isinstance(value, str):
            return SpeechTactic(value)
        return value


class PublicSpeechPlanV3(PublicSpeechPlanV2):
    """V2 strategy plus an explicit, public-safe continuity explanation."""

    schema_version: Literal["public_speech_plan.v3"]
    continuity_reason: SpeechContinuityReason
    continuity_signal_ids: list[str] = Field(max_length=3)

    @field_validator("continuity_reason", mode="before")
    @classmethod
    def parse_continuity_reason(cls, value: object) -> object:
        if isinstance(value, str):
            return SpeechContinuityReason(value)
        return value


class PublicSpeechContinuityV1(StrictDecisionModel):
    """Actor-scoped stance input for ordinary non-sheriff day speech.

    Belief evidence IDs remain private decision context. Only public signal IDs
    may be copied into a V3 plan and later persisted with a speech.
    """

    schema_version: Literal["public_speech_continuity.v1"] = (
        PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION
    )
    stance_schema_version: Literal["stance_summary.v1"] = "stance_summary.v1"
    actor_id: int = Field(gt=0)
    day: int = Field(ge=1)
    phase: Literal["DAY_MEETING"] = "DAY_MEETING"
    trusted_target_ids: list[int] = Field(max_length=2)
    primary_suspect_id: Optional[int] = Field(gt=0)
    secondary_suspect_id: Optional[int] = Field(gt=0)
    provisional_vote_target_id: Optional[int] = Field(gt=0)
    verification_target_id: Optional[int] = Field(gt=0)
    verification_condition: Optional[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    basis_evidence_ids: list[str]
    previous_position_day: Optional[int] = Field(ge=1)
    new_public_signal_ids: list[str]
    variance_allowed: bool
    mandatory_response: bool

    @field_validator("trusted_target_ids")
    @classmethod
    def validate_trusted_target_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("continuity trusted targets must be unique")
        return value

    @field_validator("basis_evidence_ids", "new_public_signal_ids")
    @classmethod
    def validate_unique_string_ids(cls, value: list[str]) -> list[str]:
        if any(not item for item in value):
            raise ValueError("continuity ids must not be empty")
        if value != sorted(set(value)):
            raise ValueError("continuity ids must be sorted and unique")
        return value


class PublicPositionV1(StrictDecisionModel):
    """Compact public projection of one validated formal speech.

    Python derives this card from an accepted plan, registered public claims,
    and explicit player wording. It is not a second free-form LLM opinion.
    Other NPCs can therefore quote it without reinterpreting a long speech.
    """

    schema_version: Literal["public_position.v1"] = PUBLIC_POSITION_SCHEMA_VERSION
    speaker_id: int = Field(gt=0)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    claimed_role: Optional[str] = Field(default=None, min_length=1)
    seer_support_id: Optional[int] = Field(default=None, gt=0)
    seer_oppose_id: Optional[int] = Field(default=None, gt=0)
    trusted_target_ids: list[int] = Field(default_factory=list, max_length=2)
    suspected_target_ids: list[int] = Field(default_factory=list, max_length=2)
    provisional_vote_target_id: Optional[int] = Field(default=None, gt=0)
    basis_signal_ids: list[str] = Field(default_factory=list, max_length=3)
    question_target_id: Optional[int] = Field(default=None, gt=0)
    question_topic: Optional[QuestionTopic] = None
    change_condition_target_id: Optional[int] = Field(default=None, gt=0)
    change_condition: Optional[VerificationCriterion] = None
    badge_flow_version: Optional[int] = Field(default=None, ge=1)
    confidence: int = Field(default=50, ge=0, le=100)

    @field_validator("trusted_target_ids", "suspected_target_ids")
    @classmethod
    def validate_position_target_ids(cls, value: list[int]) -> list[int]:
        if any(character_id <= 0 for character_id in value):
            raise ValueError("public position target ids must be positive")
        if len(value) != len(set(value)):
            raise ValueError("public position target ids must not repeat")
        return value

    @field_validator("question_topic", mode="before")
    @classmethod
    def parse_position_question_topic(cls, value: object) -> object:
        if isinstance(value, str):
            return QuestionTopic(value)
        return value

    @field_validator("change_condition", mode="before")
    @classmethod
    def parse_position_change_condition(cls, value: object) -> object:
        if isinstance(value, str):
            return VerificationCriterion(value)
        return value

    @model_validator(mode="after")
    def validate_paired_position_fields(self) -> "PublicPositionV1":
        if (self.question_target_id is None) != (self.question_topic is None):
            raise ValueError("question target and topic must be provided together")
        if (self.change_condition_target_id is None) != (
            self.change_condition is None
        ):
            raise ValueError("change-condition target and criterion must be provided together")
        return self


_INTENTS_REQUIRING_TARGET = frozenset(
    {
        PublicSpeechIntent.OBSERVE,
        PublicSpeechIntent.PRESSURE,
        PublicSpeechIntent.DEFEND,
        PublicSpeechIntent.COUNTERCLAIM,
    }
)
_INTENTS_REQUIRING_CLAIM = frozenset(
    {
        PublicSpeechIntent.COUNTERCLAIM,
        PublicSpeechIntent.REVEAL,
    }
)
_GLOBALLY_RELEVANT_SIGNAL_KINDS = frozenset(
    {
        "sheriff_elected",
        "badge_transfer",
        "badge_destroyed",
        "badge_flow",
        "badge_flow_revised",
        "badge_flow_consistency",
        "public_elimination",
    }
)
_WOLF_ONLY_TACTICS = frozenset(
    {
        SpeechTactic.WOLF_DISTANCE_TEAMMATE,
        SpeechTactic.WOLF_BUS_TEAMMATE,
        SpeechTactic.WOLF_FAKE_CHECK_TEAMMATE,
        SpeechTactic.WOLF_RESCUE_TEAMMATE,
        SpeechTactic.WOLF_FRAME_GOOD,
        SpeechTactic.WOLF_COUNTERPUSH_GOOD,
        SpeechTactic.WOLF_FAKE_SEER,
        SpeechTactic.WOLF_FAKE_GOD_CLAIM,
        SpeechTactic.WOLF_DEEP_COVER,
        SpeechTactic.WOLF_MISDIRECTION,
    }
)
_WOLF_TEAMMATE_TARGET_TACTICS = frozenset(
    {
        SpeechTactic.WOLF_DISTANCE_TEAMMATE,
        SpeechTactic.WOLF_BUS_TEAMMATE,
        SpeechTactic.WOLF_FAKE_CHECK_TEAMMATE,
        SpeechTactic.WOLF_RESCUE_TEAMMATE,
    }
)
_WOLF_GOOD_TARGET_TACTICS = frozenset(
    {
        SpeechTactic.WOLF_FRAME_GOOD,
        SpeechTactic.WOLF_COUNTERPUSH_GOOD,
    }
)
_OPPOSING_WOLF_TEAMMATE_TACTICS = frozenset(
    {
        SpeechTactic.WOLF_DISTANCE_TEAMMATE,
        SpeechTactic.WOLF_BUS_TEAMMATE,
        SpeechTactic.WOLF_FAKE_CHECK_TEAMMATE,
    }
)


def validate_public_speech_decision(
    context: NPCDecisionContextV1,
    decision: PublicSpeechDecisionV1,
) -> list[str]:
    """Return every rule-contract violation without changing game state.

    Pydantic validates field shapes first.  This second layer validates the
    decision against the rule-engine-generated allowlists in ``context``.  An
    empty list means the decision is safe to pass to the existing text/fact
    validator; it does not itself mutate claims, logs, memories, or votes.
    """

    errors: list[str] = []

    if decision.intent not in context.allowed_intents:
        errors.append(
            f"intent_not_allowed: {decision.intent.value} is not in allowed_intents"
        )

    duplicate_allowed_intents = _duplicate_values(context.allowed_intents)
    if duplicate_allowed_intents:
        errors.append(
            "duplicate_allowed_intent: "
            + ", ".join(intent.value for intent in duplicate_allowed_intents)
        )

    legal_target_ids = [target.id for target in context.legal_targets]
    duplicate_target_ids = _duplicate_values(legal_target_ids)
    if duplicate_target_ids:
        errors.append(
            "duplicate_legal_target_id: "
            + ", ".join(str(target_id) for target_id in duplicate_target_ids)
        )
    if decision.target_id is not None and decision.target_id not in legal_target_ids:
        errors.append(
            f"target_not_allowed: {decision.target_id} is not in legal_targets"
        )
    if decision.intent in _INTENTS_REQUIRING_TARGET and decision.target_id is None:
        errors.append(f"target_required: intent {decision.intent.value} needs target_id")

    selected_claim_ids = decision.claim_option_ids
    duplicate_selected_claim_ids = _duplicate_values(selected_claim_ids)
    if duplicate_selected_claim_ids:
        errors.append(
            "duplicate_claim_option_id: " + ", ".join(duplicate_selected_claim_ids)
        )

    claim_option_ids = [option.id for option in context.claim_options]
    duplicate_claim_option_ids = _duplicate_values(claim_option_ids)
    if duplicate_claim_option_ids:
        errors.append(
            "duplicate_context_claim_option_id: "
            + ", ".join(duplicate_claim_option_ids)
        )

    allowed_claim_ids = set(claim_option_ids)
    for option_id in selected_claim_ids:
        if option_id not in allowed_claim_ids:
            errors.append(f"claim_option_not_allowed: {option_id}")

    selected_claim_id_set = set(selected_claim_ids)
    for option in context.claim_options:
        if option.required and option.id not in selected_claim_id_set:
            errors.append(f"required_claim_option_missing: {option.id}")

        fact_keys = [
            (fact.claim_type, fact.claimed_role, fact.target_id, fact.result)
            for fact in option.facts
        ]
        if _duplicate_values(fact_keys):
            errors.append(f"duplicate_claim_fact: {option.id}")

    if decision.intent in _INTENTS_REQUIRING_CLAIM and not selected_claim_ids:
        errors.append(
            f"claim_option_required: intent {decision.intent.value} needs a claim option"
        )

    selected_evidence_ids = decision.evidence_ids
    duplicate_selected_evidence_ids = _duplicate_values(selected_evidence_ids)
    if duplicate_selected_evidence_ids:
        errors.append(
            "duplicate_evidence_id: " + ", ".join(duplicate_selected_evidence_ids)
        )

    evidence_ids = [item.id for item in context.evidence]
    duplicate_context_evidence_ids = _duplicate_values(evidence_ids)
    if duplicate_context_evidence_ids:
        errors.append(
            "duplicate_context_evidence_id: "
            + ", ".join(duplicate_context_evidence_ids)
        )

    evidence_by_id = {item.id: item for item in context.evidence}
    for evidence_id in selected_evidence_ids:
        item = evidence_by_id.get(evidence_id)
        if item is None:
            errors.append(f"evidence_not_allowed: {evidence_id}")
        elif item.visibility != "public":
            errors.append(f"private_evidence_not_publishable: {evidence_id}")

    selected_signal_ids = decision.signal_ids
    duplicate_selected_signal_ids = _duplicate_values(selected_signal_ids)
    if duplicate_selected_signal_ids:
        errors.append(
            "duplicate_signal_id: " + ", ".join(duplicate_selected_signal_ids)
        )

    signal_ids = [item.id for item in context.decision_signals]
    duplicate_context_signal_ids = _duplicate_values(signal_ids)
    if duplicate_context_signal_ids:
        errors.append(
            "duplicate_context_signal_id: "
            + ", ".join(duplicate_context_signal_ids)
        )
    signal_by_id = {item.id: item for item in context.decision_signals}
    for signal_id in selected_signal_ids:
        if signal_id not in signal_by_id:
            errors.append(f"signal_not_allowed: {signal_id}")

    ordinary_intents = {
        PublicSpeechIntent.OBSERVE,
        PublicSpeechIntent.PRESSURE,
        PublicSpeechIntent.DEFEND,
    }
    public_evidence_available = any(
        item.visibility == "public" for item in context.evidence
    )
    usable_signal_available = any(
        signal.kind in _GLOBALLY_RELEVANT_SIGNAL_KINDS
        or signal.actor_id in legal_target_ids
        or signal.target_id in legal_target_ids
        for signal in context.decision_signals
    )
    if (
        decision.intent in ordinary_intents
        and (usable_signal_available or public_evidence_available or context.claim_options)
        and not (
            selected_signal_ids
            or selected_evidence_ids
            or selected_claim_ids
        )
    ):
        errors.append(
            "decision_basis_required: select a public signal, evidence, or claim option"
        )

    if decision.target_id is not None and selected_signal_ids:
        selected_signals = [
            signal_by_id[signal_id]
            for signal_id in selected_signal_ids
            if signal_id in signal_by_id
        ]
        unrelated_signal_ids = [
            signal.id
            for signal in selected_signals
            if signal.kind not in _GLOBALLY_RELEVANT_SIGNAL_KINDS
            and decision.target_id not in {signal.actor_id, signal.target_id}
        ]
        if unrelated_signal_ids:
            errors.append(
                "signal_target_mismatch: " + ", ".join(unrelated_signal_ids)
            )

    duplicate_public_log_ids = _duplicate_values(
        [item.id for item in context.public_logs]
    )
    if duplicate_public_log_ids:
        errors.append(
            "duplicate_public_log_id: " + ", ".join(duplicate_public_log_ids)
        )

    duplicate_knowledge_ids = _duplicate_values(
        [item.id for item in context.legal_knowledge]
    )
    if duplicate_knowledge_ids:
        errors.append(
            "duplicate_legal_knowledge_id: " + ", ".join(duplicate_knowledge_ids)
        )

    duplicate_memory_ids = _duplicate_values(
        [item.id for item in context.private_memory]
    )
    if duplicate_memory_ids:
        errors.append(
            "duplicate_private_memory_id: " + ", ".join(duplicate_memory_ids)
        )
    for item in context.private_memory:
        if item.visibility != "private":
            errors.append(f"private_memory_visibility_invalid: {item.id}")

    return errors


def validate_public_speech_plan_v2(
    context: NPCDecisionContextV1,
    plan: PublicSpeechPlanV2,
) -> list[str]:
    """Validate a V2 plan against the rule-engine-owned V1 context.

    The plan is allowed to be strategically wrong.  Validation only enforces
    its shape, legal choices, public-evidence boundary, internal consistency,
    and faction-specific tactic permissions.
    """

    errors: list[str] = []

    if plan.intent not in context.allowed_intents:
        errors.append(
            f"intent_not_allowed: {plan.intent.value} is not in allowed_intents"
        )
    duplicate_allowed_intents = _duplicate_values(context.allowed_intents)
    if duplicate_allowed_intents:
        errors.append(
            "duplicate_allowed_intent: "
            + ", ".join(intent.value for intent in duplicate_allowed_intents)
        )

    legal_target_ids = [target.id for target in context.legal_targets]
    legal_target_id_set = set(legal_target_ids)
    duplicate_target_ids = _duplicate_values(legal_target_ids)
    if duplicate_target_ids:
        errors.append(
            "duplicate_legal_target_id: "
            + ", ".join(str(target_id) for target_id in duplicate_target_ids)
        )

    selected_targets = {
        target_id
        for target_id in [plan.primary_target_id, plan.secondary_target_id]
        if target_id is not None
    }
    target_fields: list[tuple[str, Optional[int]]] = [
        ("primary_target_id", plan.primary_target_id),
        ("secondary_target_id", plan.secondary_target_id),
        ("stance_target_id", plan.stance_target_id),
        ("provisional_vote_target_id", plan.provisional_vote_target_id),
        (
            "question.target_id",
            plan.question.target_id if plan.question is not None else None,
        ),
        (
            "verification.target_id",
            plan.verification.target_id
            if plan.verification is not None
            else None,
        ),
    ]
    for field_name, target_id in target_fields:
        if target_id is not None and target_id not in legal_target_id_set:
            errors.append(
                f"target_not_allowed: {field_name}={target_id} is not in legal_targets"
            )

    if (
        plan.primary_target_id is not None
        and plan.primary_target_id == plan.secondary_target_id
    ):
        errors.append(
            "duplicate_plan_target: secondary_target_id must differ from "
            "primary_target_id"
        )
    if plan.intent in _INTENTS_REQUIRING_TARGET and plan.primary_target_id is None:
        errors.append(
            f"target_required: intent {plan.intent.value} needs primary_target_id"
        )

    if plan.question is not None and plan.question.target_id not in selected_targets:
        errors.append(
            "question_target_mismatch: question.target_id must be a primary or secondary target"
        )
    if (
        plan.verification is not None
        and plan.verification.target_id not in selected_targets
    ):
        errors.append(
            "verification_target_mismatch: verification.target_id must be a "
            "primary or secondary target"
        )
    if (
        plan.stance_target_id is not None
        and plan.stance_target_id not in selected_targets
    ):
        errors.append(
            "stance_target_mismatch: stance_target_id must be a primary or secondary target"
        )

    if plan.stance == SpeechStance.UNDECIDED:
        if plan.stance_target_id is not None:
            errors.append(
                "stance_target_forbidden: undecided stance must use null "
                "stance_target_id"
            )
    elif plan.stance_target_id is None:
        errors.append(
            f"stance_target_required: {plan.stance.value} stance needs stance_target_id"
        )

    if plan.intent == PublicSpeechIntent.OBSERVE:
        if plan.stance != SpeechStance.UNDECIDED:
            errors.append("intent_stance_mismatch: observe intent requires undecided stance")
    elif plan.intent in {
        PublicSpeechIntent.PRESSURE,
        PublicSpeechIntent.COUNTERCLAIM,
    }:
        if plan.stance != SpeechStance.OPPOSE:
            errors.append(
                f"intent_stance_mismatch: {plan.intent.value} intent requires oppose stance"
            )
        if (
            plan.primary_target_id is not None
            and plan.stance_target_id != plan.primary_target_id
        ):
            errors.append(
                f"intent_stance_target_mismatch: {plan.intent.value} must "
                "oppose the primary target"
            )
    elif plan.intent == PublicSpeechIntent.DEFEND:
        if plan.stance != SpeechStance.SUPPORT:
            errors.append("intent_stance_mismatch: defend intent requires support stance")
        if (
            plan.primary_target_id is not None
            and plan.stance_target_id != plan.primary_target_id
        ):
            errors.append(
                "intent_stance_target_mismatch: defend must support the primary target"
            )

    if (
        plan.stance == SpeechStance.SUPPORT
        and plan.stance_target_id is not None
        and plan.provisional_vote_target_id == plan.stance_target_id
    ):
        errors.append(
            "stance_vote_mismatch: cannot provisionally vote for the supported target"
        )

    selected_claim_ids = plan.claim_option_ids
    duplicate_selected_claim_ids = _duplicate_values(selected_claim_ids)
    if duplicate_selected_claim_ids:
        errors.append(
            "duplicate_claim_option_id: " + ", ".join(duplicate_selected_claim_ids)
        )
    claim_option_ids = [option.id for option in context.claim_options]
    duplicate_claim_option_ids = _duplicate_values(claim_option_ids)
    if duplicate_claim_option_ids:
        errors.append(
            "duplicate_context_claim_option_id: "
            + ", ".join(duplicate_claim_option_ids)
        )
    allowed_claim_ids = set(claim_option_ids)
    for option_id in selected_claim_ids:
        if option_id not in allowed_claim_ids:
            errors.append(f"claim_option_not_allowed: {option_id}")
    selected_claim_id_set = set(selected_claim_ids)
    for option in context.claim_options:
        if option.required and option.id not in selected_claim_id_set:
            errors.append(f"required_claim_option_missing: {option.id}")
        fact_keys = [
            (fact.claim_type, fact.claimed_role, fact.target_id, fact.result)
            for fact in option.facts
        ]
        if _duplicate_values(fact_keys):
            errors.append(f"duplicate_claim_fact: {option.id}")
    if plan.intent in _INTENTS_REQUIRING_CLAIM and not selected_claim_ids:
        errors.append(
            f"claim_option_required: intent {plan.intent.value} needs a claim option"
        )
    if selected_claim_ids and plan.intent not in {
        PublicSpeechIntent.REVEAL,
        PublicSpeechIntent.COUNTERCLAIM,
    }:
        errors.append(
            "claim_option_intent_mismatch: selected claims require reveal or counterclaim"
        )

    selected_evidence_ids = plan.evidence_ids
    duplicate_selected_evidence_ids = _duplicate_values(selected_evidence_ids)
    if duplicate_selected_evidence_ids:
        errors.append(
            "duplicate_evidence_id: " + ", ".join(duplicate_selected_evidence_ids)
        )
    evidence_ids = [item.id for item in context.evidence]
    duplicate_context_evidence_ids = _duplicate_values(evidence_ids)
    if duplicate_context_evidence_ids:
        errors.append(
            "duplicate_context_evidence_id: "
            + ", ".join(duplicate_context_evidence_ids)
        )
    evidence_by_id = {item.id: item for item in context.evidence}
    for evidence_id in selected_evidence_ids:
        item = evidence_by_id.get(evidence_id)
        if item is None:
            errors.append(f"evidence_not_allowed: {evidence_id}")
        elif item.visibility != "public":
            errors.append(f"private_evidence_not_publishable: {evidence_id}")

    selected_signal_ids = plan.signal_ids
    duplicate_selected_signal_ids = _duplicate_values(selected_signal_ids)
    if duplicate_selected_signal_ids:
        errors.append(
            "duplicate_signal_id: " + ", ".join(duplicate_selected_signal_ids)
        )
    signal_ids = [item.id for item in context.decision_signals]
    duplicate_context_signal_ids = _duplicate_values(signal_ids)
    if duplicate_context_signal_ids:
        errors.append(
            "duplicate_context_signal_id: "
            + ", ".join(duplicate_context_signal_ids)
        )
    signal_by_id = {item.id: item for item in context.decision_signals}
    for signal_id in selected_signal_ids:
        if signal_id not in signal_by_id:
            errors.append(f"signal_not_allowed: {signal_id}")
    if selected_signal_ids and plan.signal_read == SignalRead.NONE:
        errors.append("signal_read_mismatch: selected signals require a non-none signal_read")
    if not selected_signal_ids and plan.signal_read != SignalRead.NONE:
        errors.append("signal_read_mismatch: non-none signal_read requires a selected signal")

    ordinary_intents = {
        PublicSpeechIntent.OBSERVE,
        PublicSpeechIntent.PRESSURE,
        PublicSpeechIntent.DEFEND,
    }
    public_evidence_available = any(
        item.visibility == "public" for item in context.evidence
    )
    usable_signal_available = any(
        signal.kind in _GLOBALLY_RELEVANT_SIGNAL_KINDS
        or signal.actor_id in legal_target_id_set
        or signal.target_id in legal_target_id_set
        for signal in context.decision_signals
    )
    if (
        plan.intent in ordinary_intents
        and (usable_signal_available or public_evidence_available or context.claim_options)
        and not (selected_signal_ids or selected_evidence_ids or selected_claim_ids)
    ):
        errors.append(
            "decision_basis_required: select a public signal, evidence, or claim option"
        )

    if selected_targets and selected_signal_ids:
        unrelated_signal_ids = [
            signal.id
            for signal_id in selected_signal_ids
            if (signal := signal_by_id.get(signal_id)) is not None
            and signal.kind not in _GLOBALLY_RELEVANT_SIGNAL_KINDS
            and selected_targets.isdisjoint({signal.actor_id, signal.target_id})
        ]
        if unrelated_signal_ids:
            errors.append(
                "signal_target_mismatch: " + ", ".join(unrelated_signal_ids)
            )

    is_wolf_actor = (
        context.actor.role.casefold() == "werewolf"
        or context.actor.faction.casefold() == "werewolf"
    )
    if plan.tactic in _WOLF_ONLY_TACTICS and not is_wolf_actor:
        errors.append(f"wolf_tactic_forbidden: {plan.tactic.value}")

    wolf_teammate_ids = _get_wolf_teammate_ids(context)
    if plan.tactic in _WOLF_TEAMMATE_TARGET_TACTICS:
        if plan.primary_target_id is None:
            errors.append(
                f"tactic_target_required: {plan.tactic.value} needs a primary target"
            )
        elif plan.primary_target_id not in wolf_teammate_ids:
            errors.append(
                "wolf_teammate_tactic_target_invalid: primary target is not "
                "an allowlisted wolf teammate"
            )
    if (
        plan.tactic in _WOLF_GOOD_TARGET_TACTICS
        and plan.primary_target_id is not None
        and plan.primary_target_id in wolf_teammate_ids
    ):
        errors.append(
            "wolf_good_target_tactic_invalid: primary target cannot be a wolf teammate"
        )
    if plan.tactic in _OPPOSING_WOLF_TEAMMATE_TACTICS:
        if plan.stance != SpeechStance.OPPOSE:
            errors.append(
                f"tactic_stance_mismatch: {plan.tactic.value} requires oppose stance"
            )
        if (
            plan.primary_target_id is not None
            and plan.stance_target_id != plan.primary_target_id
        ):
            errors.append(
                f"tactic_stance_target_mismatch: {plan.tactic.value} must "
                "oppose its primary target"
            )
    if plan.tactic == SpeechTactic.WOLF_RESCUE_TEAMMATE:
        if plan.stance != SpeechStance.SUPPORT:
            errors.append(
                "tactic_stance_mismatch: wolf_rescue_teammate requires support stance"
            )
        if (
            plan.primary_target_id is not None
            and plan.stance_target_id != plan.primary_target_id
        ):
            errors.append(
                "tactic_stance_target_mismatch: wolf_rescue_teammate must "
                "support its primary target"
            )

    selected_claim_facts = [
        fact
        for option in context.claim_options
        if option.id in selected_claim_id_set
        for fact in option.facts
    ]
    selected_seer_checks = [
        fact
        for fact in selected_claim_facts
        if fact.claim_type == "seer_check"
        and fact.target_id is not None
        and fact.target_id in legal_target_id_set
    ]
    selected_seer_check = next(
        (
            fact
            for fact in reversed(selected_seer_checks)
            if fact.result == "werewolf"
        ),
        selected_seer_checks[-1] if selected_seer_checks else None,
    )
    if selected_seer_check is not None:
        check_target_id = selected_seer_check.target_id
        if plan.intent == PublicSpeechIntent.COUNTERCLAIM:
            if check_target_id not in selected_targets:
                errors.append(
                    "seer_check_target_mismatch: counterclaim must keep its check target as a selected target"
                )
            selected_role_claims = {
                fact.claimed_role
                for fact in selected_claim_facts
                if fact.claim_type == "role" and fact.claimed_role
            }
            primary_context_target = next(
                (
                    target
                    for target in context.legal_targets
                    if target.id == plan.primary_target_id
                ),
                None,
            )
            if (
                primary_context_target is None
                or primary_context_target.claimed_role not in selected_role_claims
            ):
                errors.append(
                    "counterclaim_target_mismatch: primary target must be a competing claimant of the selected role"
                )
            if (
                selected_seer_check.result == "good"
                and plan.provisional_vote_target_id == check_target_id
            ):
                errors.append(
                    "good_check_vote_mismatch: a good check cannot provisionally vote for its target"
                )
        else:
            if plan.primary_target_id != check_target_id:
                errors.append(
                    "seer_check_target_mismatch: primary target must match the selected check"
                )
            if selected_seer_check.result == "werewolf":
                if (
                    plan.stance != SpeechStance.OPPOSE
                    or plan.stance_target_id != check_target_id
                ):
                    errors.append(
                        "black_check_stance_mismatch: a black check must oppose its target"
                    )
                if plan.provisional_vote_target_id != check_target_id:
                    errors.append(
                        "black_check_vote_mismatch: a black check must provisionally vote for its target"
                    )
            elif selected_seer_check.result == "good":
                if (
                    plan.stance != SpeechStance.SUPPORT
                    or plan.stance_target_id != check_target_id
                ):
                    errors.append(
                        "good_check_stance_mismatch: a good check must support its target"
                    )
                if plan.provisional_vote_target_id == check_target_id:
                    errors.append(
                        "good_check_vote_mismatch: a good check cannot provisionally vote for its target"
                    )
    if plan.tactic == SpeechTactic.WOLF_FAKE_CHECK_TEAMMATE:
        matching_check = any(
            fact.claim_type == "seer_check"
            and fact.target_id == plan.primary_target_id
            and fact.result == "werewolf"
            for fact in selected_claim_facts
        )
        if not matching_check:
            errors.append(
                "wolf_fake_check_claim_missing: tactic requires an allowlisted "
                "black-check claim on the primary target"
            )
        if plan.intent not in {
            PublicSpeechIntent.REVEAL,
            PublicSpeechIntent.COUNTERCLAIM,
        }:
            errors.append(
                "tactic_intent_mismatch: wolf_fake_check_teammate requires "
                "reveal or counterclaim intent"
            )
    if plan.tactic == SpeechTactic.WOLF_FAKE_SEER and not any(
        fact.claim_type == "role" and fact.claimed_role == "seer"
        for fact in selected_claim_facts
    ):
        errors.append(
            "wolf_fake_seer_claim_missing: tactic requires an allowlisted seer role claim"
        )
    if plan.tactic == SpeechTactic.WOLF_FAKE_GOD_CLAIM:
        god_claim_matching = any(
            fact.claim_type == "role"
            and fact.claimed_role in {"guard", "witch", "hunter"}
            for fact in selected_claim_facts
        )
        if not god_claim_matching:
            errors.append(
                "wolf_fake_god_claim_missing: tactic requires an allowlisted "
                "guard/witch/hunter role claim"
            )
        if plan.intent not in {
            PublicSpeechIntent.REVEAL,
            PublicSpeechIntent.COUNTERCLAIM,
        }:
            errors.append(
                "tactic_intent_mismatch: wolf_fake_god_claim requires "
                "reveal or counterclaim intent"
            )
        if any(
            fact.claim_type == "role" and fact.claimed_role == "seer"
            for fact in selected_claim_facts
        ):
            errors.append(
                "tactic_claim_conflict: wolf_fake_god_claim cannot be combined "
                "with a seer role claim"
            )
    if plan.tactic in {
        SpeechTactic.WOLF_FRAME_GOOD,
        SpeechTactic.WOLF_COUNTERPUSH_GOOD,
    }:
        if plan.stance != SpeechStance.OPPOSE:
            errors.append(
                f"tactic_stance_mismatch: {plan.tactic.value} requires oppose stance"
            )
        if plan.stance_target_id != plan.primary_target_id:
            errors.append(
                f"tactic_stance_target_mismatch: {plan.tactic.value} must "
                "oppose its primary target"
            )
    if (
        plan.tactic == SpeechTactic.WOLF_BUS_TEAMMATE
        and plan.provisional_vote_target_id != plan.primary_target_id
    ):
        errors.append(
            "wolf_bus_vote_mismatch: wolf_bus_teammate must provisionally vote "
            "for its primary target"
        )

    if (
        plan.tactic == SpeechTactic.CONDITIONAL_DEFENSE
        and plan.intent != PublicSpeechIntent.DEFEND
    ):
        errors.append(
            "tactic_intent_mismatch: conditional_defense requires defend intent"
        )
    if (
        plan.tactic == SpeechTactic.ROLE_REVEAL
        and plan.intent != PublicSpeechIntent.REVEAL
    ):
        errors.append("tactic_intent_mismatch: role_reveal requires reveal intent")
    if (
        plan.tactic == SpeechTactic.ROLE_COUNTERCLAIM
        and plan.intent != PublicSpeechIntent.COUNTERCLAIM
    ):
        errors.append(
            "tactic_intent_mismatch: role_counterclaim requires counterclaim intent"
        )

    duplicate_public_log_ids = _duplicate_values(
        [item.id for item in context.public_logs]
    )
    if duplicate_public_log_ids:
        errors.append(
            "duplicate_public_log_id: " + ", ".join(duplicate_public_log_ids)
        )
    duplicate_knowledge_ids = _duplicate_values(
        [item.id for item in context.legal_knowledge]
    )
    if duplicate_knowledge_ids:
        errors.append(
            "duplicate_legal_knowledge_id: " + ", ".join(duplicate_knowledge_ids)
        )
    duplicate_memory_ids = _duplicate_values(
        [item.id for item in context.private_memory]
    )
    if duplicate_memory_ids:
        errors.append(
            "duplicate_private_memory_id: " + ", ".join(duplicate_memory_ids)
        )
    for item in context.private_memory:
        if item.visibility != "private":
            errors.append(f"private_memory_visibility_invalid: {item.id}")

    return errors


def validate_public_speech_plan(
    context: NPCDecisionContextV1,
    plan: PublicSpeechPlanV2,
) -> list[str]:
    """Stable short name for the V2 validator."""

    return validate_public_speech_plan_v2(context, plan)


def get_public_speech_continuity_expectation(
    continuity: PublicSpeechContinuityV1,
) -> tuple[str, Optional[int]]:
    """Return the same dominant commitment used by M04-A speech scoring."""

    if continuity.provisional_vote_target_id is not None:
        return "vote", continuity.provisional_vote_target_id
    if continuity.primary_suspect_id is not None:
        return "suspect", continuity.primary_suspect_id
    if continuity.trusted_target_ids:
        return "trust", continuity.trusted_target_ids[0]
    return "none", None


def public_speech_plan_matches_continuity(
    continuity: PublicSpeechContinuityV1,
    plan: PublicSpeechPlanV2,
) -> bool:
    """Compare a plan with the legal stance card's dominant commitment."""

    commitment, target_id = get_public_speech_continuity_expectation(continuity)
    if target_id is None:
        return False
    if commitment in {"vote", "suspect"}:
        return (
            plan.primary_target_id == target_id
            and plan.stance == SpeechStance.OPPOSE
            and plan.stance_target_id == target_id
            and plan.provisional_vote_target_id == target_id
        )
    return (
        plan.primary_target_id == target_id
        and plan.stance == SpeechStance.SUPPORT
        and plan.stance_target_id == target_id
        and plan.provisional_vote_target_id != target_id
    )


def validate_public_speech_continuity(
    context: NPCDecisionContextV1,
    continuity: PublicSpeechContinuityV1,
    plan: PublicSpeechPlanV3,
) -> list[str]:
    """Enforce one explicit legal reason for every stance divergence."""

    errors: list[str] = []
    legal_target_ids = {target.id for target in context.legal_targets}
    if continuity.actor_id != context.actor.id:
        errors.append("continuity_actor_mismatch")
    if continuity.day != context.day or continuity.phase != context.phase:
        errors.append("continuity_transition_mismatch")
    continuity_target_ids = {
        target_id
        for target_id in [
            *continuity.trusted_target_ids,
            continuity.primary_suspect_id,
            continuity.secondary_suspect_id,
            continuity.provisional_vote_target_id,
            continuity.verification_target_id,
        ]
        if target_id is not None
    }
    for target_id in sorted(continuity_target_ids):
        if target_id == context.actor.id or target_id not in legal_target_ids:
            errors.append(f"continuity_target_not_allowed: {target_id}")

    public_signal_ids = {signal.id for signal in context.decision_signals}
    for signal_id in continuity.new_public_signal_ids:
        if signal_id not in public_signal_ids:
            errors.append(f"continuity_new_signal_not_allowed: {signal_id}")
    if len(plan.continuity_signal_ids) != len(set(plan.continuity_signal_ids)):
        errors.append("duplicate_continuity_signal_id")
    for signal_id in plan.continuity_signal_ids:
        if signal_id not in continuity.new_public_signal_ids:
            errors.append(f"continuity_signal_not_new: {signal_id}")
        if signal_id not in plan.signal_ids:
            errors.append(f"continuity_signal_not_selected: {signal_id}")

    commitment, expected_target_id = get_public_speech_continuity_expectation(
        continuity
    )
    aligned = public_speech_plan_matches_continuity(continuity, plan)
    reason = plan.continuity_reason

    if continuity.mandatory_response:
        if reason != SpeechContinuityReason.MANDATORY_RULE_RESPONSE:
            errors.append("continuity_reason_required: mandatory_rule_response")
    elif reason == SpeechContinuityReason.MANDATORY_RULE_RESPONSE:
        errors.append("continuity_mandatory_reason_not_allowed")
    elif plan.claim_option_ids:
        if reason != SpeechContinuityReason.AUTHORIZED_CLAIM:
            errors.append("continuity_reason_required: authorized_claim")
    elif reason == SpeechContinuityReason.AUTHORIZED_CLAIM:
        errors.append("continuity_claim_reason_not_allowed")
    elif expected_target_id is None:
        if reason != SpeechContinuityReason.UNSCORED:
            errors.append("continuity_reason_required: unscored")
    elif aligned:
        if reason != SpeechContinuityReason.STANCE_ALIGNED:
            errors.append("continuity_reason_required: stance_aligned")
    elif reason == SpeechContinuityReason.NEW_PUBLIC_EVIDENCE:
        if not plan.continuity_signal_ids:
            errors.append("continuity_new_evidence_signal_required")
    elif reason == SpeechContinuityReason.DETERMINISTIC_VARIANCE:
        if not continuity.variance_allowed:
            errors.append("continuity_variance_not_allowed")
    else:
        errors.append(
            "continuity_unexplained_change: "
            f"expected {commitment} target {expected_target_id}"
        )

    if (
        reason != SpeechContinuityReason.NEW_PUBLIC_EVIDENCE
        and plan.continuity_signal_ids
    ):
        errors.append("continuity_signal_reason_mismatch")
    return errors


def build_public_speech_plan_v2(
    context: NPCDecisionContextV1,
    decision: PublicSpeechDecisionV1,
    *,
    confidence: int = 50,
) -> PublicSpeechPlanV2:
    """Build a complete conservative V2 plan from an accepted V1 decision."""

    v1_errors = validate_public_speech_decision(context, decision)
    if v1_errors:
        raise ValueError("cannot upgrade invalid V1 decision: " + "; ".join(v1_errors))

    primary_target_id = decision.target_id
    secondary_target_id: Optional[int] = None
    if decision.intent in {
        PublicSpeechIntent.PRESSURE,
        PublicSpeechIntent.COUNTERCLAIM,
    }:
        stance = SpeechStance.OPPOSE
        stance_target_id = primary_target_id
        provisional_vote_target_id = primary_target_id
    elif decision.intent == PublicSpeechIntent.DEFEND:
        stance = SpeechStance.SUPPORT
        stance_target_id = primary_target_id
        provisional_vote_target_id = None
    else:
        stance = SpeechStance.UNDECIDED
        stance_target_id = None
        provisional_vote_target_id = None

    if decision.signal_ids:
        if decision.intent in {
            PublicSpeechIntent.PRESSURE,
            PublicSpeechIntent.COUNTERCLAIM,
        }:
            signal_read = SignalRead.RAISES_SUSPICION
        elif decision.intent == PublicSpeechIntent.DEFEND:
            signal_read = SignalRead.REDUCES_SUSPICION
        else:
            signal_read = SignalRead.UNCERTAIN
    else:
        signal_read = SignalRead.NONE

    selected_claim_facts = [
        fact
        for option in context.claim_options
        if option.id in set(decision.claim_option_ids)
        for fact in option.facts
    ]
    legal_target_ids = {target.id for target in context.legal_targets}
    selected_checks = [
        fact
        for fact in selected_claim_facts
        if fact.claim_type == "seer_check"
        and fact.target_id is not None
        and fact.target_id in legal_target_ids
    ]
    selected_check = next(
        (
            fact
            for fact in reversed(selected_checks)
            if fact.result == "werewolf"
        ),
        selected_checks[-1] if selected_checks else None,
    )
    if selected_check is not None:
        if decision.intent == PublicSpeechIntent.COUNTERCLAIM:
            if selected_check.target_id != primary_target_id:
                secondary_target_id = selected_check.target_id
        else:
            primary_target_id = selected_check.target_id
            stance_target_id = selected_check.target_id
            if selected_check.result == "werewolf":
                stance = SpeechStance.OPPOSE
                provisional_vote_target_id = selected_check.target_id
                signal_read = (
                    SignalRead.RAISES_SUSPICION
                    if decision.signal_ids
                    else SignalRead.NONE
                )
            else:
                stance = SpeechStance.SUPPORT
                provisional_vote_target_id = None
                signal_read = (
                    SignalRead.REDUCES_SUSPICION
                    if decision.signal_ids
                    else SignalRead.NONE
                )

    question_topic_by_intent = {
        PublicSpeechIntent.OBSERVE: QuestionTopic.STANCE,
        PublicSpeechIntent.PRESSURE: QuestionTopic.ACTION_MOTIVE,
        PublicSpeechIntent.DEFEND: QuestionTopic.RESPONSE_TO_PRESSURE,
        PublicSpeechIntent.COUNTERCLAIM: QuestionTopic.CLAIM_BASIS,
        PublicSpeechIntent.REVEAL: QuestionTopic.ROLE_RESULT,
    }
    verification_by_intent = {
        PublicSpeechIntent.OBSERVE: VerificationCriterion.NEXT_SPEECH_CONSISTENCY,
        PublicSpeechIntent.PRESSURE: VerificationCriterion.RESPONSE_QUALITY,
        PublicSpeechIntent.DEFEND: VerificationCriterion.FOLLOW_UP_ACTION,
        PublicSpeechIntent.COUNTERCLAIM: VerificationCriterion.CLAIM_CONSISTENCY,
        PublicSpeechIntent.REVEAL: VerificationCriterion.CLAIM_CONSISTENCY,
    }
    tactic_by_intent = {
        PublicSpeechIntent.OBSERVE: SpeechTactic.INFORMATION_PROBE,
        PublicSpeechIntent.PRESSURE: SpeechTactic.DIRECT_PRESSURE,
        PublicSpeechIntent.DEFEND: SpeechTactic.CONDITIONAL_DEFENSE,
        PublicSpeechIntent.COUNTERCLAIM: SpeechTactic.ROLE_COUNTERCLAIM,
        PublicSpeechIntent.REVEAL: SpeechTactic.ROLE_REVEAL,
    }
    question = (
        SpeechQuestionV2(
            target_id=primary_target_id,
            topic=question_topic_by_intent[decision.intent],
        )
        if primary_target_id is not None
        else None
    )
    verification = (
        SpeechVerificationV2(
            target_id=primary_target_id,
            criterion=verification_by_intent[decision.intent],
        )
        if primary_target_id is not None
        else None
    )
    plan = PublicSpeechPlanV2(
        schema_version=LEGACY_PUBLIC_SPEECH_PLAN_SCHEMA_VERSION,
        intent=decision.intent,
        primary_target_id=primary_target_id,
        secondary_target_id=secondary_target_id,
        stance=stance,
        stance_target_id=stance_target_id,
        confidence=confidence,
        signal_read=signal_read,
        question=question,
        verification=verification,
        provisional_vote_target_id=provisional_vote_target_id,
        tactic=tactic_by_intent[decision.intent],
        claim_option_ids=list(decision.claim_option_ids),
        evidence_ids=list(decision.evidence_ids),
        signal_ids=list(decision.signal_ids),
    )
    v2_errors = validate_public_speech_plan_v2(context, plan)
    if v2_errors:
        raise ValueError("invalid upgraded V2 plan: " + "; ".join(v2_errors))
    return plan


def upgrade_public_speech_decision_v1(
    context: NPCDecisionContextV1,
    decision: PublicSpeechDecisionV1,
    *,
    confidence: int = 50,
) -> PublicSpeechPlanV2:
    """Upgrade a V1 decision without inventing an additional target or fact."""

    return build_public_speech_plan_v2(
        context,
        decision,
        confidence=confidence,
    )


def _get_wolf_teammate_ids(context: NPCDecisionContextV1) -> set[int]:
    """Read teammate allowlist IDs emitted by the rule engine, not free text."""

    prefix = "private:wolf_teammate:"
    teammate_ids: set[int] = set()
    for item in [*context.legal_knowledge, *context.private_memory]:
        if not item.id.startswith(prefix):
            continue
        value = item.id.removeprefix(prefix)
        if value.isdigit() and int(value) > 0:
            teammate_ids.add(int(value))
    return teammate_ids


def _duplicate_values(
    values: list[HashableValue],
) -> list[HashableValue]:
    """Return duplicate values once, preserving their first duplicate order."""

    seen: set[HashableValue] = set()
    duplicates: list[HashableValue] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


__all__ = [
    "CONTEXT_SCHEMA_VERSION",
    "LEGACY_PUBLIC_SPEECH_PLAN_SCHEMA_VERSION",
    "PUBLIC_POSITION_SCHEMA_VERSION",
    "PUBLIC_SPEECH_CONTINUITY_SCHEMA_VERSION",
    "PUBLIC_SPEECH_PLAN_SCHEMA_VERSION",
    "PUBLIC_SPEECH_SCHEMA_VERSION",
    "ClaimFactV1",
    "ClaimOptionV1",
    "DecisionActorV1",
    "DecisionEvidenceV1",
    "DecisionKnowledgeV1",
    "DecisionPublicLogV1",
    "DecisionSignalV1",
    "LegalTargetV1",
    "NPCDecisionContextV1",
    "PublicSpeechDecisionV1",
    "PublicSpeechIntent",
    "PublicSpeechPlanV2",
    "PublicSpeechPlanV3",
    "PublicSpeechContinuityV1",
    "PublicPositionV1",
    "QuestionTopic",
    "SignalRead",
    "SpeechQuestionV2",
    "SpeechStance",
    "SpeechContinuityReason",
    "SpeechTactic",
    "SpeechVerificationV2",
    "VerificationCriterion",
    "build_public_speech_plan_v2",
    "get_public_speech_continuity_expectation",
    "public_speech_plan_matches_continuity",
    "validate_public_speech_decision",
    "validate_public_speech_plan",
    "validate_public_speech_plan_v2",
    "validate_public_speech_continuity",
    "upgrade_public_speech_decision_v1",
]
