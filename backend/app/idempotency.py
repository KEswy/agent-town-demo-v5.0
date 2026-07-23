"""V4.3-B external idempotency contracts for rule commands."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .event_log import canonical_payload_digest


GAME_COMMAND_IDEMPOTENCY_VERSION = "game_command_idempotency.v1"
GAME_COMMAND_RESULT_SCHEMA_VERSION = "game_command_result.v1"
IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,159}$"
DIGEST_PATTERN = r"^[0-9a-f]{64}$"


class IdempotentGameCommandRequest(BaseModel):
    """Backward-compatible request base with an optional external key."""

    idempotency_key: Optional[str] = Field(
        default=None,
        pattern=IDEMPOTENCY_KEY_PATTERN,
    )


class GameCommandResultV1(BaseModel):
    """Durable response for one successfully committed external command."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["game_command_result.v1"] = (
        GAME_COMMAND_RESULT_SCHEMA_VERSION
    )
    idempotency_contract_version: Literal["game_command_idempotency.v1"] = (
        GAME_COMMAND_IDEMPOTENCY_VERSION
    )
    idempotency_key: str = Field(pattern=IDEMPOTENCY_KEY_PATTERN)
    game_id: str = Field(min_length=1, max_length=160)
    endpoint: str = Field(pattern=r"^[a-z][a-z0-9_]{1,127}$")
    request_digest: str = Field(pattern=DIGEST_PATTERN)
    event_sequence: int = Field(ge=1)
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,127}$")
    event_digest: str = Field(pattern=DIGEST_PATTERN)
    response_model: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{1,127}$")
    response_digest: str = Field(pattern=DIGEST_PATTERN)
    response_payload: dict[str, object]


def build_idempotency_request_digest(request: BaseModel) -> str:
    """Hash the command payload without its transport-level idempotency key."""

    return canonical_payload_digest(
        request.model_dump(
            mode="json",
            exclude={"idempotency_key"},
        )
    )
