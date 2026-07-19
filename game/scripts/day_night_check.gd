extends SceneTree


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene := load("res://scenes/TownBackground.tscn") as PackedScene
	if packed_scene == null:
		_fail("could not load TownBackground.tscn")
		return

	var town_background := packed_scene.instantiate()
	root.add_child(town_background)
	await process_frame

	var world_tint := town_background.get_node("WorldTint") as CanvasModulate
	if world_tint == null:
		_fail("TownBackground is missing WorldTint")
		return

	town_background.call("set_phase", "NIGHT", true)
	if not world_tint.color.is_equal_approx(Color(0.46, 0.53, 0.72, 1)):
		_fail("NIGHT did not apply the night tint")
		return

	for day_phase in ["", "SHERIFF_SIGNUP", "DAY_MEETING", "FREE_ACTIVITY", "VOTE", "GAME_OVER"]:
		town_background.call("set_phase", day_phase, true)
		if not world_tint.color.is_equal_approx(Color.WHITE):
			_fail(str(day_phase) + " should use the day tint")
			return

	print("[OK] Town background uses NIGHT-only visual mapping.")
	town_background.queue_free()
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
