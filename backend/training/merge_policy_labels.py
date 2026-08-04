#!/usr/bin/env python3
"""Join human/expert preferences to actor-scoped policy observations."""

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
    merge_policy_labels,
    write_policy_records,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge labels by observation_digest into canonical V2 JSONL."
    )
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--include-teacher-records",
        action="store_true",
        help="retain the original rule-teacher rows in addition to labels",
    )
    args = parser.parse_args()
    observations = load_policy_records(args.observations)
    records = merge_policy_labels(
        observations,
        args.labels,
        include_teacher_records=args.include_teacher_records,
    )
    digest = write_policy_records(args.output, records)
    print(
        json.dumps(
            {
                "schema_version": "npc_policy_dataset.v1",
                "records": len(records),
                "labeled_records": sum(
                    1 for record in records if record["label_type"] != "rule_teacher"
                ),
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
