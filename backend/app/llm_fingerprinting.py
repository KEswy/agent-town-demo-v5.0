"""Redacted, deterministic fingerprints for LLM experiments.

The helpers in this module deliberately have no dependency on ``main`` or
``llm``.  Prompt text and endpoint identities are used only while calculating
digests; experiment manifests contain digests instead of those source values.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Literal
from urllib.parse import SplitResult, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


DIGEST_ALGORITHM = "canonical_json_sha256.v1"
LLM_PROMPT_FINGERPRINT_SCHEMA_VERSION = "llm_prompt_fingerprint.v1"
LLM_CONFIG_FINGERPRINT_SCHEMA_VERSION = "llm_config_fingerprint.v1"
EXPERIMENT_FINGERPRINT_SCHEMA_VERSION = "experiment_fingerprint.v1"
RULE_ONLY_EXECUTION_MODE = "rule_only_no_llm"

_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_SAFE_COMPONENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")


class ExperimentComponentFingerprintV1(BaseModel):
    """One redacted component entry in an experiment manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,95}$")
    digest: str = Field(pattern=_DIGEST_PATTERN)
    active: bool


class ExperimentFingerprintV1(BaseModel):
    """Strict, JSON-safe identity for one executable experiment setup."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["experiment_fingerprint.v1"] = (
        EXPERIMENT_FINGERPRINT_SCHEMA_VERSION
    )
    fingerprint_algorithm: Literal["canonical_json_sha256.v1"] = (
        DIGEST_ALGORITHM
    )
    execution_mode: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    configuration_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    effective_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    components: list[ExperimentComponentFingerprintV1] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_components(self) -> "ExperimentFingerprintV1":
        names = [component.name for component in self.components]
        if names != sorted(names):
            raise ValueError("experiment components must be sorted by name")
        if len(names) != len(set(names)):
            raise ValueError("experiment component names must be unique")
        if not any(component.active for component in self.components):
            raise ValueError("at least one experiment component must be active")
        return self


class _LLMConfigFingerprintPayload(BaseModel):
    """Allowlisted effective LLM settings used only as digest input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["llm_config_fingerprint.v1"] = (
        LLM_CONFIG_FINGERPRINT_SCHEMA_VERSION
    )
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=256)
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(ge=1)
    timeout_seconds: float = Field(gt=0.0)
    max_retries: int = Field(ge=0)
    retry_delay_seconds: float = Field(ge=0.0)
    endpoint_identity_digest: str = Field(pattern=_DIGEST_PATTERN)
    deepseek_thinking_type: str
    deepseek_response_format_type: str

    @model_validator(mode="after")
    def validate_finite_numbers(self) -> "_LLMConfigFingerprintPayload":
        for value in (
            self.temperature,
            self.timeout_seconds,
            self.retry_delay_seconds,
        ):
            if not math.isfinite(value):
                raise ValueError("LLM numeric settings must be finite")
        return self


def canonical_payload_digest(payload: object) -> str:
    """Return a SHA-256 digest of compact, key-sorted canonical JSON."""

    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_prompt_fingerprint(
    system_prompt: str,
    *,
    task: str,
    operation: str,
    contract_version: str = "llm_json_contract.v1",
    retry_protocol_version: str = "llm_retry_protocol.v1",
) -> str:
    """Fingerprint the exact prompt plus its request contract without leaking it."""

    if not isinstance(system_prompt, str):
        raise TypeError("system_prompt must be a string")
    for field_name, value in (
        ("task", task),
        ("operation", operation),
        ("contract_version", contract_version),
        ("retry_protocol_version", retry_protocol_version),
    ):
        if not isinstance(value, str) or not _SAFE_IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError(f"{field_name} must be a safe non-empty identifier")
    return canonical_payload_digest(
        {
            "schema_version": LLM_PROMPT_FINGERPRINT_SCHEMA_VERSION,
            "task": task,
            "operation": operation,
            "contract_version": contract_version,
            "retry_protocol_version": retry_protocol_version,
            # This exact value exists only in the temporary digest payload.
            "system_prompt": system_prompt,
        }
    )


def build_llm_config_fingerprint(settings: object) -> str:
    """Fingerprint only allowlisted effective settings, excluding all secrets.

    ``api_key``, ``configured``, and unrelated attributes are intentionally not
    read.  User information, query parameters, and fragments are removed from
    the endpoint before its identity is reduced to a nested digest.
    """

    provider = str(_setting_value(settings, "provider", "mock")).strip().lower()
    model = str(_setting_value(settings, "model", "mock-model")).strip()
    if not provider:
        provider = "mock"
    if not model:
        model = "mock-model"

    endpoint_identity = sanitize_llm_endpoint(
        str(_setting_value(settings, "base_url", ""))
    )
    is_deepseek = provider == "deepseek"
    payload = _LLMConfigFingerprintPayload(
        provider=provider,
        model=model,
        temperature=_setting_value(settings, "temperature", 0.7),
        max_tokens=_setting_value(settings, "max_tokens", 300),
        timeout_seconds=_setting_value(settings, "timeout_seconds", 30.0),
        max_retries=_setting_value(settings, "max_retries", 1),
        retry_delay_seconds=_setting_value(
            settings,
            "retry_delay_seconds",
            0.35,
        ),
        endpoint_identity_digest=canonical_payload_digest(
            {"endpoint_identity": endpoint_identity}
        ),
        deepseek_thinking_type="disabled" if is_deepseek else "provider_default",
        deepseek_response_format_type=(
            "json_object" if is_deepseek else "provider_default"
        ),
    )
    return canonical_payload_digest(payload)


def build_experiment_fingerprint(
    *,
    execution_mode: str,
    components: dict[str, tuple[object, bool]],
) -> dict[str, object]:
    """Build a digest-only manifest with full and active-only identities."""

    if (
        not isinstance(execution_mode, str)
        or not re.fullmatch(r"^[a-z][a-z0-9_.-]{0,63}$", execution_mode)
    ):
        raise ValueError("execution_mode must be a safe non-empty identifier")
    if not isinstance(components, dict) or not components:
        raise ValueError("experiment components must be a non-empty dictionary")

    component_models: list[ExperimentComponentFingerprintV1] = []
    for name in sorted(components):
        if not isinstance(name, str) or not _SAFE_COMPONENT_NAME_PATTERN.fullmatch(name):
            raise ValueError("experiment component names must be safe and unique")
        value_and_active = components[name]
        if (
            not isinstance(value_and_active, tuple)
            or len(value_and_active) != 2
            or not isinstance(value_and_active[1], bool)
        ):
            raise ValueError(
                "each experiment component must be a (payload, active) tuple"
            )
        component_models.append(
            ExperimentComponentFingerprintV1(
                name=name,
                digest=canonical_payload_digest(value_and_active[0]),
                active=value_and_active[1],
            )
        )

    component_payloads = [
        component.model_dump(mode="json") for component in component_models
    ]
    if not any(component["active"] for component in component_payloads):
        raise ValueError("at least one experiment component must be active")

    identity_header = {
        "schema_version": EXPERIMENT_FINGERPRINT_SCHEMA_VERSION,
        "fingerprint_algorithm": DIGEST_ALGORITHM,
        "execution_mode": execution_mode,
    }
    configuration_fingerprint = canonical_payload_digest(
        {
            **identity_header,
            "components": component_payloads,
        }
    )
    effective_fingerprint = canonical_payload_digest(
        {
            **identity_header,
            "components": [
                {"name": component["name"], "digest": component["digest"]}
                for component in component_payloads
                if component["active"]
            ],
        }
    )
    manifest = ExperimentFingerprintV1(
        **identity_header,
        configuration_fingerprint=configuration_fingerprint,
        effective_fingerprint=effective_fingerprint,
        components=component_models,
    )
    return manifest.model_dump(mode="json")


def _setting_value(settings: object, name: str, default: object) -> object:
    if isinstance(settings, Mapping):
        return settings.get(name, default)
    return getattr(settings, name, default)


def sanitize_llm_endpoint(base_url: str) -> str:
    """Return the non-secret endpoint identity safe for status responses.

    URL user information, query parameters, and fragments may contain
    credentials, so they are never returned.  The same normalization is used
    by the config fingerprint and the public status projection.
    """

    value = base_url.strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        # A relative endpoint cannot contain URL user information.  Query and
        # fragment data are still removed and equivalent trailing slashes are
        # normalized because LLMClient appends its request path after rstrip.
        return parsed.path.rstrip("/")

    hostname = (parsed.hostname or "").lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("LLM base_url contains an invalid port") from exc
    scheme = parsed.scheme.lower()
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = hostname
    if port is not None and not default_port:
        netloc = f"{hostname}:{port}"
    sanitized = SplitResult(
        scheme=scheme,
        netloc=netloc,
        path=parsed.path.rstrip("/"),
        query="",
        fragment="",
    )
    return urlunsplit(sanitized)


__all__ = [
    "DIGEST_ALGORITHM",
    "EXPERIMENT_FINGERPRINT_SCHEMA_VERSION",
    "ExperimentComponentFingerprintV1",
    "ExperimentFingerprintV1",
    "LLM_CONFIG_FINGERPRINT_SCHEMA_VERSION",
    "LLM_PROMPT_FINGERPRINT_SCHEMA_VERSION",
    "RULE_ONLY_EXECUTION_MODE",
    "build_experiment_fingerprint",
    "build_llm_config_fingerprint",
    "build_prompt_fingerprint",
    "canonical_payload_digest",
    "sanitize_llm_endpoint",
]
