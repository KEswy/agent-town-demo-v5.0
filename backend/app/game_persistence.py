"""Atomic V4.3 game-save envelopes and filesystem storage.

This module is intentionally rule-agnostic.  The rule layer supplies a fully
validated state payload plus event/config digests; the store only writes and
reads strict, versioned envelopes.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .event_log import GAME_RULESET_VERSION


GAME_SAVE_SCHEMA_VERSION = "game_save.v1"
GAME_SAVE_RESPONSE_SCHEMA_VERSION = "game_save_response.v1"
GAME_RESTORE_SCHEMA_VERSION = "game_restore.v1"
GAME_RECOVERY_SCHEMA_VERSION = "game_recovery.v1"
RECOVERY_CONFIG_FINGERPRINT_VERSION = "recovery_config_fingerprint.v1"
SAFE_GAME_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
DIGEST_PATTERN = r"^[0-9a-f]{64}$"


class GameSaveEnvelopeV1(BaseModel):
    """Complete private snapshot sealed at one rule-event sequence."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["game_save.v1"] = GAME_SAVE_SCHEMA_VERSION
    ruleset_version: Literal["agent_town_rules.v4.2"] = GAME_RULESET_VERSION
    game_id: str = Field(min_length=1, max_length=160)
    saved_event_sequence: int = Field(ge=1)
    saved_event_digest: str = Field(pattern=DIGEST_PATTERN)
    state_digest: str = Field(pattern=DIGEST_PATTERN)
    snapshot_digest: str = Field(pattern=DIGEST_PATTERN)
    config_fingerprint: str = Field(pattern=DIGEST_PATTERN)
    saved_at: str
    state: dict[str, object]


class GameSaveResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["game_save_response.v1"] = (
        GAME_SAVE_RESPONSE_SCHEMA_VERSION
    )
    game_id: str
    saved_event_sequence: int = Field(ge=1)
    state_digest: str = Field(pattern=DIGEST_PATTERN)
    config_fingerprint: str = Field(pattern=DIGEST_PATTERN)
    saved_at: str
    message: str


class GameRestoreResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["game_restore.v1"] = GAME_RESTORE_SCHEMA_VERSION
    game_id: str
    restored: bool
    already_cached: bool
    day: int = Field(ge=1)
    phase: str
    saved_event_sequence: int = Field(ge=1)
    state_digest: str = Field(pattern=DIGEST_PATTERN)
    message: str


class GameRecoveryFailureV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game_id: str
    reason: str


class GameRecoveryReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["game_recovery.v1"] = GAME_RECOVERY_SCHEMA_VERSION
    scanned_count: int = Field(ge=0)
    restored_count: int = Field(ge=0)
    skipped_terminal_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    restored_game_ids: list[str] = Field(default_factory=list)
    failures: list[GameRecoveryFailureV1] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GameSaveStore:
    """One JSON file per game, replaced atomically in the same directory."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def save_path(self, game_id: str) -> Path:
        self._validate_game_id(game_id)
        return self.root_dir / f"{game_id}.json"

    def save(self, envelope: GameSaveEnvelopeV1) -> Path:
        target_path = self.save_path(envelope.game_id)
        self.root_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.root_dir, 0o700)
        except OSError:
            # The write below remains authoritative.  Some mounted filesystems
            # do not permit chmod even though atomic replacement is supported.
            pass
        temporary_path = self.root_dir / (
            f".{envelope.game_id}.{uuid4().hex}.tmp"
        )
        rendered = json.dumps(
            envelope.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        file_descriptor: int | None = None
        try:
            file_descriptor = os.open(
                temporary_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            os.fchmod(file_descriptor, 0o600)
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as save_file:
                file_descriptor = None
                save_file.write(rendered)
                save_file.flush()
                os.fsync(save_file.fileno())
            os.replace(temporary_path, target_path)
            # Once replace succeeds, the new snapshot is committed.  All
            # durability cleanup below is best effort and must not make the
            # caller roll memory back behind an already-advanced disk file.
            self._sync_directory()
        finally:
            if file_descriptor is not None:
                try:
                    os.close(file_descriptor)
                except OSError:
                    pass
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        return target_path

    def load(self, game_id: str) -> GameSaveEnvelopeV1:
        save_path = self.save_path(game_id)
        payload = json.loads(save_path.read_text(encoding="utf-8"))
        return GameSaveEnvelopeV1.model_validate(payload)

    def list_game_ids(self) -> list[str]:
        if not self.root_dir.is_dir():
            return []
        game_ids = []
        for save_path in sorted(self.root_dir.glob("*.json")):
            game_id = save_path.stem
            if SAFE_GAME_ID_PATTERN.fullmatch(game_id):
                game_ids.append(game_id)
        return game_ids

    def _sync_directory(self) -> None:
        try:
            directory_fd = os.open(self.root_dir, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        except OSError:
            # Some filesystems do not support fsync on directories.  The file
            # itself has already been flushed and atomically replaced.
            pass
        finally:
            try:
                os.close(directory_fd)
            except OSError:
                pass

    @staticmethod
    def _validate_game_id(game_id: str) -> None:
        if not SAFE_GAME_ID_PATTERN.fullmatch(game_id):
            raise ValueError("game_id contains unsafe save-path characters")
