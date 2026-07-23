"""Deterministic, public-only NPC speech quality measurements.

The evaluator is an offline diagnostic.  It reads completed public speech
records, their persisted public references, and configured voice markers.  It
never reads role/camp truth and never feeds a score back into game decisions.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import main as rules


NPC_SPEECH_NORMALIZATION_SCHEMA_VERSION = "npc_speech_normalization.v1"
NPC_SPEECH_QUALITY_OBSERVATION_SCHEMA_VERSION = (
    "npc_speech_quality_observation.v1"
)
NPC_SPEECH_ACTOR_QUALITY_SCHEMA_VERSION = "npc_speech_actor_quality.v1"
NPC_SPEECH_QUALITY_SCHEMA_VERSION = "npc_speech_quality.v1"
NPC_SPEECH_ACTOR_QUALITY_BATCH_SCHEMA_VERSION = (
    "npc_speech_actor_quality_batch.v1"
)
NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION = "npc_speech_quality_batch.v1"
NEAR_DUPLICATE_THRESHOLD = 0.82


class SpeechQualityModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
    )


class NPCSpeechQualityObservationV1(SpeechQualityModel):
    schema_version: Literal["npc_speech_quality_observation.v1"] = (
        NPC_SPEECH_QUALITY_OBSERVATION_SCHEMA_VERSION
    )
    sequence: int = Field(ge=1)
    source_speech_index: int = Field(ge=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    normalized_text_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    template_text_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_character_count: int = Field(ge=0)
    information_atoms: list[str] = Field(default_factory=list)
    new_information_atoms: list[str] = Field(default_factory=list)
    evidence_reference_count: int = Field(ge=0)
    evidence_cited: bool
    persona_marker_hit_count: int = Field(ge=0)
    persona_marker_hit: bool
    surface_repeat_of_sequence: Optional[int] = Field(default=None, ge=1)
    template_repeat_of_sequence: Optional[int] = Field(default=None, ge=1)
    cross_actor_template_repeat: bool
    max_prior_template_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_observation(self) -> "NPCSpeechQualityObservationV1":
        if self.information_atoms != sorted(set(self.information_atoms)):
            raise ValueError("information atoms must be sorted and unique")
        if self.new_information_atoms != sorted(
            set(self.new_information_atoms)
        ):
            raise ValueError("new information atoms must be sorted and unique")
        if not set(self.new_information_atoms).issubset(self.information_atoms):
            raise ValueError("new information atoms must be a subset of all atoms")
        if self.evidence_cited != (self.evidence_reference_count > 0):
            raise ValueError("evidence citation flag does not match its count")
        if self.persona_marker_hit != (self.persona_marker_hit_count > 0):
            raise ValueError("persona marker flag does not match its count")
        for prior_sequence in (
            self.surface_repeat_of_sequence,
            self.template_repeat_of_sequence,
        ):
            if prior_sequence is not None and prior_sequence >= self.sequence:
                raise ValueError("a repeat must reference an earlier observation")
        if (
            self.cross_actor_template_repeat
            and self.template_repeat_of_sequence is None
        ):
            raise ValueError("cross-actor template repeats require a prior repeat")
        return self


class NPCSpeechActorQualityV1(SpeechQualityModel):
    schema_version: Literal["npc_speech_actor_quality.v1"] = (
        NPC_SPEECH_ACTOR_QUALITY_SCHEMA_VERSION
    )
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    speech_count: int = Field(ge=1)
    unique_surface_count: int = Field(ge=1)
    unique_template_count: int = Field(ge=1)
    within_actor_surface_repeat_count: int = Field(ge=0)
    within_actor_template_repeat_count: int = Field(ge=0)
    within_actor_surface_repeat_rate: float = Field(ge=0.0, le=1.0)
    within_actor_template_repeat_rate: float = Field(ge=0.0, le=1.0)
    evidence_citation_count: int = Field(ge=0)
    evidence_citation_rate: float = Field(ge=0.0, le=1.0)
    information_atom_count: int = Field(ge=0)
    new_information_atom_count: int = Field(ge=0)
    information_increment_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    zero_information_increment_count: int = Field(ge=0)
    zero_information_increment_rate: float = Field(ge=0.0, le=1.0)
    persona_marker_speech_count: int = Field(ge=0)
    persona_marker_speech_rate: float = Field(ge=0.0, le=1.0)
    average_normalized_character_count: float = Field(ge=0.0)

    @model_validator(mode="after")
    def validate_actor_counts(self) -> "NPCSpeechActorQualityV1":
        if self.unique_surface_count > self.speech_count:
            raise ValueError("actor unique surfaces exceed speeches")
        if self.unique_template_count > self.speech_count:
            raise ValueError("actor unique templates exceed speeches")
        if self.unique_surface_count + self.within_actor_surface_repeat_count != (
            self.speech_count
        ):
            raise ValueError("actor surface counts do not conserve speeches")
        if self.unique_template_count + self.within_actor_template_repeat_count != (
            self.speech_count
        ):
            raise ValueError("actor template counts do not conserve speeches")
        if self.evidence_citation_count > self.speech_count:
            raise ValueError("actor citations exceed speeches")
        if self.new_information_atom_count > self.information_atom_count:
            raise ValueError("actor new information exceeds all information")
        if self.zero_information_increment_count > self.speech_count:
            raise ValueError("actor zero-increment count exceeds speeches")
        if self.persona_marker_speech_count > self.speech_count:
            raise ValueError("actor persona markers exceed speeches")
        _validate_rate(
            "actor surface repeat rate",
            self.within_actor_surface_repeat_rate,
            self.within_actor_surface_repeat_count,
            self.speech_count,
        )
        _validate_rate(
            "actor template repeat rate",
            self.within_actor_template_repeat_rate,
            self.within_actor_template_repeat_count,
            self.speech_count,
        )
        _validate_rate(
            "actor evidence citation rate",
            self.evidence_citation_rate,
            self.evidence_citation_count,
            self.speech_count,
        )
        _validate_rate(
            "actor information increment rate",
            self.information_increment_rate,
            self.new_information_atom_count,
            self.information_atom_count,
        )
        _validate_rate(
            "actor zero-information rate",
            self.zero_information_increment_rate,
            self.zero_information_increment_count,
            self.speech_count,
        )
        _validate_rate(
            "actor persona marker rate",
            self.persona_marker_speech_rate,
            self.persona_marker_speech_count,
            self.speech_count,
        )
        return self


class NPCSpeechQualityV1(SpeechQualityModel):
    schema_version: Literal["npc_speech_quality.v1"] = (
        NPC_SPEECH_QUALITY_SCHEMA_VERSION
    )
    normalization_schema_version: Literal["npc_speech_normalization.v1"] = (
        NPC_SPEECH_NORMALIZATION_SCHEMA_VERSION
    )
    scope: Literal["npc_public_speeches_only"] = "npc_public_speeches_only"
    truth_scope: Literal["public_only_no_role_truth"] = (
        "public_only_no_role_truth"
    )
    near_duplicate_threshold: Literal[0.82] = NEAR_DUPLICATE_THRESHOLD
    speech_count: int = Field(ge=0)
    actor_count: int = Field(ge=0)
    phase_counts: dict[str, int]
    unique_surface_count: int = Field(ge=0)
    unique_template_count: int = Field(ge=0)
    surface_repeat_count: int = Field(ge=0)
    template_repeat_count: int = Field(ge=0)
    cross_actor_template_repeat_count: int = Field(ge=0)
    surface_repeat_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    template_repeat_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cross_actor_template_repeat_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    speech_pair_count: int = Field(ge=0)
    near_duplicate_pair_count: int = Field(ge=0)
    near_duplicate_pair_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    cross_actor_pair_count: int = Field(ge=0)
    cross_actor_near_duplicate_pair_count: int = Field(ge=0)
    cross_actor_near_duplicate_pair_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    cross_actor_template_similarity_sum: float = Field(ge=0.0)
    mean_cross_actor_template_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    persona_differentiation_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    evidence_citation_count: int = Field(ge=0)
    evidence_citation_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    information_atom_count: int = Field(ge=0)
    new_information_atom_count: int = Field(ge=0)
    information_increment_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    zero_information_increment_count: int = Field(ge=0)
    zero_information_increment_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    persona_marker_speech_count: int = Field(ge=0)
    persona_marker_speech_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    persona_marker_actor_count: int = Field(ge=0)
    persona_marker_actor_coverage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    actors: list[NPCSpeechActorQualityV1] = Field(default_factory=list)
    observations: list[NPCSpeechQualityObservationV1] = Field(
        default_factory=list
    )
    disclaimer: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_quality_counts(self) -> "NPCSpeechQualityV1":
        if self.speech_count != len(self.observations):
            raise ValueError("speech_count does not match observations")
        if self.actor_count != len(self.actors):
            raise ValueError("actor_count does not match actors")
        if [item.sequence for item in self.observations] != list(
            range(1, len(self.observations) + 1)
        ):
            raise ValueError("speech quality sequences must be contiguous")
        source_indexes = [
            item.source_speech_index for item in self.observations
        ]
        if source_indexes != sorted(set(source_indexes)):
            raise ValueError("source speech indexes must be unique and increasing")
        expected_phase_counts = Counter(
            item.phase for item in self.observations
        )
        if self.phase_counts != {
            key: expected_phase_counts[key]
            for key in sorted(expected_phase_counts)
        }:
            raise ValueError("phase counts do not match observations")
        actor_keys = [(actor.actor_id, actor.actor_name) for actor in self.actors]
        if actor_keys != sorted(set(actor_keys)):
            raise ValueError("speech-quality actors must be unique and sorted")
        observed_actor_keys = {
            (item.actor_id, item.actor_name) for item in self.observations
        }
        if set(actor_keys) != observed_actor_keys:
            raise ValueError("actor summaries do not match observations")
        for actor in self.actors:
            actor_observations = [
                item
                for item in self.observations
                if (item.actor_id, item.actor_name)
                == (actor.actor_id, actor.actor_name)
            ]
            if actor.speech_count != len(actor_observations):
                raise ValueError("actor speech count does not match observations")
            if actor.unique_surface_count != len(
                {item.normalized_text_digest for item in actor_observations}
            ):
                raise ValueError("actor surface count does not match observations")
            if actor.unique_template_count != len(
                {item.template_text_digest for item in actor_observations}
            ):
                raise ValueError("actor template count does not match observations")
            if actor.evidence_citation_count != sum(
                item.evidence_cited for item in actor_observations
            ):
                raise ValueError("actor citation count does not match observations")
            if actor.information_atom_count != sum(
                len(item.information_atoms) for item in actor_observations
            ):
                raise ValueError("actor information count does not match observations")
            if actor.new_information_atom_count != sum(
                len(item.new_information_atoms) for item in actor_observations
            ):
                raise ValueError("actor new-information count does not match observations")
            if actor.zero_information_increment_count != sum(
                not item.new_information_atoms for item in actor_observations
            ):
                raise ValueError("actor zero-information count does not match observations")
            if actor.persona_marker_speech_count != sum(
                item.persona_marker_hit for item in actor_observations
            ):
                raise ValueError("actor persona count does not match observations")
            expected_average_length = _round_metric(
                sum(
                    item.normalized_character_count
                    for item in actor_observations
                )
                / len(actor_observations)
            )
            if actor.average_normalized_character_count != expected_average_length:
                raise ValueError("actor average length does not match observations")
        for observation in self.observations:
            prior_observations = self.observations[: observation.sequence - 1]
            surface_matches = [
                item
                for item in prior_observations
                if item.normalized_text_digest
                == observation.normalized_text_digest
            ]
            template_matches = [
                item
                for item in prior_observations
                if item.template_text_digest == observation.template_text_digest
            ]
            expected_surface_sequence = (
                surface_matches[0].sequence if surface_matches else None
            )
            expected_template_sequence = (
                template_matches[0].sequence if template_matches else None
            )
            if observation.surface_repeat_of_sequence != expected_surface_sequence:
                raise ValueError("surface repeat reference is inconsistent")
            if observation.template_repeat_of_sequence != expected_template_sequence:
                raise ValueError("template repeat reference is inconsistent")
            expected_cross_actor_repeat = any(
                item.actor_id != observation.actor_id
                for item in template_matches
            )
            if (
                observation.cross_actor_template_repeat
                != expected_cross_actor_repeat
            ):
                raise ValueError("cross-actor repeat flag is inconsistent")
            if (observation.sequence == 1) != (
                observation.max_prior_template_similarity is None
            ):
                raise ValueError("prior similarity presence is inconsistent")
        expected_unique_surfaces = len(
            {item.normalized_text_digest for item in self.observations}
        )
        expected_unique_templates = len(
            {item.template_text_digest for item in self.observations}
        )
        if self.unique_surface_count != expected_unique_surfaces:
            raise ValueError("unique surface count does not match observations")
        if self.unique_template_count != expected_unique_templates:
            raise ValueError("unique template count does not match observations")
        if self.unique_surface_count + self.surface_repeat_count != self.speech_count:
            raise ValueError("surface counts do not conserve speeches")
        if self.unique_template_count + self.template_repeat_count != self.speech_count:
            raise ValueError("template counts do not conserve speeches")
        if sum(actor.speech_count for actor in self.actors) != self.speech_count:
            raise ValueError("actor counts do not conserve speeches")
        if self.cross_actor_template_repeat_count > self.template_repeat_count:
            raise ValueError("cross-actor repeats exceed all template repeats")
        if self.surface_repeat_count != sum(
            item.surface_repeat_of_sequence is not None
            for item in self.observations
        ):
            raise ValueError("surface repeat count does not match observations")
        if self.template_repeat_count != sum(
            item.template_repeat_of_sequence is not None
            for item in self.observations
        ):
            raise ValueError("template repeat count does not match observations")
        if self.cross_actor_template_repeat_count != sum(
            item.cross_actor_template_repeat for item in self.observations
        ):
            raise ValueError("cross-actor repeat count does not match observations")
        expected_pair_count = self.speech_count * (self.speech_count - 1) // 2
        if self.speech_pair_count != expected_pair_count:
            raise ValueError("speech pair count does not match observations")
        expected_cross_actor_pairs = sum(
            left.actor_id != right.actor_id
            for left, right in combinations(self.observations, 2)
        )
        if self.cross_actor_pair_count != expected_cross_actor_pairs:
            raise ValueError("cross-actor pair count does not match observations")
        if self.near_duplicate_pair_count > self.speech_pair_count:
            raise ValueError("near-duplicate pairs exceed all speech pairs")
        if (
            self.cross_actor_near_duplicate_pair_count
            > self.cross_actor_pair_count
        ):
            raise ValueError("cross-actor near duplicates exceed eligible pairs")
        if self.evidence_citation_count > self.speech_count:
            raise ValueError("citations exceed speeches")
        if self.evidence_citation_count != sum(
            item.evidence_cited for item in self.observations
        ):
            raise ValueError("citation count does not match observations")
        if self.new_information_atom_count > self.information_atom_count:
            raise ValueError("new information exceeds all information")
        if self.information_atom_count != sum(
            len(item.information_atoms) for item in self.observations
        ):
            raise ValueError("information count does not match observations")
        if self.new_information_atom_count != sum(
            len(item.new_information_atoms) for item in self.observations
        ):
            raise ValueError("new-information count does not match observations")
        if self.zero_information_increment_count > self.speech_count:
            raise ValueError("zero-increment speeches exceed all speeches")
        if self.zero_information_increment_count != sum(
            not item.new_information_atoms for item in self.observations
        ):
            raise ValueError("zero-information count does not match observations")
        if self.persona_marker_speech_count > self.speech_count:
            raise ValueError("persona marker speeches exceed all speeches")
        if self.persona_marker_speech_count != sum(
            item.persona_marker_hit for item in self.observations
        ):
            raise ValueError("persona marker count does not match observations")
        if self.persona_marker_actor_count > self.actor_count:
            raise ValueError("persona marker actors exceed all actors")
        if self.persona_marker_actor_count != sum(
            actor.persona_marker_speech_count > 0 for actor in self.actors
        ):
            raise ValueError("persona marker actor count does not match actors")
        if self.cross_actor_template_similarity_sum > self.cross_actor_pair_count:
            raise ValueError("cross-actor similarity sum exceeds pair count")
        _validate_similarity_summary(
            self.cross_actor_template_similarity_sum,
            self.cross_actor_pair_count,
            self.mean_cross_actor_template_similarity,
            self.persona_differentiation_score,
        )
        for label, value, numerator, denominator in (
            (
                "surface repeat rate",
                self.surface_repeat_rate,
                self.surface_repeat_count,
                self.speech_count,
            ),
            (
                "template repeat rate",
                self.template_repeat_rate,
                self.template_repeat_count,
                self.speech_count,
            ),
            (
                "cross-actor template repeat rate",
                self.cross_actor_template_repeat_rate,
                self.cross_actor_template_repeat_count,
                self.speech_count,
            ),
            (
                "near-duplicate pair rate",
                self.near_duplicate_pair_rate,
                self.near_duplicate_pair_count,
                self.speech_pair_count,
            ),
            (
                "cross-actor near-duplicate pair rate",
                self.cross_actor_near_duplicate_pair_rate,
                self.cross_actor_near_duplicate_pair_count,
                self.cross_actor_pair_count,
            ),
            (
                "evidence citation rate",
                self.evidence_citation_rate,
                self.evidence_citation_count,
                self.speech_count,
            ),
            (
                "information increment rate",
                self.information_increment_rate,
                self.new_information_atom_count,
                self.information_atom_count,
            ),
            (
                "zero-information rate",
                self.zero_information_increment_rate,
                self.zero_information_increment_count,
                self.speech_count,
            ),
            (
                "persona marker rate",
                self.persona_marker_speech_rate,
                self.persona_marker_speech_count,
                self.speech_count,
            ),
            (
                "persona actor coverage",
                self.persona_marker_actor_coverage,
                self.persona_marker_actor_count,
                self.actor_count,
            ),
        ):
            _validate_rate(label, value, numerator, denominator)
        return self


class NPCSpeechActorQualityBatchV1(SpeechQualityModel):
    schema_version: Literal["npc_speech_actor_quality_batch.v1"] = (
        NPC_SPEECH_ACTOR_QUALITY_BATCH_SCHEMA_VERSION
    )
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    game_count: int = Field(ge=1)
    speech_count: int = Field(ge=1)
    within_actor_surface_repeat_count: int = Field(ge=0)
    within_actor_template_repeat_count: int = Field(ge=0)
    within_actor_surface_repeat_rate: float = Field(ge=0.0, le=1.0)
    within_actor_template_repeat_rate: float = Field(ge=0.0, le=1.0)
    evidence_citation_count: int = Field(ge=0)
    evidence_citation_rate: float = Field(ge=0.0, le=1.0)
    information_atom_count: int = Field(ge=0)
    new_information_atom_count: int = Field(ge=0)
    information_increment_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    zero_information_increment_count: int = Field(ge=0)
    zero_information_increment_rate: float = Field(ge=0.0, le=1.0)
    persona_marker_speech_count: int = Field(ge=0)
    persona_marker_speech_rate: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_actor_batch_counts(self) -> "NPCSpeechActorQualityBatchV1":
        if self.within_actor_surface_repeat_count > self.speech_count:
            raise ValueError("batch actor surface repeats exceed speeches")
        if self.within_actor_template_repeat_count > self.speech_count:
            raise ValueError("batch actor template repeats exceed speeches")
        if self.evidence_citation_count > self.speech_count:
            raise ValueError("batch actor citations exceed speeches")
        if self.new_information_atom_count > self.information_atom_count:
            raise ValueError("batch actor new information exceeds all information")
        if self.zero_information_increment_count > self.speech_count:
            raise ValueError("batch actor zero-information count exceeds speeches")
        if self.persona_marker_speech_count > self.speech_count:
            raise ValueError("batch actor persona count exceeds speeches")
        for label, value, numerator, denominator in (
            (
                "batch actor surface repeat rate",
                self.within_actor_surface_repeat_rate,
                self.within_actor_surface_repeat_count,
                self.speech_count,
            ),
            (
                "batch actor template repeat rate",
                self.within_actor_template_repeat_rate,
                self.within_actor_template_repeat_count,
                self.speech_count,
            ),
            (
                "batch actor evidence citation rate",
                self.evidence_citation_rate,
                self.evidence_citation_count,
                self.speech_count,
            ),
            (
                "batch actor information increment rate",
                self.information_increment_rate,
                self.new_information_atom_count,
                self.information_atom_count,
            ),
            (
                "batch actor zero-information rate",
                self.zero_information_increment_rate,
                self.zero_information_increment_count,
                self.speech_count,
            ),
            (
                "batch actor persona marker rate",
                self.persona_marker_speech_rate,
                self.persona_marker_speech_count,
                self.speech_count,
            ),
        ):
            _validate_rate(label, value, numerator, denominator)
        return self


class NPCSpeechQualityBatchV1(SpeechQualityModel):
    schema_version: Literal["npc_speech_quality_batch.v1"] = (
        NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION
    )
    speech_quality_schema_version: Literal["npc_speech_quality.v1"] = (
        NPC_SPEECH_QUALITY_SCHEMA_VERSION
    )
    normalization_schema_version: Literal["npc_speech_normalization.v1"] = (
        NPC_SPEECH_NORMALIZATION_SCHEMA_VERSION
    )
    scope: Literal["npc_public_speeches_only"] = "npc_public_speeches_only"
    truth_scope: Literal["public_only_no_role_truth"] = (
        "public_only_no_role_truth"
    )
    near_duplicate_threshold: Literal[0.82] = NEAR_DUPLICATE_THRESHOLD
    game_count: int = Field(ge=1)
    games_with_npc_speech_count: int = Field(ge=0)
    speech_count: int = Field(ge=0)
    average_speeches_per_game: float = Field(ge=0.0)
    actor_game_count: int = Field(ge=0)
    distinct_actor_count: int = Field(ge=0)
    phase_counts: dict[str, int]
    surface_repeat_count: int = Field(ge=0)
    template_repeat_count: int = Field(ge=0)
    cross_actor_template_repeat_count: int = Field(ge=0)
    surface_repeat_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    template_repeat_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cross_actor_template_repeat_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    speech_pair_count: int = Field(ge=0)
    near_duplicate_pair_count: int = Field(ge=0)
    near_duplicate_pair_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    cross_actor_pair_count: int = Field(ge=0)
    cross_actor_near_duplicate_pair_count: int = Field(ge=0)
    cross_actor_near_duplicate_pair_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    cross_actor_template_similarity_sum: float = Field(ge=0.0)
    mean_cross_actor_template_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    persona_differentiation_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    evidence_citation_count: int = Field(ge=0)
    evidence_citation_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    information_atom_count: int = Field(ge=0)
    new_information_atom_count: int = Field(ge=0)
    information_increment_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    zero_information_increment_count: int = Field(ge=0)
    zero_information_increment_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    persona_marker_speech_count: int = Field(ge=0)
    persona_marker_speech_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    persona_marker_actor_game_count: int = Field(ge=0)
    persona_marker_actor_coverage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    actors: list[NPCSpeechActorQualityBatchV1] = Field(default_factory=list)
    disclaimer: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_batch_counts(self) -> "NPCSpeechQualityBatchV1":
        if self.games_with_npc_speech_count > self.game_count:
            raise ValueError("games with speech exceed all games")
        if (self.speech_count == 0) != (
            self.games_with_npc_speech_count == 0
        ):
            raise ValueError("games-with-speech count is inconsistent")
        if (
            sum(self.phase_counts.values()) != self.speech_count
            or any(not key or value < 0 for key, value in self.phase_counts.items())
        ):
            raise ValueError("batch phase counts do not conserve speeches")
        actor_keys = [(actor.actor_id, actor.actor_name) for actor in self.actors]
        if actor_keys != sorted(set(actor_keys)):
            raise ValueError("batch actors must be unique and sorted")
        if self.distinct_actor_count != len(self.actors):
            raise ValueError("distinct actor count does not match actors")
        if self.actor_game_count != sum(
            actor.game_count for actor in self.actors
        ):
            raise ValueError("actor-game count does not match actors")
        if self.actor_game_count < self.games_with_npc_speech_count:
            raise ValueError("actor-game count is smaller than games with speech")
        if self.distinct_actor_count > self.actor_game_count:
            raise ValueError("distinct actors exceed actor-game samples")
        if self.speech_count != sum(actor.speech_count for actor in self.actors):
            raise ValueError("batch speech count does not match actors")
        if self.persona_marker_actor_game_count > self.actor_game_count:
            raise ValueError("batch persona coverage exceeds actor-game samples")
        if self.surface_repeat_count > self.speech_count:
            raise ValueError("batch surface repeats exceed speeches")
        if self.template_repeat_count > self.speech_count:
            raise ValueError("batch template repeats exceed speeches")
        if self.cross_actor_template_repeat_count > self.template_repeat_count:
            raise ValueError("batch cross-actor repeats exceed template repeats")
        if self.near_duplicate_pair_count > self.speech_pair_count:
            raise ValueError("batch near duplicates exceed speech pairs")
        if self.speech_pair_count > self.speech_count * (self.speech_count - 1) // 2:
            raise ValueError("batch speech pairs exceed the maximum possible count")
        if (
            self.cross_actor_near_duplicate_pair_count
            > self.cross_actor_pair_count
        ):
            raise ValueError("batch cross-actor near duplicates exceed pairs")
        if self.new_information_atom_count > self.information_atom_count:
            raise ValueError("batch new information exceeds all information")
        if self.evidence_citation_count != sum(
            actor.evidence_citation_count for actor in self.actors
        ):
            raise ValueError("batch citation count does not match actors")
        if self.information_atom_count != sum(
            actor.information_atom_count for actor in self.actors
        ):
            raise ValueError("batch information count does not match actors")
        if self.new_information_atom_count != sum(
            actor.new_information_atom_count for actor in self.actors
        ):
            raise ValueError("batch new-information count does not match actors")
        if self.zero_information_increment_count != sum(
            actor.zero_information_increment_count for actor in self.actors
        ):
            raise ValueError("batch zero-information count does not match actors")
        if self.persona_marker_speech_count != sum(
            actor.persona_marker_speech_count for actor in self.actors
        ):
            raise ValueError("batch persona marker count does not match actors")
        if self.cross_actor_template_similarity_sum > self.cross_actor_pair_count:
            raise ValueError("batch similarity sum exceeds cross-actor pairs")
        _validate_similarity_summary(
            self.cross_actor_template_similarity_sum,
            self.cross_actor_pair_count,
            self.mean_cross_actor_template_similarity,
            self.persona_differentiation_score,
        )
        expected_average = _round_metric(self.speech_count / self.game_count)
        if self.average_speeches_per_game != expected_average:
            raise ValueError("average speeches per game is inconsistent")
        for label, value, numerator, denominator in (
            (
                "batch surface repeat rate",
                self.surface_repeat_rate,
                self.surface_repeat_count,
                self.speech_count,
            ),
            (
                "batch template repeat rate",
                self.template_repeat_rate,
                self.template_repeat_count,
                self.speech_count,
            ),
            (
                "batch cross-actor template repeat rate",
                self.cross_actor_template_repeat_rate,
                self.cross_actor_template_repeat_count,
                self.speech_count,
            ),
            (
                "batch near-duplicate pair rate",
                self.near_duplicate_pair_rate,
                self.near_duplicate_pair_count,
                self.speech_pair_count,
            ),
            (
                "batch cross-actor near-duplicate pair rate",
                self.cross_actor_near_duplicate_pair_rate,
                self.cross_actor_near_duplicate_pair_count,
                self.cross_actor_pair_count,
            ),
            (
                "batch evidence citation rate",
                self.evidence_citation_rate,
                self.evidence_citation_count,
                self.speech_count,
            ),
            (
                "batch information increment rate",
                self.information_increment_rate,
                self.new_information_atom_count,
                self.information_atom_count,
            ),
            (
                "batch zero-information rate",
                self.zero_information_increment_rate,
                self.zero_information_increment_count,
                self.speech_count,
            ),
            (
                "batch persona marker rate",
                self.persona_marker_speech_rate,
                self.persona_marker_speech_count,
                self.speech_count,
            ),
            (
                "batch persona actor coverage",
                self.persona_marker_actor_coverage,
                self.persona_marker_actor_game_count,
                self.actor_game_count,
            ),
        ):
            _validate_rate(label, value, numerator, denominator)
        return self


def normalize_speech_text(text: str) -> str:
    """NFKC, lowercase, then retain only letters and numbers."""

    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    return "".join(character for character in normalized if character.isalnum())


def canonicalize_speech_template(
    text: str,
    characters: list[rules.CharacterState],
) -> str:
    """Remove public character names/seat numbers before template comparison."""

    normalized = normalize_speech_text(text)
    replacement = "角色"
    variants: list[str] = []
    for character in characters:
        variants.extend(
            [
                normalize_speech_text(f"{character.id}号{character.name}"),
                normalize_speech_text(character.name),
            ]
        )
    for variant in sorted(set(variants), key=lambda item: (-len(item), item)):
        if variant:
            normalized = normalized.replace(variant, replacement)
    normalized = re.sub(r"\d{1,2}号", replacement, normalized)
    normalized = re.sub(r"\d+", "数", normalized)
    return normalized


def build_npc_speech_quality(
    game_state: rules.WolfGameState,
) -> NPCSpeechQualityV1:
    """Measure one completed game without consulting hidden role truth."""

    if game_state.phase != "GAME_OVER" or game_state.winner is None:
        raise ValueError("NPC speech quality requires a completed game")

    characters = sorted(game_state.characters, key=lambda item: item.id)
    character_by_id = {character.id: character for character in characters}
    known_information_atoms: set[str] = set()
    surface_first_sequence: dict[str, int] = {}
    template_first_sequence: dict[str, int] = {}
    template_prior_actor_ids: dict[str, set[int]] = defaultdict(set)
    prior_npc_templates: list[str] = []
    observations: list[NPCSpeechQualityObservationV1] = []
    normalized_surfaces: list[str] = []
    normalized_templates: list[str] = []

    for source_index, speech in enumerate(game_state.speeches, start=1):
        actor = character_by_id.get(speech.character_id)
        if actor is None:
            raise ValueError("speech references an unknown character")
        if speech.is_player != actor.is_player:
            raise ValueError("speech player marker does not match its character")
        information_atoms = _build_information_atoms(speech)
        new_information_atoms = sorted(
            information_atoms.difference(known_information_atoms)
        )
        known_information_atoms.update(information_atoms)
        if actor.is_player:
            continue

        normalized_text = normalize_speech_text(speech.speech)
        template_text = canonicalize_speech_template(
            speech.speech,
            characters,
        )
        sequence = len(observations) + 1
        surface_repeat_of = surface_first_sequence.get(normalized_text)
        template_repeat_of = template_first_sequence.get(template_text)
        prior_template_actors = template_prior_actor_ids.get(template_text, set())
        cross_actor_repeat = any(
            prior_actor_id != actor.id
            for prior_actor_id in prior_template_actors
        )
        max_prior_similarity = (
            max(
                _template_similarity(template_text, prior_template)
                for prior_template in prior_npc_templates
            )
            if prior_npc_templates
            else None
        )
        reference_ids = _build_reference_ids(speech)
        persona_markers = _configured_persona_markers(actor.name)
        marker_hit_count = sum(
            marker in normalized_text
            for marker in persona_markers
            if marker
        )
        observations.append(
            NPCSpeechQualityObservationV1(
                sequence=sequence,
                source_speech_index=source_index,
                day=speech.day,
                phase=speech.phase,
                actor_id=actor.id,
                actor_name=actor.name,
                normalized_text_digest=_digest(normalized_text),
                template_text_digest=_digest(template_text),
                normalized_character_count=len(normalized_text),
                information_atoms=sorted(information_atoms),
                new_information_atoms=new_information_atoms,
                evidence_reference_count=len(reference_ids),
                evidence_cited=bool(reference_ids),
                persona_marker_hit_count=marker_hit_count,
                persona_marker_hit=marker_hit_count > 0,
                surface_repeat_of_sequence=surface_repeat_of,
                template_repeat_of_sequence=template_repeat_of,
                cross_actor_template_repeat=cross_actor_repeat,
                max_prior_template_similarity=(
                    _round_metric(max_prior_similarity)
                    if max_prior_similarity is not None
                    else None
                ),
            )
        )
        surface_first_sequence.setdefault(normalized_text, sequence)
        template_first_sequence.setdefault(template_text, sequence)
        template_prior_actor_ids[template_text].add(actor.id)
        prior_npc_templates.append(template_text)
        normalized_surfaces.append(normalized_text)
        normalized_templates.append(template_text)

    actors = _build_actor_quality(observations)
    phase_counts = Counter(observation.phase for observation in observations)
    speech_pair_count = 0
    near_duplicate_pair_count = 0
    cross_actor_pair_count = 0
    cross_actor_near_duplicate_pair_count = 0
    cross_actor_similarity_sum = 0.0
    for left, right in combinations(observations, 2):
        speech_pair_count += 1
        left_template = normalized_templates[left.sequence - 1]
        right_template = normalized_templates[right.sequence - 1]
        similarity = _template_similarity(left_template, right_template)
        if similarity >= NEAR_DUPLICATE_THRESHOLD:
            near_duplicate_pair_count += 1
        if left.actor_id != right.actor_id:
            cross_actor_pair_count += 1
            cross_actor_similarity_sum += similarity
            if similarity >= NEAR_DUPLICATE_THRESHOLD:
                cross_actor_near_duplicate_pair_count += 1

    speech_count = len(observations)
    surface_repeat_count = speech_count - len(set(normalized_surfaces))
    template_repeat_count = speech_count - len(set(normalized_templates))
    cross_actor_template_repeat_count = sum(
        observation.cross_actor_template_repeat
        for observation in observations
    )
    evidence_citation_count = sum(
        observation.evidence_cited for observation in observations
    )
    information_atom_count = sum(
        len(observation.information_atoms) for observation in observations
    )
    new_information_atom_count = sum(
        len(observation.new_information_atoms) for observation in observations
    )
    zero_information_increment_count = sum(
        not observation.new_information_atoms for observation in observations
    )
    persona_marker_speech_count = sum(
        observation.persona_marker_hit for observation in observations
    )
    persona_marker_actor_count = sum(
        actor.persona_marker_speech_count > 0 for actor in actors
    )
    mean_cross_actor_similarity = _mean_from_sum(
        cross_actor_similarity_sum,
        cross_actor_pair_count,
    )
    return NPCSpeechQualityV1(
        near_duplicate_threshold=NEAR_DUPLICATE_THRESHOLD,
        speech_count=speech_count,
        actor_count=len(actors),
        phase_counts={key: phase_counts[key] for key in sorted(phase_counts)},
        unique_surface_count=len(set(normalized_surfaces)),
        unique_template_count=len(set(normalized_templates)),
        surface_repeat_count=surface_repeat_count,
        template_repeat_count=template_repeat_count,
        cross_actor_template_repeat_count=cross_actor_template_repeat_count,
        surface_repeat_rate=_rate(surface_repeat_count, speech_count),
        template_repeat_rate=_rate(template_repeat_count, speech_count),
        cross_actor_template_repeat_rate=_rate(
            cross_actor_template_repeat_count,
            speech_count,
        ),
        speech_pair_count=speech_pair_count,
        near_duplicate_pair_count=near_duplicate_pair_count,
        near_duplicate_pair_rate=_rate(
            near_duplicate_pair_count,
            speech_pair_count,
        ),
        cross_actor_pair_count=cross_actor_pair_count,
        cross_actor_near_duplicate_pair_count=(
            cross_actor_near_duplicate_pair_count
        ),
        cross_actor_near_duplicate_pair_rate=_rate(
            cross_actor_near_duplicate_pair_count,
            cross_actor_pair_count,
        ),
        cross_actor_template_similarity_sum=_round_metric(
            cross_actor_similarity_sum
        ),
        mean_cross_actor_template_similarity=mean_cross_actor_similarity,
        persona_differentiation_score=(
            _round_metric(1.0 - mean_cross_actor_similarity)
            if mean_cross_actor_similarity is not None
            else None
        ),
        evidence_citation_count=evidence_citation_count,
        evidence_citation_rate=_rate(evidence_citation_count, speech_count),
        information_atom_count=information_atom_count,
        new_information_atom_count=new_information_atom_count,
        information_increment_rate=_rate(
            new_information_atom_count,
            information_atom_count,
        ),
        zero_information_increment_count=zero_information_increment_count,
        zero_information_increment_rate=_rate(
            zero_information_increment_count,
            speech_count,
        ),
        persona_marker_speech_count=persona_marker_speech_count,
        persona_marker_speech_rate=_rate(
            persona_marker_speech_count,
            speech_count,
        ),
        persona_marker_actor_count=persona_marker_actor_count,
        persona_marker_actor_coverage=_rate(
            persona_marker_actor_count,
            len(actors),
        ),
        actors=actors,
        observations=observations,
        disclaimer=(
            "这是规则外的离线表达质量代理：不读取真实身份，不评价发言真假，也不参与"
            "任何实时决策。模板相似度会去除公开姓名和座位号；人设差异分只衡量文本"
            "表面差异，不等同于玩家对角色的主观辨识度。"
        ),
    )


def aggregate_npc_speech_quality(
    reports: list[dict[str, object] | NPCSpeechQualityV1],
) -> NPCSpeechQualityBatchV1:
    """Aggregate raw counts across games before deriving weighted rates."""

    if not reports:
        raise ValueError("NPC speech quality batch requires at least one game")
    parsed_reports = [
        NPCSpeechQualityV1.model_validate(
            report.model_dump(mode="python")
            if isinstance(report, NPCSpeechQualityV1)
            else report
        )
        for report in reports
    ]
    phase_counts: Counter[str] = Counter()
    actor_totals: dict[tuple[int, str], Counter[str]] = defaultdict(Counter)
    numeric_fields = (
        "speech_count",
        "surface_repeat_count",
        "template_repeat_count",
        "cross_actor_template_repeat_count",
        "speech_pair_count",
        "near_duplicate_pair_count",
        "cross_actor_pair_count",
        "cross_actor_near_duplicate_pair_count",
        "evidence_citation_count",
        "information_atom_count",
        "new_information_atom_count",
        "zero_information_increment_count",
        "persona_marker_speech_count",
    )
    totals: Counter[str] = Counter()
    cross_actor_similarity_sum = 0.0
    actor_game_count = 0
    persona_marker_actor_game_count = 0
    games_with_speech = 0
    for report in parsed_reports:
        if report.speech_count > 0:
            games_with_speech += 1
        phase_counts.update(report.phase_counts)
        actor_game_count += report.actor_count
        persona_marker_actor_game_count += report.persona_marker_actor_count
        cross_actor_similarity_sum += report.cross_actor_template_similarity_sum
        for field_name in numeric_fields:
            totals[field_name] += int(getattr(report, field_name))
        for actor in report.actors:
            actor_total = actor_totals[(actor.actor_id, actor.actor_name)]
            actor_total["game_count"] += 1
            actor_total["speech_count"] += actor.speech_count
            actor_total["within_actor_surface_repeat_count"] += (
                actor.within_actor_surface_repeat_count
            )
            actor_total["within_actor_template_repeat_count"] += (
                actor.within_actor_template_repeat_count
            )
            actor_total["evidence_citation_count"] += actor.evidence_citation_count
            actor_total["information_atom_count"] += actor.information_atom_count
            actor_total["new_information_atom_count"] += (
                actor.new_information_atom_count
            )
            actor_total["zero_information_increment_count"] += (
                actor.zero_information_increment_count
            )
            actor_total["persona_marker_speech_count"] += (
                actor.persona_marker_speech_count
            )

    actors: list[NPCSpeechActorQualityBatchV1] = []
    for (actor_id, actor_name), total in sorted(actor_totals.items()):
        speech_count = total["speech_count"]
        actors.append(
            NPCSpeechActorQualityBatchV1(
                actor_id=actor_id,
                actor_name=actor_name,
                game_count=total["game_count"],
                speech_count=speech_count,
                within_actor_surface_repeat_count=total[
                    "within_actor_surface_repeat_count"
                ],
                within_actor_template_repeat_count=total[
                    "within_actor_template_repeat_count"
                ],
                within_actor_surface_repeat_rate=_rate_required(
                    total["within_actor_surface_repeat_count"],
                    speech_count,
                ),
                within_actor_template_repeat_rate=_rate_required(
                    total["within_actor_template_repeat_count"],
                    speech_count,
                ),
                evidence_citation_count=total["evidence_citation_count"],
                evidence_citation_rate=_rate_required(
                    total["evidence_citation_count"],
                    speech_count,
                ),
                information_atom_count=total["information_atom_count"],
                new_information_atom_count=total["new_information_atom_count"],
                information_increment_rate=_rate(
                    total["new_information_atom_count"],
                    total["information_atom_count"],
                ),
                zero_information_increment_count=total[
                    "zero_information_increment_count"
                ],
                zero_information_increment_rate=_rate_required(
                    total["zero_information_increment_count"],
                    speech_count,
                ),
                persona_marker_speech_count=total[
                    "persona_marker_speech_count"
                ],
                persona_marker_speech_rate=_rate_required(
                    total["persona_marker_speech_count"],
                    speech_count,
                ),
            )
        )

    speech_count = totals["speech_count"]
    cross_actor_pair_count = totals["cross_actor_pair_count"]
    mean_cross_actor_similarity = _mean_from_sum(
        cross_actor_similarity_sum,
        cross_actor_pair_count,
    )
    return NPCSpeechQualityBatchV1(
        near_duplicate_threshold=NEAR_DUPLICATE_THRESHOLD,
        game_count=len(parsed_reports),
        games_with_npc_speech_count=games_with_speech,
        speech_count=speech_count,
        average_speeches_per_game=_round_metric(
            speech_count / len(parsed_reports)
        ),
        actor_game_count=actor_game_count,
        distinct_actor_count=len(actors),
        phase_counts={key: phase_counts[key] for key in sorted(phase_counts)},
        surface_repeat_count=totals["surface_repeat_count"],
        template_repeat_count=totals["template_repeat_count"],
        cross_actor_template_repeat_count=totals[
            "cross_actor_template_repeat_count"
        ],
        surface_repeat_rate=_rate(
            totals["surface_repeat_count"],
            speech_count,
        ),
        template_repeat_rate=_rate(
            totals["template_repeat_count"],
            speech_count,
        ),
        cross_actor_template_repeat_rate=_rate(
            totals["cross_actor_template_repeat_count"],
            speech_count,
        ),
        speech_pair_count=totals["speech_pair_count"],
        near_duplicate_pair_count=totals["near_duplicate_pair_count"],
        near_duplicate_pair_rate=_rate(
            totals["near_duplicate_pair_count"],
            totals["speech_pair_count"],
        ),
        cross_actor_pair_count=cross_actor_pair_count,
        cross_actor_near_duplicate_pair_count=totals[
            "cross_actor_near_duplicate_pair_count"
        ],
        cross_actor_near_duplicate_pair_rate=_rate(
            totals["cross_actor_near_duplicate_pair_count"],
            cross_actor_pair_count,
        ),
        cross_actor_template_similarity_sum=_round_metric(
            cross_actor_similarity_sum
        ),
        mean_cross_actor_template_similarity=mean_cross_actor_similarity,
        persona_differentiation_score=(
            _round_metric(1.0 - mean_cross_actor_similarity)
            if mean_cross_actor_similarity is not None
            else None
        ),
        evidence_citation_count=totals["evidence_citation_count"],
        evidence_citation_rate=_rate(
            totals["evidence_citation_count"],
            speech_count,
        ),
        information_atom_count=totals["information_atom_count"],
        new_information_atom_count=totals["new_information_atom_count"],
        information_increment_rate=_rate(
            totals["new_information_atom_count"],
            totals["information_atom_count"],
        ),
        zero_information_increment_count=totals[
            "zero_information_increment_count"
        ],
        zero_information_increment_rate=_rate(
            totals["zero_information_increment_count"],
            speech_count,
        ),
        persona_marker_speech_count=totals["persona_marker_speech_count"],
        persona_marker_speech_rate=_rate(
            totals["persona_marker_speech_count"],
            speech_count,
        ),
        persona_marker_actor_game_count=persona_marker_actor_game_count,
        persona_marker_actor_coverage=_rate(
            persona_marker_actor_game_count,
            actor_game_count,
        ),
        actors=actors,
        disclaimer=(
            "批量比率先汇总原始计数再计算；相似度按跨角色 speech pair 加权。该报告"
            "只用于离线诊断，不是自动平衡阈值，也不读取或输出角色真实阵营。"
        ),
    )


def _build_actor_quality(
    observations: list[NPCSpeechQualityObservationV1],
) -> list[NPCSpeechActorQualityV1]:
    by_actor: dict[tuple[int, str], list[NPCSpeechQualityObservationV1]] = (
        defaultdict(list)
    )
    for observation in observations:
        by_actor[(observation.actor_id, observation.actor_name)].append(
            observation
        )
    result: list[NPCSpeechActorQualityV1] = []
    for (actor_id, actor_name), actor_observations in sorted(by_actor.items()):
        speech_count = len(actor_observations)
        unique_surface_count = len(
            {item.normalized_text_digest for item in actor_observations}
        )
        unique_template_count = len(
            {item.template_text_digest for item in actor_observations}
        )
        surface_repeat_count = speech_count - unique_surface_count
        template_repeat_count = speech_count - unique_template_count
        evidence_count = sum(item.evidence_cited for item in actor_observations)
        information_count = sum(
            len(item.information_atoms) for item in actor_observations
        )
        new_information_count = sum(
            len(item.new_information_atoms) for item in actor_observations
        )
        zero_increment_count = sum(
            not item.new_information_atoms for item in actor_observations
        )
        persona_marker_count = sum(
            item.persona_marker_hit for item in actor_observations
        )
        result.append(
            NPCSpeechActorQualityV1(
                actor_id=actor_id,
                actor_name=actor_name,
                speech_count=speech_count,
                unique_surface_count=unique_surface_count,
                unique_template_count=unique_template_count,
                within_actor_surface_repeat_count=surface_repeat_count,
                within_actor_template_repeat_count=template_repeat_count,
                within_actor_surface_repeat_rate=_rate_required(
                    surface_repeat_count,
                    speech_count,
                ),
                within_actor_template_repeat_rate=_rate_required(
                    template_repeat_count,
                    speech_count,
                ),
                evidence_citation_count=evidence_count,
                evidence_citation_rate=_rate_required(
                    evidence_count,
                    speech_count,
                ),
                information_atom_count=information_count,
                new_information_atom_count=new_information_count,
                information_increment_rate=_rate(
                    new_information_count,
                    information_count,
                ),
                zero_information_increment_count=zero_increment_count,
                zero_information_increment_rate=_rate_required(
                    zero_increment_count,
                    speech_count,
                ),
                persona_marker_speech_count=persona_marker_count,
                persona_marker_speech_rate=_rate_required(
                    persona_marker_count,
                    speech_count,
                ),
                average_normalized_character_count=_round_metric(
                    sum(
                        item.normalized_character_count
                        for item in actor_observations
                    )
                    / speech_count
                ),
            )
        )
    return result


def _build_reference_ids(speech: rules.SpeechState) -> set[str]:
    """Collect references already validated as publishable when saved."""

    references = {
        "evidence_title:" + normalize_speech_text(title)
        for title in speech.evidence_titles
        if normalize_speech_text(title)
    }
    references.update(
        str(signal_id)
        for signal_id in speech.decision_signal_ids
        if str(signal_id).strip()
    )
    plan = speech.decision_plan
    for field_name in (
        "evidence_ids",
        "signal_ids",
        "continuity_signal_ids",
    ):
        values = plan.get(field_name, [])
        if isinstance(values, list):
            references.update(
                str(value) for value in values if str(value).strip()
            )
    if speech.public_position is not None:
        references.update(speech.public_position.basis_signal_ids)
    return references


def _build_information_atoms(
    speech: rules.SpeechState,
) -> set[str]:
    """Use only structure sealed on this speech, never terminal aggregates.

    ``game_state.public_claims`` has day-level but not speech-level provenance,
    so reading it here could backfill a later claim into an earlier speech.
    """

    atoms: set[str] = set()

    def add_target(kind: str, value: object) -> None:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            atoms.add(f"{kind}:{value}")

    if speech.focus_target_id is not None:
        intent = speech.decision_intent.strip() or "unspecified"
        atoms.add(f"focus:{intent}:{speech.focus_target_id}")
    position = speech.public_position
    if position is not None:
        if position.claimed_role:
            atoms.add(f"claim_role:{position.claimed_role}")
        add_target("seer_support", position.seer_support_id)
        add_target("seer_oppose", position.seer_oppose_id)
        for target_id in position.trusted_target_ids:
            add_target("trust", target_id)
        for target_id in position.suspected_target_ids:
            add_target("suspect", target_id)
        add_target("provisional_vote", position.provisional_vote_target_id)
        if position.question_target_id is not None:
            topic = (
                position.question_topic.value
                if position.question_topic is not None
                else "unspecified"
            )
            atoms.add(f"question:{topic}:{position.question_target_id}")
        if position.change_condition_target_id is not None:
            criterion = (
                position.change_condition.value
                if position.change_condition is not None
                else "unspecified"
            )
            atoms.add(
                f"change_condition:{criterion}:"
                f"{position.change_condition_target_id}"
            )
    plan = speech.decision_plan
    for field_name, atom_kind in (
        ("primary_target_id", "primary_target"),
        ("secondary_target_id", "secondary_target"),
        ("stance_target_id", f"stance:{plan.get('stance', 'unspecified')}"),
        ("provisional_vote_target_id", "provisional_vote"),
    ):
        add_target(atom_kind, plan.get(field_name))
    for nested_field, atom_kind in (
        ("question", "question"),
        ("verification", "verification"),
    ):
        nested = plan.get(nested_field)
        if isinstance(nested, dict):
            target_id = nested.get("target_id")
            topic = nested.get("topic", nested.get("criterion", "unspecified"))
            if isinstance(target_id, int) and not isinstance(target_id, bool):
                atoms.add(f"{atom_kind}:{topic}:{target_id}")
    claim_option_ids = plan.get("claim_option_ids", [])
    if isinstance(claim_option_ids, list):
        atoms.update(
            f"claim_option:{item}"
            for item in claim_option_ids
            if str(item).strip()
        )
    if speech.witch_directive is not None:
        directive = speech.witch_directive
        target = directive.target_id if directive.target_id is not None else "none"
        atoms.add(
            f"witch_directive:{directive.action}:{target}:"
            f"{directive.reason_kind}"
        )
    return atoms


def _configured_persona_markers(actor_name: str) -> list[str]:
    profile = rules.get_npc_voice_profile(actor_name)
    values: list[object] = []
    for field_name in ("catchphrases", "easter_eggs"):
        field_value = profile.get(field_name, [])
        if isinstance(field_value, list):
            values.extend(field_value)
    return sorted(
        {
            marker
            for value in values
            if len(marker := normalize_speech_text(str(value))) >= 2
        }
    )


def _template_similarity(left: str, right: str) -> float:
    left_ngrams = _character_ngrams(left)
    right_ngrams = _character_ngrams(right)
    if not left_ngrams and not right_ngrams:
        return 1.0
    union = left_ngrams.union(right_ngrams)
    if not union:
        return 0.0
    return len(left_ngrams.intersection(right_ngrams)) / len(union)


def _character_ngrams(text: str, size: int = 3) -> set[str]:
    if not text:
        return set()
    if len(text) < size:
        return set(text)
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_rate(
    label: str,
    actual: Optional[float],
    numerator: int,
    denominator: int,
) -> None:
    expected = _rate(numerator, denominator)
    if actual != expected:
        raise ValueError(f"{label} is inconsistent with its raw counts")


def _validate_similarity_summary(
    similarity_sum: float,
    pair_count: int,
    mean_similarity: Optional[float],
    differentiation_score: Optional[float],
) -> None:
    if pair_count <= 0:
        if (
            similarity_sum != 0.0
            or mean_similarity is not None
            or differentiation_score is not None
        ):
            raise ValueError("empty similarity samples must use zero sum and null rates")
        return
    if mean_similarity is None or differentiation_score is None:
        raise ValueError("non-empty similarity samples require mean and difference")
    if abs(mean_similarity - (similarity_sum / pair_count)) > 0.000002:
        raise ValueError("mean similarity is inconsistent with its sum and count")
    if differentiation_score != _round_metric(1.0 - mean_similarity):
        raise ValueError("persona differentiation must complement mean similarity")


def _mean_from_sum(total: float, count: int) -> Optional[float]:
    if count <= 0:
        return None
    return _round_metric(total / count)


def _rate(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return _round_metric(numerator / denominator)


def _rate_required(numerator: int, denominator: int) -> float:
    value = _rate(numerator, denominator)
    if value is None:
        raise ValueError("a required speech-quality rate has no denominator")
    return value


def _round_metric(value: float) -> float:
    return round(float(value), 6)


__all__ = [
    "NEAR_DUPLICATE_THRESHOLD",
    "NPC_SPEECH_ACTOR_QUALITY_BATCH_SCHEMA_VERSION",
    "NPC_SPEECH_ACTOR_QUALITY_SCHEMA_VERSION",
    "NPC_SPEECH_NORMALIZATION_SCHEMA_VERSION",
    "NPC_SPEECH_QUALITY_BATCH_SCHEMA_VERSION",
    "NPC_SPEECH_QUALITY_OBSERVATION_SCHEMA_VERSION",
    "NPC_SPEECH_QUALITY_SCHEMA_VERSION",
    "NPCSpeechActorQualityBatchV1",
    "NPCSpeechActorQualityV1",
    "NPCSpeechQualityBatchV1",
    "NPCSpeechQualityObservationV1",
    "NPCSpeechQualityV1",
    "aggregate_npc_speech_quality",
    "build_npc_speech_quality",
    "canonicalize_speech_template",
    "normalize_speech_text",
]
