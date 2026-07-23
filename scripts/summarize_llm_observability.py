#!/usr/bin/env python3
"""Summarize Agent Town's redacted local LLM observation JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.llm_observability import (  # noqa: E402
    LLM_OBSERVABILITY_LOG_FILE,
    summarize_observation_file,
)
from app.llm_pricing import (  # noqa: E402
    DEFAULT_LLM_PRICE_CATALOG_PATH,
    load_price_catalog,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize redacted local LLM request and validation events.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=LLM_OBSERVABILITY_LOG_FILE,
        help="Observation JSONL path (default: backend/data/llm_observability.jsonl).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path; stdout is always printed.",
    )
    parser.add_argument(
        "--price-catalog",
        type=Path,
        default=DEFAULT_LLM_PRICE_CATALOG_PATH,
        help=(
            "Versioned LLM price catalog; unknown or missing prices remain "
            "unknown instead of being treated as zero."
        ),
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize_observation_file(
        args.input,
        price_catalog=load_price_catalog(args.price_catalog),
    )
    serialized = json.dumps(
        summary,
        ensure_ascii=False,
        sort_keys=True,
        indent=None if args.compact else 2,
        separators=(",", ":") if args.compact else None,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
