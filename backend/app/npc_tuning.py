"""Strict, data-driven tuning for NPC strategy decisions.

The rule engine remains responsible for facts and legal actions.  Values from
this module only tune how an NPC ranks those legal choices.  A configuration
is resolved in the stable order ``global < faction < role < npc``.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


NPC_TUNING_SCHEMA_VERSION = "npc_tuning.v1"
NPCFaction = Literal["good", "werewolf"]
NPCRole = Literal["werewolf", "seer", "witch", "hunter", "guard", "villager", "idiot"]

VALID_FACTIONS = frozenset({"good", "werewolf"})
VALID_ROLES = frozenset(
    {"werewolf", "seer", "witch", "hunter", "guard", "villager", "idiot"}
)
ROLE_FACTIONS: dict[str, str] = {
    "werewolf": "werewolf",
    "seer": "good",
    "witch": "good",
    "hunter": "good",
    "guard": "good",
    "villager": "good",
    "idiot": "good",
}


class StrictTuningModel(BaseModel):
    """Shared strictness for every persisted and resolved tuning model."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class TuningValuesV1(StrictTuningModel):
    """A complete set of normalized strategy tuning values."""

    reasoning_skill: float = Field(ge=0.0, le=1.0)
    social_susceptibility: float = Field(ge=0.0, le=1.0)
    decision_variance: float = Field(ge=0.0, le=1.0)
    plan_consistency: float = Field(ge=0.0, le=1.0)
    deception_susceptibility: float = Field(ge=0.0, le=1.0)
    deception_strength: float = Field(ge=0.0, le=1.0)
    team_coordination: float = Field(ge=0.0, le=1.0)
    teammate_bus_pressure_threshold: int = Field(ge=0, le=100)
    teammate_black_check_chance: float = Field(ge=0.0, le=1.0)
    teammate_black_check_min_pressure: int = Field(ge=0, le=100)


class TuningOverrideV1(StrictTuningModel):
    """A partial override used at faction, role, and individual NPC levels."""

    reasoning_skill: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    social_susceptibility: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    decision_variance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    plan_consistency: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    deception_susceptibility: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    deception_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    team_coordination: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    teammate_bus_pressure_threshold: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
    )
    teammate_black_check_chance: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    teammate_black_check_min_pressure: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
    )


class FactionTuningV1(StrictTuningModel):
    """Required overrides for both supported factions."""

    good: TuningOverrideV1
    werewolf: TuningOverrideV1


class RoleTuningV1(StrictTuningModel):
    """Required overrides for the classic roles; idiot is optional."""

    werewolf: TuningOverrideV1
    seer: TuningOverrideV1
    witch: TuningOverrideV1
    hunter: TuningOverrideV1
    guard: TuningOverrideV1
    villager: TuningOverrideV1
    idiot: Optional[TuningOverrideV1] = None


class NPCTuningConfigV1(StrictTuningModel):
    """Top-level persisted contract for ``backend/config/npc_tuning.json``."""

    schema_version: Literal["npc_tuning.v1"]
    global_defaults: TuningValuesV1
    factions: FactionTuningV1
    roles: RoleTuningV1
    npcs: dict[str, TuningOverrideV1] = Field(default_factory=dict)

    @field_validator("npcs")
    @classmethod
    def validate_npc_keys(
        cls,
        value: dict[str, TuningOverrideV1],
    ) -> dict[str, TuningOverrideV1]:
        for npc_name in value:
            if not npc_name or npc_name != npc_name.strip():
                raise ValueError("NPC override names must be non-empty and trimmed")
        return value


class ResolvedNPCTuningV1(TuningValuesV1):
    """Complete tuning values after applying every applicable override."""

    npc_name: str = Field(min_length=1)
    faction: NPCFaction
    role: NPCRole


def _validated_whitelist(npc_name_whitelist: Collection[str]) -> frozenset[str]:
    if isinstance(npc_name_whitelist, str):
        raise TypeError("npc_name_whitelist must be a collection of NPC names")

    names: set[str] = set()
    for npc_name in npc_name_whitelist:
        if not isinstance(npc_name, str):
            raise TypeError("npc_name_whitelist may only contain strings")
        if not npc_name or npc_name != npc_name.strip():
            raise ValueError("NPC whitelist names must be non-empty and trimmed")
        names.add(npc_name)
    return frozenset(names)


def validate_npc_tuning_names(
    config: NPCTuningConfigV1,
    *,
    npc_name_whitelist: Collection[str],
) -> None:
    """Reject misspelled or stale per-NPC overrides."""

    allowed_names = _validated_whitelist(npc_name_whitelist)
    unknown_names = sorted(set(config.npcs) - allowed_names)
    if unknown_names:
        rendered = ", ".join(unknown_names)
        raise ValueError(f"unknown NPC tuning override(s): {rendered}")


def load_npc_tuning(
    path: str | Path,
    *,
    npc_name_whitelist: Collection[str],
) -> NPCTuningConfigV1:
    """Load and strictly validate a versioned NPC tuning JSON file.

    Pydantic validation errors and filesystem errors intentionally propagate so
    callers can fail fast at startup instead of silently using partial tuning.
    """

    config_path = Path(path)
    config = NPCTuningConfigV1.model_validate_json(
        config_path.read_text(encoding="utf-8")
    )
    validate_npc_tuning_names(
        config,
        npc_name_whitelist=npc_name_whitelist,
    )
    return config


def _apply_override(
    values: dict[str, object],
    override: TuningOverrideV1,
) -> None:
    values.update(override.model_dump(exclude_none=True))


def resolve_npc_tuning(
    config: NPCTuningConfigV1,
    *,
    faction: NPCFaction,
    role: NPCRole,
    npc_name: str,
    npc_name_whitelist: Collection[str],
) -> ResolvedNPCTuningV1:
    """Resolve one actor using ``global < faction < role < npc`` precedence."""

    allowed_names = _validated_whitelist(npc_name_whitelist)
    if npc_name not in allowed_names:
        raise ValueError(f"NPC is not in the tuning whitelist: {npc_name}")
    if faction not in VALID_FACTIONS:
        raise ValueError(f"unsupported NPC faction: {faction}")
    if role not in VALID_ROLES:
        raise ValueError(f"unsupported NPC role: {role}")

    expected_faction = ROLE_FACTIONS[role]
    if faction != expected_faction:
        raise ValueError(
            f"role {role} belongs to faction {expected_faction}, not {faction}"
        )

    validate_npc_tuning_names(
        config,
        npc_name_whitelist=allowed_names,
    )

    values: dict[str, object] = config.global_defaults.model_dump()
    _apply_override(values, getattr(config.factions, faction))
    role_override = getattr(config.roles, role, None)
    if role == "idiot" and role_override is None:
        role_override = config.roles.villager
    if role_override is not None:
        _apply_override(values, role_override)
    npc_override = config.npcs.get(npc_name)
    if npc_override is not None:
        _apply_override(values, npc_override)

    return ResolvedNPCTuningV1.model_validate(
        {
            **values,
            "npc_name": npc_name,
            "faction": faction,
            "role": role,
        }
    )
