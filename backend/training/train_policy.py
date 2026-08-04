#!/usr/bin/env python3
"""Train a small local NPC candidate scorer.

The default ``linear`` model is intentionally compatible with the V5 V1
artifact.  ``--model-type mlp`` enables a one-hidden-layer NumPy MLP; both
models only score a rule-generated candidate list.  They cannot create an
action, inspect hidden truth, bypass permission checks, or sample a result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy import (  # noqa: E402
    NPC_POLICY_TASK_EXILE_VOTE,
    NPC_POLICY_TASKS,
    NPC_POLICY_ARTIFACT_SCHEMA_VERSION,
    NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2,
    NPC_POLICY_OBSERVATION_SCHEMA_VERSION,
    NPCPolicyArtifactManifestV1,
    NPCPolicyArtifactManifestV2,
    NPCPolicyArchitectureV2,
    TASK_FEATURE_NAMES,
    TASK_FEATURE_SCHEMA_VERSIONS,
    file_sha256,
)
from backend.app.npc_policy_data import load_policy_records  # noqa: E402


EPSILON = 1e-9


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train one local candidate scorer per NPC faction."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "backend" / "policy_artifacts",
    )
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.002)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument(
        "--model-type",
        "--model-kind",
        choices=("linear", "mlp"),
        default="linear",
        help="linear keeps npc_policy_artifact.v1 compatibility; mlp writes v2",
    )
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument(
        "--task",
        choices=NPC_POLICY_TASKS,
        default="exile_vote",
        help="policy task to train (exile_vote or sheriff_vote)",
    )
    return parser.parse_args()


def split_records(
    records: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Split by whole episode, never by individual decision rows."""

    groups: dict[str, list[dict[str, object]]] = {}
    for record in records:
        group_id = str(record.get("episode_id") or record["game_id"])
        groups.setdefault(group_id, []).append(record)
    group_names = sorted(groups)
    if len(group_names) < 2:
        raise ValueError(
            "training requires at least two distinct episode_id/game_id groups"
        )
    validation_groups = [
        group
        for group in group_names
        if int(hashlib.sha256(group.encode("utf-8")).hexdigest()[:8], 16) % 5 == 0
    ]
    if not validation_groups:
        validation_groups = [group_names[-1]]
    elif len(validation_groups) == len(group_names):
        validation_groups = [group_names[-1]]
    training_groups = [
        group for group in group_names if group not in set(validation_groups)
    ]
    training = [record for group in training_groups for record in groups[group]]
    validation = [record for group in validation_groups for record in groups[group]]
    return training, validation


def feature_rows(records: Iterable[dict[str, object]]) -> np.ndarray:
    rows = [
        candidate["feature_values"]
        for record in records
        for candidate in record["candidates"]  # type: ignore[index]
    ]
    return np.asarray(rows, dtype=np.float64)


def _record_matrix(
    record: dict[str, object],
    feature_mean: np.ndarray,
    feature_scale: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    candidates = record["candidates"]  # type: ignore[assignment]
    x = (
        np.asarray(
            [candidate["feature_values"] for candidate in candidates],  # type: ignore[index]
            dtype=np.float64,
        )
        - feature_mean
    ) / feature_scale
    x = np.clip(x, -20.0, 20.0)
    target_distribution = record["target_distribution"]  # type: ignore[assignment]
    targets = np.asarray(
        [
            max(
                EPSILON,
                float(target_distribution[str(candidate["action_id"])]),  # type: ignore[index]
            )
            for candidate in candidates
        ],
        dtype=np.float64,
    )
    targets /= max(EPSILON, targets.sum())
    weight = float(record.get("weight", 1.0))
    return x, targets, weight


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    values = np.exp(np.clip(shifted, -60.0, 60.0))
    return values / max(EPSILON, float(values.sum()))


def _initial_stats(
    training_records: list[dict[str, object]],
) -> tuple[np.ndarray, np.ndarray]:
    matrix = feature_rows(training_records)
    expected = len(training_records[0]["feature_names"])
    if matrix.ndim != 2 or matrix.shape[1] != expected:
        raise ValueError("feature matrix shape is incompatible")
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale < 1e-6, 1.0, scale)
    if not np.isfinite(mean).all() or not np.isfinite(scale).all():
        raise ValueError("feature statistics are non-finite")
    return mean, scale


def _score_linear(
    x: np.ndarray,
    weights: np.ndarray,
    bias: float,
) -> np.ndarray:
    return x @ weights + bias


def _score_mlp(
    x: np.ndarray,
    input_weights: np.ndarray,
    hidden_bias: np.ndarray,
    output_weights: np.ndarray,
    output_bias: float,
) -> tuple[np.ndarray, np.ndarray]:
    hidden = np.tanh(x @ input_weights + hidden_bias)
    return hidden @ output_weights + output_bias, hidden


def fit_linear(
    training_records: list[dict[str, object]],
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
    feature_mean: np.ndarray,
    feature_scale: np.ndarray,
) -> dict[str, object]:
    weights = np.zeros(len(feature_mean), dtype=np.float64)
    bias = 0.0
    rng = np.random.default_rng(seed)
    for _epoch in range(max(1, epochs)):
        for index in rng.permutation(len(training_records)):
            x, targets, sample_weight = _record_matrix(
                training_records[int(index)],
                feature_mean,
                feature_scale,
            )
            probabilities = _softmax(_score_linear(x, weights, bias))
            error = (probabilities - targets) * sample_weight
            weights -= learning_rate * (x.T @ error / len(x) + l2 * weights)
            # A common bias cancels in the candidate softmax, but keeping it
            # makes the artifact contract explicit.
            bias -= learning_rate * float(error.mean())
    if not np.isfinite(weights).all() or not math.isfinite(bias):
        raise ValueError("linear training produced non-finite parameters")
    return {
        "model_type": "linear",
        "weights": weights,
        "bias": bias,
        "feature_mean": feature_mean,
        "feature_scale": feature_scale,
    }


def fit_mlp(
    training_records: list[dict[str, object]],
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
    hidden_size: int,
    feature_mean: np.ndarray,
    feature_scale: np.ndarray,
) -> dict[str, object]:
    if not 4 <= hidden_size <= 256:
        raise ValueError("hidden-size must be between 4 and 256")
    rng = np.random.default_rng(seed)
    input_dim = len(feature_mean)
    input_weights = rng.normal(
        0.0,
        math.sqrt(2.0 / input_dim),
        size=(input_dim, hidden_size),
    ).astype(np.float64)
    hidden_bias = np.zeros(hidden_size, dtype=np.float64)
    output_weights = rng.normal(
        0.0,
        math.sqrt(2.0 / hidden_size),
        size=hidden_size,
    ).astype(np.float64)
    output_bias = 0.0
    for _epoch in range(max(1, epochs)):
        for index in rng.permutation(len(training_records)):
            x, targets, sample_weight = _record_matrix(
                training_records[int(index)],
                feature_mean,
                feature_scale,
            )
            logits, hidden = _score_mlp(
                x,
                input_weights,
                hidden_bias,
                output_weights,
                output_bias,
            )
            error = ((_softmax(logits) - targets) * sample_weight) / len(x)
            grad_output_weights = hidden.T @ error + l2 * output_weights
            grad_output_bias = float(error.sum())
            grad_hidden = np.outer(error, output_weights)
            grad_pre_activation = grad_hidden * (1.0 - hidden * hidden)
            grad_input_weights = x.T @ grad_pre_activation + l2 * input_weights
            grad_hidden_bias = grad_pre_activation.sum(axis=0)
            input_weights -= learning_rate * grad_input_weights
            hidden_bias -= learning_rate * grad_hidden_bias
            output_weights -= learning_rate * grad_output_weights
            output_bias -= learning_rate * grad_output_bias
    if (
        not np.isfinite(input_weights).all()
        or not np.isfinite(hidden_bias).all()
        or not np.isfinite(output_weights).all()
        or not math.isfinite(output_bias)
    ):
        raise ValueError("MLP training produced non-finite parameters")
    return {
        "model_type": "mlp",
        "input_weights": input_weights,
        "hidden_bias": hidden_bias,
        "output_weights": output_weights,
        "output_bias": output_bias,
        "feature_mean": feature_mean,
        "feature_scale": feature_scale,
    }


def evaluate(
    records: list[dict[str, object]],
    model: dict[str, object],
) -> tuple[float, float]:
    losses: list[float] = []
    agreements: list[float] = []
    for record in records:
        x, target, _weight = _record_matrix(
            record,
            model["feature_mean"],  # type: ignore[arg-type]
            model["feature_scale"],  # type: ignore[arg-type]
        )
        if model["model_type"] == "linear":
            logits = _score_linear(
                x,
                model["weights"],  # type: ignore[arg-type]
                float(model["bias"]),
            )
        else:
            logits, _hidden = _score_mlp(
                x,
                model["input_weights"],  # type: ignore[arg-type]
                model["hidden_bias"],  # type: ignore[arg-type]
                model["output_weights"],  # type: ignore[arg-type]
                float(model["output_bias"]),
            )
        probability = _softmax(logits)
        losses.append(
            float(-(target * np.log(np.maximum(probability, EPSILON))).sum())
        )
        target_best = {
            int(str(candidate["target_id"]))
            for candidate, value in zip(record["candidates"], target)  # type: ignore[index]
            if value == np.max(target)
        }
        predicted_target = int(
            record["candidates"][int(np.argmax(probability))]["target_id"]  # type: ignore[index]
        )
        agreements.append(float(predicted_target in target_best))
    return float(np.mean(losses)), float(np.mean(agreements))


def fit_faction(
    faction: str,
    records: list[dict[str, object]],
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
    model_type: str,
    hidden_size: int,
) -> dict[str, object]:
    faction_records = [
        record for record in records if record["faction"] == faction
    ]
    if len(faction_records) < 2:
        raise ValueError(f"not enough {faction} records to train")
    training_records, validation_records = split_records(faction_records)
    feature_mean, feature_scale = _initial_stats(training_records)
    common = {
        "epochs": epochs,
        "learning_rate": learning_rate,
        "l2": l2,
        "seed": seed,
        "feature_mean": feature_mean,
        "feature_scale": feature_scale,
    }
    if model_type == "linear":
        model = fit_linear(training_records, **common)
    else:
        model = fit_mlp(
            training_records,
            hidden_size=hidden_size,
            **common,
        )
    validation_loss, validation_top1 = evaluate(validation_records, model)
    return {
        **model,
        "faction": faction,
        "training_samples": len(training_records),
        "validation_samples": len(validation_records),
        "validation_cross_entropy": validation_loss,
        "validation_top1_agreement": validation_top1,
        "training_episodes": sorted(
            {str(record.get("episode_id") or record["game_id"]) for record in training_records}
        ),
        "validation_episodes": sorted(
            {str(record.get("episode_id") or record["game_id"]) for record in validation_records}
        ),
    }


def save_artifact(
    output_dir: Path,
    result: dict[str, object],
    *,
    dataset_digest: str,
    training_seed: int,
    task: str,
    feature_names: tuple[str, ...],
    feature_schema_version: str,
) -> dict[str, object]:
    faction = str(result["faction"])
    model_type = str(result["model_type"])
    task_dir = "" if task == NPC_POLICY_TASK_EXILE_VOTE else task
    artifact_dir = output_dir / task_dir / (
        "good_policy_v1" if faction == "good" else "wolf_policy_v1"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.npz"
    if model_type == "linear":
        np.savez(
            model_path,
            weights=result["weights"],
            bias=np.asarray(result["bias"], dtype=np.float64),
            feature_mean=result["feature_mean"],
            feature_scale=result["feature_scale"],
        )
        manifest_payload = {
            "schema_version": NPC_POLICY_ARTIFACT_SCHEMA_VERSION,
            "model_id": (
                f"local_linear_{faction}_v1"
                if task == NPC_POLICY_TASK_EXILE_VOTE
                else f"local_linear_{task}_{faction}_v1"
            ),
        }
        manifest_cls = NPCPolicyArtifactManifestV1
    else:
        np.savez(
            model_path,
            input_weights=result["input_weights"],
            hidden_bias=result["hidden_bias"],
            output_weights=result["output_weights"],
            output_bias=np.asarray(result["output_bias"], dtype=np.float64),
            feature_mean=result["feature_mean"],
            feature_scale=result["feature_scale"],
        )
        manifest_payload = {
            "schema_version": NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2,
            "model_id": (
                f"local_mlp_{faction}_v2"
                if task == NPC_POLICY_TASK_EXILE_VOTE
                else f"local_mlp_{task}_{faction}_v2"
            ),
            "model_type": "mlp",
            "architecture": {
                "input_dim": len(feature_names),
                "hidden_dims": [int(result["input_weights"].shape[1])],  # type: ignore[index]
                "activation": "tanh",
                "output_dim": 1,
            },
        }
        manifest_cls = NPCPolicyArtifactManifestV2
    model_digest = file_sha256(model_path)
    manifest_payload.update(
        {
            "faction": faction,
            "task": task,
            "observation_schema_version": NPC_POLICY_OBSERVATION_SCHEMA_VERSION,
            "feature_schema_version": feature_schema_version,
            "feature_names": list(feature_names),
            "model_file": "model.npz",
            "model_sha256": model_digest,
            "dataset_digest": dataset_digest,
            "training_seed": training_seed,
            "training_samples": int(result["training_samples"]),
            "validation_samples": int(result["validation_samples"]),
            "validation_cross_entropy": float(result["validation_cross_entropy"]),
            "validation_top1_agreement": float(result["validation_top1_agreement"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    manifest = manifest_cls.model_validate(manifest_payload)
    (artifact_dir / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest.model_dump(mode="json")


def _artifact_directory_name(faction: str) -> str:
    return "good_policy_v1" if faction == "good" else "wolf_policy_v1"


def _commit_staged_artifacts(
    staging_dir: Path,
    output_dir: Path,
    factions: tuple[str, ...] = ("good", "werewolf"),
    task: str = NPC_POLICY_TASK_EXILE_VOTE,
) -> None:
    """Replace the two faction artifacts as one recoverable filesystem step.

    Training and serialization happen entirely below ``staging_dir``.  The
    old pair is moved to an explicit temporary backup before either new
    directory becomes active; an exception rolls the old pair back.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    task_dir = "" if task == NPC_POLICY_TASK_EXILE_VOTE else task
    if task_dir:
        (output_dir / task_dir).mkdir(parents=True, exist_ok=True)
    backup_dir = Path(
        tempfile.mkdtemp(prefix=".npc-policy-backup-", dir=output_dir)
    )
    moved_old: list[tuple[Path, Path]] = []
    moved_new: list[Path] = []
    try:
        for faction in factions:
            name = _artifact_directory_name(faction)
            source = staging_dir / task_dir / name
            target = output_dir / task_dir / name
            if not source.is_dir():
                raise FileNotFoundError(f"staged artifact is missing: {source}")
            backup_target = backup_dir / name
            if target.exists() or target.is_symlink():
                os.replace(target, backup_target)
                moved_old.append((backup_target, target))
            os.replace(source, target)
            moved_new.append(target)
    except Exception:
        for target in reversed(moved_new):
            if target.exists() or target.is_symlink():
                shutil.rmtree(target)
        for backup_target, target in reversed(moved_old):
            if backup_target.exists() or backup_target.is_symlink():
                os.replace(backup_target, target)
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)


def main() -> int:
    args = parse_args()
    if args.epochs < 1 or args.learning_rate <= 0 or args.l2 < 0:
        raise SystemExit("epochs must be positive, learning rate > 0, l2 >= 0")
    records = load_policy_records(
        args.dataset,
        reject_duplicate_observations=False,
    )
    feature_names = TASK_FEATURE_NAMES[args.task]
    feature_schema_version = TASK_FEATURE_SCHEMA_VERSIONS[args.task]
    dataset_digest = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    manifests = []
    results = {}
    factions = ("good", "werewolf")
    fitted: dict[str, dict[str, object]] = {}
    for offset, faction in enumerate(factions):
        result = fit_faction(
            faction,
            records,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            l2=args.l2,
            seed=args.seed + offset,
            model_type=args.model_type,
            hidden_size=args.hidden_size,
        )
        fitted[faction] = result
        results[faction] = {
            key: value
            for key, value in result.items()
            if not isinstance(value, np.ndarray)
            and key
            not in {
                "weights",
                "feature_mean",
                "feature_scale",
                "bias",
                "input_weights",
                "hidden_bias",
                "output_weights",
                "output_bias",
            }
        }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=".npc-policy-staging-", dir=args.output_dir)
    )
    try:
        for offset, faction in enumerate(factions):
            manifests.append(
                save_artifact(
                    staging_dir,
                    fitted[faction],
                    dataset_digest=dataset_digest,
                    training_seed=args.seed + offset,
                    task=args.task,
                    feature_names=feature_names,
                    feature_schema_version=feature_schema_version,
                )
            )
        _commit_staged_artifacts(
            staging_dir,
            args.output_dir,
            factions,
            task=args.task,
        )
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
    print(
        json.dumps(
            {
                "schema_version": (
                    NPC_POLICY_ARTIFACT_SCHEMA_VERSION
                    if args.model_type == "linear"
                    else NPC_POLICY_ARTIFACT_SCHEMA_VERSION_V2
                ),
                "model_type": args.model_type,
                "dataset": str(args.dataset),
                "dataset_digest": dataset_digest,
                "artifacts": manifests,
                "evaluation": results,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
