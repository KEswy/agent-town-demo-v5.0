"""Legal-view player strategies for deterministic Agent Town simulations.

The live game still receives real player actions through the rule API.  This
module is only for offline simulations and deliberately separates two steps:

1. Build a sanitized context containing public facts and the player's lawful
   private knowledge.
2. Rank legal candidate ids without receiving the mutable ``WolfGameState``.

Post-game metrics may inspect role truth, but no strategy function in this
module can do so.
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from . import main as rules


PLAYER_STRATEGY_SCHEMA_VERSION = "player_strategy.v1"
PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION = "player_strategy_context.v1"
PLAYER_STRATEGY_TIERS = ("beginner", "standard", "expert")
DEFAULT_PLAYER_STRATEGY = "standard"
PLAYER_STRATEGY_POLICY_VERSIONS = {
    "beginner": "basic_legal.v1",
    "standard": "legal_public_baseline.v1",
    "expert": "evidence_guided.v1",
}
BENCHMARK_PLAYER_ROLES = (
    "werewolf",
    "seer",
    "witch",
    "hunter",
    "guard",
    "villager",
)

_PUBLIC_CHARACTER_KEYS = {
    "character_id",
    "alive",
    "is_player",
    "is_sheriff",
    "claimed_role",
    "public_suspicion_score",
    "public_persuasion_strength",
    "prior_exile_vote_weight",
    "public_good_check_count",
    "public_wolf_check_count",
}
_STANDARD_PUBLIC_PRESSURE_PURPOSES = {
    "hunter_shot",
    "sheriff_speech",
    "day_speech",
    "sheriff_nomination",
    "exile_vote",
    "badge_transfer",
    "player_sheriff_badge_flow_primary",
}
_PUBLIC_SPECIAL_ROLE_VALUE = {
    "seer": 5.0,
    "witch": 4.0,
    "hunter": 3.0,
    "guard": 3.0,
    "villager": 0.0,
    "werewolf": 0.0,
    None: 0.0,
}


def normalize_player_strategy(strategy: str) -> str:
    normalized = strategy.strip().lower()
    if normalized not in PLAYER_STRATEGY_TIERS:
        raise ValueError(
            "player_strategy must be one of "
            + ", ".join(PLAYER_STRATEGY_TIERS)
        )
    return normalized


def build_player_strategy_descriptor(strategy: str) -> dict[str, str]:
    normalized = normalize_player_strategy(strategy)
    return {
        "schema_version": PLAYER_STRATEGY_SCHEMA_VERSION,
        "tier": normalized,
        "policy_version": PLAYER_STRATEGY_POLICY_VERSIONS[normalized],
        "knowledge_scope": PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION,
    }


def build_player_strategy_context(
    game_state: rules.WolfGameState,
) -> dict[str, object]:
    """Project one game into the only information an offline player may use."""

    player = rules.get_character(
        game_state,
        game_state.player_character_id,
    )
    private_info = rules.build_player_private_info_dict(game_state)
    latest_claimed_roles: dict[int, Optional[str]] = {}
    public_good_checks: dict[int, int] = {}
    public_wolf_checks: dict[int, int] = {}
    for claim in game_state.public_claims:
        if claim.claim_type == "role":
            latest_claimed_roles[claim.character_id] = claim.claimed_role
        elif claim.claim_type == "seer_check" and claim.target_id is not None:
            target_id = int(claim.target_id)
            if claim.result == "good":
                public_good_checks[target_id] = (
                    public_good_checks.get(target_id, 0) + 1
                )
            elif claim.result == "werewolf":
                public_wolf_checks[target_id] = (
                    public_wolf_checks.get(target_id, 0) + 1
                )

    prior_exile_vote_weights: dict[int, float] = {}
    for vote in game_state.votes:
        if vote.day >= game_state.day:
            continue
        prior_exile_vote_weights[vote.target_id] = (
            prior_exile_vote_weights.get(vote.target_id, 0.0)
            + float(vote.weight)
        )

    public_characters = []
    for character in sorted(game_state.characters, key=lambda item: item.id):
        public_characters.append(
            {
                "character_id": character.id,
                "alive": character.alive,
                "is_player": character.is_player,
                "is_sheriff": game_state.sheriff_id == character.id,
                "claimed_role": latest_claimed_roles.get(character.id),
                "public_suspicion_score": rules.get_public_suspicion_score(
                    game_state,
                    character.id,
                ),
                "public_persuasion_strength": (
                    rules.get_public_persuasion_strength(
                        game_state,
                        character,
                    )
                ),
                "prior_exile_vote_weight": round(
                    prior_exile_vote_weights.get(character.id, 0.0),
                    4,
                ),
                "public_good_check_count": public_good_checks.get(
                    character.id,
                    0,
                ),
                "public_wolf_check_count": public_wolf_checks.get(
                    character.id,
                    0,
                ),
            }
        )

    wolf_teammate_ids = sorted(
        int(item["id"])
        for item in private_info.get("wolf_teammates", [])
        if isinstance(item, dict) and "id" in item
    )
    seer_checks = [
        {
            "day": int(day),
            "target_id": int(target_id),
            "result": str(result),
        }
        for day, target_id, result in rules.get_character_seer_checks(
            game_state,
            player.id,
        )
    ]
    witch_attacked_target = private_info.get("witch_attacked_target")
    attacked_target_id = (
        int(witch_attacked_target["id"])
        if isinstance(witch_attacked_target, dict)
        and "id" in witch_attacked_target
        else None
    )
    own_resources = rules.get_role_resources(game_state, player.id)
    election = game_state.sheriff_election
    context: dict[str, object] = {
        "schema_version": PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION,
        "day": game_state.day,
        "phase": game_state.phase,
        "self": {
            "character_id": player.id,
            "role": player.role,
            "camp": player.camp,
            "alive": player.alive,
            "is_sheriff": game_state.sheriff_id == player.id,
        },
        "public": {
            "characters": public_characters,
            "active_sheriff_candidate_ids": (
                rules.get_active_sheriff_candidates(game_state)
                if election is not None
                else []
            ),
            "sheriff_candidate_ids": (
                list(election.candidates) if election is not None else []
            ),
            "meeting_nomination_target_id": (
                game_state.meeting.nomination_target_id
                if game_state.meeting is not None
                else None
            ),
        },
        "lawful_private": {
            "wolf_teammate_ids": wolf_teammate_ids,
            "seer_checks": seer_checks,
            "witch_attacked_target_id": attacked_target_id,
            "witch_antidote_available": bool(
                private_info.get("witch_antidote_available", False)
            ),
            "witch_poison_available": bool(
                private_info.get("witch_poison_available", False)
            ),
            "guard_last_protected_target_id": (
                int(own_resources["last_protected_target_id"])
                if own_resources.get("last_protected_target_id") is not None
                else None
            ),
            "guard_last_protected_day": int(
                own_resources.get("last_protected_day", 0)
            ),
            "hunter_can_shoot": bool(
                private_info.get("hunter_can_shoot", False)
            ),
        },
    }
    validate_player_strategy_context(context)
    return context


def validate_player_strategy_context(context: dict[str, object]) -> None:
    if (
        context.get("schema_version")
        != PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION
    ):
        raise ValueError("player strategy context schema is incompatible")
    public = context.get("public")
    if not isinstance(public, dict):
        raise ValueError("player strategy context is missing public state")
    characters = public.get("characters")
    if not isinstance(characters, list):
        raise ValueError("player strategy context is missing public characters")
    for character in characters:
        if not isinstance(character, dict):
            raise ValueError("public character projection must be an object")
        if set(character) != _PUBLIC_CHARACTER_KEYS:
            raise ValueError(
                "public character projection contains undeclared fields"
            )
        if "role" in character or "camp" in character:
            raise ValueError(
                "public character projection must not expose hidden truth"
            )


def player_strategy_context_digest(context: dict[str, object]) -> str:
    validate_player_strategy_context(context)
    encoded = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_context_character(
    context: dict[str, object],
    character_id: int,
) -> dict[str, object]:
    public = context["public"]
    if not isinstance(public, dict):
        raise ValueError("player strategy context public state is invalid")
    characters = public["characters"]
    if not isinstance(characters, list):
        raise ValueError("player strategy context character list is invalid")
    for character in characters:
        if (
            isinstance(character, dict)
            and int(character["character_id"]) == character_id
        ):
            return character
    raise ValueError(f"unknown context character id: {character_id}")


def lawful_target_constraints(
    context: dict[str, object],
) -> tuple[set[int], set[int]]:
    """Return (excluded ids, priority ids) from lawful role knowledge only."""

    self_view = context["self"]
    lawful_private = context["lawful_private"]
    if not isinstance(self_view, dict) or not isinstance(lawful_private, dict):
        raise ValueError("player strategy context private state is invalid")
    role = str(self_view["role"])
    excluded_ids: set[int] = set()
    priority_ids: set[int] = set()
    if role == "werewolf":
        excluded_ids.update(
            int(item)
            for item in lawful_private["wolf_teammate_ids"]
        )
    elif role == "seer":
        for check in lawful_private["seer_checks"]:
            if not isinstance(check, dict):
                continue
            target_id = int(check["target_id"])
            if check["result"] == "werewolf":
                priority_ids.add(target_id)
            elif check["result"] == "good":
                excluded_ids.add(target_id)
    return excluded_ids, priority_ids


def best_candidate_ids(
    context: dict[str, object],
    candidate_ids: list[int],
    *,
    strategy: str,
    purpose: str,
) -> list[int]:
    """Return every top-scoring legal id; the caller performs seeded tie-breaks."""

    normalized = normalize_player_strategy(strategy)
    unique_ids = sorted(set(int(item) for item in candidate_ids))
    if not unique_ids:
        return []
    scores = {
        character_id: _candidate_score(
            context,
            character_id,
            normalized,
            purpose,
        )
        for character_id in unique_ids
    }
    highest = max(scores.values())
    return [
        character_id
        for character_id in unique_ids
        if scores[character_id] == highest
    ]


def should_run_for_sheriff(
    context: dict[str, object],
    strategy: str,
) -> bool:
    normalized = normalize_player_strategy(strategy)
    self_view = context["self"]
    if not isinstance(self_view, dict):
        raise ValueError("player strategy context self state is invalid")
    if normalized == "beginner":
        return False
    return str(self_view["role"]) == "seer"


def choose_witch_action(
    context: dict[str, object],
    *,
    strategy: str,
    poison_candidate_ids: list[int],
) -> tuple[str, Optional[int], list[int]]:
    """Return (action_type, fixed_target, ranked_candidates).

    ``fixed_target`` is used for the private attacked target.  Poison targets
    remain a candidate list so the simulation driver can use its seeded
    tie-breaker without exposing the game state here.
    """

    normalized = normalize_player_strategy(strategy)
    self_view = context["self"]
    lawful_private = context["lawful_private"]
    if not isinstance(self_view, dict) or not isinstance(lawful_private, dict):
        raise ValueError("player strategy context private state is invalid")
    attacked_target_id = lawful_private["witch_attacked_target_id"]
    can_self_save = (
        attacked_target_id != self_view["character_id"]
        or int(context["day"]) == 1
    )
    if normalized == "beginner":
        return "none", None, []
    if normalized == "standard":
        if (
            attacked_target_id is not None
            and lawful_private["witch_antidote_available"]
            and can_self_save
        ):
            return "witch_save", int(attacked_target_id), []
        return "none", None, []

    if (
        attacked_target_id is not None
        and lawful_private["witch_antidote_available"]
        and can_self_save
    ):
        attacked = get_context_character(context, int(attacked_target_id))
        if (
            int(attacked_target_id) == int(self_view["character_id"])
            or bool(attacked["is_sheriff"])
            or float(attacked["public_suspicion_score"]) < 30.0
        ):
            return "witch_save", int(attacked_target_id), []
    if lawful_private["witch_poison_available"]:
        ranked = best_candidate_ids(
            context,
            poison_candidate_ids,
            strategy=normalized,
            purpose="night_witch_poison",
        )
        if ranked:
            highest_score = _candidate_score(
                context,
                ranked[0],
                normalized,
                "night_witch_poison",
            )
            if highest_score >= 35.0:
                return "witch_poison", None, ranked
    return "none", None, []


def _candidate_score(
    context: dict[str, object],
    character_id: int,
    strategy: str,
    purpose: str,
) -> float:
    character = get_context_character(context, character_id)
    suspicion = float(character["public_suspicion_score"])
    persuasion = float(character["public_persuasion_strength"])
    prior_votes = float(character["prior_exile_vote_weight"])
    public_good_checks = int(character["public_good_check_count"])
    public_wolf_checks = int(character["public_wolf_check_count"])
    claimed_role = character["claimed_role"]

    if strategy == "beginner":
        return 0.0
    if strategy == "standard":
        if purpose == "sheriff_vote":
            return persuasion
        if purpose in _STANDARD_PUBLIC_PRESSURE_PURPOSES:
            return suspicion
        return 0.0

    special_role_value = _PUBLIC_SPECIAL_ROLE_VALUE.get(claimed_role, 0.0)
    if purpose == "badge_transfer":
        return round(
            persuasion * 35.0
            - suspicion * 1.5
            + public_good_checks * 30.0
            - public_wolf_checks * 40.0,
            6,
        )
    if purpose == "sheriff_vote":
        return round(
            persuasion * 100.0
            - suspicion * 0.4
            + (18.0 if claimed_role == "seer" else 0.0),
            6,
        )
    if purpose == "night_werewolf_kill":
        return round(
            persuasion * 70.0
            + special_role_value * 10.0
            - suspicion * 0.15,
            6,
        )
    if purpose == "night_guard_protect":
        return round(
            persuasion * 45.0
            + (35.0 if character["is_sheriff"] else 0.0)
            + (25.0 if claimed_role == "seer" else 0.0)
            + public_good_checks * 15.0
            - suspicion * 0.7,
            6,
        )
    if purpose == "night_seer_check":
        return round(
            suspicion * 1.8
            + prior_votes * 8.0
            + special_role_value * 3.0
            + public_wolf_checks * 10.0
            - public_good_checks * 14.0,
            6,
        )
    return round(
        suspicion * 1.8
        + prior_votes * 8.0
        + public_wolf_checks * 16.0
        - public_good_checks * 14.0,
        6,
    )


__all__ = [
    "BENCHMARK_PLAYER_ROLES",
    "DEFAULT_PLAYER_STRATEGY",
    "PLAYER_STRATEGY_CONTEXT_SCHEMA_VERSION",
    "PLAYER_STRATEGY_POLICY_VERSIONS",
    "PLAYER_STRATEGY_SCHEMA_VERSION",
    "PLAYER_STRATEGY_TIERS",
    "best_candidate_ids",
    "build_player_strategy_context",
    "build_player_strategy_descriptor",
    "choose_witch_action",
    "get_context_character",
    "lawful_target_constraints",
    "normalize_player_strategy",
    "player_strategy_context_digest",
    "should_run_for_sheriff",
    "validate_player_strategy_context",
]
