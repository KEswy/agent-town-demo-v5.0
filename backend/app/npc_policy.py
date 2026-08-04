"""Versioned local NPC policy contracts, artifacts, and trace plumbing.

The rule engine owns legal action generation and final sampling.  A policy
artifact receives fixed, actor-scoped candidate features and returns one finite
score for each existing action ID.  It cannot create or remove an action.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import zipfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Callable, Iterator, Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


NPC_POLICY_OBSERVATION_SCHEMA_VERSION = "npc_policy_observation.v1"
NPC_POLICY_SCORES_SCHEMA_VERSION = "npc_policy_scores.v1"
NPC_POLICY_ARTIFACT_SCHEMA_VERSION = "npc_policy_artifact.v1"
NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2 = "npc_policy_artifact.v2"
NPC_POLICY_TRACE_SCHEMA_VERSION = "npc_policy_trace.v2"
NPC_POLICY_FEATURE_SCHEMA_VERSION = "npc_exile_vote_features.v1"
NPC_POLICY_TASK_EXILE_VOTE = "exile_vote"
NPC_POLICY_TASK_SHERIFF_VOTE = "sheriff_vote"
NPC_POLICY_TASK_SHERIFF_NOMINATION = "sheriff_nomination"
NPC_POLICY_TASKS = (
    NPC_POLICY_TASK_EXILE_VOTE,
    NPC_POLICY_TASK_SHERIFF_VOTE,
    NPC_POLICY_TASK_SHERIFF_NOMINATION,
)
SHERIFF_VOTE_FEATURE_SCHEMA_VERSION = "npc_sheriff_vote_features.v1"
SHERIFF_NOMINATION_FEATURE_SCHEMA_VERSION = (
    "npc_sheriff_nomination_features.v1"
)
NPC_POLICY_ENTROPY_GUARD_VERSION = "npc_policy_entropy_guard.v1"

GOOD_DEFAULT_ENTROPY_ALLOWANCE = 0.01
GOOD_HARD_LOGIC_ENTROPY_ALLOWANCE = 0.05
WEREWOLF_ENTROPY_ALLOWANCE = 0.08
GOOD_DEFAULT_TOTAL_VARIATION_CAP = 0.01
GOOD_HARD_LOGIC_TOTAL_VARIATION_CAP = 0.12
WEREWOLF_TOTAL_VARIATION_CAP = 0.12
GOOD_SOLE_SEER_MASS_CAP = 0.02

NPCPolicyMode = Literal["rule", "shadow", "local"]
NPCPolicyFaction = Literal["good", "werewolf"]


def policy_temperature_from_environment() -> float:
    """Read the model-score softmax temperature with a bounded default."""

    raw = os.environ.get("AGENT_TOWN_NPC_POLICY_TEMPERATURE", "1.0").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            "AGENT_TOWN_NPC_POLICY_TEMPERATURE must be a finite number"
        ) from exc
    if not math.isfinite(value) or not 0.25 <= value <= 2.0:
        raise ValueError(
            "AGENT_TOWN_NPC_POLICY_TEMPERATURE must be between 0.25 and 2.0"
        )
    return value


def policy_blend_from_environment() -> float:
    """Read the model/teacher probability blend, defaulting to full model."""

    raw = os.environ.get("AGENT_TOWN_NPC_POLICY_BLEND", "1.0").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            "AGENT_TOWN_NPC_POLICY_BLEND must be a finite number"
        ) from exc
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(
            "AGENT_TOWN_NPC_POLICY_BLEND must be between 0.0 and 1.0"
        )
    return value


def normalized_policy_entropy(
    probabilities: dict[int, float],
) -> float:
    """Return entropy divided by the legal-set maximum."""

    if not probabilities:
        raise ValueError("policy entropy requires at least one action")
    canonical = {
        int(action_id): max(0.0, float(value))
        for action_id, value in probabilities.items()
    }
    if any(not math.isfinite(value) for value in canonical.values()):
        raise ValueError("policy entropy requires finite probabilities")
    total = sum(canonical.values())
    if total <= 0.0:
        raise ValueError("policy entropy requires positive probability mass")
    if len(canonical) == 1:
        return 0.0
    values = [value / total for value in canonical.values()]
    entropy = -sum(
        value * math.log(max(value, 1e-12))
        for value in values
    )
    return entropy / math.log(len(values))


def _normalize_distribution(
    probabilities: dict[int, float],
) -> dict[int, float]:
    canonical = {
        int(action_id): max(0.0, float(value))
        for action_id, value in sorted(probabilities.items())
    }
    if any(not math.isfinite(value) for value in canonical.values()):
        raise ValueError("policy probabilities must be finite")
    total = sum(canonical.values())
    if total <= 0.0:
        raise ValueError("policy probabilities require positive mass")
    return {
        action_id: value / total
        for action_id, value in canonical.items()
    }


def _mixed_distribution(
    rule: dict[int, float],
    model: dict[int, float],
    blend: float,
) -> dict[int, float]:
    return _normalize_distribution(
        {
            action_id: (
                (1.0 - blend) * rule[action_id]
                + blend * model[action_id]
            )
            for action_id in rule
        }
    )


def _total_variation(
    left: dict[int, float],
    right: dict[int, float],
) -> float:
    return 0.5 * sum(
        abs(left[action_id] - right[action_id])
        for action_id in left
    )


def entropy_guarded_policy_blend(
    observation: "NPCPolicyObservationV1",
    rule_probabilities: dict[int, float],
    model_probabilities: dict[int, float],
    requested_blend: float,
) -> tuple[dict[int, float], dict[str, object]]:
    """Bound model perturbation before deterministic ballot sampling.

    The guard does not create or remove actions. Ordinary good-side
    observations remain exactly on the teacher. Hard public logic may consume
    the largest share of the requested model blend that both corrects in the
    expected direction and stays within entropy/total-variation limits.
    """

    if not math.isfinite(requested_blend) or not 0.0 <= requested_blend <= 1.0:
        raise ValueError("requested policy blend must be between zero and one")
    rule = _normalize_distribution(rule_probabilities)
    model = _normalize_distribution(model_probabilities)
    if set(rule) != set(model):
        raise ValueError("rule and model policy actions must match")
    candidate_features = {
        candidate.target_id: dict(
            zip(observation.feature_names, candidate.feature_values)
        )
        for candidate in observation.candidates
    }
    if set(candidate_features) != set(rule):
        raise ValueError("policy observation candidates must match probabilities")
    conflict_ids = {
        target_id
        for target_id, features in candidate_features.items()
        if features.get("candidate_logic_conflict", 0.0) > 0.0
    }
    sole_seer_ids = {
        target_id
        for target_id, features in candidate_features.items()
        if features.get("candidate_sole_consistent_seer", 0.0) > 0.0
    }
    hard_public_logic = bool(conflict_ids or sole_seer_ids)
    if observation.faction == "good":
        entropy_allowance = (
            GOOD_HARD_LOGIC_ENTROPY_ALLOWANCE
            if hard_public_logic
            else GOOD_DEFAULT_ENTROPY_ALLOWANCE
        )
        total_variation_cap = (
            GOOD_HARD_LOGIC_TOTAL_VARIATION_CAP
            if hard_public_logic
            else GOOD_DEFAULT_TOTAL_VARIATION_CAP
        )
    else:
        entropy_allowance = WEREWOLF_ENTROPY_ALLOWANCE
        total_variation_cap = WEREWOLF_TOTAL_VARIATION_CAP
    rule_entropy = normalized_policy_entropy(rule)
    allowed_entropy = min(1.0, rule_entropy + entropy_allowance)
    rule_top_action = max(
        rule,
        key=lambda action_id: (rule[action_id], -action_id),
    )
    sole_rule_mass = sum(rule[action_id] for action_id in sole_seer_ids)
    conflict_rule_mass = sum(rule[action_id] for action_id in conflict_ids)
    conflict_model_mass = sum(model[action_id] for action_id in conflict_ids)
    sole_model_mass = sum(model[action_id] for action_id in sole_seer_ids)
    directional_correction = (
        hard_public_logic
        and (
            not conflict_ids
            or conflict_model_mass >= conflict_rule_mass - 1e-12
        )
        and (
            not sole_seer_ids
            or sole_model_mass <= sole_rule_mass + 1e-12
        )
    )
    allowed_sole_mass = max(
        sole_rule_mass,
        GOOD_SOLE_SEER_MASS_CAP,
    )

    def accepted(blend: float) -> tuple[bool, dict[int, float]]:
        distribution = _mixed_distribution(rule, model, blend)
        entropy_ok = (
            normalized_policy_entropy(distribution)
            <= allowed_entropy + 1e-12
        )
        variation_ok = (
            _total_variation(rule, distribution)
            <= total_variation_cap + 1e-12
        )
        top_ok = True
        if observation.faction == "good" and not hard_public_logic:
            top_ok = max(
                distribution,
                key=lambda action_id: (
                    distribution[action_id],
                    -action_id,
                ),
            ) == rule_top_action
        sole_ok = True
        if observation.faction == "good" and sole_seer_ids:
            sole_ok = (
                sum(distribution[action_id] for action_id in sole_seer_ids)
                <= allowed_sole_mass + 1e-12
            )
        return entropy_ok and variation_ok and top_ok and sole_ok, distribution

    _, requested_distribution = accepted(requested_blend)
    maximum_blend = requested_blend
    if observation.faction == "good" and (
        not hard_public_logic or not directional_correction
    ):
        maximum_blend = 0.0
    maximum_ok, maximum_distribution = accepted(maximum_blend)
    effective_blend = maximum_blend
    guarded = maximum_distribution
    if not maximum_ok:
        low = 0.0
        high = maximum_blend
        guarded = dict(rule)
        for _iteration in range(48):
            middle = (low + high) / 2.0
            middle_ok, middle_distribution = accepted(middle)
            if middle_ok:
                low = middle
                guarded = middle_distribution
            else:
                high = middle
        effective_blend = low
    metadata = {
        "schema_version": NPC_POLICY_ENTROPY_GUARD_VERSION,
        "applied": effective_blend + 1e-12 < requested_blend,
        "hard_public_logic": hard_public_logic,
        "directional_correction": directional_correction,
        "teacher_exact_context": (
            observation.faction == "good"
            and (not hard_public_logic or not directional_correction)
        ),
        "requested_blend": requested_blend,
        "effective_blend": effective_blend,
        "rule_normalized_entropy": rule_entropy,
        "model_normalized_entropy": normalized_policy_entropy(model),
        "requested_normalized_entropy": normalized_policy_entropy(
            requested_distribution
        ),
        "final_normalized_entropy": normalized_policy_entropy(guarded),
        "allowed_normalized_entropy": allowed_entropy,
        "final_total_variation": _total_variation(rule, guarded),
        "total_variation_cap": total_variation_cap,
        "sole_consistent_seer_rule_mass": sole_rule_mass,
        "sole_consistent_seer_final_mass": sum(
            guarded[action_id] for action_id in sole_seer_ids
        ),
        "sole_consistent_seer_mass_cap": (
            allowed_sole_mass if sole_seer_ids else None
        ),
    }
    return guarded, metadata

EXILE_VOTE_FEATURE_NAMES = (
    "candidate_suspicion",
    "candidate_public_pressure",
    "candidate_distrust",
    "candidate_wolf_belief",
    "candidate_good_belief",
    "candidate_seer_belief",
    "candidate_reasoning_confidence",
    "candidate_claimed_seer",
    "candidate_logic_conflict",
    "candidate_sole_consistent_seer",
    "candidate_is_sheriff_nomination",
    "candidate_is_provisional_vote",
    "candidate_in_suspected_set",
    "candidate_in_trusted_set",
    "candidate_is_sheriff",
    "candidate_is_known_good",
    "candidate_is_known_wolf",
    "candidate_is_wolf_teammate",
    "actor_reasoning_skill",
    "actor_social_susceptibility",
    "actor_deception_susceptibility",
    "actor_plan_consistency",
    "actor_team_coordination",
    "day_progress",
    "alive_ratio",
)

SHERIFF_VOTE_FEATURE_NAMES = (
    "candidate_relationship_trust",
    "candidate_public_persuasion",
    "candidate_leadership",
    "candidate_suspicion",
    "candidate_claimed_any_role",
    "candidate_claimed_seer",
    "candidate_seer_claim_credibility",
    "candidate_seer_belief",
    "candidate_wolf_belief",
    "candidate_good_belief",
    "candidate_received_gold",
    "candidate_received_black",
    "candidate_sole_consistent_seer",
    "candidate_inconsistent_hypothesis",
    "candidate_badge_flow_published",
    "candidate_in_trusted_set",
    "candidate_in_suspected_set",
    "candidate_is_known_good",
    "candidate_is_known_wolf",
    "actor_reasoning_skill",
    "actor_social_susceptibility",
    "actor_deception_susceptibility",
    "actor_decision_variance",
    "actor_plan_consistency",
    "actor_team_coordination",
    "day_progress",
)

SHERIFF_NOMINATION_FEATURE_NAMES = SHERIFF_VOTE_FEATURE_NAMES

TASK_FEATURE_SCHEMA_VERSIONS: dict[str, str] = {
    NPC_POLICY_TASK_EXILE_VOTE: NPC_POLICY_FEATURE_SCHEMA_VERSION,
    NPC_POLICY_TASK_SHERIFF_VOTE: SHERIFF_VOTE_FEATURE_SCHEMA_VERSION,
    NPC_POLICY_TASK_SHERIFF_NOMINATION: (
        SHERIFF_NOMINATION_FEATURE_SCHEMA_VERSION
    ),
}
TASK_FEATURE_NAMES: dict[str, tuple[str, ...]] = {
    NPC_POLICY_TASK_EXILE_VOTE: EXILE_VOTE_FEATURE_NAMES,
    NPC_POLICY_TASK_SHERIFF_VOTE: SHERIFF_VOTE_FEATURE_NAMES,
    NPC_POLICY_TASK_SHERIFF_NOMINATION: SHERIFF_NOMINATION_FEATURE_NAMES,
}


def task_for_feature_schema(feature_schema_version: str) -> str:
    """Map a feature schema version back to its policy task."""

    for task, schema_version in TASK_FEATURE_SCHEMA_VERSIONS.items():
        if schema_version == feature_schema_version:
            return task
    raise ValueError(f"unknown feature schema version: {feature_schema_version}")


class StrictPolicyModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class NPCPolicyCandidateV1(StrictPolicyModel):
    action_id: str = Field(pattern=r"^[a-z_]+:[0-9]+$")
    action_type: Literal[
        "exile_vote",
        "sheriff_vote",
        "sheriff_nomination",
    ]
    target_id: int = Field(gt=0)
    feature_values: list[float]

    @model_validator(mode="after")
    def validate_features(self) -> "NPCPolicyCandidateV1":
        if any(not math.isfinite(value) for value in self.feature_values):
            raise ValueError("policy candidate features must be finite")
        return self


class NPCPolicyObservationV1(StrictPolicyModel):
    schema_version: Literal["npc_policy_observation.v1"] = (
        NPC_POLICY_OBSERVATION_SCHEMA_VERSION
    )
    feature_schema_version: Literal[
        "npc_exile_vote_features.v1",
        "npc_sheriff_vote_features.v1",
        "npc_sheriff_nomination_features.v1",
    ]
    game_id: str = Field(min_length=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    task: Literal["exile_vote", "sheriff_vote", "sheriff_nomination"]
    actor_id: int = Field(gt=0)
    faction: NPCPolicyFaction
    reasoning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_names: list[str]
    candidates: list[NPCPolicyCandidateV1] = Field(min_length=1)
    observation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> "NPCPolicyObservationV1":
        task = task_for_feature_schema(self.feature_schema_version)
        if self.feature_names != list(TASK_FEATURE_NAMES[task]):
            raise ValueError("policy feature order is incompatible")
        if self.task != task:
            raise ValueError("policy task does not match its feature schema")
        action_ids = [candidate.action_id for candidate in self.candidates]
        target_ids = [candidate.target_id for candidate in self.candidates]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("policy action IDs must be unique")
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("policy candidate targets must be unique")
        for candidate in self.candidates:
            if len(candidate.feature_values) != len(self.feature_names):
                raise ValueError("policy candidate feature length is incompatible")
        expected = policy_observation_digest(
            self.model_dump(mode="json", exclude={"observation_digest"})
        )
        if self.observation_digest != expected:
            raise ValueError("policy observation digest is stale")
        return self


class NPCPolicyActionScoreV1(StrictPolicyModel):
    action_id: str = Field(pattern=r"^[a-z_]+:[0-9]+$")
    score: float

    @model_validator(mode="after")
    def validate_score(self) -> "NPCPolicyActionScoreV1":
        if not math.isfinite(self.score):
            raise ValueError("policy action score must be finite")
        return self


class NPCPolicyScoresV1(StrictPolicyModel):
    schema_version: Literal["npc_policy_scores.v1"] = (
        NPC_POLICY_SCORES_SCHEMA_VERSION
    )
    model_id: str = Field(min_length=1)
    model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    scores: list[NPCPolicyActionScoreV1] = Field(min_length=1)


class NPCPolicyArtifactManifestV1(StrictPolicyModel):
    schema_version: Literal["npc_policy_artifact.v1"] = (
        NPC_POLICY_ARTIFACT_SCHEMA_VERSION
    )
    model_id: str = Field(min_length=1)
    faction: NPCPolicyFaction
    task: Literal["exile_vote", "sheriff_vote", "sheriff_nomination"]
    observation_schema_version: Literal["npc_policy_observation.v1"] = (
        NPC_POLICY_OBSERVATION_SCHEMA_VERSION
    )
    feature_schema_version: Literal[
        "npc_exile_vote_features.v1",
        "npc_sheriff_vote_features.v1",
        "npc_sheriff_nomination_features.v1",
    ] = NPC_POLICY_FEATURE_SCHEMA_VERSION
    feature_names: list[str]
    model_file: Literal["model.npz"] = "model.npz"
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    training_seed: int = Field(ge=0)
    training_samples: int = Field(gt=0)
    validation_samples: int = Field(gt=0)
    validation_cross_entropy: float = Field(ge=0.0)
    validation_top1_agreement: float = Field(ge=0.0, le=1.0)
    created_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_features(self) -> "NPCPolicyArtifactManifestV1":
        if self.feature_names != list(TASK_FEATURE_NAMES[self.task]):
            raise ValueError("artifact feature order is incompatible")
        if task_for_feature_schema(self.feature_schema_version) != self.task:
            raise ValueError("artifact task does not match its feature schema")
        return self


class NPCPolicyArchitectureV2(StrictPolicyModel):
    input_dim: int = Field(gt=0)
    hidden_dims: list[int] = Field(min_length=1, max_length=1)
    activation: Literal["tanh"]
    output_dim: Literal[1] = 1

    @model_validator(mode="after")
    def validate_architecture(self) -> "NPCPolicyArchitectureV2":
        if not 4 <= self.hidden_dims[0] <= 256:
            raise ValueError("policy hidden dimension must be between 4 and 256")
        return self


class NPCPolicyArtifactManifestV2(StrictPolicyModel):
    schema_version: Literal["npc_policy_artifact.v2"] = (
        NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2
    )
    model_id: str = Field(min_length=1)
    model_type: Literal["mlp"]
    faction: NPCPolicyFaction
    task: Literal["exile_vote", "sheriff_vote", "sheriff_nomination"]
    observation_schema_version: Literal["npc_policy_observation.v1"] = (
        NPC_POLICY_OBSERVATION_SCHEMA_VERSION
    )
    feature_schema_version: Literal[
        "npc_exile_vote_features.v1",
        "npc_sheriff_vote_features.v1",
        "npc_sheriff_nomination_features.v1",
    ] = NPC_POLICY_FEATURE_SCHEMA_VERSION
    feature_names: list[str]
    architecture: NPCPolicyArchitectureV2
    model_file: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    training_seed: int = Field(ge=0)
    training_samples: int = Field(gt=0)
    validation_samples: int = Field(gt=0)
    validation_cross_entropy: float = Field(ge=0.0)
    validation_top1_agreement: float = Field(ge=0.0, le=1.0)
    created_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_features(self) -> "NPCPolicyArtifactManifestV2":
        if self.feature_names != list(TASK_FEATURE_NAMES[self.task]):
            raise ValueError("artifact feature order is incompatible")
        if task_for_feature_schema(self.feature_schema_version) != self.task:
            raise ValueError("artifact task does not match its feature schema")
        if self.architecture.input_dim != len(self.feature_names):
            raise ValueError("policy architecture input_dim is incompatible")
        return self


PolicyTraceSink = Callable[[dict[str, object]], None]
_POLICY_TRACE_SINK: ContextVar[Optional[PolicyTraceSink]] = ContextVar(
    "agent_town_policy_trace_sink",
    default=None,
)


def _normalize_policy_digest_payload(payload: object) -> object:
    """Canonicalize feature numerics without changing IDs or metadata types."""

    if isinstance(payload, dict):
        normalized = {}
        for key, value in payload.items():
            if key == "feature_values" and isinstance(value, list):
                normalized[key] = [
                    float(item)
                    if isinstance(item, (int, float)) and not isinstance(item, bool)
                    else item
                    for item in value
                ]
            else:
                normalized[key] = _normalize_policy_digest_payload(value)
        return normalized
    if isinstance(payload, list):
        return [_normalize_policy_digest_payload(item) for item in payload]
    return payload


def policy_observation_digest(payload: object) -> str:
    encoded = json.dumps(
        _normalize_policy_digest_payload(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def capture_policy_traces(sink: PolicyTraceSink) -> Iterator[None]:
    token = _POLICY_TRACE_SINK.set(sink)
    try:
        yield
    finally:
        _POLICY_TRACE_SINK.reset(token)


def emit_policy_trace(payload: dict[str, object]) -> None:
    sink = _POLICY_TRACE_SINK.get()
    if sink is None:
        return
    sink(
        {
            "schema_version": NPC_POLICY_TRACE_SCHEMA_VERSION,
            **payload,
        }
    )


class LocalLinearPolicy:
    """Small safe artifact used only to score an existing candidate list."""

    def __init__(
        self,
        manifest: NPCPolicyArtifactManifestV1,
        *,
        weights: np.ndarray,
        bias: float,
        feature_mean: np.ndarray,
        feature_scale: np.ndarray,
        model_digest: str,
    ) -> None:
        feature_count = len(manifest.feature_names)
        expected_shape = (feature_count,)
        for name, value in {
            "weights": weights,
            "feature_mean": feature_mean,
            "feature_scale": feature_scale,
        }.items():
            if value.shape != expected_shape:
                raise ValueError(f"{name} shape is incompatible")
            if not np.isfinite(value).all():
                raise ValueError(f"{name} contains a non-finite value")
        if not math.isfinite(bias):
            raise ValueError("policy bias must be finite")
        if np.any(feature_scale <= 0.0):
            raise ValueError("policy feature scale must be positive")
        self.manifest = manifest
        self.weights = weights.astype(np.float64, copy=True)
        self.bias = float(bias)
        self.feature_mean = feature_mean.astype(np.float64, copy=True)
        self.feature_scale = feature_scale.astype(np.float64, copy=True)
        self.model_digest = model_digest

    @classmethod
    def load(cls, artifact_dir: Path) -> "LocalLinearPolicy":
        manifest_path = artifact_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"policy manifest is missing: {manifest_path}")
        manifest = NPCPolicyArtifactManifestV1.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        model_path = artifact_dir / manifest.model_file
        if not model_path.is_file():
            raise FileNotFoundError(f"policy model is missing: {model_path}")
        observed_digest = file_sha256(model_path)
        if observed_digest != manifest.model_sha256:
            raise ValueError("policy model digest does not match its manifest")
        try:
            with np.load(model_path, allow_pickle=False) as payload:
                required = {"weights", "bias", "feature_mean", "feature_scale"}
                if set(payload.files) != required:
                    raise ValueError("policy model fields are incompatible")
                weights = np.asarray(payload["weights"], dtype=np.float64)
                bias_array = np.asarray(payload["bias"], dtype=np.float64)
                feature_mean = np.asarray(payload["feature_mean"], dtype=np.float64)
                feature_scale = np.asarray(payload["feature_scale"], dtype=np.float64)
        except (EOFError, zipfile.BadZipFile, OSError) as exc:
            raise ValueError("policy model archive is unreadable") from exc
        if bias_array.shape not in {(), (1,)}:
            raise ValueError("policy bias shape is incompatible")
        return cls(
            manifest,
            weights=weights,
            bias=float(bias_array.reshape(-1)[0]),
            feature_mean=feature_mean,
            feature_scale=feature_scale,
            model_digest=observed_digest,
        )

    def score(
        self,
        observation: NPCPolicyObservationV1,
    ) -> NPCPolicyScoresV1:
        if observation.faction != self.manifest.faction:
            raise ValueError("policy artifact faction does not match actor")
        if observation.task != self.manifest.task:
            raise ValueError("policy artifact task does not match observation")
        feature_matrix = np.asarray(
            [candidate.feature_values for candidate in observation.candidates],
            dtype=np.float64,
        )
        normalized = (
            feature_matrix - self.feature_mean
        ) / self.feature_scale
        scores = normalized @ self.weights + self.bias
        if not np.isfinite(scores).all():
            raise ValueError("policy inference produced a non-finite score")
        result = NPCPolicyScoresV1(
            model_id=self.manifest.model_id,
            model_digest=self.model_digest,
            observation_digest=observation.observation_digest,
            scores=[
                NPCPolicyActionScoreV1(
                    action_id=candidate.action_id,
                    score=float(score),
                )
                for candidate, score in zip(observation.candidates, scores)
            ],
        )
        validate_policy_scores(observation, result)
        return result


class LocalMLPPolicy:
    """Safe one-hidden-layer NumPy scorer for an existing candidate list."""

    def __init__(
        self,
        manifest: NPCPolicyArtifactManifestV2,
        *,
        input_weights: np.ndarray,
        hidden_bias: np.ndarray,
        output_weights: np.ndarray,
        output_bias: float,
        feature_mean: np.ndarray,
        feature_scale: np.ndarray,
        model_digest: str,
    ) -> None:
        hidden_size = manifest.architecture.hidden_dims[0]
        feature_count = len(manifest.feature_names)
        expected = {
            "input_weights": (feature_count, hidden_size),
            "hidden_bias": (hidden_size,),
            "output_weights": (hidden_size,),
            "feature_mean": (feature_count,),
            "feature_scale": (feature_count,),
        }
        arrays = {
            "input_weights": input_weights,
            "hidden_bias": hidden_bias,
            "output_weights": output_weights,
            "feature_mean": feature_mean,
            "feature_scale": feature_scale,
        }
        for name, value in arrays.items():
            if value.shape != expected[name]:
                raise ValueError(f"{name} shape is incompatible")
            if not np.isfinite(value).all():
                raise ValueError(f"{name} contains a non-finite value")
        if not math.isfinite(output_bias):
            raise ValueError("policy output bias must be finite")
        if np.any(feature_scale <= 0.0):
            raise ValueError("policy feature scale must be positive")
        self.manifest = manifest
        self.input_weights = input_weights.astype(np.float64, copy=True)
        self.hidden_bias = hidden_bias.astype(np.float64, copy=True)
        self.output_weights = output_weights.astype(np.float64, copy=True)
        self.output_bias = float(output_bias)
        self.feature_mean = feature_mean.astype(np.float64, copy=True)
        self.feature_scale = feature_scale.astype(np.float64, copy=True)
        self.model_digest = model_digest

    @classmethod
    def load(cls, artifact_dir: Path) -> "LocalMLPPolicy":
        manifest_path = artifact_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"policy manifest is missing: {manifest_path}")
        manifest = NPCPolicyArtifactManifestV2.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        model_path = artifact_dir / manifest.model_file
        if not model_path.is_file():
            raise FileNotFoundError(f"policy model is missing: {model_path}")
        observed_digest = file_sha256(model_path)
        if observed_digest != manifest.model_sha256:
            raise ValueError("policy model digest does not match its manifest")
        try:
            with np.load(model_path, allow_pickle=False) as payload:
                required = {
                    "input_weights",
                    "hidden_bias",
                    "output_weights",
                    "output_bias",
                    "feature_mean",
                    "feature_scale",
                }
                if set(payload.files) != required:
                    raise ValueError("MLP model fields are incompatible")
                arrays = {
                    name: np.asarray(payload[name], dtype=np.float64)
                    for name in required
                }
        except (EOFError, zipfile.BadZipFile, OSError) as exc:
            raise ValueError("MLP model archive is unreadable") from exc
        bias = arrays.pop("output_bias")
        if bias.shape not in {(), (1,)}:
            raise ValueError("MLP output bias shape is incompatible")
        return cls(
            manifest,
            input_weights=arrays["input_weights"],
            hidden_bias=arrays["hidden_bias"],
            output_weights=arrays["output_weights"],
            output_bias=float(bias.reshape(-1)[0]),
            feature_mean=arrays["feature_mean"],
            feature_scale=arrays["feature_scale"],
            model_digest=observed_digest,
        )

    def score(self, observation: NPCPolicyObservationV1) -> NPCPolicyScoresV1:
        if observation.faction != self.manifest.faction:
            raise ValueError("policy artifact faction does not match actor")
        if observation.task != self.manifest.task:
            raise ValueError("policy artifact task does not match observation")
        feature_matrix = np.asarray(
            [candidate.feature_values for candidate in observation.candidates],
            dtype=np.float64,
        )
        normalized = (
            feature_matrix - self.feature_mean
        ) / self.feature_scale
        hidden = np.tanh(normalized @ self.input_weights + self.hidden_bias)
        scores = hidden @ self.output_weights + self.output_bias
        if not np.isfinite(scores).all():
            raise ValueError("MLP inference produced a non-finite score")
        result = NPCPolicyScoresV1(
            model_id=self.manifest.model_id,
            model_digest=self.model_digest,
            observation_digest=observation.observation_digest,
            scores=[
                NPCPolicyActionScoreV1(
                    action_id=candidate.action_id,
                    score=float(score),
                )
                for candidate, score in zip(observation.candidates, scores)
            ],
        )
        validate_policy_scores(observation, result)
        return result


def load_local_policy(
    artifact_dir: Path,
) -> LocalLinearPolicy | LocalMLPPolicy:
    """Dispatch an artifact loader while preserving V1 linear compatibility."""

    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"policy manifest is missing: {manifest_path}")
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = raw.get("schema_version") if isinstance(raw, dict) else None
    if schema == NPC_POLICY_ARTIFACT_SCHEMA_VERSION:
        return LocalLinearPolicy.load(artifact_dir)
    if schema == NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2:
        return LocalMLPPolicy.load(artifact_dir)
    raise ValueError("unsupported policy artifact schema")


def validate_policy_scores(
    observation: NPCPolicyObservationV1,
    result: NPCPolicyScoresV1,
) -> None:
    if result.observation_digest != observation.observation_digest:
        raise ValueError("policy result observation digest is stale")
    expected_ids = [candidate.action_id for candidate in observation.candidates]
    observed_ids = [score.action_id for score in result.scores]
    if observed_ids != expected_ids:
        raise ValueError("policy result must preserve canonical action order")


class LocalPolicyRegistry:
    def __init__(self) -> None:
        self._cache: dict[
            tuple[str, str, str], LocalLinearPolicy | LocalMLPPolicy
        ] = {}

    def artifact_dir(self, task: str, faction: NPCPolicyFaction) -> Path:
        project_backend = Path(__file__).resolve().parents[1]
        configured_root = Path(
            os.environ.get(
                "AGENT_TOWN_NPC_POLICY_DIR",
                str(project_backend / "policy_artifacts"),
            )
        )
        faction_dir = (
            "good_policy_v1" if faction == "good" else "wolf_policy_v1"
        )
        if task == NPC_POLICY_TASK_EXILE_VOTE:
            return configured_root / faction_dir
        return configured_root / task / faction_dir

    def get(
        self,
        task: str,
        faction: NPCPolicyFaction,
    ) -> LocalLinearPolicy | LocalMLPPolicy:
        artifact_dir = self.artifact_dir(task, faction).resolve()
        cache_key = (task, faction, str(artifact_dir))
        if cache_key not in self._cache:
            self._cache[cache_key] = load_local_policy(artifact_dir)
        return self._cache[cache_key]

    def clear(self) -> None:
        self._cache.clear()

    def descriptors(self) -> dict[str, dict[str, str]]:
        descriptors: dict[str, dict[str, str]] = {}
        for task in NPC_POLICY_TASKS:
            for faction in ("good", "werewolf"):
                try:
                    policy = self.get(task, faction)  # type: ignore[arg-type]
                except (FileNotFoundError, OSError, ValueError):
                    continue
                descriptors[f"{task}:{faction}"] = {
                    "task": task,
                    "model_id": policy.manifest.model_id,
                    "model_digest": policy.model_digest,
                    "manifest_sha256": file_sha256(
                        self.artifact_dir(task, faction)  # type: ignore[arg-type]
                        / "manifest.json"
                    ),
                    "dataset_digest": policy.manifest.dataset_digest,
                    "artifact_schema_version": policy.manifest.schema_version,
                    "feature_schema_version": (
                        policy.manifest.feature_schema_version
                    ),
                }
        return descriptors


LOCAL_POLICY_REGISTRY = LocalPolicyRegistry()


def policy_mode_from_environment() -> NPCPolicyMode:
    value = os.environ.get("AGENT_TOWN_NPC_POLICY_MODE", "local").strip().lower()
    if value not in {"rule", "shadow", "local"}:
        raise ValueError(
            "AGENT_TOWN_NPC_POLICY_MODE must be rule, shadow, or local"
        )
    return value  # type: ignore[return-value]


__all__ = [
    "EXILE_VOTE_FEATURE_NAMES",
    "LOCAL_POLICY_REGISTRY",
    "NPC_POLICY_ARTIFACT_SCHEMA_VERSION",
    "NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2",
    "NPC_POLICY_FEATURE_SCHEMA_VERSION",
    "NPC_POLICY_ENTROPY_GUARD_VERSION",
    "NPC_POLICY_OBSERVATION_SCHEMA_VERSION",
    "NPC_POLICY_SCORES_SCHEMA_VERSION",
    "NPC_POLICY_TRACE_SCHEMA_VERSION",
    "LocalLinearPolicy",
    "LocalMLPPolicy",
    "LocalPolicyRegistry",
    "NPCPolicyActionScoreV1",
    "NPCPolicyArtifactManifestV1",
    "NPCPolicyArchitectureV2",
    "NPCPolicyArtifactManifestV2",
    "NPCPolicyCandidateV1",
    "NPCPolicyMode",
    "NPCPolicyObservationV1",
    "NPCPolicyScoresV1",
    "capture_policy_traces",
    "entropy_guarded_policy_blend",
    "emit_policy_trace",
    "file_sha256",
    "load_local_policy",
    "policy_mode_from_environment",
    "normalized_policy_entropy",
    "policy_temperature_from_environment",
    "policy_blend_from_environment",
    "policy_observation_digest",
    "validate_policy_scores",
]
