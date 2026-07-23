#!/usr/bin/env python3
"""Compare sealed Agent Town rule-simulation artifacts without running games."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.experiment import compare_simulation_artifacts  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two sets of sealed agent_town_simulation_batch.v17 "
            "artifacts. This command does not run a game or call an LLM."
        )
    )
    parser.add_argument(
        "--arm-a",
        action="append",
        required=True,
        type=Path,
        metavar="BATCH_JSON",
        help="baseline batch JSON; repeat to combine fixed-role artifacts",
    )
    parser.add_argument(
        "--arm-b",
        action="append",
        required=True,
        type=Path,
        metavar="BATCH_JSON",
        help="candidate batch JSON; repeat to combine fixed-role artifacts",
    )
    parser.add_argument("--label-a", default="baseline")
    parser.add_argument("--label-b", default="candidate")
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON output; when omitted, JSON is written to stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        arm_a = [_load_json_object(path) for path in args.arm_a]
        arm_b = [_load_json_object(path) for path in args.arm_b]
        report = compare_simulation_artifacts(
            arm_a,
            arm_b,
            label_a=args.label_a,
            label_b=args.label_b,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"artifact comparison failed: {exc}") from exc

    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is None:
        print(rendered, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    outcomes = report["paired_outcomes"]
    arms = report["arm_descriptors"]
    print(
        "[ARTIFACT-A/B] "
        f"mode={report['comparison_mode']}; "
        f"cohorts={report['cohort_count']}; "
        "a="
        f"{arms['arm_a']['configuration_fingerprint'][:12]}; "
        "b="
        f"{arms['arm_b']['configuration_fingerprint'][:12]}; "
        f"a_only={outcomes['a_only_win_count']}; "
        f"b_only={outcomes['b_only_win_count']}; "
        f"same_win={outcomes['same_win_count']}; "
        f"same_loss={outcomes['same_loss_count']}; "
        f"exact_gameplay={outcomes['same_gameplay_count']}; "
        f"gameplay_changed={outcomes['changed_gameplay_count']}; "
        f"output={args.output}"
    )
    for metric_name, comparison in report[
        "speech_quality_comparisons"
    ].items():
        print(
            "[QUALITY-A/B] "
            f"metric={metric_name}; "
            f"a={_format_rate(comparison['arm_a']['rate'])}; "
            f"b={_format_rate(comparison['arm_b']['rate'])}; "
            f"delta_b_minus_a="
            f"{_format_rate(comparison['rate_delta_b_minus_a'])}; "
            f"desired={comparison['desired_direction']}"
        )
    return 0


def _load_json_object(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OSError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"invalid JSON in {path}: {exc.msg}",
            exc.doc,
            exc.pos,
        ) from exc
    if type(payload) is not dict:
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _format_rate(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
