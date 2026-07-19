#!/usr/bin/env python3
"""Run a small local smoke check for the Agent Town demo."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
GAME_DIR = ROOT_DIR / "game"
ROOT_README_FILE = ROOT_DIR / "README.md"
BACKEND_README_FILE = BACKEND_DIR / "README.md"
COMMANDS_FILE = ROOT_DIR / "COMMANDS.md"
V3_ROADMAP_FILE = ROOT_DIR / "docs" / "V3_ROADMAP.md"
MAIN_SCENE = "res://scenes/Main.tscn"
MAIN_SCENE_FILE = GAME_DIR / "scenes" / "Main.tscn"
MAIN_SCRIPT_FILE = GAME_DIR / "scripts" / "main.gd"
TOWN_BACKGROUND_SCENE_FILE = GAME_DIR / "scenes" / "TownBackground.tscn"
TOWN_BACKGROUND_SCRIPT_FILE = GAME_DIR / "scripts" / "town_background.gd"
DIALOG_SCENE_FILE = GAME_DIR / "scenes" / "DialogBox.tscn"
DIALOG_SCRIPT_FILE = GAME_DIR / "scripts" / "dialog_box.gd"
DIALOG_FONT_FILE = GAME_DIR / "assets" / "fonts" / "NotoSansSC-Variable.ttf"
DIALOG_FONT_LICENSE_FILE = GAME_DIR / "assets" / "fonts" / "OFL.txt"
NPC_SCENE_FILE = GAME_DIR / "scenes" / "NPC.tscn"
NPC_SCRIPT_FILE = GAME_DIR / "scripts" / "npc.gd"
PLAYER_SCENE_FILE = GAME_DIR / "scenes" / "Player.tscn"
PLAYER_SCRIPT_FILE = GAME_DIR / "scripts" / "player.gd"
CHARACTER_ASSET_DIR = GAME_DIR / "assets" / "characters"
POLICE_BADGE_FILE = GAME_DIR / "assets" / "ui" / "police_badge.svg"
EXPECTED_CHARACTER_ASSETS = {
    "player.svg",
    "messi.svg",
    "ronaldo.svg",
    "zhou_shen.svg",
    "mei_changsu.svg",
    "zelda.svg",
    "little_knight.svg",
    "hornet.svg",
    "pleasant_goat.svg",
    "lazy_goat.svg",
    "luoluo.svg",
    "doctor_strange.svg",
    "huaihuai.svg",
    "ranran.svg",
}
PROJECT_FILE = GAME_DIR / "project.godot"
KNOWLEDGE_FILE = BACKEND_DIR / "config" / "knowledge_base.json"
NPC_PROFILES_FILE = BACKEND_DIR / "config" / "npc_profiles.json"
NPC_TUNING_FILE = BACKEND_DIR / "config" / "npc_tuning.json"
BACKEND_MAIN_FILE = BACKEND_DIR / "app" / "main.py"
BACKEND_LLM_FILE = BACKEND_DIR / "app" / "llm.py"
BACKEND_LLM_OBSERVABILITY_FILE = BACKEND_DIR / "app" / "llm_observability.py"
BACKEND_NPC_DECISION_FILE = BACKEND_DIR / "app" / "npc_decision.py"
BACKEND_NPC_TUNING_FILE = BACKEND_DIR / "app" / "npc_tuning.py"
BACKEND_BELIEF_FILE = BACKEND_DIR / "app" / "belief.py"
BACKEND_STANCE_FILE = BACKEND_DIR / "app" / "stance.py"
BACKEND_INVARIANCE_FILE = BACKEND_DIR / "app" / "invariance.py"
BACKEND_SIMULATION_FILE = BACKEND_DIR / "app" / "simulation.py"
BACKEND_SIMULATION_METRICS_FILE = BACKEND_DIR / "app" / "simulation_metrics.py"
BACKEND_VOTE_CALIBRATION_FILE = BACKEND_DIR / "app" / "vote_calibration.py"
SIMULATION_SCRIPT_FILE = ROOT_DIR / "scripts" / "simulate_games.py"
LLM_OBSERVABILITY_SCRIPT_FILE = ROOT_DIR / "scripts" / "summarize_llm_observability.py"
BACKEND_VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
MIN_KNOWLEDGE_COUNT = 100


def main() -> int:
    checks = [
        check_release_docs,
        check_json_files,
        check_backend_compiles,
        check_llm_adapter,
        check_npc_decision_contracts,
        check_npc_tuning,
        check_headless_simulation,
        check_backend_search,
        check_resident_chat,
        check_wolf_game_start,
        check_godot_ui_layout,
        check_godot_loads,
    ]

    print("Agent Town smoke check")
    print("======================")

    for check in checks:
        try:
            check()
        except SmokeCheckError as exc:
            print(f"[FAIL] {exc}")
            return 1

    print("[OK] Smoke check passed.")
    return 0


def check_release_docs() -> None:
    required_files = [ROOT_README_FILE, BACKEND_README_FILE, COMMANDS_FILE, V3_ROADMAP_FILE]
    missing_files = [str(path.relative_to(ROOT_DIR)) for path in required_files if not path.is_file()]
    if missing_files:
        raise SmokeCheckError("release docs missing: " + ", ".join(missing_files))

    root_readme = ROOT_README_FILE.read_text(encoding="utf-8")
    backend_readme = BACKEND_README_FILE.read_text(encoding="utf-8")
    commands = COMMANDS_FILE.read_text(encoding="utf-8")
    roadmap = V3_ROADMAP_FILE.read_text(encoding="utf-8")
    release_url = "https://github.com/KEswy/agent-town-demo-v2.0"

    if not root_readme.startswith("# Agent Town Demo V3") or "V3.1-M" not in root_readme:
        raise SmokeCheckError("root README must identify the active V3.1-M iteration")
    if release_url not in root_readme or release_url not in backend_readme:
        raise SmokeCheckError("V2.0 repository URL must stay synchronized across README files")
    if "docs/V3_ROADMAP.md" not in root_readme or "../docs/V3_ROADMAP.md" not in backend_readme:
        raise SmokeCheckError("README files must link to the standalone V3 roadmap")
    if "/Users/" in commands:
        raise SmokeCheckError("COMMANDS.md must not contain a developer-specific absolute path")
    if "# Agent Town V3 改进与开发路线表" not in roadmap:
        raise SmokeCheckError("V3 roadmap title is missing")
    if roadmap.count("| M") < 24:
        raise SmokeCheckError("V3 roadmap must retain at least 24 concrete development items")

    if "V3.1-M" not in backend_readme or "V3.1-M" not in roadmap:
        raise SmokeCheckError("V3.1-M status must stay synchronized across development docs")
    if "scripts/simulate_games.py" not in commands:
        raise SmokeCheckError("COMMANDS.md must document the V3 batch simulator")
    if "agent_town_metrics.v3" not in commands:
        raise SmokeCheckError("COMMANDS.md must document the M02 metrics schema")
    if (
        "belief_state.v2" not in commands
        or "0.75" not in commands
        or "--no-belief-trace" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document M03 shadow belief handling")
    if (
        "stance_summary.v1" not in commands
        or "--no-stance-trace" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document M04 shadow stance handling")
    if (
        "public_speech_continuity.v1" not in commands
        or "public_speech_plan.v3" not in commands
        or "speech_continuity_metrics.v1" not in commands
        or "[CONTINUITY]" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document M04-B controlled speech")
    if (
        "hidden_info_invariance.v1" not in commands
        or "hidden_info_projection.v1" not in commands
        or "M06-A" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document the M06-A invariance matrix")
    if (
        "hidden_info_authorization.v1" not in commands
        or "role_scoped_private_npc" not in commands
        or "M06-B" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document the M06-B authorization matrix")
    if (
        "llm_observation.v1" not in commands
        or "llm_observability_summary.v1" not in commands
        or "scripts/summarize_llm_observability.py" not in commands
        or "M09-A" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document redacted M09-A observability")
    if (
        "vote_probability_trace.v2" not in commands
        or "vote_probability_summary.v2" not in commands
        or "good_exile_calibration.v1" not in commands
        or "--no-vote-calibration-trace" not in commands
        or "[VOTE-CALIBRATION]" not in commands
        or "M15-B" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document M15-B vote calibration")
    if (
        "witch_directive.v1" not in commands
        or "99%" not in commands
        or "[BALANCE]" not in commands
        or "[WITCH]" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document V3.1-L witch diagnostics")
    if (
        "fake_seer_campaign.v1" not in commands
        or "fake_seer_check_mix.v1" not in commands
        or "[SEER]" not in commands
        or "agent_town_simulation.v10" not in commands
    ):
        raise SmokeCheckError("COMMANDS.md must document V3.1-M seer diagnostics")

    print("[OK] V3.1-M README, commands, and roadmap status are synchronized.")


def check_json_files() -> None:
    knowledge_items = load_json_list(KNOWLEDGE_FILE, "knowledge base")
    npc_profiles = load_json_list(NPC_PROFILES_FILE, "NPC profiles")
    expected_trigger_profiles = {
        "梅西", "C罗", "周深", "梅长苏", "塞尔达", "小骑士",
        "大黄蜂", "喜羊羊", "懒羊羊", "洛洛", "奇异博士",
    }
    expected_resident_profiles = {"坏坏", "然然"}
    expected_profile_names = {
        "Guide", "Archivist", *expected_trigger_profiles, *expected_resident_profiles,
    }
    trigger_profile_names = set()
    trigger_egg_ids = set()
    role_reveal_profiles = set()

    if len(knowledge_items) < MIN_KNOWLEDGE_COUNT:
        raise SmokeCheckError(
            f"knowledge base has {len(knowledge_items)} items, expected at least {MIN_KNOWLEDGE_COUNT}"
        )

    titles = [str(item.get("title", "")).strip() for item in knowledge_items]
    duplicate_titles = sorted({title for title in titles if titles.count(title) > 1})
    if duplicate_titles:
        raise SmokeCheckError("knowledge base has duplicate titles: " + ", ".join(duplicate_titles))

    for index, item in enumerate(knowledge_items, start=1):
        require_keys(item, {"npc_name", "title", "content", "keywords"}, f"knowledge item #{index}")
        if not isinstance(item["keywords"], list):
            raise SmokeCheckError(f"knowledge item #{index} keywords must be a list")

    profile_names = [str(item.get("npc_name", "")) for item in npc_profiles]
    if len(profile_names) != len(set(profile_names)):
        raise SmokeCheckError("NPC profiles contain duplicate names")
    if set(profile_names) != expected_profile_names:
        raise SmokeCheckError("NPC profiles must contain the two town residents and eleven wolf-game NPCs")
    resident_profiles = {
        str(item.get("npc_name", "")): item
        for item in npc_profiles
        if item.get("npc_name") in expected_resident_profiles
    }
    resident_visual_markers = {
        "坏坏": ("小恐龙", "尾巴"),
        "然然": ("熊猫", "邮差包"),
    }
    for resident_name, markers in resident_visual_markers.items():
        resident = resident_profiles[resident_name]
        resident_text = json.dumps(resident, ensure_ascii=False)
        if not all(marker in resident_text for marker in markers):
            raise SmokeCheckError(
                f"resident NPC profile does not match the new visual identity: {resident_name}"
            )

    for index, item in enumerate(npc_profiles, start=1):
        require_keys(item, {"npc_name", "role", "personality", "knowledge"}, f"NPC profile #{index}")
        if not isinstance(item["knowledge"], list):
            raise SmokeCheckError(f"NPC profile #{index} knowledge must be a list")
        if item["npc_name"] in expected_trigger_profiles:
            require_keys(
                item,
                {"speech_style", "catchphrases", "easter_eggs", "trigger_easter_eggs"},
                f"wolf-game NPC profile #{index}",
            )
            if not item["speech_style"] or not item["catchphrases"] or not item["easter_eggs"]:
                raise SmokeCheckError(f"wolf-game NPC profile #{index} voice data must not be empty")
            trigger_eggs = item["trigger_easter_eggs"]
            if not isinstance(trigger_eggs, list) or len(trigger_eggs) != 1:
                raise SmokeCheckError(f"wolf-game NPC profile #{index} must have one trigger easter egg")
            trigger_egg = trigger_eggs[0]
            require_keys(
                trigger_egg,
                {"egg_id", "triggers", "reply", "repeat_reply"},
                f"trigger easter egg for {item['npc_name']}",
            )
            if (
                not trigger_egg["egg_id"]
                or not isinstance(trigger_egg["triggers"], list)
                or not trigger_egg["triggers"]
                or not trigger_egg["reply"]
                or not trigger_egg["repeat_reply"]
            ):
                raise SmokeCheckError(f"trigger easter egg for {item['npc_name']} is incomplete")
            if trigger_egg["egg_id"] in trigger_egg_ids:
                raise SmokeCheckError(f"duplicate trigger easter egg id: {trigger_egg['egg_id']}")
            trigger_profile_names.add(item["npc_name"])
            trigger_egg_ids.add(trigger_egg["egg_id"])
            if bool(trigger_egg.get("reveal_self_role", False)):
                role_reveal_profiles.add(item["npc_name"])
                if "{role}" not in trigger_egg["reply"]:
                    raise SmokeCheckError("role-reveal easter egg must contain the {role} placeholder")
        elif item["npc_name"] in expected_resident_profiles:
            require_keys(
                item,
                {"speech_style", "catchphrases", "easter_eggs", "trigger_easter_eggs", "use_llm_for_chat"},
                f"resident NPC profile #{index}",
            )
            if (
                not item["speech_style"]
                or not item["catchphrases"]
                or not item["easter_eggs"]
                or item["trigger_easter_eggs"] != []
                or item["use_llm_for_chat"] is not True
            ):
                raise SmokeCheckError(f"resident NPC profile #{index} chat data is incomplete")

    if trigger_profile_names != expected_trigger_profiles:
        raise SmokeCheckError("trigger easter eggs must cover all eleven wolf-game NPCs")
    if role_reveal_profiles != {"梅长苏"}:
        raise SmokeCheckError("only 梅长苏 may reveal a real role through a trigger easter egg")

    for path in [
        KNOWLEDGE_FILE,
        NPC_PROFILES_FILE,
        NPC_TUNING_FILE,
        BACKEND_MAIN_FILE,
        BACKEND_LLM_FILE,
        BACKEND_LLM_OBSERVABILITY_FILE,
        BACKEND_NPC_DECISION_FILE,
        BACKEND_NPC_TUNING_FILE,
        BACKEND_BELIEF_FILE,
        BACKEND_STANCE_FILE,
        BACKEND_INVARIANCE_FILE,
        BACKEND_SIMULATION_FILE,
        BACKEND_SIMULATION_METRICS_FILE,
        BACKEND_VOTE_CALIBRATION_FILE,
        SIMULATION_SCRIPT_FILE,
        LLM_OBSERVABILITY_SCRIPT_FILE,
    ]:
        if "\ufffd" in path.read_text(encoding="utf-8"):
            raise SmokeCheckError(f"Unicode replacement character found in {path.relative_to(ROOT_DIR)}")

    print(f"[OK] JSON config valid: {len(knowledge_items)} knowledge items, {len(npc_profiles)} NPC profiles.")


def check_backend_compiles() -> None:
    run_command(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(BACKEND_MAIN_FILE),
            str(BACKEND_LLM_FILE),
            str(BACKEND_LLM_OBSERVABILITY_FILE),
            str(BACKEND_NPC_DECISION_FILE),
            str(BACKEND_NPC_TUNING_FILE),
            str(BACKEND_BELIEF_FILE),
            str(BACKEND_STANCE_FILE),
            str(BACKEND_INVARIANCE_FILE),
            str(BACKEND_SIMULATION_FILE),
            str(BACKEND_SIMULATION_METRICS_FILE),
            str(BACKEND_VOTE_CALIBRATION_FILE),
            str(SIMULATION_SCRIPT_FILE),
            str(LLM_OBSERVABILITY_SCRIPT_FILE),
        ],
        cwd=ROOT_DIR,
        fail_message="backend Python files failed to compile",
    )
    print("[OK] Backend Python files compile.")


def check_llm_adapter() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = r'''
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from app.llm import LLMClient, LLMSettings
from app.llm_observability import (
    LLM_OBSERVABILITY_MODE,
    LLM_OBSERVABILITY_SUMMARY_VERSION,
    LLM_OBSERVATION_SCHEMA_VERSION,
    LLMObservationError,
    LLMObservationRecorder,
    build_validation_observation,
    normalize_observation_event,
    summarize_observation_events,
    summarize_observation_file,
)

api_key_marker = "TEST_API_KEY_MARKER_7D2F"
system_marker = "SECRET_SYSTEM_PROMPT_MARKER_8A31"
context_marker = "SECRET_CONTEXT_MARKER_4C67"
response_marker = "SECRET_RESPONSE_MARKER_9B20"
fallback_marker = "SECRET_FALLBACK_MARKER_5E14"
captured_events = []
fallback = fallback_marker

disabled_client = LLMClient(
    LLMSettings(enabled=False),
    event_sink=captured_events.append,
)
disabled_result = disabled_client.generate_json_text(
    system_marker,
    {"task": "resident_chat", "query": context_marker},
    fallback,
)
if disabled_result.used_llm or disabled_result.text != fallback:
    raise SystemExit("disabled LLM should use the rule fallback")

mock_client = LLMClient(
    LLMSettings(enabled=True, provider="mock"),
    event_sink=captured_events.append,
)
mock_result = mock_client.generate_json_text(
    system_marker,
    {"task": "resident_chat", "query": context_marker},
    fallback,
)
if mock_result.used_llm or mock_result.text != fallback:
    raise SystemExit("mock provider should stay deterministic and key-free")

def success_handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != f"Bearer {api_key_marker}":
        raise AssertionError("LLM request should use bearer authentication")
    payload = json.loads(request.content.decode("utf-8"))
    if payload.get("model") != "cheap-model":
        raise AssertionError("LLM request should include the configured model")
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": (
                            f'{{"text":"{response_marker}","intent":"observe",'
                            '"evidence_ids":[]}'
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 4,
                "total_tokens": 15,
            },
        },
    )

settings = LLMSettings(
    enabled=True,
    provider="openai_compatible",
    base_url="https://example.invalid/v1",
    api_key=api_key_marker,
    model="cheap-model",
    max_retries=0,
    retry_delay_seconds=0,
)
client = LLMClient(
    settings,
    transport=httpx.MockTransport(success_handler),
    event_sink=captured_events.append,
)
legal_context = {"task": "resident_chat", "query": context_marker}
result = client.generate_json_text(system_marker, legal_context, fallback)
if not result.used_llm or result.text != response_marker:
    raise SystemExit("OpenAI-compatible adapter should parse JSON text")
structured_result = client.generate_json_object(
    system_marker,
    legal_context,
    {"intent": "fallback"},
)
if (
    not structured_result.used_llm
    or structured_result.data.get("intent") != "observe"
    or structured_result.data.get("evidence_ids") != []
):
    raise SystemExit("LLM adapter should preserve a complete structured JSON object")
status = client.status()
if "api_key" in status or api_key_marker in json.dumps(status):
    raise SystemExit("LLM status must never expose the API key")

def deepseek_handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))
    if payload.get("thinking") != {"type": "disabled"}:
        raise AssertionError("DeepSeek rewrite requests should disable thinking mode")
    if payload.get("response_format") != {"type": "json_object"}:
        raise AssertionError("DeepSeek requests should enforce JSON object output")
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": '{"text":"DeepSeek JSON 回答。"}'}}]},
    )

deepseek_settings = LLMSettings(
    enabled=True,
    provider="deepseek",
    base_url="https://api.deepseek.com",
    api_key=api_key_marker,
    model="deepseek-v4-flash",
    max_retries=0,
    retry_delay_seconds=0,
)
deepseek_client = LLMClient(
    deepseek_settings,
    transport=httpx.MockTransport(deepseek_handler),
    event_sink=captured_events.append,
)
deepseek_result = deepseek_client.generate_json_text(
    system_marker,
    {"task": "resident_chat"},
    fallback,
)
if not deepseek_result.used_llm or deepseek_result.text != "DeepSeek JSON 回答。":
    raise SystemExit("DeepSeek adapter should use non-thinking JSON mode")

flaky_attempts = {"count": 0}

def flaky_handler(_request: httpx.Request) -> httpx.Response:
    flaky_attempts["count"] += 1
    if flaky_attempts["count"] == 1:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "not-json"}}],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 1,
                    "total_tokens": 4,
                },
            },
        )
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": '{"text":"重试成功。"}'}}],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 2,
                "total_tokens": 7,
            },
        },
    )

retry_settings = LLMSettings(
    enabled=True,
    provider="deepseek",
    base_url="https://api.deepseek.com",
    api_key=api_key_marker,
    model="deepseek-v4-flash",
    max_retries=1,
    retry_delay_seconds=0,
)
retry_client = LLMClient(
    retry_settings,
    transport=httpx.MockTransport(flaky_handler),
    event_sink=captured_events.append,
)
retry_result = retry_client.generate_json_text(
    system_marker,
    {"task": "rewrite_public_speech"},
    fallback,
)
if not retry_result.used_llm or retry_result.text != "重试成功。" or flaky_attempts["count"] != 2:
    raise SystemExit("invalid JSON should retry once before using the rule fallback")

def malformed_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "not-json"}}],
            "usage": {
                "prompt_tokens": 6,
                "completion_tokens": 1,
                "total_tokens": 7,
            },
        },
    )

malformed_client = LLMClient(
    settings,
    transport=httpx.MockTransport(malformed_handler),
    event_sink=captured_events.append,
)
malformed_result = malformed_client.generate_json_text(
    system_marker,
    {"task": "public_speech"},
    fallback,
)
if malformed_result.used_llm or malformed_result.text != fallback:
    raise SystemExit("invalid LLM JSON should use the rule fallback")

def replacement_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": '{"text":"bad�text"}'}}]},
    )

replacement_client = LLMClient(
    settings,
    transport=httpx.MockTransport(replacement_handler),
    event_sink=captured_events.append,
)
replacement_result = replacement_client.generate_json_object(
    system_marker,
    {"task": "public_speech_voice_prefix"},
    {"text": fallback},
)
if replacement_result.used_llm or replacement_result.data != {"text": fallback}:
    raise SystemExit("structured LLM JSON with replacement characters should use the fallback")

def limited_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(429, json={"error": {"message": "rate limited"}})

limited_client = LLMClient(
    settings,
    transport=httpx.MockTransport(limited_handler),
    event_sink=captured_events.append,
)
limited_result = limited_client.generate_json_text(
    system_marker,
    {"task": "rewrite_private_reply"},
    fallback,
)
if limited_result.used_llm or limited_result.text != fallback:
    raise SystemExit("LLM rate limits should use the rule fallback")

expected_event_fields = {
    "schema_version",
    "recorded_at",
    "event_type",
    "task",
    "operation",
    "provider",
    "model",
    "outcome",
    "attempt_count",
    "retry_count",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "fallback_category",
    "rejection_category_counts",
}
if len(captured_events) != 9:
    raise SystemExit(f"each LLM adapter result should emit one event: {len(captured_events)}")
if any(set(event) != expected_event_fields for event in captured_events):
    raise SystemExit("request observations must use the exact redacted v1 fields")
serialized_events = json.dumps(captured_events, ensure_ascii=False)
for secret_marker in (
    api_key_marker,
    system_marker,
    context_marker,
    response_marker,
    fallback_marker,
):
    if secret_marker in serialized_events:
        raise SystemExit("redacted observations must not retain request or response content")

event_by_key = {
    (event["task"], event["outcome"], event["fallback_category"]): event
    for event in captured_events
}
if event_by_key[("rewrite_public_speech", "success", "")]["attempt_count"] != 2:
    raise SystemExit("retry success observations must preserve the attempt count")
if event_by_key[("rewrite_public_speech", "success", "")]["retry_count"] != 1:
    raise SystemExit("retry success observations must preserve the retry count")
if event_by_key[("rewrite_public_speech", "success", "")]["total_tokens"] != 11:
    raise SystemExit("retry observations should add provider token usage across attempts")
for expected_key in (
    ("resident_chat", "fallback", "disabled"),
    ("resident_chat", "fallback", "mock"),
    ("public_speech", "fallback", "invalid_json"),
    ("public_speech_voice_prefix", "fallback", "invalid_payload"),
    ("rewrite_private_reply", "fallback", "rate_limit"),
):
    if expected_key not in event_by_key:
        raise SystemExit(f"missing classified request observation: {expected_key}")
token_events = [event for event in captured_events if event["total_tokens"] is not None]
if len(token_events) != 4 or sum(event["total_tokens"] for event in token_events) != 48:
    raise SystemExit("provider token usage should be captured when available")

validation_events = [
    build_validation_observation(
        task="public_speech",
        provider="deepseek",
        model="deepseek-v4-flash",
        outcome="recovered",
        attempts=[
            {"passed": False, "rejection_reason": "schema invalid: SECRET_RAW_ATTEMPT"},
            {"passed": True, "rejection_reason": ""},
        ],
    ),
    build_validation_observation(
        task="rewrite_private_reply",
        provider="deepseek",
        model="deepseek-v4-flash",
        outcome="fallback",
        attempts=[
            {"passed": False, "rejection_reason": "hidden private role disclosure"},
        ],
    ),
]
if "SECRET_RAW_ATTEMPT" in json.dumps(validation_events, ensure_ascii=False):
    raise SystemExit("validation observations must retain only rejection categories")
summary = summarize_observation_events([*captured_events, *validation_events])
if (
    summary["schema_version"] != LLM_OBSERVABILITY_SUMMARY_VERSION
    or summary["event_schema_version"] != LLM_OBSERVATION_SCHEMA_VERSION
    or summary["mode"] != LLM_OBSERVABILITY_MODE
    or summary["event_count"] != 11
    or summary["request_count"] != 9
    or summary["request_success_count"] != 4
    or summary["request_fallback_count"] != 5
    or summary["validation_recovered_count"] != 1
    or summary["validation_fallback_count"] != 1
    or summary["retry_count"] != 2
    or summary["token_sample_count"] != 4
    or summary["total_tokens"] != 48
):
    raise SystemExit(f"redacted observability summary is incomplete: {summary}")
if summary["rejection_category_counts"] != {
    "hidden_information": 1,
    "schema_invalid": 1,
}:
    raise SystemExit("semantic rejection categories should aggregate without raw reasons")
if "resident_chat" not in summary["by_task"]:
    raise SystemExit("observability summary should group metrics by task")
if "deepseek/deepseek-v4-flash" not in summary["by_provider_model"]:
    raise SystemExit("observability summary should group metrics by provider and model")

try:
    normalize_observation_event({**captured_events[0], "secret": context_marker})
except LLMObservationError:
    pass
else:
    raise SystemExit("the observation schema must reject undeclared fields")

with tempfile.TemporaryDirectory(prefix="agent-town-m09a-") as temp_dir:
    observation_path = Path(temp_dir) / "observations.jsonl"
    recorder = LLMObservationRecorder(observation_path)
    for event in [*captured_events, *validation_events]:
        recorder.record_event(event)
    recorder.record_event({**captured_events[0], "secret": context_marker})
    with observation_path.open("a", encoding="utf-8") as observation_file:
        observation_file.write("not-json\n")
    file_summary = summarize_observation_file(observation_path)
    if file_summary["event_count"] != 11 or file_summary["invalid_event_count"] != 1:
        raise SystemExit("file summary should skip and count malformed JSONL rows")
    cli_script = Path.cwd().parent / "scripts" / "summarize_llm_observability.py"
    cli_result = subprocess.run(
        [sys.executable, str(cli_script), "--input", str(observation_path), "--compact"],
        check=True,
        capture_output=True,
        text=True,
    )
    cli_summary = json.loads(cli_result.stdout)
    if cli_summary["schema_version"] != LLM_OBSERVABILITY_SUMMARY_VERSION:
        raise SystemExit("M09-A summary CLI should print the versioned summary")

print("LLM adapter and redacted observability smoke test passed")
'''
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="LLM adapter smoke test failed",
    )
    print("[OK] LLM adapter and redacted request/validation observability work.")


def check_npc_decision_contracts() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = r'''
from copy import deepcopy

from pydantic import ValidationError

from app.main import normalize_public_speech_plan_payload
from app.npc_decision import (
    NPCDecisionContextV1,
    PublicSpeechContinuityV1,
    PublicSpeechDecisionV1,
    PublicSpeechPlanV2,
    PublicSpeechPlanV3,
    upgrade_public_speech_decision_v1,
    validate_public_speech_continuity,
    validate_public_speech_decision,
    validate_public_speech_plan,
)

context_payload = {
    "schema_version": "npc_decision_context.v1",
    "task": "public_speech",
    "day": 1,
    "phase": "DAY_MEETING",
    "actor": {
        "id": 2,
        "name": "梅西",
        "role": "seer",
        "faction": "good",
        "personality": {"logic": 0.8},
        "speech_style": "简洁",
        "catchphrases": ["先看逻辑"],
    },
    "public_logs": [{"id": "public-log:1", "content": "1号已经发言。"}],
    "legal_knowledge": [
        {
            "id": "knowledge:self-role",
            "title": "自身身份",
            "content": "你是预言家。",
            "visibility": "private",
        }
    ],
    "private_memory": [
        {
            "id": "memory:2:1",
            "title": "私有记忆",
            "content": "昨晚查验了 3 号。",
            "visibility": "private",
        }
    ],
    "evidence": [
        {
            "id": "evidence:public:1",
            "title": "公开发言",
            "content": "3号公开表达过矛盾观点。",
            "visibility": "public",
        },
        {
            "id": "evidence:private:1",
            "title": "私有线索",
            "content": "不得公开引用。",
            "visibility": "private",
        },
    ],
    "decision_signals": [
        {
            "id": "signal:sheriff_signup:1:3",
            "kind": "sheriff_signup",
            "category": "fact",
            "day": 1,
            "phase": "SHERIFF_SIGNUP",
            "summary": "第1天，3号C罗报名竞选警长。",
            "actor_id": 3,
        },
        {
            "id": "signal:low_information:1:DAY_MEETING:3",
            "kind": "low_information_speech",
            "category": "assessment",
            "day": 1,
            "phase": "DAY_MEETING",
            "summary": "第1天，3号C罗的发言没有给出具体目标。",
            "actor_id": 3,
        },
        {
            "id": "signal:sheriff_withdraw:1:4",
            "kind": "sheriff_withdraw",
            "category": "fact",
            "day": 1,
            "phase": "SHERIFF_WITHDRAWAL",
            "summary": "第1天，4号周深在警长竞选中退水。",
            "actor_id": 4,
        },
    ],
    "legal_targets": [
        {"id": 3, "name": "C罗"},
        {"id": 4, "name": "周深"},
    ],
    "claim_options": [
        {
            "id": "claim:seer-check:3",
            "summary": "公布 3 号查验",
            "required": False,
            "facts": [
                {"claim_type": "role", "claimed_role": "seer"},
                {
                    "claim_type": "seer_check",
                    "claimed_role": "seer",
                    "target_id": 3,
                    "result": "werewolf",
                },
            ],
        }
    ],
    "allowed_intents": ["observe", "pressure", "reveal"],
}
context = NPCDecisionContextV1.model_validate(context_payload)
valid_payload = {
    "schema_version": "public_speech.v1",
    "intent": "pressure",
    "target_id": 3,
    "claim_option_ids": [],
    "evidence_ids": ["evidence:public:1"],
    "signal_ids": ["signal:sheriff_signup:1:3"],
}
valid_decision = PublicSpeechDecisionV1.model_validate(valid_payload)
context_before_validation = context.model_dump_json()
if validate_public_speech_decision(context, valid_decision):
    raise SystemExit("a valid structured public-speech decision should pass")
if context.model_dump_json() != context_before_validation:
    raise SystemExit("decision validation must not mutate its rule context")

two_signal_payload = deepcopy(valid_payload)
two_signal_payload["evidence_ids"] = []
two_signal_payload["signal_ids"] = [
    "signal:sheriff_signup:1:3",
    "signal:low_information:1:DAY_MEETING:3",
]
two_signal_decision = PublicSpeechDecisionV1.model_validate(two_signal_payload)
if validate_public_speech_decision(context, two_signal_decision):
    raise SystemExit("exactly two legal public signals should be accepted")

for label, updates, expected_error in [
    ("target", {"target_id": 99}, "target_not_allowed"),
    (
        "claim option",
        {"claim_option_ids": ["claim:forged"]},
        "claim_option_not_allowed",
    ),
    (
        "private evidence",
        {"evidence_ids": ["evidence:private:1"]},
        "private_evidence_not_publishable",
    ),
    (
        "unknown evidence",
        {"evidence_ids": ["evidence:missing"]},
        "evidence_not_allowed",
    ),
    (
        "unknown signal",
        {"signal_ids": ["signal:missing"]},
        "signal_not_allowed",
    ),
    (
        "duplicate signal",
        {"signal_ids": ["signal:sheriff_signup:1:3"] * 2},
        "duplicate_signal_id",
    ),
    (
        "unrelated signal",
        {"signal_ids": ["signal:sheriff_withdraw:1:4"]},
        "signal_target_mismatch",
    ),
    (
        "missing decision basis",
        {"evidence_ids": [], "signal_ids": []},
        "decision_basis_required",
    ),
    (
        "observe without target",
        {
            "intent": "observe",
            "target_id": None,
            "evidence_ids": ["evidence:public:1"],
            "signal_ids": [],
        },
        "target_required",
    ),
]:
    payload = deepcopy(valid_payload)
    payload.update(updates)
    decision = PublicSpeechDecisionV1.model_validate(payload)
    errors = validate_public_speech_decision(context, decision)
    if not any(error.startswith(expected_error) for error in errors):
        raise SystemExit(f"illegal {label} should be rejected: {errors}")

for label, updates in [
    ("extra text field", {"text": "策略阶段不得生成台词。"}),
    ("extra field", {"unexpected": True}),
    ("coerced target id", {"target_id": "3"}),
    ("unknown intent", {"intent": "invent"}),
    (
        "more than two signals",
        {
            "signal_ids": [
                "signal:sheriff_signup:1:3",
                "signal:low_information:1:DAY_MEETING:3",
                "signal:sheriff_withdraw:1:4",
            ]
        },
    ),
]:
    payload = deepcopy(valid_payload)
    payload.update(updates)
    try:
        PublicSpeechDecisionV1.model_validate(payload)
    except (ValidationError, ValueError):
        pass
    else:
        raise SystemExit(f"strict public-speech schema should reject {label}")

duplicate_signal_context_payload = deepcopy(context_payload)
duplicate_signal_context_payload["decision_signals"].append(
    deepcopy(duplicate_signal_context_payload["decision_signals"][0])
)
duplicate_signal_context = NPCDecisionContextV1.model_validate(
    duplicate_signal_context_payload
)
duplicate_context_errors = validate_public_speech_decision(
    duplicate_signal_context,
    valid_decision,
)
if not any(
    error.startswith("duplicate_context_signal_id")
    for error in duplicate_context_errors
):
    raise SystemExit("duplicate rule-context signal ids should be rejected")

valid_v2_payload = {
    "schema_version": "public_speech_plan.v2",
    "intent": "pressure",
    "primary_target_id": 3,
    "secondary_target_id": 4,
    "stance": "oppose",
    "stance_target_id": 3,
    "confidence": 76,
    "signal_read": "raises_suspicion",
    "question": {"target_id": 3, "topic": "action_motive"},
    "verification": {"target_id": 4, "criterion": "vote_alignment"},
    "provisional_vote_target_id": 3,
    "tactic": "direct_pressure",
    "claim_option_ids": [],
    "evidence_ids": ["evidence:public:1"],
    "signal_ids": ["signal:sheriff_signup:1:3"],
}
valid_v2_plan = PublicSpeechPlanV2.model_validate(valid_v2_payload)
context_before_v2_validation = context.model_dump_json()
if validate_public_speech_plan(context, valid_v2_plan):
    raise SystemExit("a complete legal V2 public-speech plan should pass")
if context.model_dump_json() != context_before_v2_validation:
    raise SystemExit("V2 plan validation must not mutate its rule context")

continuity_payload = {
    "schema_version": "public_speech_continuity.v1",
    "stance_schema_version": "stance_summary.v1",
    "actor_id": 2,
    "day": 1,
    "phase": "DAY_MEETING",
    "trusted_target_ids": [],
    "primary_suspect_id": 3,
    "secondary_suspect_id": 4,
    "provisional_vote_target_id": 3,
    "verification_target_id": 4,
    "verification_condition": "vote_alignment",
    "confidence": 0.76,
    "basis_evidence_ids": ["belief:public:1"],
    "previous_position_day": 1,
    "new_public_signal_ids": ["signal:sheriff_withdraw:1:4"],
    "variance_allowed": False,
    "mandatory_response": False,
}
continuity = PublicSpeechContinuityV1.model_validate(continuity_payload)
valid_v3_plan = PublicSpeechPlanV3.model_validate(
    {
        **deepcopy(valid_v2_payload),
        "schema_version": "public_speech_plan.v3",
        "continuity_reason": "stance_aligned",
        "continuity_signal_ids": [],
    }
)
if validate_public_speech_continuity(context, continuity, valid_v3_plan):
    raise SystemExit("an aligned V3 plan should consume its legal stance card")

new_signal_plan = PublicSpeechPlanV3.model_validate(
    {
        **deepcopy(valid_v2_payload),
        "schema_version": "public_speech_plan.v3",
        "primary_target_id": 4,
        "secondary_target_id": 3,
        "stance_target_id": 4,
        "question": {"target_id": 4, "topic": "action_motive"},
        "verification": {"target_id": 4, "criterion": "vote_alignment"},
        "provisional_vote_target_id": 4,
        "signal_ids": ["signal:sheriff_withdraw:1:4"],
        "continuity_reason": "new_public_evidence",
        "continuity_signal_ids": ["signal:sheriff_withdraw:1:4"],
    }
)
if (
    validate_public_speech_plan(context, new_signal_plan)
    or validate_public_speech_continuity(context, continuity, new_signal_plan)
):
    raise SystemExit("a stance change tied to one selected new public signal should pass")

unexplained_v3_plan = new_signal_plan.model_copy(
    update={
        "continuity_reason": "stance_aligned",
        "continuity_signal_ids": [],
    }
)
if not any(
    error.startswith("continuity_unexplained_change")
    for error in validate_public_speech_continuity(
        context,
        continuity,
        unexplained_v3_plan,
    )
):
    raise SystemExit("a V3 stance change without evidence or variance must fail")

variance_plan = new_signal_plan.model_copy(
    update={
        "continuity_reason": "deterministic_variance",
        "continuity_signal_ids": [],
    }
)
if not any(
    error.startswith("continuity_variance_not_allowed")
    for error in validate_public_speech_continuity(context, continuity, variance_plan)
):
    raise SystemExit("an unapproved variance reason must not bypass continuity")
variance_continuity = continuity.model_copy(update={"variance_allowed": True})
if validate_public_speech_continuity(context, variance_continuity, variance_plan):
    raise SystemExit("a deterministic actor variance gate should allow a legal divergence")

mandatory_continuity = continuity.model_copy(update={"mandatory_response": True})
mandatory_plan = valid_v3_plan.model_copy(
    update={"continuity_reason": "mandatory_rule_response"}
)
if validate_public_speech_continuity(context, mandatory_continuity, mandatory_plan):
    raise SystemExit("a Python-required response should carry its explicit continuity reason")

authorized_claim_plan = PublicSpeechPlanV3.model_validate(
    {
        **deepcopy(valid_v2_payload),
        "schema_version": "public_speech_plan.v3",
        "intent": "reveal",
        "secondary_target_id": None,
        "verification": {"target_id": 3, "criterion": "claim_consistency"},
        "tactic": "role_reveal",
        "claim_option_ids": ["claim:seer-check:3"],
        "continuity_reason": "authorized_claim",
        "continuity_signal_ids": [],
    }
)
if (
    validate_public_speech_plan(context, authorized_claim_plan)
    or validate_public_speech_continuity(
        context,
        continuity,
        authorized_claim_plan,
    )
):
    raise SystemExit("an allowlisted role/check bundle should use authorized_claim")

if normalize_public_speech_plan_payload(deepcopy(valid_v2_payload)) != valid_v2_payload:
    raise SystemExit("a normal flat V2 plan must pass through normalization unchanged")

legacy_fields_wrapper = {
    "schema_version": "public_speech_plan.v2",
    "fields": {
        key: deepcopy(value)
        for key, value in valid_v2_payload.items()
        if key != "schema_version"
    },
}
normalized_wrapper = normalize_public_speech_plan_payload(
    deepcopy(legacy_fields_wrapper)
)
if normalized_wrapper != valid_v2_payload:
    raise SystemExit("the exact legacy fields wrapper should normalize to a flat V2 plan")
PublicSpeechPlanV2.model_validate(normalized_wrapper)

for label, invalid_wrapper in [
    (
        "extra outer field",
        {**deepcopy(legacy_fields_wrapper), "text": "must stay forbidden"},
    ),
    (
        "extra inner field",
        {
            **deepcopy(legacy_fields_wrapper),
            "fields": {
                **deepcopy(legacy_fields_wrapper["fields"]),
                "unexpected": "must stay forbidden",
            },
        },
    ),
]:
    normalized_invalid_wrapper = normalize_public_speech_plan_payload(
        invalid_wrapper
    )
    try:
        PublicSpeechPlanV2.model_validate(normalized_invalid_wrapper)
    except (ValidationError, ValueError):
        pass
    else:
        raise SystemExit(f"legacy wrapper normalization must not hide an {label}")

upgraded_v1_plan = upgrade_public_speech_decision_v1(
    context,
    valid_decision,
    confidence=63,
)
if (
    upgraded_v1_plan.schema_version != "public_speech_plan.v2"
    or upgraded_v1_plan.primary_target_id != 3
    or upgraded_v1_plan.provisional_vote_target_id != 3
    or upgraded_v1_plan.confidence != 63
    or validate_public_speech_plan(context, upgraded_v1_plan)
):
    raise SystemExit("a valid V1 decision should upgrade into a legal complete V2 plan")

multi_check_context_payload = deepcopy(context_payload)
multi_check_context_payload["claim_options"][0]["facts"].append(
    {
        "claim_type": "seer_check",
        "claimed_role": "seer",
        "target_id": 4,
        "result": "good",
    }
)
multi_check_context = NPCDecisionContextV1.model_validate(
    multi_check_context_payload
)
multi_check_decision = PublicSpeechDecisionV1.model_validate(
    {
        "schema_version": "public_speech.v1",
        "intent": "reveal",
        "target_id": 4,
        "claim_option_ids": ["claim:seer-check:3"],
        "evidence_ids": [],
        "signal_ids": [],
    }
)
multi_check_plan = upgrade_public_speech_decision_v1(
    multi_check_context,
    multi_check_decision,
)
if (
    multi_check_plan.primary_target_id != 3
    or multi_check_plan.stance.value != "oppose"
    or multi_check_plan.provisional_vote_target_id != 3
    or validate_public_speech_plan(multi_check_context, multi_check_plan)
):
    raise SystemExit("multiple newly revealed checks should prioritize a black check consistently")

good_check_context_payload = deepcopy(context_payload)
good_check_context_payload["claim_options"][0]["facts"][1]["result"] = "good"
good_check_context = NPCDecisionContextV1.model_validate(good_check_context_payload)
good_check_decision = PublicSpeechDecisionV1.model_validate(
    {
        "schema_version": "public_speech.v1",
        "intent": "reveal",
        "target_id": 3,
        "claim_option_ids": ["claim:seer-check:3"],
        "evidence_ids": [],
        "signal_ids": [],
    }
)
good_check_plan = upgrade_public_speech_decision_v1(
    good_check_context,
    good_check_decision,
)
if (
    good_check_plan.stance.value != "support"
    or good_check_plan.stance_target_id != 3
    or good_check_plan.provisional_vote_target_id is not None
    or validate_public_speech_plan(good_check_context, good_check_plan)
):
    raise SystemExit("a revealed good check must support and avoid voting its target")

dead_check_context_payload = deepcopy(context_payload)
dead_check_context_payload["claim_options"][0]["facts"][1]["target_id"] = 99
dead_check_context = NPCDecisionContextV1.model_validate(
    dead_check_context_payload
)
dead_check_decision = PublicSpeechDecisionV1.model_validate(
    {
        "schema_version": "public_speech.v1",
        "intent": "reveal",
        "target_id": None,
        "claim_option_ids": ["claim:seer-check:3"],
        "evidence_ids": [],
        "signal_ids": [],
    }
)
dead_check_plan = upgrade_public_speech_decision_v1(
    dead_check_context,
    dead_check_decision,
)
if (
    dead_check_plan.primary_target_id is not None
    or validate_public_speech_plan(dead_check_context, dead_check_plan)
):
    raise SystemExit("a historical check on a non-living seat must not become a live speech target")

for label, updates, expected_error in [
    (
        "duplicate primary and secondary targets",
        {"secondary_target_id": 3},
        "duplicate_plan_target",
    ),
    (
        "question outside selected targets",
        {"secondary_target_id": None, "question": {"target_id": 4, "topic": "stance"}},
        "question_target_mismatch",
    ),
    (
        "pressure with support stance",
        {"stance": "support"},
        "intent_stance_mismatch",
    ),
    (
        "private evidence",
        {"evidence_ids": ["evidence:private:1"]},
        "private_evidence_not_publishable",
    ),
    (
        "good actor using wolf tactic",
        {"tactic": "wolf_frame_good"},
        "wolf_tactic_forbidden",
    ),
    (
        "illegal provisional vote",
        {"provisional_vote_target_id": 99},
        "target_not_allowed",
    ),
    (
        "selected signal without interpretation",
        {"signal_read": "none"},
        "signal_read_mismatch",
    ),
]:
    payload = deepcopy(valid_v2_payload)
    payload.update(updates)
    plan = PublicSpeechPlanV2.model_validate(payload)
    errors = validate_public_speech_plan(context, plan)
    if not any(error.startswith(expected_error) for error in errors):
        raise SystemExit(f"illegal V2 {label} should be rejected: {errors}")

for label, mutate in [
    ("missing nullable field", lambda payload: payload.pop("secondary_target_id")),
    ("extra publishable text", lambda payload: payload.update({"text": "不得生成台词"})),
    ("coerced target id", lambda payload: payload.update({"primary_target_id": "3"})),
    (
        "more than three evidence ids",
        lambda payload: payload.update(
            {"evidence_ids": ["evidence:public:1"] * 4}
        ),
    ),
]:
    payload = deepcopy(valid_v2_payload)
    mutate(payload)
    try:
        PublicSpeechPlanV2.model_validate(payload)
    except (ValidationError, ValueError):
        pass
    else:
        raise SystemExit(f"strict V2 public-speech schema should reject {label}")

print("NPC decision contract smoke test passed")
'''
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="NPC decision contract smoke test failed",
    )
    print("[OK] NPC V1/V2/V3 decision schemas, continuity, and allowlist validation work.")


def check_npc_tuning() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = r'''
from copy import deepcopy
import json
import tempfile
from pathlib import Path

from pydantic import ValidationError

import app.main as main_module
from app.main import GAME_STORE, GameStartRequest, start_wolf_game
from app.npc_tuning import (
    NPCTuningConfigV1,
    load_npc_tuning,
    resolve_npc_tuning,
)

npc_names = list(main_module.NPC_NAMES)
default_config = load_npc_tuning(
    Path("config/npc_tuning.json"),
    npc_name_whitelist=npc_names,
)
if default_config.schema_version != "npc_tuning.v1":
    raise SystemExit("the persisted NPC tuning config should use npc_tuning.v1")

base_values = {
    "reasoning_skill": 0.1,
    "social_susceptibility": 0.1,
    "decision_variance": 0.1,
    "plan_consistency": 0.1,
    "deception_susceptibility": 0.1,
    "deception_strength": 0.1,
    "team_coordination": 0.1,
    "teammate_bus_pressure_threshold": 80,
    "teammate_black_check_chance": 0.1,
    "teammate_black_check_min_pressure": 80,
}
precedence_payload = {
    "schema_version": "npc_tuning.v1",
    "global_defaults": base_values,
    "factions": {
        "good": {"reasoning_skill": 0.2},
        "werewolf": {"reasoning_skill": 0.25},
    },
    "roles": {
        "werewolf": {},
        "seer": {},
        "witch": {},
        "hunter": {},
        "guard": {},
        "villager": {"reasoning_skill": 0.3},
    },
    "npcs": {"梅西": {"reasoning_skill": 0.4}},
}
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir) / "npc_tuning.json"
    temp_path.write_text(
        json.dumps(precedence_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    precedence_config = load_npc_tuning(
        temp_path,
        npc_name_whitelist=npc_names,
    )

    resolved_npc = resolve_npc_tuning(
        precedence_config,
        faction="good",
        role="villager",
        npc_name="梅西",
        npc_name_whitelist=npc_names,
    )
    resolved_role = resolve_npc_tuning(
        precedence_config,
        faction="good",
        role="villager",
        npc_name="C罗",
        npc_name_whitelist=npc_names,
    )
    resolved_faction = resolve_npc_tuning(
        precedence_config,
        faction="good",
        role="seer",
        npc_name="C罗",
        npc_name_whitelist=npc_names,
    )
    resolved_global = resolve_npc_tuning(
        precedence_config,
        faction="werewolf",
        role="werewolf",
        npc_name="C罗",
        npc_name_whitelist=npc_names,
    )
    if (
        resolved_npc.reasoning_skill != 0.4
        or resolved_role.reasoning_skill != 0.3
        or resolved_faction.reasoning_skill != 0.2
        or resolved_global.reasoning_skill != 0.25
        or resolved_npc.plan_consistency != 0.1
    ):
        raise SystemExit("NPC tuning must resolve global < faction < role < NPC")

    invalid_payloads = []
    extra_payload = deepcopy(precedence_payload)
    extra_payload["global_defaults"]["unknown_knob"] = 1
    invalid_payloads.append(("unknown field", extra_payload))
    range_payload = deepcopy(precedence_payload)
    range_payload["global_defaults"]["reasoning_skill"] = 1.1
    invalid_payloads.append(("out-of-range probability", range_payload))
    unknown_npc_payload = deepcopy(precedence_payload)
    unknown_npc_payload["npcs"] = {"不存在的NPC": {"reasoning_skill": 0.5}}
    invalid_payloads.append(("unknown NPC", unknown_npc_payload))
    for label, payload in invalid_payloads:
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        try:
            load_npc_tuning(temp_path, npc_name_whitelist=npc_names)
        except (ValidationError, ValueError):
            pass
        else:
            raise SystemExit(f"strict tuning loader should reject {label}")

try:
    resolve_npc_tuning(
        default_config,
        faction="good",
        role="werewolf",
        npc_name="梅西",
        npc_name_whitelist=npc_names,
    )
except ValueError:
    pass
else:
    raise SystemExit("tuning resolution should reject faction/role mismatch")

original_live_config = main_module.NPC_TUNING_CONFIG
try:
    old_response = start_wolf_game(
        GameStartRequest(player_name="调参快照旧对局", enable_llm=False)
    )
    old_state = GAME_STORE[old_response.game_id]
    old_actor = next(character for character in old_state.characters if character.name == "梅西")
    old_snapshot = deepcopy(old_actor.strategy_tuning)
    old_reasoning = main_module.get_character_strategy_tuning(old_actor).reasoning_skill

    changed_payload = default_config.model_dump(mode="json")
    changed_payload["npcs"]["梅西"]["reasoning_skill"] = 0.01
    main_module.NPC_TUNING_CONFIG = NPCTuningConfigV1.model_validate(changed_payload)
    new_response = start_wolf_game(
        GameStartRequest(player_name="调参快照新对局", enable_llm=False)
    )
    new_state = GAME_STORE[new_response.game_id]
    new_actor = next(character for character in new_state.characters if character.name == "梅西")
    new_reasoning = main_module.get_character_strategy_tuning(new_actor).reasoning_skill
    if new_reasoning != 0.01:
        raise SystemExit("a changed tuning config should apply to a newly created game")
    if (
        old_actor.strategy_tuning != old_snapshot
        or main_module.get_character_strategy_tuning(old_actor).reasoning_skill != old_reasoning
        or old_reasoning == new_reasoning
    ):
        raise SystemExit("an existing game must retain its immutable NPC tuning snapshot")
    if old_state.characters[0].strategy_tuning or new_state.characters[0].strategy_tuning:
        raise SystemExit("the human player should not receive NPC strategy tuning")
finally:
    main_module.NPC_TUNING_CONFIG = original_live_config

print("NPC tuning smoke test passed")
'''
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="NPC tuning config and snapshot smoke test failed",
    )
    print("[OK] NPC tuning is strict, layered, and snapshotted per game.")


def check_headless_simulation() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = r'''
import os
import math
import random

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"

from app import main as rules
from app import vote_calibration as vote_calibration_module
from app.belief import (
    BELIEF_MODE,
    BELIEF_SCHEMA_VERSION,
    PUBLIC_SOFT_EVIDENCE_DAILY_DECAY,
    BeliefTraceRecorder,
    build_belief_snapshot,
)
from app.invariance import (
    ACTOR_PROJECTION_NAMES,
    AUTHORIZATION_MODE,
    AUTHORIZATION_SCHEMA_VERSION,
    INVARIANCE_MODE,
    INVARIANCE_PROJECTION_VERSION,
    INVARIANCE_SCHEMA_VERSION,
    AuthorizedPrivateCase,
    HiddenInfoInvarianceError,
    build_hidden_info_authorization_report,
    build_hidden_info_invariance_report,
    build_m06a_hidden_variants,
    build_m06b_authorized_cases,
)
from app.simulation import (
    BATCH_SCHEMA_VERSION,
    BELIEF_SCHEMA_VERSION as SIMULATION_BELIEF_SCHEMA_VERSION,
    METRICS_SCHEMA_VERSION,
    SIMULATION_SCHEMA_VERSION,
    SPEECH_CONTINUITY_METRICS_VERSION,
    STANCE_SCHEMA_VERSION as SIMULATION_STANCE_SCHEMA_VERSION,
    VOTE_CALIBRATION_SCHEMA_VERSION as SIMULATION_VOTE_CALIBRATION_SCHEMA_VERSION,
    VOTE_CALIBRATION_SUMMARY_VERSION as SIMULATION_VOTE_CALIBRATION_SUMMARY_VERSION,
    _choose_public_player_target,
    run_rule_simulation,
    run_rule_simulation_batch,
)
from app.stance import (
    STANCE_MODE,
    STANCE_SCHEMA_VERSION,
    StanceTraceRecorder,
    build_stance_snapshot,
)
from app.simulation_metrics import (
    build_game_metrics,
    summarize_ballot_distribution,
)
from app.vote_calibration import (
    COMPONENT_NAMES as VOTE_CALIBRATION_COMPONENT_NAMES,
    GOOD_EXILE_POLICY_VERSION,
    GOOD_EXILE_TEMPERATURE_OFFSET,
    SHADOW_POLICY_VERSION,
    VOTE_CALIBRATION_MODE,
    VOTE_CALIBRATION_SCHEMA_VERSION,
    VOTE_CALIBRATION_SUMMARY_VERSION,
    VoteProbabilityObservationV1,
    build_vote_probability_observation,
)

for public_model in (
    rules.GameStartRequest,
    rules.GameStartResponse,
    rules.GameStateResponse,
    rules.GameSummaryResponse,
):
    if "random_seed" in public_model.model_fields:
        raise SystemExit("the private game seed must not enter a public API schema")
    if "metrics" in public_model.model_fields:
        raise SystemExit("post-game simulation metrics must not enter live API schemas")
    if "belief_trace" in public_model.model_fields:
        raise SystemExit("shadow belief traces must not enter live API schemas")
    if "stance_trace" in public_model.model_fields:
        raise SystemExit("shadow stance traces must not enter live API schemas")
    if "vote_calibration_trace" in public_model.model_fields:
        raise SystemExit("shadow vote probabilities must not enter live API schemas")
    if "witch_strategy_decisions" in public_model.model_fields:
        raise SystemExit("NPC witch audit records must not enter live API schemas")

empty_distribution = summarize_ballot_distribution([])
if empty_distribution["entropy_bits"] is not None:
    raise SystemExit("an empty ballot sample must use null rather than zero entropy")
unanimous_distribution = summarize_ballot_distribution([2, 2, 2])
if (
    unanimous_distribution["entropy_bits"] != 0.0
    or unanimous_distribution["normalized_entropy"] != 0.0
    or unanimous_distribution["effective_target_count"] != 1.0
):
    raise SystemExit("a unanimous ballot sample must have zero entropy")
fully_split_distribution = summarize_ballot_distribution([2, 3, 4])
if fully_split_distribution["normalized_entropy"] != 1.0:
    raise SystemExit("all-distinct ballots must have normalized entropy one")

witch_policy_state = rules.create_wolf_game_state(
    rules.GameStartRequest(
        player_name="女巫策略测试玩家",
        player_role="villager",
        enable_llm=False,
        enable_rag=False,
    ),
    game_id="witch_policy_contract",
    random_seed=20260719,
)
if (
    rules.FAKE_SEER_CAMPAIGN_POLICY_VERSION != "fake_seer_campaign.v1"
    or rules.FAKE_SEER_CHECK_POLICY_VERSION != "fake_seer_check_mix.v1"
):
    raise SystemExit("V3.1-M fake-seer policies must stay explicitly versioned")
campaign_choices = [
    rules.choose_designated_fake_seer(witch_policy_state.characters, seed)
    for seed in range(2_000)
]
campaign_count = sum(choice is not None for choice in campaign_choices)
selected_fake_ids = {
    choice for choice in campaign_choices if choice is not None
}
if (
    len(selected_fake_ids) != 1
    or not 800 <= campaign_count <= 1_760
):
    raise SystemExit("fake-seer campaign must reproducibly mix entry and restraint")
random.seed(7)
campaign_replay = [
    rules.choose_designated_fake_seer(witch_policy_state.characters, seed)
    for seed in range(2_000)
]
random.seed(700_007)
if campaign_choices != campaign_replay:
    raise SystemExit("fake-seer campaign selection must ignore global random state")

good_role_swap_state = witch_policy_state.model_copy(deep=True)
good_role_swap_candidates = [
    character
    for character in good_role_swap_state.characters
    if not character.is_player and character.camp == "good"
]
good_role_swap_candidates[0].role, good_role_swap_candidates[1].role = (
    good_role_swap_candidates[1].role,
    good_role_swap_candidates[0].role,
)
if campaign_choices != [
    rules.choose_designated_fake_seer(good_role_swap_state.characters, seed)
    for seed in range(2_000)
]:
    raise SystemExit("fake-seer campaign must not inspect exact hidden good roles")

fake_seer_id = next(iter(selected_fake_ids))
fake_check_state = witch_policy_state.model_copy(deep=True)
fake_check_state.wolf_fake_seer_id = fake_seer_id
fake_check_state.wolf_checked_wolf_used = True
fake_speaker = rules.get_character(fake_check_state, fake_seer_id)
fake_check_results = []
fake_check_kinds = set()
for seed in range(2_000):
    fake_check_state.random_seed = seed
    check = rules.choose_fake_seer_check(fake_check_state, fake_speaker)
    if check is None:
        raise SystemExit("a fake seer with legal targets must always choose a check")
    target_id, result = check
    target = rules.get_character(fake_check_state, target_id)
    target_camp = "werewolf" if target.role == "werewolf" else "good"
    fake_check_results.append((target_id, result))
    fake_check_kinds.add((target_camp, result))
if fake_check_kinds != {
    ("good", "werewolf"),
    ("good", "good"),
    ("werewolf", "good"),
}:
    raise SystemExit("fake-seer checks must mix non-wolf black/gold and wolf gold")

fake_check_role_swap_state = fake_check_state.model_copy(deep=True)
fake_check_role_swap_candidates = [
    character
    for character in fake_check_role_swap_state.characters
    if not character.is_player and character.camp == "good"
]
fake_check_role_swap_candidates[0].role, fake_check_role_swap_candidates[1].role = (
    fake_check_role_swap_candidates[1].role,
    fake_check_role_swap_candidates[0].role,
)
fake_check_role_swap_speaker = rules.get_character(
    fake_check_role_swap_state,
    fake_seer_id,
)
hidden_role_check_results = []
for seed in range(2_000):
    fake_check_role_swap_state.random_seed = seed
    hidden_role_check_results.append(
        rules.choose_fake_seer_check(
            fake_check_role_swap_state,
            fake_check_role_swap_speaker,
        )
    )
if fake_check_results != hidden_role_check_results:
    raise SystemExit("fake-seer checks must not inspect exact hidden good roles")

npc_witch = next(
    character
    for character in witch_policy_state.characters
    if not character.is_player and character.role == "witch"
)
other_targets = [
    character
    for character in witch_policy_state.characters
    if character.id != npc_witch.id
]
attacked_target = other_targets[0]
self_save_decisions = set()
for seed in range(100):
    witch_policy_state.random_seed = seed
    self_save_decisions.add(
        rules.choose_npc_witch_action_decision(
            witch_policy_state,
            npc_witch,
            npc_witch.id,
        ).reason
    )
if self_save_decisions != {"first_night_self_save"}:
    raise SystemExit("an NPC witch attacked on night one must self-save 100%")
first_night_save_count = 0
first_night_skip_count = 0
for seed in range(2_000):
    witch_policy_state.random_seed = seed
    decision = rules.choose_npc_witch_action_decision(
        witch_policy_state,
        npc_witch,
        attacked_target.id,
    )
    first_night_save_count += decision.action_type == "witch_save"
    first_night_skip_count += decision.reason == "first_night_save_skip"
if (
    not 1_960 <= first_night_save_count <= 1_999
    or first_night_skip_count != 2_000 - first_night_save_count
):
    raise SystemExit("NPC witch first-night antidote use must be deterministic 99%")

poison_target = other_targets[1]
second_target = next(
    character
    for character in other_targets
    if not character.is_player
    and character.id != poison_target.id
    and character.role != poison_target.role
)
explicit_poison = rules.parse_player_speech(
    witch_policy_state,
    f"女巫今晚毒掉{poison_target.id}号，我最怀疑他是狼。",
)
if (
    explicit_poison.witch_directive is None
    or explicit_poison.witch_directive.action != "poison"
    or explicit_poison.witch_directive.target_id != poison_target.id
    or explicit_poison.witch_directive.reason_kind != "target_suspected"
):
    raise SystemExit("explicit player poison advice must become a structured directive")
if rules.parse_player_speech(
    witch_policy_state,
    f"女巫今晚毒掉{poison_target.id}号或{second_target.id}号。",
).witch_directive is not None:
    raise SystemExit("ambiguous witch prose must not be guessed into a directive")
if rules.parse_player_speech(
    witch_policy_state,
    f"我是女巫，我昨晚毒了{poison_target.id}号。",
).witch_directive is not None:
    raise SystemExit("a past potion claim must not be parsed as future poison advice")
explicit_hold = rules.parse_player_speech(
    witch_policy_state,
    "女巫今晚先压毒，当前信息不足，等明天再观察。",
)
if (
    explicit_hold.witch_directive is None
    or explicit_hold.witch_directive.action != "hold"
    or explicit_hold.witch_directive.reason_kind != "public_uncertainty"
):
    raise SystemExit("reasoned player hold advice must become a structured directive")
for invalid_directive in (
    {"action": "poison", "reason_kind": "unspecified"},
    {
        "action": "hold",
        "target_id": poison_target.id,
        "reason_kind": "public_uncertainty",
    },
    {
        "action": "hold",
        "reason_kind": "public_uncertainty",
        "hidden_role": "werewolf",
    },
):
    try:
        rules.WitchDirectiveState.model_validate(invalid_directive)
    except ValueError:
        pass
    else:
        raise SystemExit("witch directives must reject invalid or hidden fields")

witch_policy_state.day = 2
witch_policy_state.phase = "NIGHT"
witch_policy_state.speeches = []
for character in other_targets:
    npc_witch.suspicion[str(character.id)] = 10
npc_witch.suspicion[str(poison_target.id)] = 85
own_read_decision = rules.choose_npc_witch_action_decision(
    witch_policy_state,
    npc_witch,
    attacked_target.id,
)
if (
    own_read_decision.action_type != "witch_poison"
    or own_read_decision.target_id != poison_target.id
    or own_read_decision.reason != "own_suspicion"
):
    raise SystemExit("a surviving NPC witch must poison her top suspect on night two")

source = other_targets[3]
npc_witch.relationships[str(source.id)]["trust"] = 1.0
for character in other_targets:
    npc_witch.suspicion[str(character.id)] = 10
witch_policy_state.speeches = [
    rules.SpeechState(
        day=1,
        character_id=source.id,
        name=source.name,
        speech="如果女巫在场，我建议今晚先压毒，当前公开信息还不足。",
        is_player=source.is_player,
        witch_directive=rules.WitchDirectiveState(
            action="hold",
            reason_kind="public_uncertainty",
            confidence=100,
        ),
    )
]
hold_decision = rules.choose_npc_witch_action_decision(
    witch_policy_state,
    npc_witch,
    attacked_target.id,
)
if hold_decision.action_type != "none" or hold_decision.reason != "accepted_hold":
    raise SystemExit("a trusted, reasoned hold request must be able to preserve poison")

npc_witch.suspicion[str(poison_target.id)] = 90
witch_policy_state.speeches = [
    rules.SpeechState(
        day=1,
        character_id=source.id,
        name=source.name,
        speech=(
            f"如果女巫在场，我建议今晚毒掉{poison_target.id}号，"
            "这是我当前最怀疑的位置。"
        ),
        is_player=source.is_player,
        witch_directive=rules.WitchDirectiveState(
            action="poison",
            target_id=poison_target.id,
            reason_kind="target_suspected",
            confidence=100,
        ),
    )
]
advised_decision = rules.choose_npc_witch_action_decision(
    witch_policy_state,
    npc_witch,
    attacked_target.id,
)
hidden_swap_state = witch_policy_state.model_copy(deep=True)
hidden_poison_target = rules.get_character(hidden_swap_state, poison_target.id)
hidden_second_target = rules.get_character(hidden_swap_state, second_target.id)
hidden_poison_target.role, hidden_second_target.role = (
    hidden_second_target.role,
    hidden_poison_target.role,
)
hidden_poison_target.camp, hidden_second_target.camp = (
    hidden_second_target.camp,
    hidden_poison_target.camp,
)
hidden_witch = rules.get_character(hidden_swap_state, npc_witch.id)
hidden_decision = rules.choose_npc_witch_action_decision(
    hidden_swap_state,
    hidden_witch,
    attacked_target.id,
)
if (
    advised_decision.reason != "accepted_poison"
    or advised_decision.target_id != poison_target.id
    or advised_decision.model_dump(mode="json")
    != hidden_decision.model_dump(mode="json")
):
    raise SystemExit("witch advice must be believable but hidden-role invariant")

first = run_rule_simulation(20260719)
random.seed(11)
replayed = run_rule_simulation(20260719)
random.seed(999999)
replayed_again = run_rule_simulation(20260719)
if first != replayed or first != replayed_again:
    raise SystemExit("the same explicit seed must replay the exact normalized result")
if first["winner"] not in {"good", "werewolf"}:
    raise SystemExit("a simulated game must reach a legal terminal winner")
if (
    first["schema_version"] != SIMULATION_SCHEMA_VERSION
    or first["metrics_schema_version"] != METRICS_SCHEMA_VERSION
    or first["metrics"]["schema_version"] != METRICS_SCHEMA_VERSION
    or not first["metrics"]["post_game_only"]
):
    raise SystemExit("a simulated game must expose versioned post-game metrics")
if (
    SIMULATION_SCHEMA_VERSION != "agent_town_simulation.v10"
    or BATCH_SCHEMA_VERSION != "agent_town_simulation_batch.v10"
    or METRICS_SCHEMA_VERSION != "agent_town_metrics.v3"
):
    raise SystemExit("V3.1-M simulation and metrics schemas must stay explicit")
balance_diagnostics = first["metrics"]["balance_diagnostics"]
if (
    balance_diagnostics["winner_reason"] != first["winner_reason"]
    or "first_exile" not in balance_diagnostics
    or "witch" not in balance_diagnostics
    or balance_diagnostics["witch"]["poison_target_count"]
    != (
        balance_diagnostics["witch"]["wolf_poison_target_count"]
        + balance_diagnostics["witch"]["good_poison_target_count"]
    )
    or balance_diagnostics["witch"]["second_night_poison_opportunity"]
    != (
        balance_diagnostics["witch"]["second_night_poison_used"]
        + balance_diagnostics["witch"]["second_night_hold_accepted"]
    )
):
    raise SystemExit("V3.1-L balance and witch diagnostics must conserve outcomes")
seer_balance = first["metrics"]["seer_claim_balance"]
if (
    bool(seer_balance["fake_seer_id"] is not None)
    != seer_balance["fake_campaign"]
    or (
        seer_balance["fake_candidate"]
        and not seer_balance["fake_campaign"]
    )
    or seer_balance["fake_check_count"]
    != (
        seer_balance["fake_black_check_good_count"]
        + seer_balance["fake_black_check_wolf_count"]
        + seer_balance["fake_gold_check_good_count"]
        + seer_balance["fake_gold_check_wolf_count"]
    )
):
    raise SystemExit("V3.1-M per-game seer diagnostics must conserve decisions")
continuity_metrics = first["speech_continuity"]
continuity_reasons = {
    "stance_aligned",
    "new_public_evidence",
    "deterministic_variance",
    "authorized_claim",
    "mandatory_rule_response",
    "unscored",
}
if (
    continuity_metrics["schema_version"] != SPEECH_CONTINUITY_METRICS_VERSION
    or continuity_metrics["continuity_schema_version"]
    != "public_speech_continuity.v1"
    or continuity_metrics["plan_schema_version"] != "public_speech_plan.v3"
    or set(continuity_metrics["reason_counts"]) != continuity_reasons
    or sum(continuity_metrics["reason_counts"].values())
    != continuity_metrics["controlled_speech_count"]
    or continuity_metrics["controlled_speech_count"] <= 0
):
    raise SystemExit("a simulation must account for every controlled V3 speech reason")
belief_trace = first["belief_trace"]
if (
    first["belief_schema_version"] != BELIEF_SCHEMA_VERSION
    or SIMULATION_BELIEF_SCHEMA_VERSION != BELIEF_SCHEMA_VERSION
    or belief_trace["schema_version"] != BELIEF_SCHEMA_VERSION
    or belief_trace["mode"] != BELIEF_MODE
):
    raise SystemExit("a simulated game must expose a versioned shadow belief trace")
if belief_trace["capture_count"] != len(first["phase_trace"]):
    raise SystemExit("belief snapshots must cover every simulated transition")
if len(belief_trace["final_states"]) != 11:
    raise SystemExit("belief trace must retain one final state for every NPC")
evidence_by_id = {
    evidence["evidence_id"]: evidence
    for evidence in belief_trace["evidence_ledger"]
}
if len(evidence_by_id) != len(belief_trace["evidence_ledger"]):
    raise SystemExit("belief evidence ids must be unique")
for evidence in evidence_by_id.values():
    if evidence["visibility"] == "public" and evidence["observer_ids"]:
        raise SystemExit("public belief evidence must not carry private observers")
    if evidence["visibility"] != "public" and len(evidence["observer_ids"]) != 1:
        raise SystemExit("private belief evidence must identify exactly one legal observer")
for change in belief_trace["changes"]:
    for contribution in (
        change["added_contributions"]
        + change["updated_contributions"]
    ):
        if contribution["evidence_id"] not in evidence_by_id:
            raise SystemExit("every belief change must cite an existing evidence id")
    if change["removed_evidence_ids"]:
        raise SystemExit("the first belief ledger must be append-only")
if not any(
    change["updated_contributions"]
    for change in belief_trace["changes"]
):
    raise SystemExit("a multi-day belief trace must audit decayed contribution weights")
for actor_state in belief_trace["final_states"]:
    if len(actor_state["seats"]) != 11:
        raise SystemExit("each NPC belief state must cover the other eleven seats")
    for seat in actor_state["seats"]:
        if not -100 <= seat["suspicion_score"] <= 100:
            raise SystemExit("belief suspicion scores must stay in range")
        if not 0.0 <= seat["confidence"] <= 1.0:
            raise SystemExit("belief confidence must stay in range")
        for contribution in seat["contributions"]:
            evidence = evidence_by_id[contribution["evidence_id"]]
            if (
                evidence["visibility"] != "public"
                and actor_state["actor_id"] not in evidence["observer_ids"]
            ):
                raise SystemExit("an NPC belief consumed another actor's private evidence")
stance_trace = first["stance_trace"]
if (
    first["stance_schema_version"] != STANCE_SCHEMA_VERSION
    or SIMULATION_STANCE_SCHEMA_VERSION != STANCE_SCHEMA_VERSION
    or stance_trace["schema_version"] != STANCE_SCHEMA_VERSION
    or stance_trace["belief_schema_version"] != BELIEF_SCHEMA_VERSION
    or stance_trace["mode"] != STANCE_MODE
):
    raise SystemExit("a simulated game must expose a versioned shadow stance trace")
if stance_trace["capture_count"] != belief_trace["capture_count"]:
    raise SystemExit("stance and belief snapshots must cover the same transitions")
if len(stance_trace["final_states"]) != 11:
    raise SystemExit("stance trace must retain one final summary for every NPC")
for stance_state in stance_trace["final_states"]:
    if "role" in stance_state or "camp" in stance_state:
        raise SystemExit("a stance card must not embed hidden role or camp labels")
    target_ids = [
        target_id
        for target_id in (
            stance_state["trusted_target_ids"]
            + [
                stance_state["primary_suspect_id"],
                stance_state["secondary_suspect_id"],
                stance_state["provisional_vote_target_id"],
                stance_state["verification_target_id"],
            ]
        )
        if target_id is not None
    ]
    if stance_state["actor_id"] in target_ids:
        raise SystemExit("an NPC stance must not target itself")
    if len(stance_state["basis_evidence_ids"]) != len(
        set(stance_state["basis_evidence_ids"])
    ):
        raise SystemExit("stance basis evidence ids must be unique")
    for evidence_id in stance_state["basis_evidence_ids"]:
        evidence = evidence_by_id[evidence_id]
        if (
            evidence["visibility"] != "public"
            and stance_state["actor_id"] not in evidence["observer_ids"]
        ):
            raise SystemExit("a stance summary consumed another actor's private evidence")
stance_observation_ids = [
    observation["observation_id"]
    for observation in stance_trace["observations"]
]
if len(stance_observation_ids) != len(set(stance_observation_ids)):
    raise SystemExit("stance observation ids must be unique")
for observation in stance_trace["observations"]:
    if len(observation["expected_target_ids"]) != len(
        set(observation["expected_target_ids"])
    ):
        raise SystemExit("stance observation expectations must be unique")
    for evidence_id in observation["new_evidence_ids"]:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise SystemExit("stance continuity changes must cite belief evidence")
        if (
            evidence["visibility"] != "public"
            and observation["actor_id"] not in evidence["observer_ids"]
        ):
            raise SystemExit("stance continuity consumed another actor's evidence")
for change in stance_trace["changes"]:
    for evidence_id in (
        change["added_evidence_ids"]
        + change["removed_evidence_ids"]
    ):
        if evidence_id not in evidence_by_id:
            raise SystemExit("stance changes must cite existing belief evidence")
vote_calibration_trace = first["vote_calibration_trace"]
if (
    first["vote_calibration_schema_version"]
    != VOTE_CALIBRATION_SCHEMA_VERSION
    or SIMULATION_VOTE_CALIBRATION_SCHEMA_VERSION
    != VOTE_CALIBRATION_SCHEMA_VERSION
    or vote_calibration_trace["schema_version"]
    != VOTE_CALIBRATION_SCHEMA_VERSION
    or vote_calibration_trace["belief_schema_version"]
    != BELIEF_SCHEMA_VERSION
    or vote_calibration_trace["mode"] != VOTE_CALIBRATION_MODE
    or vote_calibration_trace["observation_count"] <= 0
):
    raise SystemExit("a simulation must expose a versioned M15-A/B vote trace")
if (
    vote_calibration_trace["controlled_observation_count"]
    + vote_calibration_trace["shadow_observation_count"]
    != vote_calibration_trace["observation_count"]
    or GOOD_EXILE_TEMPERATURE_OFFSET != 5.0
):
    raise SystemExit("M15-B controlled/shadow counts and calibrated offset must be explicit")
if vote_calibration_trace["candidate_evaluation_count"] != sum(
    len(observation["candidates"])
    for observation in vote_calibration_trace["observations"]
):
    raise SystemExit("vote shadow candidate evaluations must conserve observations")
vote_shadow_ids = []
vote_shadow_kinds = set()
vote_consumer_modes = set()
first_roles = {
    role["character_id"]: role
    for role in first["roles"]
}
for observation in vote_calibration_trace["observations"]:
    VoteProbabilityObservationV1.model_validate(observation)
    vote_shadow_ids.append(observation["observation_id"])
    vote_shadow_kinds.add(observation["vote_kind"])
    vote_consumer_modes.add(observation["consumer_mode"])
    voter_role = first_roles[observation["voter_id"]]
    if observation["consumer_mode"] == "controlled":
        if (
            observation["policy_version"] != GOOD_EXILE_POLICY_VERSION
            or observation["vote_kind"] != "exile_vote"
            or observation["phase"] != "VOTE"
            or voter_role["camp"] != "good"
            or voter_role["is_player"]
            or observation["hard_constraint"]
        ):
            raise SystemExit("M15-B may control only ordinary good-NPC exile ballots")
    elif observation["policy_version"] != SHADOW_POLICY_VERSION:
        raise SystemExit("non-controlled ballots must retain the M15-A shadow policy")
    if observation["voter_id"] in {
        candidate["target_id"] for candidate in observation["candidates"]
    }:
        raise SystemExit("vote shadow distributions must exclude self votes")
    if not math.isclose(
        sum(
            candidate["probability"]
            for candidate in observation["candidates"]
        ),
        1.0,
        abs_tol=0.000002,
    ):
        raise SystemExit("every vote shadow distribution must conserve probability")
    for candidate in observation["candidates"]:
        if not math.isclose(
            sum(candidate[name] for name in VOTE_CALIBRATION_COMPONENT_NAMES),
            candidate["total_utility"],
            abs_tol=0.002,
        ):
            raise SystemExit("vote shadow component utilities must conserve totals")
if len(vote_shadow_ids) != len(set(vote_shadow_ids)):
    raise SystemExit("vote shadow observation ids must be unique")
if vote_shadow_kinds != {"sheriff_vote", "exile_vote"}:
    raise SystemExit("M15-A must observe both sheriff and exile NPC ballots")
if vote_consumer_modes != {"shadow", "controlled"}:
    raise SystemExit("M15-B traces must retain shadow ballots beside controlled ballots")
try:
    VoteProbabilityObservationV1.model_validate(
        {
            **vote_calibration_trace["observations"][0],
            "hidden_role": "werewolf",
        }
    )
except ValueError:
    pass
else:
    raise SystemExit("vote shadow schemas must reject undeclared hidden fields")
if first["llm_validation_failure_count"] != 0:
    raise SystemExit("rule simulation must not call the LLM")
good_vote = first["metrics"]["good_exile_vote"]
if good_vote["ballot_count"] != (
    good_vote["correct_wolf_target_count"]
    + good_vote["misvote_good_target_count"]
):
    raise SystemExit("good-vote correctness counts must conserve ballots")
for rate_name in (
    "correct_wolf_target_rate",
    "misvote_good_target_rate",
):
    rate = good_vote[rate_name]
    if rate is not None and not 0.0 <= rate <= 1.0:
        raise SystemExit("good-vote rates must stay between zero and one")
for vote_kind in ("sheriff_vote", "exile_vote"):
    entropy = first["metrics"][vote_kind]["mean_normalized_entropy"]
    if entropy is not None and not 0.0 <= entropy <= 1.0:
        raise SystemExit("normalized vote entropy must stay between zero and one")
if any(
    not isinstance(ballot["round"], int)
    for ballot in first["sheriff_ballots"]
):
    raise SystemExit("sheriff ballots must retain their election round")

batch = run_rule_simulation_batch(20260719, 6)
if batch["games_completed"] != 6:
    raise SystemExit("batch simulation did not complete every requested game")
if (
    batch["schema_version"] != BATCH_SCHEMA_VERSION
    or batch["metrics_schema_version"] != METRICS_SCHEMA_VERSION
    or batch["metrics"]["schema_version"] != METRICS_SCHEMA_VERSION
):
    raise SystemExit("batch simulation must expose compatible metric versions")
batch_balance = batch["metrics"]["balance_diagnostics"]
if (
    sum(batch_balance["winner_reason_counts"].values()) != 6
    or batch_balance["witch"]["poison_target_count"]
    != (
        batch_balance["witch"]["wolf_poison_target_count"]
        + batch_balance["witch"]["good_poison_target_count"]
    )
    or batch_balance["witch"]["second_night_poison_opportunity"]
    != (
        batch_balance["witch"]["second_night_poison_used"]
        + batch_balance["witch"]["second_night_hold_accepted"]
    )
):
    raise SystemExit("batch V3.1-L balance diagnostics must conserve games and poison targets")
batch_seer = batch["metrics"]["seer_claim_balance"]
seer_conditions = {
    "fake_campaign",
    "fake_elected",
    "fake_black_checked_true_seer",
    "true_seer_first_exiled",
}
if (
    not 0 <= batch_seer["fake_campaign"] <= 6
    or not 0 <= batch_seer["fake_candidate"] <= batch_seer["fake_campaign"]
    or batch_seer["fake_check_count"]
    != (
        batch_seer["fake_black_check_good_count"]
        + batch_seer["fake_black_check_wolf_count"]
        + batch_seer["fake_gold_check_good_count"]
        + batch_seer["fake_gold_check_wolf_count"]
    )
    or set(batch_seer["winner_counts_by_condition"]) != seer_conditions
    or any(
        sum(batch_seer["winner_counts_by_condition"][condition].values())
        != batch_seer[condition]
        for condition in seer_conditions
    )
):
    raise SystemExit("batch V3.1-M seer diagnostics must conserve games and checks")
for rate_name in (
    "fake_campaign_rate",
    "fake_election_rate",
    "true_seer_election_rate",
):
    rate = batch_seer[rate_name]
    if rate is not None and not 0.0 <= rate <= 1.0:
        raise SystemExit("V3.1-M seer diagnostic rates must stay bounded")
if (
    batch["belief_schema_version"] != BELIEF_SCHEMA_VERSION
    or batch["belief_summary"]["schema_version"] != BELIEF_SCHEMA_VERSION
    or batch["belief_summary"]["mode"] != BELIEF_MODE
    or batch["belief_summary"]["game_count"] != 6
):
    raise SystemExit("batch simulation must aggregate compatible shadow beliefs")
if (
    batch["stance_schema_version"] != STANCE_SCHEMA_VERSION
    or batch["stance_summary"]["schema_version"] != STANCE_SCHEMA_VERSION
    or batch["stance_summary"]["mode"] != STANCE_MODE
    or batch["stance_summary"]["game_count"] != 6
):
    raise SystemExit("batch simulation must aggregate compatible shadow stances")
vote_calibration_summary = batch["vote_calibration_summary"]
if (
    batch["vote_calibration_schema_version"]
    != VOTE_CALIBRATION_SCHEMA_VERSION
    or batch["vote_calibration_summary_version"]
    != VOTE_CALIBRATION_SUMMARY_VERSION
    or SIMULATION_VOTE_CALIBRATION_SUMMARY_VERSION
    != VOTE_CALIBRATION_SUMMARY_VERSION
    or vote_calibration_summary["schema_version"]
    != VOTE_CALIBRATION_SUMMARY_VERSION
    or vote_calibration_summary["trace_schema_version"]
    != VOTE_CALIBRATION_SCHEMA_VERSION
    or vote_calibration_summary["mode"] != VOTE_CALIBRATION_MODE
    or vote_calibration_summary["game_count"] != 6
    or vote_calibration_summary["observation_count"]
    != sum(
        game["vote_calibration_trace"]["observation_count"]
        for game in batch["games"]
    )
):
    raise SystemExit("batch simulation must aggregate M15-A/B vote probabilities")
if (
    vote_calibration_summary["controlled_observation_count"]
    + vote_calibration_summary["shadow_observation_count"]
    != vote_calibration_summary["observation_count"]
    or set(vote_calibration_summary["by_consumer_mode"])
    != {"shadow", "controlled"}
    or sum(
        group["observation_count"]
        for group in vote_calibration_summary["by_consumer_mode"].values()
    )
    != vote_calibration_summary["observation_count"]
    or vote_calibration_summary["by_consumer_mode"]["controlled"][
        "observation_count"
    ]
    != vote_calibration_summary["controlled_observation_count"]
):
    raise SystemExit("M15-B consumer-mode summary groups must conserve observations")
if set(vote_calibration_summary["by_kind"]) != {
    "sheriff_vote",
    "exile_vote",
} or sum(
    group["observation_count"]
    for group in vote_calibration_summary["by_kind"].values()
) != vote_calibration_summary["observation_count"]:
    raise SystemExit("vote shadow kind groups must conserve observations")
if sum(
    group["observation_count"]
    for group in vote_calibration_summary["by_voter_camp"].values()
) != vote_calibration_summary["observation_count"]:
    raise SystemExit("vote shadow camp groups must conserve observations")
for vote_kind, camp_groups in vote_calibration_summary[
    "by_kind_and_voter_camp"
].items():
    if sum(
        group["observation_count"] for group in camp_groups.values()
    ) != vote_calibration_summary["by_kind"][vote_kind]["observation_count"]:
        raise SystemExit("nested vote shadow kind/camp groups must conserve observations")
for group in [
    *vote_calibration_summary["by_kind"].values(),
    *vote_calibration_summary["by_voter_camp"].values(),
    *vote_calibration_summary["by_consumer_mode"].values(),
]:
    for rate_name in (
        "mean_normalized_entropy",
        "mean_top_probability",
        "actual_top_match_rate",
        "mean_actual_target_probability",
    ):
        rate = group[rate_name]
        if rate is not None and not 0.0 <= rate <= 1.0:
            raise SystemExit("vote shadow probability metrics must stay in range")
    if set(group["mean_absolute_component_utility"]) != set(
        VOTE_CALIBRATION_COMPONENT_NAMES
    ):
        raise SystemExit("vote shadow summaries must retain every utility component")
good_shadow_alignment = vote_calibration_summary[
    "good_exile_probability_alignment"
]
if not math.isclose(
    good_shadow_alignment["probability_mass_on_wolves"]
    + good_shadow_alignment["probability_mass_on_good"],
    good_shadow_alignment["observation_count"],
    abs_tol=0.00002,
):
    raise SystemExit("good vote shadow probability mass must conserve observations")
continuity_summary = batch["speech_continuity_summary"]
if (
    batch["speech_continuity_schema_version"]
    != SPEECH_CONTINUITY_METRICS_VERSION
    or continuity_summary["schema_version"]
    != SPEECH_CONTINUITY_METRICS_VERSION
    or set(continuity_summary["reason_counts"]) != continuity_reasons
    or sum(continuity_summary["reason_counts"].values())
    != continuity_summary["controlled_speech_count"]
    or continuity_summary["controlled_speech_count"]
    != sum(
        game["speech_continuity"]["controlled_speech_count"]
        for game in batch["games"]
    )
):
    raise SystemExit("batch simulation must conserve controlled speech reasons")
stance_alignment_total = sum(
    batch["stance_summary"]["alignment_counts"].values()
)
if stance_alignment_total != batch["stance_summary"]["observation_count"]:
    raise SystemExit("stance alignment classes must conserve observations")
stance_scored_total = sum(
    batch["stance_summary"]["alignment_counts"][alignment]
    for alignment in (
        "aligned",
        "explained_change",
        "unexplained_change",
    )
)
if stance_scored_total != batch["stance_summary"]["scored_observation_count"]:
    raise SystemExit("scored stance alignment classes must conserve observations")
for rate_name in ("alignment_rate", "unexplained_change_rate"):
    rate = batch["stance_summary"][rate_name]
    if rate is not None and not 0.0 <= rate <= 1.0:
        raise SystemExit("stance continuity rates must stay between zero and one")
if set(batch["stance_summary"]["by_kind"]) != {
    "public_speech",
    "sheriff_vote",
    "exile_vote",
}:
    raise SystemExit("stance summary must retain every observed decision kind")
if sum(
    sum(counts.values())
    for counts in batch["stance_summary"]["by_kind"].values()
) != batch["stance_summary"]["observation_count"]:
    raise SystemExit("stance kind groups must conserve observations")
if [game["seed"] for game in batch["games"]] != list(range(20260719, 20260725)):
    raise SystemExit("batch simulation must preserve its sequential seed range")
if sum(batch["summary"]["winner_counts"].values()) != 6:
    raise SystemExit("batch winner counts must add up to the completed game count")
if sum(
    group["game_count"]
    for group in batch["metrics"]["by_player_role"].values()
) != 6:
    raise SystemExit("player-role metric groups must cover every simulated game")
if sum(
    group["ballot_count"]
    for group in batch["metrics"]["by_voter_role"].values()
) != batch["metrics"]["exile_vote"]["ballot_count"]:
    raise SystemExit("voter-role metric groups must cover every exile ballot")
if sum(
    day["ballot_count"]
    for day in batch["metrics"]["by_day"].values()
) != batch["metrics"]["exile_vote"]["ballot_count"]:
    raise SystemExit("day metric groups must cover every exile ballot")
batch_good_vote = batch["metrics"]["good_exile_vote"]
if batch_good_vote["ballot_count"] != (
    batch_good_vote["correct_wolf_target_count"]
    + batch_good_vote["misvote_good_target_count"]
):
    raise SystemExit("batch good-vote metric counts must conserve ballots")
fake_metrics = batch["metrics"]["fake_seer_acceptance"]
for rate_name in (
    "public_claim_rate",
    "election_rate",
    "good_sheriff_support_rate",
    "good_black_check_follow_rate",
):
    rate = fake_metrics[rate_name]
    if rate is not None and not 0.0 <= rate <= 1.0:
        raise SystemExit("fake-seer acceptance rates must stay between zero and one")
for game in batch["games"]:
    fake = game["metrics"]["fake_seer_acceptance"]
    for denominator_name, rate_name in (
        ("eligible_good_sheriff_ballots", "good_sheriff_support_rate"),
        ("eligible_good_exile_ballots", "good_black_check_follow_rate"),
    ):
        if (fake[denominator_name] == 0) != (fake[rate_name] is None):
            raise SystemExit("empty metric samples must map to null rates exactly")

def assert_finite_metrics(value):
    if isinstance(value, dict):
        for nested in value.values():
            assert_finite_metrics(nested)
    elif isinstance(value, list):
        for nested in value:
            assert_finite_metrics(nested)
    elif isinstance(value, float) and not math.isfinite(value):
        raise SystemExit("metric payload must not contain NaN or infinity")

assert_finite_metrics(batch["metrics"])
assert_finite_metrics(batch["vote_calibration_summary"])
if any(game_id.startswith("simulation_") for game_id in rules.GAME_STORE):
    raise SystemExit("completed simulations must be removed from the live game store")
if rules.HYBRID_INDEX.status()["initialized"]:
    raise SystemExit("rule simulation must not initialize vector RAG")

compact_batch = run_rule_simulation_batch(
    20260719,
    2,
    capture_beliefs=False,
)
if (
    compact_batch["belief_summary"] is not None
    or compact_batch["stance_summary"] is not None
    or compact_batch["vote_calibration_summary"] is None
    or any(
        game["belief_trace"] is not None
        or game["stance_trace"] is not None
        or game["vote_calibration_trace"] is None
        for game in compact_batch["games"]
    )
):
    raise SystemExit("belief-off mode must retain the independent M15-A/B vote trace")
if [game["gameplay_digest"] for game in compact_batch["games"]] != [
    game["gameplay_digest"] for game in batch["games"][:2]
]:
    raise SystemExit("compact shadow mode must preserve gameplay digests")

without_vote_calibration = run_rule_simulation_batch(
    20260719,
    2,
    capture_vote_calibration=False,
)
if (
    without_vote_calibration["vote_calibration_summary"] is not None
    or any(
        game["vote_calibration_trace"] is not None
        for game in without_vote_calibration["games"]
    )
):
    raise SystemExit("vote-trace-off mode must omit M15-A/B trace details")
if [game["gameplay_digest"] for game in without_vote_calibration["games"]] != [
    game["gameplay_digest"] for game in batch["games"][:2]
]:
    raise SystemExit("M15-A/B trace capture must not change gameplay digests")

belief_only_batch = run_rule_simulation_batch(
    20260719,
    2,
    capture_stances=False,
)
if belief_only_batch["belief_summary"] is None or (
    belief_only_batch["stance_summary"] is not None
) or any(
    game["belief_trace"] is None or game["stance_trace"] is not None
    for game in belief_only_batch["games"]
):
    raise SystemExit("belief-only mode must omit only stance traces")
if belief_only_batch["games"][0]["belief_trace"] != batch["games"][0]["belief_trace"]:
    raise SystemExit("stance capture must not change the underlying belief trace")

request = rules.GameStartRequest(
    player_name="确定性测试玩家",
    player_role="villager",
    enable_llm=False,
    enable_rag=False,
)
left = rules.create_wolf_game_state(
    request,
    game_id="seed_replay_left",
    random_seed=314159,
)
right = rules.create_wolf_game_state(
    request,
    game_id="seed_replay_right",
    random_seed=314159,
)
try:
    build_game_metrics(left)
except ValueError:
    pass
else:
    raise SystemExit("true-role metrics must reject an in-progress game state")
if [character.role for character in left.characters] != [
    character.role for character in right.characters
]:
    raise SystemExit("role assignment must depend on the explicit seed, not game id")
if left.wolf_fake_seer_id is None:
    left.wolf_fake_seer_id = next(
        fake_id
        for seed in range(1_000)
        if (
            fake_id := rules.choose_designated_fake_seer(
                left.characters,
                seed,
            )
        )
        is not None
    )
    right.wolf_fake_seer_id = left.wolf_fake_seer_id

villager_observer = next(
    character
    for character in left.characters
    if not character.is_player and character.role == "villager"
)
villager_snapshot = build_belief_snapshot(
    left,
    observer_ids=[villager_observer.id],
)
hidden_role_swap = left.model_copy(deep=True)
hidden_wolf = next(
    character
    for character in hidden_role_swap.characters
    if not character.is_player and character.role == "werewolf"
)
hidden_good = next(
    character
    for character in hidden_role_swap.characters
    if (
        not character.is_player
        and character.camp == "good"
        and character.id != villager_observer.id
    )
)
hidden_wolf.role, hidden_good.role = hidden_good.role, hidden_wolf.role
hidden_wolf.camp, hidden_good.camp = hidden_good.camp, hidden_wolf.camp
hidden_role_swap.wolf_fake_seer_id = hidden_good.id
if villager_snapshot != build_belief_snapshot(
    hidden_role_swap,
    observer_ids=[villager_observer.id],
):
    raise SystemExit("villager beliefs must be invariant to unseen role and fake-seer swaps")

left_vote_shadow_state = left.model_copy(deep=True)
left_vote_shadow_state.phase = "VOTE"
hidden_vote_shadow_state = hidden_role_swap.model_copy(deep=True)
hidden_vote_shadow_state.phase = "VOTE"
vote_shadow_candidate_ids = [
    character.id
    for character in left_vote_shadow_state.characters
    if character.alive
]
villager_vote_shadow = build_vote_probability_observation(
    left_vote_shadow_state,
    rules.get_character(left_vote_shadow_state, villager_observer.id),
    vote_kind="exile_vote",
    candidate_ids=vote_shadow_candidate_ids,
)
reordered_villager_vote_shadow = build_vote_probability_observation(
    left_vote_shadow_state,
    rules.get_character(left_vote_shadow_state, villager_observer.id),
    vote_kind="exile_vote",
    candidate_ids=list(reversed(vote_shadow_candidate_ids)),
)
hidden_role_vote_shadow = build_vote_probability_observation(
    hidden_vote_shadow_state,
    rules.get_character(hidden_vote_shadow_state, villager_observer.id),
    vote_kind="exile_vote",
    candidate_ids=vote_shadow_candidate_ids,
)
if villager_vote_shadow != reordered_villager_vote_shadow:
    raise SystemExit("vote shadow distributions must ignore candidate input order")
if villager_vote_shadow != hidden_role_vote_shadow:
    raise SystemExit("good vote shadows must ignore unseen role and fake-seer swaps")
if any(
    key in villager_vote_shadow
    for key in ["role", "camp", "evidence_ledger", "random_seed"]
):
    raise SystemExit("vote shadow observations must not serialize hidden truth or evidence")
if any(
    candidate["coordination_utility"] != 0.0
    for candidate in villager_vote_shadow["candidates"]
):
    raise SystemExit("good vote shadows must not receive wolf-team coordination")
if (
    villager_vote_shadow["consumer_mode"] != "controlled"
    or villager_vote_shadow["policy_version"] != GOOD_EXILE_POLICY_VERSION
):
    raise SystemExit("an ordinary good NPC VOTE ballot must use M15-B control")

def build_legacy_good_exile_probabilities(state, voter, candidate_ids):
    candidates = [
        rules.get_character(state, candidate_id)
        for candidate_id in sorted(set(candidate_ids))
        if candidate_id != voter.id
        and rules.get_character(state, candidate_id).alive
    ]
    scores = {
        candidate.id: round(
            rules.score_npc_vote_candidate(state, voter, candidate),
            4,
        )
        for candidate in candidates
    }
    return rules.build_softmax_vote_probabilities(
        scores,
        rules.get_character_strategy_tuning(voter),
    )

controlled_villager = rules.get_character(
    left_vote_shadow_state,
    villager_observer.id,
)
controlled_live_probabilities = rules.build_npc_exile_vote_probabilities(
    left_vote_shadow_state,
    controlled_villager,
    vote_shadow_candidate_ids,
)
controlled_trace_probabilities = {
    candidate["target_id"]: candidate["probability"]
    for candidate in villager_vote_shadow["candidates"]
}
if controlled_live_probabilities != controlled_trace_probabilities:
    raise SystemExit("the M15-B trace must match the live controlled distribution")
legacy_villager_probabilities = build_legacy_good_exile_probabilities(
    left_vote_shadow_state,
    controlled_villager,
    vote_shadow_candidate_ids,
)
if controlled_live_probabilities == legacy_villager_probabilities:
    raise SystemExit("M15-B must apply its calibrated temperature in live VOTE")
if rules.build_npc_exile_vote_probabilities(
    left_vote_shadow_state,
    controlled_villager,
    vote_shadow_candidate_ids,
    ignore_sheriff_lock=True,
) != legacy_villager_probabilities:
    raise SystemExit("sheriff nomination planning must remain on the legacy path")

sheriff_scope_state = left_vote_shadow_state.model_copy(deep=True)
sheriff_scope_state.sheriff_id = villager_observer.id
sheriff_scope_voter = rules.get_character(
    sheriff_scope_state,
    villager_observer.id,
)
if rules.build_npc_exile_vote_probabilities(
    sheriff_scope_state,
    sheriff_scope_voter,
    vote_shadow_candidate_ids,
) != build_legacy_good_exile_probabilities(
    sheriff_scope_state,
    sheriff_scope_voter,
    vote_shadow_candidate_ids,
):
    raise SystemExit("the sheriff's final nomination ballot must remain legacy")

original_controlled_builder = (
    vote_calibration_module.build_controlled_good_exile_probabilities
)
def reject_controlled_distribution(*_args, **_kwargs):
    raise ValueError("synthetic M15-B contract rejection")
vote_calibration_module.build_controlled_good_exile_probabilities = (
    reject_controlled_distribution
)
try:
    fallback_probabilities = rules.build_npc_exile_vote_probabilities(
        left_vote_shadow_state,
        controlled_villager,
        vote_shadow_candidate_ids,
    )
finally:
    vote_calibration_module.build_controlled_good_exile_probabilities = (
        original_controlled_builder
    )
if fallback_probabilities != legacy_villager_probabilities:
    raise SystemExit("a rejected M15-B contract must use the legal legacy fallback")

strong_seer_state = left_vote_shadow_state.model_copy(deep=True)
strong_seer = next(
    character
    for character in strong_seer_state.characters
    if not character.is_player and character.role == "seer"
)
strong_wolf_target = next(
    character
    for character in strong_seer_state.characters
    if character.role == "werewolf"
)
strong_seer_state.sheriff_id = None
strong_seer_state.night_actions.append(
    rules.NightActionState(
        day=1,
        actor_id=strong_seer.id,
        action_type="seer_check",
        target_id=strong_wolf_target.id,
    )
)
strong_seer.suspicion[str(strong_wolf_target.id)] = 100
strong_seer_probabilities = rules.build_npc_exile_vote_probabilities(
    strong_seer_state,
    strong_seer,
    vote_shadow_candidate_ids,
)
if (
    max(strong_seer_probabilities, key=strong_seer_probabilities.get)
    != strong_wolf_target.id
    or strong_seer_probabilities[strong_wolf_target.id] < 0.85
):
    raise SystemExit("a private seer wolf check must remain strongly persuasive")

unpublished_night_swap = left.model_copy(deep=True)
unpublished_night_swap.night_resolutions = [
    rules.NightResolutionState(
        day=1,
        attacked_target_id=hidden_wolf.id,
        protected_ids=[hidden_good.id],
        saved_target_id=hidden_wolf.id,
        poisoned_target_id=hidden_good.id,
        dead_character_ids=[hidden_good.id],
    )
]
unpublished_night_swap.pending_first_night_eliminations = [hidden_good.id]
if villager_snapshot != build_belief_snapshot(
    unpublished_night_swap,
    observer_ids=[villager_observer.id],
):
    raise SystemExit("villager beliefs must ignore unpublished night outcomes")

public_claim_left = left.model_copy(deep=True)
public_claim_left.public_claims = [
    rules.PublicClaimState(
        day=1,
        character_id=hidden_wolf.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=hidden_good.id,
        result="werewolf",
        source="internal_true_source",
    )
]
public_claim_right = public_claim_left.model_copy(deep=True)
public_claim_right.public_claims[0].source = "internal_fake_source"
claim_snapshot = build_belief_snapshot(
    public_claim_left,
    observer_ids=[villager_observer.id],
)
if claim_snapshot != build_belief_snapshot(
    public_claim_right,
    observer_ids=[villager_observer.id],
):
    raise SystemExit("beliefs must ignore the hidden source label of a public claim")
if claim_snapshot == villager_snapshot:
    raise SystemExit("a new public claim must produce a traceable belief change")
public_claim_hidden_swap = public_claim_left.model_copy(deep=True)
claim_hidden_wolf = rules.get_character(public_claim_hidden_swap, hidden_wolf.id)
claim_hidden_good = rules.get_character(public_claim_hidden_swap, hidden_good.id)
claim_hidden_wolf.role, claim_hidden_good.role = (
    claim_hidden_good.role,
    claim_hidden_wolf.role,
)
claim_hidden_wolf.camp, claim_hidden_good.camp = (
    claim_hidden_good.camp,
    claim_hidden_wolf.camp,
)
if claim_snapshot != build_belief_snapshot(
    public_claim_hidden_swap,
    observer_ids=[villager_observer.id],
):
    raise SystemExit("public-claim beliefs must not inspect claimant or target truth")

m06a_state = left.model_copy(deep=True)
m06a_observer_ids = sorted(
    character.id
    for character in m06a_state.characters
    if not character.is_player and character.role == "villager"
)
m06a_hidden_wolf = rules.get_character(
    m06a_state,
    m06a_state.wolf_fake_seer_id,
)
m06a_hidden_good = next(
    character
    for character in m06a_state.characters
    if (
        not character.is_player
        and character.camp == "good"
        and character.role != "villager"
    )
)
m06a_alternate_fake_seer = next(
    character
    for character in m06a_state.characters
    if (
        not character.is_player
        and character.role == "werewolf"
        and character.id != m06a_hidden_wolf.id
    )
)
m06a_state.phase = "DAY_MEETING"
m06a_state.meeting = rules.DayMeetingState(
    day=m06a_state.day,
    direction="clockwise",
    order=m06a_observer_ids,
)
m06a_state.public_claims = [
    rules.PublicClaimState(
        day=m06a_state.day,
        character_id=m06a_hidden_wolf.id,
        claim_type="role",
        claimed_role="seer",
        source="m06a_internal_true_source",
    ),
    rules.PublicClaimState(
        day=m06a_state.day,
        character_id=m06a_hidden_wolf.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=m06a_hidden_good.id,
        result="werewolf",
        source="m06a_internal_true_source",
    ),
]
m06a_state.wolf_fake_seer_id = m06a_hidden_wolf.id
m06a_variants = build_m06a_hidden_variants(
    m06a_state,
    hidden_wolf_id=m06a_hidden_wolf.id,
    hidden_good_id=m06a_hidden_good.id,
    alternate_fake_seer_id=m06a_alternate_fake_seer.id,
)
expected_m06a_variant_ids = {
    "claim_source_rewrite",
    "combined_hidden_mutation",
    "fake_seer_marker_change",
    "hidden_role_truth_swap",
    "role_and_designation_swap",
    "unpublished_night_result",
}
if set(m06a_variants) != expected_m06a_variant_ids:
    raise SystemExit("M06-A must retain every canonical hidden-only mutation")
m06a_report = build_hidden_info_invariance_report(
    m06a_state,
    m06a_variants,
    observer_ids=m06a_observer_ids,
)
expected_m06a_checks = len(m06a_variants) * (
    1 + len(m06a_observer_ids) * len(ACTOR_PROJECTION_NAMES)
)
if (
    m06a_report["schema_version"] != INVARIANCE_SCHEMA_VERSION
    or m06a_report["projection_version"] != INVARIANCE_PROJECTION_VERSION
    or m06a_report["mode"] != INVARIANCE_MODE
    or m06a_report["check_count"] != expected_m06a_checks
    or m06a_report["matched_check_count"] != expected_m06a_checks
    or not m06a_report["passed"]
    or any(not variant["passed"] for variant in m06a_report["variants"])
):
    raise SystemExit("the M06-A legal-perspective matrix must pass every projection")
m06a_reordered_report = build_hidden_info_invariance_report(
    m06a_state,
    dict(reversed(list(m06a_variants.items()))),
    observer_ids=list(reversed(m06a_observer_ids)),
)
if m06a_report != m06a_reordered_report:
    raise SystemExit("M06-A reports must be independent of input ordering")

m15a_observer_id = m06a_observer_ids[0]
m15a_baseline_state = m06a_state.model_copy(deep=True)
m15a_baseline_state.phase = "VOTE"
m15a_candidate_ids = [
    character.id
    for character in m15a_baseline_state.characters
    if character.alive
]
m15a_baseline_projection = build_vote_probability_observation(
    m15a_baseline_state,
    rules.get_character(m15a_baseline_state, m15a_observer_id),
    vote_kind="exile_vote",
    candidate_ids=m15a_candidate_ids,
)
for variant_id, variant in m06a_variants.items():
    vote_variant = variant.model_copy(deep=True)
    vote_variant.phase = "VOTE"
    vote_projection = build_vote_probability_observation(
        vote_variant,
        rules.get_character(vote_variant, m15a_observer_id),
        vote_kind="exile_vote",
        candidate_ids=m15a_candidate_ids,
    )
    if vote_projection != m15a_baseline_projection:
        raise SystemExit(
            f"M15-B good vote control leaked hidden M06-A variant: {variant_id}"
        )

def iter_report_strings(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from iter_report_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_report_strings(nested)
    elif isinstance(value, str):
        yield value

if any(
    value in {"werewolf", "seer", "m06a_internal_true_source"}
    for value in iter_report_strings(m06a_report)
):
    raise SystemExit("M06-A reports must not serialize hidden truth or internal sources")

m06a_public_change = m06a_state.model_copy(deep=True)
m06a_public_change.public_claims[-1].result = "good"
m15a_public_change_state = m06a_public_change.model_copy(deep=True)
m15a_public_change_state.phase = "VOTE"
if build_vote_probability_observation(
    m15a_public_change_state,
    rules.get_character(m15a_public_change_state, m15a_observer_id),
    vote_kind="exile_vote",
    candidate_ids=m15a_candidate_ids,
) == m15a_baseline_projection:
    raise SystemExit("M15-B vote control must react to a changed public check result")
m06a_negative_report = build_hidden_info_invariance_report(
    m06a_state,
    {"public_claim_result_changed": m06a_public_change},
    observer_ids=m06a_observer_ids,
)
if (
    m06a_negative_report["passed"]
    or m06a_negative_report["matched_check_count"]
    == m06a_negative_report["check_count"]
    or not any(
        mismatch["projection"] == "public_state"
        and mismatch["first_difference"]
        for mismatch in m06a_negative_report["variants"][0]["mismatches"]
    )
):
    raise SystemExit("M06-A must detect a public-input change as a negative control")

for unauthorized_state, unauthorized_observer_id in (
    (m06a_state, m06a_hidden_good.id),
    (
        m06a_state.model_copy(
            deep=True,
            update={"sheriff_id": m06a_observer_ids[0]},
        ),
        m06a_observer_ids[0],
    ),
):
    try:
        build_hidden_info_invariance_report(
            unauthorized_state,
            {"unchanged": unauthorized_state.model_copy(deep=True)},
            observer_ids=[unauthorized_observer_id],
        )
    except HiddenInfoInvarianceError:
        pass
    else:
        raise SystemExit("M06-A must reject privileged or sheriff observers")

m06a_privileged_player = m06a_state.model_copy(deep=True)
m06a_player = rules.get_character(
    m06a_privileged_player,
    m06a_privileged_player.player_character_id,
)
m06a_player.role = "seer"
try:
    build_hidden_info_invariance_report(
        m06a_privileged_player,
        {"unchanged": m06a_privileged_player.model_copy(deep=True)},
        observer_ids=[m06a_observer_ids[0]],
    )
except HiddenInfoInvarianceError:
    pass
else:
    raise SystemExit("M06-A must reject a role-privileged player projection")

m06b_state = left.model_copy(deep=True)
m06b_seer = next(
    character
    for character in m06b_state.characters
    if not character.is_player and character.role == "seer"
)
m06b_witch = next(
    character
    for character in m06b_state.characters
    if not character.is_player and character.role == "witch"
)
m06b_wolves = [
    character
    for character in m06b_state.characters
    if not character.is_player and character.role == "werewolf"
]
m06b_villagers = [
    character
    for character in m06b_state.characters
    if not character.is_player and character.role == "villager"
]
m06b_seer_baseline_target = m06b_villagers[0]
m06b_seer_new_target = m06b_wolves[0]
m06b_witch_baseline_target = m06b_villagers[1]
m06b_witch_new_target = m06b_villagers[2]
m06b_wolf_member_out = next(
    character
    for character in m06b_wolves
    if character.id != m06b_state.wolf_fake_seer_id
)
m06b_wolf_member_in = next(
    character
    for character in m06b_state.characters
    if not character.is_player and character.role in {"guard", "hunter"}
)
m06b_state.night_actions = [
    action
    for action in m06b_state.night_actions
    if not (
        action.actor_id == m06b_seer.id
        and action.action_type == "seer_check"
    )
]
m06b_state.night_actions.append(
    rules.NightActionState(
        day=1,
        actor_id=m06b_seer.id,
        action_type="seer_check",
        target_id=m06b_seer_baseline_target.id,
    )
)
m06b_state.night_resolutions = [
    rules.NightResolutionState(
        day=1,
        attacked_target_id=m06b_witch_baseline_target.id,
    )
]
m06b_state.phase = "DAY_MEETING"
m06b_state.sheriff_id = None
m06b_state.meeting = rules.DayMeetingState(
    day=m06b_state.day,
    direction="clockwise",
    order=[
        character.id
        for character in m06b_state.characters
        if not character.is_player
    ],
)
m06b_cases = build_m06b_authorized_cases(
    m06b_state,
    seer_id=m06b_seer.id,
    seer_new_target_id=m06b_seer_new_target.id,
    witch_id=m06b_witch.id,
    witch_new_attack_target_id=m06b_witch_new_target.id,
    wolf_member_out_id=m06b_wolf_member_out.id,
    wolf_member_in_id=m06b_wolf_member_in.id,
)
expected_m06b_case_ids = {
    "seer_private_check_change",
    "witch_private_attack_change",
    "wolf_team_membership_change",
}
if set(m06b_cases) != expected_m06b_case_ids:
    raise SystemExit("M06-B must retain every canonical role-private case")
m06b_report = build_hidden_info_authorization_report(
    m06b_state,
    m06b_cases,
)
m06b_observer_count = sum(
    1
    for character in m06b_state.characters
    if not character.is_player and character.alive
)
expected_m06b_checks = sum(
    1
    + (
        m06b_observer_count - len(case.excluded_observer_ids)
    ) * len(ACTOR_PROJECTION_NAMES)
    for case in m06b_cases.values()
)
if (
    m06b_report["schema_version"] != AUTHORIZATION_SCHEMA_VERSION
    or m06b_report["projection_version"] != INVARIANCE_PROJECTION_VERSION
    or m06b_report["mode"] != AUTHORIZATION_MODE
    or m06b_report["check_count"] != expected_m06b_checks
    or m06b_report["satisfied_check_count"] != expected_m06b_checks
    or expected_m06b_checks != 158
    or not m06b_report["passed"]
    or any(not case["passed"] for case in m06b_report["cases"])
):
    raise SystemExit("the M06-B role authorization matrix must pass all 158 checks")

m06b_observed_by_kind = {
    case["authorization_kind"]: list(
        case["observed_changed_by_observer"].values()
    )
    for case in m06b_report["cases"]
}
if (
    m06b_observed_by_kind["seer_private_check"]
    != [list(ACTOR_PROJECTION_NAMES)]
    or m06b_observed_by_kind["witch_private_attack"]
    != [["belief", "stance", "continuity"]]
    or len(m06b_observed_by_kind["wolf_team_membership"]) != 3
    or any(
        changed_names
        != ["belief", "stance", "decision_context", "continuity"]
        for changed_names in m06b_observed_by_kind["wolf_team_membership"]
    )
):
    raise SystemExit("M06-B private facts must propagate only through legal role layers")

m06b_reordered_report = build_hidden_info_authorization_report(
    m06b_state,
    dict(reversed(list(m06b_cases.items()))),
)
if m06b_report != m06b_reordered_report:
    raise SystemExit("M06-B reports must be independent of case input ordering")
if any(
    value.startswith("belief:private")
    or value in {"werewolf_teammate", "m06b_hidden_truth"}
    for value in iter_report_strings(m06b_report)
):
    raise SystemExit("M06-B reports must not serialize private evidence payloads")
if any("state" in case for case in m06b_report["cases"]):
    raise SystemExit("M06-B reports must not serialize variant game states")

m06b_misdeclared_observer = m06b_villagers[0].id
m06b_seer_case = m06b_cases["seer_private_check_change"]
m06b_negative_report = build_hidden_info_authorization_report(
    m06b_state,
    {
        "misdeclared_seer_authorization": AuthorizedPrivateCase(
            state=m06b_seer_case.state,
            authorization_kind="misdeclared_private_fact",
            required_changed_by_observer={
                m06b_misdeclared_observer: ("belief",),
            },
            allowed_changed_by_observer={
                m06b_misdeclared_observer: ("belief",),
            },
        )
    },
)
m06b_negative_violations = m06b_negative_report["cases"][0]["violations"]
if (
    m06b_negative_report["passed"]
    or not any(
        violation["expectation"] == "changed"
        and not violation["changed"]
        for violation in m06b_negative_violations
    )
    or not any(
        violation["expectation"] == "unchanged"
        and violation["changed"]
        for violation in m06b_negative_violations
    )
):
    raise SystemExit("M06-B must detect missing and misrouted private authorization")

villager_stance = build_stance_snapshot(
    left,
    belief_snapshot=villager_snapshot,
)
hidden_role_stance = build_stance_snapshot(
    hidden_role_swap,
    belief_snapshot=build_belief_snapshot(
        hidden_role_swap,
        observer_ids=[villager_observer.id],
    ),
)
if villager_stance != hidden_role_stance:
    raise SystemExit("villager stances must be invariant to unseen role swaps")

claim_stance_snapshot = build_stance_snapshot(
    public_claim_left,
    belief_snapshot=claim_snapshot,
)
claim_stance_actor = claim_stance_snapshot["actors"][0]
claim_evidence_id = next(
    evidence["evidence_id"]
    for evidence in claim_snapshot["evidence_ledger"]
    if evidence["kind"] == "public_seer_black_check"
)
if (
    claim_stance_actor["primary_suspect_id"] != hidden_good.id
    or claim_stance_actor["provisional_vote_target_id"] != hidden_good.id
    or claim_evidence_id not in claim_stance_actor["basis_evidence_ids"]
):
    raise SystemExit("a stance card must derive its primary read from cited beliefs")

declared_stance_state = public_claim_left.model_copy(deep=True)
declared_stance_state.phase = "DAY_MEETING"
declared_stance_state.speeches = [
    rules.SpeechState(
        day=1,
        character_id=villager_observer.id,
        name=villager_observer.name,
        speech="公开结构化立场测试。",
        is_player=False,
        phase="DAY_MEETING",
        public_position=rules.PublicPositionV1(
            speaker_id=villager_observer.id,
            day=1,
            phase="DAY_MEETING",
            suspected_target_ids=[hidden_wolf.id],
            provisional_vote_target_id=hidden_wolf.id,
            change_condition_target_id=hidden_good.id,
            change_condition="vote_alignment",
        ),
    )
]
declared_belief_snapshot = build_belief_snapshot(
    declared_stance_state,
    observer_ids=[villager_observer.id],
)
declared_stance_snapshot = build_stance_snapshot(
    declared_stance_state,
    belief_snapshot=declared_belief_snapshot,
)
declared_stance_actor = declared_stance_snapshot["actors"][0]
if (
    declared_stance_actor["provisional_vote_target_id"] != hidden_wolf.id
    or declared_stance_actor["verification_target_id"] != hidden_good.id
    or declared_stance_actor["verification_condition"] != "vote_alignment"
):
    raise SystemExit("a stance card must retain structured public commitments")
declared_text_variant = declared_stance_state.model_copy(deep=True)
declared_text_variant.speeches[0].speech = "完全不同的自由文本表达。"
if declared_stance_snapshot != build_stance_snapshot(
    declared_text_variant,
    belief_snapshot=build_belief_snapshot(
        declared_text_variant,
        observer_ids=[villager_observer.id],
    ),
):
    raise SystemExit("stance summaries must not reinterpret public speech text")

stable_stance_recorder = StanceTraceRecorder()
stable_stance_recorder.capture(
    declared_stance_state,
    declared_belief_snapshot,
)
stable_change_count = len(stable_stance_recorder.build_result()["changes"])
phase_only_stance_state = declared_stance_state.model_copy(deep=True)
phase_only_stance_state.phase = "FREE_ACTIVITY"
stable_stance_recorder.capture(
    phase_only_stance_state,
    build_belief_snapshot(
        phase_only_stance_state,
        observer_ids=[villager_observer.id],
    ),
)
if len(stable_stance_recorder.build_result()["changes"]) != stable_change_count:
    raise SystemExit("a phase change without new information must not change stance")

continuity_state = public_claim_left.model_copy(deep=True)
continuity_state.phase = "DAY_MEETING"
continuity_state.speeches = []
continuity_state.votes = []
continuity_recorder = StanceTraceRecorder()
continuity_recorder.capture(
    continuity_state,
    build_belief_snapshot(
        continuity_state,
        observer_ids=[villager_observer.id],
    ),
)
continuity_state.speeches = [
    rules.SpeechState(
        day=1,
        character_id=villager_observer.id,
        name=villager_observer.name,
        speech="我暂时投查杀目标。",
        is_player=False,
        phase="DAY_MEETING",
        public_position=rules.PublicPositionV1(
            speaker_id=villager_observer.id,
            day=1,
            phase="DAY_MEETING",
            suspected_target_ids=[hidden_good.id],
            provisional_vote_target_id=hidden_good.id,
        ),
    )
]
continuity_recorder.capture(
    continuity_state,
    build_belief_snapshot(
        continuity_state,
        observer_ids=[villager_observer.id],
    ),
)
speech_observation = continuity_recorder.build_result()["observations"][-1]
if speech_observation["alignment"] != "aligned":
    raise SystemExit("a speech matching the prior stance must be marked aligned")

unexplained_vote_state = continuity_state.model_copy(deep=True)
unexplained_vote_state.phase = "FREE_ACTIVITY"
unexplained_vote_state.votes = [
    rules.VoteState(
        day=1,
        voter_id=villager_observer.id,
        target_id=hidden_wolf.id,
        reason="无新证据换票测试",
    )
]
continuity_recorder.capture(
    unexplained_vote_state,
    build_belief_snapshot(
        unexplained_vote_state,
        observer_ids=[villager_observer.id],
    ),
)
unexplained_observation = continuity_recorder.build_result()["observations"][-1]
if (
    unexplained_observation["alignment"] != "unexplained_change"
    or unexplained_observation["new_evidence_ids"]
):
    raise SystemExit("a vote switch without intervening evidence must be unexplained")

explained_state = continuity_state.model_copy(deep=True)
explained_recorder = StanceTraceRecorder()
explained_pre_speech_state = public_claim_left.model_copy(deep=True)
explained_pre_speech_state.phase = "DAY_MEETING"
explained_pre_speech_state.speeches = []
explained_pre_speech_state.votes = []
explained_recorder.capture(
    explained_pre_speech_state,
    build_belief_snapshot(
        explained_pre_speech_state,
        observer_ids=[villager_observer.id],
    ),
)
explained_recorder.capture(
    explained_state,
    build_belief_snapshot(
        explained_state,
        observer_ids=[villager_observer.id],
    ),
)
explained_state.public_claims.append(
    rules.PublicClaimState(
        day=1,
        character_id=hidden_good.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=hidden_wolf.id,
        result="werewolf",
        source="structured_test_source",
    )
)
explained_recorder.capture(
    explained_state,
    build_belief_snapshot(
        explained_state,
        observer_ids=[villager_observer.id],
    ),
)
explained_state.phase = "FREE_ACTIVITY"
explained_state.votes = [
    rules.VoteState(
        day=1,
        voter_id=villager_observer.id,
        target_id=hidden_wolf.id,
        reason="新证据后换票测试",
    )
]
explained_recorder.capture(
    explained_state,
    build_belief_snapshot(
        explained_state,
        observer_ids=[villager_observer.id],
    ),
)
explained_observation = explained_recorder.build_result()["observations"][-1]
if (
    explained_observation["alignment"] != "explained_change"
    or not explained_observation["new_evidence_ids"]
):
    raise SystemExit("a vote switch after new belief evidence must be explained")

sheriff_filter_state = left.model_copy(deep=True)
sheriff_filter_state.phase = "SHERIFF_VOTE"
sheriff_filter_state.speeches = []
sheriff_filter_state.votes = []
sheriff_filter_state.sheriff_events = []
sheriff_filter_state.public_claims = [
    rules.PublicClaimState(
        day=1,
        character_id=hidden_wolf.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=hidden_good.id,
        result="good",
        source="structured_test_source",
    )
]
sheriff_candidate_ids = [
    character.id
    for character in sheriff_filter_state.characters
    if character.id not in {villager_observer.id, hidden_good.id}
][:2]
sheriff_filter_state.sheriff_election = rules.SheriffElectionState(
    day=1,
    candidates=sheriff_candidate_ids,
)
sheriff_filter_recorder = StanceTraceRecorder()
sheriff_filter_recorder.capture(
    sheriff_filter_state,
    build_belief_snapshot(
        sheriff_filter_state,
        observer_ids=[villager_observer.id],
    ),
)
sheriff_filter_state.sheriff_events = [
    rules.SheriffEventState(
        day=1,
        event_type="sheriff_vote",
        actor_id=villager_observer.id,
        target_id=sheriff_candidate_ids[0],
        context="round:0",
        detail="合法候选过滤测试",
    )
]
sheriff_filter_recorder.capture(
    sheriff_filter_state,
    build_belief_snapshot(
        sheriff_filter_state,
        observer_ids=[villager_observer.id],
    ),
)
sheriff_filter_observation = sheriff_filter_recorder.build_result()[
    "observations"
][-1]
if (
    sheriff_filter_observation["alignment"] != "unscored"
    or sheriff_filter_observation["expected_target_ids"]
):
    raise SystemExit("non-candidate trust must not count against a sheriff ballot")

def get_belief_contribution(snapshot, actor_id, target_id, evidence_id):
    actor = next(
        item
        for item in snapshot["actors"]
        if item["actor_id"] == actor_id
    )
    seat = next(
        item
        for item in actor["seats"]
        if item["target_id"] == target_id
    )
    return next(
        item
        for item in seat["contributions"]
        if item["evidence_id"] == evidence_id
    )

if PUBLIC_SOFT_EVIDENCE_DAILY_DECAY != 0.75:
    raise SystemExit("M03-B public soft-evidence decay must stay explicitly versioned")
claim_evidence = next(
    evidence
    for evidence in claim_snapshot["evidence_ledger"]
    if evidence["kind"] == "public_seer_black_check"
)
claim_contribution_day_one = get_belief_contribution(
    claim_snapshot,
    villager_observer.id,
    hidden_good.id,
    claim_evidence["evidence_id"],
)
public_claim_day_two = public_claim_left.model_copy(deep=True)
public_claim_day_two.day = 2
claim_snapshot_day_two = build_belief_snapshot(
    public_claim_day_two,
    observer_ids=[villager_observer.id],
)
claim_contribution_day_two = get_belief_contribution(
    claim_snapshot_day_two,
    villager_observer.id,
    hidden_good.id,
    claim_evidence["evidence_id"],
)
if not (
    0 < abs(claim_contribution_day_two["weight"])
    < abs(claim_contribution_day_one["weight"])
):
    raise SystemExit("an old public claim must lose soft belief weight across days")

decay_recorder = BeliefTraceRecorder()
decay_recorder.capture(public_claim_left)
decay_recorder.capture(public_claim_day_two)
decay_trace = decay_recorder.build_result()
if not any(
    contribution["evidence_id"] == claim_evidence["evidence_id"]
    and contribution["weight"] == claim_contribution_day_two["weight"]
    for change in decay_trace["changes"]
    for contribution in change["updated_contributions"]
):
    raise SystemExit("soft-evidence decay must be traceable as an updated contribution")

hard_vote_state = left.model_copy(deep=True)
hard_vote_state.day = 1
hard_vote_state.phase = "FREE_ACTIVITY"
hard_vote_state.public_claims = []
hard_vote_state.votes = [
    rules.VoteState(
        day=1,
        voter_id=hard_vote_state.player_character_id,
        target_id=hidden_good.id,
        reason="公开票型测试",
    )
]
hard_vote_day_one = build_belief_snapshot(
    hard_vote_state,
    observer_ids=[villager_observer.id],
)
hard_vote_evidence = next(
    evidence
    for evidence in hard_vote_day_one["evidence_ledger"]
    if evidence["kind"] == "public_exile_vote"
)
hard_vote_contribution_day_one = get_belief_contribution(
    hard_vote_day_one,
    villager_observer.id,
    hidden_good.id,
    hard_vote_evidence["evidence_id"],
)
hard_vote_state.day = 2
hard_vote_day_two = build_belief_snapshot(
    hard_vote_state,
    observer_ids=[villager_observer.id],
)
hard_vote_contribution_day_two = get_belief_contribution(
    hard_vote_day_two,
    villager_observer.id,
    hidden_good.id,
    hard_vote_evidence["evidence_id"],
)
if hard_vote_contribution_day_one != hard_vote_contribution_day_two:
    raise SystemExit("observed public ballots must not decay as soft speech evidence")

private_fact_state = rules.create_wolf_game_state(
    rules.GameStartRequest(
        player_name="私有事实衰减测试",
        player_role="villager",
        enable_llm=False,
        enable_rag=False,
    ),
    game_id="private_fact_decay",
    random_seed=271828,
)
private_seer = next(
    character
    for character in private_fact_state.characters
    if not character.is_player and character.role == "seer"
)
private_check_target = next(
    character
    for character in private_fact_state.characters
    if character.id != private_seer.id
)
private_fact_state.night_actions = [
    rules.NightActionState(
        day=1,
        actor_id=private_seer.id,
        action_type="seer_check",
        target_id=private_check_target.id,
    )
]
private_fact_day_one = build_belief_snapshot(
    private_fact_state,
    observer_ids=[private_seer.id],
)
private_seer_evidence = next(
    evidence
    for evidence in private_fact_day_one["evidence_ledger"]
    if evidence["kind"] == "private_seer_check"
)
private_seer_contribution_day_one = get_belief_contribution(
    private_fact_day_one,
    private_seer.id,
    private_check_target.id,
    private_seer_evidence["evidence_id"],
)
private_fact_state.day = 3
private_fact_day_three = build_belief_snapshot(
    private_fact_state,
    observer_ids=[private_seer.id],
)
private_seer_contribution_day_three = get_belief_contribution(
    private_fact_day_three,
    private_seer.id,
    private_check_target.id,
    private_seer_evidence["evidence_id"],
)
if private_seer_contribution_day_one != private_seer_contribution_day_three:
    raise SystemExit("a seer's legal private result must not decay")

private_wolf = next(
    character
    for character in private_fact_state.characters
    if not character.is_player and character.role == "werewolf"
)
private_teammate = next(
    character
    for character in private_fact_state.characters
    if character.id != private_wolf.id and character.role == "werewolf"
)
private_wolf_snapshot = build_belief_snapshot(
    private_fact_state,
    observer_ids=[private_wolf.id],
)
wolf_team_evidence = next(
    evidence
    for evidence in private_wolf_snapshot["evidence_ledger"]
    if evidence["kind"] == "private_wolf_teammate"
    and evidence["target_id"] == private_teammate.id
)
wolf_team_contribution = get_belief_contribution(
    private_wolf_snapshot,
    private_wolf.id,
    private_teammate.id,
    wolf_team_evidence["evidence_id"],
)
if wolf_team_contribution["weight"] != -100:
    raise SystemExit("authorized wolf-team knowledge must remain certain")

legacy_state_noise = left.model_copy(deep=True)
legacy_observer = rules.get_character(legacy_state_noise, villager_observer.id)
legacy_observer.suspicion = {
    str(character.id): 99
    for character in legacy_state_noise.characters
    if character.id != legacy_observer.id
}
for relationship in legacy_observer.relationships.values():
    relationship["trust"] = 0.01
if villager_snapshot != build_belief_snapshot(
    legacy_state_noise,
    observer_ids=[villager_observer.id],
):
    raise SystemExit("shadow beliefs must be derived from evidence, not legacy mutable scores")

wolf_observer = next(
    character
    for character in left.characters
    if (
        not character.is_player
        and character.role == "werewolf"
        and character.id not in {hidden_wolf.id, hidden_good.id}
    )
)
if build_belief_snapshot(
    left,
    observer_ids=[wolf_observer.id],
) == build_belief_snapshot(
    hidden_role_swap,
    observer_ids=[wolf_observer.id],
):
    raise SystemExit("a wolf observer must retain its authorized teammate knowledge")
wolf_vote_shadow = build_vote_probability_observation(
    left_vote_shadow_state,
    rules.get_character(left_vote_shadow_state, wolf_observer.id),
    vote_kind="exile_vote",
    candidate_ids=vote_shadow_candidate_ids,
)
changed_wolf_vote_shadow = build_vote_probability_observation(
    hidden_vote_shadow_state,
    rules.get_character(hidden_vote_shadow_state, wolf_observer.id),
    vote_kind="exile_vote",
    candidate_ids=vote_shadow_candidate_ids,
)
if wolf_vote_shadow == changed_wolf_vote_shadow:
    raise SystemExit("a wolf vote shadow must retain authorized team knowledge")

without_beliefs = run_rule_simulation(20260719, capture_beliefs=False)
if (
    without_beliefs["belief_trace"] is not None
    or without_beliefs["stance_trace"] is not None
):
    raise SystemExit("the shadow-off regression run must omit both traces")
if first["gameplay_digest"] != without_beliefs["gameplay_digest"]:
    raise SystemExit("shadow belief capture must not change any gameplay outcome")

without_stances = run_rule_simulation(20260719, capture_stances=False)
if without_stances["stance_trace"] is not None:
    raise SystemExit("stance-off mode must omit only its stance trace")
if without_stances["belief_trace"] != first["belief_trace"]:
    raise SystemExit("shadow stance capture must not change belief history")
if without_stances["gameplay_digest"] != first["gameplay_digest"]:
    raise SystemExit("shadow stance capture must not change gameplay")

left.phase = "VOTE"
choice_before_hidden_swap = _choose_public_player_target(left, "hidden_swap_check")
hidden_swap = left.model_copy(deep=True)
wolf = next(
    character
    for character in hidden_swap.characters
    if not character.is_player and character.role == "werewolf"
)
good = next(
    character
    for character in hidden_swap.characters
    if not character.is_player and character.camp == "good"
)
wolf.role, good.role = good.role, wolf.role
wolf.camp, good.camp = good.camp, wolf.camp
choice_after_hidden_swap = _choose_public_player_target(
    hidden_swap,
    "hidden_swap_check",
)
if choice_before_hidden_swap != choice_after_hidden_swap:
    raise SystemExit("good-player policy must be invariant to unseen NPC role swaps")

print("headless simulation smoke test passed")
'''
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="headless deterministic simulation smoke test failed",
    )
    print("[OK] Simulations, M06-A/B matrices, V3.1-L witch, and V3.1-M seer strategies are deterministic.")


def check_backend_search() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = """
from app.main import reload_config, search_knowledge
from app.main import get_relationship_hint, get_relationship_level
from app.rag import LocalVectorIndex
import os

reload_config()
cases = [
    ("Guide", "Godot 玩家移动怎么做"),
    ("Guide", "Top-K 检索是什么"),
    ("Archivist", "记忆文件保存在哪里"),
    ("Archivist", "资料馆是什么"),
]

for npc_name, message in cases:
    result = search_knowledge(npc_name=npc_name, message=message, limit=3)
    if not result.matched or not result.results:
        raise SystemExit(f"{npc_name} did not match knowledge for: {message}")

semantic_result = search_knowledge(
    npc_name="梅长苏",
    message="有什么办法确认别人属于哪个阵营",
    limit=5,
)
if semantic_result.retrieval_mode == "hybrid":
    semantic_titles = [result.item.title for result in semantic_result.results]
    if "预言家查验能力" not in semantic_titles:
        raise SystemExit("hybrid retrieval should semantically recall the seer-check knowledge")
elif semantic_result.retrieval_mode != "keyword":
    raise SystemExit(f"unknown retrieval mode: {semantic_result.retrieval_mode}")

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
fallback_index = LocalVectorIndex()
fallback_index.configure(["预言家每晚可以查验一名玩家。"])
if fallback_index.search("怎么确认阵营"):
    raise SystemExit("disabled vector RAG should not return vector scores")
if fallback_index.status()["mode"] != "keyword":
    raise SystemExit("disabled vector RAG should stay in keyword mode")
del os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"]

expected_relationships = {
    1: "初次见面",
    2: "熟悉",
    4: "信任",
    7: "老朋友",
}
for memory_count, expected_level in expected_relationships.items():
    actual_level = get_relationship_level(memory_count)
    if actual_level != expected_level:
        raise SystemExit(f"relationship level mismatch: {memory_count} -> {actual_level}")

relationship_hints = []
for memory_count in expected_relationships:
    relationship_hint = get_relationship_hint(memory_count)
    if not relationship_hint:
        raise SystemExit(f"missing relationship hint for: {memory_count}")
    relationship_hints.append(relationship_hint)

if len(set(relationship_hints)) != len(relationship_hints):
    raise SystemExit("relationship hints should differ by relationship stage")

print("backend search matched", len(cases), "cases")
"""
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message=(
            "backend search smoke test failed. "
            "If dependencies are missing, run: cd backend && source .venv/bin/activate && pip install -r requirements.txt"
        ),
    )
    print("[OK] Backend knowledge search works.")


def check_resident_chat() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = r'''
import json
import tempfile
from pathlib import Path

import httpx

import app.main as main_module
from app.llm import LLMClient, LLMGeneration, LLMSettings
from app.main import ChatRequest, chat, validate_resident_chat_generation

captured_contexts = []


def resident_handler(request: httpx.Request) -> httpx.Response:
    if not main_module.MEMORY_LOCK.acquire(blocking=False):
        raise RuntimeError("resident LLM request must run outside MEMORY_LOCK")
    main_module.MEMORY_LOCK.release()
    request_payload = json.loads(request.content.decode("utf-8"))
    context = json.loads(request_payload["messages"][1]["content"])
    captured_contexts.append(context)
    resident_name = context["resident"]["name"]
    response_text = (
        "我在呢，慢慢说就好。"
        if resident_name == "坏坏"
        else "好呀，我们从最有意思的一步开始！"
    )
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {"content": json.dumps({"text": response_text}, ensure_ascii=False)},
                    "finish_reason": "stop",
                }
            ]
        },
    )


settings = LLMSettings(
    enabled=True,
    provider="deepseek",
    base_url="https://resident.invalid/v1",
    api_key="test-key",
    model="deepseek-chat",
    max_retries=0,
)

with tempfile.TemporaryDirectory() as temp_dir:
    main_module.MEMORY_FILE = Path(temp_dir) / "memory.json"
    main_module.MEMORY_STORE.clear()
    main_module.LLM_CLIENT = LLMClient(settings, transport=httpx.MockTransport(resident_handler))

    first_bad = chat(ChatRequest(npc_name="坏坏", message="你好", player_id="player-a", game_phase="NIGHT"))
    if not first_bad.llm_used or first_bad.llm_provider != "deepseek":
        raise SystemExit("坏坏 should use configured DeepSeek chat")
    if first_bad.memory_count != 1 or first_bad.relationship_level != "初次见面":
        raise SystemExit("坏坏 should start an isolated long-term memory")
    if captured_contexts[-1]["current_phase"] != "NIGHT":
        raise SystemExit("resident chat context should include the current rule phase")
    if "小恐龙" not in captured_contexts[-1]["resident"]["role"]:
        raise SystemExit("坏坏 chat context should preserve the little-dinosaur identity")

    first_ran = chat(ChatRequest(npc_name="然然", message="想做一个计划", player_id="player-a"))
    if not first_ran.llm_used or first_ran.memory_count != 1:
        raise SystemExit("然然 should use DeepSeek with memory separate from 坏坏")
    if "熊猫" not in captured_contexts[-1]["resident"]["role"]:
        raise SystemExit("然然 chat context should preserve the panda identity")

    second_bad = chat(ChatRequest(npc_name="坏坏", message="还记得我吗", player_id="player-a"))
    if second_bad.memory_count != 2 or len(captured_contexts[-1]["recent_conversations"]) != 1:
        raise SystemExit("resident chat should pass recent same-resident memory to DeepSeek")
    if captured_contexts[-1]["resident"]["participates_in_werewolf_game"] is not False:
        raise SystemExit("resident context must explicitly exclude wolf-game participation")
    if len(captured_contexts[-1]["recent_conversations"]) > main_module.RESIDENT_CHAT_MEMORY_LIMIT:
        raise SystemExit("resident LLM context must stay bounded")

    other_player = chat(ChatRequest(npc_name="坏坏", message="你好", player_id="player-b"))
    if other_player.memory_count != 1:
        raise SystemExit("resident memory should be isolated by player_id")

    calls_before_guide = len(captured_contexts)
    guide = chat(ChatRequest(npc_name="Guide", message="你好", player_id="player-a"))
    if guide.llm_used or guide.llm_provider != "rule" or len(captured_contexts) != calls_before_guide:
        raise SystemExit("ordinary profiles should keep deterministic /chat behavior")

    main_module.LLM_CLIENT = LLMClient(LLMSettings(enabled=False, provider="deepseek"))
    fallback = chat(ChatRequest(npc_name="然然", message="今天有点累", player_id="player-a"))
    if fallback.llm_used or not fallback.llm_fallback_reason or fallback.memory_count != 2:
        raise SystemExit("disabled resident LLM should fall back and still save memory")
    if not fallback.reply or not main_module.MEMORY_FILE.exists():
        raise SystemExit("resident fallback should be useful and persisted")
    if "邮差包" not in fallback.reply:
        raise SystemExit("然然 fallback should keep a small amount of panda-postal characterization")

    persisted = json.loads(main_module.MEMORY_FILE.read_text(encoding="utf-8"))
    if len(persisted.get("player-a::坏坏", [])) != 2:
        raise SystemExit("坏坏 long-term memory was not persisted")
    if len(persisted.get("player-a::然然", [])) != 2:
        raise SystemExit("然然 long-term memory was not persisted")

    natural_chat = validate_resident_chat_generation(
        LLMGeneration(
            text="我不参加这局狼人杀，不过可以陪你复盘公开规则。",
            used_llm=True,
            provider="deepseek",
            model="deepseek-chat",
        ),
        "fallback",
    )
    if not natural_chat.used_llm:
        raise SystemExit("resident validation must not reject natural game-related chat")
    overlong_chat = validate_resident_chat_generation(
        LLMGeneration(
            text="太" * (main_module.RESIDENT_CHAT_MAX_LENGTH + 1),
            used_llm=True,
            provider="deepseek",
            model="deepseek-chat",
        ),
        "fallback",
    )
    if overlong_chat.used_llm or overlong_chat.text != "fallback":
        raise SystemExit("resident validation should safely reject structurally invalid output")

print("resident chat smoke test passed")
'''
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="resident DeepSeek chat and memory smoke test failed",
    )
    print("[OK] Resident DeepSeek chat, safe fallback, and isolated long-term memory work.")


def check_wolf_game_start() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = """
from collections import Counter
import json
from pathlib import Path

from fastapi import HTTPException

import app.main as main_module
from app.belief import build_belief_snapshot
from app.llm import LLMGeneration, LLMJsonGeneration
from app.llm_observability import summarize_observation_events
from app.npc_decision import (
    PublicPositionV1,
    PublicSpeechIntent,
    PublicSpeechPlanV2,
    validate_public_speech_plan,
)
from app.main import DayMeetingState, EliminationState, GAME_STORE, GameStartRequest
from app.main import HunterShotRequest, HunterShotState
from app.main import NightActionRequest, NightActionState, NightResolutionState, NightResolveRequest
from app.main import EndFreeActivityRequest, NpcSpeechRequest
from app.main import PlayerSpeechRequest
from app.main import PlayerVoteRequest, PrivateChatRequest, PrivateConversationState
from app.main import BadgeTransferRequest, SheriffElectionState, SheriffEventState, SheriffMeetingOrderRequest, SheriffNominationRequest
from app.main import SheriffSignupRequest, SheriffSpeechRequest, SheriffVoteRequest
from app.main import SheriffWithdrawalRequest, SpeechState, VoteState
from app.main import build_public_decision_rag_context, end_free_activity
from app.main import generate_npc_sheriff_campaign_speech, generate_npc_speech, private_chat
from app.main import get_game_summary, get_wolf_game_state, initialize_social_state
from app.main import resolve_hunter_shot, resolve_night
from app.main import start_wolf_game, submit_night_action
from app.main import submit_and_resolve_all_votes, submit_and_resolve_sheriff_vote
from app.main import submit_player_sheriff_speech, submit_player_speech
from app.main import submit_sheriff_meeting_order, submit_sheriff_nomination
from app.main import submit_badge_transfer, submit_sheriff_signup, submit_sheriff_withdrawal

captured_validation_observations = []

class InMemoryObservationRecorder:
    def record_event(self, event):
        captured_validation_observations.append(event)

main_module.LLM_OBSERVABILITY_RECORDER = InMemoryObservationRecorder()

forced_witch_response = start_wolf_game(
    GameStartRequest(player_name="女巫测试玩家", player_role="witch")
)
forced_witch_state = GAME_STORE[forced_witch_response.game_id]
forced_witch_player = forced_witch_state.characters[0]
if forced_witch_player.role != "witch":
    raise SystemExit("specified player role should assign witch to the player")
if Counter(character.role for character in forced_witch_state.characters) != Counter(main_module.DEFAULT_WOLF_ROLES):
    raise SystemExit("specified player role must preserve the twelve-player role pool")
witch_private = get_wolf_game_state(forced_witch_response.game_id).player_private_info
if not witch_private.witch_antidote_available or not witch_private.witch_poison_available:
    raise SystemExit("player witch should receive both potion resources")

response = start_wolf_game(
    GameStartRequest(player_name="测试玩家", enable_rag=True)
)
if response.day != 1 or response.phase != "NIGHT":
    raise SystemExit("new game should start at day 1 NIGHT")
if len(response.characters) != 12:
    raise SystemExit("new game should create 12 characters")

player_view = next(character for character in response.characters if character.is_player)
npc_views = [character for character in response.characters if not character.is_player]
game_state = GAME_STORE[response.game_id]
player = next(character for character in game_state.characters if character.is_player)
if player_view.role_visible_to_player is None:
    raise SystemExit("player role should be visible to player")
visible_npc_ids = {
    character.id
    for character in npc_views
    if character.role_visible_to_player is not None
}
if player_view.role_visible_to_player == "werewolf":
    expected_visible_npc_ids = {
        character.id
        for character in game_state.characters
        if character.role == "werewolf" and not character.is_player
    }
    if visible_npc_ids != expected_visible_npc_ids:
        raise SystemExit("werewolf player should see exactly the three wolf teammates")
elif visible_npc_ids:
    raise SystemExit("non-werewolf player should not see NPC roles")

role_counts = Counter(character.role for character in game_state.characters)
expected_roles = {
    "werewolf": 4,
    "seer": 1,
    "witch": 1,
    "hunter": 1,
    "guard": 1,
    "villager": 4,
}
if dict(role_counts) != expected_roles:
    raise SystemExit(f"unexpected role assignment: {role_counts}")

state_response = get_wolf_game_state(response.game_id)
if state_response.player_private_info.role != player_view.role_visible_to_player:
    raise SystemExit("state response should keep player private role")
if len(state_response.characters) != 12:
    raise SystemExit("state response should include 12 character views")
if not state_response.public_logs:
    raise SystemExit("state response should include public logs")
if player.role == "werewolf" and len(state_response.player_private_info.wolf_teammates) != 3:
    raise SystemExit("werewolf private state should list three teammates")

alive_targets = [
    character
    for character in game_state.characters
    if character.alive and character.id != player.id
]
stable_night_target = next(
    character
    for character in alive_targets
    if character.role == "villager"
)
game_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=character.id,
        action_type="werewolf_kill" if character.role == "werewolf" else "none",
        target_id=stable_night_target.id if character.role == "werewolf" else None,
    )
    for character in game_state.characters
    if not character.is_player
]

if player.role == "werewolf":
    target = stable_night_target
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="werewolf_kill",
        target_id=target.id,
    )
elif player.role == "seer":
    target = alive_targets[0]
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="seer_check",
        target_id=target.id,
    )
elif player.role == "guard":
    target = alive_targets[0]
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="guard_protect",
        target_id=target.id,
    )
elif player.role == "witch":
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="none",
        target_id=None,
    )
else:
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="none",
        target_id=None,
    )

action_response = submit_night_action(action)
if not action_response.success:
    raise SystemExit("night action should be accepted")

resolve_response = resolve_night(NightResolveRequest(game_id=response.game_id))
if resolve_response.game_id != response.game_id:
    raise SystemExit("night resolve should keep game id")
if GAME_STORE[response.game_id].phase != "SHERIFF_SIGNUP":
    raise SystemExit("first night should enter SHERIFF_SIGNUP before the day meeting")
if not resolve_response.public_message:
    raise SystemExit("night resolve should return a public message")
if player.role == "seer" and "seer_check" not in resolve_response.player_private_result:
    raise SystemExit("seer player should receive private check result")

expected_npc_names = [
    "梅西", "C罗", "周深", "梅长苏", "塞尔达", "小骑士",
    "大黄蜂", "喜羊羊", "懒羊羊", "洛洛", "奇异博士",
]
if [character.name for character in game_state.characters[1:]] != expected_npc_names:
    raise SystemExit("wolf game should use the eleven fixed town NPC names")

signup_response = submit_sheriff_signup(
    SheriffSignupRequest(
        game_id=response.game_id,
        character_id=player.id,
        run_for_sheriff=True,
    )
)
if not signup_response.success or player.id not in signup_response.candidates:
    raise SystemExit("player sheriff signup should add the player to candidate list")
if game_state.phase != "SHERIFF_SPEECH":
    raise SystemExit("completed sheriff signup should enter SHERIFF_SPEECH")

sheriff_speech_order = list(game_state.sheriff_election.speech_order)
while game_state.phase == "SHERIFF_SPEECH":
    current_speaker_id = main_module.get_current_sheriff_speaker_id(game_state)
    current_speaker = main_module.get_character(game_state, current_speaker_id)
    if current_speaker.is_player:
        campaign_response = submit_player_sheriff_speech(
            SheriffSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
                speech="我上警竞选，会结合后续票型给出判断。",
            )
        )
    else:
        campaign_response = generate_npc_sheriff_campaign_speech(
            SheriffSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
            )
        )
        if not campaign_response.speech.evidence_titles:
            raise SystemExit("NPC sheriff speech should expose public RAG evidence")
    if campaign_response.speech.character_id != current_speaker.id:
        raise SystemExit("sheriff speech should follow the candidate order")

if game_state.phase != "SHERIFF_WITHDRAWAL":
    raise SystemExit("sheriff speeches should always enter the withdrawal phase")
withdraw_response = submit_sheriff_withdrawal(
    SheriffWithdrawalRequest(
        game_id=response.game_id,
        character_id=player.id,
        withdraw=False,
    )
)
if not withdraw_response.success:
    raise SystemExit("withdrawal phase should accept the player's stay decision")
if player.id in game_state.sheriff_election.withdrawn:
    raise SystemExit("continue campaign should keep the player in the active sheriff candidates")

while game_state.phase in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE"}:
    if game_state.phase == "SHERIFF_RUNOFF_SPEECH":
        current_speaker_id = main_module.get_current_sheriff_speaker_id(game_state)
        current_speaker = main_module.get_character(game_state, current_speaker_id)
        if current_speaker.is_player:
            submit_player_sheriff_speech(
                SheriffSpeechRequest(
                    game_id=response.game_id,
                    character_id=current_speaker.id,
                    speech="PK 阶段我继续坚持自己的警徽流判断。",
                )
            )
        else:
            generate_npc_sheriff_campaign_speech(
                SheriffSpeechRequest(
                    game_id=response.game_id,
                    character_id=current_speaker.id,
                )
            )
        continue
    active_candidates = main_module.get_active_sheriff_candidates(game_state)
    player_can_vote = player.alive and player.id not in active_candidates
    sheriff_vote_response = submit_and_resolve_sheriff_vote(
        SheriffVoteRequest(
            game_id=response.game_id,
            character_id=player.id,
            target_id=active_candidates[0] if player_can_vote else None,
        )
    )
    if not sheriff_vote_response.ballots:
        raise SystemExit("sheriff vote should reveal all eligible ballots together")

if game_state.sheriff_election is None or not game_state.sheriff_election.completed:
    raise SystemExit("sheriff election should finish before the town meeting")
if game_state.phase == "MEETING_ORDER":
    order_view = get_wolf_game_state(response.game_id).sheriff
    if not order_view.order_options:
        raise SystemExit("player sheriff should receive left/right meeting-order choices")
    submit_sheriff_meeting_order(
        SheriffMeetingOrderRequest(
            game_id=response.game_id,
            character_id=player.id,
            side="left",
        )
    )
if game_state.phase != "DAY_MEETING":
    raise SystemExit("sheriff election should continue into DAY_MEETING")

meeting_state = get_wolf_game_state(response.game_id).meeting
alive_ids = {character.id for character in game_state.characters if character.alive}
if set(meeting_state.order) != alive_ids or len(meeting_state.order) != len(alive_ids):
    raise SystemExit("meeting order should contain each alive character exactly once")
if meeting_state.direction not in {"clockwise", "counterclockwise"}:
    raise SystemExit("meeting direction should be clockwise or counterclockwise")

spoken_order = []
player_speech_target = next(
    (character for character in game_state.characters if character.alive and not character.is_player),
    None,
)
while game_state.phase == "DAY_MEETING":
    current_speaker_id = game_state.meeting.order[game_state.meeting.current_index]
    current_speaker = game_state.characters[current_speaker_id - 1]
    spoken_order.append(current_speaker_id)

    if current_speaker.is_player:
        speech_text = "目前信息还少，我先听大家发言。"
        if player_speech_target is not None:
            speech_text = f"我觉得{player_speech_target.id}号很可疑，今天需要解释一下。"
        speech_response = submit_player_speech(
            PlayerSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
                speech=speech_text,
            )
        )
        if player_speech_target is not None and player_speech_target.id not in speech_response.parsed.mentioned_characters:
            raise SystemExit("player speech parser should detect mentioned character")
    else:
        npc_speech_response = generate_npc_speech(
            NpcSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
            )
        )
        if npc_speech_response.speech.character_id != current_speaker.id:
            raise SystemExit("only the current NPC speaker should produce a speech")
        if not npc_speech_response.speech.evidence_titles:
            raise SystemExit("NPC public speech should expose RAG evidence titles")
        if not any(marker in npc_speech_response.speech.speech for marker in ["参考", "结合知识"]):
            raise SystemExit("NPC public speech should incorporate retrieved evidence")
        if "\ufffd" in npc_speech_response.speech.speech:
            raise SystemExit("NPC public speech must not contain Unicode replacement characters")
        if any("私有记忆" in title for title in npc_speech_response.speech.evidence_titles):
            raise SystemExit("NPC public speech must not expose private-memory evidence")
        if npc_speech_response.speech.llm_used:
            raise SystemExit("default wolf-game smoke test should not call a real LLM")

if spoken_order != meeting_state.order:
    raise SystemExit("characters should speak in the generated meeting order")
if game_state.phase == "SHERIFF_NOMINATION":
    nomination_target = next(
        character
        for character in game_state.characters
        if character.alive and character.id != player.id
    )
    submit_sheriff_nomination(
        SheriffNominationRequest(
            game_id=response.game_id,
            character_id=player.id,
            target_id=nomination_target.id,
        )
    )
if game_state.phase != "FREE_ACTIVITY":
    raise SystemExit("completed meeting and sheriff nomination should enter FREE_ACTIVITY")
if player.alive and player_speech_target is not None:
    recorded_player_speech = next(
        speech
        for speech in game_state.speeches
        if speech.day == game_state.day
        and speech.is_player
        and speech.phase == "DAY_MEETING"
    )
    if recorded_player_speech.focus_target_id != player_speech_target.id:
        raise SystemExit("a player's public accusation should retain its public focus target")

free_activity_response = end_free_activity(EndFreeActivityRequest(game_id=response.game_id))
if not free_activity_response.success or game_state.phase != "VOTE":
    raise SystemExit("ending free activity should enter VOTE")

social_snapshot = {}
for character in game_state.characters:
    if character.is_player:
        continue
    social_snapshot[character.id] = {
        "suspicion": dict(character.suspicion),
        "trust": {
            character_id: float(relationship.get("trust", 0.5))
            for character_id, relationship in character.relationships.items()
        },
    }

vote_target_id = None
if player.alive:
    if game_state.sheriff_id == player.id and game_state.meeting is not None:
        vote_target_id = game_state.meeting.nomination_target_id
    if vote_target_id is None:
        vote_target_id = next(
            character.id
            for character in game_state.characters
            if character.alive and character.id != player.id
        )
sheriff_before_vote = game_state.sheriff_id
vote_resolve_response = submit_and_resolve_all_votes(
    PlayerVoteRequest(
        game_id=response.game_id,
        character_id=player.id,
        target_id=vote_target_id,
        reason="这是玩家同时提交的投票理由。",
    )
)
if not vote_resolve_response.public_message:
    raise SystemExit("vote resolve should return a public message")
if not vote_resolve_response.ballots or not vote_resolve_response.vote_totals:
    raise SystemExit("combined vote should return ballot summary and weighted totals")
for vote in vote_resolve_response.ballots:
    if vote.voter_id != player.id and not vote.evidence_titles:
        raise SystemExit("NPC vote reason should expose RAG evidence titles")
    if "\ufffd" in vote.reason or any("私有记忆" in title for title in vote.evidence_titles):
        raise SystemExit("combined vote evidence must be clean and public-safe")
if sheriff_before_vote is not None:
    sheriff_ballot = next(
        (vote for vote in vote_resolve_response.ballots if vote.voter_id == sheriff_before_vote),
        None,
    )
    if sheriff_ballot is not None and sheriff_ballot.weight != 1.5:
        raise SystemExit("sheriff ballot should count as 1.5 votes")
if GAME_STORE[response.game_id].phase not in {"NIGHT", "GAME_OVER"}:
    raise SystemExit("vote resolve should move game to next NIGHT or GAME_OVER")

social_changed = False
for character in GAME_STORE[response.game_id].characters:
    if character.is_player:
        continue
    before = social_snapshot.get(character.id)
    if before is None:
        continue
    current_trust = {
        character_id: float(relationship.get("trust", 0.5))
        for character_id, relationship in character.relationships.items()
    }
    if before["suspicion"] != character.suspicion or before["trust"] != current_trust:
        social_changed = True
        break
if not social_changed:
    raise SystemExit("vote resolve should update NPC suspicion or trust state")

state_after_vote = get_wolf_game_state(response.game_id)
if any(character.trust_to_player is None for character in state_after_vote.characters if not character.is_player):
    raise SystemExit("NPC character views should expose trust_to_player")

def select_test_fake_seer(characters):
    if not any(
        not character.is_player and character.role == "werewolf"
        for character in characters
    ):
        return None
    for test_seed in range(1_000):
        fake_seer_id = main_module.choose_designated_fake_seer(
            characters,
            test_seed,
        )
        if fake_seer_id is not None:
            return fake_seer_id
    raise SystemExit("test fixture must find a deterministic fake-seer campaign seed")

def make_rule_test_game(roles):
    if len(roles) > 12:
        raise SystemExit("rule test role list cannot exceed 12 characters")
    expanded_roles = list(roles) + ["villager"] * (12 - len(roles))
    response = start_wolf_game(GameStartRequest(player_name="规则测试"))
    game_state = GAME_STORE[response.game_id]
    for index, role in enumerate(expanded_roles):
        character = game_state.characters[index]
        character.role = role
        character.camp = "werewolf" if role == "werewolf" else "good"
        character.alive = True
        character.memory_summary = ""
        character.strategy_tuning = (
            {}
            if character.is_player
            else main_module.resolve_current_npc_tuning(
                character.name,
                character.camp,
                character.role,
            ).model_dump(mode="json")
        )
    initialize_social_state(game_state.characters)
    game_state.day = 1
    game_state.phase = "NIGHT"
    game_state.night_actions = []
    game_state.votes = []
    game_state.speeches = []
    game_state.private_conversations = []
    game_state.eliminations = []
    game_state.pending_first_night_eliminations = []
    game_state.first_night_result_pending = False
    game_state.night_resolutions = []
    game_state.hunter_shots = []
    game_state.public_claims = []
    game_state.badge_flows = []
    game_state.public_logs = []
    game_state.sheriff_id = None
    game_state.sheriff_election = SheriffElectionState(completed=True)
    game_state.sheriff_events = []
    game_state.badge_destroyed = True
    game_state.meeting_order_anchor_id = None
    game_state.meeting_order_anchor_type = ""
    game_state.pending_badge_transfer_from_id = None
    game_state.pending_badge_continuation = ""
    game_state.wolf_checked_wolf_used = False
    game_state.llm_validation_failures = []
    game_state.pending_hunter_id = None
    game_state.pending_hunter_trigger = ""
    game_state.pending_hunter_continuation = ""
    game_state.winner = None
    game_state.winner_reason = ""
    game_state.wolf_fake_seer_id = select_test_fake_seer(game_state.characters)
    main_module.initialize_role_resources(game_state)
    player = game_state.characters[0]
    game_state.player_private_info = main_module.build_player_private_info_dict(game_state)
    return game_state

seat_boundary_state = make_rule_test_game([])
seat_boundary_parse = main_module.parse_player_speech(
    seat_boundary_state,
    "12号查杀。",
)
if seat_boundary_parse.mentioned_characters != [12]:
    raise SystemExit("seat 12 references must not also match seat 2")
seat_boundary_checks = [
    claim
    for claim in seat_boundary_parse.claims
    if claim.get("claim_type") == "seer_check"
]
if len(seat_boundary_checks) != 1 or seat_boundary_checks[0].get("target_id") != 12:
    raise SystemExit("seat 12 black-check parsing must produce exactly one target")

# Badge-flow submission is atomic with a first public seer claim. An invalid
# structured flow must be rejected before any role claim, speech, log, or
# meeting progress is committed.
atomic_badge_flow_state = make_rule_test_game(
    ["villager", "villager", "villager", "villager"]
)
atomic_badge_flow_state.phase = "DAY_MEETING"
atomic_badge_flow_state.badge_destroyed = False
atomic_badge_flow_state.sheriff_id = 1
atomic_badge_flow_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[1],
    sheriff_id=1,
)
try:
    submit_player_speech(
        PlayerSpeechRequest(
            game_id=atomic_badge_flow_state.game_id,
            character_id=1,
            speech="我是预言家，先把警徽流说清楚。",
            temporary_nomination_target_id=4,
            badge_flow=main_module.BadgeFlowInput(
                primary_target_id=2,
                secondary_target_id=3,
                good_badge_target_id=4,
                werewolf_badge_target_id=3,
            ),
        )
    )
    raise SystemExit("an invalid first seer badge flow should be rejected")
except HTTPException as exc:
    if exc.status_code != 400:
        raise
if (
    atomic_badge_flow_state.public_claims
    or atomic_badge_flow_state.badge_flows
    or atomic_badge_flow_state.speeches
    or atomic_badge_flow_state.public_logs
    or atomic_badge_flow_state.meeting.current_index != 0
    or atomic_badge_flow_state.meeting.temporary_nomination_target_id is not None
):
    raise SystemExit("a rejected badge flow must not leave a partial claim, log, or nomination")

# Role aliases and whitespace are resolved before the flow is committed. The
# final role claim in the same request is authoritative, while a conflicting
# final non-seer claim rejects the whole request without leaving partial state.
for seer_alias_text in ["我是好人，我跳预言家", "我 是 预言家"]:
    alias_badge_flow_state = make_rule_test_game(
        ["villager", "villager", "villager", "villager"]
    )
    alias_badge_flow_state.phase = "DAY_MEETING"
    alias_badge_flow_state.badge_destroyed = False
    alias_badge_flow_state.meeting = DayMeetingState(
        day=1,
        direction="clockwise",
        order=[1],
    )
    alias_badge_flow_input = main_module.BadgeFlowInput(
        primary_target_id=2,
        secondary_target_id=3,
        good_badge_target_id=2,
        werewolf_badge_target_id=3,
    )
    submit_player_speech(
        PlayerSpeechRequest(
            game_id=alias_badge_flow_state.game_id,
            character_id=1,
            speech=seer_alias_text,
            badge_flow=alias_badge_flow_input,
        )
    )
    alias_role_claims = [
        claim
        for claim in alias_badge_flow_state.public_claims
        if claim.character_id == 1 and claim.claim_type == "role"
    ]
    if (
        len(alias_role_claims) != 1
        or alias_role_claims[0].claimed_role != "seer"
        or len(alias_badge_flow_state.badge_flows) != 1
    ):
        raise SystemExit(
            "seer aliases and spaced role claims must atomically publish only the final seer role and flow"
        )

conflicting_badge_flow_state = make_rule_test_game(
    ["villager", "villager", "villager", "villager"]
)
conflicting_badge_flow_state.phase = "DAY_MEETING"
conflicting_badge_flow_state.badge_destroyed = False
conflicting_badge_flow_state.sheriff_id = 1
conflicting_badge_flow_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[1],
    sheriff_id=1,
)
try:
    submit_player_speech(
        PlayerSpeechRequest(
            game_id=conflicting_badge_flow_state.game_id,
            character_id=1,
            speech="我是预言家，我是村民",
            temporary_nomination_target_id=4,
            badge_flow=main_module.BadgeFlowInput(
                primary_target_id=2,
                secondary_target_id=3,
                good_badge_target_id=2,
                werewolf_badge_target_id=3,
            ),
        )
    )
    raise SystemExit("a final villager claim must reject a same-request badge flow")
except HTTPException as exc:
    if exc.status_code != 400:
        raise
if (
    conflicting_badge_flow_state.public_claims
    or conflicting_badge_flow_state.badge_flows
    or conflicting_badge_flow_state.speeches
    or conflicting_badge_flow_state.public_logs
    or conflicting_badge_flow_state.meeting.current_index != 0
    or conflicting_badge_flow_state.meeting.temporary_nomination_target_id is not None
):
    raise SystemExit(
        "a conflicting final role claim must roll back claims, logs, nomination, speech, and badge flow"
    )

# Free-form badge-flow wording is never authoritative. Contradictory targets
# and branches are removed and replaced by the Python projection, including
# the exact night on which this flow becomes effective.
canonical_submission_state = make_rule_test_game(
    ["villager", "villager", "villager", "villager", "villager", "villager", "villager", "villager", "villager"]
)
canonical_submission_state.phase = "DAY_MEETING"
canonical_submission_state.badge_destroyed = False
canonical_submission_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[1],
)
canonical_submission_input = main_module.BadgeFlowInput(
    primary_target_id=2,
    secondary_target_id=3,
    good_badge_target_id=2,
    werewolf_badge_target_id=3,
)
submit_player_speech(
    PlayerSpeechRequest(
        game_id=canonical_submission_state.game_id,
        character_id=1,
        speech=(
            "我是预言家。我的警徽流先验8号，再验9号；"
            "金水时警徽给8号，查杀时警徽给9号。"
        ),
        badge_flow=canonical_submission_input,
    )
)
canonical_submission_speech = canonical_submission_state.speeches[-1].speech
expected_canonical_submission = main_module.build_badge_flow_input_speech_text(
    canonical_submission_state,
    canonical_submission_input,
)
if (
    expected_canonical_submission not in canonical_submission_speech
    or "第2夜生效" not in canonical_submission_speech
    or "8号" in canonical_submission_speech
    or "9号" in canonical_submission_speech
    or canonical_submission_speech.count("金水时警徽给") != 1
    or canonical_submission_speech.count("查杀时警徽给") != 1
):
    raise SystemExit(
        "stored speech must retain only canonical badge-flow targets, branches, and effective night"
    )

# Every revision remains in history and applies to the next numbered night.
# Looking up night 2 after a day-2 revision must still return day 1's v1.
badge_flow_history_state = make_rule_test_game(
    ["villager", "seer", "villager", "villager", "villager"]
)
badge_flow_claimant = badge_flow_history_state.characters[1]
main_module.register_public_claims(
    badge_flow_history_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=badge_flow_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="badge_flow_history_true",
        )
    ],
)
badge_flow_v1 = main_module.publish_badge_flow(
    badge_flow_history_state,
    badge_flow_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=3,
        secondary_target_id=4,
        good_badge_target_id=3,
        werewolf_badge_target_id=4,
    ),
)
badge_flow_history_state.day = 2
badge_flow_history_state.phase = "DAY_MEETING"
badge_flow_v2 = main_module.publish_badge_flow(
    badge_flow_history_state,
    badge_flow_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=4,
        secondary_target_id=5,
        good_badge_target_id=4,
        werewolf_badge_target_id=5,
        revision_reason="higher_value",
        reason_target_id=4,
    ),
)
if (
    badge_flow_v1.version != 1
    or badge_flow_v1.effective_night_day != 2
    or badge_flow_v1.active
    or badge_flow_v2.version != 2
    or badge_flow_v2.effective_night_day != 3
    or not badge_flow_v2.active
):
    raise SystemExit("badge-flow revisions must preserve version history and next-night scope")
if main_module.get_badge_flow_for_night(
    badge_flow_history_state,
    badge_flow_claimant.id,
    2,
) is not badge_flow_v1:
    raise SystemExit("night 2 must keep using the flow that was public before night 2")
if main_module.get_badge_flow_for_night(
    badge_flow_history_state,
    badge_flow_claimant.id,
    3,
) is not badge_flow_v2:
    raise SystemExit("night 3 must use the day-2 badge-flow revision")
canonical_badge_flow_text = main_module.build_badge_flow_input_speech_text(
    badge_flow_history_state,
    main_module.BadgeFlowInput(
        primary_target_id=4,
        secondary_target_id=5,
        good_badge_target_id=4,
        werewolf_badge_target_id=5,
        revision_reason="higher_value",
        reason_target_id=4,
    ),
)
canonical_badge_flow_parse = main_module.parse_player_speech(
    badge_flow_history_state,
    canonical_badge_flow_text,
)
if (
    any(
        claim.get("claim_type") == "seer_check"
        for claim in canonical_badge_flow_parse.claims
    )
    or canonical_badge_flow_parse.accusations
):
    raise SystemExit("canonical badge-flow branches must not be parsed as completed checks or accusations")

# Fact-based revision labels are legal only when the corresponding public fact
# already exists. Rejection is mutation-free; adding the public elimination or
# role claim then makes the same revision reason legal.
def make_fact_revision_state():
    state = make_rule_test_game(
        ["villager", "seer", "villager", "villager", "villager"]
    )
    claimant = state.characters[1]
    main_module.register_public_claims(
        state,
        [
            main_module.PublicClaimState(
                day=1,
                character_id=claimant.id,
                claim_type="role",
                claimed_role="seer",
                source="fact_revision_claim",
            )
        ],
    )
    main_module.publish_badge_flow(
        state,
        claimant,
        main_module.BadgeFlowInput(
            primary_target_id=3,
            secondary_target_id=4,
            good_badge_target_id=3,
            werewolf_badge_target_id=4,
        ),
    )
    return state, claimant

elimination_revision_state, elimination_revision_claimant = make_fact_revision_state()
elimination_logs_before = list(elimination_revision_state.public_logs)
try:
    main_module.publish_badge_flow(
        elimination_revision_state,
        elimination_revision_claimant,
        main_module.BadgeFlowInput(
            primary_target_id=4,
            secondary_target_id=5,
            good_badge_target_id=4,
            werewolf_badge_target_id=5,
            revision_reason="target_eliminated",
            reason_target_id=3,
        ),
    )
    raise SystemExit("target_eliminated must require a public elimination fact")
except HTTPException as exc:
    if exc.status_code != 400:
        raise
if (
    len(elimination_revision_state.badge_flows) != 1
    or elimination_revision_state.public_logs != elimination_logs_before
):
    raise SystemExit("a missing elimination fact must reject the revision without mutation")
elimination_revision_state.characters[2].alive = False
elimination_revision_state.eliminations.append(
    EliminationState(
        day=1,
        character_id=3,
        cause="exiled",
        source_action="day_vote",
        source_actor_ids=[],
        source_target_id=3,
    )
)
accepted_elimination_revision = main_module.publish_badge_flow(
    elimination_revision_state,
    elimination_revision_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=4,
        secondary_target_id=5,
        good_badge_target_id=4,
        werewolf_badge_target_id=5,
        revision_reason="target_eliminated",
        reason_target_id=3,
    ),
)
if accepted_elimination_revision.version != 2:
    raise SystemExit("a public elimination fact should authorize target_eliminated revision")

role_revision_state, role_revision_claimant = make_fact_revision_state()
role_logs_before = list(role_revision_state.public_logs)
try:
    main_module.publish_badge_flow(
        role_revision_state,
        role_revision_claimant,
        main_module.BadgeFlowInput(
            primary_target_id=4,
            secondary_target_id=5,
            good_badge_target_id=4,
            werewolf_badge_target_id=5,
            revision_reason="role_reveal",
            reason_target_id=3,
        ),
    )
    raise SystemExit("role_reveal must require a public role-claim fact")
except HTTPException as exc:
    if exc.status_code != 400:
        raise
if len(role_revision_state.badge_flows) != 1 or role_revision_state.public_logs != role_logs_before:
    raise SystemExit("a missing role-reveal fact must reject the revision without mutation")
main_module.register_public_claims(
    role_revision_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="role",
            claimed_role="hunter",
            source="public_role_reveal",
        )
    ],
)
accepted_role_revision = main_module.publish_badge_flow(
    role_revision_state,
    role_revision_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=4,
        secondary_target_id=5,
        good_badge_target_id=4,
        werewolf_badge_target_id=5,
        revision_reason="role_reveal",
        reason_target_id=3,
    ),
)
if accepted_role_revision.version != 2:
    raise SystemExit("a public role claim should authorize role_reveal revision")

# A true NPC seer treats the public flow as a strong but soft preference. It
# follows an otherwise equal primary target, may override it for much stronger
# legal evidence, and never repeats an already completed check while another
# unchecked target exists.
night_badge_flow_state = make_rule_test_game(
    [
        "villager", "seer", "villager", "villager", "villager", "villager",
        "villager", "villager", "villager", "villager", "werewolf", "werewolf",
    ]
)
night_badge_seer = night_badge_flow_state.characters[1]
main_module.register_public_claims(
    night_badge_flow_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=night_badge_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="night_badge_flow_true",
        )
    ],
)
main_module.publish_badge_flow(
    night_badge_flow_state,
    night_badge_seer,
    main_module.BadgeFlowInput(
        primary_target_id=3,
        secondary_target_id=4,
        good_badge_target_id=3,
        werewolf_badge_target_id=4,
    ),
)
night_badge_flow_state.day = 2
night_badge_flow_state.phase = "NIGHT"
if main_module.choose_npc_night_target(
    night_badge_flow_state,
    night_badge_seer,
    "seer_check",
) != 3:
    raise SystemExit("an otherwise equal NPC seer should prefer its public primary flow target")
night_badge_seer.suspicion["5"] = 100
main_module.register_public_claims(
    night_badge_flow_state,
    [
        main_module.PublicClaimState(
            day=2,
            character_id=5,
            claim_type="role",
            claimed_role="hunter",
            source="public_high_value_change",
        )
    ],
)
if main_module.choose_npc_night_target(
    night_badge_flow_state,
    night_badge_seer,
    "seer_check",
) != 5:
    raise SystemExit("stronger legal evidence must be able to override the soft badge-flow preference")
night_badge_flow_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=night_badge_seer.id,
        action_type="seer_check",
        target_id=3,
    )
]
if main_module.choose_npc_night_target(
    night_badge_flow_state,
    night_badge_seer,
    "seer_check",
) == 3:
    raise SystemExit("an NPC seer must not repeat a checked flow target while unchecked targets exist")

# Merely revising a flow is neutral. A reason that the public state can verify
# may add a small amount of story credibility, without proving the claimant.
badge_flow_credibility_state = make_rule_test_game(
    ["villager", "seer", "villager", "villager", "villager", "villager"]
)
badge_flow_credibility_claimant = badge_flow_credibility_state.characters[1]
main_module.register_public_claims(
    badge_flow_credibility_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=badge_flow_credibility_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="badge_flow_credibility",
        )
    ],
)
main_module.publish_badge_flow(
    badge_flow_credibility_state,
    badge_flow_credibility_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=3,
        secondary_target_id=4,
        good_badge_target_id=3,
        werewolf_badge_target_id=4,
    ),
)
initial_flow_adjustment = main_module.get_public_badge_flow_credibility_adjustment(
    badge_flow_credibility_state,
    badge_flow_credibility_claimant.id,
)
main_module.publish_badge_flow(
    badge_flow_credibility_state,
    badge_flow_credibility_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=4,
        secondary_target_id=5,
        good_badge_target_id=4,
        werewolf_badge_target_id=5,
        revision_reason="higher_value",
        reason_target_id=4,
    ),
)
neutral_revision_adjustment = main_module.get_public_badge_flow_credibility_adjustment(
    badge_flow_credibility_state,
    badge_flow_credibility_claimant.id,
)
if neutral_revision_adjustment < initial_flow_adjustment:
    raise SystemExit("changing a badge flow must not lose credibility by itself")
badge_flow_credibility_state.day = 2
badge_flow_credibility_state.characters[3].alive = False
badge_flow_credibility_state.eliminations.append(
    EliminationState(
        day=2,
        character_id=4,
        cause="exiled",
        source_action="day_vote",
        source_actor_ids=[],
        source_target_id=4,
    )
)
main_module.publish_badge_flow(
    badge_flow_credibility_state,
    badge_flow_credibility_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=5,
        secondary_target_id=6,
        good_badge_target_id=5,
        werewolf_badge_target_id=6,
        revision_reason="target_eliminated",
        reason_target_id=4,
    ),
)
verified_revision_adjustment = main_module.get_public_badge_flow_credibility_adjustment(
    badge_flow_credibility_state,
    badge_flow_credibility_claimant.id,
)
if verified_revision_adjustment <= neutral_revision_adjustment:
    raise SystemExit("a publicly verifiable badge-flow revision reason should add a small credibility bonus")

# Badge transfer inference exists only for the exact branch published for the
# matching night. Daytime transfer and an unlisted recipient remain ordinary
# transfer facts, and no unrelated non-recipient receives an inferred result.
badge_transfer_flow_state = make_rule_test_game(
    ["villager", "seer", "villager", "villager", "villager", "villager"]
)
badge_transfer_claimant = badge_transfer_flow_state.characters[1]
main_module.register_public_claims(
    badge_transfer_flow_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=badge_transfer_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="badge_transfer_flow",
        )
    ],
)
transfer_flow = main_module.publish_badge_flow(
    badge_transfer_flow_state,
    badge_transfer_claimant,
    main_module.BadgeFlowInput(
        primary_target_id=3,
        secondary_target_id=4,
        good_badge_target_id=3,
        werewolf_badge_target_id=4,
    ),
)
badge_transfer_flow_state.day = 2
badge_transfer_flow_state.sheriff_id = badge_transfer_claimant.id
badge_transfer_flow_state.badge_destroyed = False
main_module.apply_badge_transfer(
    badge_transfer_flow_state,
    badge_transfer_claimant,
    3,
    continuation="after_vote",
)
after_vote_transfer = badge_transfer_flow_state.sheriff_events[-1]
if (
    after_vote_transfer.badge_flow_version is not None
    or main_module.get_badge_transfer_flow_inference(
        badge_transfer_flow_state,
        after_vote_transfer,
    ) is not None
):
    raise SystemExit("a daytime badge transfer must not encode a next-night badge-flow result")
main_module.apply_badge_transfer(
    badge_transfer_flow_state,
    badge_transfer_claimant,
    3,
    continuation="after_night",
)
matching_night_transfer = badge_transfer_flow_state.sheriff_events[-1]
matching_inference = main_module.get_badge_transfer_flow_inference(
    badge_transfer_flow_state,
    matching_night_transfer,
)
if (
    matching_inference is None
    or matching_inference[0].version != transfer_flow.version
    or matching_inference[1:] != (3, "good")
):
    raise SystemExit("a matching after-night transfer should express exactly its published good branch")
main_module.apply_badge_transfer(
    badge_transfer_flow_state,
    badge_transfer_claimant,
    5,
    continuation="after_night",
)
unlisted_night_transfer = badge_transfer_flow_state.sheriff_events[-1]
if (
    unlisted_night_transfer.badge_flow_version is not None
    or main_module.get_badge_transfer_flow_inference(
        badge_transfer_flow_state,
        unlisted_night_transfer,
    ) is not None
    or main_module.get_matching_badge_flow_transfer_result(
        badge_transfer_flow_state,
        transfer_flow,
        5,
    )
):
    raise SystemExit("an unlisted badge recipient must not be forced into either badge-flow branch")
badge_consistency_signals = [
    signal
    for signal in main_module.build_public_decision_signals(
        badge_transfer_flow_state
    )
    if signal.kind == "badge_flow_consistency"
]
if (
    len(badge_consistency_signals) != 1
    or badge_consistency_signals[0].target_id != 3
    or any(signal.target_id in {5, 6} for signal in badge_consistency_signals)
):
    raise SystemExit("ordinary non-recipients must not receive inferred good-or-wolf badge-flow labels")

# Hidden truth and internal claim source do not alter the public flow, state
# view, key-intel projection, or selectable decision signal.
def build_public_badge_projection(claimant_role, claim_source):
    state = make_rule_test_game(
        ["villager", claimant_role, "villager", "villager", "villager"]
    )
    claimant = state.characters[1]
    main_module.register_public_claims(
        state,
        [
            main_module.PublicClaimState(
                day=1,
                character_id=claimant.id,
                claim_type="role",
                claimed_role="seer",
                source=claim_source,
            )
        ],
    )
    main_module.publish_badge_flow(
        state,
        claimant,
        main_module.BadgeFlowInput(
            primary_target_id=3,
            secondary_target_id=4,
            good_badge_target_id=3,
            werewolf_badge_target_id=4,
        ),
    )
    return (
        [item.model_dump(mode="json") for item in main_module.build_badge_flow_views(state)],
        [
            item.model_dump(mode="json")
            for item in main_module.build_public_intel_views(state)
            if item.kind == "badge_flow"
        ],
        [
            item.model_dump(mode="json")
            for item in main_module.build_public_decision_signals(state)
            if item.kind == "badge_flow"
        ],
    )

true_badge_projection = build_public_badge_projection("seer", "true_role")
fake_badge_projection = build_public_badge_projection("werewolf", "wolf_fake_seer")
if true_badge_projection != fake_badge_projection:
    raise SystemExit("true and fake seers must have identical public badge-flow projections")
if any(
    hidden_key in json.dumps(true_badge_projection, ensure_ascii=False)
    for hidden_key in ["source", "camp", "true_role", "wolf_fake_seer"]
):
    raise SystemExit("public badge-flow projections must not expose hidden role provenance")

# Player speech is conservatively reduced to a quotable public_position.v1:
# positive stance, negative stance, and provisional vote are all distinct.
player_position_state = make_rule_test_game(
    ["villager", "villager", "villager", "villager"]
)
main_module.register_public_claims(
    player_position_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=2,
            claim_type="role",
            claimed_role="seer",
            source="position_card_claim",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="role",
            claimed_role="seer",
            source="position_card_claim",
        ),
    ],
)
position_speech_text = "我信2号，不信3号，今天暂时投4号。"
position_parse = main_module.parse_player_speech(
    player_position_state,
    position_speech_text,
)
if (
    position_parse.supported_ids != [2]
    or position_parse.opposed_ids != [3]
    or position_parse.vote_intent_target_id != 4
):
    raise SystemExit("player position parsing must keep support, opposition, and provisional vote separate")
player_position_state.phase = "DAY_MEETING"
player_position_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[1],
)
submit_player_speech(
    PlayerSpeechRequest(
        game_id=player_position_state.game_id,
        character_id=1,
        speech=position_speech_text,
    )
)
stored_position = player_position_state.speeches[-1].public_position
if (
    stored_position is None
    or stored_position.schema_version != "public_position.v1"
    or stored_position.seer_support_id != 2
    or stored_position.seer_oppose_id != 3
    or stored_position.provisional_vote_target_id != 4
):
    raise SystemExit("a formal player speech must persist a complete public_position.v1 card")
position_summary = main_module.render_public_position_summary(
    player_position_state,
    stored_position,
)
if not all(marker in position_summary for marker in ["站2号", "不站3号", "暂票4号"]):
    raise SystemExit("the public position summary must retain both sides and the provisional vote")
position_signals = [
    signal
    for signal in main_module.build_public_decision_signals(player_position_state)
    if signal.kind == "public_position" and signal.actor_id == 1
]
if len(position_signals) != 1 or position_summary not in position_signals[0].summary:
    raise SystemExit("public_position.v1 must be available as one concise public decision signal")

# Public decision RAG may quote only the concise position card. The original
# long-form speech remains stored for display but is not supplied as evidence.
rag_position_state = make_rule_test_game(
    ["villager", "villager", "villager", "villager"]
)
rag_position_state.rag_enabled = True
rag_position = PublicPositionV1(
    speaker_id=2,
    day=1,
    phase="DAY_MEETING",
    suspected_target_ids=[3],
    provisional_vote_target_id=3,
)
rag_position_summary = main_module.render_public_position_summary(
    rag_position_state,
    rag_position,
)
rag_long_speech_marker = "LONG_ORIGINAL_SPEECH_MUST_NOT_ENTER_PUBLIC_RAG_7f31"
rag_position_state.speeches = [
    SpeechState(
        day=1,
        character_id=2,
        name=rag_position_state.characters[1].name,
        speech=(
            f"{rag_long_speech_marker}：这是一段刻意保留的很长原始发言，"
            "只能用于游戏展示，不能作为后续 NPC 的逐字引用材料。"
        ),
        is_player=False,
        public_position=rag_position,
    )
]
rag_position_contexts = build_public_decision_rag_context(
    rag_position_state,
    rag_position_state.characters[3],
    rag_position_state.characters[2],
    "公开发言",
)
rag_public_contexts = [
    item for item in rag_position_contexts if item.get("kind") == "public"
]
if (
    len(rag_public_contexts) != 1
    or rag_public_contexts[0].get("content") != rag_position_summary
    or rag_long_speech_marker in json.dumps(rag_position_contexts, ensure_ascii=False)
):
    raise SystemExit(
        "public decision RAG must expose only public_position summaries, never long original speech"
    )

# Negated language must not manufacture an accusation, support, or vote. A
# direct distrust statement may still become opposition, and mixed clauses
# preserve only the genuinely accused target.
not_suspicious_parse = main_module.parse_player_speech(
    player_position_state,
    "不怀疑3号",
)
if (
    not_suspicious_parse.accusations
    or not_suspicious_parse.supported_ids
    or not_suspicious_parse.opposed_ids
    or not_suspicious_parse.vote_intent_target_id is not None
):
    raise SystemExit("'不怀疑3号' must not create suspicion, support, opposition, or vote")
not_trusting_parse = main_module.parse_player_speech(
    player_position_state,
    "不太相信3号",
)
if (
    not_trusting_parse.accusations
    or not_trusting_parse.supported_ids
    or not_trusting_parse.opposed_ids != [3]
    or not_trusting_parse.vote_intent_target_id is not None
):
    raise SystemExit("'不太相信3号' may record opposition but must not become suspicion, support, or vote")
not_voting_parse = main_module.parse_player_speech(
    player_position_state,
    "不会投3号",
)
if (
    not_voting_parse.accusations
    or not_voting_parse.supported_ids
    or not_voting_parse.opposed_ids
    or not_voting_parse.vote_intent_target_id is not None
):
    raise SystemExit("'不会投3号' must not create suspicion, support, opposition, or vote")
mixed_suspicion_parse = main_module.parse_player_speech(
    player_position_state,
    "不怀疑3号、怀疑4号",
)
mixed_accused_ids = [
    accusation.get("target_id")
    for accusation in mixed_suspicion_parse.accusations
]
mixed_suspicion_position = main_module.build_public_position(
    player_position_state,
    player_position_state.characters[0],
    "DAY_MEETING",
    parsed=mixed_suspicion_parse,
)
if mixed_accused_ids != [4] or mixed_suspicion_position.suspected_target_ids != [4]:
    raise SystemExit("mixed negated and positive suspicion must retain only target 4")

explicit_suspicion_state = make_rule_test_game(
    ["villager", "villager", "villager", "villager"]
)
explicit_suspicion_state.phase = "DAY_MEETING"
explicit_suspicion_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[1],
)
submit_player_speech(
    PlayerSpeechRequest(
        game_id=explicit_suspicion_state.game_id,
        character_id=1,
        speech="3号可疑。",
    )
)
explicit_suspicion_position = explicit_suspicion_state.speeches[-1].public_position
if (
    explicit_suspicion_position is None
    or 3 not in explicit_suspicion_position.suspected_target_ids
):
    raise SystemExit("an explicit player accusation must enter public_position suspected targets")

counterclaim_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "werewolf"]
)
counterclaim_state.phase = "DAY_MEETING"
counterclaim_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
counterclaim_state.public_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=3,
        claim_type="role",
        claimed_role="seer",
        source="counterclaim_smoke",
    )
]
counterclaim_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=2,
        claim_type="role",
        claimed_role="seer",
        source="counterclaim_smoke",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=2,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=4,
        result="werewolf",
        source="counterclaim_smoke",
    ),
]
counterclaim_context = main_module.build_public_speech_decision_context(
    counterclaim_state,
    counterclaim_state.characters[1],
    [],
    counterclaim_claims,
)
if PublicSpeechIntent.COUNTERCLAIM not in counterclaim_context.allowed_intents:
    raise SystemExit("a true seer facing a competing seer claim should be allowed to counterclaim")
counterclaim_plan = PublicSpeechPlanV2.model_validate(
    {
        "schema_version": "public_speech_plan.v2",
        "intent": "counterclaim",
        "primary_target_id": 3,
        "secondary_target_id": 4,
        "stance": "oppose",
        "stance_target_id": 3,
        "confidence": 90,
        "signal_read": "none",
        "question": {"target_id": 3, "topic": "claim_basis"},
        "verification": {"target_id": 3, "criterion": "claim_consistency"},
        "provisional_vote_target_id": 4,
        "tactic": "role_counterclaim",
        "claim_option_ids": [counterclaim_context.claim_options[0].id],
        "evidence_ids": [],
        "signal_ids": [],
    }
)
if validate_public_speech_plan(counterclaim_context, counterclaim_plan):
    raise SystemExit("a competing-claimant primary plus checked secondary should form a legal counterclaim plan")

decision_context_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "villager",
    ]
)
decision_context_state.phase = "DAY_MEETING"
decision_context_state.public_logs = ["1号玩家已公开发言。"]
decision_context_state.night_actions = [
    NightActionState(day=1, actor_id=6, action_type="seer_check", target_id=3),
]
decision_context_state.characters[1].memory_summary = "狼人2号的专属私有记忆。"
decision_context_state.characters[5].memory_summary = "预言家6号的专属私有记忆。"
decision_context_state.characters[6].memory_summary = "村民7号的专属私有记忆。"
decision_context_state.characters[11].alive = False
decision_rag_context = [
    {
        "kind": "public",
        "title": "公开证据",
        "content": "只包含场上已公开的发言。",
        "safe_to_show": True,
    },
    {
        "kind": "private",
        "title": "私有证据",
        "content": "不得公开引用的内部线索。",
        "safe_to_show": False,
    },
]

def build_test_decision_context(speaker_id):
    decision_context_state.meeting = DayMeetingState(
        day=1,
        direction="clockwise",
        order=[speaker_id],
    )
    return main_module.build_public_speech_decision_context(
        decision_context_state,
        decision_context_state.characters[speaker_id - 1],
        decision_rag_context,
        [],
    )

wolf_decision_context = build_test_decision_context(2)
seer_decision_context = build_test_decision_context(6)
villager_decision_context = build_test_decision_context(7)
for context, expected_role, own_memory in [
    (wolf_decision_context, "werewolf", "狼人2号的专属私有记忆"),
    (seer_decision_context, "seer", "预言家6号的专属私有记忆"),
    (villager_decision_context, "villager", "村民7号的专属私有记忆"),
]:
    if context.phase != "DAY_MEETING" or context.actor.role != expected_role:
        raise SystemExit("decision context should include the current phase and true actor role")
    if not context.public_logs or "已公开发言" not in context.public_logs[0].content:
        raise SystemExit("decision context should include recent public logs")
    private_memory_text = "\\n".join(item.content for item in context.private_memory)
    if own_memory not in private_memory_text or "专属私有记忆" not in private_memory_text:
        raise SystemExit("decision context should include only the actor's private memory")
    other_memory_markers = {
        "werewolf": ["预言家6号", "村民7号"],
        "seer": ["狼人2号", "村民7号"],
        "villager": ["狼人2号", "预言家6号"],
    }[expected_role]
    if any(marker in private_memory_text for marker in other_memory_markers):
        raise SystemExit("decision context leaked another character's private memory")
    legal_target_ids = {target.id for target in context.legal_targets}
    if context.actor.id in legal_target_ids or 12 in legal_target_ids:
        raise SystemExit("decision context targets must exclude the actor and dead characters")

wolf_knowledge_ids = {item.id for item in wolf_decision_context.legal_knowledge}
if {f"private:wolf_teammate:{character_id}" for character_id in [3, 4, 5]} - wolf_knowledge_ids:
    raise SystemExit("an NPC wolf should know exactly its legal wolf-team identities")
if 3 in {target.id for target in wolf_decision_context.legal_targets}:
    raise SystemExit("a low-pressure wolf teammate should not be a legal public target")
seer_knowledge_ids = {item.id for item in seer_decision_context.legal_knowledge}
if "private:seer_check:1:3" not in seer_knowledge_ids:
    raise SystemExit("an NPC seer should receive its own checked result as legal knowledge")
villager_knowledge_ids = {item.id for item in villager_decision_context.legal_knowledge}
if any(
    item_id.startswith(("private:wolf_teammate:", "private:seer_check:"))
    for item_id in villager_knowledge_ids
):
    raise SystemExit("an ordinary villager decision context must not contain hidden role knowledge")
if not any(item.visibility == "private" for item in villager_decision_context.evidence):
    raise SystemExit("decision context should preserve evidence visibility for legality checks")

decision_context_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[7],
)
villager_continuity = main_module.build_public_speech_continuity_context(
    decision_context_state,
    decision_context_state.characters[6],
    villager_decision_context,
    mandatory_response=False,
)
villager_continuity_payload = villager_continuity.model_dump(mode="json")
if (
    villager_continuity.schema_version != "public_speech_continuity.v1"
    or villager_continuity.stance_schema_version != "stance_summary.v1"
    or "role" in villager_continuity_payload
    or "camp" in villager_continuity_payload
):
    raise SystemExit("the live continuity input must be versioned and omit hidden labels")
legal_villager_targets = {target.id for target in villager_decision_context.legal_targets}
continuity_targets = {
    target_id
    for target_id in [
        *villager_continuity.trusted_target_ids,
        villager_continuity.primary_suspect_id,
        villager_continuity.secondary_suspect_id,
        villager_continuity.provisional_vote_target_id,
        villager_continuity.verification_target_id,
    ]
    if target_id is not None
}
if not continuity_targets.issubset(legal_villager_targets):
    raise SystemExit("live continuity targets must stay inside the speech allowlist")

continuity_hidden_swap = decision_context_state.model_copy(deep=True)
hidden_wolf = main_module.get_character(continuity_hidden_swap, 2)
hidden_good = main_module.get_character(continuity_hidden_swap, 8)
hidden_wolf.role, hidden_good.role = hidden_good.role, hidden_wolf.role
hidden_wolf.camp, hidden_good.camp = hidden_good.camp, hidden_wolf.camp
continuity_hidden_swap.wolf_fake_seer_id = hidden_good.id
hidden_swap_speaker = main_module.get_character(continuity_hidden_swap, 7)
hidden_swap_context = main_module.build_public_speech_decision_context(
    continuity_hidden_swap,
    hidden_swap_speaker,
    decision_rag_context,
    [],
)
hidden_swap_continuity = main_module.build_public_speech_continuity_context(
    continuity_hidden_swap,
    hidden_swap_speaker,
    hidden_swap_context,
    mandatory_response=False,
)
if villager_continuity != hidden_swap_continuity:
    raise SystemExit("good live continuity must be invariant to unseen target role swaps")

decision_context_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
wolf_continuity = main_module.build_public_speech_continuity_context(
    decision_context_state,
    decision_context_state.characters[1],
    wolf_decision_context,
    mandatory_response=False,
)
legal_wolf_targets = {target.id for target in wolf_decision_context.legal_targets}
if any(
    target_id not in legal_wolf_targets
    for target_id in [
        *wolf_continuity.trusted_target_ids,
        wolf_continuity.primary_suspect_id,
        wolf_continuity.secondary_suspect_id,
        wolf_continuity.provisional_vote_target_id,
        wolf_continuity.verification_target_id,
    ]
    if target_id is not None
):
    raise SystemExit("wolf continuity must filter legal private beliefs through speech targets")

signal_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "villager", "villager", "villager", "villager",
        "villager", "guard",
    ]
)
signal_state.day = 2
signal_state.phase = "DAY_MEETING"
signal_state.sheriff_election = SheriffElectionState(
    day=1,
    candidates=[3, 4],
    withdrawn=[4],
    votes=[VoteState(day=1, voter_id=5, target_id=3, reason="")],
    completed=True,
)
signal_state.sheriff_events = [
    SheriffEventState(day=1, event_type="skip_signup", actor_id=1),
    SheriffEventState(day=1, event_type="elected", actor_id=3),
    SheriffEventState(
        day=1,
        event_type="badge_transfer",
        actor_id=3,
        target_id=6,
    ),
]
signal_state.votes = [
    VoteState(day=1, voter_id=7, target_id=8, reason="隐藏的投票理由不应进入信号。"),
]
signal_state.eliminations = [
    EliminationState(
        day=1,
        character_id=9,
        cause="witch_poison",
        source_action="witch_poison",
        source_actor_ids=[12],
        source_target_id=9,
    ),
]
signal_state.characters[8].alive = False
signal_state.pending_first_night_eliminations = [
    EliminationState(
        day=2,
        character_id=10,
        cause="night_kill",
        source_action="werewolf_kill",
        source_actor_ids=[2, 3],
        source_target_id=10,
    ),
]
signal_state.first_night_result_pending = True
signal_state.speeches = [
    SpeechState(
        day=2,
        character_id=11,
        name=signal_state.characters[10].name,
        speech="我没什么信息，先过吧。",
        is_player=False,
        evidence_titles=["已检索但没有形成实际贡献的资料"],
    ),
    SpeechState(
        day=2,
        character_id=12,
        name=signal_state.characters[11].name,
        speech="我重点怀疑4号，他退水后的解释前后不一致。",
        is_player=False,
        focus_target_id=4,
    ),
]
signal_state.public_claims = [
    main_module.PublicClaimState(
        day=2,
        character_id=11,
        claim_type="role",
        claimed_role="villager",
        source="earlier_public_phase",
    ),
]
signal_suspicion_before = [dict(character.suspicion) for character in signal_state.characters]

def build_signal_context(speaker_id):
    signal_state.meeting = DayMeetingState(
        day=2,
        direction="clockwise",
        order=[speaker_id],
    )
    return main_module.build_public_speech_decision_context(
        signal_state,
        signal_state.characters[speaker_id - 1],
        [],
        [],
    )

signal_contexts = [
    build_signal_context(2),
    build_signal_context(6),
    build_signal_context(7),
]
serialized_signal_lists = [
    [item.model_dump(mode="json") for item in context.decision_signals]
    for context in signal_contexts
]
if not serialized_signal_lists[0] or not all(
    items == serialized_signal_lists[0] for items in serialized_signal_lists[1:]
):
    raise SystemExit("public decision signals must be identical for every actor role")
signal_kinds = {item["kind"] for item in serialized_signal_lists[0]}
expected_signal_kinds = {
    "sheriff_signup", "sheriff_skip_signup", "sheriff_withdraw",
    "sheriff_continue", "sheriff_vote", "sheriff_elected", "badge_transfer",
    "exile_vote", "public_elimination", "low_information_speech",
}
if expected_signal_kinds - signal_kinds:
    raise SystemExit("public action signals should cover election, votes, elimination, and low-information speech")
signal_payload_text = json.dumps(serialized_signal_lists[0], ensure_ascii=False)
for hidden_marker in [
    "witch_poison", "werewolf_kill", "隐藏的投票理由",
    "signal:public_elimination:2:10",
]:
    if hidden_marker in signal_payload_text:
        raise SystemExit("public decision signals leaked a hidden action source or pending result")
if "夜间结果公布时出局" not in signal_payload_text:
    raise SystemExit("a published night elimination should use a public-safe cause summary")
signal_ids = {item["id"] for item in serialized_signal_lists[0]}
if {
    "signal:sheriff_skip_signup:1:2",
    "signal:sheriff_continue:1:3",
} - signal_ids:
    raise SystemExit("NPC non-candidates and active candidates should receive public signup-state signals")
night_elimination_signal = next(
    item
    for item in serialized_signal_lists[0]
    if item["kind"] == "public_elimination" and item["actor_id"] == 9
)
hidden_source_name = main_module.format_full_character_name(signal_state.characters[11])
if (
    night_elimination_signal["phase"] != "NIGHT_RESULT"
    or hidden_source_name in night_elimination_signal["summary"]
):
    raise SystemExit("a night elimination signal must omit its hidden source actor")
low_information_signal_payload = next(
    item
    for item in serialized_signal_lists[0]
    if item["kind"] == "low_information_speech" and item["actor_id"] == 11
)
if low_information_signal_payload["category"] != "assessment":
    raise SystemExit("low-information speech must remain an assessment, not an identity fact")
if any(
    item["category"] != "fact"
    for item in serialized_signal_lists[0]
    if item["kind"] != "low_information_speech"
):
    raise SystemExit("authoritative public actions should remain fact signals")
if [dict(character.suspicion) for character in signal_state.characters] != signal_suspicion_before:
    raise SystemExit("building low-information assessments must not mutate suspicion")

saved_first_night_state = make_rule_test_game(
    ["witch", "villager", "werewolf", "villager", "seer", "hunter", "guard"]
)
saved_first_night_state.sheriff_election = None
saved_first_night_state.badge_destroyed = False
saved_first_night_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="witch_save", target_id=4),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=4),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=6, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=7, action_type="none", target_id=None),
]
saved_first_night_result = resolve_night(
    NightResolveRequest(game_id=saved_first_night_state.game_id)
)
if not saved_first_night_result.result_pending or saved_first_night_result.dead_characters:
    raise SystemExit("first-night result must stay hidden until the sheriff election finishes")
if saved_first_night_state.pending_first_night_eliminations:
    raise SystemExit("a witch-saved target must not enter the pending elimination list")
if not all(character.alive for character in saved_first_night_state.characters):
    raise SystemExit("a successful first-night save must not eliminate any unrelated character")

pending_first_night_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "villager", "seer", "witch", "hunter", "guard"]
)
pending_first_night_state.sheriff_election = None
pending_first_night_state.badge_destroyed = False
pending_first_night_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=4),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=6, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=7, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=8, action_type="none", target_id=None),
]
pending_result = resolve_night(
    NightResolveRequest(game_id=pending_first_night_state.game_id)
)
if pending_result.dead_characters or not pending_first_night_state.characters[3].alive:
    raise SystemExit("first-night victim must remain in play during the sheriff election")
if [item.character_id for item in pending_first_night_state.pending_first_night_eliminations] != [4]:
    raise SystemExit("first-night pending result should contain only the legally attacked target")
main_module.finish_sheriff_election(
    pending_first_night_state,
    2,
    "2号测试警长当选。",
)
if pending_first_night_state.characters[3].alive:
    raise SystemExit("pending first-night victim should be eliminated after the election")
if any(not character.alive for character in pending_first_night_state.characters if character.id != 4):
    raise SystemExit("night resolution must never eliminate an unrelated character")
night_elimination = pending_first_night_state.eliminations[-1]
if (
    night_elimination.source_action != "werewolf_kill"
    or night_elimination.source_actor_ids != [3]
    or night_elimination.source_target_id != 4
):
    raise SystemExit("every elimination should keep a legal, traceable source")

first_night_sheriff_hunter_state = make_rule_test_game(
    ["hunter", "villager", "werewolf", "villager", "seer", "witch", "guard"]
)
first_night_sheriff_hunter_state.sheriff_election = None
first_night_sheriff_hunter_state.badge_destroyed = False
first_night_sheriff_hunter_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=6, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=7, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=first_night_sheriff_hunter_state.game_id))
main_module.finish_sheriff_election(
    first_night_sheriff_hunter_state,
    1,
    "1号玩家当选警长。",
)
if first_night_sheriff_hunter_state.phase != "HUNTER_SHOT":
    raise SystemExit("first-night sheriff hunter must resolve the shot before badge transfer")
resolve_hunter_shot(
    HunterShotRequest(
        game_id=first_night_sheriff_hunter_state.game_id,
        character_id=1,
        target_id=2,
    )
)
if first_night_sheriff_hunter_state.phase != "BADGE_TRANSFER":
    raise SystemExit("first-night sheriff hunter should transfer the badge after shooting")
submit_badge_transfer(
    BadgeTransferRequest(
        game_id=first_night_sheriff_hunter_state.game_id,
        character_id=1,
        target_id=4,
    )
)
if (
    first_night_sheriff_hunter_state.sheriff_id != 4
    or first_night_sheriff_hunter_state.phase != "DAY_MEETING"
):
    raise SystemExit("first-night badge transfer should finish before winner and meeting checks")

withdrawn_vote_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "witch", "hunter", "guard"]
)
withdrawn_vote_state.phase = "SHERIFF_VOTE"
withdrawn_vote_state.sheriff_election = SheriffElectionState(
    candidates=[1, 2, 3],
    withdrawn=[1],
    speech_order=[1, 2, 3],
)
withdrawn_vote_view = main_module.build_sheriff_view(withdrawn_vote_state)
if withdrawn_vote_view.player_can_vote or "退水者" not in withdrawn_vote_view.player_vote_ineligible_reason:
    raise SystemExit("a withdrawn candidate must remain ineligible for sheriff voting")
withdrawn_vote_result = submit_and_resolve_sheriff_vote(
    SheriffVoteRequest(
        game_id=withdrawn_vote_state.game_id,
        character_id=1,
        target_id=None,
    )
)
candidate_voters = {ballot.voter_id for ballot in withdrawn_vote_result.ballots} & {1, 2, 3}
if candidate_voters:
    raise SystemExit("all sheriff-election participants, including withdrawn candidates, must not vote")

class StubLLMClient:
    def __init__(self):
        self.public_attempts = 0
        self.public_contexts = []
        self.expression_contexts = []
        self.selected_target_id = None
        self.selected_signal_id = None
        self.gameplay_snapshots = []
        self.snapshotter = None

    def status(self):
        return {
            "enabled": True,
            "provider": "stub",
            "model": "stub-model",
            "configured": True,
            "base_url": "",
        }

    def generate_json_object(
        self,
        _system_prompt,
        context,
        _fallback_object=None,
        max_attempts=None,
    ):
        self.public_attempts += 1
        self.public_contexts.append(dict(context))
        if self.snapshotter is not None:
            self.gameplay_snapshots.append(self.snapshotter())
        continuity = context["continuity"]
        expected_target_id = (
            continuity.get("provisional_vote_target_id")
            or continuity.get("primary_suspect_id")
            or next(iter(continuity.get("trusted_target_ids", [])), None)
        )
        target = next(
            item
            for item in context["legal_targets"]
            if item["id"] == expected_target_id
        ) if expected_target_id is not None else context["legal_targets"][0]
        trusted = target["id"] in continuity.get("trusted_target_ids", []) and not (
            continuity.get("provisional_vote_target_id")
            or continuity.get("primary_suspect_id")
        )
        public_evidence = next(
            (
                item
                for item in context.get("evidence", [])
                if item.get("visibility") == "public"
            ),
            None,
        )
        public_signal = next(
            item
            for item in context.get("decision_signals", [])
            if item.get("kind") == "sheriff_elected"
        )
        data = {
            "schema_version": "public_speech_plan.v3",
            "intent": "defend" if trusted else "pressure",
            "primary_target_id": target["id"],
            "secondary_target_id": None,
            "stance": "support" if trusted else "oppose",
            "stance_target_id": target["id"],
            "confidence": 72,
            "signal_read": "reduces_suspicion" if trusted else "raises_suspicion",
            "question": {
                "target_id": target["id"],
                "topic": "response_to_pressure" if trusted else "action_motive",
            },
            "verification": {
                "target_id": target["id"],
                "criterion": "follow_up_action" if trusted else "response_quality",
            },
            "provisional_vote_target_id": None if trusted else target["id"],
            "tactic": "conditional_defense" if trusted else "direct_pressure",
            "claim_option_ids": [],
            "evidence_ids": [public_evidence["id"]] if public_evidence else [],
            "signal_ids": [public_signal["id"]],
            "continuity_reason": (
                "mandatory_rule_response"
                if continuity.get("mandatory_response")
                else "stance_aligned"
                if expected_target_id is not None
                else "unscored"
            ),
            "continuity_signal_ids": [],
        }
        if self.public_attempts == 1:
            data.pop("schema_version")
        if self.public_attempts > 1:
            self.selected_target_id = target["id"]
            self.selected_signal_id = public_signal["id"]
        return LLMJsonGeneration(
            data=data,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps(data, ensure_ascii=False),
        )

    def generate_json_text(self, _system_prompt, context, fallback_text, max_attempts=None):
        if context.get("task") == "public_speech_voice_prefix":
            self.expression_contexts.append(dict(context))
            text = "先把话说明白"
        else:
            text = fallback_text.replace("我会", "我会认真地", 1)
        return LLMGeneration(
            text=text,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps({"text": text}, ensure_ascii=False),
        )

original_llm_client = main_module.LLM_CLIENT
recovered_validation_log_path = Path("/tmp/agent-town-llm-recovered-smoke.jsonl")
original_recovered_validation_log_path = main_module.LLM_VALIDATION_LOG_FILE
try:
    recovered_validation_log_path.unlink(missing_ok=True)
    main_module.LLM_VALIDATION_LOG_FILE = recovered_validation_log_path
    llm_game_state = make_rule_test_game(
        [
            "villager", "werewolf", "werewolf", "werewolf", "werewolf",
            "seer", "guard",
        ]
    )
    llm_game_state.llm_enabled = True
    llm_game_state.phase = "DAY_MEETING"
    llm_game_state.public_logs = ["结构化决策测试的公开日志。"]
    llm_game_state.sheriff_election = SheriffElectionState(
        day=1,
        candidates=[3, 4],
        withdrawn=[4],
        completed=True,
    )
    llm_game_state.sheriff_events = [
        SheriffEventState(day=1, event_type="elected", actor_id=3),
    ]
    llm_game_state.characters[1].memory_summary = (
        "PRIVATE_STRATEGY_TOKEN：狼队内部计划。\\n"
        "NIGHT_RAW_TOKEN：夜间行动原文。\\n"
        "CHAT_RAW_TOKEN：私聊原文。"
    )
    llm_game_state.meeting = DayMeetingState(
        day=1,
        direction="clockwise",
        order=[2, 1] + list(range(3, 13)),
    )
    stub_llm_client = StubLLMClient()
    def llm_gameplay_snapshot():
        return (
            len(llm_game_state.speeches),
            len(llm_game_state.public_claims),
            tuple(llm_game_state.public_logs),
            llm_game_state.characters[1].memory_summary,
        )
    gameplay_state_before_llm = llm_gameplay_snapshot()
    stub_llm_client.snapshotter = llm_gameplay_snapshot
    main_module.LLM_CLIENT = stub_llm_client
    llm_speech_response = generate_npc_speech(
        NpcSpeechRequest(game_id=llm_game_state.game_id, character_id=2)
    )
    if not llm_speech_response.speech.llm_used:
        raise SystemExit("enabled game should use the configured LLM for NPC speech")
    if llm_speech_response.speech.llm_provider != "stub":
        raise SystemExit("NPC speech should expose the active LLM provider")
    if stub_llm_client.public_attempts != 2:
        raise SystemExit("a structured plan missing schema_version should receive one correction retry")
    if stub_llm_client.gameplay_snapshots != [
        gameplay_state_before_llm,
        gameplay_state_before_llm,
    ]:
        raise SystemExit("a rejected structured decision must not mutate gameplay state before retry")
    decision_call_context = stub_llm_client.public_contexts[0]
    if (
        decision_call_context.get("phase") != "DAY_MEETING"
        or decision_call_context.get("actor", {}).get("role") != "werewolf"
        or decision_call_context.get("actor", {}).get("faction") != "werewolf"
        or not decision_call_context.get("private_memory")
        or not decision_call_context.get("public_logs")
        or len(decision_call_context.get("decision_signals", [])) < 2
        or decision_call_context.get("continuity", {}).get("schema_version")
        != "public_speech_continuity.v1"
        or decision_call_context.get("continuity", {}).get("actor_id") != 2
    ):
        raise SystemExit("structured DAY_MEETING calls should receive the complete actor context")
    output_contract = decision_call_context.get("output_contract", {})
    if (
        output_contract.get("schema_version") != "public_speech_plan.v3"
        or output_contract.get("format") != "flat_json_object"
        or "fields" in output_contract
        or "schema_version" not in output_contract.get("required_root_keys", [])
        or output_contract.get("flat_json_example", {}).get("schema_version")
        != "public_speech_plan.v3"
    ):
        raise SystemExit("the strategy prompt should request the complete V3 speech plan contract")
    retry_feedback = stub_llm_client.public_contexts[1].get("validation_feedback", {})
    if (
        "schema_version" not in retry_feedback.get("required_root_keys", [])
        or "fields" not in retry_feedback.get("forbidden_root_keys", [])
        or "根级" not in retry_feedback.get("instruction", "")
    ):
        raise SystemExit("a schema retry should explicitly request every plan field at the JSON root")
    stored_legacy_upgrade = llm_game_state.speeches[-1].decision_plan
    if (
        stored_legacy_upgrade.get("schema_version") != "public_speech_plan.v3"
        or stored_legacy_upgrade.get("primary_target_id") != stub_llm_client.selected_target_id
        or stored_legacy_upgrade.get("provisional_vote_target_id") != stub_llm_client.selected_target_id
        or stored_legacy_upgrade.get("continuity_reason")
        not in {"stance_aligned", "mandatory_rule_response", "unscored"}
        or stored_legacy_upgrade.get("continuity_signal_ids")
    ):
        raise SystemExit(
            "an accepted flat V3 strategy should persist its safe continuity reason: "
            + json.dumps(stored_legacy_upgrade, ensure_ascii=False, sort_keys=True)
        )
    strategy_context_text = json.dumps(decision_call_context, ensure_ascii=False)
    if (
        "PRIVATE_STRATEGY_TOKEN" not in strategy_context_text
        or "private:wolf_teammate:" not in strategy_context_text
    ):
        raise SystemExit("the private strategy call should receive actor-scoped hidden knowledge")
    if len(stub_llm_client.expression_contexts) != 1:
        raise SystemExit(
            "an accepted strategy should receive one separate voice-prefix call: "
            f"got {len(stub_llm_client.expression_contexts)}"
        )
    expression_context = stub_llm_client.expression_contexts[0]
    expression_context_text = json.dumps(expression_context, ensure_ascii=False)
    if any(
        key in expression_context
        for key in [
            "actor", "legal_knowledge", "private_memory", "evidence",
            "decision_signals", "legal_targets", "claim_options", "allowed_intents",
            "continuity",
            "focus_target", "rule_text", "public_evidence", "public_plan",
            "selected_public_signals", "recent_public_logs",
        ]
    ):
        raise SystemExit("the voice-prefix call must not receive fact-bearing strategy fields")
    if any(key in expression_context.get("speaker", {}) for key in ["role", "faction"]):
        raise SystemExit("the voice-prefix speaker must not expose role or faction")
    if any(
        marker in expression_context_text
        for marker in [
            "PRIVATE_STRATEGY_TOKEN", "NIGHT_RAW_TOKEN", "CHAT_RAW_TOKEN",
            "private:wolf_teammate:",
        ]
    ):
        raise SystemExit("the voice-prefix call leaked wolf-team, night, or private-chat text")
    if (
        expression_context.get("task") != "public_speech_voice_prefix"
        or expression_context.get("phase") != "DAY_MEETING"
        or expression_context.get("speaker", {}).get("id") != 2
        or not expression_context.get("output_contract")
    ):
        raise SystemExit("the voice-prefix call should receive only safe voice metadata")
    selected_signal_summaries = {
        item.get("summary")
        for item in decision_call_context.get("decision_signals", [])
        if item.get("id") == stub_llm_client.selected_signal_id
    }
    if any(summary in expression_context_text for summary in selected_signal_summaries):
        raise SystemExit("the voice-prefix call must not receive even selected game facts")
    if not selected_signal_summaries or not all(
        summary.rstrip("。") in llm_speech_response.speech.speech
        for summary in selected_signal_summaries
    ):
        raise SystemExit("the Python-rendered speech should preserve the selected signal summary")
    if not all(
        marker in llm_speech_response.speech.speech
        for marker in ["重点压力位", "我具体问", "不符合", "暂定票"]
    ):
        raise SystemExit(
            "the Python-rendered V3 body must preserve stance, question, verification, and provisional vote"
        )
    if not recovered_validation_log_path.exists():
        raise SystemExit("a rejected draft should be logged even when a later validation succeeds")

    llm_game_state.phase = "FREE_ACTIVITY"
    llm_private_response = private_chat(
        PrivateChatRequest(
            game_id=llm_game_state.game_id,
            npc_character_id=2,
            question="你最怀疑谁？",
        )
    )
    if not llm_private_response.llm_used or llm_private_response.llm_provider != "stub":
        raise SystemExit("enabled game should use the configured LLM for private chat")

    ambiguous_private_response = private_chat(
        PrivateChatRequest(
            game_id=llm_game_state.game_id,
            npc_character_id=3,
            question="你觉得他可信吗？",
        )
    )
    if not ambiguous_private_response.llm_used:
        raise SystemExit("ambiguous-reference clarification should still use the configured LLM")
finally:
    main_module.LLM_CLIENT = original_llm_client
    main_module.LLM_VALIDATION_LOG_FILE = original_recovered_validation_log_path
    recovered_validation_log_path.unlink(missing_ok=True)

class AlwaysInvalidStructuredLLMClient:
    def __init__(self):
        self.attempts = 0
        self.rejection_cases = []

    def status(self):
        return {
            "enabled": True,
            "provider": "stub",
            "model": "stub-model",
            "configured": True,
            "base_url": "",
        }

    def generate_json_object(
        self,
        _system_prompt,
        context,
        _fallback_object=None,
        max_attempts=None,
    ):
        self.attempts += 1
        legal_target = context["legal_targets"][0]
        public_evidence = next(
            item for item in context["evidence"]
            if item["visibility"] == "public"
        )
        private_evidence = next(
            item for item in context["evidence"]
            if item["visibility"] == "private"
        )
        data = {
            "schema_version": "public_speech.v1",
            "intent": "pressure",
            "target_id": legal_target["id"],
            "claim_option_ids": [],
            "evidence_ids": [public_evidence["id"]],
            "signal_ids": [],
        }
        if self.attempts == 1:
            data["target_id"] = 999
            self.rejection_cases.append("illegal_target")
        elif self.attempts == 2:
            data["claim_option_ids"] = ["claim:forged"]
            self.rejection_cases.append("illegal_claim")
        else:
            data["evidence_ids"] = [private_evidence["id"]]
            self.rejection_cases.append("private_evidence")
        return LLMJsonGeneration(
            data=data,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps(data, ensure_ascii=False),
        )

validation_failure_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "seer", "guard", "witch", "hunter"]
)
validation_failure_state.llm_enabled = True
validation_failure_state.phase = "DAY_MEETING"
validation_failure_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
validation_failure_speaker = validation_failure_state.characters[1]
validation_failure_target = validation_failure_state.characters[0]
validation_failure_speaker.memory_summary = "校验失败前的私有记忆。"
validation_failure_state.speeches = [
    SpeechState(
        day=1,
        character_id=validation_failure_target.id,
        name=validation_failure_target.name,
        speech="我没什么信息，先过吧。",
        is_player=True,
    ),
]
validation_failure_rag = [
    {
        "kind": "public",
        "title": "可公开证据",
        "content": "1号的公开发言可供观察。",
        "safe_to_show": True,
    },
    {
        "kind": "private",
        "title": "私有证据",
        "content": "这条证据不得公开引用。",
        "safe_to_show": False,
    },
]
always_invalid_client = AlwaysInvalidStructuredLLMClient()
validation_log_path = Path("/tmp/agent-town-llm-validation-smoke.jsonl")
original_validation_log_path = main_module.LLM_VALIDATION_LOG_FILE
try:
    validation_log_path.unlink(missing_ok=True)
    main_module.LLM_VALIDATION_LOG_FILE = validation_log_path
    main_module.LLM_CLIENT = always_invalid_client
    gameplay_before_failed_plan = (
        list(validation_failure_state.speeches),
        list(validation_failure_state.public_claims),
        list(validation_failure_state.public_logs),
        validation_failure_speaker.memory_summary,
    )
    (
        failed_target,
        failed_claims,
        failed_rag_context,
        failed_generation,
        failed_plan,
    ) = main_module.generate_structured_public_speech_plan(
        validation_failure_state,
        validation_failure_speaker,
        False,
        validation_failure_target,
        validation_failure_rag,
        [],
    )
    if failed_generation.used_llm or always_invalid_client.attempts != 5:
        raise SystemExit("invalid structured decisions should receive exactly five validation attempts")
    if set(always_invalid_client.rejection_cases) != {
        "illegal_target",
        "illegal_claim",
        "private_evidence",
    }:
        raise SystemExit("structured validation should exercise target, claim, and evidence allowlists")
    if (
        failed_target is None
        or failed_target.id != validation_failure_target.id
        or failed_plan.schema_version != "public_speech_plan.v3"
        or failed_plan.primary_target_id != validation_failure_target.id
        or failed_claims
        or len(failed_rag_context) != 1
        or not failed_rag_context[0].get("safe_to_show")
    ):
        raise SystemExit("five invalid structured attempts should return the deterministic rule plan")
    if (
        not failed_generation.decision_signal_ids
        or "信息量" not in failed_generation.text
        or validation_failure_target.name not in failed_generation.text
        or main_module.is_empty_pass_public_speech(failed_generation.text)
    ):
        raise SystemExit("five failed strategies should fall back to a concrete signal-grounded speech")
    gameplay_after_failed_plan = (
        list(validation_failure_state.speeches),
        list(validation_failure_state.public_claims),
        list(validation_failure_state.public_logs),
        validation_failure_speaker.memory_summary,
    )
    if gameplay_after_failed_plan != gameplay_before_failed_plan:
        raise SystemExit("structured validation failure must not write gameplay facts before commit")
    if not failed_generation.validation_failure_id:
        raise SystemExit("five failed validations should create a visible audit id")
    failure_view = main_module.build_llm_validation_failure_view(
        validation_failure_state,
        failed_generation.validation_failure_id,
    )
    if failure_view is None or len(failure_view.attempts) != 5:
        raise SystemExit("validation failure view should expose all five attempts")
    if not all(
        attempt.text == "[LLM 原始输出已隐藏]"
        for attempt in failure_view.attempts
    ):
        raise SystemExit("an in-game validation audit should hide every raw strategy output")
    if not all(attempt.sensitive for attempt in failure_view.attempts):
        raise SystemExit("every rejected private-context strategy JSON should be marked sensitive")
    full_failure_view = main_module.build_llm_validation_failure_view(
        validation_failure_state,
        failed_generation.validation_failure_id,
        reveal_sensitive=True,
    )
    if full_failure_view is None or not any(
        "claim:forged" in attempt.text for attempt in full_failure_view.attempts
    ):
        raise SystemExit("post-game validation audit should retain the original strategy JSON")
    if not validation_log_path.exists():
        raise SystemExit("validation failures should also be written to the backend JSONL log")
    raw_validation_log = validation_log_path.read_text(encoding="utf-8")
    for expected_raw_detail in ["target_not_allowed: 999", "claim:forged", "evidence:2"]:
        if expected_raw_detail not in raw_validation_log:
            raise SystemExit("the server-side log should retain structured rejection details")
    validation_log_records = [
        json.loads(line)
        for line in raw_validation_log.splitlines()
        if line.strip()
    ]
    if not validation_log_records or any(
        record.get("validator_version") != main_module.LLM_VALIDATOR_VERSION
        or not record.get("recorded_at")
        for record in validation_log_records
    ):
        raise SystemExit("validation log records should identify their validator version and time")
finally:
    main_module.LLM_CLIENT = original_llm_client
    main_module.LLM_VALIDATION_LOG_FILE = original_validation_log_path
    validation_log_path.unlink(missing_ok=True)

class IntentStructuredLLMClient:
    def __init__(self, intent, target_id, expression_text):
        self.intent = intent
        self.target_id = target_id
        self.expression_text = expression_text
        self.strategy_calls = 0
        self.expression_calls = 0

    def generate_json_object(
        self,
        _system_prompt,
        context,
        _fallback_object=None,
        max_attempts=None,
    ):
        self.strategy_calls += 1
        if self.target_id not in {item["id"] for item in context["legal_targets"]}:
            raise AssertionError("intent test target should be legal")
        data = {
            "schema_version": "public_speech.v1",
            "intent": self.intent,
            "target_id": self.target_id,
            "claim_option_ids": [],
            "evidence_ids": [
                item["id"]
                for item in context.get("evidence", [])
                if item.get("visibility") == "public"
            ][:1],
            "signal_ids": [],
        }
        return LLMJsonGeneration(
            data=data,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps(data, ensure_ascii=False),
        )

    def generate_json_text(
        self,
        _system_prompt,
        context,
        _fallback_text,
        max_attempts=None,
    ):
        if context.get("task") != "public_speech_voice_prefix":
            raise AssertionError("intent test should only call the public voice layer")
        self.expression_calls += 1
        return LLMGeneration(
            text="先把逻辑说清",
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps(
                {"text": "先把逻辑说清"},
                ensure_ascii=False,
            ),
        )

def run_structured_intent_update(intent, expression_text):
    state = make_rule_test_game(
        [
            "villager", "villager", "villager", "villager",
            "werewolf", "werewolf", "werewolf", "werewolf",
            "seer", "witch", "hunter", "guard",
        ]
    )
    state.llm_enabled = True
    state.phase = "DAY_MEETING"
    state.meeting = DayMeetingState(
        day=1,
        direction="clockwise",
        order=[2],
    )
    speaker = state.characters[1]
    target = state.characters[2]
    listener = state.characters[3]
    listener.suspicion[str(target.id)] = 20
    parsed_expression = main_module.parse_player_speech(state, expression_text)
    client = IntentStructuredLLMClient(intent, target.id, expression_text)
    main_module.LLM_CLIENT = client
    try:
        response = generate_npc_speech(
            NpcSpeechRequest(game_id=state.game_id, character_id=speaker.id)
        )
    finally:
        main_module.LLM_CLIENT = original_llm_client
    if client.strategy_calls != 1 or client.expression_calls != 1:
        raise SystemExit("structured intent should use one strategy and one voice-prefix call")
    if (
        target.name not in response.speech.speech
        or "先把逻辑说清" not in response.speech.speech
    ):
        raise SystemExit("structured intent speech should combine voice with Python-rendered facts")
    return parsed_expression, listener.suspicion.get(str(target.id), 0)

defend_text = "我不怀疑3号C罗，别急着推他。"
defend_parsed, suspicion_after_defend = run_structured_intent_update(
    "defend",
    defend_text,
)
if defend_parsed.accusations:
    raise SystemExit("explicitly defending target 3 must not be parsed as an accusation")
if not 0 <= suspicion_after_defend < 20:
    raise SystemExit("structured defend intent should lower listener suspicion")

_natural_defend_parsed, suspicion_after_natural_defend = run_structured_intent_update(
    "defend",
    "目前3号C罗的公开信息还不足以直接定性，我暂时不赞成把他推成焦点。",
)
if suspicion_after_natural_defend != suspicion_after_defend:
    raise SystemExit("natural defend wording should keep the structured defend intent")

_pressure_parsed, suspicion_after_pressure = run_structured_intent_update(
    "pressure",
    "3号C罗，先回答我的问题：你的验人逻辑是什么？犹豫只会暴露破绽。",
)
if suspicion_after_pressure <= 20:
    raise SystemExit("natural pressure wording should keep the structured pressure intent")

class LowInformationRetryLLMClient:
    def __init__(self, target_id, grounded_text):
        self.target_id = target_id
        self.grounded_text = grounded_text
        self.strategy_calls = 0
        self.expression_calls = 0
        self.selected_signal_id = ""

    def generate_json_object(
        self,
        _system_prompt,
        context,
        _fallback_object=None,
        max_attempts=None,
    ):
        self.strategy_calls += 1
        signal = next(
            item
            for item in context.get("decision_signals", [])
            if item.get("kind") == "low_information_speech"
            and item.get("actor_id") == self.target_id
        )
        self.selected_signal_id = signal["id"]
        data = {
            "schema_version": "public_speech.v1",
            "intent": "pressure",
            "target_id": self.target_id,
            "claim_option_ids": [],
            "evidence_ids": [],
            "signal_ids": [self.selected_signal_id],
        }
        return LLMJsonGeneration(
            data=data,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps(data, ensure_ascii=False),
        )

    def generate_json_text(
        self,
        _system_prompt,
        context,
        _fallback_text,
        max_attempts=None,
    ):
        if context.get("task") != "public_speech_voice_prefix":
            raise AssertionError("low-information test should use the voice-prefix layer")
        self.expression_calls += 1
        text = (
            f"我今天投{self.target_id}号"
            if self.expression_calls == 1
            else "先把细节说清"
        )
        return LLMGeneration(
            text=text,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps({"text": text}, ensure_ascii=False),
        )

low_information_state = make_rule_test_game(
    [
        "villager", "villager", "villager", "villager",
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
    ]
)
low_information_state.llm_enabled = True
low_information_state.phase = "DAY_MEETING"
low_information_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
low_information_speaker = low_information_state.characters[1]
low_information_target = low_information_state.characters[2]
low_information_listener = low_information_state.characters[3]
low_information_listener.suspicion[str(low_information_target.id)] = 20
low_information_state.speeches = [
    SpeechState(
        day=1,
        character_id=low_information_target.id,
        name=low_information_target.name,
        speech="我没什么信息，先过吧。",
        is_player=False,
    ),
]
low_information_baseline_state = low_information_state.model_copy(deep=True)
grounded_low_information_text = (
    "3号C罗，你上一轮发言信息量偏低，没有给出具体目标；"
    "现在请明确站边，我会结合你后续票型判断。"
)
low_information_client = LowInformationRetryLLMClient(
    low_information_target.id,
    grounded_low_information_text,
)
low_information_log_path = Path("/tmp/agent-town-low-information-smoke.jsonl")
original_low_information_log_path = main_module.LLM_VALIDATION_LOG_FILE
try:
    low_information_log_path.unlink(missing_ok=True)
    main_module.LLM_VALIDATION_LOG_FILE = low_information_log_path
    main_module.LLM_CLIENT = low_information_client
    low_information_response = generate_npc_speech(
        NpcSpeechRequest(
            game_id=low_information_state.game_id,
            character_id=low_information_speaker.id,
        )
    )
finally:
    main_module.LLM_CLIENT = original_llm_client
    main_module.LLM_VALIDATION_LOG_FILE = original_low_information_log_path
    low_information_log_path.unlink(missing_ok=True)
low_information_baseline_state.speeches.append(
    low_information_state.speeches[-1].model_copy(deep=True)
)
low_information_baseline_speaker = low_information_baseline_state.characters[1]
low_information_baseline_target = low_information_baseline_state.characters[2]
low_information_baseline_listener = low_information_baseline_state.characters[3]
main_module.apply_structured_public_speech_updates(
    low_information_baseline_state,
    low_information_baseline_speaker,
    PublicSpeechIntent.PRESSURE,
    low_information_baseline_target,
)
expected_low_information_suspicion = (
    low_information_baseline_listener.suspicion.get(
        str(low_information_baseline_target.id),
        0,
    )
)
if (
    low_information_client.strategy_calls != 1
    or low_information_client.expression_calls != 2
):
    raise SystemExit("an empty-pass expression should be rejected once and then retried")
if (
    "先把细节说清" not in low_information_response.speech.speech
    or low_information_target.name not in low_information_response.speech.speech
    or main_module.is_empty_pass_public_speech(low_information_response.speech.speech)
):
    raise SystemExit("the recovered voice prefix should keep a concrete Python-rendered contribution")
if low_information_state.speeches[-1].decision_signal_ids != [
    low_information_client.selected_signal_id
]:
    raise SystemExit("accepted public speech should retain its selected signal id for audit")
if (
    low_information_listener.suspicion.get(str(low_information_target.id), 0)
    != expected_low_information_suspicion
):
    raise SystemExit("a low-information assessment should not add suspicion beyond pressure intent")

fallback_signal_state = make_rule_test_game(
    [
        "villager", "villager", "villager", "villager",
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
    ]
)
fallback_signal_state.phase = "DAY_MEETING"
fallback_signal_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
fallback_signal_state.speeches = [
    SpeechState(
        day=1,
        character_id=3,
        name=fallback_signal_state.characters[2].name,
        speech="我没什么信息，先过吧。",
        is_player=False,
    ),
]
fallback_signal_speaker = fallback_signal_state.characters[1]
fallback_signal_context = main_module.build_public_speech_decision_context(
    fallback_signal_state,
    fallback_signal_speaker,
    [],
    [],
)
fallback_signal_decision = main_module.build_public_speech_fallback_decision(
    fallback_signal_context,
    None,
    "",
)
fallback_signal_errors = main_module.validate_public_speech_plan(
    fallback_signal_context,
    fallback_signal_decision,
)
if fallback_signal_errors:
    raise SystemExit(f"rule fallback should remain a legal structured decision: {fallback_signal_errors}")
fallback_signal_target = main_module.get_character(
    fallback_signal_state,
    fallback_signal_decision.primary_target_id,
)
fallback_selected_signals = [
    signal
    for signal in fallback_signal_context.decision_signals
    if signal.id in fallback_signal_decision.signal_ids
]
fallback_signal_text = main_module.build_structured_public_speech_rule_text(
    fallback_signal_state,
    fallback_signal_speaker,
    False,
    fallback_signal_decision,
    fallback_signal_target,
    None,
    [],
    fallback_selected_signals,
)
if (
    fallback_signal_decision.primary_target_id != 3
    or not fallback_signal_decision.signal_ids
    or not all(
        main_module.text_preserves_public_signal(
            fallback_signal_text,
            signal,
            fallback_signal_state,
        )
        for signal in fallback_selected_signals
    )
    or not main_module.text_mentions_character(
        fallback_signal_text,
        fallback_signal_target,
    )
    or not any(
        marker in fallback_signal_text
        for marker in ["解释", "明确", "站边", "票型", "验证", "检验"]
    )
    or main_module.is_empty_pass_public_speech(fallback_signal_text)
):
    raise SystemExit("rule fallback should target the low-information speaker and make a concrete follow-up")

class RoleOnlyRevealLLMClient:
    def __init__(self):
        self.strategy_attempts = 0
        self.expression_calls = 0

    def generate_json_object(
        self,
        _system_prompt,
        context,
        _fallback_object=None,
        max_attempts=None,
    ):
        self.strategy_attempts += 1
        claim_option_id = context["claim_options"][0]["id"]
        data = {
            "schema_version": "public_speech.v1",
            "intent": "reveal",
            "target_id": 3 if self.strategy_attempts == 1 else None,
            "claim_option_ids": [claim_option_id],
            "evidence_ids": [],
            "signal_ids": [],
        }
        return LLMJsonGeneration(
            data=data,
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps(data, ensure_ascii=False),
        )

    def generate_json_text(
        self,
        _system_prompt,
        context,
        fallback_text,
        max_attempts=None,
    ):
        if context.get("task") != "public_speech_voice_prefix":
            raise AssertionError("role-only reveal should use the public voice layer")
        self.expression_calls += 1
        return LLMGeneration(
            text="这次我说清楚",
            used_llm=True,
            provider="stub",
            model="stub-model",
            raw_response_text=json.dumps({"text": "这次我说清楚"}, ensure_ascii=False),
        )

role_only_state = make_rule_test_game(
    ["villager", "hunter", "villager", "werewolf", "seer", "witch", "guard"]
)
role_only_state.llm_enabled = True
role_only_state.phase = "DAY_MEETING"
role_only_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
role_only_speaker = role_only_state.characters[1]
role_only_fallback_target = role_only_state.characters[2]
role_only_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=role_only_speaker.id,
        claim_type="role",
        claimed_role="hunter",
        source="role_only_smoke",
    )
]
role_only_context = main_module.build_public_speech_decision_context(
    role_only_state,
    role_only_speaker,
    [],
    role_only_claims,
)
role_only_rule_fallback = main_module.build_public_speech_fallback_decision(
    role_only_context,
    role_only_fallback_target,
    "",
)
if (
    role_only_rule_fallback.intent.value != "reveal"
    or role_only_rule_fallback.primary_target_id is not None
    or not role_only_rule_fallback.claim_option_ids
):
    raise SystemExit("a role-only rule fallback must reveal with target_id null")

role_only_client = RoleOnlyRevealLLMClient()
role_only_log_path = Path("/tmp/agent-town-role-only-reveal-smoke.jsonl")
original_role_only_log_path = main_module.LLM_VALIDATION_LOG_FILE
try:
    role_only_log_path.unlink(missing_ok=True)
    main_module.LLM_VALIDATION_LOG_FILE = role_only_log_path
    main_module.LLM_CLIENT = role_only_client
    (
        role_only_target,
        selected_role_only_claims,
        _role_only_rag,
        role_only_generation,
        role_only_plan,
    ) = main_module.generate_structured_public_speech_plan(
        role_only_state,
        role_only_speaker,
        False,
        role_only_fallback_target,
        [],
        role_only_claims,
    )
    if (
        role_only_client.strategy_attempts != 2
        or role_only_client.expression_calls != 1
        or role_only_target is not None
        or role_only_plan.schema_version != "public_speech_plan.v3"
        or role_only_plan.primary_target_id is not None
        or selected_role_only_claims != role_only_claims
        or not role_only_generation.used_llm
        or role_only_generation.decision_intent != "reveal"
    ):
        raise SystemExit("role-only reveal should reject a target then accept target_id null")
    if (
        not role_only_log_path.exists()
        or "role-only reveal must use primary_target_id null"
        not in role_only_log_path.read_text(encoding="utf-8")
    ):
        raise SystemExit("role-only non-null target rejection should be audited")
finally:
    main_module.LLM_CLIENT = original_llm_client
    main_module.LLM_VALIDATION_LOG_FILE = original_role_only_log_path
    role_only_log_path.unlink(missing_ok=True)

meeting_influence_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "villager", "guard", "seer"]
)
meeting_influence_state.phase = "DAY_MEETING"
meeting_influence_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(1, 13)),
)
submit_player_speech(
    PlayerSpeechRequest(
        game_id=meeting_influence_state.game_id,
        character_id=1,
        speech="我觉得3号很可疑。",
    )
)
later_listener = meeting_influence_state.characters[3]
before_npc_speech = later_listener.suspicion.get("3", 0)
generate_npc_speech(
    NpcSpeechRequest(
        game_id=meeting_influence_state.game_id,
        character_id=2,
    )
)
if later_listener.suspicion.get("3", 0) <= before_npc_speech:
    raise SystemExit("an earlier NPC speech should affect later NPC suspicion")

meeting_influence_state.phase = "FREE_ACTIVITY"
private_npc = meeting_influence_state.characters[1]
private_target = meeting_influence_state.characters[2]
public_logs_before_private_chat = list(meeting_influence_state.public_logs)
suspicion_before_private_chat = private_npc.suspicion.get(str(private_target.id), 0)
first_private_response = private_chat(
    PrivateChatRequest(
        game_id=meeting_influence_state.game_id,
        npc_character_id=private_npc.id,
        question=f"我觉得{private_target.id}号很可疑，我们一起合作。",
    )
)
if not first_private_response.effective:
    raise SystemExit("the first daily private question should affect NPC decisions")
if private_npc.suspicion.get(str(private_target.id), 0) <= suspicion_before_private_chat:
    raise SystemExit("an effective private question should update the target NPC suspicion")
if meeting_influence_state.public_logs != public_logs_before_private_chat:
    raise SystemExit("private chat must not be written to public logs")
if first_private_response.retrieval_mode not in {"hybrid", "keyword"}:
    raise SystemExit("private chat should expose the active retrieval mode")
if any("私有记忆" in title for title in first_private_response.knowledge_titles):
    raise SystemExit("private RAG source titles must not leak private memory")
first_private_conversation = meeting_influence_state.private_conversations[-1]
first_private_influences = {
    (influence.target_id, influence.direction)
    for influence in first_private_conversation.belief_influences
}
if first_private_influences != {
    (private_target.id, "suspect"),
    (meeting_influence_state.player_character_id, "trust"),
}:
    raise SystemExit("an effective private chat must retain its applied target directions")
private_evidence_ids = [
    influence.evidence_id
    for influence in first_private_conversation.belief_influences
]
if (
    len(private_evidence_ids) != len(set(private_evidence_ids))
    or not all(
        evidence_id.startswith("belief:private_chat:")
        for evidence_id in private_evidence_ids
    )
):
    raise SystemExit("structured private-chat evidence ids must be stable and unique")
owner_private_snapshot = build_belief_snapshot(
    meeting_influence_state,
    observer_ids=[private_npc.id],
)
owner_private_evidence = [
    evidence
    for evidence in owner_private_snapshot["evidence_ledger"]
    if evidence["kind"].startswith("private_chat_")
]
if {
    evidence["evidence_id"]
    for evidence in owner_private_evidence
} != set(private_evidence_ids) or any(
    evidence["observer_ids"] != [private_npc.id]
    for evidence in owner_private_evidence
):
    raise SystemExit("private-chat belief evidence must be scoped to its NPC listener")
other_private_observer = next(
    character
    for character in meeting_influence_state.characters
    if not character.is_player and character.id != private_npc.id
)
if any(
    evidence["kind"].startswith("private_chat_")
    for evidence in build_belief_snapshot(
        meeting_influence_state,
        observer_ids=[other_private_observer.id],
    )["evidence_ledger"]
):
    raise SystemExit("one NPC must not receive another NPC's private-chat evidence")
private_text_variant = meeting_influence_state.model_copy(deep=True)
private_text_variant.private_conversations[-1].question = "完全不同的私聊自由文本"
private_text_variant.private_conversations[-1].reply = "完全不同的 NPC 回复"
if owner_private_snapshot != build_belief_snapshot(
    private_text_variant,
    observer_ids=[private_npc.id],
):
    raise SystemExit("belief projection must consume structured private chat, not free text")
private_hidden_swap = meeting_influence_state.model_copy(deep=True)
private_hidden_target = main_module.get_character(
    private_hidden_swap,
    private_target.id,
)
private_hidden_good = next(
    character
    for character in private_hidden_swap.characters
    if (
        not character.is_player
        and character.id not in {private_npc.id, private_hidden_target.id}
        and character.camp == "good"
    )
)
private_hidden_target.role, private_hidden_good.role = (
    private_hidden_good.role,
    private_hidden_target.role,
)
private_hidden_target.camp, private_hidden_good.camp = (
    private_hidden_good.camp,
    private_hidden_target.camp,
)
if owner_private_snapshot != build_belief_snapshot(
    private_hidden_swap,
    observer_ids=[private_npc.id],
):
    raise SystemExit("private-chat beliefs must not inspect a target's hidden role")
private_chat_day_two = meeting_influence_state.model_copy(deep=True)
private_chat_day_two.day = 2
private_weights_day_one = {
    contribution["evidence_id"]: contribution["weight"]
    for actor in owner_private_snapshot["actors"]
    for seat in actor["seats"]
    for contribution in seat["contributions"]
    if contribution["evidence_id"] in private_evidence_ids
}
private_weights_day_two = {
    contribution["evidence_id"]: contribution["weight"]
    for actor in build_belief_snapshot(
        private_chat_day_two,
        observer_ids=[private_npc.id],
    )["actors"]
    for seat in actor["seats"]
    for contribution in seat["contributions"]
    if contribution["evidence_id"] in private_evidence_ids
}
if private_weights_day_one != private_weights_day_two:
    raise SystemExit("structured private-chat evidence must not use public soft decay")
private_view = next(
    character
    for character in get_wolf_game_state(meeting_influence_state.game_id).characters
    if character.id == private_npc.id
)
if not private_view.private_question_used_today:
    raise SystemExit("character view should expose that today's effective private question was used")

decision_snapshot = (
    dict(private_npc.suspicion),
    dict(private_npc.relationships[str(meeting_influence_state.player_character_id)]),
    private_npc.memory_summary,
)
second_private_response = private_chat(
    PrivateChatRequest(
        game_id=meeting_influence_state.game_id,
        npc_character_id=private_npc.id,
        question=f"你再想想{private_target.id}号。",
    )
)
if second_private_response.effective:
    raise SystemExit("a second private question to the same NPC should not affect decisions")
if meeting_influence_state.private_conversations[-1].belief_influences:
    raise SystemExit("an ineffective follow-up must not create private belief evidence")
if decision_snapshot != (
    dict(private_npc.suspicion),
    dict(private_npc.relationships[str(meeting_influence_state.player_character_id)]),
    private_npc.memory_summary,
):
    raise SystemExit("follow-up private questions should not update decision state again")
if meeting_influence_state.public_logs != public_logs_before_private_chat:
    raise SystemExit("follow-up private chat must remain private")

private_npc.memory_summary += "\\n绝密私有记忆：3号的隐藏身份。"
public_decision_context = build_public_decision_rag_context(
    meeting_influence_state,
    private_npc,
    private_target,
    "公开发言",
)
if any(context.get("kind") == "private" for context in public_decision_context):
    raise SystemExit("public-decision RAG must not retrieve private-memory items")
if any("绝密私有记忆" in str(context.get("content", "")) for context in public_decision_context):
    raise SystemExit("public-decision RAG leaked private memory content")

perspective_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "seer", "guard", "villager"]
)
perspective_state.phase = "FREE_ACTIVITY"
perspective_npc = perspective_state.characters[1]
perspective_response = private_chat(
    PrivateChatRequest(
        game_id=perspective_state.game_id,
        npc_character_id=perspective_npc.id,
        question="我怀疑你，你最怀疑谁？",
    )
)
if not perspective_response.effective or "你直接怀疑我" not in perspective_response.reply:
    raise SystemExit("directly accusing the current NPC should use the private-chat perspective")
if perspective_state.characters[0].name in perspective_response.reply or perspective_npc.name in perspective_response.reply:
    raise SystemExit("private reply should call the player 你 and the current NPC 我")

reference_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "seer", "guard", "villager"]
)
reference_state.phase = "FREE_ACTIVITY"
ambiguous_response = private_chat(
    PrivateChatRequest(
        game_id=reference_state.game_id,
        npc_character_id=2,
        question="他是不是狼？",
    )
)
if ambiguous_response.effective or not ambiguous_response.can_influence_again:
    raise SystemExit("an unresolved pronoun should not consume the effective private question")
if reference_state.private_conversations[-1].belief_influences:
    raise SystemExit("an unresolved private pronoun must not create belief evidence")
if "哪位角色" not in ambiguous_response.reply:
    raise SystemExit("an unresolved pronoun should ask the player to name a character")
private_chat(
    PrivateChatRequest(
        game_id=reference_state.game_id,
        npc_character_id=2,
        question="我想问3号C罗。",
    )
)
followup_response = private_chat(
    PrivateChatRequest(
        game_id=reference_state.game_id,
        npc_character_id=2,
        question="我怀疑他。",
    )
)
if "3号 C罗" not in followup_response.reply:
    raise SystemExit("a follow-up pronoun should resolve to the latest explicit third party")

guard_state = make_rule_test_game(["guard", "villager", "werewolf", "villager", "villager", "villager"])
guard_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="guard_protect", target_id=2),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=2),
]
guard_result = resolve_night(NightResolveRequest(game_id=guard_state.game_id))
if guard_result.dead_characters:
    raise SystemExit("guarded character should survive wolf kill")
if not guard_result.is_peaceful_night:
    raise SystemExit("guard protection should create a peaceful night")
if not guard_state.characters[1].alive:
    raise SystemExit("guarded target should remain alive")
if "成功挡下狼刀" not in guard_state.characters[0].memory_summary:
    raise SystemExit("guard should remember successful protection")

player_seer_state = make_rule_test_game(["seer", "villager", "werewolf", "villager", "villager", "villager"])
player_seer_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=3, action_type="none", target_id=None),
]
player_seer_result = resolve_night(NightResolveRequest(game_id=player_seer_state.game_id))
seer_check = player_seer_result.player_private_result.get("seer_check", {})
if seer_check.get("target_id") != 3 or seer_check.get("result") != "werewolf":
    raise SystemExit("player seer should learn checked target camp")
state_after_player_seer = get_wolf_game_state(player_seer_state.game_id)
last_check = state_after_player_seer.player_private_info.last_check_result or {}
if last_check.get("target_id") != 3 or last_check.get("result") != "werewolf":
    raise SystemExit("player seer check should persist in private state")
if not any(
    "第1夜 · 预言家：查验3号 C罗 → 狼人" in item
    for item in state_after_player_seer.player_private_info.action_history
):
    raise SystemExit("player action history should show resolved seer checks")
if "查验" not in player_seer_state.characters[0].memory_summary:
    raise SystemExit("player seer should remember check result")

full_player_speech = "这是需要完整保留在玩家行动记录中的公开发言。"
player_seer_state.speeches.append(
    SpeechState(
        day=1,
        character_id=1,
        name="规则测试",
        speech=full_player_speech,
        is_player=True,
        phase="DAY_MEETING",
    )
)
player_seer_state.private_conversations.append(
    PrivateConversationState(
        day=1,
        npc_character_id=2,
        question="你如何评价3号？",
        reply="我会继续观察。",
        effective=True,
    )
)
player_seer_state.votes.append(
    VoteState(day=1, voter_id=1, target_id=3, reason="我的公开投票理由。")
)
complete_player_history = get_wolf_game_state(
    player_seer_state.game_id
).player_private_info.action_history
if not any(full_player_speech in item for item in complete_player_history):
    raise SystemExit("player action history should retain the full public speech")
if not any("私聊2号 梅西：你如何评价3号？" in item for item in complete_player_history):
    raise SystemExit("player action history should retain private questions")
if not any("投给3号 C罗；理由：我的公开投票理由。" in item for item in complete_player_history):
    raise SystemExit("player action history should retain vote targets and reasons")

npc_seer_state = make_rule_test_game(["villager", "seer", "werewolf", "villager", "villager", "villager"])
npc_seer_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=3, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=npc_seer_state.game_id))
npc_seer = npc_seer_state.characters[1]
if npc_seer.suspicion.get("3", 0) < 100:
    raise SystemExit("NPC seer should strongly suspect checked werewolf")
if "查验" not in npc_seer.memory_summary:
    raise SystemExit("NPC seer should remember check result")
npc_seer_view = next(
    character
    for character in get_wolf_game_state(npc_seer_state.game_id).characters
    if character.id == 2
)
if npc_seer_view.memory_count <= 0:
    raise SystemExit("character view should expose memory count")

player_claim_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "guard", "witch", "hunter"]
)
player_claim_state.phase = "DAY_MEETING"
player_claim_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(1, 13)),
)
player_claim_response = submit_player_speech(
    PlayerSpeechRequest(
        game_id=player_claim_state.game_id,
        character_id=1,
        speech="我是预言家，昨晚查验3号C罗是狼人。",
    )
)
if len(player_claim_response.parsed.claims) != 2:
    raise SystemExit("player speech should parse role and seer-check claims")
player_claim_view = get_wolf_game_state(player_claim_state.game_id).characters[0]
if player_claim_view.claimed_role != "seer":
    raise SystemExit("player public role claim should appear in the character view")
if not any("称验3号 C罗为狼人" in label for label in player_claim_view.public_claims):
    raise SystemExit("player claimed check should appear as a neutral public label")
player_claim_public_intel = get_wolf_game_state(player_claim_state.game_id).public_intel
if not any(
    item.kind == "role"
    and item.claimed_role == "seer"
    and "公开跳预言家" in item.display_text
    for item in player_claim_public_intel
):
    raise SystemExit("the public-intel view should expose a neutral seer claim")
if not any(
    item.kind == "seer_check"
    and item.target_id == 3
    and item.result == "werewolf"
    and "查杀" in item.display_text
    for item in player_claim_public_intel
):
    raise SystemExit("the public-intel view should expose the claimed seer result")
if any(
    "source" in item.model_dump()
    or "role" in item.model_dump()
    or "camp" in item.model_dump()
    for item in player_claim_public_intel
):
    raise SystemExit("public-intel entries must not expose claim origin or hidden truth")
public_intel_before_source_change = [
    item.model_dump(mode="json") for item in player_claim_public_intel
]
for claim in player_claim_state.public_claims:
    claim.source = "wolf_fake_seer"
public_intel_after_source_change = [
    item.model_dump(mode="json")
    for item in get_wolf_game_state(player_claim_state.game_id).public_intel
]
if public_intel_before_source_change != public_intel_after_source_change:
    raise SystemExit("public-intel projection must be invariant to hidden claim source")

power_intel_state = make_rule_test_game(
    ["villager", "witch", "guard", "hunter", "villager", "werewolf"]
)
main_module.register_public_claims(
    power_intel_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=2,
            claim_type="role",
            claimed_role="witch",
            source="true_role",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=2,
            claim_type="witch_save",
            claimed_role="witch",
            target_id=5,
            source="night_1",
        ),
        main_module.PublicClaimState(
            day=2,
            character_id=2,
            claim_type="witch_poison",
            claimed_role="witch",
            target_id=6,
            source="night_2",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="role",
            claimed_role="guard",
            source="true_role",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="guard_success",
            claimed_role="guard",
            target_id=5,
            source="night_1",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=4,
            claim_type="role",
            claimed_role="hunter",
            source="true_role",
        ),
    ],
)
power_intel_state.hunter_shots.append(
    HunterShotState(day=2, hunter_id=4, target_id=5, trigger="exile")
)
power_public_intel = get_wolf_game_state(power_intel_state.game_id).public_intel
power_public_text = "\\n".join(item.display_text for item in power_public_intel)
for expected_public_text in [
    "2号 梅西公开跳女巫",
    "2号 梅西声称用解药救了5号 梅长苏",
    "2号 梅西声称用毒药毒了6号 塞尔达",
    "3号 C罗公开跳守卫",
    "3号 C罗声称守护5号 梅长苏成功",
    "4号 周深公开跳猎人",
    "4号 周深开枪带走5号 梅长苏",
]:
    if expected_public_text not in power_public_text:
        raise SystemExit("public-intel accordion data is missing: " + expected_public_text)
if not any(item.category == "confirmed_action" for item in power_public_intel):
    raise SystemExit("confirmed hunter actions should be distinct from unverified claims")

true_seer_claim_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "guard", "witch", "hunter"]
)
true_seer_claim_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=3, action_type="none", target_id=None),
]
true_seer_claim_state.phase = "DAY_MEETING"
true_seer_claim_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
true_seer_speech = generate_npc_speech(
    NpcSpeechRequest(game_id=true_seer_claim_state.game_id, character_id=2)
).speech.speech
if "预言家" not in true_seer_speech or "C罗" not in true_seer_speech or "狼人" not in true_seer_speech:
    raise SystemExit("true NPC seer should claim and report a wolf check")
true_seer_claims = [
    claim
    for claim in true_seer_claim_state.public_claims
    if claim.character_id == 2
]
if {claim.claim_type for claim in true_seer_claims} != {"role", "seer_check"}:
    raise SystemExit("true NPC seer claims should be stored structurally")

fake_seer_state = make_rule_test_game(
    ["villager", "werewolf", "seer", "werewolf", "guard", "witch", "hunter"]
)
fake_seer_state.wolf_fake_seer_id = 2
main_module.register_public_claims(
    fake_seer_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="role",
            claimed_role="seer",
            source="true_role",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=2,
            result="werewolf",
            source="night_1",
        ),
    ],
)
fake_seer_state.phase = "DAY_MEETING"
fake_seer_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
fake_seer_actor = main_module.get_character(fake_seer_state, 2)
for fake_check_seed in range(1_000):
    fake_seer_state.random_seed = fake_check_seed
    planned_fake_check = main_module.choose_fake_seer_check(
        fake_seer_state,
        fake_seer_actor,
    )
    if planned_fake_check is not None and planned_fake_check[1] == "werewolf":
        break
else:
    raise SystemExit("fake-seer fixture must find a deterministic black-check seed")
pre_fake_check_suspicion = {
    character.id: dict(character.suspicion)
    for character in fake_seer_state.characters
}
generate_npc_speech(
    NpcSpeechRequest(game_id=fake_seer_state.game_id, character_id=2)
)
day_one_fake_checks = [
    claim
    for claim in fake_seer_state.public_claims
    if claim.character_id == 2 and claim.claim_type == "seer_check"
]
if len(day_one_fake_checks) != 1 or day_one_fake_checks[0].source != "wolf_fake_seer":
    raise SystemExit("designated NPC wolf should counterclaim seer with a fake check")
fake_target_id = day_one_fake_checks[0].target_id
good_listener = next(
    character
    for character in fake_seer_state.characters
    if (
        not character.is_player
        and character.camp == "good"
        and character.role != "seer"
        and character.id != fake_target_id
    )
)
fake_check_suspicion_before = pre_fake_check_suspicion[good_listener.id].get(
    str(fake_target_id),
    0,
)
fake_check_suspicion_after = good_listener.suspicion.get(str(fake_target_id), 0)
if (
    day_one_fake_checks[0].result != "werewolf"
    or fake_check_suspicion_after <= fake_check_suspicion_before
):
    raise SystemExit("a fake black check should influence ordinary NPC suspicion")

fake_seer_state.day = 2
fake_seer_state.phase = "DAY_MEETING"
fake_seer_state.meeting = DayMeetingState(
    day=2,
    direction="clockwise",
    order=[2],
)
generate_npc_speech(
    NpcSpeechRequest(game_id=fake_seer_state.game_id, character_id=2)
)
all_fake_checks = [
    claim
    for claim in fake_seer_state.public_claims
    if claim.character_id == 2 and claim.claim_type == "seer_check"
]
if len(all_fake_checks) != 2 or len({claim.target_id for claim in all_fake_checks}) != 2:
    raise SystemExit("fake seer should maintain a new, non-contradictory check each day")

wolf_check_wolf_state = make_rule_test_game(
    ["villager", "werewolf", "seer", "werewolf", "werewolf", "werewolf"]
)
wolf_check_wolf_state.wolf_fake_seer_id = 2
wolf_check_wolf_state.speeches = [
    SpeechState(
        day=1,
        character_id=character.id,
        name=character.name,
        speech="我公开把4号放进压力位。",
        is_player=character.is_player,
        decision_intent="pressure",
        focus_target_id=4,
    )
    for character in wolf_check_wolf_state.characters
    if character.id != 4
][:9]
if main_module.get_public_suspicion_score(wolf_check_wolf_state, 4) < (
    main_module.get_character_strategy_tuning(
        wolf_check_wolf_state.characters[1]
    ).teammate_black_check_min_pressure
):
    raise SystemExit("wolf-checks-wolf regression must exceed the tuned pressure threshold")
wolf_check_target = main_module.choose_fake_seer_check(
    wolf_check_wolf_state,
    wolf_check_wolf_state.characters[1],
)
if wolf_check_target != (4, "werewolf") or wolf_check_wolf_state.wolf_checked_wolf_used:
    raise SystemExit("planning a wolf-checks-wolf option must not consume it before commit")
main_module.register_public_claims(
    wolf_check_wolf_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=2,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=4,
            result="werewolf",
            source="wolf_fake_seer",
        )
    ],
)
if not wolf_check_wolf_state.wolf_checked_wolf_used:
    raise SystemExit("committing a wolf-checks-wolf claim should consume the strategy")

witch_claim_state = make_rule_test_game(
    ["villager", "villager", "witch", "werewolf", "villager", "seer", "guard", "hunter"]
)
witch_claim_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="witch_poison", target_id=4),
]
witch_claim_types = {
    claim.claim_type
    for claim in main_module.plan_npc_public_claims(
        witch_claim_state,
        witch_claim_state.characters[2],
    )
}
if witch_claim_types != {"role", "witch_poison"}:
    raise SystemExit("a bold NPC witch should be able to reveal a used potion")

guard_claim_state = make_rule_test_game(
    ["villager", "villager", "guard", "werewolf", "villager", "seer", "witch", "hunter"]
)
guard_claim_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="guard_protect", target_id=5),
]
guard_claim_state.night_resolutions = [
    NightResolutionState(day=1, attacked_target_id=5, protected_ids=[5], dead_character_ids=[]),
]
guard_claim_types = {
    claim.claim_type
    for claim in main_module.plan_npc_public_claims(
        guard_claim_state,
        guard_claim_state.characters[2],
    )
}
if guard_claim_types != {"role", "guard_success"}:
    raise SystemExit("a bold NPC guard should be able to reveal a successful protection")

hunter_claim_state = make_rule_test_game(
    ["villager", "villager", "hunter", "werewolf", "villager", "seer", "witch", "guard"]
)
hunter_claim_state.speeches = [
    SpeechState(
        day=1,
        character_id=character.id,
        name=character.name,
        speech="我公开质疑3号。",
        is_player=character.is_player,
        decision_intent="pressure",
        focus_target_id=3,
    )
    for character in hunter_claim_state.characters
    if character.id != 3
][:5]
hunter_claims = main_module.plan_npc_public_claims(
    hunter_claim_state,
    hunter_claim_state.characters[2],
)
if not any(claim.claimed_role == "hunter" for claim in hunter_claims):
    raise SystemExit("an NPC hunter under pressure should be able to reveal the role")

voice_state = make_rule_test_game(["villager"])
voice_npc = voice_state.characters[1]
voice_profile = main_module.get_npc_voice_profile(voice_npc.name)
if not voice_profile["speech_style"] or not voice_profile["catchphrases"] or not voice_profile["easter_eggs"]:
    raise SystemExit("wolf-game NPC should expose configured voice and easter-egg data")
voice_changed = False
for test_day in range(1, 12):
    voice_state.day = test_day
    if main_module.apply_npc_voice(voice_state, voice_npc, "基础判断。", "meeting") != "基础判断。":
        voice_changed = True
        break
if not voice_changed:
    raise SystemExit("configured NPC voice should occasionally affect rule speech")

easter_egg_state = make_rule_test_game(["villager"])
easter_egg_state.phase = "FREE_ACTIVITY"
mei_changsu = next(
    character for character in easter_egg_state.characters
    if character.name == "梅长苏"
)
mei_changsu.role = "guard"
mei_changsu.camp = "good"
easter_egg_response = private_chat(
    PrivateChatRequest(
        game_id=easter_egg_state.game_id,
        npc_character_id=mei_changsu.id,
        question="林殊！",
    )
)
if not easter_egg_response.easter_egg_triggered or not easter_egg_response.easter_egg_first_time:
    raise SystemExit("梅长苏 should recognize the 林殊 trigger with punctuation")
if easter_egg_response.effective or not easter_egg_response.can_influence_again:
    raise SystemExit("a trigger easter egg must not consume the effective private question")
if "我是守卫" not in easter_egg_response.reply:
    raise SystemExit("梅长苏's 林殊 easter egg must reveal the real game role")

repeat_easter_egg_response = private_chat(
    PrivateChatRequest(
        game_id=easter_egg_state.game_id,
        npc_character_id=mei_changsu.id,
        question="你真的是林殊吗？",
    )
)
if not repeat_easter_egg_response.easter_egg_triggered or repeat_easter_egg_response.easter_egg_first_time:
    raise SystemExit("a repeated trigger should use the repeat easter-egg response")
easter_egg_history = get_wolf_game_state(easter_egg_state.game_id).player_private_info.action_history
if sum("发现梅长苏的关键词彩蛋" in item for item in easter_egg_history) != 1:
    raise SystemExit("a trigger easter egg should appear once in player private history")
if not any("本局身份是守卫" in item for item in easter_egg_history):
    raise SystemExit("the privately revealed role should be saved in player action history")

for trigger_npc in easter_egg_state.characters:
    if trigger_npc.is_player or trigger_npc.id == mei_changsu.id:
        continue
    trigger_profile = main_module.NPC_PROFILES[trigger_npc.name]
    trigger_text = trigger_profile.trigger_easter_eggs[0].triggers[0]
    trigger_response = private_chat(
        PrivateChatRequest(
            game_id=easter_egg_state.game_id,
            npc_character_id=trigger_npc.id,
            question=f"试试这个口令：{trigger_text}！",
        )
    )
    if not trigger_response.easter_egg_triggered or not trigger_response.easter_egg_first_time:
        raise SystemExit(f"{trigger_npc.name} trigger easter egg should work in private chat")
    if trigger_response.effective:
        raise SystemExit(f"{trigger_npc.name} trigger easter egg must not affect decisions")

post_easter_egg_question = private_chat(
    PrivateChatRequest(
        game_id=easter_egg_state.game_id,
        npc_character_id=mei_changsu.id,
        question="我怀疑2号梅西，他的发言需要解释。",
    )
)
if not post_easter_egg_question.effective:
    raise SystemExit("a normal private question should remain effective after an easter egg")

easter_egg_rule_text = main_module.build_triggered_easter_egg_reply(
    mei_changsu,
    main_module.NPC_PROFILES["梅长苏"].trigger_easter_eggs[0],
    True,
)
authorized_role_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="你既然认出了林殊，我便直说：我是守卫，这件事暂且不要公开。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    easter_egg_rule_text,
    easter_egg_state,
    speaker=mei_changsu,
    required_self_role="guard",
)
if not authorized_role_rewrite.used_llm:
    raise SystemExit("validator should accept the authorized true self-role easter egg")

for invalid_text in [
    "你既然认出了林殊，这件事暂且不要公开。",
    "你既然认出了林殊，我便直说：我是狼人。",
    "你既然认出了林殊，我是守卫，但我也继续以预言家身份行动。",
]:
    invalid_role_rewrite = main_module.validate_llm_rewrite(
        LLMGeneration(
            text=invalid_text,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        easter_egg_rule_text,
        easter_egg_state,
        speaker=mei_changsu,
        required_self_role="guard",
    )
    if invalid_role_rewrite.used_llm:
        raise SystemExit("validator should reject an omitted or changed easter-egg role")

wolf_team_state = make_rule_test_game(
    [
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
        "villager", "villager", "villager", "villager",
    ]
)
wolf_team_view = get_wolf_game_state(wolf_team_state.game_id)
if len(wolf_team_view.player_private_info.wolf_teammates) != 3:
    raise SystemExit("werewolf player should receive all living wolf teammates")
visible_wolf_ids = {
    character.id
    for character in wolf_team_view.characters
    if character.role_visible_to_player == "werewolf"
}
if visible_wolf_ids != {1, 2, 3, 4}:
    raise SystemExit("werewolf player should see all four wolf identities")
for wolf in wolf_team_state.characters[:4]:
    teammate_ids = {1, 2, 3, 4} - {wolf.id}
    if any(
        wolf.relationships[str(teammate_id)].get("alliance") != "wolf_teammate"
        for teammate_id in teammate_ids
    ):
        raise SystemExit("NPC wolves should internally recognize every wolf teammate")

wolf_speaker = wolf_team_state.characters[1]
low_pressure_focus = main_module.choose_speech_focus_target(wolf_team_state, wolf_speaker)
if low_pressure_focus is None or low_pressure_focus.role == "werewolf":
    raise SystemExit("NPC wolf should avoid exposing a low-pressure teammate")
high_pressure_teammate = wolf_team_state.characters[2]
public_pressure_speakers = [
    character
    for character in wolf_team_state.characters
    if character.id != high_pressure_teammate.id
][:7]
wolf_team_state.speeches = [
    SpeechState(
        day=1,
        character_id=character.id,
        name=character.name,
        speech=f"我公开质疑{high_pressure_teammate.id}号。",
        is_player=character.is_player,
        decision_intent="pressure",
        focus_target_id=high_pressure_teammate.id,
    )
    for character in public_pressure_speakers
]
designated_bus_ids = main_module.get_designated_wolf_bus_actor_ids(
    wolf_team_state,
    high_pressure_teammate,
)
if len(designated_bus_ids) != 1:
    raise SystemExit("moderate public pressure should designate exactly one wolf bus actor")
designated_bus_wolf = main_module.get_character(
    wolf_team_state,
    next(iter(designated_bus_ids)),
)
non_designated_wolf = next(
    character
    for character in wolf_team_state.characters
    if character.role == "werewolf"
    and not character.is_player
    and character.id not in designated_bus_ids
    and character.id != high_pressure_teammate.id
)
if not main_module.should_wolf_sell_teammate(
    wolf_team_state,
    designated_bus_wolf,
    high_pressure_teammate,
):
    raise SystemExit("NPC wolf should allow a strategic sell under high public pressure")
if main_module.choose_speech_focus_target(
    wolf_team_state,
    designated_bus_wolf,
).id != high_pressure_teammate.id:
    raise SystemExit("NPC wolf speech should focus the high-pressure teammate when selling")
wolf_bus_strategy = main_module.choose_wolf_team_vote_strategy(
    wolf_team_state,
    "exile",
)
if wolf_bus_strategy != "bus":
    raise SystemExit("high public teammate pressure should select the wolf bus strategy")
wolf_bus_strategy_before_ballot = wolf_bus_strategy
wolf_team_state.votes.append(
    VoteState(
        day=wolf_team_state.day,
        voter_id=designated_bus_wolf.id,
        target_id=high_pressure_teammate.id,
        reason="current round generation-order regression",
    )
)
if main_module.choose_wolf_team_vote_strategy(wolf_team_state, "exile") != wolf_bus_strategy_before_ballot:
    raise SystemExit("wolf strategy selection must ignore current-round ballot generation order")
wolf_team_state.votes.pop()

designated_bus_probabilities = main_module.build_npc_exile_vote_probabilities(
    wolf_team_state,
    designated_bus_wolf,
)
non_designated_probabilities = main_module.build_npc_exile_vote_probabilities(
    wolf_team_state,
    non_designated_wolf,
)
if abs(sum(designated_bus_probabilities.values()) - 1.0) > 1e-9:
    raise SystemExit("wolf exile-vote probabilities must normalize to one")
if list(designated_bus_probabilities) != sorted(designated_bus_probabilities):
    raise SystemExit("wolf exile-vote probabilities must use canonical candidate order")
if designated_bus_probabilities.get(high_pressure_teammate.id, 0.0) <= 0.0:
    raise SystemExit("a designated wolf bus target must retain positive vote probability")
if non_designated_probabilities.get(high_pressure_teammate.id, 0.0) <= 0.0:
    raise SystemExit("ordinary wolf teammates must remain legal with non-zero probability")
if (
    designated_bus_probabilities[high_pressure_teammate.id]
    <= non_designated_probabilities[high_pressure_teammate.id]
):
    raise SystemExit("the designated bus actor should weight the pressured teammate more heavily")
reversed_bus_probabilities = main_module.build_npc_exile_vote_probabilities(
    wolf_team_state,
    designated_bus_wolf,
    list(reversed(list(designated_bus_probabilities))),
)
if designated_bus_probabilities != reversed_bus_probabilities:
    raise SystemExit("exile-vote probabilities must be invariant to candidate input order")
first_replayed_bus_choice = main_module.choose_npc_vote_target(
    wolf_team_state,
    designated_bus_wolf,
)
second_replayed_bus_choice = main_module.choose_npc_vote_target(
    wolf_team_state,
    designated_bus_wolf,
)
if first_replayed_bus_choice != second_replayed_bus_choice:
    raise SystemExit("the same game id must replay the same sampled exile ballot")
if main_module.choose_speech_focus_target(
    wolf_team_state,
    non_designated_wolf,
).id == high_pressure_teammate.id:
    raise SystemExit("a non-designated wolf must not automatically join the public bus")

strong_evidence_probabilities = main_module.build_softmax_vote_probabilities(
    {high_pressure_teammate.id: 180.0, 5: 0.0},
    main_module.get_character_strategy_tuning(designated_bus_wolf),
)
if strong_evidence_probabilities[high_pressure_teammate.id] <= 0.99:
    raise SystemExit("overwhelming legal evidence should still allow vote convergence")
if strong_evidence_probabilities != main_module.build_softmax_vote_probabilities(
    {5: 0.0, high_pressure_teammate.id: 180.0},
    main_module.get_character_strategy_tuning(designated_bus_wolf),
):
    raise SystemExit("softmax vote construction must be independent of score insertion order")
bus_plan = PublicSpeechPlanV2.model_validate(
    {
        "schema_version": "public_speech_plan.v2",
        "intent": "pressure",
        "primary_target_id": high_pressure_teammate.id,
        "secondary_target_id": None,
        "stance": "oppose",
        "stance_target_id": high_pressure_teammate.id,
        "confidence": 75,
        "signal_read": "none",
        "question": {
            "target_id": high_pressure_teammate.id,
            "topic": "response_to_pressure",
        },
        "verification": {
            "target_id": high_pressure_teammate.id,
            "criterion": "vote_alignment",
        },
        "provisional_vote_target_id": high_pressure_teammate.id,
        "tactic": "wolf_bus_teammate",
        "claim_option_ids": [],
        "evidence_ids": [],
        "signal_ids": [],
    }
)
if main_module.validate_wolf_coordination_plan(
    wolf_team_state,
    designated_bus_wolf,
    bus_plan,
):
    raise SystemExit("the designated wolf's high-pressure bus plan should be legal")
if not main_module.validate_wolf_coordination_plan(
    wolf_team_state,
    non_designated_wolf,
    bus_plan,
):
    raise SystemExit("a non-designated wolf's LLM bus plan must be rejected")

wolf_strategy_baseline_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard", "villager", "villager", "villager",
    ]
)
original_wolf_strategy_seed = wolf_strategy_baseline_state.random_seed
observed_low_pressure_strategies = set()
for seed_index in range(1, 121):
    wolf_strategy_baseline_state.random_seed = seed_index
    observed_low_pressure_strategies.add(
        main_module.choose_wolf_team_vote_strategy(
            wolf_strategy_baseline_state,
            "exile",
        )
    )
wolf_strategy_baseline_state.random_seed = original_wolf_strategy_seed
if not {"consolidate", "split_cover"}.issubset(observed_low_pressure_strategies):
    raise SystemExit("low-pressure wolf teams must reach both consolidation and split-cover branches")

wolf_deep_hook_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard", "villager", "villager", "villager",
    ]
)
deep_hook_actor = wolf_deep_hook_state.characters[1]
deep_hook_teammate = wolf_deep_hook_state.characters[2]
wolf_deep_hook_state.speeches = [
    SpeechState(
        day=1,
        character_id=deep_hook_actor.id,
        name=deep_hook_actor.name,
        speech=f"我公开怀疑{deep_hook_teammate.id}号。",
        is_player=False,
        phase="DAY_MEETING",
        focus_target_id=deep_hook_teammate.id,
        decision_intent="pressure",
        public_position=PublicPositionV1(
            speaker_id=deep_hook_actor.id,
            day=1,
            phase="DAY_MEETING",
            suspected_target_ids=[deep_hook_teammate.id],
            provisional_vote_target_id=deep_hook_teammate.id,
            confidence=72,
        ),
    )
]
if main_module.choose_wolf_team_vote_strategy(wolf_deep_hook_state, "exile") != "deep_hook":
    raise SystemExit("a wolf's existing public teammate pressure should select deep-hook continuity")

wolf_rescue_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard", "villager", "villager", "villager",
    ]
)
rescue_teammate = wolf_rescue_state.characters[2]
wolf_rescue_state.speeches = [
    SpeechState(
        day=1,
        character_id=character.id,
        name=character.name,
        speech=f"我质疑{rescue_teammate.id}号。",
        is_player=character.is_player,
        phase="DAY_MEETING",
        focus_target_id=rescue_teammate.id,
        decision_intent="pressure",
    )
    for character in wolf_rescue_state.characters
    if character.id != rescue_teammate.id
][:4]
if main_module.choose_wolf_team_vote_strategy(wolf_rescue_state, "exile") != "rescue":
    raise SystemExit("moderate public teammate pressure should select the wolf rescue branch")

wolf_abandon_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard", "villager", "villager", "villager",
    ]
)
abandoned_fake_seer = wolf_abandon_state.characters[1]
competing_true_seer = wolf_abandon_state.characters[5]
wolf_abandon_state.wolf_fake_seer_id = abandoned_fake_seer.id
main_module.register_public_claims(
    wolf_abandon_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=abandoned_fake_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="wolf_abandon_fake",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=competing_true_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="wolf_abandon_true",
        ),
    ],
)
wolf_abandon_state.speeches = [
    SpeechState(
        day=1,
        character_id=character.id,
        name=character.name,
        speech=f"我不信{abandoned_fake_seer.id}号。",
        is_player=character.is_player,
        phase="DAY_MEETING",
        focus_target_id=abandoned_fake_seer.id,
        decision_intent="pressure",
    )
    for character in wolf_abandon_state.characters
    if character.id != abandoned_fake_seer.id
][:5]
if main_module.choose_wolf_team_vote_strategy(wolf_abandon_state, "exile") != "abandon_fake_seer":
    raise SystemExit("a collapsing contested fake seer should reach the abandon branch")

black_check_story_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "seer", "werewolf",
        "witch", "hunter", "guard", "villager", "villager",
        "villager", "villager",
    ]
)
black_check_story_state.phase = "DAY_MEETING"
black_check_story_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[3],
)
fake_seer_wolf = black_check_story_state.characters[1]
black_checked_wolf = black_check_story_state.characters[2]
true_seer_candidate = black_check_story_state.characters[3]
other_wolf = black_check_story_state.characters[4]
for actor in [fake_seer_wolf, black_checked_wolf, other_wolf]:
    actor.strategy_tuning = main_module.resolve_current_npc_tuning(
        actor.name,
        actor.camp,
        actor.role,
    ).model_dump(mode="json")
black_check_story_state.wolf_fake_seer_id = fake_seer_wolf.id
black_check_story_state.public_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=fake_seer_wolf.id,
        claim_type="role",
        claimed_role="seer",
        source="wolf_story_smoke",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=fake_seer_wolf.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=black_checked_wolf.id,
        result="werewolf",
        source="wolf_story_smoke",
    ),
]
if main_module.choose_npc_sheriff_vote_target(
    black_check_story_state,
    black_checked_wolf,
    [fake_seer_wolf.id, true_seer_candidate.id],
) != true_seer_candidate.id:
    raise SystemExit("a black-checked wolf must not elect the teammate who sacrificed them")
if main_module.choose_speech_focus_target(
    black_check_story_state,
    black_checked_wolf,
).id != fake_seer_wolf.id:
    raise SystemExit("the black-checked wolf's later speech must challenge the fake-seer teammate")
(
    story_target,
    _story_claims,
    _story_rag,
    story_generation,
    story_plan,
) = main_module.generate_structured_public_speech_plan(
    black_check_story_state,
    black_checked_wolf,
    False,
    fake_seer_wolf,
    [],
    [],
)
if (
    story_target is None
    or story_target.id != fake_seer_wolf.id
    or story_plan.primary_target_id != fake_seer_wolf.id
    or story_plan.provisional_vote_target_id != fake_seer_wolf.id
    or story_plan.stance.value != "oppose"
    or story_plan.tactic.value != "wolf_distance_teammate"
    or fake_seer_wolf.name not in story_generation.text
):
    raise SystemExit("the fallback strategy must keep the wolf sacrifice story coherent")
if main_module.choose_npc_vote_target(
    black_check_story_state,
    black_checked_wolf,
) != fake_seer_wolf.id:
    raise SystemExit("the black-checked wolf's exile vote must oppose the sacrificing teammate")
if main_module.choose_npc_vote_target(
    black_check_story_state,
    fake_seer_wolf,
) != black_checked_wolf.id:
    raise SystemExit("the fake seer must vote the wolf teammate it publicly black-checked")
story_vote_reason = main_module.build_npc_vote_reason(
    black_check_story_state,
    black_checked_wolf,
    fake_seer_wolf,
    None,
)
if "查杀" not in story_vote_reason or "反投" not in story_vote_reason:
    raise SystemExit("the coherent wolf vote should have a public-story reason")
fake_seer_wolf.alive = False
if main_module.choose_npc_badge_heir(
    black_check_story_state,
    fake_seer_wolf,
) == black_checked_wolf.id:
    raise SystemExit("the sacrificed wolf must not receive the fake seer's badge")
fake_seer_wolf.alive = True
black_checked_wolf.alive = False
if main_module.choose_npc_badge_heir(
    black_check_story_state,
    black_checked_wolf,
) == fake_seer_wolf.id:
    raise SystemExit("the black-checked wolf sheriff must not return the badge to its accuser")
black_checked_wolf.alive = True

public_pressure_state = make_rule_test_game(
    [
        "villager", "seer", "villager", "werewolf", "werewolf",
        "witch", "hunter", "guard", "villager", "villager",
        "werewolf", "villager",
    ]
)
private_seer = public_pressure_state.characters[1]
private_check_target = public_pressure_state.characters[2]
baseline_public_pressure = main_module.get_public_suspicion_score(
    public_pressure_state,
    private_check_target.id,
)
public_pressure_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=private_seer.id,
        action_type="seer_check",
        target_id=private_check_target.id,
    ),
]
private_seer.suspicion[str(private_check_target.id)] = 100
public_pressure_state.characters[4].suspicion[str(private_check_target.id)] = 80
if main_module.get_public_suspicion_score(
    public_pressure_state,
    private_check_target.id,
) != baseline_public_pressure:
    raise SystemExit("public pressure must not aggregate private suspicion or a seer's hidden check")
public_pressure_state.public_claims.append(
    main_module.PublicClaimState(
        day=1,
        character_id=private_seer.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=private_check_target.id,
        result="werewolf",
        source="public_pressure_smoke",
    )
)
claim_public_pressure = main_module.get_public_suspicion_score(
    public_pressure_state,
    private_check_target.id,
)
if claim_public_pressure <= baseline_public_pressure:
    raise SystemExit("a public black-check claim should change public pressure")
public_pressure_state.speeches.append(
    SpeechState(
        day=1,
        character_id=5,
        name=public_pressure_state.characters[4].name,
        speech=f"我重点质疑{private_check_target.id}号。",
        is_player=False,
        decision_intent="pressure",
        focus_target_id=private_check_target.id,
    )
)
speech_public_pressure = main_module.get_public_suspicion_score(
    public_pressure_state,
    private_check_target.id,
)
if speech_public_pressure <= claim_public_pressure:
    raise SystemExit("a public pressure speech should change public pressure")
public_pressure_state.sheriff_events.append(
    SheriffEventState(
        day=1,
        event_type="nomination",
        actor_id=4,
        target_id=private_check_target.id,
        detail="警长公开归票。",
    )
)
if main_module.get_public_suspicion_score(
    public_pressure_state,
    private_check_target.id,
) <= speech_public_pressure:
    raise SystemExit("a public sheriff action should change public pressure")

seer_gold_vote_state = make_rule_test_game(
    [
        "villager", "seer", "villager", "werewolf", "werewolf",
        "witch", "hunter", "guard", "villager", "villager",
        "werewolf", "villager",
    ]
)
true_seer_voter = seer_gold_vote_state.characters[1]
known_good_target = seer_gold_vote_state.characters[2]
alternative_wolf_target = seer_gold_vote_state.characters[3]
seer_gold_vote_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=true_seer_voter.id,
        action_type="seer_check",
        target_id=known_good_target.id,
    ),
]
true_seer_voter.suspicion[str(known_good_target.id)] = 200
true_seer_voter.suspicion[str(alternative_wolf_target.id)] = 50
seer_vote_probabilities = main_module.build_npc_exile_vote_probabilities(
    seer_gold_vote_state,
    true_seer_voter,
)
if known_good_target.id in seer_vote_probabilities:
    raise SystemExit("a true seer's privately checked good target must be excluded from legal ballots")
if max(seer_vote_probabilities, key=seer_vote_probabilities.get) != alternative_wolf_target.id:
    raise SystemExit("the true seer should rank another suspicious legal target above alternatives")

deception_vote_state = make_rule_test_game(
    [
        "villager", "werewolf", "villager", "seer", "werewolf",
        "witch", "hunter", "guard", "villager", "villager",
        "werewolf", "werewolf",
    ]
)
fake_claimant = deception_vote_state.characters[1]
framed_good = deception_vote_state.characters[2]
susceptible_good = deception_vote_state.characters[9]
for actor in [fake_claimant, susceptible_good]:
    actor.strategy_tuning = main_module.resolve_current_npc_tuning(
        actor.name,
        actor.camp,
        actor.role,
    ).model_dump(mode="json")
if framed_good.role != "villager" or susceptible_good.role != "villager":
    raise SystemExit("deception regression requires a good listener and a framed good target")
deception_probabilities_before_claim = main_module.build_npc_exile_vote_probabilities(
    deception_vote_state,
    susceptible_good,
)
main_module.register_public_claims(
    deception_vote_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=fake_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="deception_vote_smoke",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=fake_claimant.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=framed_good.id,
            result="werewolf",
            source="deception_vote_smoke",
        ),
    ],
)
deception_bonus = main_module.get_public_black_check_vote_bonus(
    deception_vote_state,
    susceptible_good,
    framed_good,
)
if deception_bonus <= 0:
    raise SystemExit("a persuasive wolf black check should influence a susceptible good listener")
deception_probabilities_after_claim = main_module.build_npc_exile_vote_probabilities(
    deception_vote_state,
    susceptible_good,
)
if (
    deception_probabilities_after_claim.get(framed_good.id, 0.0)
    <= deception_probabilities_before_claim.get(framed_good.id, 0.0)
):
    raise SystemExit("a persuasive public black check should raise a good listener's wrong-vote probability")
original_deception_seed = deception_vote_state.random_seed
deception_seed_choices = set()
for seed_index in range(1, 161):
    deception_vote_state.random_seed = seed_index
    deception_seed_choices.add(
        main_module.choose_npc_vote_target(
            deception_vote_state,
            susceptible_good,
        )
    )
deception_vote_state.random_seed = original_deception_seed
if framed_good.id not in deception_seed_choices:
    raise SystemExit("a good NPC must sometimes believe a wolf lie and cast a wrong vote")
deceived_reason = main_module.build_npc_vote_reason(
    deception_vote_state,
    susceptible_good,
    framed_good,
    None,
)
if "公开验人" not in deceived_reason or "暂时采信" not in deceived_reason:
    raise SystemExit("a deceived vote reason should cite only the public claim, not hidden truth")

sheriff_belief_state = make_rule_test_game(
    [
        "villager", "werewolf", "seer", "villager", "villager",
        "witch", "hunter", "guard", "villager", "villager",
        "werewolf", "werewolf",
    ]
)
fake_sheriff_claimant = sheriff_belief_state.characters[1]
true_sheriff_claimant = sheriff_belief_state.characters[2]
fake_sheriff_voter = sheriff_belief_state.characters[3]
true_sheriff_voter = sheriff_belief_state.characters[4]
main_module.register_public_claims(
    sheriff_belief_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=fake_sheriff_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="sheriff_belief_fake",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=fake_sheriff_claimant.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=6,
            result="good",
            source="sheriff_belief_fake",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=true_sheriff_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="sheriff_belief_true",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=true_sheriff_claimant.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=7,
            result="good",
            source="sheriff_belief_true",
        ),
    ],
)
fake_sheriff_voter.relationships[str(fake_sheriff_claimant.id)]["trust"] = 0.94
fake_sheriff_voter.relationships[str(true_sheriff_claimant.id)]["trust"] = 0.18
true_sheriff_voter.relationships[str(fake_sheriff_claimant.id)]["trust"] = 0.18
true_sheriff_voter.relationships[str(true_sheriff_claimant.id)]["trust"] = 0.94

sheriff_candidate_ids = [fake_sheriff_claimant.id, true_sheriff_claimant.id]
sheriff_choice_before_role_swap = main_module.choose_npc_sheriff_vote_target(
    sheriff_belief_state,
    fake_sheriff_voter,
    sheriff_candidate_ids,
)
sheriff_probabilities_before_role_swap = main_module.build_npc_sheriff_vote_probabilities(
    sheriff_belief_state,
    fake_sheriff_voter,
    sheriff_candidate_ids,
)
if abs(sum(sheriff_probabilities_before_role_swap.values()) - 1.0) > 1e-9:
    raise SystemExit("sheriff-vote probabilities must normalize to one")
if list(sheriff_probabilities_before_role_swap) != sorted(sheriff_candidate_ids):
    raise SystemExit("sheriff-vote probabilities must use canonical candidate order")
if sheriff_probabilities_before_role_swap != main_module.build_npc_sheriff_vote_probabilities(
    sheriff_belief_state,
    fake_sheriff_voter,
    list(reversed(sheriff_candidate_ids)),
):
    raise SystemExit("sheriff-vote probabilities must be invariant to candidate input order")
if sheriff_choice_before_role_swap != main_module.choose_npc_sheriff_vote_target(
    sheriff_belief_state,
    fake_sheriff_voter,
    sheriff_candidate_ids,
):
    raise SystemExit("the same game id must replay the same sampled sheriff ballot")
scores_before_role_swap = (
    main_module.score_npc_sheriff_candidate(
        sheriff_belief_state,
        fake_sheriff_voter,
        fake_sheriff_claimant,
    ),
    main_module.score_npc_sheriff_candidate(
        sheriff_belief_state,
        fake_sheriff_voter,
        true_sheriff_claimant,
    ),
)
fake_original_role, fake_original_camp = (
    fake_sheriff_claimant.role,
    fake_sheriff_claimant.camp,
)
true_original_role, true_original_camp = (
    true_sheriff_claimant.role,
    true_sheriff_claimant.camp,
)
fake_sheriff_claimant.role, fake_sheriff_claimant.camp = (
    true_original_role,
    true_original_camp,
)
true_sheriff_claimant.role, true_sheriff_claimant.camp = (
    fake_original_role,
    fake_original_camp,
)
scores_after_role_swap = (
    main_module.score_npc_sheriff_candidate(
        sheriff_belief_state,
        fake_sheriff_voter,
        fake_sheriff_claimant,
    ),
    main_module.score_npc_sheriff_candidate(
        sheriff_belief_state,
        fake_sheriff_voter,
        true_sheriff_claimant,
    ),
)
sheriff_probabilities_after_role_swap = main_module.build_npc_sheriff_vote_probabilities(
    sheriff_belief_state,
    fake_sheriff_voter,
    sheriff_candidate_ids,
)
sheriff_choice_after_role_swap = main_module.choose_npc_sheriff_vote_target(
    sheriff_belief_state,
    fake_sheriff_voter,
    sheriff_candidate_ids,
)
fake_sheriff_claimant.role, fake_sheriff_claimant.camp = (
    fake_original_role,
    fake_original_camp,
)
true_sheriff_claimant.role, true_sheriff_claimant.camp = (
    true_original_role,
    true_original_camp,
)
if scores_before_role_swap != scores_after_role_swap:
    raise SystemExit("good sheriff-vote scoring must be invariant to hidden claimant roles")
if sheriff_probabilities_before_role_swap != sheriff_probabilities_after_role_swap:
    raise SystemExit("good sheriff-vote probabilities must be invariant to hidden claimant roles")
if sheriff_choice_before_role_swap != sheriff_choice_after_role_swap:
    raise SystemExit("good sheriff-vote choice must be invariant to hidden claimant roles")

fake_listener_probabilities = main_module.build_npc_sheriff_vote_probabilities(
    sheriff_belief_state,
    fake_sheriff_voter,
    sheriff_candidate_ids,
)
true_listener_probabilities = main_module.build_npc_sheriff_vote_probabilities(
    sheriff_belief_state,
    true_sheriff_voter,
    sheriff_candidate_ids,
)
if fake_listener_probabilities[fake_sheriff_claimant.id] <= fake_listener_probabilities[true_sheriff_claimant.id]:
    raise SystemExit("a good NPC should be more likely to elect a trusted fake seer")
if true_listener_probabilities[true_sheriff_claimant.id] <= true_listener_probabilities[fake_sheriff_claimant.id]:
    raise SystemExit("different good NPC beliefs should favor different competing seers")

natural_sheriff_state = make_rule_test_game(
    [
        "werewolf", "villager", "seer", "villager", "witch", "werewolf",
        "hunter", "guard", "villager", "villager", "werewolf", "werewolf",
    ]
)
natural_fake_seer = natural_sheriff_state.characters[0]
natural_gold_recipient = natural_sheriff_state.characters[1]
natural_true_seer = natural_sheriff_state.characters[2]
natural_sheriff_state.speeches = [
    SpeechState(
        day=1,
        character_id=natural_fake_seer.id,
        name=natural_fake_seer.name,
        speech="我是预言家，昨晚验了2号梅西，是金水。警徽给我，我会用后续验人和票型负责。",
        is_player=True,
        phase="SHERIFF_SPEECH",
    ),
    SpeechState(
        day=1,
        character_id=natural_true_seer.id,
        name=natural_true_seer.name,
        speech="我才是预言家，昨晚验了6号塞尔达，是查杀。警徽给我，后续验人和票型会验证。",
        is_player=False,
        phase="SHERIFF_SPEECH",
    ),
]
main_module.register_public_claims(
    natural_sheriff_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=natural_fake_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="natural_fake",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=natural_fake_seer.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=natural_gold_recipient.id,
            result="good",
            source="natural_fake",
        ),
    ],
)
main_module.register_public_claims(
    natural_sheriff_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=natural_true_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="natural_true",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=natural_true_seer.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=6,
            result="werewolf",
            source="natural_true",
        ),
    ],
)
natural_candidate_ids = [natural_fake_seer.id, natural_true_seer.id]
natural_good_voters = [
    character
    for character in natural_sheriff_state.characters
    if character.camp == "good" and character.id not in natural_candidate_ids
]
original_natural_seed = natural_sheriff_state.random_seed
natural_good_choices = set()
for seed_index in range(1, 121):
    natural_sheriff_state.random_seed = seed_index
    for voter in natural_good_voters:
        probabilities = main_module.build_npc_sheriff_vote_probabilities(
            natural_sheriff_state,
            voter,
            natural_candidate_ids,
        )
        if abs(sum(probabilities.values()) - 1.0) > 1e-9:
            raise SystemExit("each good listener's sheriff-vote probabilities must normalize")
        natural_good_choices.add(
            main_module.choose_npc_sheriff_vote_target(
                natural_sheriff_state,
                voter,
                natural_candidate_ids,
            )
        )
natural_sheriff_state.random_seed = original_natural_seed
if not set(natural_candidate_ids).issubset(natural_good_choices):
    raise SystemExit("across reproducible game ids, both fake and true seers must receive good votes")
received_gold_adjustment = main_module.get_received_seer_check_sheriff_adjustment(
    natural_sheriff_state,
    natural_gold_recipient,
    natural_fake_seer,
)
if received_gold_adjustment <= 0:
    raise SystemExit("receiving a compatible public gold should create a positive soft personal read")
natural_gold_recipient.relationships[str(natural_fake_seer.id)]["trust"] = 0.05
natural_gold_recipient.relationships[str(natural_true_seer.id)]["trust"] = 0.95
natural_gold_recipient.suspicion[str(natural_fake_seer.id)] = 55
contrary_gold_probabilities = main_module.build_npc_sheriff_vote_probabilities(
    natural_sheriff_state,
    natural_gold_recipient,
    natural_candidate_ids,
)
if contrary_gold_probabilities[natural_true_seer.id] <= contrary_gold_probabilities[natural_fake_seer.id]:
    raise SystemExit("a received gold must remain a soft influence rather than locking the sheriff vote")
if contrary_gold_probabilities[natural_fake_seer.id] <= 0.0:
    raise SystemExit("a received gold should remain a possible soft sheriff-vote influence")

natural_gold_recipient.relationships[str(natural_fake_seer.id)]["trust"] = 0.5
natural_gold_recipient.relationships[str(natural_true_seer.id)]["trust"] = 0.5
natural_gold_recipient.suspicion[str(natural_fake_seer.id)] = 0
natural_scores_before_hidden_swap = (
    main_module.score_npc_sheriff_candidate(
        natural_sheriff_state,
        natural_gold_recipient,
        natural_fake_seer,
    ),
    main_module.score_npc_sheriff_candidate(
        natural_sheriff_state,
        natural_gold_recipient,
        natural_true_seer,
    ),
)
natural_probabilities_before_hidden_swap = main_module.build_npc_sheriff_vote_probabilities(
    natural_sheriff_state,
    natural_gold_recipient,
    natural_candidate_ids,
)
natural_fake_role = (natural_fake_seer.role, natural_fake_seer.camp)
natural_true_role = (natural_true_seer.role, natural_true_seer.camp)
natural_fake_seer.role, natural_fake_seer.camp = natural_true_role
natural_true_seer.role, natural_true_seer.camp = natural_fake_role
natural_scores_after_hidden_swap = (
    main_module.score_npc_sheriff_candidate(
        natural_sheriff_state,
        natural_gold_recipient,
        natural_fake_seer,
    ),
    main_module.score_npc_sheriff_candidate(
        natural_sheriff_state,
        natural_gold_recipient,
        natural_true_seer,
    ),
)
natural_probabilities_after_hidden_swap = main_module.build_npc_sheriff_vote_probabilities(
    natural_sheriff_state,
    natural_gold_recipient,
    natural_candidate_ids,
)
natural_fake_seer.role, natural_fake_seer.camp = natural_fake_role
natural_true_seer.role, natural_true_seer.camp = natural_true_role
if natural_scores_before_hidden_swap != natural_scores_after_hidden_swap:
    raise SystemExit("received-check sheriff scoring must not inspect claimant hidden roles")
if natural_probabilities_before_hidden_swap != natural_probabilities_after_hidden_swap:
    raise SystemExit("received-check sheriff probabilities must not inspect claimant hidden roles")

natural_sheriff_state.phase = "DAY_MEETING"
natural_sheriff_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[natural_gold_recipient.id],
)
natural_sheriff_state.sheriff_id = natural_true_seer.id
natural_sheriff_state.sheriff_election = SheriffElectionState(
    day=1,
    candidates=natural_candidate_ids,
    votes=[
        VoteState(
            day=1,
            voter_id=natural_gold_recipient.id,
            target_id=natural_true_seer.id,
            reason="NPC 警长票。",
        )
    ],
    completed=True,
)
received_signal_before_source_change = [
    signal.model_dump(mode="json")
    for signal in main_module.build_public_decision_signals(natural_sheriff_state)
    if signal.kind == "seer_check_claim"
    and signal.actor_id == natural_fake_seer.id
    and signal.target_id == natural_gold_recipient.id
]
if len(received_signal_before_source_change) != 1:
    raise SystemExit("a received gold should become one public decision signal")
if "source" in received_signal_before_source_change[0]:
    raise SystemExit("received-check signals must not expose internal claim source")
next(
    claim
    for claim in natural_sheriff_state.public_claims
    if claim.character_id == natural_fake_seer.id
    and claim.claim_type == "seer_check"
).source = "hidden_truth_changed"
received_signal_after_source_change = [
    signal.model_dump(mode="json")
    for signal in main_module.build_public_decision_signals(natural_sheriff_state)
    if signal.kind == "seer_check_claim"
    and signal.actor_id == natural_fake_seer.id
    and signal.target_id == natural_gold_recipient.id
]
if received_signal_before_source_change != received_signal_after_source_change:
    raise SystemExit("received-check signal projection must ignore hidden claim source")

received_gold_context = main_module.build_public_speech_decision_context(
    natural_sheriff_state,
    natural_gold_recipient,
    [],
    [],
)
required_received_signals = main_module.get_required_received_seer_check_signals(
    received_gold_context
)
if [signal.id for signal in required_received_signals] != [
    received_signal_before_source_change[0]["id"]
]:
    raise SystemExit("the actor-scoped context should mark its received gold as required")
unanswered_plan = main_module.build_public_speech_fallback_decision(
    received_gold_context,
    natural_true_seer,
    "",
)
if not main_module.validate_received_seer_check_response_plan(
    received_gold_context,
    unanswered_plan,
):
    raise SystemExit("a structured plan must not silently ignore a received check")
answered_plan = main_module.enforce_received_seer_check_response_plan(
    natural_sheriff_state,
    natural_gold_recipient,
    received_gold_context,
    unanswered_plan,
)
answered_plan_errors = main_module.validate_public_speech_plan(
    received_gold_context,
    answered_plan,
)
answered_plan_errors.extend(
    main_module.validate_received_seer_check_response_plan(
        received_gold_context,
        answered_plan,
    )
)
if answered_plan_errors:
    raise SystemExit(
        "the rule response to a received gold should be a legal plan: "
        + "; ".join(answered_plan_errors)
    )

received_gold_speech = generate_npc_speech(
    NpcSpeechRequest(
        game_id=natural_sheriff_state.game_id,
        character_id=natural_gold_recipient.id,
    )
).speech.speech
received_gold_plan = natural_sheriff_state.speeches[-1].decision_plan
if (
    "给我发了金水" not in received_gold_speech
    or "我的警长票投给了" not in received_gold_speech
):
    raise SystemExit("a gold recipient must mention the claim and explain an opposite sheriff vote")
if not any(
    signal_id.startswith("signal:seer_check_claim:1:1:2:good")
    for signal_id in received_gold_plan.get("signal_ids", [])
):
    raise SystemExit("the accepted day plan must retain the received-gold signal")

received_black_state = make_rule_test_game(
    [
        "werewolf", "villager", "seer", "villager", "witch", "werewolf",
        "hunter", "guard", "villager", "villager", "werewolf", "werewolf",
    ]
)
received_black_source = received_black_state.characters[0]
received_black_target = received_black_state.characters[1]
main_module.register_public_claims(
    received_black_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=received_black_source.id,
            claim_type="role",
            claimed_role="seer",
            source="fake_black",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=received_black_source.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=received_black_target.id,
            result="werewolf",
            source="fake_black",
        ),
    ],
)
received_black_state.phase = "DAY_MEETING"
received_black_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[received_black_target.id],
)
received_black_speech = generate_npc_speech(
    NpcSpeechRequest(
        game_id=received_black_state.game_id,
        character_id=received_black_target.id,
    )
).speech.speech
received_black_plan = received_black_state.speeches[-1].decision_plan
if "给我发了查杀" not in received_black_speech:
    raise SystemExit("a black-check recipient must address the public check")
if (
    received_black_plan.get("primary_target_id") != received_black_source.id
    or received_black_plan.get("stance") != "oppose"
):
    raise SystemExit("a black-check recipient must publicly challenge its source")

fake_checks_true_state = make_rule_test_game(
    [
        "villager", "werewolf", "seer", "villager", "villager",
        "witch", "hunter", "guard", "villager", "villager",
        "werewolf", "werewolf",
    ]
)
meeting_fake_seer = fake_checks_true_state.characters[1]
meeting_true_seer = fake_checks_true_state.characters[2]
deceived_meeting_voter = fake_checks_true_state.characters[9]
deceived_meeting_voter.relationships[str(meeting_fake_seer.id)]["trust"] = 0.94
deceived_meeting_voter.relationships[str(meeting_true_seer.id)]["trust"] = 0.12
main_module.register_public_claims(
    fake_checks_true_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=meeting_fake_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="fake_checks_true",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=meeting_fake_seer.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=meeting_true_seer.id,
            result="werewolf",
            source="fake_checks_true",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=meeting_true_seer.id,
            claim_type="role",
            claimed_role="seer",
            source="true_seer_counterclaim",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=meeting_true_seer.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=5,
            result="good",
            source="true_seer_counterclaim",
        ),
    ],
)
meeting_choice_before_role_swap = main_module.choose_npc_vote_target(
    fake_checks_true_state,
    deceived_meeting_voter,
)
meeting_probabilities_before_role_swap = main_module.build_npc_exile_vote_probabilities(
    fake_checks_true_state,
    deceived_meeting_voter,
)
if abs(sum(meeting_probabilities_before_role_swap.values()) - 1.0) > 1e-9:
    raise SystemExit("good exile-vote probabilities must normalize to one")
if meeting_choice_before_role_swap != main_module.choose_npc_vote_target(
    fake_checks_true_state,
    deceived_meeting_voter,
):
    raise SystemExit("the same game id must replay the same sampled good exile ballot")
meeting_scores_before_role_swap = (
    main_module.score_npc_vote_candidate(
        fake_checks_true_state,
        deceived_meeting_voter,
        meeting_fake_seer,
    ),
    main_module.score_npc_vote_candidate(
        fake_checks_true_state,
        deceived_meeting_voter,
        meeting_true_seer,
    ),
)
meeting_fake_original_role, meeting_fake_original_camp = (
    meeting_fake_seer.role,
    meeting_fake_seer.camp,
)
meeting_true_original_role, meeting_true_original_camp = (
    meeting_true_seer.role,
    meeting_true_seer.camp,
)
meeting_fake_seer.role, meeting_fake_seer.camp = (
    meeting_true_original_role,
    meeting_true_original_camp,
)
meeting_true_seer.role, meeting_true_seer.camp = (
    meeting_fake_original_role,
    meeting_fake_original_camp,
)
meeting_scores_after_role_swap = (
    main_module.score_npc_vote_candidate(
        fake_checks_true_state,
        deceived_meeting_voter,
        meeting_fake_seer,
    ),
    main_module.score_npc_vote_candidate(
        fake_checks_true_state,
        deceived_meeting_voter,
        meeting_true_seer,
    ),
)
meeting_probabilities_after_role_swap = main_module.build_npc_exile_vote_probabilities(
    fake_checks_true_state,
    deceived_meeting_voter,
)
meeting_choice_after_role_swap = main_module.choose_npc_vote_target(
    fake_checks_true_state,
    deceived_meeting_voter,
)
meeting_fake_seer.role, meeting_fake_seer.camp = (
    meeting_fake_original_role,
    meeting_fake_original_camp,
)
meeting_true_seer.role, meeting_true_seer.camp = (
    meeting_true_original_role,
    meeting_true_original_camp,
)
if meeting_scores_before_role_swap != meeting_scores_after_role_swap:
    raise SystemExit("good exile-vote scoring must be invariant to hidden candidate roles")
if meeting_probabilities_before_role_swap != meeting_probabilities_after_role_swap:
    raise SystemExit("good exile-vote probabilities must be invariant to hidden candidate roles")
if meeting_choice_before_role_swap != meeting_choice_after_role_swap:
    raise SystemExit("good exile-vote choice must be invariant to hidden candidate roles")

black_check_bonus_before_role_change = main_module.get_public_black_check_vote_bonus(
    fake_checks_true_state,
    deceived_meeting_voter,
    meeting_true_seer,
)
meeting_fake_original_role, meeting_fake_original_camp = (
    meeting_fake_seer.role,
    meeting_fake_seer.camp,
)
meeting_fake_seer.role, meeting_fake_seer.camp = "villager", "good"
black_check_bonus_after_role_change = main_module.get_public_black_check_vote_bonus(
    fake_checks_true_state,
    deceived_meeting_voter,
    meeting_true_seer,
)
meeting_fake_seer.role, meeting_fake_seer.camp = (
    meeting_fake_original_role,
    meeting_fake_original_camp,
)
if black_check_bonus_before_role_change != black_check_bonus_after_role_change:
    raise SystemExit("public black-check persuasion must not inspect the claimant's hidden role")
deceived_meeting_probabilities = main_module.build_npc_exile_vote_probabilities(
    fake_checks_true_state,
    deceived_meeting_voter,
)
if (
    deceived_meeting_probabilities[meeting_true_seer.id]
    <= deceived_meeting_probabilities[meeting_fake_seer.id]
):
    raise SystemExit("a trusted fake seer's public black check should raise pressure on the true seer")
if deceived_meeting_probabilities[meeting_fake_seer.id] <= 0.0:
    raise SystemExit("competing public seers must remain probabilistic rather than hidden-role locked")
original_fake_checks_seed = fake_checks_true_state.random_seed
deceived_seed_choices = set()
for seed_index in range(1, 161):
    fake_checks_true_state.random_seed = seed_index
    deceived_seed_choices.add(
        main_module.choose_npc_vote_target(
            fake_checks_true_state,
            deceived_meeting_voter,
        )
    )
fake_checks_true_state.random_seed = original_fake_checks_seed
if meeting_true_seer.id not in deceived_seed_choices:
    raise SystemExit("a good NPC must sometimes believe a fake seer and vote out the true seer")
deceived_true_seer_reason = main_module.build_npc_vote_reason(
    fake_checks_true_state,
    deceived_meeting_voter,
    meeting_true_seer,
    None,
)
if "公开验人" not in deceived_true_seer_reason or "暂时采信" not in deceived_true_seer_reason:
    raise SystemExit("a wrong vote on the true seer must cite only public information")

plan_vote_state = make_rule_test_game(
    [
        "villager", "villager", "villager", "werewolf", "seer",
        "witch", "hunter", "guard", "villager", "villager",
        "werewolf", "werewolf",
    ]
)
plan_voter = plan_vote_state.characters[1]
planned_vote_target = plan_vote_state.characters[2]
new_evidence_target = plan_vote_state.characters[3]
plan_voter.strategy_tuning = main_module.resolve_current_npc_tuning(
    plan_voter.name,
    plan_voter.camp,
    plan_voter.role,
).model_dump(mode="json")
plan_vote_state.speeches = [
    SpeechState(
        day=1,
        character_id=plan_voter.id,
        name=plan_voter.name,
        speech=f"我暂定投{planned_vote_target.id}号。",
        is_player=False,
        phase="DAY_MEETING",
        focus_target_id=planned_vote_target.id,
        public_position=PublicPositionV1(
            speaker_id=plan_voter.id,
            day=1,
            phase="DAY_MEETING",
            suspected_target_ids=[planned_vote_target.id],
            provisional_vote_target_id=planned_vote_target.id,
            confidence=92,
        ),
    ),
]
planned_vote_probabilities = main_module.build_npc_exile_vote_probabilities(
    plan_vote_state,
    plan_voter,
)
if max(planned_vote_probabilities, key=planned_vote_probabilities.get) != planned_vote_target.id:
    raise SystemExit("a same-day public position should be the strongest later-vote influence")
planned_reason = main_module.build_npc_vote_reason(
    plan_vote_state,
    plan_voter,
    planned_vote_target,
    None,
)
if "发言时暂定" not in planned_reason or "不足以推翻" not in planned_reason:
    raise SystemExit("a position-consistent vote should explain its decision continuity")
plan_voter.suspicion[str(new_evidence_target.id)] = 100
new_evidence_probabilities = main_module.build_npc_exile_vote_probabilities(
    plan_vote_state,
    plan_voter,
)
if max(new_evidence_probabilities, key=new_evidence_probabilities.get) != new_evidence_target.id:
    raise SystemExit("strong new legal evidence must outweigh a provisional public position")

selected_plan_state = make_rule_test_game(
    [
        "villager", "werewolf", "werewolf", "villager",
        "werewolf", "werewolf", "seer",
    ]
)
selected_plan_speaker = selected_plan_state.characters[1]
low_pressure_teammate = selected_plan_state.characters[2]
selected_plan_target = selected_plan_state.characters[3]
if (
    main_module.get_public_suspicion_score(
        selected_plan_state,
        low_pressure_teammate.id,
    ) != 0
    or low_pressure_teammate.id in {
        target.id
        for target in main_module.get_legal_public_speech_targets(
            selected_plan_state,
            selected_plan_speaker,
        )
    }
):
    raise SystemExit("selected-plan regression requires a hidden low-pressure wolf teammate")
selected_plan_rule_text = "我会追问4号周深的矛盾。"
secondary_character_reference = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我会追问4号周深的矛盾，3号C罗也必须解释。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    selected_plan_rule_text,
    selected_plan_state,
    speaker=selected_plan_speaker,
    required_target=selected_plan_target,
    public_text=True,
    required_intent="pressure",
)
if not secondary_character_reference.used_llm:
    raise SystemExit(
        "public rewrite should allow public seat references while preserving the selected target"
    )

low_information_signal = main_module.DecisionSignalV1(
    id="signal:low_information:1:DAY_MEETING:4",
    kind="low_information_speech",
    category="assessment",
    day=1,
    phase="DAY_MEETING",
    actor_id=selected_plan_target.id,
    summary="第1天，4号周深的发言没有给出具体目标或立场。",
)
empty_pass_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="4号周深，我没什么信息，先过吧。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "4号周深上一轮发言信息量偏低，我会继续核对他的站边和票型。",
    selected_plan_state,
    speaker=selected_plan_speaker,
    required_target=selected_plan_target,
    public_text=True,
    required_intent="observe",
    required_signals=[low_information_signal],
)
if (
    empty_pass_rewrite.used_llm
    or "empty pass" not in empty_pass_rewrite.fallback_reason
):
    raise SystemExit("a short no-information pass should fail public-expression validation")

grounded_signal_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="4号周深刚才只复述别人，没有形成自己的判断；请明确站边，我会结合你后续票型判断。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "4号周深上一轮发言信息量偏低，我会继续核对他的站边和票型。",
    selected_plan_state,
    speaker=selected_plan_speaker,
    required_target=selected_plan_target,
    public_text=True,
    required_intent="observe",
    required_signals=[low_information_signal],
)
if not grounded_signal_rewrite.used_llm:
    raise SystemExit("a natural synonym grounded in the selected public signal should pass")

action_actor = selected_plan_state.characters[3]
action_target = selected_plan_state.characters[6]
action_actor_name = main_module.format_full_character_name(action_actor)
action_target_name = main_module.format_full_character_name(action_target)

def validate_action_signal_text(signal, text, required_target):
    return main_module.validate_llm_rewrite(
        LLMGeneration(
            text=text,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        signal.summary + "我会继续核对相关解释和后续票型。",
        selected_plan_state,
        speaker=selected_plan_speaker,
        required_target=required_target,
        public_text=True,
        required_intent="observe",
        required_signals=[signal],
    )

sheriff_vote_signal = main_module.DecisionSignalV1(
    id="signal:sheriff_vote:1:4:7",
    kind="sheriff_vote",
    category="fact",
    day=1,
    phase="SHERIFF_VOTE",
    actor_id=action_actor.id,
    target_id=action_target.id,
    summary=f"第1天警长投票中，{action_actor_name}投给{action_target_name}。",
)
correct_vote_rewrite = validate_action_signal_text(
    sheriff_vote_signal,
    f"{action_actor_name}支持{action_target_name}竞选警长，我会继续看这组警长票关系。",
    action_target,
)
if not correct_vote_rewrite.used_llm:
    raise SystemExit("a natural actor-to-target sheriff vote should pass")
generic_process_support = validate_action_signal_text(
    sheriff_vote_signal,
    f"{action_actor_name}支持警长投票这套流程，{action_target_name}需要解释自己的发言。",
    action_target,
)
if generic_process_support.used_llm:
    raise SystemExit("supporting the voting process must not be mistaken for voting for the next speaker")
passive_vote_rewrite = validate_action_signal_text(
    sheriff_vote_signal,
    f"{action_target_name}收到{action_actor_name}投来的警长票，我会继续看这组关系。",
    action_target,
)
if not passive_vote_rewrite.used_llm:
    raise SystemExit("an unambiguous passive sheriff-vote sentence should pass")
for reversed_vote_text in [
    f"{action_target_name}把警长票投给{action_actor_name}，我会继续观察。",
    f"{action_actor_name}收到{action_target_name}投给他的警长票，我会继续观察。",
]:
    reversed_vote_rewrite = validate_action_signal_text(
        sheriff_vote_signal,
        reversed_vote_text,
        action_target,
    )
    if reversed_vote_rewrite.used_llm:
        raise SystemExit("a reversed sheriff-vote actor and target must be rejected")

badge_transfer_signal = main_module.DecisionSignalV1(
    id="signal:badge_transfer:1:4:7",
    kind="badge_transfer",
    category="fact",
    day=1,
    phase="BADGE_TRANSFER",
    actor_id=action_actor.id,
    target_id=action_target.id,
    summary=f"第1天，{action_actor_name}将警徽移交给{action_target_name}。",
)
natural_badge_rewrite = validate_action_signal_text(
    badge_transfer_signal,
    f"{action_actor_name}把徽章递给{action_target_name}，这次选择值得继续验证。",
    action_target,
)
if not natural_badge_rewrite.used_llm:
    raise SystemExit("a natural badge-transfer synonym should pass")
reversed_badge_rewrite = validate_action_signal_text(
    badge_transfer_signal,
    f"{action_target_name}把警徽交给{action_actor_name}，这次选择值得继续验证。",
    action_target,
)
if reversed_badge_rewrite.used_llm:
    raise SystemExit("a reversed badge transfer must be rejected")

night_elimination_action_signal = main_module.DecisionSignalV1(
    id="signal:public_elimination:1:4",
    kind="public_elimination",
    category="fact",
    day=1,
    phase="NIGHT_RESULT",
    actor_id=action_actor.id,
    summary=f"第1天，{action_actor_name}在夜间结果公布时出局。",
)
correct_night_elimination = validate_action_signal_text(
    night_elimination_action_signal,
    f"{action_actor_name}昨夜出局，这个公开结果会影响我今天的判断。",
    action_actor,
)
if not correct_night_elimination.used_llm:
    raise SystemExit("a public night-elimination synonym should pass")
generic_elimination_rewrite = validate_action_signal_text(
    night_elimination_action_signal,
    f"{action_actor_name}已经倒牌，这个公开结果会影响我今天的判断。",
    action_actor,
)
if not generic_elimination_rewrite.used_llm:
    raise SystemExit("an expression may omit a public elimination source without changing it")
wrong_elimination_source = validate_action_signal_text(
    night_elimination_action_signal,
    f"{action_actor_name}白天被放逐出局，这个结果会影响我今天的判断。",
    action_actor,
)
if wrong_elimination_source.used_llm:
    raise SystemExit("a night result must not be rewritten as a daytime exile")

elected_action_signal = main_module.DecisionSignalV1(
    id="signal:sheriff_elected:1:4",
    kind="sheriff_elected",
    category="fact",
    day=1,
    phase="SHERIFF_RESULT",
    actor_id=action_actor.id,
    summary=f"第1天，{action_actor_name}当选警长。",
)
sheriff_candidate_only = validate_action_signal_text(
    elected_action_signal,
    f"{action_actor_name}是警长候选人，{action_target_name}需要解释自己的票型。",
    action_actor,
)
if sheriff_candidate_only.used_llm:
    raise SystemExit("being a sheriff candidate must not be mistaken for winning the badge")
unselected_action_rewrite = validate_action_signal_text(
    elected_action_signal,
    f"{action_actor_name}戴上了警徽，但2号梅西随后退水，我会继续观察。",
    action_actor,
)
if (
    unselected_action_rewrite.used_llm
    or "public action absent from authoritative public state"
    not in unselected_action_rewrite.fallback_reason
):
    raise SystemExit("an expression must not invent an unsupported public action")

authoritative_action_state = selected_plan_state.model_copy(deep=True)
authoritative_withdrawer = authoritative_action_state.characters[4]
authoritative_action_actor = authoritative_action_state.characters[3]
authoritative_action_target = authoritative_action_state.characters[6]
authoritative_action_state.sheriff_election = SheriffElectionState(
    day=1,
    candidates=[authoritative_action_actor.id, authoritative_withdrawer.id],
    withdrawn=[authoritative_withdrawer.id],
    completed=True,
)
authoritative_action_state.sheriff_events = [
    SheriffEventState(
        day=1,
        event_type="elected",
        actor_id=authoritative_action_actor.id,
        detail="规则状态确认其当选警长。",
    )
]
authoritative_action_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            f"{main_module.format_full_character_name(authoritative_action_actor)}戴上了警徽，"
            f"{main_module.format_full_character_name(authoritative_withdrawer)}此前退水，"
            "我会把这两项公开动作放在一起看。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    elected_action_signal.summary + "我会继续核对公开动作。",
    authoritative_action_state,
    speaker=authoritative_action_state.characters[1],
    required_target=authoritative_action_actor,
    public_text=True,
    required_intent="observe",
    required_signals=[elected_action_signal],
)
if not authoritative_action_rewrite.used_llm:
    raise SystemExit(
        "selected signals should be a required lower bound, not exclude other authoritative actions: "
        + authoritative_action_rewrite.fallback_reason
    )

withdraw_action_signal = main_module.DecisionSignalV1(
    id="signal:sheriff_withdraw:1:4",
    kind="sheriff_withdraw",
    category="fact",
    day=1,
    phase="SHERIFF_WITHDRAWAL",
    actor_id=action_actor.id,
    summary=f"第1天，{action_actor_name}在警长竞选中退水。",
)
speculative_motive_rewrite = validate_action_signal_text(
    withdraw_action_signal,
    f"{action_actor_name}已经退水，我认为{action_actor_name}可能是狼，先放进压力位继续验证。",
    action_actor,
)
if not speculative_motive_rewrite.used_llm:
    raise SystemExit("an NPC may make a possibly wrong inference from an accurate public action")
concrete_pass_wording = validate_action_signal_text(
    withdraw_action_signal,
    f"信息不多，但{action_actor_name}退水没有解释，我怀疑他在避嫌，这个点先过吧。",
    action_actor,
)
if not concrete_pass_wording.used_llm:
    raise SystemExit("the word pass should not reject a speech that has an action, target, and judgment")

quoted_action_text = (
    f"{action_actor_name}自称预言家，验了{action_target_name}是金水，并上警竞选。"
)
quoted_action_facts = main_module.extract_public_action_assertions(
    quoted_action_text,
    selected_plan_state,
)
if ("sheriff_signup", action_target.id, 0) in quoted_action_facts:
    raise SystemExit("an action after a quoted check must not be assigned to the checked target")

seer_role_claim = main_module.PublicClaimState(
    day=1,
    character_id=selected_plan_speaker.id,
    claim_type="role",
    claimed_role="seer",
    source="validation_false_positive_smoke",
)
seer_good_claim = main_module.PublicClaimState(
    day=1,
    character_id=selected_plan_speaker.id,
    claim_type="seer_check",
    claimed_role="seer",
    target_id=action_target.id,
    result="good",
    source="validation_false_positive_smoke",
)
claim_with_short_ending = (
    f"我是预言家，昨晚验了{action_target_name}，金水。先看行动，话够了，看票。"
)
claim_with_short_ending_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=claim_with_short_ending,
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    claim_with_short_ending,
    selected_plan_state,
    speaker=selected_plan_speaker,
    required_target=action_target,
    required_claims=[seer_role_claim, seer_good_claim],
    public_text=True,
)
if not claim_with_short_ending_rewrite.used_llm:
    raise SystemExit("a complete role and check claim must not be rejected for a concise ending")

seer_wolf_claim = seer_good_claim.model_copy(update={"result": "werewolf"})
shorthand_check_text = f"我起跳预言家，{action_target_name}，查杀。"
shorthand_check_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=shorthand_check_text,
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    shorthand_check_text,
    selected_plan_state,
    speaker=selected_plan_speaker,
    required_target=action_target,
    required_claims=[seer_role_claim, seer_wolf_claim],
    public_text=True,
)
if not shorthand_check_rewrite.used_llm:
    raise SystemExit("the natural seer shorthand target-comma-check result should pass")

villager_role_text = "你既认出了我，我便直说：此局我拿的是村民牌。"
villager_role_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=villager_role_text,
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    villager_role_text,
    selected_plan_state,
    speaker=action_actor,
    required_self_role="villager",
)
if not villager_role_rewrite.used_llm:
    raise SystemExit("the natural self-role phrase '我拿的是村民牌' should pass")

quoted_claimant = selected_plan_state.characters[4]
quoted_target = selected_plan_state.characters[1]
quoted_check_text = (
    f"{main_module.format_full_character_name(quoted_claimant)}起跳预言家，"
    f"给{main_module.format_full_character_name(quoted_target)}发金水；"
    f"但我的查验是{action_target_name}为好人。"
)
quoted_checks = main_module.extract_seer_check_assertions(
    quoted_check_text,
    selected_plan_state,
    selected_plan_state.characters[11],
)
if any(
    claimant_id == selected_plan_state.characters[11].id
    and target_id == quoted_target.id
    for claimant_id, target_id, _result in quoted_checks
):
    raise SystemExit("an omitted subject in a quoted gold claim must not default to the current speaker")

explicit_quote_text = (
    f"{main_module.format_full_character_name(quoted_claimant)}给"
    f"{main_module.format_full_character_name(action_target)}金水。"
)
explicit_quote_checks = main_module.extract_seer_check_assertions(
    explicit_quote_text,
    selected_plan_state,
    selected_plan_speaker,
)
if (quoted_claimant.id, action_target.id, "good") not in explicit_quote_checks:
    raise SystemExit("an explicitly attributed public gold claim should retain its real claimant")

unsafe_role_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(text="我是女巫，今晚有完整信息。", used_llm=True, provider="stub", model="stub"),
    "我会继续观察。",
    wolf_team_state,
)
if unsafe_role_rewrite.used_llm or "role claim" not in unsafe_role_rewrite.fallback_reason:
    raise SystemExit("LLM validator should reject unsupported witch or hunter role claims")
unsafe_team_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(text="C罗是我的队友。", used_llm=True, provider="stub", model="stub"),
    "我会继续观察C罗。",
    wolf_team_state,
)
if not unsafe_team_rewrite.used_llm:
    raise SystemExit("generic teammate wording should not be treated as a wolf-team disclosure")

semantic_validation_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "villager", "seer", "witch", "hunter"]
)
semantic_speaker = semantic_validation_state.characters[4]
semantic_target = semantic_validation_state.characters[2]
semantic_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=semantic_speaker.id,
        claim_type="role",
        claimed_role="seer",
        source="sheriff_true_seer",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=semantic_speaker.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=semantic_target.id,
        result="good",
        source="sheriff_night_1",
    ),
]
semantic_rule_text = main_module.build_public_claim_speech(
    semantic_validation_state,
    semantic_speaker,
    semantic_claims,
)
real_deepseek_good_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "那我就不绕了，我是预言家，"
            "昨晚验了3号C罗，他是好人。我会竞选警长，后续用发言和票型来印证这个信息。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    semantic_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=semantic_target,
    required_claims=semantic_claims,
    public_text=True,
)
if not real_deepseek_good_rewrite.used_llm:
    raise SystemExit(
        "semantic validator should accept natural '我是预言家/验了/好人' wording: "
        + real_deepseek_good_rewrite.fallback_reason
    )

fake_speaker = semantic_validation_state.characters[2]
fake_target = semantic_validation_state.characters[3]
fake_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=fake_speaker.id,
        claim_type="role",
        claimed_role="seer",
        source="sheriff_wolf_fake_seer",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=fake_speaker.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=fake_target.id,
        result="werewolf",
        source="sheriff_wolf_fake_seer",
    ),
]
fake_rule_text = main_module.build_public_claim_speech(
    semantic_validation_state,
    fake_speaker,
    fake_claims,
)
real_deepseek_wolf_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "冷静，Calma。场上有人起跳，但我也把话讲清楚。我是预言家，"
            "验了4号周深是狼人。我竞选警长，会用后续发言和票型证明这套信息。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    fake_rule_text,
    semantic_validation_state,
    speaker=fake_speaker,
    required_target=fake_target,
    required_claims=fake_claims,
    public_text=True,
)
if not real_deepseek_wolf_rewrite.used_llm:
    raise SystemExit(
        "semantic validator should accept a rule-approved fake-seer wolf check: "
        + real_deepseek_wolf_rewrite.fallback_reason
    )

attributed_speaker = semantic_validation_state.characters[9]
attributed_target = semantic_validation_state.characters[3]
referenced_claimant = semantic_validation_state.characters[4]
referenced_target = semantic_validation_state.characters[7]
main_module.register_public_claims(
    semantic_validation_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=referenced_claimant.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=referenced_target.id,
            result="good",
            source="public_reference",
        )
    ],
)
attributed_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=attributed_speaker.id,
        claim_type="role",
        claimed_role="seer",
        source="sheriff_true_seer",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=attributed_speaker.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=attributed_target.id,
        result="good",
        source="sheriff_night_1",
    ),
]
attributed_rule_text = main_module.build_public_claim_speech(
    semantic_validation_state,
    attributed_speaker,
    attributed_claims,
)
attributed_rule_text = (
    "5号起跳给8号金水，3号也接了话。" + attributed_rule_text
)
real_attribution_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "先别催，我都听着呢。5号起跳给8号金水，3号也接了话。"
            "那我也把话说清楚：我验了4号周深，是好人。我上警竞选警长。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    attributed_rule_text,
    semantic_validation_state,
    speaker=attributed_speaker,
    required_target=attributed_target,
    required_claims=attributed_claims,
    public_text=True,
)
if not real_attribution_rewrite.used_llm:
    raise SystemExit(
        "semantic validator should distinguish cited claimant 5 from checked target 8 "
        "and treat '我验了' as a seer claim: "
        + real_attribution_rewrite.fallback_reason
    )

changed_check_result = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我是预言家，昨晚验了3号C罗，他是狼人。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    semantic_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=semantic_target,
    required_claims=semantic_claims,
    public_text=True,
)
if changed_check_result.used_llm or "changed an approved seer-check result" not in changed_check_result.fallback_reason:
    raise SystemExit("semantic validator should reject a changed seer-check result")

invented_check = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "我是预言家，昨晚验了3号C罗，他是好人。除此之外，"
            "我还验了4号周深，他是狼人。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    semantic_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=semantic_target,
    required_claims=semantic_claims,
    public_text=True,
)
if invented_check.used_llm or "unapproved seer check" not in invented_check.fallback_reason:
    raise SystemExit("semantic validator should reject an invented second seer check")

unsupported_power_identity = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我会观察4号周深，但4号周深就是女巫。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "我会继续观察4号周深。",
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if unsupported_power_identity.used_llm or "unsupported character identity" not in unsupported_power_identity.fallback_reason:
    raise SystemExit("semantic validator should reject an unapproved categorical power-role identity")

camp_rule_text = "我会继续观察4号周深。"
for allowed_public_camp_text in [
    "我会观察4号周深，但4号周深就是狼牌。",
    "我会观察4号周深，但4号周深确定属于好人阵营。",
    "我是好人，但4号周深必须解释站边，我会继续观察。",
    "我们是好人阵营，4号周深仍需要解释。",
]:
    allowed_public_camp_assertion = main_module.validate_llm_rewrite(
        LLMGeneration(
            text=allowed_public_camp_text,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        camp_rule_text,
        semantic_validation_state,
        speaker=semantic_speaker,
        required_target=fake_target,
        public_text=True,
    )
    if not allowed_public_camp_assertion.used_llm:
        raise SystemExit(
            "public camp reads and first-person good claims should remain fallible opinions: "
            + allowed_public_camp_assertion.fallback_reason
        )

for unsupported_self_wolf_text in [
    "我是狼，但我会继续观察4号周深。",
    "我是狼人，但我会继续观察4号周深。",
    "我是一张狼牌，但我会继续观察4号周深。",
    "我属于狼人阵营，但我会继续观察4号周深。",
]:
    unsupported_camp_assertion = main_module.validate_llm_rewrite(
        LLMGeneration(
            text=unsupported_self_wolf_text,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        camp_rule_text,
        semantic_validation_state,
        speaker=semantic_speaker,
        required_target=fake_target,
        public_text=True,
    )
    if (
        unsupported_camp_assertion.used_llm
        or unsupported_camp_assertion.text != camp_rule_text
        or "unsupported camp assertion" not in unsupported_camp_assertion.fallback_reason
    ):
        raise SystemExit("validator should reject an unauthorized first-person wolf disclosure")

for non_assertive_camp_text in [
    "4号周深，你凭什么认定我是狼？先回答我的问题。",
    "4号周深，你凭什么认定我是狼人？先回答我的问题。",
    "4号周深刚才说我是狼，我不同意这个结论。",
    "我不是狼，4号周深的判断没有依据。",
    "如果我是狼，4号周深的逻辑也不能因此成立。",
    "我如果是狼，4号周深的逻辑也不能因此成立。",
]:
    non_assertive_camp_rewrite = main_module.validate_llm_rewrite(
        LLMGeneration(
            text=non_assertive_camp_text,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        "我会追问4号周深的说法。",
        semantic_validation_state,
        speaker=semantic_speaker,
        required_target=fake_target,
        public_text=True,
        required_intent="pressure",
    )
    if not non_assertive_camp_rewrite.used_llm:
        raise SystemExit(
            "validator should allow challenged, quoted, negated, or hypothetical camp wording: "
            + non_assertive_camp_rewrite.fallback_reason
        )

parallel_attribution_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="4号周深刚才说5号刘亦菲是狼，7号贝多芬也是狼；我会追问4号这套判断的依据。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "我会追问4号周深的说法。",
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
    required_intent="pressure",
)
if not parallel_attribution_rewrite.used_llm:
    raise SystemExit(
        "a parallel quoted camp claim must not become the current speaker's assertion: "
        + parallel_attribution_rewrite.fallback_reason
    )

public_claim_rewrite_state = semantic_validation_state.model_copy(deep=True)
public_claimant = public_claim_rewrite_state.characters[3]
public_check_target = public_claim_rewrite_state.characters[6]
public_claim_rewrite_state.public_claims.extend(
    [
        main_module.PublicClaimState(
            day=1,
            character_id=public_claimant.id,
            claim_type="role",
            claimed_role="seer",
            source="public_claim_rewrite_smoke",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=public_claimant.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=public_check_target.id,
            result="werewolf",
            source="public_claim_rewrite_smoke",
        ),
    ]
)
registered_public_claim_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            f"{main_module.format_full_character_name(public_claimant)}自称预言家，"
            f"验了{main_module.format_full_character_name(public_check_target)}是狼人；"
            f"我会继续核对{main_module.format_full_character_name(public_claimant)}的逻辑。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    f"我会继续核对{main_module.format_full_character_name(public_claimant)}的公开声明。",
    public_claim_rewrite_state,
    speaker=public_claim_rewrite_state.characters[1],
    required_target=public_claimant,
    public_text=True,
    required_intent="observe",
)
if not registered_public_claim_rewrite.used_llm:
    raise SystemExit(
        "an already registered public role and check may be accurately restated: "
        + registered_public_claim_rewrite.fallback_reason
    )

wolf_team_variant = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我们狼队今天先观察4号周深。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    camp_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if wolf_team_variant.used_llm or "hidden wolf-team information" not in wolf_team_variant.fallback_reason:
    raise SystemExit("semantic validator should reject first-person wolf-team variants")

direct_wolf_teammate = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="3号C罗是我的狼队友，我会继续观察4号周深。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    camp_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if (
    direct_wolf_teammate.used_llm
    or "hidden wolf-team information" not in direct_wolf_teammate.fallback_reason
):
    raise SystemExit("a direct first-person wolf-teammate disclosure must still fail")

for public_team_read in [
    "如果9号喜羊羊是狼，3号C罗可能是狼队友；4号周深需要解释站边。",
    "我觉得3号C罗和9号喜羊羊像双狼，4号周深也要继续解释。",
    "4号周深刚才说3号C罗是狼队友，我会核对这句话。",
    "3号C罗不是我的狼队友，4号周深需要解释票型。",
    "凭什么说3号C罗是狼队友？4号周深先把依据讲清楚。",
    "3号C罗是我的队友，但4号周深的逻辑仍要单独核对。",
]:
    public_team_rewrite = main_module.validate_llm_rewrite(
        LLMGeneration(
            text=public_team_read,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        camp_rule_text,
        semantic_validation_state,
        speaker=semantic_speaker,
        required_target=fake_target,
        public_text=True,
    )
    if not public_team_rewrite.used_llm:
        raise SystemExit(
            "conditional, speculative, quoted, negated, questioned, or generic team wording should pass: "
            + public_team_rewrite.fallback_reason
        )

known_wolf_name = next(
    character.name
    for character in semantic_validation_state.characters
    if character.role == "werewolf"
)
known_good_name = next(
    character.name
    for character in semantic_validation_state.characters
    if character.role != "werewolf" and not character.is_player
)
wolf_name_sensitive = main_module.is_sensitive_llm_failure(
    "LLM text omitted the rule-selected target",
    known_wolf_name,
    semantic_validation_state,
    camp_rule_text,
)
good_name_sensitive = main_module.is_sensitive_llm_failure(
    "LLM text omitted the rule-selected target",
    known_good_name,
    semantic_validation_state,
    camp_rule_text,
)
if wolf_name_sensitive != good_name_sensitive:
    raise SystemExit("validation redaction must not reveal whether a mentioned seat is truly a wolf")
for role_independent_reason, expected_sensitive in [
    ("LLM text introduced hidden wolf-team information", True),
    ("LLM text omitted the rule-selected target", False),
]:
    if any(
        main_module.is_sensitive_llm_failure(
            role_independent_reason,
            raw_name,
            semantic_validation_state,
            camp_rule_text,
        )
        != expected_sensitive
        for raw_name in [known_wolf_name, known_good_name]
    ):
        raise SystemExit("validation redaction should depend on rejection type, not hidden role")

speculative_camp_read = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我会观察4号周深，我觉得4号周深可能是狼人。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    camp_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if not speculative_camp_read.used_llm:
    raise SystemExit("semantic validator should allow a clearly speculative camp read")

speculative_power_read = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我会观察4号周深，我觉得4号周深可能是女巫。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "我会继续观察4号周深。",
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if not speculative_power_read.used_llm:
    raise SystemExit("semantic validator should allow a clearly speculative role read")

wolf_team_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=9),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=10),
    NightActionState(day=1, actor_id=4, action_type="werewolf_kill", target_id=10),
]
submit_night_action(
    NightActionRequest(
        game_id=wolf_team_state.game_id,
        character_id=1,
        action_type="werewolf_kill",
        target_id=11,
    )
)
if main_module.get_current_wolf_target(wolf_team_state) != 11:
    raise SystemExit("player werewolf target should override the NPC wolf majority")

witch_state = make_rule_test_game(
    [
        "witch", "guard", "werewolf", "werewolf", "villager", "hunter",
        "seer", "villager", "villager", "villager", "villager", "villager",
    ]
)
witch_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="witch_save", target_id=5),
    NightActionState(day=1, actor_id=2, action_type="guard_protect", target_id=5),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=5),
    NightActionState(day=1, actor_id=4, action_type="werewolf_kill", target_id=5),
]
witch_result = resolve_night(NightResolveRequest(game_id=witch_state.game_id))
if 5 not in witch_result.dead_characters or witch_state.characters[4].alive:
    raise SystemExit("guard and antidote on the same wolf target should still eliminate it")
if main_module.get_role_resources(witch_state, 1).get("antidote_available", True):
    raise SystemExit("witch antidote should be consumed after use")

hunter_state = make_rule_test_game(
    [
        "hunter", "werewolf", "werewolf", "seer", "guard", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
hunter_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=character.id,
        action_type="werewolf_kill" if character.role == "werewolf" else "none",
        target_id=1 if character.role == "werewolf" else None,
    )
    for character in hunter_state.characters
    if not character.is_player
]
hunter_night_result = resolve_night(NightResolveRequest(game_id=hunter_state.game_id))
if hunter_state.phase != "HUNTER_SHOT" or 1 not in hunter_night_result.dead_characters:
    raise SystemExit("eliminated player hunter should pause the game for a shot")
if not get_wolf_game_state(hunter_state.game_id).player_private_info.hunter_can_shoot:
    raise SystemExit("player hunter private state should enable the shot control")
hunter_shot_result = resolve_hunter_shot(
    HunterShotRequest(game_id=hunter_state.game_id, character_id=1, target_id=2)
)
if not hunter_shot_result.success or hunter_state.characters[1].alive:
    raise SystemExit("player hunter shot should eliminate the selected target")
if hunter_state.phase != "DAY_MEETING":
    raise SystemExit("hunter shot should resume the interrupted night flow")

poisoned_hunter_state = make_rule_test_game(
    [
        "hunter", "werewolf", "witch", "seer", "guard", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
poisoned_hunter_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=6),
    NightActionState(day=1, actor_id=3, action_type="witch_poison", target_id=1),
    NightActionState(day=1, actor_id=4, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=poisoned_hunter_state.game_id))
if poisoned_hunter_state.phase == "HUNTER_SHOT" or poisoned_hunter_state.hunter_shots:
    raise SystemExit("poisoned hunter must not receive a shot")

player_freedom_state = make_rule_test_game(
    ["seer", "werewolf", "werewolf", "werewolf", "werewolf", "villager"]
)
player_freedom_state.badge_destroyed = False
player_freedom_state.sheriff_election = None
main_module.start_sheriff_signup(player_freedom_state)
freedom_signup = submit_sheriff_signup(
    SheriffSignupRequest(
        game_id=player_freedom_state.game_id,
        character_id=1,
        run_for_sheriff=False,
    )
)
if 1 in freedom_signup.candidates:
    raise SystemExit("player seer must be free to stay off the sheriff election")

npc_only_withdrawal_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
npc_only_withdrawal_state.badge_destroyed = False
npc_only_withdrawal_state.sheriff_election = SheriffElectionState(
    candidates=[2, 3],
    speech_order=[2, 3],
    current_index=1,
)
npc_only_withdrawal_state.phase = "SHERIFF_SPEECH"
main_module.advance_sheriff_speech(npc_only_withdrawal_state)
if npc_only_withdrawal_state.phase == "SHERIFF_WITHDRAWAL":
    raise SystemExit("a player who stayed off sheriff should not have to complete NPC withdrawals")

wolf_coordination_state = make_rule_test_game(
    ["werewolf", "seer", "werewolf", "werewolf", "werewolf", "villager"]
)
wolf_coordination_state.badge_destroyed = False
wolf_coordination_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="seer_check", target_id=3),
]
wolf_coordination_state.wolf_fake_seer_id = main_module.choose_designated_fake_seer(
    wolf_coordination_state.characters,
    wolf_coordination_state.random_seed,
)
if wolf_coordination_state.wolf_fake_seer_id is None:
    wolf_coordination_state.wolf_fake_seer_id = select_test_fake_seer(
        wolf_coordination_state.characters
    )
fake_seer_id = wolf_coordination_state.wolf_fake_seer_id
wolf_coordination_state.sheriff_election = SheriffElectionState(
    candidates=[1, fake_seer_id, 2],
    speech_order=[1, fake_seer_id, 2],
)
wolf_coordination_state.phase = "SHERIFF_SPEECH"
submit_player_sheriff_speech(
    SheriffSpeechRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=1,
        speech="我是预言家，昨晚查验4号是好人，我来带队。",
    )
)
fake_campaign = generate_npc_sheriff_campaign_speech(
    SheriffSpeechRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=fake_seer_id,
    )
)
if "起跳预言家" in fake_campaign.speech.speech:
    raise SystemExit("NPC wolf should be able to yield when a wolf player already makes a strong seer claim")
generate_npc_sheriff_campaign_speech(
    SheriffSpeechRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=2,
    )
)
true_seer_claims = [
    claim
    for claim in wolf_coordination_state.public_claims
    if claim.character_id == 2
]
if not any(claim.claim_type == "role" and claim.claimed_role == "seer" for claim in true_seer_claims):
    raise SystemExit("NPC true seer must claim seer during the sheriff election")
if not any(claim.claim_type == "seer_check" and claim.target_id == 3 and claim.result == "werewolf" for claim in true_seer_claims):
    raise SystemExit("NPC true seer must reveal the real first-night check")
submit_sheriff_withdrawal(
    SheriffWithdrawalRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=1,
        withdraw=False,
    )
)
if fake_seer_id not in wolf_coordination_state.sheriff_election.withdrawn:
    raise SystemExit("NPC fake seer should support the explicit withdrawal flow after yielding")

runoff_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
runoff_state.badge_destroyed = False
runoff_state.sheriff_election = SheriffElectionState(candidates=[2, 3])
runoff_state.phase = "SHERIFF_VOTE"
original_sheriff_vote_chooser = main_module.choose_npc_sheriff_vote_target
try:
    def force_first_round_tie(_game_state, voter, _candidate_ids):
        return 2 if voter.id <= 7 else 3

    main_module.choose_npc_sheriff_vote_target = force_first_round_tie
    first_sheriff_vote = submit_and_resolve_sheriff_vote(
        SheriffVoteRequest(
            game_id=runoff_state.game_id,
            character_id=1,
            target_id=2,
        )
    )
    if runoff_state.phase != "SHERIFF_RUNOFF_SPEECH" or sorted(first_sheriff_vote.tied_candidate_ids) != [2, 3]:
        raise SystemExit("a tied first sheriff vote should enter one PK speech round")
    while runoff_state.phase == "SHERIFF_RUNOFF_SPEECH":
        speaker_id = main_module.get_current_sheriff_speaker_id(runoff_state)
        generate_npc_sheriff_campaign_speech(
            SheriffSpeechRequest(game_id=runoff_state.game_id, character_id=speaker_id)
        )

    def force_runoff_winner(_game_state, _voter, _candidate_ids):
        return 2

    main_module.choose_npc_sheriff_vote_target = force_runoff_winner
    runoff_result = submit_and_resolve_sheriff_vote(
        SheriffVoteRequest(
            game_id=runoff_state.game_id,
            character_id=1,
            target_id=2,
        )
    )
    if runoff_result.winner_id != 2 or runoff_state.sheriff_id != 2:
        raise SystemExit("the single runoff should elect the second-round winner")
finally:
    main_module.choose_npc_sheriff_vote_target = original_sheriff_vote_chooser

meeting_anchor_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "witch", "villager"]
)
meeting_anchor_state.badge_destroyed = False
meeting_anchor_state.sheriff_id = 1
meeting_anchor_state.eliminations = [
    EliminationState(
        day=1,
        character_id=4,
        cause="night_kill",
        source_action="werewolf_kill",
        source_actor_ids=[3],
        source_target_id=4,
    ),
    EliminationState(
        day=1,
        character_id=6,
        cause="witch_poison",
        source_action="witch_poison",
        source_actor_ids=[5],
        source_target_id=6,
    ),
]
meeting_anchor_state.characters[3].alive = False
meeting_anchor_state.characters[5].alive = False
main_module.prepare_sheriff_meeting_order(meeting_anchor_state)
if meeting_anchor_state.phase != "MEETING_ORDER" or meeting_anchor_state.meeting_order_anchor_id not in {4, 6}:
    raise SystemExit("multiple night eliminations should pick one public meeting anchor")
submit_sheriff_meeting_order(
    SheriffMeetingOrderRequest(
        game_id=meeting_anchor_state.game_id,
        character_id=1,
        side="right",
    )
)
if meeting_anchor_state.meeting.order[-1] == 1 or meeting_anchor_state.meeting.order_source != "out_right":
    raise SystemExit("sheriff should keep the natural seat position after choosing an eliminated-player side")
if meeting_anchor_state.meeting.order.count(1) != 1:
    raise SystemExit("natural meeting order should contain the sheriff exactly once")

temporary_nomination_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
temporary_nomination_state.badge_destroyed = False
temporary_nomination_state.sheriff_id = 1
temporary_nomination_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(1, 13)),
    sheriff_id=1,
)
temporary_nomination_state.phase = "DAY_MEETING"
temporary_speech = submit_player_speech(
    PlayerSpeechRequest(
        game_id=temporary_nomination_state.game_id,
        character_id=1,
        speech="我先听后面的发言。",
        temporary_nomination_target_id=3,
    )
)
if temporary_nomination_state.meeting.temporary_nomination_target_id != 3:
    raise SystemExit("player sheriff speech should record a temporary nomination")
if "暂时归票" not in temporary_speech.public_log:
    raise SystemExit("temporary sheriff nomination should be included in the public speech")
if main_module.choose_speech_focus_target(
    temporary_nomination_state,
    temporary_nomination_state.characters[1],
).id != 3:
    raise SystemExit("later NPC speech should react to the sheriff's temporary nomination")
temporary_nomination_state.meeting.current_index = len(temporary_nomination_state.meeting.order)
temporary_nomination_state.meeting.completed = True
temporary_nomination_state.phase = "SHERIFF_NOMINATION"
submit_sheriff_nomination(
    SheriffNominationRequest(
        game_id=temporary_nomination_state.game_id,
        character_id=1,
        target_id=4,
    )
)
if temporary_nomination_state.meeting.nomination_target_id != 4:
    raise SystemExit("player sheriff should be able to change the final nomination after all speeches")
if temporary_nomination_state.phase != "FREE_ACTIVITY":
    raise SystemExit("final sheriff nomination should continue to free activity")

locked_vote_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
locked_vote_state.badge_destroyed = False
locked_vote_state.sheriff_id = 1
locked_vote_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(2, 13)) + [1],
    sheriff_id=1,
    nomination_target_id=3,
    completed=True,
)
locked_vote_state.phase = "VOTE"
try:
    submit_and_resolve_all_votes(
        PlayerVoteRequest(
            game_id=locked_vote_state.game_id,
            character_id=1,
            target_id=4,
            reason="尝试偏离归票。",
        )
    )
    raise SystemExit("sheriff should not be allowed to vote away from the nomination")
except HTTPException as exc:
    if exc.status_code != 400:
        raise

edge_win_state = make_rule_test_game(
    [
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
        "villager", "villager", "villager", "villager",
    ]
)
for character in edge_win_state.characters:
    if character.role == "villager":
        character.alive = False
if main_module.check_winner(edge_win_state) != "werewolf":
    raise SystemExit("wolves should win when the villager side is fully eliminated")
for character in edge_win_state.characters:
    character.alive = character.role != "werewolf"
if main_module.check_winner(edge_win_state) != "good":
    raise SystemExit("good camp should win when all wolves are eliminated")
for character in edge_win_state.characters:
    character.alive = character.role not in main_module.GOD_ROLES
if main_module.check_winner(edge_win_state) != "werewolf":
    raise SystemExit("wolves should win when the god side is fully eliminated")

control_win_state = make_rule_test_game(
    [
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
        "villager", "villager", "villager", "villager",
    ]
)
for character in control_win_state.characters:
    character.alive = character.id in {1, 2, 5, 9}
control_winner, control_reason = main_module.get_winner_result(control_win_state)
if control_winner != "werewolf" or control_reason != "wolf_control":
    raise SystemExit("wolves should win after reaching equal numbers with the good camp")
if "控场" not in main_module.build_winner_message(control_winner, control_reason):
    raise SystemExit("wolf-control winner message should explain the trigger")

hunter_priority_state = make_rule_test_game(
    [
        "hunter", "werewolf", "werewolf", "seer", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
for character in hunter_priority_state.characters:
    character.alive = character.id <= 5
hunter_priority_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=4, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=hunter_priority_state.game_id))
if hunter_priority_state.phase != "HUNTER_SHOT":
    raise SystemExit("hunter shot must take priority over an immediate wolf-control win")
resolve_hunter_shot(
    HunterShotRequest(
        game_id=hunter_priority_state.game_id,
        character_id=1,
        target_id=2,
    )
)
if hunter_priority_state.phase != "DAY_MEETING" or hunter_priority_state.winner is not None:
    raise SystemExit("hunter should be able to break wolf control before winner evaluation")

badge_hunter_state = make_rule_test_game(
    [
        "hunter", "werewolf", "werewolf", "seer", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
for character in badge_hunter_state.characters:
    character.alive = character.id <= 5
badge_hunter_state.badge_destroyed = False
badge_hunter_state.sheriff_id = 1
badge_hunter_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=4, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=badge_hunter_state.game_id))
if badge_hunter_state.phase != "HUNTER_SHOT":
    raise SystemExit("sheriff hunter should resolve the shot before badge transfer")
resolve_hunter_shot(
    HunterShotRequest(
        game_id=badge_hunter_state.game_id,
        character_id=1,
        target_id=2,
    )
)
if badge_hunter_state.phase != "BADGE_TRANSFER":
    raise SystemExit("player sheriff should transfer the badge after finishing the hunter shot")
submit_badge_transfer(
    BadgeTransferRequest(
        game_id=badge_hunter_state.game_id,
        character_id=1,
        target_id=4,
    )
)
if badge_hunter_state.sheriff_id != 4 or badge_hunter_state.phase != "DAY_MEETING":
    raise SystemExit("badge heir should immediately control the next meeting order")

summary_state = make_rule_test_game(
    ["seer", "guard", "werewolf", "werewolf", "villager", "villager"]
)
try:
    get_game_summary(summary_state.game_id)
    raise SystemExit("game summary should be hidden before GAME_OVER")
except HTTPException as exc:
    if exc.status_code != 400:
        raise

summary_state.day = 2
summary_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=2, action_type="guard_protect", target_id=5),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=5),
]
summary_state.night_resolutions = [
    NightResolutionState(day=1, attacked_target_id=5, protected_ids=[5], dead_character_ids=[]),
]
summary_state.speeches = [
    SpeechState(day=1, character_id=1, name="规则测试", speech="我查到了线索。", is_player=True),
]
summary_state.public_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=1,
        claim_type="role",
        claimed_role="seer",
        source="player_speech",
    ),
]
summary_state.private_conversations = [
    PrivateConversationState(
        day=1,
        npc_character_id=2,
        question="你相信谁？",
        reply="我会继续观察。",
        effective=True,
    ),
]
summary_state.votes = [
    VoteState(day=1, voter_id=1, target_id=3, reason="查验结果指向狼人。"),
]
summary_state.eliminations = [
    EliminationState(
        day=1,
        character_id=3,
        cause="exiled",
        source_action="day_vote",
        source_actor_ids=[1],
        source_target_id=3,
    ),
]
summary_state.characters[2].alive = False
summary_state.phase = "GAME_OVER"
summary_state.winner = "good"
summary = get_game_summary(summary_state.game_id)
if len(summary.characters) != 12 or summary.winner != "good":
    raise SystemExit("game summary should reveal all twelve roles and the winner")
timeline_text = "\\n".join(event.text for event in summary.timeline)
for expected_text in ["查验", "成功挡下狼刀", "公开声明", "私下询问", "投给"]:
    if expected_text not in timeline_text:
        raise SystemExit(f"game summary is missing action detail: {expected_text}")
if not any(event.is_private for event in summary.timeline):
    raise SystemExit("game summary should mark hidden actions and private chats")

validation_observability_summary = summarize_observation_events(
    captured_validation_observations
)
if (
    validation_observability_summary["validation_recovered_count"] < 1
    or validation_observability_summary["validation_fallback_count"] < 1
):
    raise SystemExit(
        "real semantic validation paths should emit recovered and fallback observations"
    )
serialized_validation_observations = json.dumps(
    captured_validation_observations,
    ensure_ascii=False,
)
for forbidden_observation_detail in [
    "PRIVATE_STRATEGY_TOKEN",
    "NIGHT_RAW_TOKEN",
    "CHAT_RAW_TOKEN",
    "claim:forged",
    "target_not_allowed: 999",
]:
    if forbidden_observation_detail in serialized_validation_observations:
        raise SystemExit("redacted semantic observations leaked raw validation data")

print("wolf game start smoke test passed")
"""
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="wolf game start smoke test failed",
    )
    print("[OK] Wolf game meeting, private chat, role, memory, social, and vote APIs work.")


def check_godot_loads() -> None:
    godot_bin = shutil.which("godot") or shutil.which("godot4")
    if godot_bin is None:
        raise SmokeCheckError("Godot CLI not found. On macOS, install it with: brew install --cask godot")

    run_command(
        [godot_bin, "--headless", "--editor", "--path", str(GAME_DIR), "--quit"],
        cwd=ROOT_DIR,
        fail_message="Godot failed to import project resources",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load script"),
    )
    run_command(
        [godot_bin, "--headless", "--path", str(GAME_DIR), "--script", "res://scripts/font_check.gd"],
        cwd=ROOT_DIR,
        fail_message="Godot dialog font glyph check failed",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load", "missing characters"),
    )
    run_command(
        [godot_bin, "--headless", "--path", str(GAME_DIR), "--script", "res://scripts/day_night_check.gd"],
        cwd=ROOT_DIR,
        fail_message="Godot day/night phase mapping check failed",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load"),
    )
    run_command(
        [godot_bin, "--headless", "--path", str(GAME_DIR), MAIN_SCENE, "--quit"],
        cwd=ROOT_DIR,
        fail_message="Godot failed to load the main scene",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load script"),
    )
    print("[OK] Godot font, NIGHT-only visual mapping, and main scene loading checks pass.")


def check_godot_ui_layout() -> None:
    try:
        scene_text = MAIN_SCENE_FILE.read_text(encoding="utf-8")
        script_text = MAIN_SCRIPT_FILE.read_text(encoding="utf-8")
        town_background_scene_text = TOWN_BACKGROUND_SCENE_FILE.read_text(encoding="utf-8")
        town_background_script_text = TOWN_BACKGROUND_SCRIPT_FILE.read_text(encoding="utf-8")
        project_text = PROJECT_FILE.read_text(encoding="utf-8")
        dialog_scene_text = DIALOG_SCENE_FILE.read_text(encoding="utf-8")
        dialog_script_text = DIALOG_SCRIPT_FILE.read_text(encoding="utf-8")
        npc_scene_text = NPC_SCENE_FILE.read_text(encoding="utf-8")
        npc_script_text = NPC_SCRIPT_FILE.read_text(encoding="utf-8")
        player_scene_text = PLAYER_SCENE_FILE.read_text(encoding="utf-8")
        player_script_text = PLAYER_SCRIPT_FILE.read_text(encoding="utf-8")
        huaihuai_asset_text = (CHARACTER_ASSET_DIR / "huaihuai.svg").read_text(
            encoding="utf-8"
        )
        ranran_asset_text = (CHARACTER_ASSET_DIR / "ranran.svg").read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise SmokeCheckError(f"could not read Godot UI files: {exc}") from exc

    required_scene_fragments = [
        '[ext_resource type="PackedScene" path="res://scenes/TownBackground.tscn" id="6_town_background"]',
        '[node name="TownBackground" parent="." instance=ExtResource("6_town_background")]',
        '[node name="PhaseHUD" type="Control" parent="UI"]',
        '[node name="IdentityPanel" type="PanelContainer" parent="UI"]',
        '[node name="PlayerIdentityBlock" type="VBoxContainer" parent="UI/IdentityPanel/Margin"]',
        '[node name="KeyInfoToggleButton" type="Button" parent="UI/IdentityPanel/Margin/PlayerIdentityBlock"]',
        '[node name="KeyInfoContentPanel" type="PanelContainer" parent="UI/IdentityPanel/Margin/PlayerIdentityBlock"]',
        '[node name="KeyInfoLabel" type="Label" parent="UI/IdentityPanel/Margin/PlayerIdentityBlock/KeyInfoContentPanel/Margin/VBox/ScrollContainer"]',
        'text = "◇ 公开说法（真假未确认） · ● 已确认公开动作"',
        '[node name="WolfPanel" type="Control" parent="UI"]',
        'text = "当前行动"',
        '[node name="IntelPanel" type="Control" parent="UI"]',
        '[node name="Tabs" type="TabContainer" parent="UI/IntelPanel/Panel/Margin/VBox"]',
        '[node name="CharacterGrid" type="GridContainer" parent="UI/IntelPanel/Panel/Margin/VBox/Tabs/Roster/Margin"]',
        '[node name="PublicLogLabel" type="Label" parent="UI/IntelPanel/Panel/Margin/VBox/Tabs/PublicRecords/Margin"]',
        '[node name="PlayerActionHistoryBlock" type="VBoxContainer" parent="UI/IntelPanel/Panel/Margin/VBox/Tabs/MyRecords"]',
        '[node name="GameSetupOverlay" type="Control" parent="UI"]',
        '[node name="PlayerNameInput" type="LineEdit" parent="UI/GameSetupOverlay/Panel/Margin/VBox/PlayerNameRow"]',
        '[node name="LLMEnabledToggle" type="CheckButton" parent="UI/GameSetupOverlay/Panel/Margin/VBox/LLMSettingsRow"]',
        '[node name="PlayerRoleOption" type="OptionButton" parent="UI/GameSetupOverlay/Panel/Margin/VBox/PlayerRoleRow"]',
        '[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_phase_hud"]',
        '[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_wolf_panel"]',
        '[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_intel"]',
        '[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_light_control"]',
        '[sub_resource type="Theme" id="Theme_light_ui"]',
        'Button/colors/font_color = Color(0, 0, 0, 1)',
        'CheckButton/colors/font_color = Color(0, 0, 0, 1)',
        'Label/colors/font_color = Color(0, 0, 0, 1)',
        'LineEdit/colors/font_color = Color(0, 0, 0, 1)',
        'OptionButton/colors/font_color = Color(0, 0, 0, 1)',
        'TabBar/colors/font_selected_color = Color(0, 0, 0, 1)',
        'TabBar/colors/font_unselected_color = Color(0, 0, 0, 1)',
        'TextEdit/colors/font_readonly_color = Color(0, 0, 0, 1)',
        'offset_left = -270.0',
        '[node name="ScrollContainer" type="ScrollContainer"',
        'horizontal_scroll_mode = 0',
        'offset_left = -456.0',
        'default_font_size = 13',
        'columns = 3',
        'text = "RanRanHuaiHuaiKill"',
        '[node name="GameSummaryOverlay" type="Control"',
        '[node name="ReviewGameButton" type="Button"',
        '[node name="GameSummaryRequest" type="HTTPRequest"',
        '[node name="LittleKnight" parent="." instance=ExtResource("3_npc_scene")]',
        '[node name="DoctorStrange" parent="." instance=ExtResource("3_npc_scene")]',
        '[node name="HuaiHuai" parent="." instance=ExtResource("3_npc_scene")]',
        '[node name="RanRan" parent="." instance=ExtResource("3_npc_scene")]',
        'position = Vector2(-170, 0)',
        'position = Vector2(870, 0)',
        '[node name="NightActionOption" type="OptionButton"',
        '[node name="HunterActionRow" type="HBoxContainer"',
        '[node name="HunterShotRequest" type="HTTPRequest"',
        '[node name="SheriffActionLabel" type="Label"',
        '[node name="SheriffOption" type="OptionButton"',
        '[node name="SheriffWithdrawalRow" type="HBoxContainer"',
        '[node name="ContinueButton" type="Button"',
        'text = "继续竞选"',
        '[node name="WithdrawButton" type="Button"',
        'text = "退水"',
        '[node name="SheriffSpeechInput" type="LineEdit"',
        '[node name="VoteReasonInput" type="LineEdit"',
        '[node name="VoteResultLabel" type="Label"',
        '[node name="CombinedVoteRequest" type="HTTPRequest"',
        '[ext_resource type="FontFile" path="res://assets/fonts/NotoSansSC-Variable.ttf" id="5_main_font"]',
        'theme = SubResource("Theme_main_cjk")',
        '[node name="HistoryText" type="TextEdit"',
        'custom_minimum_size = Vector2(0, 420)',
        'theme_override_font_sizes/font_size = 13',
        'text = "仅你可见的行动记录"',
        '[node name="TemporaryNominationOption" type="OptionButton"',
        '[node name="SheriffOverviewLabel" type="Label"',
        'position = Vector2(350, -285)',
        'position = Vector2(657, 41)',
        'position = Vector2(182, -240)',
    ]
    for fragment in required_scene_fragments:
        if fragment not in scene_text:
            raise SmokeCheckError(f"Godot menu layout is missing: {fragment}")

    if scene_text.count('instance=ExtResource("3_npc_scene")') != 13:
        raise SmokeCheckError("Godot world should contain eleven game NPCs and two town residents")
    if scene_text.count("wolf_character_id = 0") != 2:
        raise SmokeCheckError("exactly 坏坏 and 然然 should be non-participating resident NPCs")
    for character_id in range(2, 13):
        if scene_text.count(f"wolf_character_id = {character_id}\n") != 1:
            raise SmokeCheckError(f"wolf-game NPC id {character_id} should appear exactly once")
    for resident_name, asset_name in [("坏坏", "huaihuai.svg"), ("然然", "ranran.svg")]:
        mapping = f'"{resident_name}": "res://assets/characters/{asset_name}"'
        if mapping not in npc_script_text or mapping not in dialog_script_text:
            raise SmokeCheckError(f"Godot resident skin and portrait mapping is incomplete: {resident_name}")
    resident_asset_markers = {
        "坏坏": (
            huaihuai_asset_text,
            ["<title>坏坏小恐龙</title>", "#79bd67", "#78c9df", "#f3d66b"],
        ),
        "然然": (
            ranran_asset_text,
            ["<title>然然熊猫</title>", "#252b31", "#f8f4e9", "#62b7d0"],
        ),
    }
    for resident_name, (asset_text, markers) in resident_asset_markers.items():
        if 'width="64" height="64" viewBox="0 0 64 64"' not in asset_text:
            raise SmokeCheckError(f"resident pixel asset must stay 64x64: {resident_name}")
        if not all(marker in asset_text for marker in markers):
            raise SmokeCheckError(
                f"resident pixel asset does not match its designed species and palette: {resident_name}"
            )
    for fragment in [
        'dialog_text = "我是坏坏，点心屋的小恐龙。',
        'dialog_text = "我是然然，心情邮局的熊猫邮差。',
    ]:
        if fragment not in scene_text:
            raise SmokeCheckError("resident scene introduction is not synchronized with its visual identity")

    if scene_text.count('theme = SubResource("Theme_light_ui")') != 5:
        raise SmokeCheckError("every light UI root should use the black-text light theme")
    light_ui_start = scene_text.index('[node name="PhaseHUD" type="Control" parent="UI"]')
    light_ui_end = scene_text.index('[node name="GameSummaryOverlay" type="Control" parent="UI"]')
    light_ui_text = scene_text[light_ui_start:light_ui_end]
    for line in light_ui_text.splitlines():
        if "theme_override_colors/font" in line and "Color(0, 0, 0, 1)" not in line:
            raise SmokeCheckError(f"light UI text is not black: {line.strip()}")

    if 'card.custom_minimum_size = Vector2(168, 205)' not in script_text:
        raise SmokeCheckError("Godot character cards are not using the intel drawer three-column size")
    for fragment in [
        '[node name="TownBackground" type="Node2D"]',
        'z_index = -20',
        '[node name="WorldTint" type="CanvasModulate" parent="."]',
    ]:
        if fragment not in town_background_scene_text:
            raise SmokeCheckError(f"Godot layered town scene is missing: {fragment}")
    for fragment in [
        'const NIGHT_TINT :=',
        'const LAMP_POSITIONS :=',
        'func set_night(enabled: bool, immediate: bool = false) -> void:',
        '_transition_tween = create_tween()',
        'func _draw_pond() -> void:',
        'func _draw_buildings() -> void:',
        'func _draw_meeting_square() -> void:',
        'func _draw_gardens() -> void:',
        'func _draw_trees() -> void:',
        'func _draw_night_details() -> void:',
    ]:
        if fragment not in town_background_script_text:
            raise SmokeCheckError(f"Godot layered town drawing is missing: {fragment}")
    for fragment in [
        '@onready var town_background: Node2D = $TownBackground',
        'func _phase_uses_night_visual(phase: String) -> bool:',
        'return phase == "NIGHT"',
        'func _update_world_time(phase: String, immediate: bool = false) -> void:',
        'town_background.call("set_night", _phase_uses_night_visual(phase), immediate)',
        '_update_world_time("", true)',
        '_update_world_time(_current_wolf_phase)',
        '@onready var wolf_scroll_container: ScrollContainer',
        'const WOLF_MENU_WIDTH := 440.0',
        'const WOLF_MENU_MIN_EXPANDED_HEIGHT := 320.0',
        'const WOLF_MENU_MAX_EXPANDED_HEIGHT := 520.0',
        'const INTEL_PANEL_WIDTH := 600.0',
        'const IDENTITY_PANEL_COLLAPSED_BOTTOM := 184.0',
        'const IDENTITY_PANEL_EXPANDED_BOTTOM := 500.0',
        'viewport_height * 0.62',
        'func _show_game_setup() -> void:',
        'game_setup_overlay.add_to_group("dialog_open")',
        'setup_status_label.text = "创建失败：后端响应缺少游戏编号。"',
        'func _set_intel_panel_open(open: bool) -> void:',
        'game_summary_request.cancel_request()',
        'intel_tabs.set_tab_title(0, "场上角色")',
        'wolf_panel.visible = has_game',
        'setup_toggle_button.disabled = has_game and _current_wolf_phase != "GAME_OVER"',
        'for ui_root in [phase_hud, wolf_panel, intel_panel, game_setup_overlay]:',
        'var phase_changed := _current_wolf_phase != str(phase)',
        'call_deferred("_keep_sheriff_controls_visible")',
        'wolf_scroll_container.ensure_control_visible(sheriff_withdrawal_row)',
        'player_action_history_text.text = "\\n".join(lines)',
        'wolf_scroll_container.scroll_vertical = 0',
        'var easter_egg_triggered := bool(json.data.get("easter_egg_triggered", false))',
        '发现新的角色彩蛋。本次不会消耗今天的有效追问机会。',
    ]:
        if fragment not in script_text:
            raise SmokeCheckError(f"Godot compact panel behavior is missing: {fragment}")
    for removed_fragment in [
        '[node name="Ground" type="Polygon2D" parent="."]',
        '[node name="Path" type="Polygon2D" parent="."]',
        '[node name="MeetingSquare" type="Polygon2D" parent="."]',
        '[node name="GenerateNpcVoteButton"',
        '[node name="ResolveVoteButton"',
    ]:
        if removed_fragment in scene_text:
            raise SmokeCheckError(f"obsolete staged vote control is still present: {removed_fragment}")
    for script_fragment in [
        'func _render_game_summary(summary: Dictionary)',
        'func _request_game_summary()',
        'game_summary_tabs.set_tab_title(0, "角色复盘")',
        '"enable_llm": llm_enabled_toggle.button_pressed',
        '"npc_count": 11',
        'func _update_hunter_controls(game_data: Dictionary)',
        'private_info.get("wolf_teammates", [])',
        'character.get("public_claims", [])',
        'const WOLF_COMBINED_VOTE_URL',
        'func _update_sheriff_controls(game_data: Dictionary)',
        'func _on_sheriff_continue_button_pressed()',
        'func _on_sheriff_withdraw_button_pressed()',
        'func _submit_sheriff_action(withdraw_choice: Variant = null)',
        '"投警长并公布" if can_vote else "公布警长票型"',
        '"SHERIFF_WITHDRAWAL":',
        'func _format_combined_vote_result(vote_data: Dictionary)',
        '"reason": vote_reason',
        'str(_wolf_campaign_status.get(character_id, ""))',
        '"player_role": str(_get_selected_option_metadata(player_role_option, "random"))',
        'func _update_player_identity_display(game_data: Dictionary)',
        'func _update_key_public_info(game_data: Dictionary)',
        'game_data.get("public_intel", [])',
        'func _set_key_info_expanded(expanded: bool, animate: bool = true)',
        'previous_count == 0 and _key_info_count > 0',
        '"●" if str(item.get("category", "claim")) == "confirmed_action" else "◇"',
        'player_role_label.add_theme_color_override("font_color", Color(0, 0, 0, 1))',
        'label.add_theme_color_override("font_color", Color(0, 0, 0, 1))',
        'func _update_player_action_history(game_data: Dictionary)',
        'func _configure_wolf_panel_focus()',
        'node.focus_mode = Control.FOCUS_NONE',
        'call_deferred("_release_wolf_panel_focus")',
        'private_info.get("wolf_teammates", [])',
        'func _update_contextual_panel_visibility()',
        'night_action_option.visible = has_active_night_skill',
        '"temporary_nomination_target_id": null',
        'func _update_sheriff_overview()',
        'func _finish_gameplay_text_submission(input: LineEdit)',
        'player_speech_input.text_submitted.connect(_on_player_speech_input_submitted)',
        'sheriff_speech_input.text_submitted.connect(_on_sheriff_speech_input_submitted)',
        'vote_reason_input.text_submitted.connect(_on_vote_reason_input_submitted)',
        'get_viewport().gui_release_focus()',
    ]:
        if script_fragment not in script_text:
            raise SmokeCheckError(f"Godot game summary UI is missing: {script_fragment}")
    if 'window/size/viewport_width=1280' not in project_text or 'window/size/viewport_height=720' not in project_text:
        raise SmokeCheckError("Godot default window should be 1280x720")
    for dialog_fragment in [
        '[ext_resource type="FontFile" path="res://assets/fonts/NotoSansSC-Variable.ttf"',
        'theme = SubResource("Theme_dialog_cjk")',
        '[node name="ValidationFailureButton" type="Button"',
    ]:
        if dialog_fragment not in dialog_scene_text:
            raise SmokeCheckError(f"Godot dialog font fallback is missing: {dialog_fragment}")
    for script_fragment in [
        "func _clean_display_text",
        "func show_public_evidence_notice",
        "func _format_llm_fallback_reason",
        "func _on_validation_failure_button_pressed",
    ]:
        if script_fragment not in dialog_script_text:
            raise SmokeCheckError(f"Godot dialog text protection is missing: {script_fragment}")
    if not DIALOG_FONT_FILE.exists() or DIALOG_FONT_FILE.stat().st_size < 10_000_000:
        raise SmokeCheckError("bundled Noto Sans SC font is missing or incomplete")
    if not DIALOG_FONT_LICENSE_FILE.exists():
        raise SmokeCheckError("bundled Noto Sans SC OFL license is missing")

    for scene_label, scene_source in [
        ("NPC", npc_scene_text),
        ("player", player_scene_text),
    ]:
        if 'node name="CharacterSprite" type="Sprite2D"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its character sprite")
        if 'node name="SheriffBadge" type="Polygon2D"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its sheriff badge")
        if 'node name="CampaignBadge" type="Sprite2D"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its sheriff campaign badge")
        if 'node name="CampaignPKLabel" type="Label"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its PK marker")
    if 'campaign_status: String = ""' not in npc_script_text:
        raise SmokeCheckError("Godot NPC state does not expose sheriff campaign visuals")
    if 'theme_override_colors/font_outline_color = Color(0.96, 0.98, 1, 0.96)' not in npc_scene_text:
        raise SmokeCheckError("Godot NPC names need a light outline for night readability")
    if 'campaign_status: String = ""' not in player_script_text:
        raise SmokeCheckError("Godot player state does not expose sheriff campaign visuals")
    if 'func lock_movement_until_release()' not in player_script_text:
        raise SmokeCheckError("Godot player is missing the post-input movement release lock")
    if '_movement_release_lock = _is_any_movement_key_physically_pressed()' not in player_script_text:
        raise SmokeCheckError("Godot movement release lock should only capture keys held during submission")
    if 'focus_owner.is_visible_in_tree() and focus_owner.editable' not in player_script_text:
        raise SmokeCheckError("Godot player should ignore stale focus on disabled text inputs")
    if 'Vector2(menu_width * 0.5, 0.0)' not in player_script_text:
        raise SmokeCheckError("Godot camera safe area should center the player in the unobstructed viewport")
    if not POLICE_BADGE_FILE.exists():
        raise SmokeCheckError("Godot police campaign badge asset is missing")

    actual_assets = {path.name for path in CHARACTER_ASSET_DIR.glob("*.svg")}
    missing_assets = sorted(EXPECTED_CHARACTER_ASSETS - actual_assets)
    if missing_assets:
        raise SmokeCheckError("Godot character pixel assets are missing: " + ", ".join(missing_assets))
    for asset_name in EXPECTED_CHARACTER_ASSETS:
        asset_text = (CHARACTER_ASSET_DIR / asset_name).read_text(encoding="utf-8")
        if (
            'width="64" height="64"' not in asset_text
            or 'viewBox="0 0 64 64"' not in asset_text
            or 'shape-rendering="crispEdges"' not in asset_text
            or "\ufffd" in asset_text
            or any(marker in asset_text for marker in ["<image", "<text", "href=", "filter=", "gradient"])
        ):
            raise SmokeCheckError(f"Godot character asset is invalid: {asset_name}")

    print("[OK] Godot layered town, rule-driven day/night visuals, contextual UI, and pixel characters are present.")


def load_json_list(path: Path, label: str) -> list[dict]:
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise SmokeCheckError(f"{label} JSON is invalid: {exc}") from exc
    except OSError as exc:
        raise SmokeCheckError(f"could not read {label}: {exc}") from exc

    if not isinstance(data, list):
        raise SmokeCheckError(f"{label} must be a JSON list")
    return data


def require_keys(item: dict, keys: set[str], label: str) -> None:
    missing_keys = sorted(key for key in keys if key not in item)
    if missing_keys:
        raise SmokeCheckError(f"{label} missing keys: {', '.join(missing_keys)}")


def run_command(
    command: list[str],
    cwd: Path,
    fail_message: str,
    forbidden_output: tuple[str, ...] = (),
) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = "\n".join([result.stdout, result.stderr])
    output_error = next(
        (pattern for pattern in forbidden_output if pattern in combined_output),
        "",
    )
    if result.returncode != 0 or output_error:
        details = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        if output_error:
            details = f"forbidden output detected: {output_error}\n{details}"
        raise SmokeCheckError(f"{fail_message}\n{details}")


class SmokeCheckError(Exception):
    pass


if __name__ == "__main__":
    raise SystemExit(main())
