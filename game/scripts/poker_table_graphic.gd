extends Node2D

const TABLE_RADIUS := 150.0
const RIM_WIDTH := 12.0


func _draw() -> void:
	draw_circle(Vector2(6, 10), TABLE_RADIUS + 10.0, Color(0.1, 0.16, 0.12, 0.25))
	draw_circle(Vector2.ZERO, TABLE_RADIUS, Color(0.36, 0.24, 0.14, 1))
	draw_circle(Vector2.ZERO, TABLE_RADIUS - RIM_WIDTH, Color(0.14, 0.42, 0.22, 1))
	draw_arc(
		Vector2.ZERO,
		TABLE_RADIUS - RIM_WIDTH,
		0.0,
		TAU,
		72,
		Color(0.2, 0.52, 0.3, 0.8),
		2.0,
	)
	draw_circle(Vector2(0, -6), 40.0, Color(0.1, 0.3, 0.18, 0.95))
	draw_arc(Vector2(0, -6), 40.0, 0.0, TAU, 40, Color(0.9, 0.75, 0.4, 0.85), 3.0)
	for marker_i in range(8):
		var angle := TAU * float(marker_i) / 8.0
		draw_line(
			Vector2(cos(angle), sin(angle)) * (TABLE_RADIUS - RIM_WIDTH - 6.0),
			Vector2(cos(angle), sin(angle)) * (TABLE_RADIUS - RIM_WIDTH - 16.0),
			Color(0.22, 0.55, 0.32, 0.55),
			2.0,
		)
