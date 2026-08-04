#!/bin/sh
set -eu

PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$PACKAGE_DIR/.env"
BACKEND_BIN="$PACKAGE_DIR/backend/agent-town-backend"
GAME_BIN="$PACKAGE_DIR/Agent Town Demo.app/Contents/MacOS/Agent Town Demo"
HEALTH_URL="http://127.0.0.1:8000/api/health"
BACKEND_PID=""

if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi

DATA_DIR="${AGENT_TOWN_DATA_DIR:-$HOME/Library/Application Support/Agent Town Demo}"
export ENABLE_LLM="${ENABLE_LLM:-false}"
export LLM_PROVIDER="${LLM_PROVIDER:-mock}"
export AGENT_TOWN_DISABLE_VECTOR_RAG="${AGENT_TOWN_DISABLE_VECTOR_RAG:-1}"
export AGENT_TOWN_NPC_POLICY_MODE="${AGENT_TOWN_NPC_POLICY_MODE:-rule}"
export AGENT_TOWN_DATA_DIR="$DATA_DIR"
export AGENT_TOWN_GAME_SAVE_DIR="${AGENT_TOWN_GAME_SAVE_DIR:-$DATA_DIR/games}"

mkdir -p "$DATA_DIR"

cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

if ! curl --fail --silent --show-error "$HEALTH_URL" >/dev/null 2>&1; then
    "$BACKEND_BIN" >"$DATA_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    attempt=0
    while [ "$attempt" -lt 80 ]; do
        if curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1; then
            break
        fi
        if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            printf '后端启动失败，请查看：%s\n' "$DATA_DIR/backend.log" >&2
            exit 1
        fi
        attempt=$((attempt + 1))
        sleep 0.25
    done
fi

if ! curl --fail --silent --show-error "$HEALTH_URL" >/dev/null; then
    printf '后端健康检查超时，请查看：%s\n' "$DATA_DIR/backend.log" >&2
    exit 1
fi

"$GAME_BIN"
