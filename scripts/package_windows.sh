#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GODOT_BIN="${GODOT_BIN:-$(command -v godot || true)}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/backend/.venv/bin/python}"
if [ -n "${AGENT_TOWN_GODOT_TEMPLATE_DIR:-}" ]; then
    TEMPLATE_DIR="$AGENT_TOWN_GODOT_TEMPLATE_DIR"
elif [ "$(uname -s)" = "Darwin" ]; then
    TEMPLATE_DIR="$HOME/Library/Application Support/Godot/export_templates/4.7.stable"
else
    TEMPLATE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates/4.7.stable"
fi
TEMPLATE_FILE="$TEMPLATE_DIR/windows_release_x86_64.exe"
CACHE_DIR="${AGENT_TOWN_PACKAGE_CACHE_DIR:-$HOME/.cache/agent-town-demo-packaging}"
EMBED_NAME="python-3.12.10-embed-amd64.zip"
EMBED_URL="https://www.python.org/ftp/python/3.12.10/$EMBED_NAME"
EMBED_SHA256="4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
EMBED_ARCHIVE="$CACHE_DIR/$EMBED_NAME"
RELEASE_ROOT="${AGENT_TOWN_RELEASE_DIR:-$ROOT_DIR/dist}"
PACKAGE_NAME="AgentTownDemo-V5-Windows-x64"
PACKAGE_DIR="$RELEASE_ROOT/$PACKAGE_NAME"
ARCHIVE_PATH="$RELEASE_ROOT/$PACKAGE_NAME.zip"
CHECKSUM_PATH="$ARCHIVE_PATH.sha256"
WORK_DIR=$(mktemp -d /tmp/agent-town-package-windows.XXXXXX)

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT INT TERM

if [ -z "$GODOT_BIN" ] || [ ! -x "$GODOT_BIN" ]; then
    printf 'Godot CLI not found. Set GODOT_BIN to a Godot 4.7 executable.\n' >&2
    exit 1
fi
if [ ! -x "$PYTHON_BIN" ]; then
    printf 'Builder Python not found: %s\n' "$PYTHON_BIN" >&2
    exit 1
fi
if [ ! -f "$TEMPLATE_FILE" ]; then
    printf 'Godot Windows x86_64 export template is missing: %s\n' \
        "$TEMPLATE_FILE" >&2
    exit 1
fi
if [ -e "$PACKAGE_DIR" ] || [ -e "$ARCHIVE_PATH" ]; then
    printf 'Release target already exists; move it aside before rebuilding:\n' >&2
    printf '  %s\n  %s\n' "$PACKAGE_DIR" "$ARCHIVE_PATH" >&2
    exit 1
fi

mkdir -p "$CACHE_DIR" "$RELEASE_ROOT"
if [ ! -f "$EMBED_ARCHIVE" ]; then
    curl -L --fail --show-error --output "$EMBED_ARCHIVE" "$EMBED_URL"
fi
ACTUAL_EMBED_SHA256=$(shasum -a 256 "$EMBED_ARCHIVE" | awk '{print $1}')
if [ "$ACTUAL_EMBED_SHA256" != "$EMBED_SHA256" ]; then
    printf 'Python embeddable package checksum mismatch.\n' >&2
    exit 1
fi

mkdir -p \
    "$WORK_DIR/godot" \
    "$WORK_DIR/python" \
    "$WORK_DIR/python/Lib/site-packages"
unzip -q "$EMBED_ARCHIVE" -d "$WORK_DIR/python"
cp "$ROOT_DIR/packaging/windows/python312._pth" \
    "$WORK_DIR/python/python312._pth"

"$PYTHON_BIN" -m pip install \
    --disable-pip-version-check \
    --progress-bar off \
    --no-compile \
    --only-binary=:all: \
    --platform win_amd64 \
    --python-version 3.12 \
    --implementation cp \
    --abi cp312 \
    --target "$WORK_DIR/python/Lib/site-packages" \
    --requirement "$ROOT_DIR/packaging/windows/requirements.txt"

"$GODOT_BIN" \
    --headless \
    --path "$ROOT_DIR/game" \
    --export-release "Windows Desktop" \
    "$WORK_DIR/godot/Agent Town Demo.exe"

mkdir -p "$PACKAGE_DIR/backend"
cp "$WORK_DIR/godot/Agent Town Demo.exe" \
    "$PACKAGE_DIR/Agent Town Demo.exe"
ditto "$WORK_DIR/python" "$PACKAGE_DIR/backend/python"
rsync -a \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    "$ROOT_DIR/backend/app/" \
    "$PACKAGE_DIR/backend/app/"
ditto "$ROOT_DIR/backend/config" "$PACKAGE_DIR/backend/config"
ditto \
    "$ROOT_DIR/backend/policy_artifacts" \
    "$PACKAGE_DIR/backend/policy_artifacts"
cp "$ROOT_DIR/packaging/backend_entry.py" \
    "$PACKAGE_DIR/backend/backend_entry.py"
cp "$ROOT_DIR/packaging/windows/Start Agent Town Demo.bat" \
    "$PACKAGE_DIR/Start Agent Town Demo.bat"
cp "$ROOT_DIR/packaging/windows/Start Agent Town Demo.ps1" \
    "$PACKAGE_DIR/Start Agent Town Demo.ps1"
cp "$ROOT_DIR/packaging/windows/.env.example" \
    "$PACKAGE_DIR/配置示例.env"
cp "$ROOT_DIR/packaging/windows/README.md" \
    "$PACKAGE_DIR/使用说明.md"

{
    printf 'name=%s\n' "$PACKAGE_NAME"
    printf 'built_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'godot=%s\n' "$("$GODOT_BIN" --version)"
    printf 'client_arch=x86_64\n'
    printf 'backend_python=3.12.10-embed-amd64\n'
    printf 'git_commit=%s\n' "$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf unknown)"
    printf 'signed=%s\n' \
        "${AGENT_TOWN_WINDOWS_CERT:-no}"
    printf 'windows_runtime_verified=no\n'
} >"$PACKAGE_DIR/BUILD_INFO.txt"

test -f "$PACKAGE_DIR/Agent Town Demo.exe"
test -f "$PACKAGE_DIR/backend/python/python.exe"
test -f "$PACKAGE_DIR/backend/python/python312.dll"
test -f "$PACKAGE_DIR/backend/python/Lib/site-packages/numpy/__init__.py"
test -f "$PACKAGE_DIR/backend/app/main.py"

if [[ -n "${AGENT_TOWN_WINDOWS_CERT:-}" ]]; then
    # Authenticode signing; requires a Windows code-signing certificate.
    # Set AGENT_TOWN_WINDOWS_CERT (path to the .pfx) and
    # AGENT_TOWN_WINDOWS_CERT_PASSWORD before running on a Windows host (or
    # via osxcross/osslsigncode on macOS).
    if command -v signtool >/dev/null 2>&1; then
        signtool sign /f "$AGENT_TOWN_WINDOWS_CERT" \
            /p "${AGENT_TOWN_WINDOWS_CERT_PASSWORD:-}" \
            "$PACKAGE_DIR/Agent Town Demo.exe"
    elif command -v osslsigncode >/dev/null 2>&1; then
        osslsigncode sign \
            -pkcs12 "$AGENT_TOWN_WINDOWS_CERT" \
            -pass "${AGENT_TOWN_WINDOWS_CERT_PASSWORD:-}" \
            -in "$PACKAGE_DIR/Agent Town Demo.exe" \
            -out "$PACKAGE_DIR/Agent Town Demo.signed.exe"
        mv "$PACKAGE_DIR/Agent Town Demo.signed.exe" \
            "$PACKAGE_DIR/Agent Town Demo.exe"
    else
        printf 'warning: no signtool/osslsigncode found; cert not applied\n' >&2
    fi
fi
file "$PACKAGE_DIR/Agent Town Demo.exe" | grep -q "PE32+"
file "$PACKAGE_DIR/backend/python/python.exe" | grep -q "PE32+"
if [ -e "$PACKAGE_DIR/.env" ] || [ -d "$PACKAGE_DIR/backend/data" ]; then
    printf 'Windows package unexpectedly contains private runtime data.\n' >&2
    exit 1
fi
if grep -E '^LLM_API_KEY=.+$' \
    "$PACKAGE_DIR/配置示例.env" >/dev/null 2>&1; then
    printf 'Windows package unexpectedly contains a non-empty API key.\n' >&2
    exit 1
fi

(
    cd "$RELEASE_ROOT"
    zip -q -r "$(basename "$ARCHIVE_PATH")" "$PACKAGE_NAME"
    shasum -a 256 "$(basename "$ARCHIVE_PATH")" \
        >"$(basename "$CHECKSUM_PATH")"
)
unzip -tq "$ARCHIVE_PATH"

printf 'Windows package ready (structurally verified; Windows runtime pending):\n'
printf '  folder: %s\n' "$PACKAGE_DIR"
printf '  archive: %s\n' "$ARCHIVE_PATH"
printf '  checksum: %s\n' "$CHECKSUM_PATH"
