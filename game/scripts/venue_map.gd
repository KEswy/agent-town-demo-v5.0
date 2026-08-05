extends RefCounted

## Town venue registry: centers, radii, palettes, and NPC home/interest mapping.
## World coordinates follow the town WORLD_RECT and the existing NPC ring seats.

const WORLD_RECT := Rect2(-2000, -1500, 4000, 3000)
const MEETING_CENTER := Vector2(350, 0)
const POKER_DOOR_POSITION := Vector2(900, -260)

const VENUES := {
	"球场": {
		"center": Vector2(1150, -160),
		"radius": 300.0,
		"label": "球场",
		"kind": "football_field",
	},
	"至圣所": {
		"center": Vector2(-980, -300),
		"radius": 210.0,
		"label": "至圣所",
		"kind": "sanctum",
	},
	"点心屋": {
		"center": Vector2(-80, 420),
		"radius": 190.0,
		"label": "点心屋",
		"kind": "snack_house",
	},
	"心情邮局": {
		"center": Vector2(1250, 80),
		"radius": 190.0,
		"label": "心情邮局",
		"kind": "post_office",
	},
	"德州扑克馆": {
		"center": Vector2(1420, -450),
		"radius": 220.0,
		"label": "德州扑克馆",
		"kind": "poker_hall",
	},
}

const MINI_VENUES := {
	"练歌台": {"center": Vector2(560, -560), "radius": 150.0, "label": "练歌台", "kind": "stage"},
	"书房": {"center": Vector2(-820, -80), "radius": 160.0, "label": "书房", "kind": "study"},
	"钟楼": {"center": Vector2(350, 520), "radius": 150.0, "label": "钟楼", "kind": "clock_tower"},
	"训练场": {"center": Vector2(760, 520), "radius": 170.0, "label": "训练场", "kind": "training"},
	"工坊": {"center": Vector2(-420, 500), "radius": 160.0, "label": "工坊", "kind": "workshop"},
	"瞭望台": {"center": Vector2(1250, 320), "radius": 170.0, "label": "瞭望台", "kind": "lookout"},
	"野餐点": {"center": Vector2(60, -560), "radius": 170.0, "label": "野餐点", "kind": "picnic"},
}

## Render scale per venue kind (drawers are scaled around the venue center).
const VENUE_SCALES := {
	"football_field": 1.45,
	"picnic": 1.45,
	"stage": 1.4,
	"clock_tower": 1.35,
	"poker_hall": 1.35,
	"sanctum": 1.35,
	"snack_house": 1.35,
	"post_office": 1.35,
	"study": 1.35,
	"training": 1.35,
	"workshop": 1.35,
	"lookout": 1.35,
}

## Ground footprint half-extent per venue kind (so NPCs walk around, never on).
const FOOTPRINTS := {
	"football_field": 130.0,
	"sanctum": 115.0,
	"snack_house": 95.0,
	"post_office": 95.0,
	"poker_hall": 125.0,
	"stage": 100.0,
	"study": 100.0,
	"clock_tower": 60.0,
	"training": 110.0,
	"workshop": 100.0,
	"lookout": 95.0,
	"picnic": 105.0,
}

## NPCs that stay fixed at their venue doing an activity (relative to center).
const STATIONARY_SPOTS := {
	"梅西": Vector2(-90, 0),
	"C罗": Vector2(90, 0),
	"周深": Vector2(0, -5),
	"塞尔达": Vector2(-10, -62),
	"小骑士": Vector2(-60, 40),
	"喜羊羊": Vector2(-60, 0),
	"懒羊羊": Vector2(60, 0),
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

## Fixed venue activities and easter-egg bubble lines per NPC.
const NPC_ACTIVITIES := {
	"梅西": {
		"action": "踢球",
		"lines": [
			"这球要是进了，今晚的烤串我请！",
			"嘘……我其实惯用左脚，别告诉 C罗。",
			"刚才那脚弧线，你们看见了吗？",
			"看我的进球！",
		],
	},
	"C罗": {
		"action": "踢球",
		"lines": [
			"梅西，球门在那边，不在你脚下！",
			"我这记电梯球，小镇没人守得住。",
			"传球？……好吧，这球我自己带。",
		],
	},
	"周深": {
		"action": "唱歌",
		"lines": [
			"怕你飞远去，怕你离我而去，更怕你永远停留在这里。",
			"我是只化身孤岛的蓝鲸，有着最巨大的身影。",
			"达拉崩吧斑得贝迪卜多比鲁翁！",
			"莫听穿林打叶声，何妨吟啸且徐行。",
		],
	},
	"梅长苏": {
		"action": "看书",
		"lines": [
			"江左梅郎，麒麟才子，得之可得天下。",
			"这书里的计谋，比我当年的案卷还多。",
			"再狡黠的狐狸，也斗不过好猎手。",
		],
	},
	"塞尔达": {
		"action": "眺望远方",
		"lines": [
			"林克，等你归来。",
			"从瞭望台看下去，整个小镇尽收眼底。",
			"风从海那边来……",
		],
	},
	"小骑士": {
		"action": "训练（挥舞骨钉）",
		"lines": [
			"我是容器。",
			"骨钉在手，无所畏惧。",
			"再来三组！……呼，休息一下。",
		],
	},
	"大黄蜂": {
		"action": "修机械",
		"lines": [
			"嘎拉嘛！",
			"嗡嗡……别想逃。",
			"零件都在，就是螺丝还差一颗。",
		],
	},
	"喜羊羊": {
		"action": "野餐",
		"lines": [
			"野餐时间！谁带了沙拉？",
			"我数过了，零食够吃一下午。",
			"这块蛋糕归我啦！",
		],
	},
	"懒羊羊": {
		"action": "晒太阳",
		"lines": [
			"晒太阳……真舒服。",
			"运动？下次一定。",
			"吃完了，再睡一会儿。",
		],
	},
	"洛洛": {
		"action": "守钟楼",
		"lines": [
			"钟敲几下，我就数到几。",
			"十二点了，该睡觉啦。",
		],
	},
	"奇异博士": {
		"action": "守护至圣所",
		"lines": [
			"多重宇宙里，至少有一个你正坐在这个位置。",
			"我看见了 1400 万种结局，其中一种是我们去吃火锅。",
		],
	},
	"坏坏": {
		"action": "烤点心",
		"lines": [
			"今天的曲奇出炉啦，趁热！",
			"别怕，我的小尖牙只咬饼干。",
		],
	},
	"然然": {
		"action": "整理信件",
		"lines": [
			"您想寄存的故事，我帮您收好。",
			"今天的邮票，是心形的哦。",
		],
	},
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
