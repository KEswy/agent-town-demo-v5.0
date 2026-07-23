"""Public-safe evidence timeline contracts for an in-progress game.

The timeline is a read-only projection.  It deliberately distinguishes what
someone said or promised from actions that the Python rule engine has publicly
confirmed.  It never contains role truth, camp truth, hidden action sources, or
post-game verdicts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


PUBLIC_EVIDENCE_ITEM_SCHEMA_VERSION = "public_evidence_item.v1"
PUBLIC_EVIDENCE_TIMELINE_SCHEMA_VERSION = "public_evidence_timeline.v1"
PUBLIC_COMMITMENT_STATE_SCHEMA_VERSION = "public_commitment_state.v1"
PUBLIC_CONTRADICTION_CANDIDATE_SCHEMA_VERSION = (
    "public_contradiction_candidate.v1"
)
PUBLIC_EVIDENCE_ANALYSIS_SCHEMA_VERSION = "public_evidence_analysis.v1"

PublicEvidenceCategory = Literal["claim", "commitment", "confirmed_action"]
PublicEvidenceVerification = Literal["unverified", "confirmed"]
PublicCommitmentStatus = Literal[
    "active",
    "superseded",
    "fulfilled",
    "invalidated",
    "undetermined",
    "contradicted",
]
PublicCommitmentStatusReason = Literal[
    "awaiting_effective_night",
    "awaiting_public_follow_up",
    "revised_before_effective_night",
    "claimant_unavailable_before_effective_night",
    "target_unavailable_before_effective_night",
    "reported_planned_target",
    "badge_action_matched_published_branch",
    "published_branch_became_unavailable",
    "reported_different_target",
    "badge_action_outside_published_branches",
    "public_follow_up_missing",
    "revised_after_due_without_public_result",
]
PublicContradictionKind = Literal[
    "identity_claim_changed",
    "seer_result_changed",
    "badge_flow_target_mismatch",
    "badge_flow_action_mismatch",
]


class PublicEvidenceItemV1(BaseModel):
    """One public fact-shaped record without any hidden-truth verdict."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public_evidence_item.v1"] = (
        PUBLIC_EVIDENCE_ITEM_SCHEMA_VERSION
    )
    evidence_id: str = Field(
        pattern=r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$"
    )
    sequence: int = Field(ge=1)
    day: int = Field(ge=1)
    category: PublicEvidenceCategory
    kind: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    verification: PublicEvidenceVerification
    actor_id: Optional[int] = Field(default=None, gt=0)
    actor_name: str = ""
    target_id: Optional[int] = Field(default=None, gt=0)
    target_name: str = ""
    related_character_ids: list[int] = Field(default_factory=list)
    public_result: str = ""
    display_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_public_semantics(self) -> "PublicEvidenceItemV1":
        expected_verification = (
            "confirmed" if self.category == "confirmed_action" else "unverified"
        )
        if self.verification != expected_verification:
            raise ValueError(
                "claims and commitments stay unverified; only public actions "
                "may be confirmed"
            )
        if self.actor_id is None and self.actor_name:
            raise ValueError("actor_name requires actor_id")
        if self.actor_id is not None and not self.actor_name.strip():
            raise ValueError("actor_id requires actor_name")
        if self.target_id is None and self.target_name:
            raise ValueError("target_name requires target_id")
        if self.target_id is not None and not self.target_name.strip():
            raise ValueError("target_id requires target_name")
        if any(character_id <= 0 for character_id in self.related_character_ids):
            raise ValueError("related character IDs must be positive")
        if len(set(self.related_character_ids)) != len(self.related_character_ids):
            raise ValueError("related character IDs must be unique")
        for character_id in (self.actor_id, self.target_id):
            if (
                character_id is not None
                and character_id not in self.related_character_ids
            ):
                raise ValueError(
                    "actor and target IDs must be included in related_character_ids"
                )
        return self


class PublicEvidenceTimelineV1(BaseModel):
    """A deterministic projection pinned to the current rule-event cursor."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public_evidence_timeline.v1"] = (
        PUBLIC_EVIDENCE_TIMELINE_SCHEMA_VERSION
    )
    game_id: str = Field(min_length=1)
    projected_event_sequence: int = Field(ge=1)
    item_count: int = Field(ge=0)
    items: list[PublicEvidenceItemV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timeline(self) -> "PublicEvidenceTimelineV1":
        if self.item_count != len(self.items):
            raise ValueError("public evidence item_count does not match items")
        if [item.sequence for item in self.items] != list(
            range(1, len(self.items) + 1)
        ):
            raise ValueError("public evidence sequences must be contiguous")
        evidence_ids = [item.evidence_id for item in self.items]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("public evidence IDs must be unique")
        return self


class PublicCommitmentStateV1(BaseModel):
    """Current public-only lifecycle state for one badge-flow version."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public_commitment_state.v1"] = (
        PUBLIC_COMMITMENT_STATE_SCHEMA_VERSION
    )
    commitment_id: str = Field(pattern=r"^public-commitment:[0-9a-f]{20}$")
    sequence: int = Field(ge=1)
    source_evidence_id: str = Field(
        pattern=r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$"
    )
    day: int = Field(ge=1)
    effective_night_day: int = Field(ge=1)
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    primary_target_id: int = Field(gt=0)
    primary_target_name: str = Field(min_length=1)
    secondary_target_id: Optional[int] = Field(default=None, gt=0)
    secondary_target_name: str = ""
    claimed_good_anchor_id: Optional[int] = Field(default=None, gt=0)
    claimed_good_anchor_name: str = ""
    werewolf_branch_destroys_badge: bool
    version: int = Field(ge=1)
    scope: Literal["badge_flow_primary_and_badge_branches"] = (
        "badge_flow_primary_and_badge_branches"
    )
    status: PublicCommitmentStatus
    status_reason: PublicCommitmentStatusReason
    superseded_by_evidence_id: Optional[str] = Field(
        default=None,
        pattern=r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$",
    )
    resolved_by_evidence_id: Optional[str] = Field(
        default=None,
        pattern=r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$",
    )
    related_evidence_ids: list[str] = Field(default_factory=list)
    judgment: Literal["none"] = "none"
    display_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "PublicCommitmentStateV1":
        allowed_reasons = {
            "active": {
                "awaiting_effective_night",
                "awaiting_public_follow_up",
            },
            "superseded": {"revised_before_effective_night"},
            "fulfilled": {
                "reported_planned_target",
                "badge_action_matched_published_branch",
            },
            "invalidated": {
                "claimant_unavailable_before_effective_night",
                "target_unavailable_before_effective_night",
                "published_branch_became_unavailable",
            },
            "contradicted": {
                "reported_different_target",
                "badge_action_outside_published_branches",
            },
            "undetermined": {
                "public_follow_up_missing",
                "revised_after_due_without_public_result",
            },
        }
        if self.status_reason not in allowed_reasons[self.status]:
            raise ValueError("commitment status and reason do not match")
        if self.status == "superseded" and self.superseded_by_evidence_id is None:
            raise ValueError("a superseded commitment must name its replacement")
        if self.status in {"fulfilled", "contradicted"} and (
            self.resolved_by_evidence_id is None
        ):
            raise ValueError("a resolved commitment must name its public evidence")
        if self.secondary_target_id is None and self.secondary_target_name:
            raise ValueError("secondary target name requires an ID")
        if self.secondary_target_id is not None and not self.secondary_target_name:
            raise ValueError("secondary target ID requires a name")
        if self.claimed_good_anchor_id is None:
            if self.claimed_good_anchor_name:
                raise ValueError("claimed-good anchor name requires an ID")
            if not self.werewolf_branch_destroys_badge:
                raise ValueError("an absent anchor must mean badge destruction")
        else:
            if not self.claimed_good_anchor_name:
                raise ValueError("claimed-good anchor ID requires a name")
            if self.werewolf_branch_destroys_badge:
                raise ValueError("an explicit anchor cannot also destroy the badge")
        if len(set(self.related_evidence_ids)) != len(self.related_evidence_ids):
            raise ValueError("related evidence IDs must be unique")
        return self


class PublicContradictionCandidateV1(BaseModel):
    """A neutral public inconsistency candidate, never an alignment verdict."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public_contradiction_candidate.v1"] = (
        PUBLIC_CONTRADICTION_CANDIDATE_SCHEMA_VERSION
    )
    candidate_id: str = Field(
        pattern=r"^public-contradiction:[a-z_]+:[0-9a-f]{16}$"
    )
    sequence: int = Field(ge=1)
    day: int = Field(ge=1)
    kind: PublicContradictionKind
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    target_id: Optional[int] = Field(default=None, gt=0)
    target_name: str = ""
    earlier_evidence_id: str = Field(
        pattern=r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$"
    )
    later_evidence_id: str = Field(
        pattern=r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$"
    )
    review_status: Literal["needs_review"] = "needs_review"
    judgment: Literal["none"] = "none"
    display_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_candidate(self) -> "PublicContradictionCandidateV1":
        if self.earlier_evidence_id == self.later_evidence_id:
            raise ValueError("a contradiction candidate requires two evidence items")
        if self.target_id is None and self.target_name:
            raise ValueError("target_name requires target_id")
        if self.target_id is not None and not self.target_name:
            raise ValueError("target_id requires target_name")
        return self


class PublicEvidenceAnalysisV1(BaseModel):
    """Commitment and inconsistency analysis over one public timeline cursor."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public_evidence_analysis.v1"] = (
        PUBLIC_EVIDENCE_ANALYSIS_SCHEMA_VERSION
    )
    game_id: str = Field(min_length=1)
    projected_event_sequence: int = Field(ge=1)
    truth_scope: Literal["public_only_no_post_game_truth"] = (
        "public_only_no_post_game_truth"
    )
    commitment_count: int = Field(ge=0)
    contradiction_candidate_count: int = Field(ge=0)
    commitments: list[PublicCommitmentStateV1] = Field(default_factory=list)
    contradiction_candidates: list[PublicContradictionCandidateV1] = Field(
        default_factory=list
    )
    disclaimer: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_analysis(self) -> "PublicEvidenceAnalysisV1":
        if self.commitment_count != len(self.commitments):
            raise ValueError("commitment_count does not match commitments")
        if self.contradiction_candidate_count != len(
            self.contradiction_candidates
        ):
            raise ValueError(
                "contradiction_candidate_count does not match candidates"
            )
        if [item.sequence for item in self.commitments] != list(
            range(1, len(self.commitments) + 1)
        ):
            raise ValueError("commitment sequences must be contiguous")
        if [item.sequence for item in self.contradiction_candidates] != list(
            range(1, len(self.contradiction_candidates) + 1)
        ):
            raise ValueError("contradiction sequences must be contiguous")
        if len({item.commitment_id for item in self.commitments}) != len(
            self.commitments
        ):
            raise ValueError("commitment IDs must be unique")
        if len(
            {item.candidate_id for item in self.contradiction_candidates}
        ) != len(self.contradiction_candidates):
            raise ValueError("contradiction candidate IDs must be unique")
        return self


@dataclass(frozen=True)
class PublicEvidenceDraft:
    """Internal public-only material used to order and identify one item."""

    source_family: str
    source_index: int
    day: int
    phase_rank: int
    source_rank: int
    category: PublicEvidenceCategory
    kind: str
    verification: PublicEvidenceVerification
    actor_id: Optional[int]
    actor_name: str
    target_id: Optional[int]
    target_name: str
    related_character_ids: tuple[int, ...]
    public_result: str
    display_text: str


def _stable_public_digest(payload: dict[str, object], length: int) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:length]


def build_public_commitment_id(source_evidence_id: str) -> str:
    """Identify one lifecycle snapshot from its public commitment record."""

    digest = _stable_public_digest(
        {
            "schema_version": PUBLIC_COMMITMENT_STATE_SCHEMA_VERSION,
            "source_evidence_id": source_evidence_id,
        },
        20,
    )
    return f"public-commitment:{digest}"


def build_public_contradiction_id(
    kind: PublicContradictionKind,
    earlier_evidence_id: str,
    later_evidence_id: str,
) -> str:
    """Identify a neutral candidate from the two public records it links."""

    digest = _stable_public_digest(
        {
            "schema_version": PUBLIC_CONTRADICTION_CANDIDATE_SCHEMA_VERSION,
            "kind": kind,
            "earlier_evidence_id": earlier_evidence_id,
            "later_evidence_id": later_evidence_id,
        },
        16,
    )
    return f"public-contradiction:{kind}:{digest}"


def _stable_evidence_id(draft: PublicEvidenceDraft) -> str:
    """Build an ID from public structure only, never internal claim origin."""

    related_character_ids = list(
        dict.fromkeys(
            character_id
            for character_id in draft.related_character_ids
            if character_id > 0
        )
    )
    identity_payload = {
        "schema_version": PUBLIC_EVIDENCE_ITEM_SCHEMA_VERSION,
        "source_family": draft.source_family,
        "source_index": draft.source_index,
        "day": draft.day,
        "category": draft.category,
        "kind": draft.kind,
        "actor_id": draft.actor_id,
        "target_id": draft.target_id,
        "related_character_ids": related_character_ids,
        "public_result": draft.public_result,
    }
    digest = _stable_public_digest(identity_payload, 64)
    return (
        f"public-evidence:{draft.source_family}:"
        f"{draft.source_index + 1}:{digest[:16]}"
    )


def build_public_evidence_timeline_from_drafts(
    *,
    game_id: str,
    projected_event_sequence: int,
    drafts: list[PublicEvidenceDraft],
) -> PublicEvidenceTimelineV1:
    """Sort public drafts deterministically and assign contiguous sequences."""

    ordered_drafts = sorted(
        drafts,
        key=lambda draft: (
            draft.day,
            draft.phase_rank,
            draft.source_rank,
            draft.source_index,
            draft.kind,
        ),
    )
    items = []
    for sequence, draft in enumerate(ordered_drafts, start=1):
        related_character_ids = list(
            dict.fromkeys(
                character_id
                for character_id in draft.related_character_ids
                if character_id > 0
            )
        )
        items.append(
            PublicEvidenceItemV1(
                evidence_id=_stable_evidence_id(draft),
                sequence=sequence,
                day=draft.day,
                category=draft.category,
                kind=draft.kind,
                verification=draft.verification,
                actor_id=draft.actor_id,
                actor_name=draft.actor_name,
                target_id=draft.target_id,
                target_name=draft.target_name,
                related_character_ids=related_character_ids,
                public_result=draft.public_result,
                display_text=draft.display_text.strip(),
            )
        )
    return PublicEvidenceTimelineV1(
        game_id=game_id,
        projected_event_sequence=projected_event_sequence,
        item_count=len(items),
        items=items,
    )
