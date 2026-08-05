extends Area2D

signal dialog_requested(npc_name: String, dialog_text: String, wolf_character_id: int)

@export var npc_name: String = "Guide"
@export_multiline var dialog_text: String = "你好，我是第一个 AI NPC。后面我会接入记忆和知识库。"
@export var wolf_character_id: int = 0
@export var body_color: Color = Color(0.95, 0.58, 0.2, 1)

const SKIN_PATHS := {
	"梅西": "res://assets/characters/messi.svg",
	"C罗": "res://assets/characters/ronaldo.svg",
	"周深": "res://assets/characters/zhou_shen.svg",
	"梅长苏": "res://assets/characters/mei_changsu.svg",
	"塞尔达": "res://assets/characters/zelda.svg",
	"小骑士": "res://assets/characters/little_knight.svg",
	"大黄蜂": "res://assets/characters/hornet.svg",
	"喜羊羊": "res://assets/characters/pleasant_goat.svg",
	"懒羊羊": "res://assets/characters/lazy_goat.svg",
	"洛洛": "res://assets/characters/luoluo.svg",
	"奇异博士": "res://assets/characters/doctor_strange.svg",
	"坏坏": "res://assets/characters/huaihuai.svg",
	"然然": "res://assets/characters/ranran.svg",
}
const VENUE_MAP = preload("res://scripts/venue_map.gd")

var _player_nearby := false
var _alive := true
var _is_current_speaker := false
var _is_sheriff := false
var _campaign_status := ""
var _roaming_enabled := true
var _move_state := "idle"
var _move_target := Vector2.ZERO
var _stay_until_ms := 0
var _walk_speed := 46.0
var _stay_seconds := 2.5
var _walk_phase := 0.0
var _ring_position := Vector2.ZERO
var _locked := false
var _facing_right := true
var _poker_indicator_visible := false
var _rng := RandomNumberGenerator.new()

@onready var body_shape: Polygon2D = $Body
@onready var character_sprite: Sprite2D = $CharacterSprite
@onready var sheriff_badge: Polygon2D = $SheriffBadge
@onready var campaign_badge: Sprite2D = $CampaignBadge
@onready var campaign_pk_label: Label = $CampaignPKLabel
@onready var nearby_marker: Polygon2D = $NearbyMarker
@onready var turn_indicator: Polygon2D = $TurnIndicator
@onready var speech_hint: Node2D = $SpeechHint
@onready var name_label: Label = $NameLabel
@onready var poker_indicator: Label = $PokerIndicator


func _ready() -> void:
	add_to_group("npc")
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	nearby_marker.visible = false
	turn_indicator.visible = false
	speech_hint.visible = false
	poker_indicator.visible = false
	body_shape.color = body_color
	_load_character_skin()
	_init_movement()
	_update_visual_state()


func is_player_nearby() -> bool:
	return _player_nearby


func request_dialog() -> void:
	if _player_nearby:
		dialog_requested.emit(npc_name, dialog_text, wolf_character_id)


func get_wolf_character_id() -> int:
	return wolf_character_id


func set_wolf_game_state(
	alive: bool,
	is_current_speaker: bool,
	is_sheriff: bool = false,
	campaign_status: String = ""
) -> void:
	_alive = alive
	_is_current_speaker = is_current_speaker
	_is_sheriff = is_sheriff
	_campaign_status = campaign_status
	_update_visual_state()


func _load_character_skin() -> void:
	var path := str(SKIN_PATHS.get(npc_name, ""))
	if path.is_empty() or not ResourceLoader.exists(path):
		character_sprite.visible = false
		body_shape.visible = true
		return
	var texture = load(path)
	if texture is Texture2D:
		character_sprite.texture = texture
		character_sprite.visible = true
		body_shape.visible = false


func _update_visual_state() -> void:
	var title := npc_name
	if wolf_character_id > 0:
		title += " [" + str(wolf_character_id) + "号]"
	if not _alive:
		title += "\n已出局"
	elif _is_current_speaker:
		title += "\n轮到发言"
	elif _is_sheriff:
		title += "\n警长"

	name_label.text = title
	body_shape.color = Color(0.42, 0.42, 0.42, 1) if not _alive else body_color
	character_sprite.modulate = Color(0.42, 0.42, 0.42, 0.62) if not _alive else Color.WHITE
	name_label.modulate = Color(0.65, 0.65, 0.65, 1) if not _alive else Color.WHITE
	nearby_marker.color = Color(1, 0.84, 0.2, 1) if _is_current_speaker else Color(1, 0.9, 0.32, 1)
	nearby_marker.scale = Vector2(1.35, 1.35) if _is_current_speaker else Vector2.ONE
	turn_indicator.visible = _alive and _is_current_speaker
	# The badge represents current ownership, including the short transfer window
	# after a sheriff dies. It disappears only when backend state transfers or
	# destroys the badge.
	sheriff_badge.visible = _is_sheriff
	campaign_badge.visible = _alive and _campaign_status in ["candidate", "withdrawn"]
	campaign_badge.modulate = (
		Color(0.48, 0.52, 0.56, 1)
		if _campaign_status == "withdrawn"
		else Color(0.24, 0.68, 0.94, 1)
	)
	campaign_pk_label.visible = _alive and _campaign_status == "pk"


func _process(_delta: float) -> void:
	if turn_indicator.visible:
		turn_indicator.position.y = -56.0 + sin(Time.get_ticks_msec() / 180.0) * 4.0
	_process_movement(_delta)


func _init_movement() -> void:
	_ring_position = VENUE_MAP.RING_SEATS.get(npc_name, position)
	_rng.randomize()
	var personality: Dictionary = _npc_personality()
	var aggressiveness := float(personality.get("aggressiveness", 0.5))
	var cautiousness := float(personality.get("cautiousness", 0.5))
	_walk_speed = 34.0 + aggressiveness * 46.0
	_stay_seconds = 1.8 + cautiousness * 2.4
	_choose_walk_target(true)


func _npc_personality() -> Dictionary:
	return VENUE_MAP.NPC_PERSONALITIES.get(npc_name, {})


func _process_movement(delta: float) -> void:
	if not _roaming_enabled and not _locked:
		return
	if _move_state == "walk_to":
		var offset := _move_target - position
		var distance := offset.length()
		if distance < 4.0:
			position = _move_target
			_move_state = "stay"
			if _locked:
				return
			_stay_until_ms = Time.get_ticks_msec() + int(_stay_seconds * 1000.0)
			body_shape.position.y = 0.0
			return
		var direction := offset.normalized()
		position += direction * _walk_speed * delta
		position.x = clampf(
			position.x,
			VENUE_MAP.WORLD_RECT.position.x + 30.0,
			VENUE_MAP.WORLD_RECT.end.x - 30.0,
		)
		position.y = clampf(
			position.y,
			VENUE_MAP.WORLD_RECT.position.y + 30.0,
			VENUE_MAP.WORLD_RECT.end.y - 30.0,
		)
		var facing_right := direction.x >= 0.0
		if facing_right != _facing_right:
			_facing_right = facing_right
			body_shape.scale.x = 1.0 if facing_right else -1.0
		_walk_phase += delta * _walk_speed
		body_shape.position.y = -abs(sin(_walk_phase * 0.18)) * 2.5
	elif _move_state == "stay":
		if _locked:
			return
		if Time.get_ticks_msec() >= _stay_until_ms:
			_choose_walk_target()


func _choose_walk_target(initial: bool = false) -> void:
	if not _roaming_enabled:
		return
	var home_venue := VENUE_MAP.home_venue(npc_name)
	var home_center := VENUE_MAP.venue_center(home_venue)
	var roll := _rng.randf()
	if roll < 0.58 or initial:
		var radius := float(VENUE_MAP.VENUES.get(home_venue, {}).get("radius", 90.0))
		if VENUE_MAP.MINI_VENUES.has(home_venue):
			radius = float(VENUE_MAP.MINI_VENUES[home_venue].get("radius", 90.0))
		# Walk around the building rather than standing on top of it.
		_move_target = home_center + Vector2(
			(_rng.randf() - 0.5) * radius * 1.7,
			(_rng.randf() - 0.5) * radius * 1.7,
		)
	else:
		var targets: Array = VENUE_MAP.interest_targets(npc_name)
		_move_target = targets[_rng.randi_range(0, targets.size() - 1)]
	_move_state = "walk_to"


func lock_to_ring() -> void:
	_locked = true
	_move_target = _ring_position
	_move_state = "walk_to"


func lock_to_position(target: Vector2) -> void:
	_locked = true
	_move_target = target
	_move_state = "walk_to"


func unlock_roaming() -> void:
	if not _locked and _roaming_enabled:
		return
	_locked = false
	_roaming_enabled = true
	_choose_walk_target(true)


func set_roaming_enabled(enabled: bool) -> void:
	_roaming_enabled = enabled
	if not enabled:
		_move_state = "idle"
	elif not _locked:
		_choose_walk_target(true)


func set_poker_indicator(visible: bool) -> void:
	_poker_indicator_visible = visible
	poker_indicator.visible = visible


func _on_body_entered(body: Node) -> void:
	if body.is_in_group("player"):
		_player_nearby = true
		nearby_marker.visible = true
		speech_hint.visible = true


func _on_body_exited(body: Node) -> void:
	if body.is_in_group("player"):
		_player_nearby = false
		nearby_marker.visible = false
		speech_hint.visible = false
