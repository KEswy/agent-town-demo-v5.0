#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GODOT_BIN="${GODOT_BIN:-$(command -v godot || true)}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/backend/.venv/bin/python}"
TEMPLATE_DIR="$HOME/Library/Application Support/Godot/export_templates/4.7.stable"
TEMPLATE_FILE="$TEMPLATE_DIR/macos.zip"
RELEASE_ROOT="${AGENT_TOWN_RELEASE_DIR:-$ROOT_DIR/dist}"
PACKAGE_NAME="AgentTownDemo-V5-macOS-arm64"
PACKAGE_DIR="$RELEASE_ROOT/$PACKAGE_NAME"
ARCHIVE_PATH="$RELEASE_ROOT/$PACKAGE_NAME.zip"
CHECKSUM_PATH="$ARCHIVE_PATH.sha256"
WORK_DIR=$(mktemp -d /tmp/agent-town-package-macos.XXXXXX)
BACKEND_PID=""

cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT INT TERM

if [ -z "$GODOT_BIN" ] || [ ! -x "$GODOT_BIN" ]; then
    printf 'Godot CLI not found. Set GODOT_BIN to a Godot 4.7 executable.\n' >&2
    exit 1
fi
if [ ! -x "$PYTHON_BIN" ]; then
    printf 'Packaging Python not found: %s\n' "$PYTHON_BIN" >&2
    exit 1
fi
if [ ! -f "$TEMPLATE_FILE" ]; then
    printf 'Godot 4.7 export template is missing: %s\n' "$TEMPLATE_FILE" >&2
    printf 'Install it from Editor > Manage Export Templates, then rerun.\n' >&2
    exit 1
fi
if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
    printf 'PyInstaller is missing. Run:\n' >&2
    printf '  backend/.venv/bin/pip install -r backend/requirements-packaging.txt\n' >&2
    exit 1
fi
if [ -e "$PACKAGE_DIR" ] || [ -e "$ARCHIVE_PATH" ]; then
    printf 'Release target already exists; move it aside before rebuilding:\n' >&2
    printf '  %s\n  %s\n' "$PACKAGE_DIR" "$ARCHIVE_PATH" >&2
    exit 1
fi

mkdir -p "$RELEASE_ROOT"
mkdir -p "$WORK_DIR/godot" "$WORK_DIR/pyinstaller-dist"

"$GODOT_BIN" \
    --headless \
    --path "$ROOT_DIR/game" \
    --export-release "macOS" \
    "$WORK_DIR/godot/Agent Town Demo.app"

"$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --onedir \
    --name agent-town-backend \
    --paths "$ROOT_DIR/backend" \
    --add-data "$ROOT_DIR/backend/config:config" \
    --add-data "$ROOT_DIR/backend/policy_artifacts:policy_artifacts" \
    --exclude-module fastembed \
    --exclude-module onnxruntime \
    --exclude-module tokenizers \
    --exclude-module huggingface_hub \
    --distpath "$WORK_DIR/pyinstaller-dist" \
    --workpath "$WORK_DIR/pyinstaller-work" \
    --specpath "$WORK_DIR/pyinstaller-spec" \
    "$ROOT_DIR/packaging/backend_entry.py"

mkdir -p "$PACKAGE_DIR"
ditto "$WORK_DIR/godot/Agent Town Demo.app" "$PACKAGE_DIR/Agent Town Demo.app"
ditto \
    "$WORK_DIR/pyinstaller-dist/agent-town-backend" \
    "$PACKAGE_DIR/backend"
cp "$ROOT_DIR/packaging/macos/launch_game.command" \
    "$PACKAGE_DIR/启动 Agent Town Demo.command"
cp "$ROOT_DIR/packaging/macos/.env.example" "$PACKAGE_DIR/配置示例.env"
cp "$ROOT_DIR/packaging/macos/README.md" "$PACKAGE_DIR/使用说明.md"
chmod +x "$PACKAGE_DIR/启动 Agent Town Demo.command"

{
    printf 'name=%s\n' "$PACKAGE_NAME"
    printf 'built_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'godot=%s\n' "$("$GODOT_BIN" --version)"
    printf 'backend_arch=%s\n' "$(uname -m)"
    printf 'git_commit=%s\n' "$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf unknown)"
    printf 'signed=%s\n' \
        "${AGENT_TOWN_CODESIGN_IDENTITY:-ad-hoc}"
    printf 'notarized=%s\n' \
        "${AGENT_TOWN_NOTARY_PROFILE:-no}"
} >"$PACKAGE_DIR/BUILD_INFO.txt"

if [[ -n "${AGENT_TOWN_CODESIGN_IDENTITY:-}" ]]; then
    # Developer ID distribution signing; requires a paid Apple Developer
    # account.  Set AGENT_TOWN_CODESIGN_IDENTITY (e.g. "Developer ID Application:
    # Your Name (TEAMID)") before running.
    codesign --force --options runtime \
        --sign "$AGENT_TOWN_CODESIGN_IDENTITY" \
        --deep "$PACKAGE_DIR/Agent Town Demo.app"
fi
codesign --verify --deep --strict "$PACKAGE_DIR/Agent Town Demo.app"
test -x "$PACKAGE_DIR/backend/agent-town-backend"
test -x "$PACKAGE_DIR/Agent Town Demo.app/Contents/MacOS/Agent Town Demo"

if [[ -n "${AGENT_TOWN_NOTARY_PROFILE:-}" ]]; then
    # Upload to Apple notary after signing.  The profile must be configured
    # with `xcrun notarytool store-credentials <profile> --apple-id ...`.
    ditto -c -k --keepParent \
        "$PACKAGE_DIR/Agent Town Demo.app" "$PACKAGE_DIR/Agent Town Demo.zip"
    xcrun notarytool submit \
        "$PACKAGE_DIR/Agent Town Demo.zip" \
        --keychain-profile "$AGENT_TOWN_NOTARY_PROFILE" \
        --wait
    xcrun stapler staple "$PACKAGE_DIR/Agent Town Demo.app"
fi

AGENT_TOWN_DATA_DIR="$WORK_DIR/runtime-data" \
AGENT_TOWN_GAME_SAVE_DIR="$WORK_DIR/runtime-data/games" \
AGENT_TOWN_BACKEND_PORT=18765 \
ENABLE_LLM=false \
LLM_PROVIDER=mock \
AGENT_TOWN_DISABLE_VECTOR_RAG=1 \
    "$PACKAGE_DIR/backend/agent-town-backend" \
    >"$WORK_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

attempt=0
while [ "$attempt" -lt 80 ]; do
    if curl --fail --silent http://127.0.0.1:18765/api/health \
        >"$WORK_DIR/health.json"; then
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        sed -n '1,160p' "$WORK_DIR/backend.log" >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 0.25
done

if ! grep -q '"status":"ok"' "$WORK_DIR/health.json"; then
    sed -n '1,160p' "$WORK_DIR/backend.log" >&2
    exit 1
fi

"$PACKAGE_DIR/Agent Town Demo.app/Contents/MacOS/Agent Town Demo" \
    --headless \
    --quit-after 2

kill "$BACKEND_PID" 2>/dev/null || true
wait "$BACKEND_PID" 2>/dev/null || true
BACKEND_PID=""

ditto -c -k --sequesterRsrc --keepParent "$PACKAGE_DIR" "$ARCHIVE_PATH"
(
    cd "$RELEASE_ROOT"
    shasum -a 256 "$(basename "$ARCHIVE_PATH")" \
        >"$(basename "$CHECKSUM_PATH")"
)

printf 'macOS package ready:\n'
printf '  folder: %s\n' "$PACKAGE_DIR"
printf '  archive: %s\n' "$ARCHIVE_PATH"
printf '  checksum: %s\n' "$CHECKSUM_PATH"
