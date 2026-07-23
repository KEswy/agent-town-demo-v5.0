from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import httpx
from dotenv import load_dotenv

from .llm_fingerprinting import (
    build_llm_config_fingerprint,
    build_prompt_fingerprint,
    sanitize_llm_endpoint,
)
from .llm_observability import (
    LLM_OBSERVABILITY_RECORDER,
    build_request_observation,
    classify_request_fallback,
    extract_token_usage,
    normalize_llm_task,
    normalize_safe_identifier,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


@dataclass
class LLMSettings:
    enabled: bool = False
    provider: str = "mock"
    base_url: str = ""
    api_key: str = ""
    model: str = "mock-model"
    temperature: float = 0.7
    max_tokens: int = 300
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_delay_seconds: float = 0.35

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            enabled=_env_bool("ENABLE_LLM", False),
            provider=os.getenv("LLM_PROVIDER", "mock").strip().lower() or "mock",
            base_url=os.getenv("LLM_BASE_URL", "").strip(),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            model=os.getenv("LLM_MODEL", "mock-model").strip() or "mock-model",
            temperature=_env_float("LLM_TEMPERATURE", 0.7, 0.0, 2.0),
            max_tokens=_env_int("LLM_MAX_TOKENS", 300, 32, 2000),
            timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 30.0, 1.0, 120.0),
            max_retries=_env_int("LLM_MAX_RETRIES", 1, 0, 4),
            retry_delay_seconds=_env_float(
                "LLM_RETRY_DELAY_SECONDS", 0.35, 0.0, 5.0
            ),
        )

    def is_configured(self) -> bool:
        if self.provider == "mock":
            return True
        return bool(self.base_url and self.api_key and self.model)


@dataclass
class LLMGeneration:
    text: str
    used_llm: bool
    provider: str
    model: str
    fallback_reason: str = ""
    raw_response_text: str = ""
    validation_attempts: list[dict[str, object]] = field(default_factory=list)
    validation_failure_id: str = ""
    decision_intent: str = ""
    decision_signal_ids: list[str] = field(default_factory=list)


@dataclass
class LLMJsonGeneration:
    data: dict[str, object]
    used_llm: bool
    provider: str
    model: str
    fallback_reason: str = ""
    raw_response_text: str = ""


class LLMClient:
    def __init__(
        self,
        settings: Optional[LLMSettings] = None,
        transport: Optional[httpx.BaseTransport] = None,
        event_sink: Optional[Callable[[dict[str, object]], None]] = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self._transport = transport
        self._event_sink = event_sink

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.settings.enabled,
            "provider": self.settings.provider,
            "model": self.settings.model,
            "configured": self.settings.is_configured(),
            # Keep the stable response field for the existing UI, but expose
            # only the endpoint identity.  URL userinfo, query values, and
            # fragments may contain credentials and must not cross the API.
            "base_url": sanitize_llm_endpoint(self.settings.base_url),
            "config_fingerprint": build_llm_config_fingerprint(self.settings),
        }

    def generate_json_text(
        self,
        system_prompt: str,
        context: dict[str, object],
        fallback_text: str,
        max_attempts: Optional[int] = None,
    ) -> LLMGeneration:
        json_result = self._generate_json_object(
            system_prompt,
            context,
            {"text": fallback_text},
            max_attempts,
            _validate_text_payload,
        )
        return LLMGeneration(
            text=str(json_result.data.get("text", fallback_text)).strip() or fallback_text,
            used_llm=json_result.used_llm,
            provider=json_result.provider,
            model=json_result.model,
            fallback_reason=json_result.fallback_reason,
            raw_response_text=json_result.raw_response_text,
        )

    def generate_json_object(
        self,
        system_prompt: str,
        context: dict[str, object],
        fallback_object: Optional[dict[str, object]] = None,
        max_attempts: Optional[int] = None,
    ) -> LLMJsonGeneration:
        """Generate one JSON object without imposing a game-specific schema."""
        return self._generate_json_object(
            system_prompt,
            context,
            fallback_object or {},
            max_attempts,
        )

    def _generate_json_object(
        self,
        system_prompt: str,
        context: dict[str, object],
        fallback_object: dict[str, object],
        max_attempts: Optional[int],
        validator: Optional[Callable[[dict[str, object]], None]] = None,
    ) -> LLMJsonGeneration:
        started_at = time.perf_counter()
        task = context.get("task")
        operation = "json_text" if validator is not None else "json_object"
        normalized_task = normalize_llm_task(task)
        prompt_fingerprint = _best_effort_prompt_fingerprint(
            system_prompt,
            task=normalized_task,
            operation=operation,
        )
        config_fingerprint = _best_effort_config_fingerprint(self.settings)
        if not self.settings.enabled:
            reason = "LLM is disabled"
            self._record_request_observation(
                task=task,
                operation=operation,
                outcome="fallback",
                attempt_count=0,
                started_at=started_at,
                fallback_reason=reason,
                prompt_fingerprint=prompt_fingerprint,
                config_fingerprint=config_fingerprint,
            )
            return self._json_fallback(fallback_object, reason)
        if self.settings.provider == "mock":
            reason = "mock provider uses deterministic rule text"
            self._record_request_observation(
                task=task,
                operation=operation,
                outcome="fallback",
                attempt_count=0,
                started_at=started_at,
                fallback_reason=reason,
                prompt_fingerprint=prompt_fingerprint,
                config_fingerprint=config_fingerprint,
            )
            return self._json_fallback(
                fallback_object,
                reason,
            )
        if not self.settings.is_configured():
            reason = "LLM provider is not fully configured"
            self._record_request_observation(
                task=task,
                operation=operation,
                outcome="fallback",
                attempt_count=0,
                started_at=started_at,
                fallback_reason=reason,
                prompt_fingerprint=prompt_fingerprint,
                config_fingerprint=config_fingerprint,
            )
            return self._json_fallback(
                fallback_object,
                reason,
            )

        attempts = (
            max(1, max_attempts)
            if max_attempts is not None
            else self.settings.max_retries + 1
        )
        last_error = "unknown LLM error"
        attempts_made = 0
        raw_response_text = ""
        observed_prompt_tokens: Optional[int] = None
        observed_completion_tokens: Optional[int] = None
        observed_total_tokens: Optional[int] = None
        usage_reported_attempt_count = 0
        usage_unreported_attempt_count = 0
        usage_complete_attempt_count = 0
        observed_billing_models: set[str] = set()
        provider_model_observed = False
        for attempt in range(attempts):
            attempts_made = attempt + 1
            usage_accounted = False
            try:
                response_data = self._request_chat_completion(system_prompt, context)
                prompt_tokens, completion_tokens, total_tokens = (
                    extract_token_usage(response_data)
                )
                usage_accounted = True
                if any(
                    value is not None
                    for value in (prompt_tokens, completion_tokens, total_tokens)
                ):
                    usage_reported_attempt_count += 1
                else:
                    usage_unreported_attempt_count += 1
                if all(
                    value is not None
                    for value in (prompt_tokens, completion_tokens, total_tokens)
                ):
                    usage_complete_attempt_count += 1
                response_model = response_data.get("model")
                normalized_response_model = normalize_safe_identifier(
                    response_model,
                    "",
                )
                if normalized_response_model:
                    observed_billing_models.add(normalized_response_model)
                    provider_model_observed = True
                else:
                    observed_billing_models.add(
                        normalize_safe_identifier(
                            self.settings.model,
                            "unknown",
                        )
                    )
                if prompt_tokens is not None:
                    observed_prompt_tokens = (
                        (observed_prompt_tokens or 0) + prompt_tokens
                    )
                if completion_tokens is not None:
                    observed_completion_tokens = (
                        (observed_completion_tokens or 0) + completion_tokens
                    )
                if total_tokens is not None:
                    observed_total_tokens = (
                        (observed_total_tokens or 0) + total_tokens
                    )
                content = _extract_response_content(response_data)
                raw_response_text = content
                parsed = _parse_json_object(content)
                if _contains_replacement_character(parsed):
                    raise ValueError("LLM JSON contained a replacement character")
                if validator is not None:
                    validator(parsed)
                self._record_request_observation(
                    task=task,
                    operation=operation,
                    outcome="success",
                    attempt_count=attempts_made,
                    started_at=started_at,
                    prompt_tokens=observed_prompt_tokens,
                    completion_tokens=observed_completion_tokens,
                    total_tokens=observed_total_tokens,
                    prompt_fingerprint=prompt_fingerprint,
                    config_fingerprint=config_fingerprint,
                    usage_reported_attempt_count=(
                        usage_reported_attempt_count
                    ),
                    usage_unreported_attempt_count=(
                        usage_unreported_attempt_count
                    ),
                    usage_complete_attempt_count=(
                        usage_complete_attempt_count
                    ),
                    **_billing_model_observation_fields(
                        self.settings.model,
                        observed_billing_models,
                        provider_model_observed,
                    ),
                )
                return LLMJsonGeneration(
                    data=parsed,
                    used_llm=True,
                    provider=self.settings.provider,
                    model=self.settings.model,
                    raw_response_text=content,
                )
            except (
                httpx.HTTPError,
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                if not usage_accounted:
                    usage_unreported_attempt_count += 1
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt + 1 >= attempts or not _is_retryable_error(exc):
                    break
                delay = self.settings.retry_delay_seconds * (2**attempt)
                if delay > 0:
                    time.sleep(delay)

        fallback_reason = f"{last_error} after {attempts_made} attempt(s)"
        self._record_request_observation(
            task=task,
            operation=operation,
            outcome="fallback",
            attempt_count=attempts_made,
            started_at=started_at,
            fallback_reason=fallback_reason,
            prompt_tokens=observed_prompt_tokens,
            completion_tokens=observed_completion_tokens,
            total_tokens=observed_total_tokens,
            prompt_fingerprint=prompt_fingerprint,
            config_fingerprint=config_fingerprint,
            usage_reported_attempt_count=usage_reported_attempt_count,
            usage_unreported_attempt_count=usage_unreported_attempt_count,
            usage_complete_attempt_count=usage_complete_attempt_count,
            **_billing_model_observation_fields(
                self.settings.model,
                observed_billing_models,
                provider_model_observed,
            ),
        )
        return self._json_fallback(
            fallback_object,
            fallback_reason,
            raw_response_text,
        )

    def _record_request_observation(
        self,
        *,
        task: object,
        operation: str,
        outcome: str,
        attempt_count: int,
        started_at: float,
        fallback_reason: str = "",
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        prompt_fingerprint: Optional[str] = None,
        config_fingerprint: Optional[str] = None,
        usage_reported_attempt_count: int = 0,
        usage_unreported_attempt_count: Optional[int] = None,
        usage_complete_attempt_count: Optional[int] = None,
        billing_model: Optional[str] = None,
        billing_model_source: str = "configured",
    ) -> None:
        if self._event_sink is None:
            return
        try:
            unreported_attempts = (
                attempt_count - usage_reported_attempt_count
                if usage_unreported_attempt_count is None
                else usage_unreported_attempt_count
            )
            token_usage_status = _token_usage_status(
                attempt_count,
                usage_reported_attempt_count,
                unreported_attempts,
                (
                    usage_reported_attempt_count
                    if usage_complete_attempt_count is None
                    else usage_complete_attempt_count
                ),
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )
            event = build_request_observation(
                task=task,
                operation=operation,
                provider=self.settings.provider,
                model=self.settings.model,
                outcome=outcome,
                attempt_count=attempt_count,
                retry_count=max(0, attempt_count - 1),
                latency_ms=(time.perf_counter() - started_at) * 1000,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                fallback_category=(
                    classify_request_fallback(fallback_reason)
                    if outcome == "fallback"
                    else ""
                ),
                prompt_fingerprint=prompt_fingerprint,
                config_fingerprint=config_fingerprint,
                token_usage_status=token_usage_status,
                usage_reported_attempt_count=usage_reported_attempt_count,
                usage_unreported_attempt_count=unreported_attempts,
                billing_model=(
                    normalize_safe_identifier(
                        self.settings.model,
                        "unknown",
                    )
                    if billing_model is None
                    and billing_model_source == "configured"
                    else billing_model
                ),
                billing_model_source=billing_model_source,
            )
            self._event_sink(event)
        except Exception:
            # Metrics are best-effort and must never change the LLM result.
            return

    def _request_chat_completion(
        self,
        system_prompt: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }
        if self.settings.provider == "deepseek":
            payload["thinking"] = {"type": "disabled"}
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(
            timeout=self.settings.timeout_seconds,
            transport=self._transport,
        ) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
        if not isinstance(response_data, dict):
            raise TypeError("LLM response must be a JSON object")
        return response_data

    def _json_fallback(
        self,
        data: dict[str, object],
        reason: str,
        raw_response_text: str = "",
    ) -> LLMJsonGeneration:
        return LLMJsonGeneration(
            data=dict(data),
            used_llm=False,
            provider=self.settings.provider,
            model=self.settings.model,
            fallback_reason=reason,
            raw_response_text=raw_response_text,
        )


def _token_usage_status(
    attempt_count: int,
    usage_reported_attempt_count: int,
    usage_unreported_attempt_count: int,
    usage_complete_attempt_count: int,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
) -> str:
    if attempt_count == 0:
        return "not_applicable"
    complete_split = all(
        value is not None
        for value in (prompt_tokens, completion_tokens, total_tokens)
    )
    if (
        complete_split
        and usage_complete_attempt_count == attempt_count
        and usage_reported_attempt_count == attempt_count
        and usage_unreported_attempt_count == 0
    ):
        return "complete"
    if usage_reported_attempt_count > 0:
        return "partial"
    return "missing"


def _best_effort_prompt_fingerprint(
    system_prompt: object,
    *,
    task: str,
    operation: str,
) -> Optional[str]:
    try:
        return build_prompt_fingerprint(
            system_prompt,  # type: ignore[arg-type]
            task=task,
            operation=operation,
        )
    except (TypeError, ValueError):
        return None


def _best_effort_config_fingerprint(settings: object) -> Optional[str]:
    try:
        return build_llm_config_fingerprint(settings)
    except (TypeError, ValueError):
        return None


def _billing_model_observation_fields(
    configured_model: str,
    observed_models: set[str],
    provider_model_observed: bool,
) -> dict[str, object]:
    safe_configured_model = normalize_safe_identifier(
        configured_model,
        "unknown",
    )
    if len(observed_models) > 1:
        return {
            "billing_model": None,
            "billing_model_source": "mixed",
        }
    if observed_models:
        return {
            "billing_model": next(iter(observed_models)),
            "billing_model_source": (
                "provider_response"
                if provider_model_observed
                else "configured"
            ),
        }
    return {
        "billing_model": safe_configured_model,
        "billing_model_source": "configured",
    }


def _extract_response_content(response_data: dict[str, object]) -> str:
    choices = response_data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise KeyError("LLM response did not contain choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise TypeError("LLM choice must be a JSON object")
    if first_choice.get("finish_reason") == "length":
        raise ValueError("LLM output reached the token limit")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise TypeError("LLM choice did not contain a message")
    content = message.get("content")
    if not isinstance(content, str):
        raise TypeError("LLM message content must be text")
    return content


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code in {408, 409, 425, 429} or status_code >= 500
    if isinstance(exc, httpx.HTTPError):
        return True
    return isinstance(exc, (json.JSONDecodeError, KeyError, TypeError, ValueError))


def _parse_json_object(content: str) -> dict[str, object]:
    normalized = content.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()
    parsed = json.loads(normalized)
    if not isinstance(parsed, dict):
        raise TypeError("LLM content must decode to a JSON object")
    return parsed


def _validate_text_payload(payload: dict[str, object]) -> None:
    generated_text = payload.get("text")
    if not isinstance(generated_text, str) or not generated_text.strip():
        raise ValueError("LLM JSON did not contain text")


def _contains_replacement_character(value: object) -> bool:
    if isinstance(value, str):
        return "\ufffd" in value
    if isinstance(value, dict):
        return any(
            _contains_replacement_character(key)
            or _contains_replacement_character(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_replacement_character(item) for item in value)
    return False


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


LLM_CLIENT = LLMClient(
    event_sink=LLM_OBSERVABILITY_RECORDER.record_event,
)
