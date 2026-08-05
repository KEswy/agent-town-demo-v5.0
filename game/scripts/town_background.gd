extends Node2D

const DAY_TINT := Color(1, 1, 1, 1)
const NIGHT_TINT := Color(0.46, 0.53, 0.72, 1)
const TRANSITION_SECONDS := 0.75
const WORLD_RECT := Rect2(-2000, -1500, 4000, 3000)
const MEETING_CENTER := Vector2(350, 0)
const POND_CENTER := Vector2(-250, 255)

const VENUE_MAP = preload("res://scripts/venue_map.gd")

const TREE_POSITIONS := [
	Vector2(-880, -470), Vector2(-710, -590), Vector2(-500, -420),
	Vector2(-195, -300), Vector2(-55, -360), Vector2(770, -310),
	Vector2(940, -185), Vector2(1040, 95), Vector2(900, 310),
	Vector2(730, 405), Vector2(-575, 430), Vector2(-760, 245),
	Vector2(-980, 30), Vector2(1240, -520), Vector2(1320, 390),
]
const LAMP_POSITIONS := [
	Vector2(350, -192), Vector2(542, 0),
	Vector2(350, 192), Vector2(158, 0),
]
const FIREFLY_POSITIONS := [
	Vector2(-395, 182), Vector2(-334, 326), Vector2(-176, 181),
	Vector2(-82, 298), Vector2(815, 255), Vector2(872, 338),
	Vector2(-128, -278), Vector2(763, -268),
]
const FLOWER_COLORS := [
	Color(1, 0.79, 0.22, 1),
	Color(1, 0.55, 0.65, 1),
	Color(0.64, 0.82, 1, 1),
	Color(0.92, 0.72, 1, 1),
]

@onready var world_tint: CanvasModulate = $WorldTint

var _is_night := false
var _night_amount := 0.0
var _transition_tween: Tween


func _ready() -> void:
	set_night(false, true)
	queue_redraw()


func set_phase(phase: String, immediate: bool = false) -> void:
	set_night(phase == "NIGHT", immediate)


func set_night(enabled: bool, immediate: bool = false) -> void:
	if _is_night == enabled and not immediate:
		return
	_is_night = enabled
	if _transition_tween != null and _transition_tween.is_valid():
		_transition_tween.kill()

	var target_tint := NIGHT_TINT if enabled else DAY_TINT
	var target_amount := 1.0 if enabled else 0.0
	if immediate:
		world_tint.color = target_tint
		_set_night_amount(target_amount)
		return

	_transition_tween = create_tween()
	_transition_tween.set_parallel(true)
	_transition_tween.set_trans(Tween.TRANS_SINE)
	_transition_tween.set_ease(Tween.EASE_IN_OUT)
	_transition_tween.tween_property(world_tint, "color", target_tint, TRANSITION_SECONDS)
	_transition_tween.tween_method(
		_set_night_amount,
		_night_amount,
		target_amount,
		TRANSITION_SECONDS
	)


func _set_night_amount(value: float) -> void:
	_night_amount = clampf(value, 0.0, 1.0)
	queue_redraw()


func _draw() -> void:
	_draw_ground()
	_draw_paths()
	_draw_pond()
	_draw_buildings()
	_draw_venues()
	_draw_meeting_square()
	_draw_gardens()
	_draw_trees()
	_draw_square_furniture()
	_draw_night_details()


func _draw_venues() -> void:
	for venue in [VENUE_MAP.VENUES, VENUE_MAP.MINI_VENUES]:
		for venue_name in venue:
			var data: Dictionary = venue[venue_name]
			var center: Vector2 = data["center"]
			var kind := str(data["kind"])
			_draw_venue_building(kind, center)
			_draw_venue_label(center, str(data["label"]), kind)


func _draw_venue_building(kind: String, center: Vector2) -> void:
	match kind:
		"football_field":
			_draw_football_field(center)
		"sanctum":
			_draw_sanctum(center)
		"snack_house":
			_draw_snack_house(center)
		"post_office":
			_draw_post_office(center)
		"poker_hall":
			_draw_poker_hall(center)
		"stage":
			_draw_stage(center)
		"study":
			_draw_study(center)
		"clock_tower":
			_draw_clock_tower(center)
		"training":
			_draw_training(center)
		"workshop":
			_draw_workshop(center)
		"lookout":
			_draw_lookout(center)
		"picnic":
			_draw_picnic(center)


func _draw_venue_label(center: Vector2, label: String, kind: String) -> void:
	var font := ThemeDB.fallback_font
	var label_offset := 52.0
	match kind:
		"football_field":
			label_offset = 64.0
		"clock_tower":
			label_offset = 84.0
		"stage":
			label_offset = 44.0
		"picnic":
			label_offset = 52.0
	draw_string(
		font,
		center + Vector2(-34.0, label_offset),
		label,
		HORIZONTAL_ALIGNMENT_CENTER,
		68.0,
		13,
		Color(1, 1, 1, 0.96),
		TextServer.JUSTIFICATION_NONE,
		TextServer.DIRECTION_AUTO,
		TextServer.ORIENTATION_HORIZONTAL,
		6,
	)


func _draw_shadow(center: Vector2, width: float, height: float) -> void:
	draw_rect(
		Rect2(center + Vector2(-width * 0.5 + 6.0, -height * 0.5 + 9.0), Vector2(width, height)),
		Color(0.1, 0.2, 0.16, 0.2),
	)


func _draw_football_field(center: Vector2) -> void:
	var pitch := Rect2(center + Vector2(-82, -54), Vector2(164, 108))
	_draw_shadow(center, 180, 124)
	draw_rect(pitch, Color(0.36, 0.62, 0.32, 1))
	draw_rect(pitch, Color(0.94, 0.96, 0.9, 0.95), false, 3.0)
	draw_line(
		center + Vector2(0, -54),
		center + Vector2(0, 54),
		Color(0.94, 0.96, 0.9, 0.9),
		2.0,
	)
	draw_arc(center, 20.0, 0.0, TAU, 32, Color(0.94, 0.96, 0.9, 0.9), 2.0)
	for side in [-1.0, 1.0]:
		draw_rect(
			Rect2(center + Vector2(side * 82.0 - (6.0 if side < 0 else 0.0), -20), Vector2(6, 40)),
			Color(0.94, 0.96, 0.9, 0.9),
		)
		draw_rect(
			Rect2(center + Vector2(side * 58.0 - (6.0 if side < 0 else 0.0), -34), Vector2(6, 68)),
			Color(0.94, 0.96, 0.9, 0.9),
		)


func _draw_sanctum(center: Vector2) -> void:
	_draw_shadow(center, 176, 116)
	var wall_color := Color(0.28, 0.25, 0.55, 1)
	var gold := Color(0.88, 0.66, 0.26, 1)
	draw_rect(Rect2(center + Vector2(-80, -48), Vector2(160, 96)), wall_color)
	draw_colored_polygon(
		PackedVector2Array([
			center + Vector2(-96, -48),
			center + Vector2(-38, -88),
			center + Vector2(38, -88),
			center + Vector2(96, -48),
		]),
		gold,
	)
	draw_rect(Rect2(center + Vector2(-82, -50), Vector2(164, 5)), gold)
	draw_arc(center + Vector2(0, -8), 30.0, 0.0, TAU, 40, gold, 4.0)
	draw_circle(center + Vector2(0, -8), 24.0, Color(0.68, 0.82, 1, 1))
	for spoke in range(6):
		var angle := TAU * float(spoke) / 6.0
		draw_line(
			center + Vector2(0, -8) + Vector2(cos(angle), sin(angle)) * 7.0,
			center + Vector2(0, -8) + Vector2(cos(angle), sin(angle)) * 22.0,
			gold,
			2.0,
		)
	draw_rect(Rect2(center + Vector2(-20, 12), Vector2(40, 36)), Color(0.12, 0.1, 0.2, 1))
	draw_arc(center + Vector2(0, 30), 20.0, 0.0, PI, 24, gold, 3.0)
	draw_rect(Rect2(center + Vector2(-88, -8), Vector2(8, 40)), gold)
	draw_rect(Rect2(center + Vector2(80, -8), Vector2(8, 40)), gold)
	draw_circle(center + Vector2(0, -102), 7.0, gold)


func _draw_snack_house(center: Vector2) -> void:
	_draw_house_at(
		center,
		150.0,
		104.0,
		Color(0.98, 0.86, 0.62, 1),
		Color(0.78, 0.34, 0.3, 1),
	)
	var counter_y := center.y + 52.0
	draw_rect(Rect2(center + Vector2(-56, counter_y - 16), Vector2(112, 14)), Color(0.78, 0.58, 0.3, 1))
	for stripe_x in range(-56, 56, 28):
		draw_rect(
			Rect2(center + Vector2(float(stripe_x), counter_y - 30), Vector2(14, 14)),
			Color(0.95, 0.75, 0.3, 1) if (stripe_x / 28) % 2 == 0 else Color(0.85, 0.45, 0.4, 1),
		)
	draw_rect(Rect2(center + Vector2(-46, counter_y - 40), Vector2(92, 10)), Color(0.6, 0.42, 0.22, 1))


func _draw_post_office(center: Vector2) -> void:
	_draw_house_at(
		center,
		150.0,
		104.0,
		Color(0.72, 0.88, 0.96, 1),
		Color(0.28, 0.42, 0.62, 1),
	)
	var mailbox := center + Vector2(62, 20)
	draw_line(mailbox + Vector2(0, 26), mailbox + Vector2(0, -6), Color(0.42, 0.3, 0.18, 1), 5.0)
	draw_rect(Rect2(mailbox + Vector2(-16, -26), Vector2(32, 22)), Color(0.22, 0.4, 0.7, 1))
	draw_rect(Rect2(mailbox + Vector2(-16, -26), Vector2(32, 4)), Color(0.9, 0.9, 0.95, 1))
	draw_rect(Rect2(mailbox + Vector2(10, -32), Vector2(6, 10)), Color(0.8, 0.3, 0.25, 1))


func _draw_poker_hall(center: Vector2) -> void:
	_draw_shadow(center, 190, 128)
	var navy := Color(0.3, 0.4, 0.52, 1)
	var gold := Color(0.95, 0.78, 0.25, 1)
	draw_rect(Rect2(center + Vector2(-86, -54), Vector2(172, 104)), navy)
	draw_colored_polygon(
		PackedVector2Array([
			center + Vector2(-100, -54),
			center + Vector2(-44, -90),
			center + Vector2(44, -90),
			center + Vector2(100, -54),
		]),
		gold,
	)
	draw_rect(Rect2(center + Vector2(-88, -56), Vector2(176, 5)), Color(0.98, 0.9, 0.6, 1))
	for chip_y in [-118.0, -104.0, -90.0]:
		draw_circle(center + Vector2(0, chip_y), 14.0, Color(0.82, 0.3, 0.28, 1))
		draw_arc(center + Vector2(0, chip_y), 14.0, 0.0, TAU, 24, Color(0.98, 0.9, 0.6, 1), 2.5)
	draw_rect(Rect2(center + Vector2(-20, 22), Vector2(40, 30)), Color(0.14, 0.18, 0.24, 1))
	draw_rect(Rect2(center + Vector2(-24, 14), Vector2(48, 10)), Color(0.9, 0.82, 0.62, 1))


func _draw_stage(center: Vector2) -> void:
	_draw_shadow(center, 160, 52)
	draw_rect(Rect2(center + Vector2(-76, -14), Vector2(152, 26)), Color(0.68, 0.5, 0.3, 1))
	draw_rect(Rect2(center + Vector2(-76, -14), Vector2(152, 6)), Color(0.78, 0.6, 0.36, 1))
	for rail_x in range(-76, 76, 38):
		draw_rect(Rect2(center + Vector2(float(rail_x), 12), Vector2(5, 16)), Color(0.45, 0.33, 0.2, 1))
	draw_line(center + Vector2(-30, -14), center + Vector2(-30, -68), Color(0.5, 0.38, 0.22, 1), 4.0)
	draw_circle(center + Vector2(-30, -72), 6.0, Color(0.2, 0.22, 0.28, 1))
	draw_line(center + Vector2(-30, -76), center + Vector2(-30, -80), Color(0.2, 0.22, 0.28, 1), 2.0)
	draw_rect(Rect2(center + Vector2(38, -8), Vector2(22, 20)), Color(0.28, 0.3, 0.34, 1))
	draw_circle(center + Vector2(49, -14), 8.0, Color(0.28, 0.3, 0.34, 1))


func _draw_study(center: Vector2) -> void:
	_draw_house_at(
		center,
		140.0,
		100.0,
		Color(0.93, 0.87, 0.72, 1),
		Color(0.34, 0.55, 0.38, 1),
	)
	var window_rect := Rect2(center + Vector2(30, -14), Vector2(44, 46))
	draw_rect(window_rect, Color(0.72, 0.85, 0.92, 1))
	draw_rect(Rect2(center + Vector2(24, -20), Vector2(56, 4)), Color(0.5, 0.4, 0.26, 1))
	for shelf in range(3):
		var y := window_rect.position.y + 8.0 + float(shelf) * 14.0
		draw_rect(Rect2(window_rect.position + Vector2(6, y), Vector2(32, 5)), Color(0.5 + shelf * 0.12, 0.3 + shelf * 0.1, 0.4, 1))


func _draw_clock_tower(center: Vector2) -> void:
	_draw_shadow(center, 110, 150)
	draw_rect(Rect2(center + Vector2(-46, -6), Vector2(92, 78)), Color(0.8, 0.76, 0.68, 1))
	draw_rect(Rect2(center + Vector2(-34, -86), Vector2(68, 80)), Color(0.86, 0.82, 0.74, 1))
	draw_arc(center + Vector2(0, -58), 24.0, 0.0, TAU, 36, Color(0.4, 0.35, 0.3, 1), 3.0)
	draw_circle(center + Vector2(0, -58), 19.0, Color(0.96, 0.94, 0.86, 1))
	draw_line(center + Vector2(0, -58), center + Vector2(0, -46), Color(0.3, 0.28, 0.26, 1), 2.5)
	draw_line(center + Vector2(0, -58), center + Vector2(10, -58), Color(0.3, 0.28, 0.26, 1), 2.5)
	draw_colored_polygon(
		PackedVector2Array([
			center + Vector2(-52, -86),
			center + Vector2(0, -138),
			center + Vector2(52, -86),
		]),
		Color(0.72, 0.36, 0.32, 1),
	)
	draw_rect(Rect2(center + Vector2(-14, 44), Vector2(28, 28)), Color(0.42, 0.3, 0.2, 1))


func _draw_training(center: Vector2) -> void:
	_draw_shadow(center, 130, 104)
	draw_rect(Rect2(center + Vector2(-62, -48), Vector2(124, 96)), Color(0.6, 0.55, 0.44, 1))
	for corner in [Vector2(-62, -48), Vector2(62, -48), Vector2(-62, 48), Vector2(62, 48)]:
		draw_rect(Rect2(center + corner - Vector2(4, 4), Vector2(8, 8)), Color(0.4, 0.34, 0.26, 1))
	draw_line(center + Vector2(-62, -34), center + Vector2(62, -34), Color(0.5, 0.44, 0.34, 1), 4.0)
	draw_line(center + Vector2(-62, 34), center + Vector2(62, 34), Color(0.5, 0.44, 0.34, 1), 4.0)
	var dummy := center + Vector2(0, 10)
	draw_line(dummy + Vector2(0, 32), dummy + Vector2(0, -14), Color(0.52, 0.4, 0.26, 1), 6.0)
	draw_rect(Rect2(dummy + Vector2(-14, -18), Vector2(28, 30)), Color(0.78, 0.7, 0.55, 1))
	draw_circle(dummy + Vector2(0, -30), 9.0, Color(0.68, 0.5, 0.32, 1))
	draw_line(dummy + Vector2(-12, -10), dummy + Vector2(-26, 8), Color(0.52, 0.4, 0.26, 1), 4.0)
	draw_line(dummy + Vector2(12, -10), dummy + Vector2(26, 8), Color(0.52, 0.4, 0.26, 1), 4.0)


func _draw_workshop(center: Vector2) -> void:
	_draw_house_at(
		center,
		140.0,
		100.0,
		Color(0.76, 0.72, 0.66, 1),
		Color(0.5, 0.38, 0.26, 1),
	)
	draw_rect(Rect2(center + Vector2(-58, -74), Vector2(20, 30)), Color(0.4, 0.32, 0.24, 1))
	for puff_y in [-86.0, -98.0, -108.0]:
		draw_circle(center + Vector2(-48, puff_y), 7.0, Color(0.85, 0.83, 0.78, 0.7))


func _draw_lookout(center: Vector2) -> void:
	_draw_shadow(center, 120, 96)
	draw_rect(Rect2(center + Vector2(-52, 18), Vector2(8, 30)), Color(0.45, 0.33, 0.2, 1))
	draw_rect(Rect2(center + Vector2(44, 18), Vector2(8, 30)), Color(0.45, 0.33, 0.2, 1))
	draw_rect(Rect2(center + Vector2(-58, -24), Vector2(116, 10)), Color(0.66, 0.5, 0.3, 1))
	draw_line(center + Vector2(-58, -18), center + Vector2(-58, 10), Color(0.5, 0.38, 0.24, 1), 3.0)
	draw_line(center + Vector2(58, -18), center + Vector2(58, 10), Color(0.5, 0.38, 0.24, 1), 3.0)
	draw_line(center + Vector2(-58, -18), center + Vector2(58, -18), Color(0.55, 0.42, 0.26, 1), 3.0)
	draw_colored_polygon(
		PackedVector2Array([
			center + Vector2(-46, -24),
			center + Vector2(0, -58),
			center + Vector2(46, -24),
		]),
		Color(0.72, 0.46, 0.3, 1),
	)


func _draw_picnic(center: Vector2) -> void:
	_draw_shadow(center, 130, 78)
	draw_rect(Rect2(center + Vector2(-60, -34), Vector2(120, 68)), Color(0.85, 0.55, 0.5, 1))
	draw_rect(Rect2(center + Vector2(-60, -34), Vector2(60, 34)), Color(0.92, 0.84, 0.68, 1))
	draw_rect(Rect2(center + Vector2(0, 0), Vector2(60, 34)), Color(0.92, 0.84, 0.68, 1))
	draw_line(center + Vector2(-60, -17), center + Vector2(60, -17), Color(0.8, 0.7, 0.56, 1), 2.0)
	draw_line(center + Vector2(-30, -34), center + Vector2(-30, 34), Color(0.8, 0.7, 0.56, 1), 2.0)
	draw_line(center + Vector2(30, -34), center + Vector2(30, 34), Color(0.8, 0.7, 0.56, 1), 2.0)
	var basket := center + Vector2(30, 4)
	draw_colored_polygon(
		PackedVector2Array([
			basket + Vector2(-20, -14),
			basket + Vector2(20, -14),
			basket + Vector2(14, 6),
			basket + Vector2(-14, 6),
		]),
		Color(0.72, 0.5, 0.28, 1),
	)
	draw_arc(basket + Vector2(0, -14), 12.0, PI, TAU, 12, Color(0.55, 0.38, 0.22, 1), 3.0)


func _draw_house_at(
	center: Vector2,
	width: float,
	height: float,
	wall_color: Color,
	roof_color: Color,
) -> void:
	_draw_shadow(center, width, height)
	_draw_house(
		center - Vector2(width * 0.5, height * 0.5),
		Vector2(width, height),
		wall_color,
		roof_color,
	)


func _draw_ground() -> void:
	draw_rect(WORLD_RECT, Color(0.43, 0.66, 0.38, 1))
	var tile_size := 160.0
	for x_index in range(25):
		for y_index in range(19):
			if (x_index + y_index * 2) % 4 != 0:
				continue
			var tile_position := Vector2(
				WORLD_RECT.position.x + float(x_index) * tile_size,
				WORLD_RECT.position.y + float(y_index) * tile_size
			)
			draw_rect(
				Rect2(tile_position, Vector2(tile_size, tile_size)),
				Color(0.48, 0.71, 0.42, 0.18)
			)

	for grass_mark_value in [
		Vector2(-1040, -180), Vector2(-920, 420), Vector2(-690, -120),
		Vector2(-420, 510), Vector2(-170, -470), Vector2(825, -410),
		Vector2(1080, 290), Vector2(1240, -80), Vector2(720, 540),
	]:
		var grass_mark: Vector2 = grass_mark_value
		draw_line(grass_mark + Vector2(-7, 5), grass_mark + Vector2(-2, -8), Color(0.24, 0.5, 0.25, 0.65), 2.0)
		draw_line(grass_mark + Vector2(0, 6), grass_mark + Vector2(5, -7), Color(0.24, 0.5, 0.25, 0.65), 2.0)


func _draw_paths() -> void:
	var path_border := Color(0.56, 0.46, 0.25, 1)
	var path_fill := Color(0.84, 0.75, 0.48, 1)
	draw_rect(Rect2(-2000, -88, 4000, 176), path_border)
	draw_rect(Rect2(-2000, -70, 4000, 140), path_fill)
	draw_rect(Rect2(262, -1500, 176, 3000), path_border)
	draw_rect(Rect2(280, -1500, 140, 3000), path_fill)

	for x_position in range(-1920, 1970, 96):
		draw_line(
			Vector2(float(x_position), -54),
			Vector2(float(x_position + 46), 54),
			Color(0.68, 0.58, 0.34, 0.34),
			2.0
		)
	for y_position in range(-1440, 1470, 96):
		draw_line(
			Vector2(296, float(y_position)),
			Vector2(404, float(y_position + 46)),
			Color(0.68, 0.58, 0.34, 0.32),
			2.0
		)


func _draw_pond() -> void:
	draw_colored_polygon(_ellipse_points(POND_CENTER + Vector2(8, 12), Vector2(188, 125)), Color(0.2, 0.35, 0.28, 0.24))
	draw_colored_polygon(_ellipse_points(POND_CENTER, Vector2(190, 126)), Color(0.62, 0.76, 0.43, 1))
	draw_colored_polygon(_ellipse_points(POND_CENTER, Vector2(168, 106)), Color(0.31, 0.68, 0.77, 1))
	draw_colored_polygon(_ellipse_points(POND_CENTER + Vector2(-22, -12), Vector2(126, 68)), Color(0.43, 0.78, 0.84, 0.72))
	for offset_value in [Vector2(-95, 8), Vector2(-18, 55), Vector2(80, -25)]:
		var offset: Vector2 = offset_value
		draw_line(POND_CENTER + offset, POND_CENTER + offset + Vector2(42, -4), Color(0.8, 0.94, 0.93, 0.65), 3.0, true)
	for lily_position_value in [Vector2(-324, 248), Vector2(-210, 298), Vector2(-147, 229)]:
		var lily_position: Vector2 = lily_position_value
		draw_circle(lily_position, 10.0, Color(0.3, 0.63, 0.34, 1))
		draw_line(lily_position, lily_position + Vector2(9, -5), Color(0.18, 0.48, 0.27, 1), 2.0)


func _draw_buildings() -> void:
	_draw_house(Vector2(-820, -620), Vector2(240, 160), Color(1, 0.88, 0.55, 1), Color(0.36, 0.58, 0.72, 1))
	_draw_house(Vector2(1010, -570), Vector2(250, 165), Color(0.72, 0.9, 0.97, 1), Color(0.85, 0.42, 0.32, 1))
	_draw_house(Vector2(-920, 520), Vector2(230, 155), Color(0.74, 0.9, 0.98, 1), Color(0.94, 0.67, 0.24, 1))
	_draw_house(Vector2(1010, 485), Vector2(250, 165), Color(1, 0.9, 0.62, 1), Color(0.31, 0.55, 0.7, 1))
	_draw_house(Vector2(250, -760), Vector2(205, 145), Color(0.96, 0.83, 0.53, 1), Color(0.76, 0.34, 0.3, 1))
	_draw_market_stall(Vector2(830, 245), Color(0.96, 0.72, 0.2, 1), Color(0.42, 0.7, 0.82, 1))
	_draw_market_stall(Vector2(-670, -205), Color(0.4, 0.7, 0.82, 1), Color(1, 0.75, 0.28, 1))


func _draw_house(origin: Vector2, size: Vector2, wall_color: Color, roof_color: Color) -> void:
	draw_rect(Rect2(origin + Vector2(10, 12), size), Color(0.18, 0.25, 0.22, 0.22))
	draw_rect(Rect2(origin, size), wall_color)
	draw_colored_polygon(
		PackedVector2Array([
			origin + Vector2(-18, 24),
			origin + Vector2(size.x * 0.5, -42),
			origin + Vector2(size.x + 18, 24),
		]),
		roof_color
	)
	draw_rect(Rect2(origin + Vector2(size.x * 0.5 - 18, size.y - 62), Vector2(36, 62)), Color(0.42, 0.28, 0.18, 1))
	for window_x_value in [origin.x + 38, origin.x + size.x - 70]:
		var window_x := float(window_x_value)
		var window_rect := Rect2(Vector2(window_x, origin.y + 58), Vector2(32, 30))
		draw_rect(window_rect, Color(0.65, 0.9, 1, 1))
		draw_line(window_rect.position + Vector2(16, 0), window_rect.position + Vector2(16, 30), Color(0.31, 0.52, 0.62, 1), 2.0)
		draw_line(window_rect.position + Vector2(0, 15), window_rect.position + Vector2(32, 15), Color(0.31, 0.52, 0.62, 1), 2.0)


func _draw_market_stall(origin: Vector2, canopy_color: Color, stripe_color: Color) -> void:
	draw_rect(Rect2(origin + Vector2(8, 9), Vector2(126, 76)), Color(0.17, 0.24, 0.21, 0.2))
	draw_rect(Rect2(origin + Vector2(6, 26), Vector2(6, 62)), Color(0.4, 0.28, 0.17, 1))
	draw_rect(Rect2(origin + Vector2(116, 26), Vector2(6, 62)), Color(0.4, 0.28, 0.17, 1))
	draw_rect(Rect2(origin, Vector2(128, 30)), canopy_color)
	for stripe_x in range(0, 128, 32):
		draw_rect(Rect2(origin + Vector2(float(stripe_x), 0), Vector2(16, 30)), stripe_color)
	draw_rect(Rect2(origin + Vector2(10, 62), Vector2(108, 24)), Color(0.64, 0.42, 0.2, 1))


func _draw_meeting_square() -> void:
	draw_circle(MEETING_CENTER + Vector2(8, 10), 228.0, Color(0.18, 0.25, 0.22, 0.24))
	draw_circle(MEETING_CENTER, 228.0, Color(0.58, 0.51, 0.35, 1))
	draw_circle(MEETING_CENTER, 211.0, Color(0.84, 0.8, 0.65, 1))
	draw_circle(MEETING_CENTER, 176.0, Color(0.88, 0.85, 0.72, 1))
	for stone_index in range(24):
		var angle := TAU * float(stone_index) / 24.0
		var stone_position := MEETING_CENTER + Vector2(cos(angle), sin(angle)) * 194.0
		draw_circle(stone_position, 5.0, Color(0.67, 0.62, 0.49, 0.7))
	for line_index in range(8):
		var line_angle := TAU * float(line_index) / 8.0
		draw_line(
			MEETING_CENTER + Vector2(cos(line_angle), sin(line_angle)) * 92.0,
			MEETING_CENTER + Vector2(cos(line_angle), sin(line_angle)) * 168.0,
			Color(0.69, 0.65, 0.53, 0.42),
			2.0
		)


func _draw_gardens() -> void:
	_draw_flower_patch(Vector2(-55, 145), Vector2(110, 58), 0)
	_draw_flower_patch(Vector2(735, 92), Vector2(118, 60), 1)
	_draw_flower_patch(Vector2(-545, -285), Vector2(105, 56), 2)
	_draw_flower_patch(Vector2(680, -455), Vector2(112, 54), 3)
	_draw_fence(Vector2(-1050, -720), Vector2(-470, -720), 8)
	_draw_fence(Vector2(890, 700), Vector2(1410, 700), 7)


func _draw_flower_patch(origin: Vector2, size: Vector2, color_offset: int) -> void:
	draw_rect(Rect2(origin + Vector2(4, 5), size), Color(0.15, 0.24, 0.19, 0.18))
	draw_rect(Rect2(origin, size), Color(0.31, 0.53, 0.29, 1))
	for column in range(5):
		for row in range(2):
			var flower_position := origin + Vector2(14 + column * 21, 16 + row * 25)
			var flower_color: Color = FLOWER_COLORS[(column + row + color_offset) % FLOWER_COLORS.size()]
			draw_line(flower_position, flower_position + Vector2(0, 8), Color(0.18, 0.42, 0.21, 1), 2.0)
			draw_circle(flower_position, 4.0, flower_color)


func _draw_fence(from: Vector2, to: Vector2, post_count: int) -> void:
	draw_line(from + Vector2(0, 8), to + Vector2(0, 8), Color(0.62, 0.43, 0.23, 1), 6.0)
	for post_index in range(post_count):
		var ratio := float(post_index) / float(maxi(post_count - 1, 1))
		var post_position := from.lerp(to, ratio)
		draw_rect(Rect2(post_position + Vector2(-4, -8), Vector2(8, 32)), Color(0.72, 0.5, 0.27, 1))


func _draw_trees() -> void:
	for tree_index in range(TREE_POSITIONS.size()):
		var scale_factor := 0.82 + float(tree_index % 4) * 0.08
		var tree_position: Vector2 = TREE_POSITIONS[tree_index]
		_draw_tree(tree_position, scale_factor)


func _draw_tree(position: Vector2, scale_factor: float) -> void:
	draw_colored_polygon(
		_ellipse_points(position + Vector2(8, 18) * scale_factor, Vector2(48, 25) * scale_factor),
		Color(0.13, 0.24, 0.17, 0.22)
	)
	draw_rect(
		Rect2(position + Vector2(-8, 4) * scale_factor, Vector2(16, 45) * scale_factor),
		Color(0.42, 0.28, 0.16, 1)
	)
	draw_circle(position + Vector2(-22, -8) * scale_factor, 31.0 * scale_factor, Color(0.2, 0.51, 0.25, 1))
	draw_circle(position + Vector2(22, -7) * scale_factor, 32.0 * scale_factor, Color(0.25, 0.59, 0.29, 1))
	draw_circle(position + Vector2(0, -30) * scale_factor, 39.0 * scale_factor, Color(0.3, 0.65, 0.33, 1))
	draw_circle(position + Vector2(-5, -36) * scale_factor, 18.0 * scale_factor, Color(0.42, 0.72, 0.4, 0.7))


func _draw_square_furniture() -> void:
	_draw_bench(Vector2(-30, -230), false)
	_draw_bench(Vector2(720, 260), true)
	for lamp_position_value in LAMP_POSITIONS:
		var lamp_position: Vector2 = lamp_position_value
		_draw_lamp(lamp_position)
	_draw_sign(Vector2(-18, -112))


func _draw_bench(position: Vector2, vertical: bool) -> void:
	if vertical:
		draw_rect(Rect2(position + Vector2(-10, -38), Vector2(20, 76)), Color(0.51, 0.32, 0.17, 1))
		draw_line(position + Vector2(-16, -30), position + Vector2(-16, 30), Color(0.28, 0.25, 0.2, 1), 4.0)
	else:
		draw_rect(Rect2(position + Vector2(-38, -10), Vector2(76, 20)), Color(0.51, 0.32, 0.17, 1))
		draw_line(position + Vector2(-30, 16), position + Vector2(30, 16), Color(0.28, 0.25, 0.2, 1), 4.0)


func _draw_lamp(position: Vector2) -> void:
	draw_line(position + Vector2(0, 20), position + Vector2(0, -22), Color(0.18, 0.25, 0.29, 1), 6.0)
	draw_rect(Rect2(position + Vector2(-10, -34), Vector2(20, 18)), Color(0.2, 0.31, 0.36, 1))
	draw_circle(position + Vector2(0, -25), 6.0, Color(1, 0.82, 0.3, 1))
	draw_line(position + Vector2(-13, 21), position + Vector2(13, 21), Color(0.18, 0.25, 0.29, 1), 5.0)


func _draw_sign(position: Vector2) -> void:
	draw_line(position + Vector2(0, 2), position + Vector2(0, 48), Color(0.43, 0.29, 0.17, 1), 7.0)
	draw_rect(Rect2(position + Vector2(-42, -22), Vector2(84, 30)), Color(0.88, 0.69, 0.34, 1))
	draw_line(position + Vector2(-30, -7), position + Vector2(26, -7), Color(0.38, 0.32, 0.22, 0.7), 3.0)


func _draw_night_details() -> void:
	if _night_amount <= 0.001:
		return
	for lamp_position_value in LAMP_POSITIONS:
		var lamp_position: Vector2 = lamp_position_value
		var light_center := lamp_position + Vector2(0, -25)
		draw_circle(light_center, 92.0, Color(1, 0.74, 0.18, 0.08 * _night_amount))
		draw_circle(light_center, 56.0, Color(1, 0.78, 0.2, 0.14 * _night_amount))
		draw_circle(light_center, 24.0, Color(1, 0.87, 0.42, 0.24 * _night_amount))
	for firefly_position_value in FIREFLY_POSITIONS:
		var firefly_position: Vector2 = firefly_position_value
		draw_circle(firefly_position, 8.0, Color(1, 0.87, 0.28, 0.12 * _night_amount))
		draw_circle(firefly_position, 2.5, Color(1, 0.95, 0.55, 0.95 * _night_amount))
	draw_colored_polygon(
		_ellipse_points(POND_CENTER + Vector2(48, -8), Vector2(48, 20)),
		Color(0.72, 0.86, 1, 0.18 * _night_amount)
	)


func _ellipse_points(center: Vector2, radius: Vector2, point_count: int = 48) -> PackedVector2Array:
	var points := PackedVector2Array()
	for point_index in range(point_count):
		var angle := TAU * float(point_index) / float(point_count)
		points.append(center + Vector2(cos(angle) * radius.x, sin(angle) * radius.y))
	return points
