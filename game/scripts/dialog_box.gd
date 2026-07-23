extends Control

signal message_submitted(message: String)
signal memory_view_requested
signal memory_reset_requested
signal config_reload_requested
signal closed

const MOVEMENT_ACTIONS := ["move_left", "move_right", "move_up", "move_down"]
const DIALOG_COMPACT_MAX_WINDOW_WIDTH := 1199
const DIALOG_WIDE_MIN_WINDOW_WIDTH := 1440
const DIALOG_WIDE_MIN_WINDOW_HEIGHT := 820
const PORTRAIT_PATHS := {
	"玩家": "res://assets/characters/player.svg",
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

@onready var panel: PanelContainer = $Panel
@onready var portrait: TextureRect = $Panel/Margin/VBox/Portrait
@onready var name_label: Label = $Panel/Margin/VBox/NameLabel
@onready var text_scroll: ScrollContainer = $Panel/Margin/VBox/DetailsScroll
@onready var memory_label: Label = $Panel/Margin/VBox/DetailsScroll/DetailsVBox/MemoryLabel
@onready var knowledge_label: Label = $Panel/Margin/VBox/DetailsScroll/DetailsVBox/KnowledgeLabel
@onready var text_label: Label = $Panel/Margin/VBox/DetailsScroll/DetailsVBox/TextLabel
@onready var message_input: LineEdit = $Panel/Margin/VBox/InputRow/MessageInput
@onready var send_button: Button = $Panel/Margin/VBox/InputRow/SendButton
@onready var view_memory_button: Button = $Panel/Margin/VBox/ActionRow/ViewMemoryButton
@onready var reset_memory_button: Button = $Panel/Margin/VBox/ActionRow/ResetMemoryButton
@onready var reload_config_button: Button = $Panel/Margin/VBox/ActionRow/ReloadConfigButton
@onready var validation_failure_button: Button = $Panel/Margin/VBox/ActionRow/ValidationFailureButton
@onready var close_button: Button = $Panel/Margin/VBox/ActionRow/CloseButton

var _dialog_text_before_failure := ""
var _validation_failure_data: Dictionary = {}
var _showing_validation_failure := false
var _focus_before_dialog: Control


func _ready() -> void:
	message_input.text_submitted.connect(_on_message_input_submitted)
	send_button.pressed.connect(_on_send_button_pressed)
	view_memory_button.pressed.connect(_on_view_memory_button_pressed)
	reset_memory_button.pressed.connect(_on_reset_memory_button_pressed)
	reload_config_button.pressed.connect(_on_reload_config_button_pressed)
	validation_failure_button.pressed.connect(_on_validation_failure_button_pressed)
	close_button.pressed.connect(hide_dialog)
	get_window().size_changed.connect(_update_responsive_layout)
	_configure_focus_navigation()
	_update_responsive_layout()


func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event.is_action_pressed("ui_cancel"):
		hide_dialog()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("ui_focus_prev"):
		_move_focus(-1)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("ui_focus_next"):
		_move_focus(1)
		get_viewport().set_input_as_handled()
	elif _handle_focus_direction(event):
		get_viewport().set_input_as_handled()


func _exit_tree() -> void:
	remove_from_group("dialog_open")


func show_dialog(npc_name: String, dialog_text: String) -> void:
	if not visible:
		var focus_owner := get_viewport().gui_get_focus_owner()
		_focus_before_dialog = focus_owner if focus_owner is Control else null
	name_label.text = _clean_display_text(npc_name)
	_set_portrait(npc_name)
	text_label.text = _clean_display_text(dialog_text)
	_dialog_text_before_failure = text_label.text
	_set_validation_failure({})
	memory_label.visible = false
	knowledge_label.visible = false
	visible = true
	add_to_group("dialog_open")
	call_deferred("_focus_dialog_primary")


func _set_portrait(character_name: String) -> void:
	var path := str(PORTRAIT_PATHS.get(character_name, ""))
	if path.is_empty() or not ResourceLoader.exists(path):
		portrait.texture = null
		portrait.visible = false
		return
	var texture = load(path)
	portrait.texture = texture if texture is Texture2D else null
	portrait.visible = portrait.texture != null


func show_response(
	npc_name: String,
	dialog_text: String,
	knowledge_titles: Variant = "",
	memory_count: int = 0,
	relationship_level: String = "",
	retrieval_mode: String = "",
	llm_used: bool = false,
	llm_provider: String = "rule",
	llm_fallback_reason: String = ""
) -> void:
	show_dialog(npc_name, dialog_text)
	if memory_count > 0:
		memory_label.text = "记忆次数：第 " + str(memory_count) + " 次对话"
		if not relationship_level.is_empty():
			memory_label.text += "\n关系阶段：" + relationship_level
		memory_label.visible = true

	var source_text := _format_knowledge_sources(knowledge_titles)
	if source_text.is_empty():
		knowledge_label.text = "未命中知识"
	else:
		knowledge_label.text = source_text
	if not retrieval_mode.is_empty():
		knowledge_label.text += "\n检索模式：" + _format_retrieval_mode(retrieval_mode)
	knowledge_label.text += "\n文本生成：" + _format_text_generator(llm_used, llm_provider)
	if not llm_used and not llm_fallback_reason.is_empty():
		knowledge_label.text += "\n回退原因：" + _format_llm_fallback_reason(llm_fallback_reason)
	knowledge_label.visible = true


func show_prompt(npc_name: String, prompt_text: String) -> void:
	show_dialog(npc_name, prompt_text)
	message_input.text = ""
	message_input.editable = true
	send_button.disabled = false
	view_memory_button.disabled = false
	reset_memory_button.disabled = false
	reload_config_button.disabled = false
	message_input.grab_focus()


func show_notice(npc_name: String, notice_text: String) -> void:
	show_dialog(npc_name, notice_text)
	message_input.text = ""
	message_input.release_focus()
	message_input.editable = false
	send_button.disabled = true
	view_memory_button.disabled = true
	reset_memory_button.disabled = true
	reload_config_button.disabled = true


func show_private_prompt(npc_name: String, prompt_text: String) -> void:
	show_dialog(npc_name, prompt_text)
	message_input.text = ""
	message_input.editable = true
	send_button.disabled = false
	view_memory_button.disabled = true
	reset_memory_button.disabled = true
	reload_config_button.disabled = true
	message_input.grab_focus()


func show_private_response(
	npc_name: String,
	response_text: String,
	knowledge_titles: Variant,
	retrieval_mode: String,
	llm_used: bool = false,
	llm_provider: String = "rule",
	llm_fallback_reason: String = "",
	llm_validation_failure: Variant = {}
) -> void:
	show_private_prompt(npc_name, response_text)
	var source_text := _format_knowledge_sources(knowledge_titles)
	knowledge_label.text = source_text if not source_text.is_empty() else "未命中可公开的检索来源"
	knowledge_label.text += "\n检索模式：" + _format_retrieval_mode(retrieval_mode)
	knowledge_label.text += "\n文本生成：" + _format_text_generator(llm_used, llm_provider)
	if not llm_used and not llm_fallback_reason.is_empty():
		knowledge_label.text += "\n回退原因：" + _format_llm_fallback_reason(llm_fallback_reason)
	knowledge_label.visible = true
	_set_validation_failure(llm_validation_failure)


func show_public_evidence_notice(
	npc_name: String,
	response_text: String,
	evidence_titles: Variant,
	retrieval_mode: String,
	llm_used: bool = false,
	llm_provider: String = "rule",
	llm_fallback_reason: String = "",
	llm_validation_failure: Variant = {}
) -> void:
	show_notice(npc_name, response_text)
	var source_text := _format_knowledge_sources(evidence_titles)
	if source_text.is_empty():
		knowledge_label.text = "本次未命中额外公开证据"
	else:
		knowledge_label.text = source_text.replace("命中知识：", "公开依据：")
	knowledge_label.text += "\n检索模式：" + _format_retrieval_mode(retrieval_mode)
	knowledge_label.text += "\n文本生成：" + _format_text_generator(llm_used, llm_provider)
	if not llm_used and not llm_fallback_reason.is_empty():
		knowledge_label.text += "\n回退原因：" + _format_llm_fallback_reason(llm_fallback_reason)
	knowledge_label.visible = true
	_set_validation_failure(llm_validation_failure)


func set_waiting() -> void:
	message_input.editable = false
	send_button.disabled = true
	view_memory_button.disabled = true
	reset_memory_button.disabled = true
	reload_config_button.disabled = true
	call_deferred("_repair_dialog_focus")


func set_ready_for_input() -> void:
	message_input.editable = true
	send_button.disabled = false
	view_memory_button.disabled = false
	reset_memory_button.disabled = false
	reload_config_button.disabled = false
	call_deferred("_focus_dialog_primary")


func hide_dialog(restore_focus: bool = true) -> void:
	if not visible:
		return
	var return_focus := _focus_before_dialog
	_focus_before_dialog = null
	visible = false
	message_input.text = ""
	message_input.release_focus()
	_release_movement_actions()
	memory_label.visible = false
	knowledge_label.visible = false
	_set_validation_failure({})
	remove_from_group("dialog_open")
	if restore_focus:
		call_deferred("_restore_focus_after_close", return_focus)
	else:
		get_viewport().gui_release_focus()
	closed.emit()


func _configure_focus_navigation() -> void:
	for node in find_children("*", "BaseButton", true, false):
		if node is Control:
			node.focus_mode = Control.FOCUS_ALL
	text_scroll.focus_mode = Control.FOCUS_ALL


func _update_responsive_layout() -> void:
	var window_size := get_window().size
	var viewport_size := get_viewport().get_visible_rect().size
	var profile := "default"
	if window_size.x <= DIALOG_COMPACT_MAX_WINDOW_WIDTH:
		profile = "compact"
	elif (
		window_size.x >= DIALOG_WIDE_MIN_WINDOW_WIDTH
		and window_size.y >= DIALOG_WIDE_MIN_WINDOW_HEIGHT
	):
		profile = "wide"
	var panel_width := 1120.0
	var panel_height := 480.0
	if profile == "compact":
		panel_width = 1000.0
	elif profile == "wide":
		panel_height = 500.0
	panel_width = minf(panel_width, maxf(320.0, viewport_size.x - 32.0))
	panel_height = minf(panel_height, maxf(360.0, viewport_size.y - 32.0))
	panel.anchor_left = 0.5
	panel.anchor_top = 1.0
	panel.anchor_right = 0.5
	panel.anchor_bottom = 1.0
	panel.offset_left = panel_width * -0.5
	panel.offset_right = panel_width * 0.5
	panel.offset_top = -panel_height - 16.0
	panel.offset_bottom = -16.0


func _focus_dialog_primary() -> void:
	if not visible:
		return
	if message_input.editable and not message_input.is_queued_for_deletion():
		message_input.grab_focus()
	else:
		close_button.grab_focus()


func _repair_dialog_focus() -> void:
	if not visible:
		return
	var focus_owner := get_viewport().gui_get_focus_owner()
	if focus_owner is Control and is_ancestor_of(focus_owner) and _is_focus_candidate(focus_owner):
		return
	_focus_dialog_primary()


func _move_focus(direction: int) -> void:
	var focusable := _focusable_controls()
	if focusable.is_empty():
		return
	var focus_owner := get_viewport().gui_get_focus_owner()
	var current_index := focusable.find(focus_owner)
	if current_index < 0:
		current_index = 0 if direction >= 0 else focusable.size() - 1
	else:
		current_index = posmod(current_index + direction, focusable.size())
	focusable[current_index].grab_focus()


func _handle_focus_direction(event: InputEvent) -> bool:
	var focus_owner := get_viewport().gui_get_focus_owner()
	if focus_owner is TextEdit:
		return false
	if focus_owner is LineEdit:
		if event.is_action_pressed("ui_left") or event.is_action_pressed("ui_right"):
			return false
	if focus_owner is OptionButton:
		if event.is_action_pressed("ui_up") or event.is_action_pressed("ui_down"):
			return false
	if focus_owner is ScrollContainer:
		if event.is_action_pressed("ui_up"):
			focus_owner.scroll_vertical = maxi(0, focus_owner.scroll_vertical - 48)
			return true
		if event.is_action_pressed("ui_down"):
			focus_owner.scroll_vertical += 48
			return true
	if event.is_action_pressed("ui_left") or event.is_action_pressed("ui_up"):
		_move_focus(-1)
		return true
	if event.is_action_pressed("ui_right") or event.is_action_pressed("ui_down"):
		_move_focus(1)
		return true
	return false


func _focusable_controls() -> Array[Control]:
	var controls: Array[Control] = []
	for node in find_children("*", "Control", true, false):
		if node is Control and _is_focus_candidate(node):
			controls.append(node)
	return controls


func _is_focus_candidate(control: Control) -> bool:
	if not control.is_visible_in_tree() or control.focus_mode == Control.FOCUS_NONE:
		return false
	if control is BaseButton and control.disabled:
		return false
	if control is LineEdit and not control.editable:
		return false
	return true


func _restore_focus_after_close(return_focus: Control) -> void:
	if (
		return_focus != null
		and is_instance_valid(return_focus)
		and _is_focus_candidate(return_focus)
	):
		return_focus.grab_focus()
		return
	get_viewport().gui_release_focus()


func is_open() -> bool:
	return visible


func has_text_focus() -> bool:
	return message_input.has_focus()


func _submit_message(raw_message: String) -> void:
	var message := raw_message.strip_edges()
	if message.is_empty():
		message = "你好"
	message_input.text = ""
	_lock_player_movement_until_release()
	message_submitted.emit(message)


func _on_message_input_submitted(message: String) -> void:
	_submit_message(message)


func _on_send_button_pressed() -> void:
	_submit_message(message_input.text)


func _on_view_memory_button_pressed() -> void:
	memory_view_requested.emit()


func _on_reset_memory_button_pressed() -> void:
	memory_reset_requested.emit()


func _on_reload_config_button_pressed() -> void:
	config_reload_requested.emit()


func _format_knowledge_sources(knowledge_titles: Variant) -> String:
	if typeof(knowledge_titles) == TYPE_ARRAY:
		if knowledge_titles.is_empty():
			return ""

		var lines: Array[String] = ["命中知识："]
		var index := 1
		for title in knowledge_titles:
			var title_text := _clean_display_text(str(title)).strip_edges()
			if title_text.is_empty():
				continue
			lines.append(str(index) + ". " + title_text)
			index += 1

		if lines.size() == 1:
			return ""

		var output := ""
		for line_index in range(lines.size()):
			if line_index > 0:
				output += "\n"
			output += lines[line_index]
		return output

	var title_text := _clean_display_text(str(knowledge_titles)).strip_edges()
	if title_text.is_empty():
		return ""
	return "命中知识：\n1. " + title_text


func _format_retrieval_mode(retrieval_mode: String) -> String:
	return "向量 + 关键词" if retrieval_mode == "hybrid" else "关键词降级"


func _format_text_generator(llm_used: bool, llm_provider: String) -> String:
	return "LLM（" + llm_provider + "）" if llm_used else "规则模板"


func _format_llm_fallback_reason(reason: String) -> String:
	var normalized := reason.to_lower()
	if "llm is disabled" in normalized:
		return "全局 LLM 未启用"
	if "mock provider" in normalized:
		return "Mock 模式使用规则回复"
	if "disabled for this game" in normalized:
		return "本局未启用 LLM"
	if "not fully configured" in normalized:
		return "LLM 配置不完整"
	if "httpstatuserror" in normalized or "timeout" in normalized or "network" in normalized:
		return "LLM 服务暂时不可用，重试后仍失败"
	if "json" in normalized or "token limit" in normalized:
		return "LLM 返回格式异常，重试后仍失败"
	if "validation failed after 5 attempts" in normalized:
		return "LLM 五次回答均未通过规则校验"
	if "replacement character" in normalized:
		return "LLM 回答包含异常字符"
	if "resident chat" in normalized:
		return "常驻居民回复未通过轻量格式检查"
	return "LLM 重试后仍未获得可用回答"


func _clean_display_text(value: String) -> String:
	return value.replace(String.chr(0xFFFD), "?")


func _release_movement_actions() -> void:
	for action in MOVEMENT_ACTIONS:
		if InputMap.has_action(action):
			Input.action_release(action)
	_lock_player_movement_until_release()


func _lock_player_movement_until_release() -> void:
	for player in get_tree().get_nodes_in_group("player"):
		if player.has_method("lock_movement_until_release"):
			player.call("lock_movement_until_release")


func _set_validation_failure(value: Variant) -> void:
	_validation_failure_data = value.duplicate(true) if typeof(value) == TYPE_DICTIONARY else {}
	_showing_validation_failure = false
	validation_failure_button.visible = (
		_validation_failure_data.has("attempts")
		and typeof(_validation_failure_data.get("attempts")) == TYPE_ARRAY
		and not _validation_failure_data.get("attempts", []).is_empty()
	)
	validation_failure_button.text = "LLM校验失败查看"


func _on_validation_failure_button_pressed() -> void:
	_showing_validation_failure = not _showing_validation_failure
	if not _showing_validation_failure:
		text_label.text = _dialog_text_before_failure
		text_scroll.scroll_vertical = 0
		validation_failure_button.text = "LLM校验失败查看"
		return

	var lines: Array[String] = ["DeepSeek 五轮校验记录（调试模式，可能包含隐藏身份）"]
	var attempts = _validation_failure_data.get("attempts", [])
	for attempt in attempts:
		if typeof(attempt) != TYPE_DICTIONARY:
			continue
		var attempt_number := int(attempt.get("attempt", lines.size()))
		var output := _clean_display_text(str(attempt.get("text", "[无返回内容]")))
		var reason := _format_validation_reason(str(attempt.get("rejection_reason", "未知原因")))
		lines.append("第 " + str(attempt_number) + " 次：" + output + "\n未通过原因：" + reason)
	text_label.text = "\n\n".join(lines)
	text_scroll.scroll_vertical = 0
	validation_failure_button.text = "返回 NPC 对话"


func _format_validation_reason(reason: String) -> String:
	var normalized := reason.to_lower()
	if "omitted the rule-selected target" in normalized:
		return "遗漏规则指定的目标"
	if "omitted a required public claim" in normalized:
		return "遗漏必须保留的公开声明"
	if "introduced a new character" in normalized:
		return "加入了规则文本中没有的角色"
	if "unsupported role claim" in normalized:
		return "加入了未经规则批准的身份声明"
	if "hidden wolf-team" in normalized or "private information" in normalized:
		return "包含不应公开的隐藏信息"
	if "length is invalid" in normalized:
		return "文本为空或长度不符合要求"
	if "replacement character" in normalized:
		return "文本包含异常字符"
	if "json" in normalized:
		return "返回格式不是有效 JSON"
	if "timeout" in normalized or "network" in normalized:
		return "网络请求失败或超时"
	return reason
