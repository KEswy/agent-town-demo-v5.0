#!/usr/bin/env python3
"""Run deterministic Agent Town games without starting FastAPI or Godot."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# A simulation must never trigger a model download even if a future rule path
# accidentally asks the shared RAG index for vectors.
os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.simulation import (  # noqa: E402
    DEFAULT_PLAYER_STRATEGY,
    DEFAULT_MAX_DAYS,
    DEFAULT_MAX_STEPS,
    PLAYER_BENCHMARK_SCHEMA_VERSION,
    PLAYER_STRATEGY_TIERS,
    NPC_POLICY_MODES,
    run_player_strategy_benchmark,
    run_rule_simulation_batch,
)


PLAYER_ROLE_CHOICES = [
    "random",
    "werewolf",
    "seer",
    "witch",
    "hunter",
    "guard",
    "villager",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run rule-only, seed-replayable Agent Town games in the current process. "
            "No HTTP server, Godot process, LLM request, or vector model is started."
        )
    )
    parser.add_argument("--seed", type=int, default=1, help="first non-negative game seed")
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        help=(
            "number of sequential games, or seeds per fixed role when "
            "--benchmark-player-strategies is used"
        ),
    )
    parser.add_argument(
        "--player-role",
        choices=PLAYER_ROLE_CHOICES,
        default="random",
        help="fixed simulated player role or random",
    )
    parser.add_argument(
        "--variant",
        choices=["classic", "idiot"],
        default="classic",
        help="role-pool variant; idiot replaces one villager with an Idiot",
    )
    parser.add_argument(
        "--player-strategy",
        choices=PLAYER_STRATEGY_TIERS,
        default=DEFAULT_PLAYER_STRATEGY,
        help="offline simulated player tier; standard preserves the V3 baseline",
    )
    parser.add_argument(
        "--benchmark-player-strategies",
        action="store_true",
        help=(
            "run beginner/standard/expert on the same seeds for all six fixed "
            "roles; detailed belief/stance/vote traces are disabled"
        ),
    )
    parser.add_argument(
        "--npc-policy-mode",
        choices=NPC_POLICY_MODES,
        default="rule",
        help=(
            "NPC exile-decision mode: rule uses the current scorer, shadow "
            "also scores a local model but acts by rule, local acts by the "
            "sealed local model with rule fallback"
        ),
    )
    parser.add_argument(
        "--include-policy-traces",
        action="store_true",
        help=(
            "include actor-scoped candidate features, rule targets, and "
            "local scores for offline policy training/evaluation"
        ),
    )
    parser.add_argument("--max-days", type=int, default=DEFAULT_MAX_DAYS)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--no-belief-trace",
        action="store_true",
        help="omit belief and dependent stance traces for smaller reports",
    )
    parser.add_argument(
        "--no-stance-trace",
        action="store_true",
        help="keep beliefs but omit detailed shadow stance continuity traces",
    )
    parser.add_argument(
        "--no-vote-calibration-trace",
        action="store_true",
        help="omit M15-A/B vote probability traces and batch summary",
    )
    parser.add_argument(
        "--include-event-logs",
        action="store_true",
        help=(
            "include full V4.2 event arrays in batch JSON; replay verification "
            "and event summaries are always retained"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON file; stdout is used when omitted",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.benchmark_player_strategies:
        if args.player_role != "random":
            raise SystemExit(
                "--player-role cannot be combined with "
                "--benchmark-player-strategies"
            )
        if args.player_strategy != DEFAULT_PLAYER_STRATEGY:
            raise SystemExit(
                "--player-strategy cannot be combined with "
                "--benchmark-player-strategies"
            )
        if args.npc_policy_mode != "rule" or args.include_policy_traces:
            raise SystemExit(
                "--benchmark-player-strategies cannot be combined with "
                "--npc-policy-mode or --include-policy-traces"
            )
        report = run_player_strategy_benchmark(
            args.seed,
            args.games,
            variant=args.variant,
            max_days=args.max_days,
            max_steps=args.max_steps,
            capture_event_logs=args.include_event_logs,
        )
    else:
        report = run_rule_simulation_batch(
            args.seed,
            args.games,
            player_role=args.player_role,
            variant=args.variant,
            player_strategy=args.player_strategy,
            max_days=args.max_days,
            max_steps=args.max_steps,
            capture_beliefs=not args.no_belief_trace,
            capture_stances=(
                not args.no_belief_trace
                and not args.no_stance_trace
            ),
            capture_vote_calibration=not args.no_vote_calibration_trace,
            capture_event_logs=args.include_event_logs,
            capture_npc_policy=args.include_policy_traces,
            npc_policy_mode=args.npc_policy_mode,
        )
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        if report["schema_version"] == PLAYER_BENCHMARK_SCHEMA_VERSION:
            metrics = report["metrics"]
            strategy_wins = {
                strategy: group["player_performance"][
                    "player_win_count"
                ]
                for strategy, group in metrics["by_strategy"].items()
            }
            print(
                f"[OK] benchmarked {report['games_completed']} games "
                f"across {report['cohorts_completed']} paired cohort(s); "
                f"player_wins={strategy_wins}; output={args.output}"
            )
            print(
                "[REPLAY] "
                f"verified={sum(1 for game in report['games'] if game['replay']['verified'])}"
                f"/{report['games_completed']}; "
                f"events={sum(int(game['event_summary']['event_count']) for game in report['games'])}; "
                f"full_logs={'yes' if args.include_event_logs else 'no'}"
            )
            for comparison, outcome in metrics["paired_outcomes"].items():
                print(
                    "[PAIRED] "
                    f"{comparison}="
                    f"{_format_rate(outcome['player_win_rate_delta_b_minus_a'])}; "
                    f"a_only={outcome['a_only_win_count']}; "
                    f"b_only={outcome['b_only_win_count']}; "
                    f"same_win={outcome['same_win_count']}; "
                    f"same_loss={outcome['same_loss_count']}"
                )
            return 0
        experiment_fingerprint = report["experiment_fingerprint"]
        print(
            "[EXPERIMENT] "
            f"mode={experiment_fingerprint['execution_mode']}; "
            "configuration="
            f"{experiment_fingerprint['configuration_fingerprint'][:12]}; "
            "effective="
            f"{experiment_fingerprint['effective_fingerprint'][:12]}; "
            f"llm_requests=0; npc_policy={report['npc_policy_mode']}"
        )
        summary = report["summary"]
        metrics = report["metrics"]
        belief_summary = report["belief_summary"]
        stance_summary = report["stance_summary"]
        continuity_summary = report["speech_continuity_summary"]
        speech_quality_summary = report["npc_speech_quality_summary"]
        vote_calibration_summary = report["vote_calibration_summary"]
        good_vote = metrics["good_exile_vote"]
        fake_seer = metrics["fake_seer_acceptance"]
        balance = metrics["balance_diagnostics"]
        witch = balance["witch"]
        seer_balance = metrics["seer_claim_balance"]
        exile_chain = metrics["cross_day_exile_chain"]
        npc_vote_transitions = exile_chain["good_npc_vote_transitions"]
        first_wolf_transitions = exile_chain[
            "after_first_wolf_exile_good_npc_vote_transitions"
        ]
        print(
            f"[OK] simulated {report['games_completed']} game(s); "
            f"winner_counts={summary['winner_counts']}; output={args.output}"
        )
        print(
            "[REPLAY] "
            f"verified={summary['replays_verified']}/{report['games_completed']}; "
            f"events={summary['events_recorded']}; "
            f"full_logs={'yes' if report['event_logs_included'] else 'no'}"
        )
        print(
            "[METRICS] "
            f"good_win_rate={_format_rate(metrics['camp_balance']['good_win_rate'])}; "
            f"exile_entropy={_format_rate(metrics['exile_vote']['mean_normalized_entropy'])}; "
            f"good_misvote_rate={_format_rate(good_vote['misvote_good_target_rate'])}; "
            f"fake_seer_sheriff_support={_format_rate(fake_seer['good_sheriff_support_rate'])}; "
            f"fake_black_check_follow={_format_rate(fake_seer['good_black_check_follow_rate'])}"
        )
        print(
            "[BALANCE] "
            f"winner_reasons={balance['winner_reason_counts']}; "
            f"first_exile_camps={balance['first_exile_camp_counts']}"
        )
        print(
            "[WITCH] "
            f"first_night_save={_format_rate(witch['first_night_save_rate'])}; "
            f"second_night_poison={_format_rate(witch['second_night_poison_rate'])}; "
            f"accepted_hold={witch['accepted_hold_count']}; "
            f"poison_wolf_hit={_format_rate(witch['wolf_poison_rate'])}"
        )
        print(
            "[SEER] "
            f"fake_campaign={_format_rate(seer_balance['fake_campaign_rate'])}; "
            f"fake_elected={seer_balance['fake_elected']}; "
            "fake_black_checked_true="
            f"{seer_balance['fake_black_checked_true_seer']}; "
            f"true_first_exiled={seer_balance['true_seer_first_exiled']}"
        )
        print(
            "[EXILE-CHAIN] "
            "first_wolf_exile="
            f"{exile_chain['first_exile_wolf_game_count']}; "
            "next_exile_wolf="
            f"{_format_rate(exile_chain['next_exile_wolf_rate'])}; "
            "npc_correct_retention="
            f"{_format_rate(npc_vote_transitions['correct_retention_rate'])}; "
            "after_first_wolf_retention="
            f"{_format_rate(first_wolf_transitions['correct_retention_rate'])}"
        )
        if belief_summary is None:
            print("[BELIEF] detailed trace disabled")
        else:
            print(
                "[BELIEF] "
                f"mode={belief_summary['mode']}; "
                f"avg_evidence={belief_summary['average_evidence_per_game']}; "
                f"avg_changes={belief_summary['average_changes_per_game']}; "
                f"avg_final_confidence={_format_rate(belief_summary['average_final_confidence'])}"
            )
        if stance_summary is None:
            print("[STANCE] detailed trace disabled")
        else:
            print(
                "[STANCE] "
                f"mode={stance_summary['mode']}; "
                f"observations={stance_summary['observation_count']}; "
                f"alignment={_format_rate(stance_summary['alignment_rate'])}; "
                "unexplained_change="
                f"{_format_rate(stance_summary['unexplained_change_rate'])}"
            )
        print(
            "[CONTINUITY] "
            f"controlled_speeches={continuity_summary['controlled_speech_count']}; "
            f"reasons={continuity_summary['reason_counts']}"
        )
        print(
            "[SPEECH-QUALITY] "
            f"speeches={speech_quality_summary['speech_count']}; "
            "template_repeat="
            f"{_format_rate(speech_quality_summary['template_repeat_rate'])}; "
            "cross_actor_near_duplicate="
            f"{_format_rate(speech_quality_summary['cross_actor_near_duplicate_pair_rate'])}; "
            "information_increment="
            f"{_format_rate(speech_quality_summary['information_increment_rate'])}; "
            "evidence_citation="
            f"{_format_rate(speech_quality_summary['evidence_citation_rate'])}; "
            "persona_differentiation="
            f"{_format_rate(speech_quality_summary['persona_differentiation_score'])}"
        )
        if vote_calibration_summary is None:
            print("[VOTE-CALIBRATION] trace disabled")
        else:
            controlled_votes = vote_calibration_summary["by_consumer_mode"][
                "controlled"
            ]
            good_alignment = vote_calibration_summary[
                "good_exile_probability_alignment"
            ]
            print(
                "[VOTE-CALIBRATION] "
                f"observations={vote_calibration_summary['observation_count']}; "
                "controlled="
                f"{vote_calibration_summary['controlled_observation_count']}; "
                "controlled_entropy="
                f"{_format_rate(controlled_votes['mean_normalized_entropy'])}; "
                "controlled_top="
                f"{_format_rate(controlled_votes['mean_top_probability'])}; "
                "good_mass_on_wolves="
                f"{_format_rate(good_alignment['mean_probability_mass_on_wolves'])}"
            )
    return 0


def _format_rate(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "n/a"
    return f"{float(value):.1%}"


if __name__ == "__main__":
    raise SystemExit(main())
