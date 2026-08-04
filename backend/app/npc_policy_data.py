"""Strict offline data contracts for feeding NPC policy training.

The running game never consumes this module's labels.  It validates an
actor-scoped policy observation, optionally joins a human/expert label by
``observation_digest``, and emits a canonical JSONL record for offline
training.  Hidden roles and end-game outcomes are deliberately not part of
the runtime observation contract.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .npc_policy import (
    EXILE_VOTE_FEATURE_NAMES,
    SHERIFF_VOTE_FEATURE_NAMES,
    TASK_FEATURE_NAMES,
    TASK_FEATURE_SCHEMA_VERSIONS,
    NPCPolicyCandidateV1,
    NPCPolicyObservationV1,
    policy_observation_digest,
    task_for_feature_schema,
)


POLICY_TRAINING_RECORD_V1 = "npc_policy_training_record.v1"
POLICY_TRAINING_RECORD_V2 = "npc_policy_training_record.v2"
POLICY_LABEL_SCHEMA_V1 = "npc_policy_label.v1"
POLICY_DATASET_SCHEMA_V1 = "npc_policy_dataset.v1"
_HEX64 = r"^[0-9a-f]{64}$"
_ACTION_ID = r"^[a-z_]+:[0-9]+$"
_PROBABILITY_TOLERANCE = 1e-5


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    """Reject duplicate object keys instead of silently taking the last one."""

    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


class StrictPolicyDataModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class PolicyTrainingRecordV1(StrictPolicyDataModel):
    """The trace format emitted by ``generate_policy_dataset.py``."""

    schema_version: Literal["npc_policy_training_record.v1"] = (
        POLICY_TRAINING_RECORD_V1
    )
    seed: int = Field(ge=0)
    game_index: int = Field(ge=0)
    trace_index: int = Field(ge=0)
    game_id: str = Field(min_length=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    actor_id: int = Field(gt=0)
    faction: Literal["good", "werewolf"]
    reasoning_digest: str = Field(pattern=_HEX64)
    observation_digest: str = Field(pattern=_HEX64)
    feature_schema_version: Literal[
        "npc_exile_vote_features.v1",
        "npc_sheriff_vote_features.v1",
        "npc_sheriff_nomination_features.v1",
        "npc_night_target_features.v1",
    ]
    feature_names: list[str]
    candidates: list[NPCPolicyCandidateV1] = Field(min_length=1)
    rule_probabilities: dict[str, float]

    @model_validator(mode="after")
    def validate_record(self) -> "PolicyTrainingRecordV1":
        task = task_for_feature_schema(self.feature_schema_version)
        if self.feature_names != list(TASK_FEATURE_NAMES[task]):
            raise ValueError(
                f"feature_names do not match {self.feature_schema_version}"
            )
        candidate_ids = [candidate.action_id for candidate in self.candidates]
        target_ids = [str(candidate.target_id) for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate action_id values must be unique")
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("candidate target_id values must be unique")
        if set(self.rule_probabilities) != set(target_ids):
            raise ValueError("rule_probabilities keys must equal candidate targets")
        probabilities = list(self.rule_probabilities.values())
        if any(not math.isfinite(value) or value < 0.0 for value in probabilities):
            raise ValueError("rule_probabilities must be finite and non-negative")
        if not math.isclose(sum(probabilities), 1.0, abs_tol=_PROBABILITY_TOLERANCE):
            raise ValueError("rule_probabilities must sum to 1")
        observation_payload = {
            "schema_version": "npc_policy_observation.v1",
            "feature_schema_version": self.feature_schema_version,
            "game_id": self.game_id,
            "day": self.day,
            "phase": self.phase,
            "task": task_for_feature_schema(self.feature_schema_version),
            "actor_id": self.actor_id,
            "faction": self.faction,
            "reasoning_digest": self.reasoning_digest,
            "feature_names": self.feature_names,
            "candidates": [
                candidate.model_dump(mode="json")
                for candidate in self.candidates
            ],
        }
        # The observation model's own validator checks candidate lengths and
        # the digest.  Building it here also canonicalizes int/float inputs.
        normalized_observation = NPCPolicyObservationV1(
            **observation_payload,
            observation_digest=policy_observation_digest(observation_payload),
        )
        if normalized_observation.observation_digest != self.observation_digest:
            raise ValueError("observation_digest is stale")
        return self


class PolicyTrainingRecordV2(StrictPolicyDataModel):
    """Canonical training record supporting teacher and human labels."""

    schema_version: Literal["npc_policy_training_record.v2"] = (
        POLICY_TRAINING_RECORD_V2
    )
    record_id: str = Field(pattern=_HEX64)
    seed: int = Field(ge=0)
    episode_id: str = Field(min_length=1)
    game_id: str = Field(min_length=1)
    trace_index: int = Field(ge=0)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    actor_id: int = Field(gt=0)
    faction: Literal["good", "werewolf"]
    reasoning_digest: str = Field(pattern=_HEX64)
    observation_digest: str = Field(pattern=_HEX64)
    feature_schema_version: Literal[
        "npc_exile_vote_features.v1",
        "npc_sheriff_vote_features.v1",
        "npc_sheriff_nomination_features.v1",
        "npc_night_target_features.v1",
    ]
    feature_names: list[str]
    candidates: list[NPCPolicyCandidateV1] = Field(min_length=1)
    target_distribution: dict[str, float]
    label_type: Literal[
        "rule_teacher",
        "human_preference",
        "expert_preference",
        "self_play",
        "imported",
    ]
    source_id: str = Field(min_length=1)
    weight: float = Field(gt=0.0, le=100.0)
    rationale: Optional[str] = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_record(self) -> "PolicyTrainingRecordV2":
        task = task_for_feature_schema(self.feature_schema_version)
        if self.feature_names != list(TASK_FEATURE_NAMES[task]):
            raise ValueError(
                f"feature_names do not match {self.feature_schema_version}"
            )
        candidate_ids = [candidate.action_id for candidate in self.candidates]
        target_ids = set(candidate_ids)
        if len(candidate_ids) != len(target_ids):
            raise ValueError("candidate action_id values must be unique")
        target_ids_by_target = [candidate.target_id for candidate in self.candidates]
        if len(target_ids_by_target) != len(set(target_ids_by_target)):
            raise ValueError("candidate target_id values must be unique")
        if any(
            len(candidate.feature_values) != len(self.feature_names)
            for candidate in self.candidates
        ):
            raise ValueError("candidate feature length is incompatible")
        if set(self.target_distribution) != target_ids:
            raise ValueError("target_distribution keys must equal candidate actions")
        probabilities = list(self.target_distribution.values())
        if any(not math.isfinite(value) or value < 0.0 for value in probabilities):
            raise ValueError("target_distribution must be finite and non-negative")
        if not math.isclose(sum(probabilities), 1.0, abs_tol=_PROBABILITY_TOLERANCE):
            raise ValueError("target_distribution must sum to 1")
        observation_payload = {
            "schema_version": "npc_policy_observation.v1",
            "feature_schema_version": self.feature_schema_version,
            "game_id": self.game_id,
            "day": self.day,
            "phase": self.phase,
            "task": task_for_feature_schema(self.feature_schema_version),
            "actor_id": self.actor_id,
            "faction": self.faction,
            "reasoning_digest": self.reasoning_digest,
            "feature_names": self.feature_names,
            "candidates": [
                candidate.model_dump(mode="json")
                for candidate in self.candidates
            ],
        }
        expected_observation = policy_observation_digest(observation_payload)
        if expected_observation != self.observation_digest:
            raise ValueError("observation_digest is stale")
        if self.record_id != training_record_id(
            self.observation_digest,
            self.source_id,
            self.label_type,
        ):
            raise ValueError("record_id is not deterministic for this label")
        return self


class NPCPolicyLabelV1(StrictPolicyDataModel):
    """A separate human/expert label joined to a trace by digest."""

    schema_version: Literal["npc_policy_label.v1"] = POLICY_LABEL_SCHEMA_V1
    observation_digest: str = Field(pattern=_HEX64)
    preferred_action_id: Optional[str] = Field(
        default=None,
        pattern=_ACTION_ID,
    )
    target_distribution: Optional[dict[str, float]] = None
    label_type: Literal[
        "human_preference",
        "expert_preference",
        "self_play",
        "imported",
    ]
    weight: float = Field(default=1.0, gt=0.0, le=100.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_id: str = Field(min_length=1)
    rationale: Optional[str] = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_label(self) -> "NPCPolicyLabelV1":
        has_preferred = self.preferred_action_id is not None
        has_distribution = self.target_distribution is not None
        if has_preferred == has_distribution:
            raise ValueError(
                "provide exactly one of preferred_action_id or target_distribution"
            )
        if self.target_distribution is not None:
            if not self.target_distribution:
                raise ValueError("target_distribution cannot be empty")
            values = list(self.target_distribution.values())
            if any(not math.isfinite(value) or value < 0.0 for value in values):
                raise ValueError("label target_distribution is invalid")
            if not math.isclose(
                sum(values),
                1.0,
                abs_tol=_PROBABILITY_TOLERANCE,
            ):
                raise ValueError("label target_distribution must sum to 1")
        return self


class PolicyDataValidationError(ValueError):
    """Raised with a stable, user-facing JSONL line error."""


def _canonicalize_v1_payload(payload: dict[str, object]) -> dict[str, object]:
    """Canonicalize only floating-point fields; keep IDs/seeds as integers.

    ``strict=True`` intentionally rejects ``1.0`` where an integer is
    required.  User-authored JSON commonly writes feature values as integers,
    though, so those values are converted before the digest is calculated.
    """

    copied = dict(payload)
    candidates = copied.get("candidates")
    if isinstance(candidates, list):
        normalized_candidates = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                normalized_candidates.append(candidate)
                continue
            normalized_candidate = dict(candidate)
            values = normalized_candidate.get("feature_values")
            if isinstance(values, list):
                normalized_candidate["feature_values"] = [
                    float(value)
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                    else value
                    for value in values
                ]
            normalized_candidates.append(normalized_candidate)
        copied["candidates"] = normalized_candidates
    for field_name in ("rule_probabilities", "target_distribution"):
        values = copied.get(field_name)
        if isinstance(values, dict):
            copied[field_name] = {
                str(key): (
                    float(value)
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                    else value
                )
                for key, value in values.items()
            }
    for field_name in ("weight", "confidence"):
        value = copied.get(field_name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            copied[field_name] = float(value)
    return copied


def _observation_payload_from_record(
    record: PolicyTrainingRecordV1 | PolicyTrainingRecordV2,
) -> dict[str, object]:
    return {
        "schema_version": "npc_policy_observation.v1",
        "feature_schema_version": record.feature_schema_version,
        "game_id": record.game_id,
        "day": record.day,
        "phase": record.phase,
        "task": task_for_feature_schema(record.feature_schema_version),
        "actor_id": record.actor_id,
        "faction": record.faction,
        "reasoning_digest": record.reasoning_digest,
        "feature_names": record.feature_names,
        "candidates": [
            candidate.model_dump(mode="json")
            for candidate in record.candidates
        ],
    }


def training_record_id(
    observation_digest: str,
    source_id: str,
    label_type: str,
) -> str:
    return policy_observation_digest(
        {
            "observation_digest": observation_digest,
            "source_id": source_id,
            "label_type": label_type,
        }
    )


def _normalized_from_v1(
    record: PolicyTrainingRecordV1,
) -> dict[str, object]:
    target_distribution = {
        candidate.action_id: float(
            record.rule_probabilities[str(candidate.target_id)]
        )
        for candidate in record.candidates
    }
    return {
        "schema_version": POLICY_TRAINING_RECORD_V2,
        "record_id": training_record_id(
            record.observation_digest,
            "rule_teacher",
            "rule_teacher",
        ),
        "seed": record.seed,
        "episode_id": record.game_id,
        "game_id": record.game_id,
        "trace_index": record.trace_index,
        "day": record.day,
        "phase": record.phase,
        "actor_id": record.actor_id,
        "faction": record.faction,
        "reasoning_digest": record.reasoning_digest,
        "observation_digest": record.observation_digest,
        "feature_schema_version": record.feature_schema_version,
        "feature_names": record.feature_names,
        "candidates": [
            candidate.model_dump(mode="json")
            for candidate in record.candidates
        ],
        "target_distribution": target_distribution,
        "label_type": "rule_teacher",
        "source_id": "rule_teacher",
        "weight": 1.0,
        "rationale": None,
        "tags": ["converted_from_v1"],
    }


def load_policy_records(
    path: Path,
    *,
    reject_duplicate_observations: bool = True,
) -> list[dict[str, object]]:
    """Read V1/V2 JSONL and return canonical V2 dictionaries.

    No output is written when a line fails.  Errors include the source line so
    an external data feeder can fix one sample at a time.
    """

    records: list[dict[str, object]] = []
    seen_observations: dict[str, set[str]] = {}
    seen_trace_keys: dict[tuple[str, int], set[str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
            if not isinstance(raw, dict):
                raise ValueError("record must be a JSON object")
            canonical = _canonicalize_v1_payload(raw)
            schema = canonical.get("schema_version")
            if schema == POLICY_TRAINING_RECORD_V1:
                parsed = PolicyTrainingRecordV1.model_validate(canonical)
                normalized = _normalized_from_v1(parsed)
                trace_key = (parsed.game_id, parsed.trace_index)
            elif schema == POLICY_TRAINING_RECORD_V2:
                parsed_v2 = PolicyTrainingRecordV2.model_validate(canonical)
                normalized = parsed_v2.model_dump(mode="json")
                trace_key = (parsed_v2.game_id, parsed_v2.trace_index)
            else:
                raise ValueError(f"unsupported schema_version: {schema!r}")
            digest = str(normalized["observation_digest"])
            source_id = str(normalized["source_id"])
            if digest in seen_observations:
                if reject_duplicate_observations:
                    raise ValueError("duplicate observation_digest")
                if source_id in seen_observations[digest]:
                    raise ValueError("duplicate observation/source_id")
            if trace_key in seen_trace_keys and source_id in seen_trace_keys[trace_key]:
                raise ValueError("duplicate (game_id, trace_index, source_id)")
            seen_observations.setdefault(digest, set()).add(source_id)
            seen_trace_keys.setdefault(trace_key, set()).add(source_id)
            records.append(normalized)
        except Exception as exc:
            raise PolicyDataValidationError(
                f"{path}:{line_number}: {exc}"
            ) from exc
    if not records:
        raise PolicyDataValidationError(f"{path}: dataset contains no records")
    return records


def label_distribution(
    label: NPCPolicyLabelV1,
    candidates: list[dict[str, object]],
) -> dict[str, float]:
    action_ids = [str(candidate["action_id"]) for candidate in candidates]
    action_set = set(action_ids)
    if label.target_distribution is not None:
        if set(label.target_distribution) != action_set:
            raise ValueError("label actions do not match observation candidates")
        distribution = {
            action_id: float(label.target_distribution[action_id])
            for action_id in action_ids
        }
    else:
        assert label.preferred_action_id is not None
        if label.preferred_action_id not in action_set:
            raise ValueError("preferred_action_id is not a legal candidate")
        # A one-action legal set has probability one regardless of a
        # reviewer-supplied confidence value; confidence expresses ambiguity,
        # not permission to create a zero-mass label.
        if len(action_ids) == 1:
            return {action_ids[0]: 1.0}
        remainder = (1.0 - label.confidence) / (len(action_ids) - 1)
        distribution = {
            action_id: (
                label.confidence
                if action_id == label.preferred_action_id
                else remainder
            )
            for action_id in action_ids
        }
    total = sum(distribution.values())
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("label distribution has no probability mass")
    return {
        action_id: value / total for action_id, value in distribution.items()
    }


def merge_policy_labels(
    observations: list[dict[str, object]],
    labels_path: Path,
    *,
    include_teacher_records: bool = False,
) -> list[dict[str, object]]:
    by_digest = {
        str(record["observation_digest"]): record for record in observations
    }
    output = list(observations) if include_teacher_records else []
    seen_labels: set[tuple[str, str]] = set()
    for line_number, line in enumerate(
        labels_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            raw = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_json_keys,
            )
            if not isinstance(raw, dict):
                raise ValueError("label must be a JSON object")
            label = NPCPolicyLabelV1.model_validate(
                _canonicalize_v1_payload(raw)
            )
            base = by_digest.get(label.observation_digest)
            if base is None:
                raise ValueError("label references an unknown observation_digest")
            key = (label.observation_digest, label.source_id)
            if key in seen_labels:
                raise ValueError("duplicate label for observation/source_id")
            seen_labels.add(key)
            candidates = list(base["candidates"])  # type: ignore[arg-type]
            distribution = label_distribution(label, candidates)
            merged = {
                **base,
                "schema_version": POLICY_TRAINING_RECORD_V2,
                "record_id": training_record_id(
                    label.observation_digest,
                    label.source_id,
                    label.label_type,
                ),
                "target_distribution": distribution,
                "label_type": label.label_type,
                "source_id": label.source_id,
                "weight": label.weight,
                "rationale": label.rationale,
                "tags": list(label.tags),
            }
            # A human label is an offline annotation.  Keep only the canonical
            # fields accepted by the V2 model and validate the final record.
            parsed = PolicyTrainingRecordV2.model_validate(merged)
            output.append(parsed.model_dump(mode="json"))
        except Exception as exc:
            raise PolicyDataValidationError(
                f"{labels_path}:{line_number}: {exc}"
            ) from exc
    if not output:
        raise PolicyDataValidationError("label merge produced no records")
    return output


def write_policy_records(path: Path, records: list[dict[str, object]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for record in records
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "NPCPolicyLabelV1",
    "POLICY_DATASET_SCHEMA_V1",
    "POLICY_LABEL_SCHEMA_V1",
    "POLICY_TRAINING_RECORD_V1",
    "POLICY_TRAINING_RECORD_V2",
    "PolicyDataValidationError",
    "PolicyTrainingRecordV1",
    "PolicyTrainingRecordV2",
    "label_distribution",
    "load_policy_records",
    "merge_policy_labels",
    "policy_observation_digest",
    "training_record_id",
    "write_policy_records",
]
