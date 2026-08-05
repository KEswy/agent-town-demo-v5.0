extends Node2D

## Small animated props that bring fixed venue activities to life:
## a soccer ball rolling between Messi and Ronaldo, music notes floating up
## from the stage mic while Zhou Shen sings, and Little Knight's nail swing.

const VENUE_MAP = preload("res://scripts/venue_map.gd")

var _time := 0.0
var _active := true


func _process(delta: float) -> void:
	if _active:
		_time += delta
		queue_redraw()


func set_active(enabled: bool) -> void:
	if _active == enabled:
		return
	_active = enabled
	queue_redraw()


func _draw() -> void:
	if not _active:
		return
	_draw_football_ball()
	_draw_music_notes()
	_draw_nail_swing()


func _draw_football_ball() -> void:
	var left := Vector2(1060, -160)
	var right := Vector2(1240, -160)
	var phase := fmod(_time / 1.5, 1.0)
	var ball_pos := left.lerp(right, phase)
	var height: float = absf(sin(phase * PI)) * 30.0
	ball_pos.y -= height
	draw_circle(Vector2(ball_pos.x, -152), 8.0 - height * 0.08, Color(0.1, 0.12, 0.12, 0.22))
	draw_circle(ball_pos, 7.0, Color(1, 1, 1, 1))
	draw_circle(ball_pos + Vector2(-2.2, -2.2), 2.0, Color(0.12, 0.12, 0.12, 1))
	draw_circle(ball_pos + Vector2(2.2, 2.2), 2.0, Color(0.12, 0.12, 0.12, 1))


func _draw_music_notes() -> void:
	var burst := fmod(_time, 6.0)
	if burst >= 2.8:
		return
	var origin := Vector2(512, -600)
	for i in range(3):
		var t := fmod(_time * 0.42 + float(i) * 0.37, 1.0)
		var note_pos := origin + Vector2(sin((t + float(i)) * 5.0) * 12.0, -t * 70.0)
		_draw_note(note_pos, Color(1, 0.92, 0.55, (1.0 - t) * 0.95))


func _draw_note(pos: Vector2, color: Color) -> void:
	draw_circle(pos, 5.0, color)
	draw_line(pos + Vector2(4, -3), pos + Vector2(4, -24), color, 2.0)
	draw_colored_polygon(
		PackedVector2Array([
			pos + Vector2(4, -24),
			pos + Vector2(14, -19),
			pos + Vector2(4, -15),
		]),
		color,
	)


func _draw_nail_swing() -> void:
	var pivot := Vector2(736, 548)
	var angle := sin(_time * 3.0) * 1.15 - 0.45
	var tip := pivot + Vector2(cos(angle), sin(angle)) * 46.0
	draw_line(pivot, tip, Color(0.72, 0.74, 0.8, 1), 5.0)
	draw_line(pivot + Vector2(0, 11), pivot + Vector2(0, -11), Color(0.5, 0.42, 0.3, 1), 4.0)
	draw_circle(tip, 3.0, Color(0.85, 0.87, 0.92, 1))
	draw_arc(pivot, 56.0, angle - 0.5, angle + 0.15, 12, Color(1, 1, 1, 0.35), 2.0)
