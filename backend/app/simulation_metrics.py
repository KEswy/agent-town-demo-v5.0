"""Post-game-only metrics for deterministic Agent Town simulations.

This module is imported by the offline simulation driver, never by a live
decision path. True roles are intentionally used only after ``GAME_OVER`` to
score decisions that were made from legal in-game perspectives.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable, Optional

from . import main as rules


METRICS_SCHEMA_VERSION = "agent_town_metrics.v1"


def summarize_ballot_distribution(target_ids: Iterable[int]) -> dict[str, object]:
    """Return deterministic Shannon-entropy statistics for unweighted choices.

    Normalization uses ``log2(ballot_count)``: zero means unanimous and one
    means every ballot selected a different target. A missing sample is
    represented by ``None`` instead of being mislabeled as zero dispersion.
    """

    counts = Counter(int(target_id) for target_id in target_ids)
    ballot_count = sum(counts.values())
    if ballot_count == 0:
        return {
            "ballot_count": 0,
            "target_count": 0,
            "target_counts": {},
            "entropy_bits": None,
            "normalized_entropy": None,
            "effective_target_count": None,
        }

    probabilities = [count / ballot_count for count in counts.values()]
    entropy_bits = -sum(
        probability * math.log2(probability)
        for probability in probabilities
    )
    normalized_entropy = (
        entropy_bits / math.log2(ballot_count)
        if ballot_count > 1
        else 0.0
    )
    return {
        "ballot_count": ballot_count,
        "target_count": len(counts),
        "target_counts": {
            str(target_id): counts[target_id]
            for target_id in sorted(counts)
        },
        "entropy_bits": _round_metric(entropy_bits),
        "normalized_entropy": _round_metric(normalized_entropy),
        "effective_target_count": _round_metric(2 ** entropy_bits),
    }


def build_game_metrics(game_state: rules.WolfGameState) -> dict[str, object]:
    """Build metrics from one terminal state; reject in-progress information."""

    if game_state.phase != "GAME_OVER" or game_state.winner not in {
        "good",
        "werewolf",
    }:
        raise ValueError("simulation metrics may only inspect a completed game")

    characters = {character.id: character for character in game_state.characters}
    sheriff_round_ballots: dict[int, list[int]] = defaultdict(list)
    for event in game_state.sheriff_events:
        if (
            event.event_type != "sheriff_vote"
            or event.actor_id is None
            or event.target_id is None
        ):
            continue
        sheriff_round_ballots[_parse_sheriff_round(event.context)].append(
            event.target_id
        )

    sheriff_rounds = [
        {
            "round": round_index,
            **summarize_ballot_distribution(sheriff_round_ballots[round_index]),
        }
        for round_index in sorted(sheriff_round_ballots)
    ]

    exile_votes_by_day: dict[int, list[rules.VoteState]] = defaultdict(list)
    for vote in game_state.votes:
        exile_votes_by_day[vote.day].append(vote)

    exile_days = []
    for day in sorted(exile_votes_by_day):
        day_votes = exile_votes_by_day[day]
        exile_days.append(
            {
                "day": day,
                **summarize_ballot_distribution(
                    vote.target_id for vote in day_votes
                ),
                "good_voter_alignment": _with_good_vote_labels(
                    _summarize_target_alignment(
                        day_votes,
                        characters,
                        voter_camp="good",
                    )
                ),
            }
        )

    good_exile_alignment = _with_good_vote_labels(
        _summarize_target_alignment(
            game_state.votes,
            characters,
            voter_camp="good",
        )
    )
    by_voter_role = {
        role: _summarize_target_alignment(
            [
                vote
                for vote in game_state.votes
                if characters[vote.voter_id].role == role
            ],
            characters,
        )
        for role in sorted({character.role for character in game_state.characters})
    }

    metrics = {
        "schema_version": METRICS_SCHEMA_VERSION,
        "post_game_only": True,
        "sheriff_vote": {
            **_summarize_distribution_samples(sheriff_rounds),
            "rounds": sheriff_rounds,
        },
        "exile_vote": {
            **_summarize_distribution_samples(exile_days),
            "days": exile_days,
        },
        "good_exile_vote": good_exile_alignment,
        "by_voter_role": by_voter_role,
        "fake_seer_acceptance": _build_fake_seer_metrics(
            game_state,
            characters,
        ),
    }
    _validate_game_metric_conservation(metrics)
    return metrics


def aggregate_batch_metrics(
    game_results: list[dict[str, object]],
) -> dict[str, object]:
    """Aggregate exact count numerators so rates are sample-weighted."""

    if not game_results:
        raise ValueError("batch metrics require at least one completed game")

    winner_counts = Counter(str(game["winner"]) for game in game_results)
    total_days = sum(int(game["total_days"]) for game in game_results)
    sheriff_samples: list[dict[str, object]] = []
    exile_samples: list[dict[str, object]] = []
    good_alignment_totals = _new_alignment_counter()
    by_voter_role_totals: dict[str, dict[str, int]] = defaultdict(
        _new_alignment_counter
    )
    by_day_totals: dict[int, dict[str, object]] = {}
    by_player_role: dict[str, dict[str, object]] = {}
    fake_totals = {
        "designated_games": 0,
        "publicly_claimed_games": 0,
        "candidate_games": 0,
        "elected_games": 0,
        "eligible_good_sheriff_ballots": 0,
        "supporting_good_sheriff_ballots": 0,
        "black_check_claims": 0,
        "black_check_games": 0,
        "eligible_good_exile_ballots": 0,
        "following_good_exile_ballots": 0,
    }

    for game in game_results:
        metrics = _require_game_metrics(game)
        sheriff_samples.extend(metrics["sheriff_vote"]["rounds"])
        exile_samples.extend(metrics["exile_vote"]["days"])
        _add_alignment_counts(good_alignment_totals, metrics["good_exile_vote"])

        for role, alignment in metrics["by_voter_role"].items():
            _add_alignment_counts(by_voter_role_totals[role], alignment)

        for day_metrics in metrics["exile_vote"]["days"]:
            day = int(day_metrics["day"])
            day_total = by_day_totals.setdefault(
                day,
                {
                    "games_with_vote": 0,
                    "ballot_count": 0,
                    "entropy_bits": [],
                    "normalized_entropy": [],
                    "good_alignment": _new_alignment_counter(),
                },
            )
            day_total["games_with_vote"] += 1
            day_total["ballot_count"] += int(day_metrics["ballot_count"])
            _append_if_number(day_total["entropy_bits"], day_metrics["entropy_bits"])
            _append_if_number(
                day_total["normalized_entropy"],
                day_metrics["normalized_entropy"],
            )
            _add_alignment_counts(
                day_total["good_alignment"],
                day_metrics["good_voter_alignment"],
            )

        _add_fake_seer_counts(fake_totals, metrics["fake_seer_acceptance"])
        _add_player_role_game(by_player_role, game)

    aggregate = {
        "schema_version": METRICS_SCHEMA_VERSION,
        "game_count": len(game_results),
        "camp_balance": {
            "winner_counts": {
                "good": winner_counts.get("good", 0),
                "werewolf": winner_counts.get("werewolf", 0),
            },
            "good_win_rate": _rate(winner_counts.get("good", 0), len(game_results)),
            "werewolf_win_rate": _rate(
                winner_counts.get("werewolf", 0),
                len(game_results),
            ),
        },
        "average_total_days": _round_metric(total_days / len(game_results)),
        "sheriff_vote": _summarize_distribution_samples(sheriff_samples),
        "exile_vote": _summarize_distribution_samples(exile_samples),
        "good_exile_vote": _with_good_vote_labels(
            _finalize_alignment_counts(good_alignment_totals)
        ),
        "fake_seer_acceptance": _finalize_fake_seer_counts(fake_totals),
        "by_player_role": _finalize_player_role_groups(by_player_role),
        "by_voter_role": {
            role: _finalize_alignment_counts(by_voter_role_totals[role])
            for role in sorted(by_voter_role_totals)
        },
        "by_day": {
            str(day): {
                "games_with_vote": int(by_day_totals[day]["games_with_vote"]),
                "ballot_count": int(by_day_totals[day]["ballot_count"]),
                "mean_entropy_bits": _mean_or_none(
                    by_day_totals[day]["entropy_bits"]
                ),
                "mean_normalized_entropy": _mean_or_none(
                    by_day_totals[day]["normalized_entropy"]
                ),
                "good_voter_alignment": _with_good_vote_labels(
                    _finalize_alignment_counts(
                        by_day_totals[day]["good_alignment"]
                    )
                ),
            }
            for day in sorted(by_day_totals)
        },
    }
    _validate_batch_metric_conservation(aggregate)
    return aggregate


def _build_fake_seer_metrics(
    game_state: rules.WolfGameState,
    characters: dict[int, rules.CharacterState],
) -> dict[str, object]:
    fake_seer_id = game_state.wolf_fake_seer_id
    if fake_seer_id is None:
        return {
            "designated": False,
            "character_id": None,
            "publicly_claimed_seer": False,
            "was_candidate": False,
            "was_elected": False,
            "eligible_good_sheriff_ballots": 0,
            "supporting_good_sheriff_ballots": 0,
            "good_sheriff_support_rate": None,
            "black_check_claim_count": 0,
            "black_check_target_ids": [],
            "eligible_good_exile_ballots": 0,
            "following_good_exile_ballots": 0,
            "good_black_check_follow_rate": None,
        }

    election = game_state.sheriff_election
    publicly_claimed = any(
        claim.character_id == fake_seer_id
        and claim.claim_type == "role"
        and claim.claimed_role == "seer"
        for claim in game_state.public_claims
    )
    eligible_good_sheriff_ballots = 0
    supporting_good_sheriff_ballots = 0
    for event in game_state.sheriff_events:
        if (
            event.event_type != "sheriff_vote"
            or event.actor_id is None
            or event.target_id is None
        ):
            continue
        round_index = _parse_sheriff_round(event.context)
        if not _fake_seer_eligible_in_round(election, fake_seer_id, round_index):
            continue
        if characters[event.actor_id].camp != "good":
            continue
        eligible_good_sheriff_ballots += 1
        if event.target_id == fake_seer_id:
            supporting_good_sheriff_ballots += 1

    black_checks = [
        claim
        for claim in game_state.public_claims
        if claim.character_id == fake_seer_id
        and claim.claim_type == "seer_check"
        and claim.result == "werewolf"
        and claim.target_id is not None
    ]
    eligible_good_exile_ballots = 0
    following_good_exile_ballots = 0
    for vote in game_state.votes:
        if characters[vote.voter_id].camp != "good":
            continue
        active_black_targets = {
            int(claim.target_id)
            for claim in black_checks
            if claim.day <= vote.day and claim.target_id is not None
        }
        if not active_black_targets:
            continue
        eligible_good_exile_ballots += 1
        if vote.target_id in active_black_targets:
            following_good_exile_ballots += 1

    was_elected = any(
        event.event_type == "elected" and event.actor_id == fake_seer_id
        for event in game_state.sheriff_events
    )
    return {
        "designated": True,
        "character_id": fake_seer_id,
        "publicly_claimed_seer": publicly_claimed,
        "was_candidate": bool(
            election is not None and fake_seer_id in election.candidates
        ),
        "was_elected": was_elected,
        "eligible_good_sheriff_ballots": eligible_good_sheriff_ballots,
        "supporting_good_sheriff_ballots": supporting_good_sheriff_ballots,
        "good_sheriff_support_rate": _rate(
            supporting_good_sheriff_ballots,
            eligible_good_sheriff_ballots,
        ),
        "black_check_claim_count": len(black_checks),
        "black_check_target_ids": sorted(
            {int(claim.target_id) for claim in black_checks if claim.target_id is not None}
        ),
        "eligible_good_exile_ballots": eligible_good_exile_ballots,
        "following_good_exile_ballots": following_good_exile_ballots,
        "good_black_check_follow_rate": _rate(
            following_good_exile_ballots,
            eligible_good_exile_ballots,
        ),
    }


def _fake_seer_eligible_in_round(
    election: Optional[rules.SheriffElectionState],
    fake_seer_id: int,
    round_index: int,
) -> bool:
    if election is None:
        return False
    if round_index <= 0:
        return (
            fake_seer_id in election.candidates
            and fake_seer_id not in election.withdrawn
        )
    return fake_seer_id in election.runoff_candidates


def _summarize_target_alignment(
    votes: Iterable[rules.VoteState],
    characters: dict[int, rules.CharacterState],
    *,
    voter_camp: Optional[str] = None,
) -> dict[str, object]:
    counter = _new_alignment_counter()
    for vote in votes:
        voter = characters[vote.voter_id]
        if voter_camp is not None and voter.camp != voter_camp:
            continue
        target = characters[vote.target_id]
        counter["ballot_count"] += 1
        if target.camp == "werewolf":
            counter["werewolf_target_count"] += 1
        else:
            counter["good_target_count"] += 1
    return _finalize_alignment_counts(counter)


def _new_alignment_counter() -> dict[str, int]:
    return {
        "ballot_count": 0,
        "werewolf_target_count": 0,
        "good_target_count": 0,
    }


def _add_alignment_counts(
    total: dict[str, int],
    alignment: dict[str, object],
) -> None:
    for key in total:
        total[key] += int(alignment[key])


def _finalize_alignment_counts(counter: dict[str, int]) -> dict[str, object]:
    ballot_count = counter["ballot_count"]
    return {
        "ballot_count": ballot_count,
        "werewolf_target_count": counter["werewolf_target_count"],
        "good_target_count": counter["good_target_count"],
        "werewolf_target_rate": _rate(
            counter["werewolf_target_count"],
            ballot_count,
        ),
        "good_target_rate": _rate(
            counter["good_target_count"],
            ballot_count,
        ),
    }


def _with_good_vote_labels(alignment: dict[str, object]) -> dict[str, object]:
    """Add explicit correctness names when the voter sample is known-good."""

    return {
        **alignment,
        "correct_wolf_target_count": int(alignment["werewolf_target_count"]),
        "misvote_good_target_count": int(alignment["good_target_count"]),
        "correct_wolf_target_rate": alignment["werewolf_target_rate"],
        "misvote_good_target_rate": alignment["good_target_rate"],
    }


def _summarize_distribution_samples(
    samples: list[dict[str, object]],
) -> dict[str, object]:
    entropy_values = [
        float(sample["entropy_bits"])
        for sample in samples
        if sample.get("entropy_bits") is not None
    ]
    normalized_values = [
        float(sample["normalized_entropy"])
        for sample in samples
        if sample.get("normalized_entropy") is not None
    ]
    return {
        "sample_count": len(samples),
        "ballot_count": sum(int(sample["ballot_count"]) for sample in samples),
        "mean_entropy_bits": _mean_or_none(entropy_values),
        "mean_normalized_entropy": _mean_or_none(normalized_values),
    }


def _require_game_metrics(game: dict[str, object]) -> dict[str, object]:
    metrics = game.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("simulation result is missing per-game metrics")
    if metrics.get("schema_version") != METRICS_SCHEMA_VERSION:
        raise ValueError("simulation result uses an incompatible metrics schema")
    return metrics


def _add_player_role_game(
    groups: dict[str, dict[str, object]],
    game: dict[str, object],
) -> None:
    player = next(
        role
        for role in game["roles"]
        if bool(role["is_player"])
    )
    role = str(player["role"])
    group = groups.setdefault(
        role,
        {
            "game_count": 0,
            "total_days": 0,
            "player_win_count": 0,
            "winner_counts": Counter(),
        },
    )
    group["game_count"] += 1
    group["total_days"] += int(game["total_days"])
    winner = str(game["winner"])
    group["winner_counts"][winner] += 1
    if winner == str(player["camp"]):
        group["player_win_count"] += 1


def _finalize_player_role_groups(
    groups: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    finalized = {}
    for role in sorted(groups):
        group = groups[role]
        game_count = int(group["game_count"])
        winner_counts = group["winner_counts"]
        finalized[role] = {
            "game_count": game_count,
            "winner_counts": {
                "good": winner_counts.get("good", 0),
                "werewolf": winner_counts.get("werewolf", 0),
            },
            "player_win_count": int(group["player_win_count"]),
            "player_win_rate": _rate(
                int(group["player_win_count"]),
                game_count,
            ),
            "average_total_days": _round_metric(
                int(group["total_days"]) / game_count
            ),
        }
    return finalized


def _add_fake_seer_counts(
    total: dict[str, int],
    fake_metrics: dict[str, object],
) -> None:
    if bool(fake_metrics["designated"]):
        total["designated_games"] += 1
    if bool(fake_metrics["publicly_claimed_seer"]):
        total["publicly_claimed_games"] += 1
    if bool(fake_metrics["was_candidate"]):
        total["candidate_games"] += 1
    if bool(fake_metrics["was_elected"]):
        total["elected_games"] += 1
    total["eligible_good_sheriff_ballots"] += int(
        fake_metrics["eligible_good_sheriff_ballots"]
    )
    total["supporting_good_sheriff_ballots"] += int(
        fake_metrics["supporting_good_sheriff_ballots"]
    )
    black_check_count = int(fake_metrics["black_check_claim_count"])
    total["black_check_claims"] += black_check_count
    if black_check_count:
        total["black_check_games"] += 1
    total["eligible_good_exile_ballots"] += int(
        fake_metrics["eligible_good_exile_ballots"]
    )
    total["following_good_exile_ballots"] += int(
        fake_metrics["following_good_exile_ballots"]
    )


def _finalize_fake_seer_counts(total: dict[str, int]) -> dict[str, object]:
    return {
        **total,
        "public_claim_rate": _rate(
            total["publicly_claimed_games"],
            total["designated_games"],
        ),
        "election_rate": _rate(
            total["elected_games"],
            total["candidate_games"],
        ),
        "good_sheriff_support_rate": _rate(
            total["supporting_good_sheriff_ballots"],
            total["eligible_good_sheriff_ballots"],
        ),
        "good_black_check_follow_rate": _rate(
            total["following_good_exile_ballots"],
            total["eligible_good_exile_ballots"],
        ),
    }


def _parse_sheriff_round(context: str) -> int:
    if context.startswith("round:"):
        try:
            return max(0, int(context.split(":", 1)[1]))
        except ValueError:
            return 0
    return 0


def _append_if_number(values: list[float], value: object) -> None:
    if isinstance(value, (int, float)):
        values.append(float(value))


def _mean_or_none(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return _round_metric(sum(values) / len(values))


def _rate(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return _round_metric(numerator / denominator)


def _round_metric(value: float) -> float:
    return round(float(value), 6)


def _validate_game_metric_conservation(metrics: dict[str, object]) -> None:
    good_vote = metrics["good_exile_vote"]
    if int(good_vote["ballot_count"]) != (
        int(good_vote["werewolf_target_count"])
        + int(good_vote["good_target_count"])
    ):
        raise ValueError("good exile-vote metric counts do not conserve ballots")
    fake = metrics["fake_seer_acceptance"]
    if int(fake["supporting_good_sheriff_ballots"]) > int(
        fake["eligible_good_sheriff_ballots"]
    ):
        raise ValueError("fake-seer sheriff support exceeds eligible ballots")
    if int(fake["following_good_exile_ballots"]) > int(
        fake["eligible_good_exile_ballots"]
    ):
        raise ValueError("fake-seer exile follows exceed eligible ballots")


def _validate_batch_metric_conservation(metrics: dict[str, object]) -> None:
    camp = metrics["camp_balance"]
    if sum(camp["winner_counts"].values()) != int(metrics["game_count"]):
        raise ValueError("batch winner counts do not match game count")
    good_vote = metrics["good_exile_vote"]
    if int(good_vote["ballot_count"]) != (
        int(good_vote["werewolf_target_count"])
        + int(good_vote["good_target_count"])
    ):
        raise ValueError("batch good-vote counts do not conserve ballots")


__all__ = [
    "METRICS_SCHEMA_VERSION",
    "aggregate_batch_metrics",
    "build_game_metrics",
    "summarize_ballot_distribution",
]
