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
    DEFAULT_MAX_DAYS,
    DEFAULT_MAX_STEPS,
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
    parser.add_argument("--games", type=int, default=1, help="number of sequential seeds")
    parser.add_argument(
        "--player-role",
        choices=PLAYER_ROLE_CHOICES,
        default="random",
        help="fixed simulated player role or random",
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
        "--output",
        type=Path,
        help="optional JSON file; stdout is used when omitted",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_rule_simulation_batch(
        args.seed,
        args.games,
        player_role=args.player_role,
        max_days=args.max_days,
        max_steps=args.max_steps,
        capture_beliefs=not args.no_belief_trace,
        capture_stances=(
            not args.no_belief_trace
            and not args.no_stance_trace
        ),
        capture_vote_calibration=not args.no_vote_calibration_trace,
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
        summary = report["summary"]
        metrics = report["metrics"]
        belief_summary = report["belief_summary"]
        stance_summary = report["stance_summary"]
        continuity_summary = report["speech_continuity_summary"]
        vote_calibration_summary = report["vote_calibration_summary"]
        good_vote = metrics["good_exile_vote"]
        fake_seer = metrics["fake_seer_acceptance"]
        print(
            f"[OK] simulated {report['games_completed']} game(s); "
            f"winner_counts={summary['winner_counts']}; output={args.output}"
        )
        print(
            "[METRICS] "
            f"good_win_rate={_format_rate(metrics['camp_balance']['good_win_rate'])}; "
            f"exile_entropy={_format_rate(metrics['exile_vote']['mean_normalized_entropy'])}; "
            f"good_misvote_rate={_format_rate(good_vote['misvote_good_target_rate'])}; "
            f"fake_seer_sheriff_support={_format_rate(fake_seer['good_sheriff_support_rate'])}; "
            f"fake_black_check_follow={_format_rate(fake_seer['good_black_check_follow_rate'])}"
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
