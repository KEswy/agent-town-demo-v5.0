#!/usr/bin/env python3
"""Validate and canonicalize policy JSONL before training."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_policy_data import (  # noqa: E402
    load_policy_records,
    write_policy_records,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strictly validate/canonicalize npc policy JSONL."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-duplicate-observations",
        action="store_true",
        help="allow duplicate observations (normally labels should be merged separately)",
    )
    args = parser.parse_args()
    records = load_policy_records(
        args.input,
        reject_duplicate_observations=not args.allow_duplicate_observations,
    )
    digest = write_policy_records(args.output, records)
    factions: dict[str, int] = {}
    for record in records:
        faction = str(record["faction"])
        factions[faction] = factions.get(faction, 0) + 1
    print(
        json.dumps(
            {
                "schema_version": "npc_policy_dataset.v1",
                "records": len(records),
                "factions": factions,
                "output": str(args.output),
                "content_sha256": digest,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
