"""Versioned, conservative LLM price lookup and cost summaries.

The price catalog is local configuration, not a claim that an upstream price
is current.  A request is only assigned a total cost when its provider usage,
billing model, and effective price are all known.  Otherwise the summary keeps
the raw counters and any independently provable partial cost, while leaving
``total_cost_usd_micros`` null.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


LLM_PRICE_CATALOG_SCHEMA_VERSION = "llm_price_catalog.v1"
LLM_COST_SUMMARY_SCHEMA_VERSION = "llm_cost_summary.v1"
LLM_PROVIDER_MODEL_COST_SCHEMA_VERSION = "llm_provider_model_cost.v1"
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LLM_PRICE_CATALOG_PATH = BACKEND_DIR / "config" / "llm_pricing.json"
# Short aliases make the default path easy to discover without weakening the
# explicit public constant used by callers and documentation.
DEFAULT_PRICE_CATALOG_PATH = DEFAULT_LLM_PRICE_CATALOG_PATH

SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")
UTC = timezone.utc


class LLMPricingError(ValueError):
    """Raised when an event cannot satisfy the cost-summary contract."""


class StrictPricingModel(BaseModel):
    """Base model for persisted catalogs and emitted summaries."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class LLMPriceEntryV1(StrictPricingModel):
    """One non-overlapping price window for a provider/model/billing mode."""

    price_id: str = Field(min_length=1, max_length=160)
    provider: str = Field(min_length=1, max_length=160)
    model: str = Field(min_length=1, max_length=160)
    billing_mode: str = Field(min_length=1, max_length=160)
    effective_from: str = Field(min_length=1)
    effective_until: Optional[str] = Field(default=None, min_length=1)
    pricing_status: Literal["known", "unknown"]
    input_usd_micros_per_million_tokens: Optional[int] = Field(
        default=None,
        ge=0,
    )
    output_usd_micros_per_million_tokens: Optional[int] = Field(
        default=None,
        ge=0,
    )
    source: Optional[str] = Field(default=None, min_length=1)
    verified_at: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_price_entry(self) -> "LLMPriceEntryV1":
        for field_name in ("price_id", "provider", "model", "billing_mode"):
            value = getattr(self, field_name)
            if SAFE_IDENTIFIER_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{field_name} must be a safe identifier")

        effective_from = _parse_utc_timestamp(
            self.effective_from,
            "effective_from",
        )
        if self.effective_until is not None:
            effective_until = _parse_utc_timestamp(
                self.effective_until,
                "effective_until",
            )
            if effective_until <= effective_from:
                raise ValueError("effective_until must be after effective_from")
        if self.verified_at is not None:
            _parse_utc_timestamp(self.verified_at, "verified_at")

        rates = (
            self.input_usd_micros_per_million_tokens,
            self.output_usd_micros_per_million_tokens,
        )
        if self.pricing_status == "known" and any(
            rate is None for rate in rates
        ):
            raise ValueError("known prices require both input and output rates")
        if self.pricing_status == "unknown" and any(
            rate is not None for rate in rates
        ):
            raise ValueError("unknown prices must not contain token rates")
        return self


class LLMPriceCatalogV1(StrictPricingModel):
    """Strict local price catalog with interval and identity validation."""

    schema_version: Literal["llm_price_catalog.v1"] = (
        LLM_PRICE_CATALOG_SCHEMA_VERSION
    )
    catalog_version: str = Field(min_length=1, max_length=160)
    currency: Literal["USD"] = "USD"
    unit_tokens: Literal[1_000_000] = 1_000_000
    entries: list[LLMPriceEntryV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_catalog(self) -> "LLMPriceCatalogV1":
        price_ids: set[str] = set()
        windows: dict[
            tuple[str, str, str],
            list[tuple[datetime, Optional[datetime], str]],
        ] = defaultdict(list)
        for entry in self.entries:
            if entry.price_id in price_ids:
                raise ValueError(f"duplicate price_id: {entry.price_id}")
            price_ids.add(entry.price_id)
            key = (entry.provider, entry.model, entry.billing_mode)
            windows[key].append(
                (
                    _parse_utc_timestamp(
                        entry.effective_from,
                        "effective_from",
                    ),
                    (
                        _parse_utc_timestamp(
                            entry.effective_until,
                            "effective_until",
                        )
                        if entry.effective_until is not None
                        else None
                    ),
                    entry.price_id,
                )
            )

        for key, key_windows in windows.items():
            sorted_windows = sorted(key_windows, key=lambda item: item[0])
            for previous, current in zip(sorted_windows, sorted_windows[1:]):
                previous_end = previous[1]
                if previous_end is None or current[0] < previous_end:
                    rendered_key = "/".join(key)
                    raise ValueError(
                        "overlapping price windows for "
                        f"{rendered_key}: {previous[2]} and {current[2]}"
                    )
        return self


class LLMProviderModelCostV1(StrictPricingModel):
    """Cost counters for one unambiguous structured provider/model group."""

    schema_version: Literal["llm_provider_model_cost.v1"] = (
        LLM_PROVIDER_MODEL_COST_SCHEMA_VERSION
    )
    provider: str = Field(min_length=1)
    configured_model: str = Field(min_length=1)
    billing_model: Optional[str] = Field(default=None, min_length=1)
    billing_mode: str = Field(min_length=1)
    request_count: int = Field(ge=0)
    billable_request_count: int = Field(ge=0)
    provider_attempt_count: int = Field(ge=0)
    adapter_retry_count: int = Field(ge=0)
    usage_complete_request_count: int = Field(ge=0)
    usage_partial_request_count: int = Field(ge=0)
    usage_missing_request_count: int = Field(ge=0)
    known_price_request_count: int = Field(ge=0)
    unknown_price_request_count: int = Field(ge=0)
    fully_costed_request_count: int = Field(ge=0)
    cost_unknown_request_count: int = Field(ge=0)
    raw_prompt_tokens: int = Field(ge=0)
    raw_completion_tokens: int = Field(ge=0)
    raw_total_tokens: int = Field(ge=0)
    known_cost_usd_micros: int = Field(ge=0)
    total_cost_usd_micros: Optional[int] = Field(default=None, ge=0)
    cost_complete: bool
    unknown_reason_counts: dict[str, int]

    @model_validator(mode="after")
    def validate_conservation(self) -> "LLMProviderModelCostV1":
        _validate_counter_conservation(
            self.billable_request_count,
            (
                self.usage_complete_request_count,
                self.usage_partial_request_count,
                self.usage_missing_request_count,
            ),
            "usage request counts",
        )
        _validate_counter_conservation(
            self.billable_request_count,
            (
                self.known_price_request_count,
                self.unknown_price_request_count,
            ),
            "price request counts",
        )
        _validate_counter_conservation(
            self.billable_request_count,
            (
                self.fully_costed_request_count,
                self.cost_unknown_request_count,
            ),
            "cost request counts",
        )
        if self.billable_request_count > self.request_count:
            raise ValueError("billable requests exceed all requests")
        if self.provider_attempt_count < self.billable_request_count:
            raise ValueError("provider attempts are fewer than billable requests")
        _validate_unknown_reasons(
            self.unknown_reason_counts,
            self.cost_unknown_request_count,
        )
        _validate_total_cost(
            self.cost_complete,
            self.cost_unknown_request_count,
            self.known_cost_usd_micros,
            self.total_cost_usd_micros,
        )
        return self


class LLMCostSummaryV1(StrictPricingModel):
    """Strict aggregate whose raw request, usage, and price counts conserve."""

    schema_version: Literal["llm_cost_summary.v1"] = (
        LLM_COST_SUMMARY_SCHEMA_VERSION
    )
    catalog_schema_version: Literal["llm_price_catalog.v1"] = (
        LLM_PRICE_CATALOG_SCHEMA_VERSION
    )
    catalog_version: str = Field(min_length=1)
    price_catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    currency: Literal["USD"] = "USD"
    unit_tokens: Literal[1_000_000] = 1_000_000
    request_count: int = Field(ge=0)
    billable_request_count: int = Field(ge=0)
    provider_attempt_count: int = Field(ge=0)
    adapter_retry_count: int = Field(ge=0)
    semantic_retry_count: int = Field(ge=0)
    usage_complete_request_count: int = Field(ge=0)
    usage_partial_request_count: int = Field(ge=0)
    usage_missing_request_count: int = Field(ge=0)
    known_price_request_count: int = Field(ge=0)
    unknown_price_request_count: int = Field(ge=0)
    fully_costed_request_count: int = Field(ge=0)
    cost_unknown_request_count: int = Field(ge=0)
    raw_prompt_tokens: int = Field(ge=0)
    raw_completion_tokens: int = Field(ge=0)
    raw_total_tokens: int = Field(ge=0)
    known_cost_usd_micros: int = Field(ge=0)
    total_cost_usd_micros: Optional[int] = Field(default=None, ge=0)
    cost_complete: bool
    unknown_reason_counts: dict[str, int]
    by_provider_model: list[LLMProviderModelCostV1]

    @model_validator(mode="after")
    def validate_conservation(self) -> "LLMCostSummaryV1":
        _validate_counter_conservation(
            self.billable_request_count,
            (
                self.usage_complete_request_count,
                self.usage_partial_request_count,
                self.usage_missing_request_count,
            ),
            "usage request counts",
        )
        _validate_counter_conservation(
            self.billable_request_count,
            (
                self.known_price_request_count,
                self.unknown_price_request_count,
            ),
            "price request counts",
        )
        _validate_counter_conservation(
            self.billable_request_count,
            (
                self.fully_costed_request_count,
                self.cost_unknown_request_count,
            ),
            "cost request counts",
        )
        _validate_unknown_reasons(
            self.unknown_reason_counts,
            self.cost_unknown_request_count,
        )
        _validate_total_cost(
            self.cost_complete,
            self.cost_unknown_request_count,
            self.known_cost_usd_micros,
            self.total_cost_usd_micros,
        )

        count_fields = (
            "request_count",
            "billable_request_count",
            "provider_attempt_count",
            "adapter_retry_count",
            "usage_complete_request_count",
            "usage_partial_request_count",
            "usage_missing_request_count",
            "known_price_request_count",
            "unknown_price_request_count",
            "fully_costed_request_count",
            "cost_unknown_request_count",
            "raw_prompt_tokens",
            "raw_completion_tokens",
            "raw_total_tokens",
            "known_cost_usd_micros",
        )
        for field_name in count_fields:
            group_total = sum(
                getattr(group, field_name) for group in self.by_provider_model
            )
            if group_total != getattr(self, field_name):
                raise ValueError(f"by_provider_model does not conserve {field_name}")
        combined_reasons: Counter[str] = Counter()
        for group in self.by_provider_model:
            combined_reasons.update(group.unknown_reason_counts)
        if dict(sorted(combined_reasons.items())) != self.unknown_reason_counts:
            raise ValueError("by_provider_model does not conserve unknown reasons")
        expected_order = sorted(
            self.by_provider_model,
            key=lambda item: (
                item.provider,
                item.configured_model,
                item.billing_model or "",
                item.billing_mode,
            ),
        )
        if self.by_provider_model != expected_order:
            raise ValueError("by_provider_model must be sorted")
        return self


def load_price_catalog(
    path: str | Path = DEFAULT_LLM_PRICE_CATALOG_PATH,
) -> LLMPriceCatalogV1:
    """Read and strictly validate one versioned local JSON price catalog."""

    return LLMPriceCatalogV1.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def price_catalog_fingerprint(
    catalog: LLMPriceCatalogV1 | dict[str, object],
) -> str:
    """Return the SHA-256 of the catalog's canonical strict JSON payload."""

    validated = (
        catalog
        if isinstance(catalog, LLMPriceCatalogV1)
        else LLMPriceCatalogV1.model_validate(catalog)
    )
    canonical = json.dumps(
        validated.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def summarize_llm_cost(
    events: Iterable[dict[str, object]],
    catalog: LLMPriceCatalogV1 | dict[str, object],
) -> dict[str, object]:
    """Summarize provable LLM cost without treating estimates as totals.

    Adapter-level ``request`` observations with at least one provider attempt
    are billable.  Semantic ``validation`` observations never add billable
    requests, but their retries are retained in ``semantic_retry_count``.
    Legacy v1 observations are fully costable only for a single attempt with a
    complete prompt/completion split; multi-attempt v1 usage has unknown retry
    coverage by contract.
    """

    validated_catalog = (
        catalog
        if isinstance(catalog, LLMPriceCatalogV1)
        else LLMPriceCatalogV1.model_validate(catalog)
    )
    summary = _empty_accumulator()
    groups: dict[tuple[str, str, Optional[str], str], dict[str, object]] = {}

    for raw_event in events:
        if not isinstance(raw_event, dict):
            raise LLMPricingError("LLM observation events must be objects")
        schema_version = str(raw_event.get("schema_version", ""))
        if schema_version not in {"llm_observation.v1", "llm_observation.v2"}:
            raise LLMPricingError("unsupported LLM observation schema version")
        event_type = str(raw_event.get("event_type", ""))
        if event_type == "validation":
            validation_attempt_count = _strict_non_negative_int(
                raw_event.get("attempt_count"),
                "attempt_count",
            )
            validation_retry_count = _strict_non_negative_int(
                raw_event.get("retry_count"),
                "retry_count",
            )
            if validation_retry_count != max(
                0,
                validation_attempt_count - 1,
            ):
                raise LLMPricingError(
                    "retry_count must equal max(0, attempt_count - 1)"
                )
            summary["semantic_retry_count"] += validation_retry_count
            continue
        if event_type != "request":
            raise LLMPricingError("unknown LLM observation event type")
        provider = _safe_event_identifier(raw_event.get("provider"), "provider")
        configured_model = _safe_event_identifier(
            raw_event.get("model"),
            "model",
        )
        billing_mode = _safe_event_identifier(
            raw_event.get("billing_mode", "standard"),
            "billing_mode",
        )
        attempt_count = _strict_non_negative_int(
            raw_event.get("attempt_count"),
            "attempt_count",
        )
        retry_count = _strict_non_negative_int(
            raw_event.get("retry_count"),
            "retry_count",
        )
        if retry_count != max(0, attempt_count - 1):
            raise LLMPricingError(
                "retry_count must equal max(0, attempt_count - 1)"
            )

        billing_model, billing_model_source = _event_billing_model(
            raw_event,
            schema_version=schema_version,
            configured_model=configured_model,
        )
        group_key = (
            provider,
            configured_model,
            billing_model,
            billing_mode,
        )
        group = groups.setdefault(group_key, _empty_accumulator())
        for accumulator in (summary, group):
            accumulator["request_count"] += 1

        if attempt_count == 0:
            _validate_zero_attempt_usage(raw_event, schema_version)
            continue

        prompt_tokens = _optional_strict_token_count(
            raw_event.get("prompt_tokens"),
            "prompt_tokens",
        )
        completion_tokens = _optional_strict_token_count(
            raw_event.get("completion_tokens"),
            "completion_tokens",
        )
        total_tokens = _optional_strict_token_count(
            raw_event.get("total_tokens"),
            "total_tokens",
        )
        if (
            prompt_tokens is not None
            and completion_tokens is not None
            and total_tokens is not None
            and prompt_tokens + completion_tokens != total_tokens
        ):
            raise LLMPricingError("token counts do not add up")

        usage_status, legacy_retry_unknown = _event_usage_status(
            raw_event,
            schema_version=schema_version,
            attempt_count=attempt_count,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        recorded_at = _parse_recorded_at(
            _required_event_string(raw_event.get("recorded_at"), "recorded_at"),
        )
        price_entry = None
        if billing_model is not None and billing_model_source not in {
            "mixed",
            "unknown",
        }:
            price_entry = _find_effective_price(
                validated_catalog,
                provider=provider,
                model=billing_model,
                billing_mode=billing_mode,
                recorded_at=recorded_at,
            )
        price_known = (
            price_entry is not None and price_entry.pricing_status == "known"
        )

        for accumulator in (summary, group):
            accumulator["billable_request_count"] += 1
            accumulator["provider_attempt_count"] += attempt_count
            accumulator["adapter_retry_count"] += retry_count
            accumulator[f"usage_{usage_status}_request_count"] += 1
            accumulator[
                "known_price_request_count"
                if price_known
                else "unknown_price_request_count"
            ] += 1
            accumulator["raw_prompt_tokens"] += prompt_tokens or 0
            accumulator["raw_completion_tokens"] += completion_tokens or 0
            accumulator["raw_total_tokens"] += total_tokens or 0

        event_known_cost = 0
        if price_known and price_entry is not None:
            event_known_cost = _known_event_cost_usd_micros(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                price_entry=price_entry,
                unit_tokens=validated_catalog.unit_tokens,
            )
        for accumulator in (summary, group):
            accumulator["known_cost_usd_micros"] += event_known_cost

        unknown_reason = _cost_unknown_reason(
            usage_status=usage_status,
            legacy_retry_unknown=legacy_retry_unknown,
            billing_model=billing_model,
            billing_model_source=billing_model_source,
            price_entry=price_entry,
        )
        if unknown_reason is None:
            for accumulator in (summary, group):
                accumulator["fully_costed_request_count"] += 1
        else:
            for accumulator in (summary, group):
                accumulator["cost_unknown_request_count"] += 1
                accumulator["unknown_reason_counts"][unknown_reason] += 1

    group_models: list[LLMProviderModelCostV1] = []
    for group_key in sorted(
        groups,
        key=lambda item: (item[0], item[1], item[2] or "", item[3]),
    ):
        provider, configured_model, billing_model, billing_mode = group_key
        group_models.append(
            LLMProviderModelCostV1.model_validate(
                {
                    "schema_version": LLM_PROVIDER_MODEL_COST_SCHEMA_VERSION,
                    "provider": provider,
                    "configured_model": configured_model,
                    "billing_model": billing_model,
                    "billing_mode": billing_mode,
                    **_finalize_accumulator(groups[group_key]),
                }
            )
        )

    result = LLMCostSummaryV1.model_validate(
        {
            "schema_version": LLM_COST_SUMMARY_SCHEMA_VERSION,
            "catalog_schema_version": LLM_PRICE_CATALOG_SCHEMA_VERSION,
            "catalog_version": validated_catalog.catalog_version,
            "price_catalog_fingerprint": price_catalog_fingerprint(
                validated_catalog
            ),
            "currency": validated_catalog.currency,
            "unit_tokens": validated_catalog.unit_tokens,
            **_finalize_accumulator(summary),
            "semantic_retry_count": summary["semantic_retry_count"],
            "by_provider_model": group_models,
        }
    )
    return result.model_dump(mode="json")


def _empty_accumulator() -> dict[str, object]:
    return {
        "request_count": 0,
        "billable_request_count": 0,
        "provider_attempt_count": 0,
        "adapter_retry_count": 0,
        "semantic_retry_count": 0,
        "usage_complete_request_count": 0,
        "usage_partial_request_count": 0,
        "usage_missing_request_count": 0,
        "known_price_request_count": 0,
        "unknown_price_request_count": 0,
        "fully_costed_request_count": 0,
        "cost_unknown_request_count": 0,
        "raw_prompt_tokens": 0,
        "raw_completion_tokens": 0,
        "raw_total_tokens": 0,
        "known_cost_usd_micros": 0,
        "unknown_reason_counts": Counter(),
    }


def _finalize_accumulator(accumulator: dict[str, object]) -> dict[str, object]:
    billable_request_count = int(accumulator["billable_request_count"])
    provider_attempt_count = int(accumulator["provider_attempt_count"])
    adapter_retry_count = int(accumulator["adapter_retry_count"])
    if provider_attempt_count != billable_request_count + adapter_retry_count:
        raise LLMPricingError(
            "provider attempts must equal billable requests plus adapter retries"
        )
    cost_unknown_count = int(accumulator["cost_unknown_request_count"])
    known_cost = int(accumulator["known_cost_usd_micros"])
    return {
        key: value
        for key, value in accumulator.items()
        if key != "semantic_retry_count"
    } | {
        "unknown_reason_counts": dict(
            sorted(Counter(accumulator["unknown_reason_counts"]).items())
        ),
        "cost_complete": cost_unknown_count == 0,
        "total_cost_usd_micros": (
            known_cost if cost_unknown_count == 0 else None
        ),
    }


def _event_billing_model(
    event: dict[str, object],
    *,
    schema_version: str,
    configured_model: str,
) -> tuple[Optional[str], str]:
    if schema_version == "llm_observation.v1":
        return configured_model, "configured"
    source = _required_event_string(
        event.get("billing_model_source"),
        "billing_model_source",
    )
    if source not in {"configured", "provider_response", "mixed", "unknown"}:
        raise LLMPricingError("unknown billing_model_source")
    raw_model = event.get("billing_model")
    if raw_model is None:
        if source not in {"mixed", "unknown"}:
            raise LLMPricingError("known billing model source requires a model")
        return None, source
    billing_model = _safe_event_identifier(raw_model, "billing_model")
    return billing_model, source


def _validate_zero_attempt_usage(
    event: dict[str, object],
    schema_version: str,
) -> None:
    if event.get("outcome") != "fallback":
        raise LLMPricingError(
            "zero-attempt requests must be non-billable fallbacks"
        )
    if any(
        event.get(field) is not None
        for field in ("prompt_tokens", "completion_tokens", "total_tokens")
    ):
        raise LLMPricingError("zero-attempt requests cannot contain token usage")
    if schema_version == "llm_observation.v1":
        return
    if event.get("token_usage_status") != "not_applicable":
        raise LLMPricingError(
            "zero-attempt requests require not_applicable token usage"
        )
    if (
        _strict_non_negative_int(
            event.get("usage_reported_attempt_count"),
            "usage_reported_attempt_count",
        )
        != 0
        or _strict_non_negative_int(
            event.get("usage_unreported_attempt_count"),
            "usage_unreported_attempt_count",
        )
        != 0
    ):
        raise LLMPricingError("zero-attempt usage counts must be zero")


def _event_usage_status(
    event: dict[str, object],
    *,
    schema_version: str,
    attempt_count: int,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
) -> tuple[str, bool]:
    values = (prompt_tokens, completion_tokens, total_tokens)
    inferred = (
        "missing"
        if all(value is None for value in values)
        else "complete"
        if all(value is not None for value in values)
        else "partial"
    )
    if schema_version == "llm_observation.v1":
        return inferred, attempt_count > 1

    status = _required_event_string(
        event.get("token_usage_status"),
        "token_usage_status",
    )
    if status not in {"complete", "partial", "missing"}:
        raise LLMPricingError("unknown token_usage_status")
    reported_attempts = _strict_non_negative_int(
        event.get("usage_reported_attempt_count"),
        "usage_reported_attempt_count",
    )
    unreported_attempts = _strict_non_negative_int(
        event.get("usage_unreported_attempt_count"),
        "usage_unreported_attempt_count",
    )
    if reported_attempts + unreported_attempts != attempt_count:
        raise LLMPricingError("usage attempt counts do not add up")
    if status == "complete":
        if inferred != "complete" or unreported_attempts != 0:
            raise LLMPricingError("complete usage does not cover every attempt")
    elif status == "missing":
        if inferred != "missing" or reported_attempts != 0:
            raise LLMPricingError("missing usage contains reported token data")
    elif inferred == "missing" and reported_attempts == 0:
        raise LLMPricingError("partial usage has no reported token data")
    return status, False


def _cost_unknown_reason(
    *,
    usage_status: str,
    legacy_retry_unknown: bool,
    billing_model: Optional[str],
    billing_model_source: str,
    price_entry: Optional[LLMPriceEntryV1],
) -> Optional[str]:
    if legacy_retry_unknown:
        return "legacy_retry_coverage_unknown"
    if usage_status == "missing":
        return "usage_missing"
    if usage_status == "partial":
        return "usage_partial"
    if billing_model_source == "mixed":
        return "billing_model_mixed"
    if billing_model_source == "unknown" or billing_model is None:
        return "billing_model_unknown"
    if price_entry is None:
        return "price_not_found"
    if price_entry.pricing_status == "unknown":
        return "price_catalog_unknown"
    return None


def _find_effective_price(
    catalog: LLMPriceCatalogV1,
    *,
    provider: str,
    model: str,
    billing_mode: str,
    recorded_at: datetime,
) -> Optional[LLMPriceEntryV1]:
    for entry in catalog.entries:
        if (
            entry.provider != provider
            or entry.model != model
            or entry.billing_mode != billing_mode
        ):
            continue
        effective_from = _parse_utc_timestamp(
            entry.effective_from,
            "effective_from",
        )
        effective_until = (
            _parse_utc_timestamp(entry.effective_until, "effective_until")
            if entry.effective_until is not None
            else None
        )
        if recorded_at >= effective_from and (
            effective_until is None or recorded_at < effective_until
        ):
            return entry
    return None


def _known_event_cost_usd_micros(
    *,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    price_entry: LLMPriceEntryV1,
    unit_tokens: int,
) -> int:
    input_rate = price_entry.input_usd_micros_per_million_tokens
    output_rate = price_entry.output_usd_micros_per_million_tokens
    if input_rate is None or output_rate is None:
        return 0
    exact_cost = (
        Decimal(prompt_tokens or 0) * Decimal(input_rate)
        + Decimal(completion_tokens or 0) * Decimal(output_rate)
    ) / Decimal(unit_tokens)
    return int(exact_cost.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _parse_utc_timestamp(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be UTC")
    return parsed.astimezone(UTC)


def _parse_recorded_at(value: str) -> datetime:
    """Accept any explicit observation timezone and compare it in UTC."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LLMPricingError("recorded_at must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise LLMPricingError("recorded_at must include a timezone")
    return parsed.astimezone(UTC)


def _strict_non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LLMPricingError(f"{field_name} must be a non-negative integer")
    return value


def _optional_strict_token_count(
    value: object,
    field_name: str,
) -> Optional[int]:
    if value is None:
        return None
    return _strict_non_negative_int(value, field_name)


def _required_event_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise LLMPricingError(f"{field_name} must be a non-empty trimmed string")
    return value


def _safe_event_identifier(value: object, field_name: str) -> str:
    identifier = _required_event_string(value, field_name)
    if SAFE_IDENTIFIER_PATTERN.fullmatch(identifier) is None:
        raise LLMPricingError(f"{field_name} must be a safe identifier")
    return identifier


def _validate_counter_conservation(
    expected: int,
    parts: tuple[int, ...],
    label: str,
) -> None:
    if sum(parts) != expected:
        raise ValueError(f"{label} do not conserve billable requests")


def _validate_unknown_reasons(
    reasons: dict[str, int],
    expected: int,
) -> None:
    for reason, count in reasons.items():
        if SAFE_IDENTIFIER_PATTERN.fullmatch(reason) is None:
            raise ValueError("unknown cost reason must be a safe identifier")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("unknown cost reason counts must be non-negative ints")
    if reasons != {key: reasons[key] for key in sorted(reasons)}:
        raise ValueError("unknown cost reasons must be sorted")
    if sum(reasons.values()) != expected:
        raise ValueError("unknown cost reasons do not conserve unknown requests")


def _validate_total_cost(
    cost_complete: bool,
    unknown_count: int,
    known_cost: int,
    total_cost: Optional[int],
) -> None:
    expected_complete = unknown_count == 0
    if cost_complete != expected_complete:
        raise ValueError("cost_complete does not match unknown request count")
    expected_total = known_cost if expected_complete else None
    if total_cost != expected_total:
        raise ValueError("total cost must be known cost iff cost is complete")


__all__ = [
    "DEFAULT_LLM_PRICE_CATALOG_PATH",
    "LLM_COST_SUMMARY_SCHEMA_VERSION",
    "LLM_PRICE_CATALOG_SCHEMA_VERSION",
    "LLMCostSummaryV1",
    "LLMPriceCatalogV1",
    "LLMPriceEntryV1",
    "LLMPricingError",
    "load_price_catalog",
    "price_catalog_fingerprint",
    "summarize_llm_cost",
]
