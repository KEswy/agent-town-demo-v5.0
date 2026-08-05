extends RefCounted

## Town venue registry: centers, radii, palettes, and NPC home/interest mapping.
## World coordinates follow the town WORLD_RECT and the existing NPC ring seats.

const WORLD_RECT := Rect2(-2000, -1500, 4000, 3000)
const MEETING_CENTER := Vector2(350, 0)
const POKER_DOOR_POSITION := Vector2(900, -260)

const VENUES := {
	"球场": {
		"center": Vector2(880, 165),
		"radius": 92.0,
		"fill": Color(0.45, 0.7, 0.38, 0.8),
		"ring": Color(1, 1, 1, 0.85),
		"label": "球场",
		"kind": "football_field",
	},
	"至圣所": {
		"center": Vector2(-430, -140),
		"radius": 86.0,
		"fill": Color(0.24, 0.21, 0.45, 0.85),
		"ring": Color(0.88, 0.66, 0.26, 0.95),
		"label": "至圣所",
		"kind": "sanctum",
	},
	"点心屋": {
		"center": Vector2(-170, 0),
		"radius": 76.0,
		"fill": Color(0.94, 0.8, 0.58, 0.88),
		"ring": Color(0.78, 0.5, 0.28, 0.95),
		"label": "点心屋",
		"kind": "snack_house",
	},
	"心情邮局": {
		"center": Vector2(870, -15),
		"radius": 78.0,
		"fill": Color(0.86, 0.72, 0.92, 0.88),
		"ring": Color(0.52, 0.32, 0.62, 0.95),
		"label": "心情邮局",
		"kind": "post_office",
	},
	"德州扑克馆": {
		"center": Vector2(900, -260),
		"radius": 74.0,
		"fill": Color(0.36, 0.46, 0.56, 0.88),
		"ring": Color(0.95, 0.78, 0.25, 0.95),
		"label": "德州扑克馆",
		"kind": "poker_hall",
	},
}

const MINI_VENUES := {
	"练歌台": {"center": Vector2(632, -118), "radius": 46.0, "label": "练歌台", "kind": "stage"},
	"书房": {"center": Vector2(657, 41), "radius": 46.0, "label": "书房", "kind": "study"},
	"钟楼": {"center": Vector2(584, 187), "radius": 50.0, "label": "钟楼", "kind": "clock_tower"},
	"训练场": {"center": Vector2(437, 273), "radius": 52.0, "label": "训练场", "kind": "training"},
	"工坊": {"center": Vector2(263, 273), "radius": 46.0, "label": "工坊", "kind": "workshop"},
	"瞭望台": {"center": Vector2(116, 187), "radius": 46.0, "label": "瞭望台", "kind": "lookout"},
	"野餐点": {"center": Vector2(43, 41), "radius": 48.0, "label": "野餐点", "kind": "picnic"},
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
