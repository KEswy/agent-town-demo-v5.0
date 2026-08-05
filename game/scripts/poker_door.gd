extends Area2D

signal door_requested

var _player_nearby := false

@onready var nearby_marker: Polygon2D = $NearbyMarker


func _ready() -> void:
	add_to_group("poker_door")
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	nearby_marker.visible = false


func is_player_nearby() -> bool:
	return _player_nearby


func request_entry() -> void:
	if _player_nearby:
		door_requested.emit()


func _on_body_entered(_body: Node) -> void:
	_player_nearby = true
	nearby_marker.visible = true


func _on_body_exited(_body: Node) -> void:
	_player_nearby = false
	nearby_marker.visible = false
