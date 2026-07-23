"""Strict post-game explanation contracts.

These models are deliberately separate from the in-progress public evidence
contracts.  Role and camp truth is permitted only after the Python rule engine
has sealed a winner, and every item carries an explicit post-game truth marker.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


POST_GAME_EVIDENCE_REFERENCE_SCHEMA_VERSION = "post_game_evidence_reference.v1"
POST_GAME_DECISION_REVIEW_SCHEMA_VERSION = "post_game_decision_review.v1"
POST_GAME_EXPLAINABLE_REVIEW_SCHEMA_VERSION = "post_game_explainable_review.v1"

PostGameDecisionKind = Literal[
    "public_speech",
    "exile_vote",
    "night_action",
    "hunter_shot",
]
PostGameAssessment = Literal[
    "accurate",
    "mistaken",
    "strategic",
    "neutral",
    "unscored",
]
PostGameErrorCategory = Literal[
    "none",
    "deceived",
    "insufficient_evidence",
    "continuity_break",
    "skill_misuse",
    "deterministic_variance",
    "not_applicable",
]

ASSESSMENT_KEYS = (
    "accurate",
    "mistaken",
    "strategic",
    "neutral",
    "unscored",
)
ERROR_CATEGORY_KEYS = (
    "none",
    "deceived",
    "insufficient_evidence",
    "continuity_break",
    "skill_misuse",
    "deterministic_variance",
    "not_applicable",
)
PUBLIC_EVIDENCE_ID_PATTERN = (
    r"^public-evidence:[a-z0-9_]+:[0-9]+:[0-9a-f]{16}$"
)


class PostGameEvidenceReferenceV1(BaseModel):
    """Human-readable reference to one public evidence timeline item."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["post_game_evidence_reference.v1"] = (
        POST_GAME_EVIDENCE_REFERENCE_SCHEMA_VERSION
    )
    evidence_id: str = Field(pattern=PUBLIC_EVIDENCE_ID_PATTERN)
    day: int = Field(ge=1)
    relation: Literal["prior_public", "later_public"]
    display_text: str = Field(min_length=1)


class PostGameDecisionReviewV1(BaseModel):
    """One persisted decision explained against later post-game truth."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["post_game_decision_review.v1"] = (
        POST_GAME_DECISION_REVIEW_SCHEMA_VERSION
    )
    review_id: str = Field(
        pattern=(
            r"^post-game-review:"
            r"(public_speech|exile_vote|night_action|hunter_shot):[0-9a-f]{20}$"
        )
    )
    sequence: int = Field(ge=1)
    source_ref: str = Field(pattern=r"^[a-z_]+:[0-9]+$")
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    decision_kind: PostGameDecisionKind
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    actor_role: str = Field(min_length=1)
    actor_camp: Literal["good", "werewolf"]
    target_id: Optional[int] = Field(default=None, gt=0)
    target_name: str = ""
    target_role: str = ""
    target_camp: str = ""
    decision_summary: str = Field(min_length=1)
    knowledge_boundary: Literal[
        "recorded_basis_plus_prior_day_public_evidence"
    ] = "recorded_basis_plus_prior_day_public_evidence"
    prior_public_evidence: list[PostGameEvidenceReferenceV1] = Field(
        default_factory=list,
        max_length=6,
    )
    recorded_basis: list[str] = Field(default_factory=list, max_length=8)
    later_public_evidence: list[PostGameEvidenceReferenceV1] = Field(
        default_factory=list,
        max_length=6,
    )
    assessment: PostGameAssessment
    error_category: PostGameErrorCategory
    truth_summary: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    post_game_truth_unlocked: Literal[True] = True

    @model_validator(mode="after")
    def validate_review_semantics(self) -> "PostGameDecisionReviewV1":
        target_fields = [
            self.target_name.strip(),
            self.target_role.strip(),
            self.target_camp.strip(),
        ]
        if self.target_id is None and any(target_fields):
            raise ValueError("target truth fields require target_id")
        if self.target_id is not None:
            if not all(target_fields):
                raise ValueError("target_id requires complete post-game truth fields")
            if self.target_camp not in {"good", "werewolf"}:
                raise ValueError("target_camp must be a known game camp")

        for reference in self.prior_public_evidence:
            if reference.relation != "prior_public" or reference.day >= self.day:
                raise ValueError("prior evidence must come from an earlier day")
        for reference in self.later_public_evidence:
            if reference.relation != "later_public" or reference.day <= self.day:
                raise ValueError("later evidence must come from a later day")
        evidence_ids = [
            reference.evidence_id
            for reference in (
                self.prior_public_evidence + self.later_public_evidence
            )
        ]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("a review must not repeat public evidence IDs")
        if any(not item.strip() for item in self.recorded_basis):
            raise ValueError("recorded basis entries must not be empty")

        mistaken_categories = {
            "deceived",
            "insufficient_evidence",
            "continuity_break",
            "skill_misuse",
            "deterministic_variance",
        }
        if self.assessment == "accurate" and self.error_category != "none":
            raise ValueError("accurate decisions must use the none error category")
        if (
            self.assessment == "mistaken"
            and self.error_category not in mistaken_categories
        ):
            raise ValueError("mistaken decisions require one concrete error category")
        if self.assessment in {"strategic", "neutral", "unscored"} and (
            self.error_category != "not_applicable"
        ):
            raise ValueError("unscored decisions must use not_applicable")
        return self


class PostGameExplainableReviewV1(BaseModel):
    """Deterministic, terminal-only decision review for one complete game."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["post_game_explainable_review.v1"] = (
        POST_GAME_EXPLAINABLE_REVIEW_SCHEMA_VERSION
    )
    game_id: str = Field(min_length=1)
    generated_from_event_sequence: int = Field(ge=1)
    truth_scope: Literal["post_game_truth_unlocked"] = "post_game_truth_unlocked"
    knowledge_scope: Literal[
        "recorded_basis_plus_prior_day_public_evidence"
    ] = "recorded_basis_plus_prior_day_public_evidence"
    review_count: int = Field(ge=0)
    assessment_counts: dict[str, int]
    error_category_counts: dict[str, int]
    items: list[PostGameDecisionReviewV1] = Field(default_factory=list)
    disclaimer: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_complete_review(self) -> "PostGameExplainableReviewV1":
        if self.review_count != len(self.items):
            raise ValueError("review_count does not match items")
        if set(self.assessment_counts) != set(ASSESSMENT_KEYS):
            raise ValueError("assessment_counts must contain the complete vocabulary")
        if set(self.error_category_counts) != set(ERROR_CATEGORY_KEYS):
            raise ValueError(
                "error_category_counts must contain the complete vocabulary"
            )
        if any(value < 0 for value in self.assessment_counts.values()):
            raise ValueError("assessment counts must be non-negative")
        if any(value < 0 for value in self.error_category_counts.values()):
            raise ValueError("error category counts must be non-negative")
        if sum(self.assessment_counts.values()) != self.review_count:
            raise ValueError("assessment counts must sum to review_count")
        if sum(self.error_category_counts.values()) != self.review_count:
            raise ValueError("error category counts must sum to review_count")
        if [item.sequence for item in self.items] != list(
            range(1, len(self.items) + 1)
        ):
            raise ValueError("review item sequences must be contiguous")
        if len({item.review_id for item in self.items}) != len(self.items):
            raise ValueError("review IDs must be unique")
        if any(not item.post_game_truth_unlocked for item in self.items):
            raise ValueError("every item must be marked as post-game truth")
        observed_assessments = {
            key: sum(item.assessment == key for item in self.items)
            for key in ASSESSMENT_KEYS
        }
        observed_errors = {
            key: sum(item.error_category == key for item in self.items)
            for key in ERROR_CATEGORY_KEYS
        }
        if observed_assessments != self.assessment_counts:
            raise ValueError("assessment counts do not match review items")
        if observed_errors != self.error_category_counts:
            raise ValueError("error category counts do not match review items")
        return self


def build_post_game_review_id(
    *,
    decision_kind: PostGameDecisionKind,
    source_ref: str,
    day: int,
    actor_id: int,
    target_id: Optional[int],
) -> str:
    """Derive a stable ID from persisted source coordinates, not prose."""

    payload = {
        "schema_version": POST_GAME_DECISION_REVIEW_SCHEMA_VERSION,
        "decision_kind": decision_kind,
        "source_ref": source_ref,
        "day": day,
        "actor_id": actor_id,
        "target_id": target_id,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:20]
    return f"post-game-review:{decision_kind}:{digest}"
