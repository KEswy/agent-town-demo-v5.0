"""Redacted local LLM request and validation metrics for Agent Town M09-A."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional


LLM_OBSERVATION_SCHEMA_VERSION = "llm_observation.v1"
LLM_OBSERVABILITY_SUMMARY_VERSION = "llm_observability_summary.v1"
LLM_OBSERVABILITY_MODE = "redacted_local_jsonl"
BACKEND_DIR = Path(__file__).resolve().parents[1]
LLM_OBSERVABILITY_LOG_FILE = BACKEND_DIR / "data" / "llm_observability.jsonl"
KNOWN_LLM_TASKS = {
    "connection_check",
    "public_speech",
    "public_speech_voice_prefix",
    "resident_chat",
    "rewrite_private_reply",
    "rewrite_public_speech",
}
REQUEST_OUTCOMES = ("success", "fallback")
VALIDATION_OUTCOMES = ("recovered", "fallback")
EVENT_FIELDS = {
    "schema_version",
    "recorded_at",
    "event_type",
    "task",
    "operation",
    "provider",
    "model",
    "outcome",
    "attempt_count",
    "retry_count",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "fallback_category",
    "rejection_category_counts",
}
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,96}$")


class LLMObservationError(ValueError):
    """Raised when an event does not satisfy the redacted M09-A contract."""


class LLMObservationRecorder:
    """Append validated, redacted observation events to one local JSONL file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def record_event(self, event: dict[str, object]) -> None:
        try:
            normalized = normalize_observation_event(event)
            serialized = json.dumps(
                normalized,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as log_file:
                    log_file.write(serialized + "\n")
        except (LLMObservationError, OSError, TypeError, ValueError):
            # Observability must never interrupt a game or an LLM fallback.
            return


LLM_OBSERVABILITY_RECORDER = LLMObservationRecorder(
    LLM_OBSERVABILITY_LOG_FILE
)


def build_request_observation(
    *,
    task: object,
    operation: str,
    provider: object,
    model: object,
    outcome: str,
    attempt_count: int,
    retry_count: int,
    latency_ms: float,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    fallback_category: str = "",
    recorded_at: Optional[str] = None,
) -> dict[str, object]:
    """Build one adapter-level event without prompts, contexts, or responses."""

    return normalize_observation_event(
        {
            "schema_version": LLM_OBSERVATION_SCHEMA_VERSION,
            "recorded_at": recorded_at or _utc_now(),
            "event_type": "request",
            "task": normalize_llm_task(task),
            "operation": operation,
            "provider": normalize_safe_identifier(provider, "unknown"),
            "model": normalize_safe_identifier(model, "unknown"),
            "outcome": outcome,
            "attempt_count": attempt_count,
            "retry_count": retry_count,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "fallback_category": fallback_category,
            "rejection_category_counts": {},
        }
    )


def build_validation_observation(
    *,
    task: object,
    provider: object,
    model: object,
    outcome: str,
    attempts: list[dict[str, object]],
    recorded_at: Optional[str] = None,
) -> dict[str, object]:
    """Build one semantic-validation event from categories, never raw attempts."""

    return normalize_observation_event(
        {
            "schema_version": LLM_OBSERVATION_SCHEMA_VERSION,
            "recorded_at": recorded_at or _utc_now(),
            "event_type": "validation",
            "task": normalize_llm_task(task),
            "operation": "semantic_validation",
            "provider": normalize_safe_identifier(provider, "unknown"),
            "model": normalize_safe_identifier(model, "unknown"),
            "outcome": outcome,
            "attempt_count": len(attempts),
            "retry_count": max(0, len(attempts) - 1),
            "latency_ms": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "fallback_category": (
                "validation_exhausted" if outcome == "fallback" else ""
            ),
            "rejection_category_counts": build_rejection_category_counts(
                attempts
            ),
        }
    )


def build_rejection_category_counts(
    attempts: list[dict[str, object]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for attempt in attempts:
        if bool(attempt.get("passed", False)):
            continue
        reason = str(attempt.get("rejection_reason", ""))
        counts[classify_validation_rejection(reason)] += 1
    return {key: counts[key] for key in sorted(counts)}


def classify_validation_rejection(reason: str) -> str:
    normalized = reason.casefold()
    if any(
        marker in normalized
        for marker in (
            "hidden",
            "private",
            "unsupported role",
            "unsupported character identity",
            "unsupported camp assertion",
        )
    ):
        return "hidden_information"
    if "continuity" in normalized:
        return "continuity"
    if "schema" in normalized or "json" in normalized:
        return "schema_invalid"
    if any(marker in normalized for marker in ("omitted", "required", "missing")):
        return "missing_required_fact"
    if any(
        marker in normalized
        for marker in ("changed", "introduced", "mismatch", "not_allowed")
    ):
        return "fact_mismatch"
    if "length" in normalized or "token limit" in normalized:
        return "invalid_length"
    if any(
        marker in normalized
        for marker in ("empty pass", "replacement character", "voice prefix")
    ):
        return "unsafe_expression"
    if any(
        marker in normalized
        for marker in ("http", "timeout", "network", "connect", "request failed")
    ):
        return "request_failure"
    return "validation_other"


def classify_request_fallback(reason: object) -> str:
    normalized = str(reason).casefold()
    if "disabled" in normalized:
        return "disabled"
    if "mock provider" in normalized:
        return "mock"
    if "not fully configured" in normalized:
        return "not_configured"
    if "429" in normalized or "rate limit" in normalized:
        return "rate_limit"
    if "401" in normalized or "403" in normalized or "authentication" in normalized:
        return "authentication"
    if "timeout" in normalized:
        return "timeout"
    if any(marker in normalized for marker in ("connect", "network", "protocol")):
        return "network"
    if "jsondecodeerror" in normalized or "not-json" in normalized:
        return "invalid_json"
    if "replacement character" in normalized:
        return "invalid_payload"
    if "token limit" in normalized:
        return "token_limit"
    if "empty" in normalized:
        return "empty_response"
    if "httpstatuserror" in normalized:
        return "http_error"
    if any(marker in normalized for marker in ("keyerror", "typeerror")):
        return "invalid_response"
    if "valueerror" in normalized:
        return "invalid_payload"
    return "unknown"


def normalize_observation_event(
    event: dict[str, object],
) -> dict[str, object]:
    if set(event) != EVENT_FIELDS:
        raise LLMObservationError("observation event fields do not match v1")
    if event.get("schema_version") != LLM_OBSERVATION_SCHEMA_VERSION:
        raise LLMObservationError("unknown observation schema version")
    recorded_at = str(event.get("recorded_at", "")).strip()
    if not recorded_at:
        raise LLMObservationError("recorded_at is required")
    try:
        parsed_recorded_at = datetime.fromisoformat(
            recorded_at.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise LLMObservationError("recorded_at must be ISO 8601") from exc
    if parsed_recorded_at.tzinfo is None:
        raise LLMObservationError("recorded_at must include a timezone")
    event_type = str(event.get("event_type", ""))
    if event_type not in {"request", "validation"}:
        raise LLMObservationError("unknown observation event type")
    task = normalize_llm_task(event.get("task"))
    operation = normalize_safe_identifier(event.get("operation"), "unknown")
    provider = normalize_safe_identifier(event.get("provider"), "unknown")
    model = normalize_safe_identifier(event.get("model"), "unknown")
    outcome = str(event.get("outcome", ""))
    allowed_outcomes = (
        REQUEST_OUTCOMES if event_type == "request" else VALIDATION_OUTCOMES
    )
    if outcome not in allowed_outcomes:
        raise LLMObservationError("outcome does not match event type")
    attempt_count = _non_negative_int(event.get("attempt_count"), "attempt_count")
    retry_count = _non_negative_int(event.get("retry_count"), "retry_count")
    if retry_count > max(0, attempt_count - 1):
        raise LLMObservationError("retry_count exceeds attempt_count")
    latency_ms = _optional_non_negative_float(event.get("latency_ms"), "latency_ms")
    prompt_tokens = _optional_non_negative_int(event.get("prompt_tokens"), "prompt_tokens")
    completion_tokens = _optional_non_negative_int(
        event.get("completion_tokens"),
        "completion_tokens",
    )
    total_tokens = _optional_non_negative_int(event.get("total_tokens"), "total_tokens")
    if (
        total_tokens is not None
        and prompt_tokens is not None
        and completion_tokens is not None
        and total_tokens != prompt_tokens + completion_tokens
    ):
        raise LLMObservationError("token counts do not add up")
    fallback_category = str(event.get("fallback_category", "")).strip()
    if fallback_category:
        fallback_category = normalize_safe_identifier(
            fallback_category,
            "unknown",
        )
    rejection_counts_raw = event.get("rejection_category_counts")
    if not isinstance(rejection_counts_raw, dict):
        raise LLMObservationError("rejection_category_counts must be an object")
    rejection_counts: dict[str, int] = {}
    for raw_category, raw_count in rejection_counts_raw.items():
        category = normalize_safe_identifier(raw_category, "unknown")
        rejection_counts[category] = _non_negative_int(
            raw_count,
            "rejection category count",
        )
    if event_type == "request" and rejection_counts:
        raise LLMObservationError("request events cannot contain rejection counts")
    if event_type == "validation" and latency_ms is not None:
        raise LLMObservationError("validation latency is measured by request events")
    return {
        "schema_version": LLM_OBSERVATION_SCHEMA_VERSION,
        "recorded_at": recorded_at,
        "event_type": event_type,
        "task": task,
        "operation": operation,
        "provider": provider,
        "model": model,
        "outcome": outcome,
        "attempt_count": attempt_count,
        "retry_count": retry_count,
        "latency_ms": latency_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "fallback_category": fallback_category,
        "rejection_category_counts": {
            key: rejection_counts[key] for key in sorted(rejection_counts)
        },
    }


def normalize_llm_task(value: object) -> str:
    task = str(value or "").strip().casefold()
    return task if task in KNOWN_LLM_TASKS else "other"


def normalize_safe_identifier(value: object, fallback: str) -> str:
    normalized = str(value or "").strip()
    return normalized if SAFE_IDENTIFIER_PATTERN.fullmatch(normalized) else fallback


def extract_token_usage(response_data: dict[str, object]) -> tuple[
    Optional[int],
    Optional[int],
    Optional[int],
]:
    usage = response_data.get("usage")
    if not isinstance(usage, dict):
        return None, None, None
    try:
        prompt_tokens = _optional_non_negative_int(
            usage.get("prompt_tokens"),
            "prompt_tokens",
        )
        completion_tokens = _optional_non_negative_int(
            usage.get("completion_tokens"),
            "completion_tokens",
        )
        total_tokens = _optional_non_negative_int(
            usage.get("total_tokens"),
            "total_tokens",
        )
    except LLMObservationError:
        return None, None, None
    if (
        total_tokens is None
        and prompt_tokens is not None
        and completion_tokens is not None
    ):
        total_tokens = prompt_tokens + completion_tokens
    if (
        total_tokens is not None
        and prompt_tokens is not None
        and completion_tokens is not None
        and total_tokens != prompt_tokens + completion_tokens
    ):
        return None, None, None
    return prompt_tokens, completion_tokens, total_tokens


def summarize_observation_events(
    events: Iterable[dict[str, object]],
    *,
    invalid_event_count: int = 0,
) -> dict[str, object]:
    normalized_events: list[dict[str, object]] = []
    invalid_count = max(0, int(invalid_event_count))
    for event in events:
        try:
            normalized_events.append(normalize_observation_event(event))
        except (LLMObservationError, TypeError, ValueError):
            invalid_count += 1
    timestamps = sorted(str(event["recorded_at"]) for event in normalized_events)
    overall = _summarize_group(normalized_events)
    tasks = sorted({str(event["task"]) for event in normalized_events})
    provider_models = sorted(
        {
            f"{event['provider']}/{event['model']}"
            for event in normalized_events
        }
    )
    return {
        "schema_version": LLM_OBSERVABILITY_SUMMARY_VERSION,
        "event_schema_version": LLM_OBSERVATION_SCHEMA_VERSION,
        "mode": LLM_OBSERVABILITY_MODE,
        "window_start": timestamps[0] if timestamps else None,
        "window_end": timestamps[-1] if timestamps else None,
        "event_count": len(normalized_events),
        "invalid_event_count": invalid_count,
        **overall,
        "by_task": {
            task: _summarize_group(
                [event for event in normalized_events if event["task"] == task]
            )
            for task in tasks
        },
        "by_provider_model": {
            key: _summarize_group(
                [
                    event
                    for event in normalized_events
                    if f"{event['provider']}/{event['model']}" == key
                ]
            )
            for key in provider_models
        },
    }


def summarize_observation_file(path: Path) -> dict[str, object]:
    events: list[dict[str, object]] = []
    invalid_count = 0
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    except OSError:
        lines = []
        invalid_count = 1
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            invalid_count += 1
            continue
        if not isinstance(payload, dict):
            invalid_count += 1
            continue
        events.append(payload)
    return summarize_observation_events(
        events,
        invalid_event_count=invalid_count,
    )


def _summarize_group(events: list[dict[str, object]]) -> dict[str, object]:
    request_events = [event for event in events if event["event_type"] == "request"]
    validation_events = [
        event for event in events if event["event_type"] == "validation"
    ]
    request_outcomes = Counter(str(event["outcome"]) for event in request_events)
    validation_outcomes = Counter(
        str(event["outcome"]) for event in validation_events
    )
    fallback_categories = Counter(
        str(event["fallback_category"])
        for event in events
        if event["fallback_category"]
    )
    rejection_categories: Counter[str] = Counter()
    for event in validation_events:
        rejection_categories.update(event["rejection_category_counts"])
    attempt_counts = [int(event["attempt_count"]) for event in events]
    latencies = sorted(
        float(event["latency_ms"])
        for event in request_events
        if event["latency_ms"] is not None
    )
    token_events = [
        event for event in request_events if event["total_tokens"] is not None
    ]
    request_count = len(request_events)
    success_count = request_outcomes.get("success", 0)
    return {
        "request_count": request_count,
        "request_success_count": success_count,
        "request_fallback_count": request_outcomes.get("fallback", 0),
        "request_success_rate": (
            round(success_count / request_count, 6) if request_count else None
        ),
        "validation_count": len(validation_events),
        "validation_recovered_count": validation_outcomes.get("recovered", 0),
        "validation_fallback_count": validation_outcomes.get("fallback", 0),
        "attempt_count": sum(attempt_counts),
        "average_attempt_count": (
            round(sum(attempt_counts) / len(attempt_counts), 3)
            if attempt_counts
            else None
        ),
        "retry_count": sum(int(event["retry_count"]) for event in events),
        "latency_sample_count": len(latencies),
        "average_latency_ms": (
            round(sum(latencies) / len(latencies), 3) if latencies else None
        ),
        "p95_latency_ms": _nearest_rank_percentile(latencies, 0.95),
        "max_latency_ms": round(latencies[-1], 3) if latencies else None,
        "token_sample_count": len(token_events),
        "prompt_tokens": sum(int(event["prompt_tokens"] or 0) for event in token_events),
        "completion_tokens": sum(
            int(event["completion_tokens"] or 0) for event in token_events
        ),
        "total_tokens": sum(int(event["total_tokens"] or 0) for event in token_events),
        "fallback_category_counts": {
            key: fallback_categories[key] for key in sorted(fallback_categories)
        },
        "rejection_category_counts": {
            key: rejection_categories[key] for key in sorted(rejection_categories)
        },
    }


def _nearest_rank_percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    rank = max(1, math.ceil(percentile * len(values)))
    return round(values[rank - 1], 3)


def _non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LLMObservationError(f"{label} must be a non-negative integer")
    return value


def _optional_non_negative_int(value: object, label: str) -> Optional[int]:
    if value is None:
        return None
    return _non_negative_int(value, label)


def _optional_non_negative_float(value: object, label: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMObservationError(f"{label} must be numeric or null")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise LLMObservationError(f"{label} must be finite and non-negative")
    return round(normalized, 3)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "KNOWN_LLM_TASKS",
    "LLM_OBSERVABILITY_MODE",
    "LLM_OBSERVABILITY_LOG_FILE",
    "LLM_OBSERVABILITY_RECORDER",
    "LLM_OBSERVABILITY_SUMMARY_VERSION",
    "LLM_OBSERVATION_SCHEMA_VERSION",
    "LLMObservationError",
    "LLMObservationRecorder",
    "build_rejection_category_counts",
    "build_request_observation",
    "build_validation_observation",
    "classify_request_fallback",
    "classify_validation_rejection",
    "extract_token_usage",
    "normalize_llm_task",
    "normalize_observation_event",
    "summarize_observation_events",
    "summarize_observation_file",
]
