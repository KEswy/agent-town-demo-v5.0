extends RefCounted

## Town venue registry: centers, radii, palettes, and NPC home/interest mapping.
## World coordinates follow the town WORLD_RECT and the existing NPC ring seats.

const WORLD_RECT := Rect2(-2000, -1500, 4000, 3000)
const MEETING_CENTER := Vector2(350, 0)
const POKER_DOOR_POSITION := Vector2(900, -260)

const VENUES := {
	"球场": {
		"center": Vector2(1150, -160),
		"radius": 150.0,
		"label": "球场",
		"kind": "football_field",
	},
	"至圣所": {
		"center": Vector2(-980, -300),
		"radius": 130.0,
		"label": "至圣所",
		"kind": "sanctum",
	},
	"点心屋": {
		"center": Vector2(-80, 420),
		"radius": 120.0,
		"label": "点心屋",
		"kind": "snack_house",
	},
	"心情邮局": {
		"center": Vector2(1250, 80),
		"radius": 120.0,
		"label": "心情邮局",
		"kind": "post_office",
	},
	"德州扑克馆": {
		"center": Vector2(1420, -450),
		"radius": 140.0,
		"label": "德州扑克馆",
		"kind": "poker_hall",
	},
}

const MINI_VENUES := {
	"练歌台": {"center": Vector2(560, -560), "radius": 90.0, "label": "练歌台", "kind": "stage"},
	"书房": {"center": Vector2(-820, -80), "radius": 90.0, "label": "书房", "kind": "study"},
	"钟楼": {"center": Vector2(350, 520), "radius": 100.0, "label": "钟楼", "kind": "clock_tower"},
	"训练场": {"center": Vector2(760, 520), "radius": 105.0, "label": "训练场", "kind": "training"},
	"工坊": {"center": Vector2(-420, 500), "radius": 90.0, "label": "工坊", "kind": "workshop"},
	"瞭望台": {"center": Vector2(1250, 320), "radius": 90.0, "label": "瞭望台", "kind": "lookout"},
	"野餐点": {"center": Vector2(60, -560), "radius": 100.0, "label": "野餐点", "kind": "picnic"},
}

const NPC_HOMES := {
	"梅西": "球场",
	"C罗": "球场",
	"奇异博士": "至圣所",
	"坏坏": "点心屋",
	"然然": "心情邮局",
	"周深": "练歌台",
	"梅长苏": "书房",
	"洛洛": "钟楼",
	"小骑士": "训练场",
	"大黄蜂": "工坊",
	"塞尔达": "瞭望台",
	"喜羊羊": "野餐点",
	"懒羊羊": "野餐点",
}

## Fixed werewolf-game ring seats (they gather here in a circle during games).
const RING_SEATS := {
	"梅西": Vector2(350, -285),
	"C罗": Vector2(518, -240),
	"周深": Vector2(632, -118),
	"梅长苏": Vector2(657, 41),
	"塞尔达": Vector2(584, 187),
	"小骑士": Vector2(437, 273),
	"大黄蜂": Vector2(263, 273),
	"喜羊羊": Vector2(116, 187),
	"懒羊羊": Vector2(43, 41),
	"洛洛": Vector2(68, -118),
	"奇异博士": Vector2(182, -240),
	"坏坏": Vector2(-170, 0),
	"然然": Vector2(870, 0),
}

## Client-side mirror of the backend NPC personalities (movement pacing only).
const NPC_PERSONALITIES := {
	"梅西": {"aggressiveness": 0.24, "cautiousness": 0.76},
	"C罗": {"aggressiveness": 0.78, "cautiousness": 0.34},
	"周深": {"aggressiveness": 0.20, "cautiousness": 0.68},
	"梅长苏": {"aggressiveness": 0.38, "cautiousness": 0.88},
	"塞尔达": {"aggressiveness": 0.52, "cautiousness": 0.72},
	"小骑士": {"aggressiveness": 0.30, "cautiousness": 0.82},
	"大黄蜂": {"aggressiveness": 0.74, "cautiousness": 0.70},
	"喜羊羊": {"aggressiveness": 0.48, "cautiousness": 0.72},
	"懒羊羊": {"aggressiveness": 0.16, "cautiousness": 0.50},
	"洛洛": {"aggressiveness": 0.44, "cautiousness": 0.66},
	"奇异博士": {"aggressiveness": 0.36, "cautiousness": 0.88},
	"坏坏": {"aggressiveness": 0.35, "cautiousness": 0.60},
	"然然": {"aggressiveness": 0.30, "cautiousness": 0.65},
}

const INTEREST_POINTS := {
	"梅西": [Vector2(560, -40), MEETING_CENTER],
	"C罗": [Vector2(560, -40), MEETING_CENTER],
	"奇异博士": [Vector2(-250, -80), MEETING_CENTER],
	"周深": [MEETING_CENTER],
	"梅长苏": [MEETING_CENTER],
	"洛洛": [MEETING_CENTER],
	"小骑士": [MEETING_CENTER],
	"大黄蜂": [MEETING_CENTER],
	"塞尔达": [MEETING_CENTER],
	"喜羊羊": [MEETING_CENTER],
	"懒羊羊": [MEETING_CENTER],
	"坏坏": [MEETING_CENTER],
	"然然": [MEETING_CENTER],
}


static func venue_center(name: String) -> Vector2:
	if VENUES.has(name):
		return VENUES[name]["center"]
	if MINI_VENUES.has(name):
		return MINI_VENUES[name]["center"]
	return MEETING_CENTER


static func home_venue(npc_name: String) -> String:
	return str(NPC_HOMES.get(npc_name, "会议广场"))


static func interest_targets(npc_name: String) -> Array:
	return INTEREST_POINTS.get(npc_name, [MEETING_CENTER])
