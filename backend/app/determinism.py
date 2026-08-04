"""Process-independent deterministic random helpers (no global RNG)."""

from __future__ import annotations

import hashlib
import random
from typing import Any


def deterministic_seed_value(random_seed: int, salt: str) -> int:
    """Derive a process-independent integer from one private game seed."""

    payload = f"agent-town-v3|{int(random_seed)}|{salt}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def deterministic_seed_shuffle(
    values: list[Any],
    random_seed: int,
    salt: str,
) -> None:
    """Shuffle in place without consuming Python's process-global RNG."""

    random.Random(deterministic_seed_value(random_seed, salt)).shuffle(values)


def deterministic_game_choice(
    game_state: Any,
    values: list[Any],
    salt: str,
) -> Any:
    """Choose from a caller-canonicalized list using only game-owned state."""

    if not values:
        raise ValueError("deterministic game choice requires at least one value")
    derived_salt = f"day:{game_state.day}|phase:{game_state.phase}|{salt}"
    index = deterministic_seed_value(game_state.random_seed, derived_salt) % len(values)
    return values[index]


def deterministic_strategy_roll(
    game_state: Any,
    actor: Any,
    salt: str,
) -> float:
    """Stable pseudo-randomness keeps varied choices reproducible in tests."""

    seed = deterministic_seed_value(
        game_state.random_seed,
        (
            f"strategy|day:{game_state.day}|actor:{actor.id}|"
            f"speeches:{len(game_state.speeches)}|{salt}"
        ),
    )
    return (seed % 1_000_000) / 999_999
