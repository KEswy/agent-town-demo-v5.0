"""Standalone packaged-backend entry point for macOS and Windows."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_data_dir() -> Path:
    if os.name == "nt":
        return (
            Path(
                os.environ.get(
                    "LOCALAPPDATA",
                    str(Path.home() / "AppData" / "Local"),
                )
            )
            / "Agent Town Demo"
        )
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Agent Town Demo"
        )
    return (
        Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        / "agent-town-demo"
    )


def main() -> None:
    os.environ.setdefault("ENABLE_LLM", "false")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault("AGENT_TOWN_DISABLE_VECTOR_RAG", "1")
    os.environ.setdefault("AGENT_TOWN_NPC_POLICY_MODE", "rule")
    os.environ.setdefault("AGENT_TOWN_DATA_DIR", str(_default_data_dir()))
    os.environ.setdefault(
        "AGENT_TOWN_GAME_SAVE_DIR",
        str(Path(os.environ["AGENT_TOWN_DATA_DIR"]) / "games"),
    )

    from app.main import app
    import uvicorn

    host = os.environ.get("AGENT_TOWN_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("AGENT_TOWN_BACKEND_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("AGENT_TOWN_BACKEND_PORT must be between 1 and 65535")
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,
        reload=False,
        access_log=False,
        log_level=os.environ.get(
            "AGENT_TOWN_BACKEND_LOG_LEVEL",
            "warning",
        ),
    )


if __name__ == "__main__":
    main()
