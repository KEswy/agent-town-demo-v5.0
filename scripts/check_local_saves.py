#!/usr/bin/env python3
"""Boot-check the on-disk game saves without starting FastAPI or Godot.

Every schema change that touches ``WolfGameState`` (new optional fields,
renamed state, etc.) must keep every previously saved game restorable, because
``activate_game_persistence`` refuses to start otherwise.  Run this script
before committing any backend change that could affect persistence:

    backend/.venv/bin/python scripts/check_local_saves.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# A save-restore must never trigger a model download.
os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import (  # noqa: E402
    recover_unfinished_games_from_disk,
)


def main() -> int:
    report = recover_unfinished_games_from_disk()
    print(
        f"scanned={report.scanned_count} restored={report.restored_count} "
        f"failures={report.failure_count}"
    )
    for failure in report.failures:
        print(f"FAIL {failure.game_id}: {failure.reason}")
    if report.failure_count:
        print("backend would refuse to start; fix persistence compatibility first")
        return 1
    print("all local saves restore cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
