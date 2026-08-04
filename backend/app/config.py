"""App-wide constants and configuration (no business logic).

Kept separate from ``main.py`` so request/response schemas and rule code can
import the same defaults without circular imports.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR = Path(
    os.environ.get("AGENT_TOWN_DATA_DIR", str(DEFAULT_DATA_DIR))
).expanduser()
MEMORY_FILE = DATA_DIR / "memory.json"
GAME_SAVE_DIR = Path(
    os.environ.get("AGENT_TOWN_GAME_SAVE_DIR", str(DATA_DIR / "games"))
)
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
NPC_PROFILES_FILE = CONFIG_DIR / "npc_profiles.json"
KNOWLEDGE_BASE_FILE = CONFIG_DIR / "knowledge_base.json"
NPC_TUNING_FILE = CONFIG_DIR / "npc_tuning.json"
LLM_VALIDATION_LOG_FILE = DATA_DIR / "llm_validation_failures.jsonl"
MAX_LLM_VALIDATION_ATTEMPTS = 5
LLM_VALIDATOR_VERSION = "semantic-v3"
RESIDENT_CHAT_CONTEXT_SCHEMA_VERSION = "resident_chat_context.v1"
RESIDENT_CHAT_MEMORY_LIMIT = 8
RESIDENT_CHAT_MAX_LENGTH = 360
VALID_ELIMINATION_SOURCES = {
    "night_kill": "werewolf_kill",
    "witch_poison": "witch_poison",
    "hunter_shot": "hunter_shot",
    "exiled": "day_vote",
}
BADGE_FLOW_REASON_LABELS = {
    "initial": "初始警徽流",
    "target_eliminated": "原目标已经出局",
    "role_reveal": "原目标公开了身份信息",
    "new_counterclaim": "场上出现新的对跳关系",
    "vote_shift": "公开票型发生变化",
    "speech_change": "目标的发言或站边发生变化",
    "higher_value": "新的位置更值得优先定义",
    "avoid_predictability": "避免狼人根据旧警徽流安排刀口",
    "other_public_reason": "根据新的公开局势调整",
}

DEFAULT_WOLF_ROLES = {
    "werewolf": 4,
    "seer": 1,
    "witch": 1,
    "hunter": 1,
    "guard": 1,
    "villager": 4,
}
ROLE_LABELS = {
    "werewolf": "狼人",
    "seer": "预言家",
    "witch": "女巫",
    "hunter": "猎人",
    "guard": "守卫",
    "villager": "村民",
}
CAMP_BY_ROLE = {
    "werewolf": "werewolf",
    "seer": "good",
    "witch": "good",
    "hunter": "good",
    "guard": "good",
    "villager": "good",
}
GOD_ROLES = {"seer", "witch", "hunter", "guard"}
NPC_NAMES = [
    "梅西",
    "C罗",
    "周深",
    "梅长苏",
    "塞尔达",
    "小骑士",
    "大黄蜂",
    "喜羊羊",
    "懒羊羊",
    "洛洛",
    "奇异博士",
]
FIXED_NPC_COUNT = 11
MAX_GAME_RANDOM_SEED = (1 << 63) - 1
WITCH_DIRECTIVE_SCHEMA_VERSION = "witch_directive.v1"
WITCH_STRATEGY_SCHEMA_VERSION = "witch_strategy_decision.v1"
NPC_WITCH_FIRST_NIGHT_SAVE_RATE = 0.99
FAKE_SEER_CAMPAIGN_POLICY_VERSION = "fake_seer_campaign.v2"
# Keep the paired-cohort random stream stable while policy thresholds evolve.
FAKE_SEER_CAMPAIGN_RANDOM_STREAM = "fake_seer_campaign.v1"
FAKE_SEER_CHECK_POLICY_VERSION = "fake_seer_check_mix.v1"
WOLF_SHERIFF_CAMPAIGN_POLICY_VERSION = "wolf_sheriff_campaign.v1"
PUBLIC_CONTESTED_EXILE_MAX_SHARE = 0.75
PUBLIC_SPEECH_LLM_MAX_CHARS = 120
SHERIFF_WINDOW_PHASES = {
    "SHERIFF_SPEECH",
    "SHERIFF_RUNOFF_SPEECH",
    "SHERIFF_WITHDRAWAL",
    "SHERIFF_RUNOFF_VOTE",
    "SHERIFF_VOTE",
}

NPC_PERSONALITIES = {
    "梅西": {
        "aggressiveness": 0.24,
        "cautiousness": 0.76,
        "deception": 0.34,
        "logic": 0.78,
        "empathy": 0.68,
        "leadership": 0.50,
    },
    "C罗": {
        "aggressiveness": 0.78,
        "cautiousness": 0.34,
        "deception": 0.50,
        "logic": 0.62,
        "empathy": 0.38,
        "leadership": 0.84,
    },
    "周深": {
        "aggressiveness": 0.20,
        "cautiousness": 0.68,
        "deception": 0.32,
        "logic": 0.66,
        "empathy": 0.88,
        "leadership": 0.42,
    },
    "梅长苏": {
        "aggressiveness": 0.38,
        "cautiousness": 0.88,
        "deception": 0.82,
        "logic": 0.95,
        "empathy": 0.52,
        "leadership": 0.76,
    },
    "塞尔达": {
        "aggressiveness": 0.52,
        "cautiousness": 0.72,
        "deception": 0.34,
        "logic": 0.72,
        "empathy": 0.70,
        "leadership": 0.68,
    },
    "小骑士": {
        "aggressiveness": 0.30,
        "cautiousness": 0.82,
        "deception": 0.45,
        "logic": 0.74,
        "empathy": 0.48,
        "leadership": 0.35,
    },
    "大黄蜂": {
        "aggressiveness": 0.74,
        "cautiousness": 0.70,
        "deception": 0.58,
        "logic": 0.78,
        "empathy": 0.46,
        "leadership": 0.72,
    },
    "喜羊羊": {
        "aggressiveness": 0.48,
        "cautiousness": 0.72,
        "deception": 0.60,
        "logic": 0.86,
        "empathy": 0.76,
        "leadership": 0.82,
    },
    "懒羊羊": {
        "aggressiveness": 0.16,
        "cautiousness": 0.50,
        "deception": 0.38,
        "logic": 0.50,
        "empathy": 0.80,
        "leadership": 0.28,
    },
    "洛洛": {
        "aggressiveness": 0.44,
        "cautiousness": 0.66,
        "deception": 0.52,
        "logic": 0.90,
        "empathy": 0.54,
        "leadership": 0.64,
    },
    "奇异博士": {
        "aggressiveness": 0.36,
        "cautiousness": 0.88,
        "deception": 0.74,
        "logic": 0.94,
        "empathy": 0.58,
        "leadership": 0.78,
    },
}


