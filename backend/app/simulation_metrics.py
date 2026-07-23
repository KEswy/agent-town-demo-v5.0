"""Post-game-only metrics for deterministic Agent Town simulations.

This module is imported by the offline simulation driver, never by a live
decision path. True roles are intentionally used only after ``GAME_OVER`` to
score decisions that were made from legal in-game perspectives.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import combinations
from typing import Iterable, Optional

from . import main as rules


METRICS_SCHEMA_VERSION = "agent_town_metrics.v5"
PLAYER_PERFORMANCE_SCHEMA_VERSION = "player_performance.v1"
CROSS_DAY_EXILE_CHAIN_SCHEMA_VERSION = "cross_day_exile_chain.v1"
VOTE_TRANSITION_COUNT_KEYS = (
    "correct_to_correct_count",
    "correct_to_misvote_count",
    "misvote_to_correct_count",
    "misvote_to_misvote_count",
)
SEER_BALANCE_WINNER_CONDITIONS = (
    "fake_campaign",
    "fake_elected",
    "fake_black_checked_true_seer",
    "true_seer_first_exiled",
)


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
        "balance_diagnostics": _build_balance_diagnostics(
            game_state,
            characters,
        ),
        "seer_claim_balance": _build_seer_claim_balance_metrics(
            game_state,
            characters,
        ),
        "cross_day_exile_chain": _build_cross_day_exile_chain_metrics(
            game_state,
            characters,
        ),
        "player_performance": _build_player_performance_metrics(
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
    player_performance_totals = _new_player_performance_counter()
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
    winner_reason_counts: Counter[str] = Counter()
    first_exile_camp_counts: Counter[str] = Counter()
    first_exile_role_counts: Counter[str] = Counter()
    elimination_cause_camp_counts: dict[str, Counter[str]] = defaultdict(Counter)
    witch_totals: Counter[str] = Counter()
    seer_totals: Counter[str] = Counter()
    seer_condition_winners: dict[str, Counter[str]] = defaultdict(Counter)
    first_exile_wolf_winners: Counter[str] = Counter()
    next_exile_after_first_wolf_camps: Counter[str] = Counter()
    cross_day_transition_totals: Counter[str] = Counter()
    first_wolf_transition_totals: Counter[str] = Counter()
    first_exile_wolf_game_count = 0
    no_next_exile_after_first_wolf_count = 0

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
        diagnostics = metrics["balance_diagnostics"]
        winner_reason_counts[str(diagnostics["winner_reason"])] += 1
        first_exile = diagnostics["first_exile"]
        if first_exile is not None:
            first_exile_camp_counts[str(first_exile["camp"])] += 1
            first_exile_role_counts[str(first_exile["role"])] += 1
        for cause, camp_counts in diagnostics[
            "elimination_counts_by_cause_and_camp"
        ].items():
            elimination_cause_camp_counts[str(cause)].update(
                {
                    str(camp): int(count)
                    for camp, count in camp_counts.items()
                }
            )
        for key, value in diagnostics["witch"].items():
            if isinstance(value, bool):
                witch_totals[key] += int(value)
            elif isinstance(value, int):
                witch_totals[key] += value
        seer_balance = metrics["seer_claim_balance"]
        for key, value in seer_balance.items():
            if isinstance(value, bool):
                seer_totals[key] += int(value)
            elif isinstance(value, int) and not key.endswith("_id"):
                seer_totals[key] += value
        winner = str(game["winner"])
        for condition in SEER_BALANCE_WINNER_CONDITIONS:
            if bool(seer_balance[condition]):
                seer_condition_winners[condition][winner] += 1
        exile_chain = metrics["cross_day_exile_chain"]
        _add_vote_transition_counts(
            cross_day_transition_totals,
            exile_chain["good_npc_vote_transitions"],
        )
        _add_vote_transition_counts(
            first_wolf_transition_totals,
            exile_chain["after_first_wolf_exile_good_npc_vote_transitions"],
        )
        if bool(exile_chain["first_exile_wolf"]):
            first_exile_wolf_game_count += 1
            first_exile_wolf_winners[winner] += 1
            next_camp = exile_chain["next_exile_after_first_wolf_camp"]
            if next_camp is None:
                no_next_exile_after_first_wolf_count += 1
            else:
                next_exile_after_first_wolf_camps[str(next_camp)] += 1
        _add_player_role_game(by_player_role, game)
        _add_player_performance_counts(
            player_performance_totals,
            metrics["player_performance"],
        )

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
        "balance_diagnostics": {
            "winner_reason_counts": {
                reason: winner_reason_counts[reason]
                for reason in sorted(winner_reason_counts)
            },
            "first_exile_camp_counts": {
                camp: first_exile_camp_counts[camp]
                for camp in sorted(first_exile_camp_counts)
            },
            "first_exile_role_counts": {
                role: first_exile_role_counts[role]
                for role in sorted(first_exile_role_counts)
            },
            "elimination_counts_by_cause_and_camp": {
                cause: {
                    camp: elimination_cause_camp_counts[cause][camp]
                    for camp in sorted(elimination_cause_camp_counts[cause])
                }
                for cause in sorted(elimination_cause_camp_counts)
            },
            "witch": {
                **{
                    key: witch_totals[key]
                    for key in sorted(witch_totals)
                },
                "first_night_save_rate": _rate(
                    witch_totals["first_night_save_used"],
                    witch_totals["first_night_save_opportunity"],
                ),
                "second_night_poison_rate": _rate(
                    witch_totals["second_night_poison_used"],
                    witch_totals["second_night_poison_opportunity"],
                ),
                "wolf_poison_rate": _rate(
                    witch_totals["wolf_poison_target_count"],
                    witch_totals["poison_target_count"],
                ),
            },
        },
        "seer_claim_balance": {
            **{
                key: seer_totals[key]
                for key in sorted(seer_totals)
            },
            "fake_campaign_rate": _rate(
                seer_totals["fake_campaign"],
                len(game_results),
            ),
            "fake_election_rate": _rate(
                seer_totals["fake_elected"],
                seer_totals["fake_candidate"],
            ),
            "true_seer_election_rate": _rate(
                seer_totals["true_seer_elected"],
                seer_totals["true_seer_candidate"],
            ),
            "winner_counts_by_condition": {
                condition: {
                    "good": seer_condition_winners[condition].get("good", 0),
                    "werewolf": seer_condition_winners[condition].get(
                        "werewolf",
                        0,
                    ),
                }
                for condition in SEER_BALANCE_WINNER_CONDITIONS
            },
        },
        "cross_day_exile_chain": {
            "schema_version": CROSS_DAY_EXILE_CHAIN_SCHEMA_VERSION,
            "game_count": len(game_results),
            "first_exile_wolf_game_count": first_exile_wolf_game_count,
            "first_exile_wolf_game_rate": _rate(
                first_exile_wolf_game_count,
                len(game_results),
            ),
            "first_exile_wolf_winner_counts": {
                "good": first_exile_wolf_winners.get("good", 0),
                "werewolf": first_exile_wolf_winners.get("werewolf", 0),
            },
            "first_exile_wolf_good_win_rate": _rate(
                first_exile_wolf_winners.get("good", 0),
                first_exile_wolf_game_count,
            ),
            "next_exile_after_first_wolf_count": sum(
                next_exile_after_first_wolf_camps.values()
            ),
            "next_exile_after_first_wolf_camp_counts": {
                "good": next_exile_after_first_wolf_camps.get("good", 0),
                "werewolf": next_exile_after_first_wolf_camps.get(
                    "werewolf",
                    0,
                ),
            },
            "no_next_exile_after_first_wolf_count": (
                no_next_exile_after_first_wolf_count
            ),
            "next_exile_wolf_rate": _rate(
                next_exile_after_first_wolf_camps.get("werewolf", 0),
                sum(next_exile_after_first_wolf_camps.values()),
            ),
            "good_npc_vote_transitions": _finalize_vote_transition_counts(
                cross_day_transition_totals
            ),
            "after_first_wolf_exile_good_npc_vote_transitions": (
                _finalize_vote_transition_counts(first_wolf_transition_totals)
            ),
        },
        "by_player_role": _finalize_player_role_groups(by_player_role),
        "player_performance": _finalize_player_performance_counts(
            player_performance_totals,
        ),
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


def aggregate_player_benchmark_metrics(
    game_results: list[dict[str, object]],
    *,
    strategy_order: list[str],
) -> dict[str, object]:
    """Aggregate role-paired player strategies without hiding raw counts."""

    if not game_results:
        raise ValueError("player benchmark metrics require completed games")
    if len(strategy_order) < 2 or len(set(strategy_order)) != len(
        strategy_order
    ):
        raise ValueError("player benchmark strategies must be unique")

    by_strategy: dict[str, dict[str, object]] = {}
    by_strategy_and_role: dict[str, dict[str, dict[str, object]]] = {}
    cohorts: dict[tuple[int, str], dict[str, dict[str, object]]] = {}
    for game in game_results:
        descriptor = game.get("player_strategy")
        if not isinstance(descriptor, dict):
            raise ValueError("benchmark game is missing player strategy metadata")
        strategy = str(descriptor.get("tier", ""))
        if strategy not in strategy_order:
            raise ValueError("benchmark game uses an undeclared strategy")
        performance = _require_game_metrics(game)["player_performance"]
        role = str(performance["player_role"])
        _add_player_benchmark_group(
            by_strategy.setdefault(strategy, _new_player_benchmark_group()),
            game,
            performance,
        )
        role_groups = by_strategy_and_role.setdefault(strategy, {})
        _add_player_benchmark_group(
            role_groups.setdefault(role, _new_player_benchmark_group()),
            game,
            performance,
        )
        cohort = cohorts.setdefault((int(game["seed"]), role), {})
        if strategy in cohort:
            raise ValueError("benchmark cohort contains a duplicate strategy")
        cohort[strategy] = game

    expected_strategies = set(strategy_order)
    for cohort_key, cohort in cohorts.items():
        if set(cohort) != expected_strategies:
            raise ValueError(
                f"benchmark cohort {cohort_key} is not strategy-complete"
            )

    paired_outcomes: dict[str, dict[str, object]] = {}
    for strategy_a, strategy_b in combinations(strategy_order, 2):
        a_only_win_count = 0
        b_only_win_count = 0
        same_win_count = 0
        same_loss_count = 0
        for cohort in cohorts.values():
            a_performance = _require_game_metrics(
                cohort[strategy_a]
            )["player_performance"]
            b_performance = _require_game_metrics(
                cohort[strategy_b]
            )["player_performance"]
            a_won = bool(a_performance["player_won"])
            b_won = bool(b_performance["player_won"])
            if a_won and b_won:
                same_win_count += 1
            elif not a_won and not b_won:
                same_loss_count += 1
            elif a_won:
                a_only_win_count += 1
            else:
                b_only_win_count += 1
        cohort_count = len(cohorts)
        paired_outcomes[f"{strategy_b}_minus_{strategy_a}"] = {
            "strategy_a": strategy_a,
            "strategy_b": strategy_b,
            "cohort_count": cohort_count,
            "a_only_win_count": a_only_win_count,
            "b_only_win_count": b_only_win_count,
            "same_win_count": same_win_count,
            "same_loss_count": same_loss_count,
            "player_win_rate_delta_b_minus_a": _round_metric(
                (b_only_win_count - a_only_win_count) / cohort_count
            ),
        }

    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "player_performance_schema_version": (
            PLAYER_PERFORMANCE_SCHEMA_VERSION
        ),
        "game_count": len(game_results),
        "cohort_count": len(cohorts),
        "strategy_count": len(strategy_order),
        "by_strategy": {
            strategy: _finalize_player_benchmark_group(by_strategy[strategy])
            for strategy in strategy_order
        },
        "by_strategy_and_role": {
            strategy: {
                role: _finalize_player_benchmark_group(
                    by_strategy_and_role[strategy][role]
                )
                for role in sorted(by_strategy_and_role[strategy])
            }
            for strategy in strategy_order
        },
        "paired_outcomes": paired_outcomes,
    }


def _new_player_benchmark_group() -> dict[str, object]:
    return {
        "game_count": 0,
        "total_days": 0,
        "winner_counts": Counter(),
        "performance": _new_player_performance_counter(),
    }


def _add_player_benchmark_group(
    group: dict[str, object],
    game: dict[str, object],
    performance: dict[str, object],
) -> None:
    group["game_count"] = int(group["game_count"]) + 1
    group["total_days"] = int(group["total_days"]) + int(
        game["total_days"]
    )
    winner_counts = group["winner_counts"]
    if not isinstance(winner_counts, Counter):
        raise ValueError("benchmark winner counter is invalid")
    winner_counts[str(game["winner"])] += 1
    performance_counter = group["performance"]
    if not isinstance(performance_counter, Counter):
        raise ValueError("benchmark performance counter is invalid")
    _add_player_performance_counts(performance_counter, performance)


def _finalize_player_benchmark_group(
    group: dict[str, object],
) -> dict[str, object]:
    game_count = int(group["game_count"])
    if game_count <= 0:
        raise ValueError("benchmark group must contain completed games")
    winner_counts = group["winner_counts"]
    performance = group["performance"]
    if not isinstance(winner_counts, Counter) or not isinstance(
        performance,
        Counter,
    ):
        raise ValueError("benchmark group counters are invalid")
    return {
        "game_count": game_count,
        "winner_counts": {
            "good": winner_counts.get("good", 0),
            "werewolf": winner_counts.get("werewolf", 0),
        },
        "average_total_days": _round_metric(
            int(group["total_days"]) / game_count
        ),
        "player_performance": _finalize_player_performance_counts(
            performance
        ),
    }


def _build_seer_claim_balance_metrics(
    game_state: rules.WolfGameState,
    characters: dict[int, rules.CharacterState],
) -> dict[str, object]:
    true_seer = next(
        character
        for character in game_state.characters
        if character.role == "seer"
    )
    fake_seer_id = game_state.wolf_fake_seer_id
    election = game_state.sheriff_election
    elected_id = next(
        (
            event.actor_id
            for event in game_state.sheriff_events
            if event.event_type == "elected"
        ),
        None,
    )
    first_exile_id = next(
        (
            elimination.character_id
            for elimination in game_state.eliminations
            if elimination.cause == "exiled"
        ),
        None,
    )
    exiled_ids = {
        elimination.character_id
        for elimination in game_state.eliminations
        if elimination.cause == "exiled"
    }
    true_public_claim = any(
        claim.character_id == true_seer.id
        and claim.claim_type == "role"
        and claim.claimed_role == "seer"
        for claim in game_state.public_claims
    )
    fake_checks = [
        claim
        for claim in game_state.public_claims
        if fake_seer_id is not None
        and claim.character_id == fake_seer_id
        and claim.claim_type == "seer_check"
        and claim.target_id is not None
    ]
    fake_public_claim = bool(
        fake_seer_id is not None
        and any(
            claim.character_id == fake_seer_id
            and claim.claim_type == "role"
            and claim.claimed_role == "seer"
            for claim in game_state.public_claims
        )
    )

    def count_fake_checks(result: str, target_camp: str) -> int:
        return sum(
            claim.result == result
            and characters[int(claim.target_id)].camp == target_camp
            for claim in fake_checks
            if claim.target_id is not None
        )

    fake_campaign = fake_seer_id is not None
    fake_candidate = bool(
        fake_seer_id is not None
        and election is not None
        and fake_seer_id in election.candidates
    )
    return {
        "true_seer_id": true_seer.id,
        "true_seer_candidate": bool(
            election is not None and true_seer.id in election.candidates
        ),
        "true_seer_elected": elected_id == true_seer.id,
        "true_seer_publicly_claimed": true_public_claim,
        "true_seer_first_exiled": first_exile_id == true_seer.id,
        "true_seer_exiled": true_seer.id in exiled_ids,
        "fake_seer_id": fake_seer_id,
        "fake_campaign": fake_campaign,
        "fake_candidate": fake_candidate,
        "fake_elected": fake_seer_id is not None and elected_id == fake_seer_id,
        "fake_publicly_claimed": fake_public_claim,
        "fake_first_exiled": (
            fake_seer_id is not None and first_exile_id == fake_seer_id
        ),
        "fake_exiled": fake_seer_id is not None and fake_seer_id in exiled_ids,
        "fake_black_checked_true_seer": any(
            claim.result == "werewolf" and claim.target_id == true_seer.id
            for claim in fake_checks
        ),
        "fake_check_count": len(fake_checks),
        "fake_black_check_good_count": count_fake_checks("werewolf", "good"),
        "fake_black_check_wolf_count": count_fake_checks(
            "werewolf",
            "werewolf",
        ),
        "fake_gold_check_good_count": count_fake_checks("good", "good"),
        "fake_gold_check_wolf_count": count_fake_checks("good", "werewolf"),
    }


def _build_cross_day_exile_chain_metrics(
    game_state: rules.WolfGameState,
    characters: dict[int, rules.CharacterState],
) -> dict[str, object]:
    """Score cross-day NPC vote quality without feeding role truth back in-game."""

    exiles = [
        elimination
        for elimination in game_state.eliminations
        if elimination.cause == "exiled"
    ]
    exile_camp_sequence = [
        characters[elimination.character_id].camp
        for elimination in exiles
    ]
    first_exile_wolf = bool(
        exile_camp_sequence and exile_camp_sequence[0] == "werewolf"
    )
    next_exile_camp = (
        exile_camp_sequence[1]
        if first_exile_wolf and len(exile_camp_sequence) > 1
        else None
    )
    correctness_by_day = _build_good_npc_vote_correctness_by_day(
        game_state.votes,
        characters,
    )
    vote_days = sorted(correctness_by_day)
    all_day_pairs = list(zip(vote_days, vote_days[1:]))
    first_wolf_day_pairs: list[tuple[int, int]] = []
    if first_exile_wolf:
        first_exile_day = exiles[0].day
        next_vote_day = next(
            (day for day in vote_days if day > first_exile_day),
            None,
        )
        if next_vote_day is not None:
            first_wolf_day_pairs.append((first_exile_day, next_vote_day))

    return {
        "schema_version": CROSS_DAY_EXILE_CHAIN_SCHEMA_VERSION,
        "exile_camp_sequence": exile_camp_sequence,
        "first_exile_wolf": first_exile_wolf,
        "next_exile_after_first_wolf_camp": next_exile_camp,
        "good_npc_vote_transitions": _summarize_vote_transition_pairs(
            correctness_by_day,
            all_day_pairs,
        ),
        "after_first_wolf_exile_good_npc_vote_transitions": (
            _summarize_vote_transition_pairs(
                correctness_by_day,
                first_wolf_day_pairs,
            )
        ),
    }


def _build_good_npc_vote_correctness_by_day(
    votes: Iterable[rules.VoteState],
    characters: dict[int, rules.CharacterState],
) -> dict[int, dict[int, bool]]:
    correctness_by_day: dict[int, dict[int, bool]] = defaultdict(dict)
    for vote in votes:
        voter = characters[vote.voter_id]
        if voter.is_player or voter.camp != "good":
            continue
        correctness_by_day[vote.day][vote.voter_id] = (
            characters[vote.target_id].camp == "werewolf"
        )
    return dict(correctness_by_day)


def _summarize_vote_transition_pairs(
    correctness_by_day: dict[int, dict[int, bool]],
    day_pairs: Iterable[tuple[int, int]],
) -> dict[str, object]:
    counts: Counter[str] = Counter()
    transition_names = {
        (True, True): "correct_to_correct_count",
        (True, False): "correct_to_misvote_count",
        (False, True): "misvote_to_correct_count",
        (False, False): "misvote_to_misvote_count",
    }
    for previous_day, current_day in day_pairs:
        previous_votes = correctness_by_day.get(previous_day, {})
        current_votes = correctness_by_day.get(current_day, {})
        for voter_id in sorted(set(previous_votes) & set(current_votes)):
            counts[
                transition_names[
                    (previous_votes[voter_id], current_votes[voter_id])
                ]
            ] += 1
    return _finalize_vote_transition_counts(counts)


def _add_vote_transition_counts(
    total: Counter[str],
    transitions: dict[str, object],
) -> None:
    for key in VOTE_TRANSITION_COUNT_KEYS:
        total[key] += int(transitions[key])


def _finalize_vote_transition_counts(
    counts: Counter[str],
) -> dict[str, object]:
    values = {
        key: int(counts.get(key, 0))
        for key in VOTE_TRANSITION_COUNT_KEYS
    }
    previous_correct_count = (
        values["correct_to_correct_count"]
        + values["correct_to_misvote_count"]
    )
    previous_misvote_count = (
        values["misvote_to_correct_count"]
        + values["misvote_to_misvote_count"]
    )
    return {
        **values,
        "transition_count": sum(values.values()),
        "previous_correct_count": previous_correct_count,
        "previous_misvote_count": previous_misvote_count,
        "correct_retention_rate": _rate(
            values["correct_to_correct_count"],
            previous_correct_count,
        ),
        "misvote_correction_rate": _rate(
            values["misvote_to_correct_count"],
            previous_misvote_count,
        ),
    }


def _build_balance_diagnostics(
    game_state: rules.WolfGameState,
    characters: dict[int, rules.CharacterState],
) -> dict[str, object]:
    exiles = [
        elimination
        for elimination in game_state.eliminations
        if elimination.cause == "exiled"
    ]
    first_exile = None
    if exiles:
        elimination = exiles[0]
        character = characters[elimination.character_id]
        first_exile = {
            "day": elimination.day,
            "character_id": character.id,
            "camp": character.camp,
            "role": character.role,
        }

    by_cause_and_camp: dict[str, Counter[str]] = defaultdict(Counter)
    for elimination in game_state.eliminations:
        target = characters[elimination.character_id]
        by_cause_and_camp[elimination.cause][target.camp] += 1

    witch = next(
        character
        for character in game_state.characters
        if character.role == "witch"
    )
    npc_decisions = [
        decision
        for decision in game_state.witch_strategy_decisions
        if decision.actor_id == witch.id
    ]
    first_night = next(
        (decision for decision in npc_decisions if decision.day == 1),
        None,
    )
    second_night = next(
        (decision for decision in npc_decisions if decision.day == 2),
        None,
    )
    poison_targets = [
        characters[action.target_id]
        for action in game_state.night_actions
        if action.actor_id == witch.id
        and action.action_type == "witch_poison"
        and action.target_id is not None
    ]
    directives = [
        speech.witch_directive
        for speech in game_state.speeches
        if speech.witch_directive is not None
    ]
    first_night_opportunity = bool(
        first_night is not None
        and first_night.reason
        in {
            "first_night_self_save",
            "first_night_save_99",
            "first_night_save_skip",
        }
    )
    second_night_opportunity = bool(
        second_night is not None
        and second_night.reason not in {"poison_unavailable", "no_legal_target"}
    )
    return {
        "winner_reason": game_state.winner_reason,
        "first_exile": first_exile,
        "elimination_counts_by_cause_and_camp": {
            cause: {
                camp: by_cause_and_camp[cause][camp]
                for camp in sorted(by_cause_and_camp[cause])
            }
            for cause in sorted(by_cause_and_camp)
        },
        "witch": {
            "npc_controlled": not witch.is_player,
            "public_directive_count": len(directives),
            "public_poison_directive_count": sum(
                directive.action == "poison" for directive in directives
            ),
            "public_hold_directive_count": sum(
                directive.action == "hold" for directive in directives
            ),
            "first_night_save_opportunity": first_night_opportunity,
            "first_night_save_used": bool(
                first_night is not None
                and first_night.action_type == "witch_save"
            ),
            "first_night_self_save_used": bool(
                first_night is not None
                and first_night.reason == "first_night_self_save"
            ),
            "second_night_poison_opportunity": second_night_opportunity,
            "second_night_poison_used": bool(
                second_night is not None
                and second_night.action_type == "witch_poison"
            ),
            "second_night_hold_accepted": bool(
                second_night is not None
                and second_night.reason == "accepted_hold"
            ),
            "accepted_hold_count": sum(
                decision.reason == "accepted_hold"
                for decision in npc_decisions
            ),
            "accepted_poison_directive_count": sum(
                decision.reason == "accepted_poison"
                for decision in npc_decisions
            ),
            "poison_target_count": len(poison_targets),
            "wolf_poison_target_count": sum(
                target.camp == "werewolf" for target in poison_targets
            ),
            "good_poison_target_count": sum(
                target.camp == "good" for target in poison_targets
            ),
        },
    }


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


_PLAYER_PERFORMANCE_COUNT_FIELDS = (
    "game_count",
    "player_win_count",
    "exile_ballot_count",
    "exile_wolf_target_count",
    "exile_good_target_count",
    "sheriff_ballot_count",
    "sheriff_wolf_target_count",
    "sheriff_good_target_count",
    "night_action_count",
    "seer_check_count",
    "seer_unique_check_target_count",
    "seer_repeat_check_count",
    "seer_wolf_hit_count",
    "witch_save_count",
    "witch_poison_count",
    "witch_poison_wolf_count",
    "witch_poison_good_count",
    "guard_protect_count",
    "guard_intercept_count",
    "hunter_shot_count",
    "hunter_wolf_hit_count",
    "werewolf_kill_choice_count",
    "werewolf_special_role_target_count",
    "public_target_speech_count",
    "npc_follow_eligible_ballot_count",
    "npc_follow_ballot_count",
)


def _build_player_performance_metrics(
    game_state: rules.WolfGameState,
    characters: dict[int, rules.CharacterState],
) -> dict[str, object]:
    player = characters[game_state.player_character_id]
    exile_ballots = [
        vote
        for vote in game_state.votes
        if vote.voter_id == player.id
    ]
    sheriff_ballots = [
        event
        for event in game_state.sheriff_events
        if event.event_type == "sheriff_vote"
        and event.actor_id == player.id
        and event.target_id is not None
    ]
    night_actions = [
        action
        for action in game_state.night_actions
        if action.actor_id == player.id
    ]
    seer_checks = [
        action
        for action in night_actions
        if action.action_type == "seer_check"
        and action.target_id is not None
    ]
    witch_saves = [
        action
        for action in night_actions
        if action.action_type == "witch_save"
        and action.target_id is not None
    ]
    witch_poisons = [
        action
        for action in night_actions
        if action.action_type == "witch_poison"
        and action.target_id is not None
    ]
    guard_actions = [
        action
        for action in night_actions
        if action.action_type == "guard_protect"
        and action.target_id is not None
    ]
    guard_intercepts = 0
    guard_target_by_day = {
        action.day: int(action.target_id)
        for action in guard_actions
        if action.target_id is not None
    }
    for resolution in game_state.night_resolutions:
        guard_target_id = guard_target_by_day.get(resolution.day)
        if (
            guard_target_id is not None
            and resolution.attacked_target_id == guard_target_id
            and guard_target_id in resolution.protected_ids
        ):
            guard_intercepts += 1

    hunter_shots = [
        shot
        for shot in game_state.hunter_shots
        if shot.hunter_id == player.id and shot.target_id is not None
    ]
    wolf_kill_choices = [
        action
        for action in night_actions
        if action.action_type == "werewolf_kill"
        and action.target_id is not None
    ]

    public_target_speech_count = 0
    npc_follow_eligible_ballot_count = 0
    npc_follow_ballot_count = 0
    latest_player_target_by_day: dict[int, int] = {}
    for speech in game_state.speeches:
        if speech.character_id != player.id or speech.phase != "DAY_MEETING":
            continue
        parsed = rules.parse_player_speech(
            game_state,
            speech.speech,
            speaker_id=player.id,
        )
        if parsed.vote_intent_target_id is None:
            continue
        latest_player_target_by_day[speech.day] = int(
            parsed.vote_intent_target_id
        )
    public_target_speech_count = len(latest_player_target_by_day)
    for vote in game_state.votes:
        if vote.voter_id == player.id:
            continue
        target_id = latest_player_target_by_day.get(vote.day)
        if target_id is None:
            continue
        npc_follow_eligible_ballot_count += 1
        if vote.target_id == target_id:
            npc_follow_ballot_count += 1

    seer_target_ids = [
        int(action.target_id)
        for action in seer_checks
        if action.target_id is not None
    ]
    metrics = {
        "schema_version": PLAYER_PERFORMANCE_SCHEMA_VERSION,
        "post_game_only": True,
        "player_role": player.role,
        "player_camp": player.camp,
        "player_won": game_state.winner == player.camp,
        "game_count": 1,
        "player_win_count": int(game_state.winner == player.camp),
        "exile_ballot_count": len(exile_ballots),
        "exile_wolf_target_count": sum(
            characters[vote.target_id].camp == "werewolf"
            for vote in exile_ballots
        ),
        "exile_good_target_count": sum(
            characters[vote.target_id].camp == "good"
            for vote in exile_ballots
        ),
        "sheriff_ballot_count": len(sheriff_ballots),
        "sheriff_wolf_target_count": sum(
            characters[int(event.target_id)].camp == "werewolf"
            for event in sheriff_ballots
            if event.target_id is not None
        ),
        "sheriff_good_target_count": sum(
            characters[int(event.target_id)].camp == "good"
            for event in sheriff_ballots
            if event.target_id is not None
        ),
        "night_action_count": len(
            [
                action
                for action in night_actions
                if action.action_type != "none"
            ]
        ),
        "seer_check_count": len(seer_checks),
        "seer_unique_check_target_count": len(set(seer_target_ids)),
        "seer_repeat_check_count": (
            len(seer_target_ids) - len(set(seer_target_ids))
        ),
        "seer_wolf_hit_count": sum(
            characters[target_id].camp == "werewolf"
            for target_id in seer_target_ids
        ),
        "witch_save_count": len(witch_saves),
        "witch_poison_count": len(witch_poisons),
        "witch_poison_wolf_count": sum(
            characters[int(action.target_id)].camp == "werewolf"
            for action in witch_poisons
            if action.target_id is not None
        ),
        "witch_poison_good_count": sum(
            characters[int(action.target_id)].camp == "good"
            for action in witch_poisons
            if action.target_id is not None
        ),
        "guard_protect_count": len(guard_actions),
        "guard_intercept_count": guard_intercepts,
        "hunter_shot_count": len(hunter_shots),
        "hunter_wolf_hit_count": sum(
            characters[int(shot.target_id)].camp == "werewolf"
            for shot in hunter_shots
            if shot.target_id is not None
        ),
        "werewolf_kill_choice_count": len(wolf_kill_choices),
        "werewolf_special_role_target_count": sum(
            characters[int(action.target_id)].role
            in {"seer", "witch", "hunter", "guard"}
            for action in wolf_kill_choices
            if action.target_id is not None
        ),
        "public_target_speech_count": public_target_speech_count,
        "npc_follow_eligible_ballot_count": (
            npc_follow_eligible_ballot_count
        ),
        "npc_follow_ballot_count": npc_follow_ballot_count,
    }
    metrics.update(_player_performance_rates(metrics))
    _validate_player_performance_conservation(metrics)
    return metrics


def _new_player_performance_counter() -> Counter[str]:
    return Counter()


def _add_player_performance_counts(
    total: Counter[str],
    performance: dict[str, object],
) -> None:
    if performance.get("schema_version") != PLAYER_PERFORMANCE_SCHEMA_VERSION:
        raise ValueError("player performance schema is incompatible")
    for field in _PLAYER_PERFORMANCE_COUNT_FIELDS:
        total[field] += int(performance[field])


def _finalize_player_performance_counts(
    total: Counter[str],
) -> dict[str, object]:
    finalized = {
        "schema_version": PLAYER_PERFORMANCE_SCHEMA_VERSION,
        "post_game_only": True,
        **{
            field: int(total[field])
            for field in _PLAYER_PERFORMANCE_COUNT_FIELDS
        },
    }
    finalized.update(_player_performance_rates(finalized))
    _validate_player_performance_conservation(finalized)
    return finalized


def _player_performance_rates(
    counts: dict[str, object],
) -> dict[str, Optional[float]]:
    return {
        "player_win_rate": _rate(
            int(counts["player_win_count"]),
            int(counts["game_count"]),
        ),
        "exile_wolf_target_rate": _rate(
            int(counts["exile_wolf_target_count"]),
            int(counts["exile_ballot_count"]),
        ),
        "sheriff_good_target_rate": _rate(
            int(counts["sheriff_good_target_count"]),
            int(counts["sheriff_ballot_count"]),
        ),
        "seer_wolf_hit_rate": _rate(
            int(counts["seer_wolf_hit_count"]),
            int(counts["seer_check_count"]),
        ),
        "witch_poison_wolf_rate": _rate(
            int(counts["witch_poison_wolf_count"]),
            int(counts["witch_poison_count"]),
        ),
        "guard_intercept_rate": _rate(
            int(counts["guard_intercept_count"]),
            int(counts["guard_protect_count"]),
        ),
        "hunter_wolf_hit_rate": _rate(
            int(counts["hunter_wolf_hit_count"]),
            int(counts["hunter_shot_count"]),
        ),
        "werewolf_special_role_target_rate": _rate(
            int(counts["werewolf_special_role_target_count"]),
            int(counts["werewolf_kill_choice_count"]),
        ),
        "npc_follow_rate": _rate(
            int(counts["npc_follow_ballot_count"]),
            int(counts["npc_follow_eligible_ballot_count"]),
        ),
    }


def _validate_player_performance_conservation(
    performance: dict[str, object],
) -> None:
    if int(performance["player_win_count"]) > int(
        performance["game_count"]
    ):
        raise ValueError("player wins exceed completed games")
    if int(performance["exile_ballot_count"]) != (
        int(performance["exile_wolf_target_count"])
        + int(performance["exile_good_target_count"])
    ):
        raise ValueError("player exile targets do not conserve ballots")
    if int(performance["sheriff_ballot_count"]) != (
        int(performance["sheriff_wolf_target_count"])
        + int(performance["sheriff_good_target_count"])
    ):
        raise ValueError("player sheriff targets do not conserve ballots")
    if int(performance["seer_check_count"]) != (
        int(performance["seer_unique_check_target_count"])
        + int(performance["seer_repeat_check_count"])
    ):
        raise ValueError("player seer checks do not conserve targets")
    if int(performance["witch_poison_count"]) != (
        int(performance["witch_poison_wolf_count"])
        + int(performance["witch_poison_good_count"])
    ):
        raise ValueError("player witch poison targets do not conserve actions")
    if int(performance["guard_intercept_count"]) > int(
        performance["guard_protect_count"]
    ):
        raise ValueError("player guard intercepts exceed protections")
    if int(performance["hunter_wolf_hit_count"]) > int(
        performance["hunter_shot_count"]
    ):
        raise ValueError("player hunter hits exceed shots")
    if int(performance["werewolf_special_role_target_count"]) > int(
        performance["werewolf_kill_choice_count"]
    ):
        raise ValueError("player wolf special-role targets exceed kill choices")
    if int(performance["npc_follow_ballot_count"]) > int(
        performance["npc_follow_eligible_ballot_count"]
    ):
        raise ValueError("NPC follows exceed eligible ballots")


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
    witch = metrics["balance_diagnostics"]["witch"]
    if int(witch["poison_target_count"]) != (
        int(witch["wolf_poison_target_count"])
        + int(witch["good_poison_target_count"])
    ):
        raise ValueError("witch poison-target metrics do not conserve actions")
    if int(witch["public_directive_count"]) != (
        int(witch["public_poison_directive_count"])
        + int(witch["public_hold_directive_count"])
    ):
        raise ValueError("public witch-directive metrics do not conserve speech records")
    if int(witch["second_night_poison_opportunity"]) != (
        int(witch["second_night_poison_used"])
        + int(witch["second_night_hold_accepted"])
    ):
        raise ValueError("night-two witch choices must be poison or accepted hold")
    seer = metrics["seer_claim_balance"]
    if int(seer["fake_check_count"]) != sum(
        int(seer[key])
        for key in (
            "fake_black_check_good_count",
            "fake_black_check_wolf_count",
            "fake_gold_check_good_count",
            "fake_gold_check_wolf_count",
        )
    ):
        raise ValueError("fake-seer check mix does not conserve public checks")
    if bool(seer["fake_candidate"]) and not bool(seer["fake_campaign"]):
        raise ValueError("a fake-seer candidate requires a selected campaign")
    exile_chain = metrics["cross_day_exile_chain"]
    if exile_chain["schema_version"] != CROSS_DAY_EXILE_CHAIN_SCHEMA_VERSION:
        raise ValueError("cross-day exile-chain schema is incompatible")
    exile_sequence = exile_chain["exile_camp_sequence"]
    if bool(exile_chain["first_exile_wolf"]) != bool(
        exile_sequence and exile_sequence[0] == "werewolf"
    ):
        raise ValueError("first-wolf exile flag must match the exile sequence")
    expected_next_camp = (
        exile_sequence[1]
        if exile_chain["first_exile_wolf"] and len(exile_sequence) > 1
        else None
    )
    if exile_chain["next_exile_after_first_wolf_camp"] != expected_next_camp:
        raise ValueError("next exile after a first wolf must match the sequence")
    _validate_vote_transition_conservation(
        exile_chain["good_npc_vote_transitions"]
    )
    _validate_vote_transition_conservation(
        exile_chain["after_first_wolf_exile_good_npc_vote_transitions"]
    )
    _validate_player_performance_conservation(
        metrics["player_performance"]
    )


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
    witch = metrics["balance_diagnostics"]["witch"]
    if int(witch["poison_target_count"]) != (
        int(witch["wolf_poison_target_count"])
        + int(witch["good_poison_target_count"])
    ):
        raise ValueError("batch witch poison-target metrics do not conserve actions")
    if int(witch["public_directive_count"]) != (
        int(witch["public_poison_directive_count"])
        + int(witch["public_hold_directive_count"])
    ):
        raise ValueError("batch public witch directives do not conserve speech records")
    if int(witch["second_night_poison_opportunity"]) != (
        int(witch["second_night_poison_used"])
        + int(witch["second_night_hold_accepted"])
    ):
        raise ValueError("batch night-two witch choices do not conserve opportunities")
    seer = metrics["seer_claim_balance"]
    if int(seer["fake_check_count"]) != sum(
        int(seer[key])
        for key in (
            "fake_black_check_good_count",
            "fake_black_check_wolf_count",
            "fake_gold_check_good_count",
            "fake_gold_check_wolf_count",
        )
    ):
        raise ValueError("batch fake-seer check mix does not conserve checks")
    for condition, winner_counts in seer["winner_counts_by_condition"].items():
        if sum(int(count) for count in winner_counts.values()) != int(
            seer[condition]
        ):
            raise ValueError(
                f"seer condition winner counts do not conserve {condition}"
            )
    exile_chain = metrics["cross_day_exile_chain"]
    if (
        exile_chain["schema_version"] != CROSS_DAY_EXILE_CHAIN_SCHEMA_VERSION
        or int(exile_chain["game_count"]) != int(metrics["game_count"])
    ):
        raise ValueError("batch cross-day exile-chain schema is incompatible")
    first_wolf_games = int(exile_chain["first_exile_wolf_game_count"])
    if (
        sum(exile_chain["first_exile_wolf_winner_counts"].values())
        != first_wolf_games
    ):
        raise ValueError("first-wolf winner counts do not conserve games")
    if (
        int(exile_chain["next_exile_after_first_wolf_count"])
        + int(exile_chain["no_next_exile_after_first_wolf_count"])
        != first_wolf_games
    ):
        raise ValueError("first-wolf follow-up counts do not conserve games")
    if sum(exile_chain["next_exile_after_first_wolf_camp_counts"].values()) != int(
        exile_chain["next_exile_after_first_wolf_count"]
    ):
        raise ValueError("next-exile camp counts do not conserve follow-ups")
    _validate_vote_transition_conservation(
        exile_chain["good_npc_vote_transitions"]
    )
    _validate_vote_transition_conservation(
        exile_chain["after_first_wolf_exile_good_npc_vote_transitions"]
    )
    player_performance = metrics["player_performance"]
    if int(player_performance["game_count"]) != int(metrics["game_count"]):
        raise ValueError("batch player performance does not cover every game")
    _validate_player_performance_conservation(player_performance)


def _validate_vote_transition_conservation(
    transitions: dict[str, object],
) -> None:
    transition_count = sum(
        int(transitions[key])
        for key in VOTE_TRANSITION_COUNT_KEYS
    )
    if transition_count != int(transitions["transition_count"]):
        raise ValueError("cross-day vote transitions do not conserve observations")
    if int(transitions["previous_correct_count"]) != (
        int(transitions["correct_to_correct_count"])
        + int(transitions["correct_to_misvote_count"])
    ):
        raise ValueError("previous-correct transition counts do not conserve")
    if int(transitions["previous_misvote_count"]) != (
        int(transitions["misvote_to_correct_count"])
        + int(transitions["misvote_to_misvote_count"])
    ):
        raise ValueError("previous-misvote transition counts do not conserve")


__all__ = [
    "CROSS_DAY_EXILE_CHAIN_SCHEMA_VERSION",
    "METRICS_SCHEMA_VERSION",
    "PLAYER_PERFORMANCE_SCHEMA_VERSION",
    "aggregate_batch_metrics",
    "aggregate_player_benchmark_metrics",
    "build_game_metrics",
    "summarize_ballot_distribution",
]
