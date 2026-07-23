"""Read-only comparison of sealed rule-simulation artifacts.

The comparator in this module deliberately does not run a simulation, import
the live rule engine, or request an LLM.  It only accepts integrity-checked
``agent_town_simulation_batch.v17`` JSON artifacts and pairs their fixed-role
games by ``(seed, player_role)``.
"""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from typing import Any, Optional

from .llm_fingerprinting import (
    DIGEST_ALGORITHM,
    RULE_ONLY_EXECUTION_MODE,
    canonical_payload_digest,
)


ARTIFACT_AB_SCHEMA_VERSION = "agent_town_artifact_ab.v1"
SUPPORTED_BATCH_SCHEMA_VERSION = "agent_town_simulation_batch.v17"
SUPPORTED_SIMULATION_SCHEMA_VERSION = "agent_town_simulation.v17"
EXPERIMENT_FINGERPRINT_SCHEMA_VERSION = "experiment_fingerprint.v1"
COMPARISON_MODE = "rule_only_artifacts_no_llm"

_FIXED_PLAYER_ROLES = frozenset(
    {"werewolf", "seer", "witch", "hunter", "guard", "villager"}
)
_FINGERPRINT_KEYS = frozenset(
    {
        "schema_version",
        "fingerprint_algorithm",
        "execution_mode",
        "configuration_fingerprint",
        "effective_fingerprint",
        "components",
    }
)
_FINGERPRINT_COMPONENT_KEYS = frozenset({"name", "digest", "active"})
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMPONENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_PLAYER_STRATEGY_POLICIES = {
    "beginner": "basic_legal.v1",
    "standard": "legal_public_baseline.v1",
    "expert": "evidence_guided.v1",
}
_PLAYER_STRATEGY_FIELDS = frozenset(
    {"schema_version", "tier", "policy_version", "knowledge_scope"}
)
_TRACE_CAPTURE_FIELDS = frozenset(
    {"beliefs", "stances", "vote_calibration", "event_logs"}
)
_TRACE_FIELDS = (
    "belief_trace",
    "stance_trace",
    "vote_calibration_trace",
    "event_log",
)


@dataclass(frozen=True)
class _QualitySpec:
    name: str
    numerator_field: Optional[str]
    denominator_field: str
    source_rate_field: str
    desired_direction: str


_QUALITY_SPECS = (
    _QualitySpec(
        "template_repeat_rate",
        "template_repeat_count",
        "speech_count",
        "template_repeat_rate",
        "lower",
    ),
    _QualitySpec(
        "cross_actor_near_duplicate_pair_rate",
        "cross_actor_near_duplicate_pair_count",
        "cross_actor_pair_count",
        "cross_actor_near_duplicate_pair_rate",
        "lower",
    ),
    _QualitySpec(
        "information_increment_rate",
        "new_information_atom_count",
        "information_atom_count",
        "information_increment_rate",
        "higher",
    ),
    _QualitySpec(
        "evidence_citation_rate",
        "evidence_citation_count",
        "speech_count",
        "evidence_citation_rate",
        "higher",
    ),
    _QualitySpec(
        "persona_differentiation_score",
        None,
        "cross_actor_pair_count",
        "persona_differentiation_score",
        "higher",
    ),
)


@dataclass(frozen=True)
class _GameArtifact:
    game: dict[str, Any]
    seed: int
    player_role: str
    player_won: bool
    winner: str
    total_days: int
    gameplay_digest: str
    result_digest: str
    compatibility: dict[str, Any]
    quality: dict[str, dict[str, Any]]

    @property
    def cohort_key(self) -> tuple[int, str]:
        return (self.seed, self.player_role)


@dataclass(frozen=True)
class _ArmArtifact:
    label: str
    report_count: int
    artifact_digests: tuple[str, ...]
    fingerprint: dict[str, Any]
    controls: dict[str, Any]
    games: dict[tuple[int, str], _GameArtifact]


def compare_simulation_artifacts(
    arm_a_reports: list[dict],
    arm_b_reports: list[dict],
    *,
    label_a: str = "baseline",
    label_b: str = "candidate",
) -> dict:
    """Compare two sealed, exactly paired collections of batch artifacts.

    The two arms must have different configuration and effective fingerprints.
    All other comparability controls are checked per paired game.  No sample is
    silently dropped and a zero-denominator quality metric remains ``None``.
    """

    normalized_label_a = _validate_label(label_a, "label_a")
    normalized_label_b = _validate_label(label_b, "label_b")
    if normalized_label_a == normalized_label_b:
        raise ValueError("arm labels must be different")

    arm_a = _validate_arm(
        arm_a_reports,
        label=normalized_label_a,
        arm_name="arm_a",
    )
    arm_b = _validate_arm(
        arm_b_reports,
        label=normalized_label_b,
        arm_name="arm_b",
    )
    if (
        arm_a.fingerprint["configuration_fingerprint"]
        == arm_b.fingerprint["configuration_fingerprint"]
    ):
        raise ValueError(
            "arm configuration_fingerprint values must be different"
        )
    if (
        arm_a.fingerprint["effective_fingerprint"]
        == arm_b.fingerprint["effective_fingerprint"]
    ):
        raise ValueError("arm effective_fingerprint values must be different")
    if (
        arm_a.fingerprint["fingerprint_algorithm"]
        != arm_b.fingerprint["fingerprint_algorithm"]
    ):
        raise ValueError("arm fingerprint algorithms are incompatible")

    cohort_keys_a = set(arm_a.games)
    cohort_keys_b = set(arm_b.games)
    if cohort_keys_a != cohort_keys_b:
        missing_from_b = sorted(cohort_keys_a - cohort_keys_b)
        missing_from_a = sorted(cohort_keys_b - cohort_keys_a)
        raise ValueError(
            "arm cohorts are not identical; "
            f"missing_from_arm_b={missing_from_b}; "
            f"missing_from_arm_a={missing_from_a}"
        )

    paired_games: list[tuple[_GameArtifact, _GameArtifact]] = []
    paired_cohorts: list[dict[str, Any]] = []
    for cohort_key in sorted(cohort_keys_a):
        game_a = arm_a.games[cohort_key]
        game_b = arm_b.games[cohort_key]
        _validate_pair_compatibility(game_a, game_b)
        paired_games.append((game_a, game_b))
        paired_cohorts.append(
            _build_paired_cohort(game_a, game_b, arm_a.label, arm_b.label)
        )

    paired_outcomes = _build_paired_outcomes(paired_games)
    quality_a = _aggregate_quality([pair[0] for pair in paired_games])
    quality_b = _aggregate_quality([pair[1] for pair in paired_games])
    quality_comparisons = _build_quality_comparisons(
        paired_games,
        quality_a,
        quality_b,
    )

    report: dict[str, Any] = {
        "schema_version": ARTIFACT_AB_SCHEMA_VERSION,
        "comparison_mode": COMPARISON_MODE,
        "llm_evaluated": False,
        "prompt_effect_evaluated": False,
        "arm_descriptors": {
            "arm_a": _arm_descriptor(arm_a),
            "arm_b": _arm_descriptor(arm_b),
        },
        "comparison_controls": copy.deepcopy(arm_a.controls),
        "cohort_count": len(paired_games),
        "paired_cohorts": paired_cohorts,
        "paired_outcomes": paired_outcomes,
        "speech_quality_by_arm": {
            "arm_a": {
                "label": arm_a.label,
                "game_count": len(paired_games),
                "metrics": quality_a,
            },
            "arm_b": {
                "label": arm_b.label,
                "game_count": len(paired_games),
                "metrics": quality_b,
            },
        },
        "speech_quality_comparisons": quality_comparisons,
        "disclaimer": (
            "This report compares sealed rule-only simulation artifacts. "
            "It never calls an LLM, and differing prompt fingerprints do not "
            "measure prompt or live-model effects. Quality scores are "
            "public-speech diagnostics, not hidden-role truth judgments."
        ),
    }
    report["report_digest"] = canonical_payload_digest(report)
    return report


def _validate_arm(
    reports: list[dict],
    *,
    label: str,
    arm_name: str,
) -> _ArmArtifact:
    if type(reports) is not list or not reports:
        raise ValueError(f"{arm_name} must contain at least one batch report")

    expected_fingerprint: Optional[dict[str, Any]] = None
    expected_controls: Optional[dict[str, Any]] = None
    artifact_digests: list[str] = []
    games: dict[tuple[int, str], _GameArtifact] = {}
    for report_index, raw_report in enumerate(reports, start=1):
        location = f"{arm_name} report {report_index}"
        report = _require_dict(raw_report, location)
        if report.get("schema_version") != SUPPORTED_BATCH_SCHEMA_VERSION:
            raise ValueError(
                f"{location} must use {SUPPORTED_BATCH_SCHEMA_VERSION}"
            )
        _verify_self_digest(report, "artifact_digest", location)
        artifact_digests.append(
            _require_digest(
                report.get("artifact_digest"),
                f"{location} artifact_digest",
            )
        )
        fingerprint = _validate_fingerprint(
            report.get("experiment_fingerprint"),
            f"{location} experiment_fingerprint",
        )
        if expected_fingerprint is None:
            expected_fingerprint = fingerprint
        elif fingerprint != expected_fingerprint:
            raise ValueError(
                f"{arm_name} reports do not share one experiment fingerprint"
            )

        report_player_role = _require_fixed_role(
            report.get("player_role"),
            f"{location} player_role",
        )
        report_strategy = _validate_strategy(
            report.get("player_strategy"),
            f"{location} player_strategy",
        )
        report_policy = _require_nonempty_string(
            report.get("player_policy_version"),
            f"{location} player_policy_version",
        )
        if report_policy != report_strategy["policy_version"]:
            raise ValueError(
                f"{location} player policy does not match its strategy"
            )
        report_ruleset = _require_nonempty_string(
            report.get("ruleset_version"),
            f"{location} ruleset_version",
        )
        event_logs_included = _require_bool(
            report.get("event_logs_included"),
            f"{location} event_logs_included",
        )
        root_trace_flags = _validate_root_trace_flags(
            report,
            event_logs_included,
            location,
        )
        root_schema_versions = _extract_schema_versions(report)
        if (
            root_schema_versions.get("simulation_schema_version")
            != SUPPORTED_SIMULATION_SCHEMA_VERSION
        ):
            raise ValueError(
                f"{location} simulation_schema_version must be "
                f"{SUPPORTED_SIMULATION_SCHEMA_VERSION}"
            )
        report_controls = {
            "player_strategy_tier": report_strategy["tier"],
            "player_policy_version": report_policy,
            "ruleset_version": report_ruleset,
            "schema_versions": root_schema_versions,
            "trace_flags": root_trace_flags,
        }
        if expected_controls is None:
            expected_controls = copy.deepcopy(report_controls)
        elif report_controls != expected_controls:
            raise ValueError(
                f"{arm_name} reports do not share strategy/rules/schema/trace controls"
            )

        report_games = report.get("games")
        if type(report_games) is not list or not report_games:
            raise ValueError(f"{location} games must be a non-empty list")
        completed = _require_nonnegative_int(
            report.get("games_completed"),
            f"{location} games_completed",
        )
        requested = _require_nonnegative_int(
            report.get("games_requested"),
            f"{location} games_requested",
        )
        start_seed = _require_nonnegative_int(
            report.get("start_seed"),
            f"{location} start_seed",
        )
        if completed != len(report_games) or requested != completed:
            raise ValueError(
                f"{location} requested/completed counts do not match games"
            )

        report_seed_values: list[int] = []
        for game_index, raw_game in enumerate(report_games, start=1):
            game_location = f"{location} game {game_index}"
            game = _validate_game(
                raw_game,
                location=game_location,
                report_fingerprint=fingerprint,
                report_player_role=report_player_role,
                report_strategy=report_strategy,
                report_policy=report_policy,
                report_ruleset=report_ruleset,
                root_schema_versions=root_schema_versions,
                root_trace_flags=root_trace_flags,
            )
            if game.cohort_key in games:
                raise ValueError(
                    f"{arm_name} contains duplicate cohort "
                    f"seed={game.seed}, role={game.player_role}"
                )
            games[game.cohort_key] = game
            report_seed_values.append(game.seed)
        if sorted(report_seed_values) != list(
            range(start_seed, start_seed + requested)
        ):
            raise ValueError(
                f"{location} games do not cover its exact sequential seed range"
            )

    if (
        expected_fingerprint is None
        or expected_controls is None
        or not games
    ):  # pragma: no cover - guarded
        raise ValueError(f"{arm_name} has no comparable games")
    return _ArmArtifact(
        label=label,
        report_count=len(reports),
        artifact_digests=tuple(artifact_digests),
        fingerprint=copy.deepcopy(expected_fingerprint),
        controls=copy.deepcopy(expected_controls),
        games=games,
    )


def _validate_game(
    raw_game: object,
    *,
    location: str,
    report_fingerprint: dict[str, Any],
    report_player_role: str,
    report_strategy: dict[str, str],
    report_policy: str,
    report_ruleset: str,
    root_schema_versions: dict[str, str],
    root_trace_flags: dict[str, Any],
) -> _GameArtifact:
    game = _require_dict(raw_game, location)
    if game.get("schema_version") != SUPPORTED_SIMULATION_SCHEMA_VERSION:
        raise ValueError(
            f"{location} must use {SUPPORTED_SIMULATION_SCHEMA_VERSION}"
        )
    _verify_self_digest(game, "result_digest", location)
    fingerprint = _validate_fingerprint(
        game.get("experiment_fingerprint"),
        f"{location} experiment_fingerprint",
    )
    if fingerprint != report_fingerprint:
        raise ValueError(
            f"{location} experiment fingerprint differs from its report"
        )

    seed = _require_nonnegative_int(game.get("seed"), f"{location} seed")
    metrics = _require_dict(game.get("metrics"), f"{location} metrics")
    metrics_schema = _require_nonempty_string(
        metrics.get("schema_version"),
        f"{location} metrics.schema_version",
    )
    performance = _require_dict(
        metrics.get("player_performance"),
        f"{location} metrics.player_performance",
    )
    performance_schema = _require_nonempty_string(
        performance.get("schema_version"),
        f"{location} metrics.player_performance.schema_version",
    )
    if performance.get("post_game_only") is not True:
        raise ValueError(f"{location} player performance must be post-game-only")
    player_role = _require_fixed_role(
        performance.get("player_role"),
        f"{location} metrics.player_performance.player_role",
    )
    if player_role != report_player_role:
        raise ValueError(
            f"{location} actual player role differs from fixed report role"
        )
    player_camp = _require_nonempty_string(
        performance.get("player_camp"),
        f"{location} metrics.player_performance.player_camp",
    )
    player_won = _require_bool(
        performance.get("player_won"),
        f"{location} metrics.player_performance.player_won",
    )
    winner = _require_nonempty_string(game.get("winner"), f"{location} winner")
    if winner not in {"good", "werewolf"}:
        raise ValueError(f"{location} winner must be good or werewolf")
    if player_camp not in {"good", "werewolf"}:
        raise ValueError(f"{location} player camp must be good or werewolf")
    expected_player_camp = (
        "werewolf" if player_role == "werewolf" else "good"
    )
    if player_camp != expected_player_camp:
        raise ValueError(f"{location} player role and camp are inconsistent")
    if player_won != (winner == player_camp):
        raise ValueError(f"{location} player outcome is inconsistent")
    performance_game_count = _require_nonnegative_int(
        performance.get("game_count"),
        f"{location} metrics.player_performance.game_count",
    )
    performance_win_count = _require_nonnegative_int(
        performance.get("player_win_count"),
        f"{location} metrics.player_performance.player_win_count",
    )
    if performance_game_count != 1 or performance_win_count != int(player_won):
        raise ValueError(f"{location} player-performance counts are inconsistent")

    game_strategy = _validate_strategy(
        game.get("player_strategy"),
        f"{location} player_strategy",
    )
    game_policy = _require_nonempty_string(
        game.get("player_policy_version"),
        f"{location} player_policy_version",
    )
    if (
        game_strategy != report_strategy
        or game_policy != report_policy
        or game_policy != game_strategy["policy_version"]
    ):
        raise ValueError(f"{location} player strategy differs from its report")
    ruleset = _require_nonempty_string(
        game.get("ruleset_version"),
        f"{location} ruleset_version",
    )
    if ruleset != report_ruleset:
        raise ValueError(f"{location} ruleset differs from its report")

    schema_versions = _extract_schema_versions(game)
    if schema_versions.get("schema_version") != SUPPORTED_SIMULATION_SCHEMA_VERSION:
        raise ValueError(f"{location} simulation schema is incompatible")
    if metrics_schema != schema_versions.get("metrics_schema_version"):
        raise ValueError(f"{location} metrics schema is inconsistent")
    if performance_schema != schema_versions.get(
        "player_performance_schema_version"
    ):
        raise ValueError(f"{location} player-performance schema is inconsistent")
    for root_key, game_key in (
        ("metrics_schema_version", "metrics_schema_version"),
        ("npc_speech_quality_schema_version", "npc_speech_quality_schema_version"),
        ("player_strategy_schema_version", "player_strategy_schema_version"),
        ("event_schema_version", "event_schema_version"),
        ("event_log_schema_version", "event_log_schema_version"),
        ("replay_schema_version", "replay_schema_version"),
    ):
        if root_key in root_schema_versions and (
            schema_versions.get(game_key) != root_schema_versions[root_key]
        ):
            raise ValueError(
                f"{location} {game_key} differs from its report"
            )

    quality_payload = _require_dict(
        game.get("npc_speech_quality"),
        f"{location} npc_speech_quality",
    )
    if (
        quality_payload.get("schema_version")
        != schema_versions.get("npc_speech_quality_schema_version")
    ):
        raise ValueError(f"{location} speech quality schema is inconsistent")
    if quality_payload.get("scope") != "npc_public_speeches_only":
        raise ValueError(f"{location} speech quality must be NPC-public-only")
    if quality_payload.get("truth_scope") != "public_only_no_role_truth":
        raise ValueError(f"{location} speech quality must exclude role truth")
    quality = _extract_quality_metrics(quality_payload, location)

    gameplay_projection = _require_nonempty_string(
        game.get("gameplay_digest_projection_version"),
        f"{location} gameplay_digest_projection_version",
    )
    initial_layout_digest = _require_digest(
        game.get("initial_layout_digest"),
        f"{location} initial_layout_digest",
    )
    gameplay_digest = _require_digest(
        game.get("gameplay_digest"),
        f"{location} gameplay_digest",
    )
    result_digest = _require_digest(
        game.get("result_digest"),
        f"{location} result_digest",
    )
    total_days = _require_nonnegative_int(
        game.get("total_days"),
        f"{location} total_days",
    )
    trace_presence = _extract_trace_presence(game, location)
    if trace_presence["event_log"] != root_trace_flags["event_logs_included"]:
        raise ValueError(f"{location} event-log presence differs from report flag")
    _validate_trace_capture_consistency(
        trace_presence,
        root_trace_flags.get("trace_capture"),
        location,
    )

    compatibility = {
        "player_strategy_tier": game_strategy["tier"],
        "player_policy_version": game_policy,
        "ruleset_version": ruleset,
        "report_schema_versions": copy.deepcopy(root_schema_versions),
        "game_schema_versions": copy.deepcopy(schema_versions),
        "metrics_schema_version": metrics_schema,
        "player_performance_schema_version": performance_schema,
        "quality_schema_version": quality_payload.get("schema_version"),
        "gameplay_digest_projection_version": gameplay_projection,
        "initial_layout_digest": initial_layout_digest,
        "trace_flags": copy.deepcopy(root_trace_flags),
        "trace_presence": trace_presence,
    }
    return _GameArtifact(
        game=game,
        seed=seed,
        player_role=player_role,
        player_won=player_won,
        winner=winner,
        total_days=total_days,
        gameplay_digest=gameplay_digest,
        result_digest=result_digest,
        compatibility=compatibility,
        quality=quality,
    )


def _validate_fingerprint(value: object, location: str) -> dict[str, Any]:
    fingerprint = _require_dict(value, location)
    if set(fingerprint) != _FINGERPRINT_KEYS:
        missing = sorted(_FINGERPRINT_KEYS - set(fingerprint))
        extra = sorted(set(fingerprint) - _FINGERPRINT_KEYS)
        raise ValueError(
            f"{location} fields are invalid; missing={missing}, extra={extra}"
        )
    if fingerprint["schema_version"] != EXPERIMENT_FINGERPRINT_SCHEMA_VERSION:
        raise ValueError(
            f"{location} must use {EXPERIMENT_FINGERPRINT_SCHEMA_VERSION}"
        )
    if fingerprint["fingerprint_algorithm"] != DIGEST_ALGORITHM:
        raise ValueError(f"{location} fingerprint algorithm is incompatible")
    if fingerprint["execution_mode"] != RULE_ONLY_EXECUTION_MODE:
        raise ValueError(
            f"{location} must use execution_mode={RULE_ONLY_EXECUTION_MODE}"
        )
    _require_digest(
        fingerprint["configuration_fingerprint"],
        f"{location} configuration_fingerprint",
    )
    _require_digest(
        fingerprint["effective_fingerprint"],
        f"{location} effective_fingerprint",
    )
    components = fingerprint["components"]
    if type(components) is not list or not components:
        raise ValueError(f"{location} components must be a non-empty list")
    component_names: list[str] = []
    for index, raw_component in enumerate(components, start=1):
        component_location = f"{location} component {index}"
        component = _require_dict(raw_component, component_location)
        if set(component) != _FINGERPRINT_COMPONENT_KEYS:
            raise ValueError(f"{component_location} fields are invalid")
        component_name = _require_nonempty_string(
            component["name"],
            f"{component_location} name",
        )
        if not _COMPONENT_NAME_PATTERN.fullmatch(component_name):
            raise ValueError(f"{component_location} name is not a safe identifier")
        component_names.append(component_name)
        _require_digest(component["digest"], f"{component_location} digest")
        _require_bool(component["active"], f"{component_location} active")
    if component_names != sorted(set(component_names)):
        raise ValueError(f"{location} components must be unique and sorted")
    if not any(component["active"] for component in components):
        raise ValueError(f"{location} must have at least one active component")

    identity_header = {
        "schema_version": fingerprint["schema_version"],
        "fingerprint_algorithm": fingerprint["fingerprint_algorithm"],
        "execution_mode": fingerprint["execution_mode"],
    }
    expected_configuration = canonical_payload_digest(
        {**identity_header, "components": components}
    )
    expected_effective = canonical_payload_digest(
        {
            **identity_header,
            "components": [
                {"name": component["name"], "digest": component["digest"]}
                for component in components
                if component["active"]
            ],
        }
    )
    if fingerprint["configuration_fingerprint"] != expected_configuration:
        raise ValueError(f"{location} configuration fingerprint is inconsistent")
    if fingerprint["effective_fingerprint"] != expected_effective:
        raise ValueError(f"{location} effective fingerprint is inconsistent")
    return copy.deepcopy(fingerprint)


def _validate_strategy(value: object, location: str) -> dict[str, str]:
    strategy = _require_dict(value, location)
    if set(strategy) != _PLAYER_STRATEGY_FIELDS:
        raise ValueError(f"{location} fields do not match player_strategy.v1")
    if strategy.get("schema_version") != "player_strategy.v1":
        raise ValueError(f"{location} schema_version must be player_strategy.v1")
    if strategy.get("knowledge_scope") != "player_strategy_context.v1":
        raise ValueError(
            f"{location} knowledge_scope must be player_strategy_context.v1"
        )
    tier = _require_nonempty_string(strategy.get("tier"), f"{location} tier")
    policy = _require_nonempty_string(
        strategy.get("policy_version"),
        f"{location} policy_version",
    )
    expected_policy = _PLAYER_STRATEGY_POLICIES.get(tier)
    if expected_policy is None or policy != expected_policy:
        raise ValueError(f"{location} tier and policy_version are inconsistent")
    return {"tier": tier, "policy_version": policy}


def _validate_root_trace_flags(
    report: dict[str, Any],
    event_logs_included: bool,
    location: str,
) -> dict[str, Any]:
    flags: dict[str, Any] = {"event_logs_included": event_logs_included}
    if "trace_capture" not in report:
        raise ValueError(f"{location} must include trace_capture")
    raw_capture = _require_dict(
        report["trace_capture"],
        f"{location} trace_capture",
    )
    if set(raw_capture) != _TRACE_CAPTURE_FIELDS:
        raise ValueError(f"{location} trace_capture fields are invalid")
    capture: dict[str, bool] = {}
    for key in sorted(raw_capture):
        capture[_require_nonempty_string(key, f"{location} trace_capture key")] = (
            _require_bool(
                raw_capture[key],
                f"{location} trace_capture.{key}",
            )
        )
    flags["trace_capture"] = capture
    if capture["event_logs"] != event_logs_included:
        raise ValueError(
            f"{location} trace_capture.event_logs differs from event_logs_included"
        )
    if capture["stances"] and not capture["beliefs"]:
        raise ValueError(
            f"{location} trace_capture.stances requires beliefs"
        )
    return flags


def _extract_trace_presence(
    game: dict[str, Any],
    location: str,
) -> dict[str, bool]:
    presence: dict[str, bool] = {}
    for field in _TRACE_FIELDS:
        if field not in game:
            raise ValueError(f"{location} is missing trace field {field}")
        value = game[field]
        if value is not None and type(value) is not dict:
            raise ValueError(f"{location} {field} must be an object or null")
        presence[field] = value is not None
    return presence


def _validate_trace_capture_consistency(
    presence: dict[str, bool],
    trace_capture: object,
    location: str,
) -> None:
    capture = _require_dict(trace_capture, f"{location} trace_capture")
    field_by_flag = {
        "beliefs": "belief_trace",
        "stances": "stance_trace",
        "vote_calibration": "vote_calibration_trace",
        "event_logs": "event_log",
    }
    for flag, field in field_by_flag.items():
        if capture[flag] != presence[field]:
            raise ValueError(
                f"{location} trace {field} differs from trace_capture.{flag}"
            )


def _extract_schema_versions(payload: dict[str, Any]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for key, value in payload.items():
        if key == "schema_version" or key.endswith("_version"):
            if type(value) is not str or not value:
                raise ValueError(f"{key} must be a non-empty string")
            versions[key] = value
    return {key: versions[key] for key in sorted(versions)}


def _extract_quality_metrics(
    quality: dict[str, Any],
    location: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for spec in _QUALITY_SPECS:
        denominator = _require_nonnegative_int(
            quality.get(spec.denominator_field),
            f"{location} npc_speech_quality.{spec.denominator_field}",
        )
        if spec.numerator_field is None:
            similarity_sum = _require_nonnegative_number(
                quality.get("cross_actor_template_similarity_sum"),
                f"{location} npc_speech_quality.cross_actor_template_similarity_sum",
            )
            if similarity_sum > denominator + 0.000002:
                raise ValueError(
                    f"{location} speech-quality similarity exceeds its pairs"
                )
            numerator: float | int = _round_metric(
                max(0.0, denominator - similarity_sum)
            )
        else:
            numerator = _require_nonnegative_int(
                quality.get(spec.numerator_field),
                f"{location} npc_speech_quality.{spec.numerator_field}",
            )
            if numerator > denominator:
                raise ValueError(
                    f"{location} speech-quality numerator exceeds denominator "
                    f"for {spec.name}"
                )
            similarity_sum = None
        rate = _rate(numerator, denominator)
        source_rate = quality.get(spec.source_rate_field)
        if source_rate is None:
            if rate is not None:
                raise ValueError(
                    f"{location} speech-quality source rate is unexpectedly null "
                    f"for {spec.name}"
                )
        else:
            source_rate_number = _require_nonnegative_number(
                source_rate,
                f"{location} npc_speech_quality.{spec.source_rate_field}",
            )
            if source_rate_number > 1.0 or rate is None or (
                abs(source_rate_number - rate) > 0.000002
            ):
                raise ValueError(
                    f"{location} speech-quality source rate is inconsistent "
                    f"for {spec.name}"
                )
        metric: dict[str, Any] = {
            "numerator": numerator,
            "denominator": denominator,
            "rate": rate,
        }
        if similarity_sum is not None:
            metric["source_similarity_sum"] = _round_metric(similarity_sum)
        result[spec.name] = metric
    return result


def _validate_pair_compatibility(
    game_a: _GameArtifact,
    game_b: _GameArtifact,
) -> None:
    if game_a.compatibility != game_b.compatibility:
        differing_fields = [
            key
            for key in sorted(
                set(game_a.compatibility).union(game_b.compatibility)
            )
            if game_a.compatibility.get(key) != game_b.compatibility.get(key)
        ]
        raise ValueError(
            "paired cohort is incompatible for "
            f"seed={game_a.seed}, role={game_a.player_role}; "
            f"differing_fields={differing_fields}"
        )


def _build_paired_cohort(
    game_a: _GameArtifact,
    game_b: _GameArtifact,
    label_a: str,
    label_b: str,
) -> dict[str, Any]:
    return {
        "seed": game_a.seed,
        "player_role": game_a.player_role,
        "player_strategy_tier": game_a.compatibility["player_strategy_tier"],
        "player_policy_version": game_a.compatibility["player_policy_version"],
        "initial_layout_digest": game_a.compatibility["initial_layout_digest"],
        "arm_a": _paired_game_summary(game_a, label_a),
        "arm_b": _paired_game_summary(game_b, label_b),
        "same_gameplay": game_a.gameplay_digest == game_b.gameplay_digest,
        "total_days_delta_b_minus_a": game_b.total_days - game_a.total_days,
    }


def _paired_game_summary(game: _GameArtifact, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "winner": game.winner,
        "player_won": game.player_won,
        "total_days": game.total_days,
        "gameplay_digest": game.gameplay_digest,
        "result_digest": game.result_digest,
    }


def _build_paired_outcomes(
    paired_games: list[tuple[_GameArtifact, _GameArtifact]],
) -> dict[str, Any]:
    a_only = 0
    b_only = 0
    same_win = 0
    same_loss = 0
    same_gameplay = 0
    winner_transitions: dict[str, int] = {}
    total_days_a = 0
    total_days_b = 0
    for game_a, game_b in paired_games:
        if game_a.player_won and not game_b.player_won:
            a_only += 1
        elif game_b.player_won and not game_a.player_won:
            b_only += 1
        elif game_a.player_won:
            same_win += 1
        else:
            same_loss += 1
        same_gameplay += int(game_a.gameplay_digest == game_b.gameplay_digest)
        transition = f"{game_a.winner}_to_{game_b.winner}"
        winner_transitions[transition] = winner_transitions.get(transition, 0) + 1
        total_days_a += game_a.total_days
        total_days_b += game_b.total_days

    cohort_count = len(paired_games)
    return {
        "cohort_count": cohort_count,
        "a_only_win_count": a_only,
        "b_only_win_count": b_only,
        "same_win_count": same_win,
        "same_loss_count": same_loss,
        "arm_a_player_win_count": a_only + same_win,
        "arm_b_player_win_count": b_only + same_win,
        "winner_transition_counts": {
            key: winner_transitions[key] for key in sorted(winner_transitions)
        },
        "same_gameplay_count": same_gameplay,
        "changed_gameplay_count": cohort_count - same_gameplay,
        "total_days": {
            "arm_a_total": total_days_a,
            "arm_b_total": total_days_b,
            "total_delta_b_minus_a": total_days_b - total_days_a,
            "arm_a_average": _average(total_days_a, cohort_count),
            "arm_b_average": _average(total_days_b, cohort_count),
            "average_delta_b_minus_a": _average(
                total_days_b - total_days_a,
                cohort_count,
            ),
        },
    }


def _aggregate_quality(
    games: list[_GameArtifact],
) -> dict[str, dict[str, Any]]:
    aggregate: dict[str, dict[str, Any]] = {}
    for spec in _QUALITY_SPECS:
        source_metrics = [game.quality[spec.name] for game in games]
        denominator = sum(int(metric["denominator"]) for metric in source_metrics)
        if spec.numerator_field is None:
            similarity_sum = math.fsum(
                float(metric["source_similarity_sum"])
                for metric in source_metrics
            )
            numerator: int | float = _round_metric(
                max(0.0, denominator - similarity_sum)
            )
        else:
            numerator = sum(int(metric["numerator"]) for metric in source_metrics)
            similarity_sum = None
        metric = {
            "numerator": numerator,
            "denominator": denominator,
            "rate": _rate(numerator, denominator),
        }
        if similarity_sum is not None:
            metric["source_similarity_sum"] = _round_metric(similarity_sum)
        aggregate[spec.name] = metric
    return aggregate


def _build_quality_comparisons(
    paired_games: list[tuple[_GameArtifact, _GameArtifact]],
    quality_a: dict[str, dict[str, Any]],
    quality_b: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    comparisons: dict[str, dict[str, Any]] = {}
    for spec in _QUALITY_SPECS:
        pair_counts = {
            "a_better_count": 0,
            "b_better_count": 0,
            "tied_count": 0,
            "unscored_count": 0,
        }
        for game_a, game_b in paired_games:
            rate_a = game_a.quality[spec.name]["rate"]
            rate_b = game_b.quality[spec.name]["rate"]
            if rate_a is None or rate_b is None:
                pair_counts["unscored_count"] += 1
                continue
            difference = float(rate_b) - float(rate_a)
            if abs(difference) <= 0.0000005:
                pair_counts["tied_count"] += 1
            elif (
                spec.desired_direction == "higher" and difference > 0
            ) or (
                spec.desired_direction == "lower" and difference < 0
            ):
                pair_counts["b_better_count"] += 1
            else:
                pair_counts["a_better_count"] += 1
        rate_a = quality_a[spec.name]["rate"]
        rate_b = quality_b[spec.name]["rate"]
        comparisons[spec.name] = {
            "desired_direction": spec.desired_direction,
            "arm_a": copy.deepcopy(quality_a[spec.name]),
            "arm_b": copy.deepcopy(quality_b[spec.name]),
            "rate_delta_b_minus_a": (
                _round_metric(float(rate_b) - float(rate_a))
                if rate_a is not None and rate_b is not None
                else None
            ),
            "paired_cohort_counts": pair_counts,
        }
    return comparisons


def _arm_descriptor(arm: _ArmArtifact) -> dict[str, Any]:
    roles = sorted({role for _seed, role in arm.games})
    return {
        "label": arm.label,
        "report_count": arm.report_count,
        "artifact_digests": list(arm.artifact_digests),
        "game_count": len(arm.games),
        "player_roles": roles,
        "configuration_fingerprint": arm.fingerprint[
            "configuration_fingerprint"
        ],
        "effective_fingerprint": arm.fingerprint["effective_fingerprint"],
        "experiment_fingerprint": copy.deepcopy(arm.fingerprint),
        "controls": copy.deepcopy(arm.controls),
    }


def _verify_self_digest(
    payload: dict[str, Any],
    field_name: str,
    location: str,
) -> None:
    expected = _require_digest(payload.get(field_name), f"{location} {field_name}")
    unsigned = dict(payload)
    unsigned.pop(field_name, None)
    actual = canonical_payload_digest(unsigned)
    if actual != expected:
        raise ValueError(
            f"{location} {field_name} verification failed; "
            f"expected={expected}, actual={actual}"
        )


def _validate_label(value: object, field_name: str) -> str:
    label = _require_nonempty_string(value, field_name).strip()
    if not label:
        raise ValueError(f"{field_name} must not be blank")
    return label


def _require_dict(value: object, location: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{location} must be an object")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{location} keys must be strings")
    return value


def _require_nonempty_string(value: object, location: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{location} must be a non-empty string")
    return value


def _require_fixed_role(value: object, location: str) -> str:
    role = _require_nonempty_string(value, location)
    if role == "random":
        raise ValueError(f"{location} must be fixed; random is not comparable")
    if role not in _FIXED_PLAYER_ROLES:
        raise ValueError(f"{location} is not a supported fixed player role")
    return role


def _require_bool(value: object, location: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{location} must be a boolean")
    return value


def _require_nonnegative_int(value: object, location: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{location} must be a non-negative integer")
    return value


def _require_nonnegative_number(value: object, location: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{location} must be a finite non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{location} must be a finite non-negative number")
    return number


def _require_digest(value: object, location: str) -> str:
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{location} must be a lowercase SHA-256 digest")
    return value


def _rate(numerator: int | float, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return _round_metric(float(numerator) / denominator)


def _average(total: int, count: int) -> Optional[float]:
    if count == 0:
        return None
    return _round_metric(total / count)


def _round_metric(value: float) -> float:
    return round(float(value), 6)


__all__ = [
    "ARTIFACT_AB_SCHEMA_VERSION",
    "COMPARISON_MODE",
    "EXPERIMENT_FINGERPRINT_SCHEMA_VERSION",
    "SUPPORTED_BATCH_SCHEMA_VERSION",
    "SUPPORTED_SIMULATION_SCHEMA_VERSION",
    "compare_simulation_artifacts",
]
