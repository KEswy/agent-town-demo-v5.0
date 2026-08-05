extends Node2D

const CHAT_URL := "http://127.0.0.1:8000/chat"
const MEMORY_URL := "http://127.0.0.1:8000/memory"
const CONFIG_RELOAD_URL := "http://127.0.0.1:8000/admin/reload-config"
const WOLF_GAME_START_URL := "http://127.0.0.1:8000/api/game/start"
const WOLF_GAME_STATE_URL_PREFIX := "http://127.0.0.1:8000/api/game/"
const WOLF_NIGHT_ACTION_URL := "http://127.0.0.1:8000/api/night/action"
const WOLF_NIGHT_RESOLVE_URL := "http://127.0.0.1:8000/api/night/resolve"
const WOLF_HUNTER_SHOT_URL := "http://127.0.0.1:8000/api/hunter/shot"
const WOLF_PLAYER_SPEECH_URL := "http://127.0.0.1:8000/api/day/player-speech"
const WOLF_PLAYER_SPEECH_PREVIEW_URL := "http://127.0.0.1:8000/api/player-speech/preview"
const WOLF_NPC_SPEECH_URL := "http://127.0.0.1:8000/api/day/npc-speech"
const WOLF_NPC_SPEECHES_BATCH_URL := "http://127.0.0.1:8000/api/day/npc-speeches-batch"
const WOLF_END_FREE_ACTIVITY_URL := "http://127.0.0.1:8000/api/day/end-free-activity"
const WOLF_PRIVATE_CHAT_URL := "http://127.0.0.1:8000/api/day/private-chat"
const WOLF_SHERIFF_SIGNUP_URL := "http://127.0.0.1:8000/api/sheriff/signup"
const WOLF_SHERIFF_PLAYER_SPEECH_URL := "http://127.0.0.1:8000/api/sheriff/player-speech"
const WOLF_SHERIFF_NPC_SPEECH_URL := "http://127.0.0.1:8000/api/sheriff/npc-speech"
const WOLF_SHERIFF_WITHDRAW_URL := "http://127.0.0.1:8000/api/sheriff/withdraw"
const WOLF_SHERIFF_VOTE_URL := "http://127.0.0.1:8000/api/sheriff/vote"
const WOLF_SHERIFF_MEETING_ORDER_URL := "http://127.0.0.1:8000/api/sheriff/meeting-order"
const WOLF_SHERIFF_NOMINATE_URL := "http://127.0.0.1:8000/api/sheriff/nominate"
const WOLF_SHERIFF_TRANSFER_URL := "http://127.0.0.1:8000/api/sheriff/transfer"
const WOLF_COMBINED_VOTE_URL := "http://127.0.0.1:8000/api/vote/submit-and-resolve"
const WOLF_RECOVERY_STATUS_URL := "http://127.0.0.1:8000/api/game/recovery-status"
const KNOWLEDGE_SEARCH_URL := "http://127.0.0.1:8000/knowledge/search"
const NPCS_URL := "http://127.0.0.1:8000/npcs"
const SPECTATE_GAMES_URL := "http://127.0.0.1:8000/api/spectate/active-games"
const SPECTATE_URL_PREFIX := "http://127.0.0.1:8000/api/spectate/"
const POKER_TABLE_URL := "http://127.0.0.1:8000/api/poker/table"
const POKER_URL_PREFIX := "http://127.0.0.1:8000/api/poker/table/"
const SESSION_SETTINGS_PATH := "user://agent_town_session.cfg"
const STATS_PATH := "user://agent_town_stats.json"
const ACHIEVEMENTS_PATH := "user://agent_town_achievements.cfg"
const ACHIEVEMENTS_SECTION := "achievements"
const SESSION_SETTINGS_SECTION := "session"
const PLAYER_ID := "player"
const RESPONSIVE_LAYOUT_SCHEMA_VERSION := "agent_town_responsive_layout.v1"
const FOCUS_NAVIGATION_SCHEMA_VERSION := "agent_town_focus_navigation.v1"
const RESPONSIVE_COMPACT_MAX_WINDOW_WIDTH := 1199
const RESPONSIVE_WIDE_MIN_WINDOW_WIDTH := 1440
const RESPONSIVE_WIDE_MIN_WINDOW_HEIGHT := 820
const RESPONSIVE_LAYOUT_PROFILES := {
	"compact": {
		"hud_width": 448.0,
		"wolf_menu_width": 420.0,
		"wolf_height_ratio": 0.66,
		"intel_panel_width": 520.0,
		"intel_columns": 2,
		"card_min_width": 160.0,
		"identity_width": 270.0,
		"setup_width": 560.0,
		"summary_margin_horizontal": 20.0,
		"summary_margin_vertical": 16.0,
		"history_min_height": 320.0,
	},
	"default": {
		"hud_width": 540.0,
		"wolf_menu_width": 440.0,
		"wolf_height_ratio": 0.62,
		"intel_panel_width": 600.0,
		"intel_columns": 3,
		"card_min_width": 160.0,
		"identity_width": 294.0,
		"setup_width": 600.0,
		"summary_margin_horizontal": 48.0,
		"summary_margin_vertical": 36.0,
		"history_min_height": 420.0,
	},
	"wide": {
		"hud_width": 620.0,
		"wolf_menu_width": 480.0,
		"wolf_height_ratio": 0.68,
		"intel_panel_width": 736.0,
		"intel_columns": 4,
		"card_min_width": 160.0,
		"identity_width": 294.0,
		"setup_width": 640.0,
		"summary_margin_horizontal": 64.0,
		"summary_margin_vertical": 48.0,
		"history_min_height": 440.0,
	},
}
const UI_FOCUS_SCOPE_WORLD := "WORLD"
const UI_FOCUS_SCOPE_PANEL := "PANEL"
const UI_FOCUS_SCOPE_TEXT_ENTRY := "TEXT_ENTRY"
const UI_FOCUS_SCOPE_MODAL := "MODAL"
const WOLF_MENU_TOP := 86.0
const WOLF_MENU_COLLAPSED_HEIGHT := 46.0
const WOLF_MENU_MIN_EXPANDED_HEIGHT := 320.0
const WOLF_MENU_MAX_EXPANDED_HEIGHT := 520.0
const IDENTITY_PANEL_COLLAPSED_BOTTOM := 184.0
const IDENTITY_PANEL_EXPANDED_BOTTOM := 500.0
const ONBOARDING_SCHEMA_VERSION := "agent_town_onboarding.v1"
const ONBOARDING_SETTINGS_PATH := "user://agent_town_onboarding.cfg"
const ONBOARDING_SETTINGS_SECTION := "onboarding"
const ONBOARDING_STATUS_VALUES := ["inactive", "active", "completed", "dismissed"]
const ONBOARDING_STEPS := [
	{
		"step_id": "identity_and_scope",
		"trigger_kind": "full_state",
		"phases": [],
		"roles": [],
		"information_scope": "player_private",
		"title": "先认清自己的身份",
		"body": "身份、阵营、夜间结果和仅限你的技能状态来自 Python 规则状态。它们不会因为打开引导而公开，也不能被 LLM 改写。",
	},
	{
		"step_id": "night_skill",
		"trigger_kind": "phase",
		"phases": ["NIGHT"],
		"roles": ["werewolf", "seer", "witch", "hunter", "guard", "villager"],
		"information_scope": "player_private",
		"title": "夜间技能由 Python 判定",
		"body": "只提交当前界面允许的行动和目标。可用次数、合法目标、行动结果与是否进入猎人开枪窗口都由 Python 决定。",
	},
	{
		"step_id": "sheriff_flow",
		"trigger_kind": "phase",
		"phases": ["SHERIFF_SIGNUP", "SHERIFF_SPEECH", "SHERIFF_WITHDRAWAL", "SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE", "MEETING_ORDER", "SHERIFF_NOMINATION", "BADGE_TRANSFER"],
		"roles": [],
		"information_scope": "public_unverified",
		"title": "警长流程是公开行动",
		"body": "报名、竞选发言、退水、警长投票、PK、归票和警徽移交都会进入公开流程。公开身份声明只是场上说法，在规则确认前不等于真实身份。",
	},
	{
		"step_id": "public_speech",
		"trigger_kind": "player_speech_turn",
		"phases": ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH", "DAY_MEETING"],
		"roles": [],
		"information_scope": "public_action",
		"title": "发言先预览，再确认提交",
		"body": "预览只解释这段话会形成哪些公开意图、目标和声明，不会推进阶段。确认后仍由 Python 校验事实、权限和当前状态；自由文本不能绕过规则。",
	},
	{
		"step_id": "private_chat",
		"trigger_kind": "alive_phase",
		"phases": ["FREE_ACTIVITY"],
		"roles": [],
		"information_scope": "player_private",
		"title": "私聊会影响 NPC，但不会自动公开",
		"body": "自由活动时靠近 NPC 并按 E、Enter 或 Space 私聊。内容会进入你与该 NPC 的私密互动记录，并可能影响其后续判断；它不会自动变成公开事实。",
	},
	{
		"step_id": "exile_vote",
		"trigger_kind": "alive_phase",
		"phases": ["VOTE"],
		"roles": [],
		"information_scope": "public_action",
		"title": "放逐票一次提交并统一结算",
		"body": "选择目标并写下基于场上信息的理由。提交后 Python 同时生成 NPC 票、计算警长权重、处理平票或出局，并判断是否结束游戏。",
	},
	{
		"step_id": "post_game_review",
		"trigger_kind": "phase",
		"phases": ["GAME_OVER"],
		"roles": [],
		"information_scope": "post_game_truth",
		"title": "赛后才能解锁身份真值",
		"body": "游戏结束后点击“复盘”，查看完整角色、公开时间线和决定解释。赛后真值只用于复盘，不会倒灌进进行中的 NPC 决策。",
	},
]
const ONBOARDING_ROLE_GUIDES := {
	"werewolf": {
		"goal": "与狼队友协作，让狼人阵营达到 Python 判定的胜利条件。",
		"skill": "夜间选择合法袭击目标；狼队友名单仅狼人玩家可见。",
		"private_note": "你的狼人身份、狼队友和夜间选择仅你可见，不会自动公开。",
	},
	"seer": {
		"goal": "帮助好人识别狼人并保护关键公开信息链。",
		"skill": "夜间查验一名合法目标；查验结果先进入你的私密记录。",
		"private_note": "查验结果只有你知道，是否以及如何公开由你在合法发言阶段决定。",
	},
	"witch": {
		"goal": "利用有限药品帮助好人控制夜间损失。",
		"skill": "夜间可用行动、刀口信息和药品余量以 Python 返回的当前状态为准。",
		"private_note": "刀口、药品状态和你的选择仅你可见，不会自动公开。",
	},
	"hunter": {
		"goal": "通过公开判断帮助好人，并在合法开枪窗口作出选择。",
		"skill": "平时没有主动夜间按钮；只有 Python 打开猎人窗口时才可开枪或放弃。",
		"private_note": "是否可以开枪由规则状态决定，身份不会因引导而公开。",
	},
	"guard": {
		"goal": "用守护行动帮助好人减少夜间损失。",
		"skill": "夜间只可选择 Python 当前允许的守护目标。",
		"private_note": "守护目标和行动历史仅你可见，不会自动公开。",
	},
	"villager": {
		"goal": "依靠公开发言、投票和承诺变化帮助好人找出狼人。",
		"skill": "没有主动夜间技能；夜间按界面提示等待规则结算。",
		"private_note": "你只知道自己的村民身份，不能读取其他角色的隐藏身份。",
	},
	"idiot": {
		"goal": "用自己的翻牌技能保护好人阵营的放逐轮次。",
		"skill": "白天被投票放逐时自动翻牌免死一次；翻牌后可以继续发言，但不能再投票。",
		"private_note": "翻牌只会在被放逐时公开触发；夜间被袭击仍会正常出局。",
	},
}
const BADGE_FLOW_REVISION_REASON_OPTIONS := [
	["目标已出局", "target_eliminated"],
	["出现公开身份信息", "role_reveal"],
	["场上出现新对跳", "new_counterclaim"],
	["票型发生变化", "vote_shift"],
	["发言或站边变化", "speech_change"],
	["发现更高价值验人", "higher_value"],
	["避免警徽流过于可预测", "avoid_predictability"],
	["其他公开场上理由", "other_public_reason"],
]
const CHARACTER_SKIN_PATHS := {
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
}

@onready var dialog_box: Control = $UI/DialogBox
@onready var player: CharacterBody2D = $Player
@onready var town_background: Node2D = $TownBackground
@onready var phase_hud: Control = $UI/PhaseHUD
@onready var phase_title_label: Label = $UI/PhaseHUD/Panel/Margin/Row/TitleLabel
@onready var wolf_menu_summary_label: Label = $UI/PhaseHUD/Panel/Margin/Row/MenuSummaryLabel
@onready var refresh_state_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/RefreshButton
@onready var review_game_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/ReviewButton
@onready var intel_toggle_button: Button = $UI/PhaseHUD/Panel/Margin/Row/IntelToggleButton
@onready var guide_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/GuideButton
@onready var setup_toggle_button: Button = $UI/PhaseHUD/Panel/Margin/Row/SetupToggleButton
@onready var identity_panel: PanelContainer = $UI/IdentityPanel
@onready var player_identity_block: VBoxContainer = $UI/IdentityPanel/Margin/PlayerIdentityBlock
@onready var player_role_label: Label = $UI/IdentityPanel/Margin/PlayerIdentityBlock/RoleLabel
@onready var wolf_teammates_label: Label = $UI/IdentityPanel/Margin/PlayerIdentityBlock/WolfTeammatesLabel
@onready var key_info_toggle_button: Button = $UI/IdentityPanel/Margin/PlayerIdentityBlock/KeyInfoToggleButton
@onready var key_info_content_panel: PanelContainer = $UI/IdentityPanel/Margin/PlayerIdentityBlock/KeyInfoContentPanel
@onready var key_info_safety_label: Label = $UI/IdentityPanel/Margin/PlayerIdentityBlock/KeyInfoContentPanel/Margin/VBox/SafetyLabel
@onready var key_info_scroll: ScrollContainer = $UI/IdentityPanel/Margin/PlayerIdentityBlock/KeyInfoContentPanel/Margin/VBox/ScrollContainer
@onready var key_info_label: Label = $UI/IdentityPanel/Margin/PlayerIdentityBlock/KeyInfoContentPanel/Margin/VBox/ScrollContainer/KeyInfoLabel
@onready var wolf_panel: Control = $UI/WolfPanel
@onready var wolf_content_panel: PanelContainer = $UI/WolfPanel/ContentPanel
@onready var wolf_scroll_container: ScrollContainer = $UI/WolfPanel/ContentPanel/ScrollContainer
@onready var wolf_menu_toggle_button: Button = $UI/WolfPanel/HeaderPanel/HeaderMargin/HeaderRow/ToggleButton
@onready var wolf_status_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/StatusLabel
@onready var wolf_game_info_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/GameInfoLabel
@onready var sheriff_overview_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffOverviewLabel
@onready var night_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionLabel
@onready var night_action_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow
@onready var night_action_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/NightActionOption
@onready var night_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/NightTargetOption
@onready var submit_night_action_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/SubmitNightActionButton
@onready var resolve_night_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/ResolveNightButton
@onready var hunter_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionLabel
@onready var hunter_action_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow
@onready var hunter_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow/HunterTargetOption
@onready var hunter_shoot_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow/HunterShootButton
@onready var hunter_pass_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow/HunterPassButton
@onready var sheriff_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffActionLabel
@onready var sheriff_choice_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffChoiceRow
@onready var sheriff_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffChoiceRow/SheriffOption
@onready var sheriff_action_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffChoiceRow/SheriffActionButton
@onready var sheriff_withdrawal_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffWithdrawalRow
@onready var sheriff_continue_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffWithdrawalRow/ContinueButton
@onready var sheriff_withdraw_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffWithdrawalRow/WithdrawButton
@onready var sheriff_speech_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffSpeechRow/SheriffSpeechInput
@onready var sheriff_speech_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffSpeechRow/SheriffSpeechButton
@onready var sheriff_speech_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffSpeechRow
@onready var badge_flow_panel: PanelContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel
@onready var badge_flow_collapse_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/HeaderRow/CollapseButton
@onready var badge_flow_include_toggle: CheckButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/HeaderRow/IncludeToggle
@onready var badge_flow_current_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/CurrentLabel
@onready var badge_flow_form_grid: GridContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid
@onready var badge_flow_primary_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid/PrimaryOption
@onready var badge_flow_secondary_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid/SecondaryOption
@onready var badge_flow_good_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid/GoodBadgeOption
@onready var badge_flow_wolf_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid/WolfBadgeOption
@onready var badge_flow_reason_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid/ReasonOption
@onready var badge_flow_reason_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/FormGrid/ReasonTargetOption
@onready var badge_flow_hint_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/BadgeFlowPanel/Margin/VBox/HintLabel
@onready var day_speech_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechLabel
@onready var temporary_nomination_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/TemporaryNominationRow
@onready var temporary_nomination_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/TemporaryNominationRow/TemporaryNominationOption
@onready var day_speech_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow
@onready var player_speech_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/PlayerSpeechInput
@onready var submit_speech_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/SubmitSpeechButton
@onready var end_free_activity_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/EndFreeActivityButton
@onready var fast_forward_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/FastForwardButton
@onready var speech_preview_panel: PanelContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SpeechPreviewPanel
@onready var speech_preview_summary: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SpeechPreviewPanel/Margin/VBox/Summary
@onready var speech_preview_edit_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SpeechPreviewPanel/Margin/VBox/Actions/EditButton
@onready var speech_preview_confirm_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SpeechPreviewPanel/Margin/VBox/Actions/ConfirmButton
@onready var vote_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionLabel
@onready var vote_reason_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteReasonInput
@onready var vote_action_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionRow
@onready var vote_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionRow/VoteTargetOption
@onready var submit_vote_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionRow/SubmitVoteButton
@onready var vote_result_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteResultLabel
@onready var intel_panel: Control = $UI/IntelPanel
@onready var intel_close_button: Button = $UI/IntelPanel/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var intel_tabs: TabContainer = $UI/IntelPanel/Panel/Margin/VBox/Tabs
@onready var character_grid: GridContainer = $UI/IntelPanel/Panel/Margin/VBox/Tabs/Roster/Margin/CharacterGrid
@onready var public_log_label: Label = $UI/IntelPanel/Panel/Margin/VBox/Tabs/PublicRecords/Margin/PublicLogLabel
@onready var player_action_history_block: VBoxContainer = $UI/IntelPanel/Panel/Margin/VBox/Tabs/MyRecords/PlayerActionHistoryBlock
@onready var player_action_history_text: TextEdit = $UI/IntelPanel/Panel/Margin/VBox/Tabs/MyRecords/PlayerActionHistoryBlock/HistoryText
@onready var game_setup_overlay: Control = $UI/GameSetupOverlay
@onready var game_setup_panel: PanelContainer = $UI/GameSetupOverlay/Panel
@onready var setup_close_button: Button = $UI/GameSetupOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var setup_status_label: Label = $UI/GameSetupOverlay/Panel/Margin/VBox/SetupStatusLabel
@onready var player_name_input: LineEdit = $UI/GameSetupOverlay/Panel/Margin/VBox/PlayerNameRow/PlayerNameInput
@onready var start_game_button: Button = $UI/GameSetupOverlay/Panel/Margin/VBox/ActionRow/StartGameButton
@onready var continue_game_button: Button = $UI/GameSetupOverlay/Panel/Margin/VBox/ActionRow/ContinueGameButton
@onready var sound_enabled_toggle: CheckButton = $UI/GameSetupOverlay/Panel/Margin/VBox/SoundRow/SoundEnabledToggle
@onready var knowledge_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/RuleButton
@onready var knowledge_overlay: Control = $UI/KnowledgeOverlay
@onready var knowledge_search_input: LineEdit = $UI/KnowledgeOverlay/Panel/Margin/VBox/SearchRow/SearchInput
@onready var knowledge_search_button: Button = $UI/KnowledgeOverlay/Panel/Margin/VBox/SearchRow/SearchButton
@onready var knowledge_close_button: Button = $UI/KnowledgeOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var knowledge_status_label: Label = $UI/KnowledgeOverlay/Panel/Margin/VBox/StatusLabel
@onready var knowledge_results_list: VBoxContainer = $UI/KnowledgeOverlay/Panel/Margin/VBox/ResultsScroll/ResultsList
@onready var knowledge_search_request: HTTPRequest = $KnowledgeSearchRequest
@onready var stats_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/StatsButton
@onready var menu_button: Button = $UI/PhaseHUD/Panel/Margin/Row/MenuButton
@onready var menu_overlay: Control = $UI/MenuOverlay
@onready var menu_close_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var archive_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/ArchiveButton
@onready var archive_overlay: Control = $UI/ArchiveOverlay
@onready var archive_close_button: Button = $UI/ArchiveOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var archive_status_label: Label = $UI/ArchiveOverlay/Panel/Margin/VBox/StatusLabel
@onready var archive_list_box: VBoxContainer = $UI/ArchiveOverlay/Panel/Margin/VBox/ListScroll/ListBox
@onready var archive_request: HTTPRequest = $ArchiveRequest
@onready var load_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/LoadButton
@onready var load_overlay: Control = $UI/LoadOverlay
@onready var load_close_button: Button = $UI/LoadOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var load_slot_info_labels: Array = [
	$UI/LoadOverlay/Panel/Margin/VBox/Slot1Row/SlotInfoLabel,
	$UI/LoadOverlay/Panel/Margin/VBox/Slot2Row/SlotInfoLabel,
	$UI/LoadOverlay/Panel/Margin/VBox/Slot3Row/SlotInfoLabel,
]
@onready var load_slot_buttons: Array = [
	$UI/LoadOverlay/Panel/Margin/VBox/Slot1Row/LoadSlotButton,
	$UI/LoadOverlay/Panel/Margin/VBox/Slot2Row/LoadSlotButton,
	$UI/LoadOverlay/Panel/Margin/VBox/Slot3Row/LoadSlotButton,
]
@onready var spectate_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/SpectateButton
@onready var spectate_overlay: Control = $UI/SpectateOverlay
@onready var spectate_close_button: Button = $UI/SpectateOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var spectate_refresh_button: Button = $UI/SpectateOverlay/Panel/Margin/VBox/HeaderRow/RefreshButton
@onready var spectate_game_select: OptionButton = $UI/SpectateOverlay/Panel/Margin/VBox/HeaderRow/GameSelect
@onready var spectate_phase_label: Label = $UI/SpectateOverlay/Panel/Margin/VBox/Body/LeftPanel/Margin/VBox/StatusRow/PhaseLabel
@onready var spectate_day_label: Label = $UI/SpectateOverlay/Panel/Margin/VBox/Body/LeftPanel/Margin/VBox/StatusRow/DayLabel
@onready var spectate_winner_label: Label = $UI/SpectateOverlay/Panel/Margin/VBox/Body/LeftPanel/Margin/VBox/StatusRow/WinnerLabel
@onready var spectate_character_grid: GridContainer = $UI/SpectateOverlay/Panel/Margin/VBox/Body/LeftPanel/Margin/VBox/CharacterScroll/CharacterGrid
@onready var spectate_timeline_list: VBoxContainer = $UI/SpectateOverlay/Panel/Margin/VBox/Body/RightPanel/Margin/VBox/TimelineScroll/TimelineList
@onready var spectate_games_request: HTTPRequest = $SpectateGamesRequest
@onready var spectate_request: HTTPRequest = $SpectateRequest
@onready var spectate_poll_timer: Timer = $SpectatePollTimer
@onready var achievement_toast: Control = $UI/AchievementToast
@onready var achievement_toast_label: Label = $UI/AchievementToast/Panel/Margin/Label
@onready var poker_overlay: Control = $UI/PokerTableOverlay
@onready var poker_close_button: Button = $UI/PokerTableOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var poker_result_label: Label = $UI/PokerTableOverlay/Panel/Margin/VBox/HeaderRow/ResultLabel
@onready var poker_phase_label: Label = $UI/PokerTableOverlay/Panel/Margin/VBox/StatusRow/PhaseLabel
@onready var poker_pot_label: Label = $UI/PokerTableOverlay/Panel/Margin/VBox/StatusRow/PotLabel
@onready var poker_hand_label: Label = $UI/PokerTableOverlay/Panel/Margin/VBox/StatusRow/HandLabel
@onready var poker_community_label: Label = $UI/PokerTableOverlay/Panel/Margin/VBox/TablePanel/Margin/VBox/CommunityLabel
@onready var poker_players_list: VBoxContainer = $UI/PokerTableOverlay/Panel/Margin/VBox/TablePanel/Margin/VBox/PlayersList
@onready var poker_fold_button: Button = $UI/PokerTableOverlay/Panel/Margin/VBox/ActionRow/FoldButton
@onready var poker_check_call_button: Button = $UI/PokerTableOverlay/Panel/Margin/VBox/ActionRow/CheckCallButton
@onready var poker_raise_button: Button = $UI/PokerTableOverlay/Panel/Margin/VBox/ActionRow/RaiseButton
@onready var poker_all_in_button: Button = $UI/PokerTableOverlay/Panel/Margin/VBox/ActionRow/AllInButton
@onready var poker_raise_value_label: Label = $UI/PokerTableOverlay/Panel/Margin/VBox/ActionRow/RaiseBox/RaiseValueLabel
@onready var poker_raise_slider: HSlider = $UI/PokerTableOverlay/Panel/Margin/VBox/ActionRow/RaiseBox/RaiseSlider
@onready var poker_next_hand_button: Button = $UI/PokerTableOverlay/Panel/Margin/VBox/NextHandButton
@onready var poker_request: HTTPRequest = $PokerRequest
@onready var poker_hall_door: Area2D = $PokerHallDoor
@onready var board_game_door: Area2D = $BoardGameDoor
@onready var venue_props: Node2D = $VenueProps
@onready var highlights_label: Label = $UI/GameSummaryOverlay/Panel/Margin/VBox/HighlightsLabel
@onready var export_review_button: Button = $UI/GameSummaryOverlay/Panel/Margin/VBox/HeaderRow/ExportReviewButton
@onready var export_stats_button: Button = $UI/StatsOverlay/Panel/Margin/VBox/HeaderRow/ExportStatsButton
@onready var replay_button: Button = $UI/GameSummaryOverlay/Panel/Margin/VBox/HeaderRow/ReplayButton
@onready var replay_overlay: Control = $UI/ReplayOverlay
@onready var replay_close_button: Button = $UI/ReplayOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var replay_progress_label: Label = $UI/ReplayOverlay/Panel/Margin/VBox/ProgressLabel
@onready var replay_body_label: Label = $UI/ReplayOverlay/Panel/Margin/VBox/BodyScroll/BodyLabel
@onready var replay_prev_button: Button = $UI/ReplayOverlay/Panel/Margin/VBox/NavRow/PrevButton
@onready var replay_play_button: Button = $UI/ReplayOverlay/Panel/Margin/VBox/NavRow/PlayButton
@onready var replay_next_button: Button = $UI/ReplayOverlay/Panel/Margin/VBox/NavRow/NextButton
@onready var stats_overlay: Control = $UI/StatsOverlay
@onready var stats_close_button: Button = $UI/StatsOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var stats_body_list: VBoxContainer = $UI/StatsOverlay/Panel/Margin/VBox/BodyScroll/BodyList
@onready var bgm_volume_slider: HSlider = $UI/GameSetupOverlay/Panel/Margin/VBox/SoundRow/BGMVolumeBox/BGMVolumeSlider
@onready var sfx_volume_slider: HSlider = $UI/GameSetupOverlay/Panel/Margin/VBox/SoundRow/SFXVolumeBox/SFXVolumeSlider
@onready var language_option: OptionButton = $UI/GameSetupOverlay/Panel/Margin/VBox/LanguageRow/LanguageOption
@onready var slot_option: OptionButton = $UI/GameSetupOverlay/Panel/Margin/VBox/SlotRow/SlotOption
@onready var tutorial_hints_toggle: CheckButton = $UI/GameSetupOverlay/Panel/Margin/VBox/TutorialHintRow/TutorialHintsToggle
@onready var save_button: Button = $UI/MenuOverlay/Panel/Margin/VBox/SaveButton
@onready var save_game_request: HTTPRequest = $SaveGameRequest
@onready var player_role_option: OptionButton = $UI/GameSetupOverlay/Panel/Margin/VBox/PlayerRoleRow/PlayerRoleOption
@onready var variant_option: OptionButton = $UI/GameSetupOverlay/Panel/Margin/VBox/VariantRow/VariantOption
@onready var npc_policy_option: OptionButton = $UI/GameSetupOverlay/Panel/Margin/VBox/NpcPolicyRow/NpcPolicyOption
@onready var llm_enabled_toggle: CheckButton = $UI/GameSetupOverlay/Panel/Margin/VBox/LLMSettingsRow/LLMEnabledToggle
@onready var llm_settings_hint: Label = $UI/GameSetupOverlay/Panel/Margin/VBox/LLMSettingsRow/LLMSettingsHint
@onready var llm_validation_toggle: CheckButton = $UI/GameSetupOverlay/Panel/Margin/VBox/LLMValidationRow/LLMValidationToggle
@onready var game_summary_overlay: Control = $UI/GameSummaryOverlay
@onready var game_summary_panel: PanelContainer = $UI/GameSummaryOverlay/Panel
@onready var game_summary_close_button: Button = $UI/GameSummaryOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var game_summary_winner_label: Label = $UI/GameSummaryOverlay/Panel/Margin/VBox/WinnerLabel
@onready var game_summary_tabs: TabContainer = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs
@onready var game_summary_character_list: VBoxContainer = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs/CharacterReview/Margin/CharacterList
@onready var game_summary_timeline_label: Label = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs/TimelineReview/Margin/TimelineLabel
@onready var game_summary_review_label: Label = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs/ExplainableReview/Margin/ReviewLabel
@onready var onboarding_overlay: Control = $UI/OnboardingOverlay
@onready var onboarding_panel: PanelContainer = $UI/OnboardingOverlay/Panel
@onready var onboarding_progress_label: Label = $UI/OnboardingOverlay/Panel/Margin/VBox/HeaderRow/ProgressLabel
@onready var onboarding_close_button: Button = $UI/OnboardingOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var onboarding_title_label: Label = $UI/OnboardingOverlay/Panel/Margin/VBox/TitleLabel
@onready var onboarding_scope_label: Label = $UI/OnboardingOverlay/Panel/Margin/VBox/ScopeLabel
@onready var onboarding_body_scroll: ScrollContainer = $UI/OnboardingOverlay/Panel/Margin/VBox/BodyScroll
@onready var onboarding_body_label: Label = $UI/OnboardingOverlay/Panel/Margin/VBox/BodyScroll/BodyLabel
@onready var onboarding_skip_button: Button = $UI/OnboardingOverlay/Panel/Margin/VBox/ActionRow/SkipButton
@onready var onboarding_back_button: Button = $UI/OnboardingOverlay/Panel/Margin/VBox/ActionRow/BackButton
@onready var onboarding_next_button: Button = $UI/OnboardingOverlay/Panel/Margin/VBox/ActionRow/NextButton
@onready var chat_request: HTTPRequest = $ChatRequest
@onready var memory_view_request: HTTPRequest = $MemoryViewRequest
@onready var memory_reset_request: HTTPRequest = $MemoryResetRequest
@onready var config_reload_request: HTTPRequest = $ConfigReloadRequest
@onready var game_start_request: HTTPRequest = $GameStartRequest
@onready var game_state_request: HTTPRequest = $GameStateRequest
@onready var recovery_status_request: HTTPRequest = $RecoveryStatusRequest
@onready var night_action_request: HTTPRequest = $NightActionRequest
@onready var night_resolve_request: HTTPRequest = $NightResolveRequest
@onready var hunter_shot_request: HTTPRequest = $HunterShotRequest
@onready var player_speech_request: HTTPRequest = $PlayerSpeechRequest
@onready var player_speech_preview_request: HTTPRequest = $PlayerSpeechPreviewRequest
@onready var npc_speech_request: HTTPRequest = $NpcSpeechRequest
@onready var npc_speeches_batch_request: HTTPRequest = $NpcSpeechesBatchRequest
@onready var end_free_activity_request: HTTPRequest = $EndFreeActivityRequest
@onready var private_chat_request: HTTPRequest = $PrivateChatRequest
@onready var sheriff_action_request: HTTPRequest = $SheriffActionRequest
@onready var sheriff_speech_request: HTTPRequest = $SheriffSpeechRequest
@onready var combined_vote_request: HTTPRequest = $CombinedVoteRequest
@onready var game_summary_request: HTTPRequest = $GameSummaryRequest

var _fallback_npc_name := ""
var _fallback_dialog_text := ""
var _current_npc_name := ""
var _current_npc_character_id := 0
var _is_requesting := false
var _is_viewing_memory := false
var _is_resetting_memory := false
var _is_reloading_config := false
var _is_starting_wolf_game := false
var _is_loading_wolf_state := false
var _is_submitting_night_action := false
var _is_resolving_night := false
var _is_submitting_hunter_shot := false
var _is_previewing_player_speech := false
var _is_submitting_player_speech := false
var _is_generating_npc_speeches := false
var _is_fast_forwarding_speeches := false
var _is_ending_free_activity := false
var _is_private_chat_requesting := false
var _is_sheriff_action_requesting := false
var _is_sheriff_speech_requesting := false
var _is_submitting_vote := false
var _is_loading_game_summary := false
var _current_wolf_game_id := ""
var _resume_pending_game := false
var _session_slot := 1
var _replay_events: Array = []
var _replay_index := 0
var _replay_playing := false
var _tutorial_hints := true
var _session_variant := "classic"
var _session_npc_policy_mode := "local"
var _spectate_current_game_id := ""
var _achievement_toast_queue: Array[String] = []
var _achievement_chime: AudioStreamWAV
var _poker_table_id := ""
var _poker_requesting := false
var _poker_state: Dictionary = {}
var _poker_recorded_hand_number := 0
var _recovered_game_ids: Array[String] = []
var _sound_enabled := true
var _bgm_volume := 70.0
var _sfx_volume := 80.0
var _last_night_visual := false
var _animate_eliminations_on_next_render := false
var _last_alive_ids := {}
var _audio_bgm_day: AudioStreamPlayer
var _audio_bgm_night: AudioStreamPlayer
var _audio_sfx: AudioStreamPlayer
var _sfx_streams := {}
var _current_wolf_phase := ""
var _current_wolf_day := 1
var _current_player_character_id := 0
var _current_player_role := ""
var _current_player_alive := false
var _current_meeting_speaker_id := 0
var _current_meeting_order: Array[int] = []
var _current_meeting_direction := ""
var _current_sheriff_speaker_id := 0
var _current_sheriff_id := 0
var _current_sheriff_data: Dictionary = {}
var _pending_sheriff_action := ""
var _wolf_character_names := {}
var _wolf_character_alive := {}
var _wolf_character_is_sheriff := {}
var _wolf_private_question_used := {}
var _wolf_campaign_status := {}
var _preserve_wolf_game_info_once := false
var _wolf_menu_expanded := false
var _wolf_menu_tween: Tween
var _key_info_expanded := false
var _key_info_tween: Tween
var _key_info_count := 0
var _key_info_game_id := ""
var _intel_panel_open := false
var _summary_requested_game_id := ""
var _game_summary_data: Dictionary = {}
var _latest_wolf_game_data: Dictionary = {}
var _pending_player_speech_text := ""
var _pending_sheriff_speech_text := ""
var _pending_speech_preview_kind := ""
var _pending_speech_preview_body: Dictionary = {}
var _pending_speech_preview_fingerprint := ""
var _pending_speech_submission_confirmed := false
var _pending_vote_reason_text := ""
var _idempotency_counter := 0
var _pending_idempotency_commands: Dictionary = {}
var _player_publicly_claimed_seer := false
var _player_badge_flow_version := 0
var _badge_flow_game_id := ""
var _badge_flow_collapsed := true
var _onboarding_status := "inactive"
var _onboarding_current_step_id := ""
var _onboarding_seen_step_ids: Dictionary = {}
var _onboarding_pending_step_ids: Array[String] = []
var _onboarding_automatic_enabled := true
var _onboarding_automatic_guide_completed := false
var _onboarding_manual_mode := false
var _onboarding_manual_step_index := 0
var _onboarding_game_id := ""
var _onboarding_full_state_pending_after_manual := false
var _game_summary_pending_after_onboarding := false
var _responsive_layout_profile_name := "default"
var _wolf_menu_width := 440.0
var _intel_panel_width := 600.0
var _character_card_min_width := 160.0
var _ui_focus_scope := UI_FOCUS_SCOPE_WORLD
var _setup_focus_return: Control
var _summary_focus_return: Control
var _onboarding_focus_return: Control
var _intel_focus_return: Control
var _speech_preview_focus_return: Control


func _prepare_idempotent_body(channel: String, operation: String, body: Dictionary) -> Dictionary:
	var payload := body.duplicate(true)
	payload.erase("idempotency_key")
	var signature := operation + "|" + JSON.stringify(payload)
	var pending: Dictionary = _pending_idempotency_commands.get(channel, {})
	if str(pending.get("signature", "")) != signature:
		_idempotency_counter += 1
		pending = {
			"signature": signature,
			"key": "cmd:%d:%d:%d" % [
				int(Time.get_unix_time_from_system()),
				Time.get_ticks_usec(),
				_idempotency_counter,
			],
		}
		_pending_idempotency_commands[channel] = pending
	payload["idempotency_key"] = str(pending.get("key", ""))
	return payload


func _complete_idempotent_command(channel: String) -> void:
	_pending_idempotency_commands.erase(channel)


func _reset_idempotency_commands() -> void:
	_pending_idempotency_commands.clear()
	_idempotency_counter = 0


func _ready() -> void:
	_setup_audio()
	_update_world_time("", true)
	for npc in get_tree().get_nodes_in_group("npc"):
		npc.connect("dialog_requested", Callable(self, "_on_npc_dialog_requested"))
	chat_request.request_completed.connect(_on_chat_request_completed)
	memory_view_request.request_completed.connect(_on_memory_view_request_completed)
	memory_reset_request.request_completed.connect(_on_memory_reset_request_completed)
	config_reload_request.request_completed.connect(_on_config_reload_request_completed)
	game_start_request.request_completed.connect(_on_game_start_request_completed)
	game_state_request.request_completed.connect(_on_game_state_request_completed)
	recovery_status_request.request_completed.connect(_on_recovery_status_request_completed)
	knowledge_search_request.request_completed.connect(_on_knowledge_search_request_completed)
	stats_button.pressed.connect(_on_stats_button_pressed)
	stats_close_button.pressed.connect(_on_stats_close_button_pressed)
	save_button.pressed.connect(_on_save_button_pressed)
	save_game_request.request_completed.connect(_on_save_game_request_completed)
	bgm_volume_slider.value_changed.connect(_on_bgm_volume_changed)
	sfx_volume_slider.value_changed.connect(_on_sfx_volume_changed)
	night_action_request.request_completed.connect(_on_night_action_request_completed)
	night_resolve_request.request_completed.connect(_on_night_resolve_request_completed)
	hunter_shot_request.request_completed.connect(_on_hunter_shot_request_completed)
	player_speech_request.request_completed.connect(_on_player_speech_request_completed)
	player_speech_preview_request.request_completed.connect(_on_player_speech_preview_request_completed)
	npc_speech_request.request_completed.connect(_on_npc_speech_request_completed)
	npc_speeches_batch_request.request_completed.connect(_on_npc_speeches_batch_request_completed)
	end_free_activity_request.request_completed.connect(_on_end_free_activity_request_completed)
	private_chat_request.request_completed.connect(_on_private_chat_request_completed)
	sheriff_action_request.request_completed.connect(_on_sheriff_action_request_completed)
	sheriff_speech_request.request_completed.connect(_on_sheriff_speech_request_completed)
	combined_vote_request.request_completed.connect(_on_combined_vote_request_completed)
	game_summary_request.request_completed.connect(_on_game_summary_request_completed)
	start_game_button.pressed.connect(_on_start_game_button_pressed)
	continue_game_button.pressed.connect(_on_continue_game_button_pressed)
	knowledge_button.pressed.connect(_on_knowledge_button_pressed)
	knowledge_search_button.pressed.connect(_on_knowledge_search_submitted)
	knowledge_search_input.text_submitted.connect(_on_knowledge_search_submitted)
	knowledge_close_button.pressed.connect(_on_knowledge_close_button_pressed)
	sound_enabled_toggle.toggled.connect(_set_sound_enabled)
	slot_option.item_selected.connect(_on_slot_selected)
	tutorial_hints_toggle.toggled.connect(_on_tutorial_hints_toggled)
	llm_enabled_toggle.toggled.connect(_on_llm_enabled_toggled)
	llm_validation_toggle.toggled.connect(_on_llm_validation_toggled)
	refresh_state_button.pressed.connect(_on_refresh_state_button_pressed)
	review_game_button.pressed.connect(_on_review_game_button_pressed)
	submit_night_action_button.pressed.connect(_on_submit_night_action_button_pressed)
	resolve_night_button.pressed.connect(_on_resolve_night_button_pressed)
	night_action_option.item_selected.connect(_on_night_action_option_selected)
	hunter_shoot_button.pressed.connect(_on_hunter_shoot_button_pressed)
	hunter_pass_button.pressed.connect(_on_hunter_pass_button_pressed)
	sheriff_action_button.pressed.connect(_on_sheriff_action_button_pressed)
	sheriff_continue_button.pressed.connect(_on_sheriff_continue_button_pressed)
	sheriff_withdraw_button.pressed.connect(_on_sheriff_withdraw_button_pressed)
	sheriff_speech_button.pressed.connect(_on_sheriff_speech_button_pressed)
	sheriff_speech_input.text_submitted.connect(_on_sheriff_speech_input_submitted)
	sheriff_speech_input.text_changed.connect(_on_badge_flow_speech_draft_changed)
	badge_flow_include_toggle.toggled.connect(_on_badge_flow_include_toggled)
	badge_flow_collapse_button.pressed.connect(_on_badge_flow_collapse_pressed)
	badge_flow_primary_option.item_selected.connect(_on_badge_flow_target_selected)
	badge_flow_secondary_option.item_selected.connect(_on_badge_flow_target_selected)
	submit_speech_button.pressed.connect(_on_submit_speech_button_pressed)
	player_speech_input.text_submitted.connect(_on_player_speech_input_submitted)
	player_speech_input.text_changed.connect(_on_badge_flow_speech_draft_changed)
	speech_preview_edit_button.pressed.connect(_on_speech_preview_edit_button_pressed)
	speech_preview_confirm_button.pressed.connect(_on_speech_preview_confirm_button_pressed)
	end_free_activity_button.pressed.connect(_on_end_free_activity_button_pressed)
	fast_forward_button.pressed.connect(_on_fast_forward_button_pressed)
	submit_vote_button.pressed.connect(_on_submit_vote_button_pressed)
	vote_reason_input.text_submitted.connect(_on_vote_reason_input_submitted)
	wolf_menu_toggle_button.pressed.connect(_on_wolf_menu_toggle_button_pressed)
	key_info_toggle_button.pressed.connect(_on_key_info_toggle_button_pressed)
	intel_toggle_button.pressed.connect(_on_intel_toggle_button_pressed)
	intel_close_button.pressed.connect(_on_intel_close_button_pressed)
	guide_button.pressed.connect(_on_guide_button_pressed)
	menu_button.pressed.connect(_on_menu_button_pressed)
	menu_close_button.pressed.connect(_on_menu_close_button_pressed)
	archive_button.pressed.connect(_on_archive_button_pressed)
	load_button.pressed.connect(_on_load_button_pressed)
	load_close_button.pressed.connect(_on_load_close_button_pressed)
	for slot_index in range(load_slot_buttons.size()):
		load_slot_buttons[slot_index].pressed.connect(_on_load_slot_pressed.bind(slot_index + 1))
	spectate_button.pressed.connect(_on_spectate_button_pressed)
	spectate_close_button.pressed.connect(_on_spectate_close_button_pressed)
	spectate_refresh_button.pressed.connect(_on_spectate_refresh_button_pressed)
	spectate_game_select.item_selected.connect(_on_spectate_game_selected)
	spectate_poll_timer.timeout.connect(_request_spectate_snapshot)
	spectate_games_request.request_completed.connect(_on_spectate_games_request_completed)
	spectate_request.request_completed.connect(_on_spectate_request_completed)
	poker_close_button.pressed.connect(_on_poker_close_button_pressed)
	poker_fold_button.pressed.connect(_on_poker_action_pressed.bind("fold", 0))
	poker_check_call_button.pressed.connect(_on_poker_action_pressed.bind("call", 0))
	poker_raise_button.pressed.connect(_on_poker_raise_pressed)
	poker_all_in_button.pressed.connect(_on_poker_all_in_pressed)
	poker_raise_slider.value_changed.connect(_on_poker_raise_slider_changed)
	poker_next_hand_button.pressed.connect(_on_poker_next_hand_pressed)
	poker_request.request_completed.connect(_on_poker_request_completed)
	poker_hall_door.door_requested.connect(_on_venue_door_requested)
	board_game_door.door_requested.connect(_on_venue_door_requested)
	archive_close_button.pressed.connect(_on_archive_close_button_pressed)
	archive_request.request_completed.connect(_on_archive_request_completed)
	export_review_button.pressed.connect(_on_export_review_pressed)
	export_stats_button.pressed.connect(_on_export_stats_pressed)
	replay_button.pressed.connect(_on_replay_button_pressed)
	replay_close_button.pressed.connect(_on_replay_close_button_pressed)
	replay_prev_button.pressed.connect(_on_replay_prev_pressed)
	replay_next_button.pressed.connect(_on_replay_next_pressed)
	replay_play_button.pressed.connect(_on_replay_play_pressed)
	setup_toggle_button.pressed.connect(_on_setup_toggle_button_pressed)
	setup_close_button.pressed.connect(_on_setup_close_button_pressed)
	language_option.item_selected.connect(_on_language_option_selected)
	L10n.language_changed.connect(_on_language_changed)
	game_summary_close_button.pressed.connect(_hide_game_summary)
	onboarding_close_button.pressed.connect(_on_onboarding_close_button_pressed)
	onboarding_skip_button.pressed.connect(_on_onboarding_skip_button_pressed)
	onboarding_back_button.pressed.connect(_on_onboarding_back_button_pressed)
	onboarding_next_button.pressed.connect(_on_onboarding_next_button_pressed)
	get_window().size_changed.connect(_on_viewport_size_changed)
	dialog_box.call("connect", "message_submitted", Callable(self, "_on_dialog_message_submitted"))
	dialog_box.call("connect", "memory_view_requested", Callable(self, "_on_memory_view_requested"))
	dialog_box.call("connect", "memory_reset_requested", Callable(self, "_on_memory_reset_requested"))
	dialog_box.call("connect", "config_reload_requested", Callable(self, "_on_config_reload_requested"))
	dialog_box.call("connect", "closed", Callable(self, "_on_dialog_closed"))
	_configure_ui_focus_navigation()
	intel_tabs.set_tab_title(0, L10n.t("场上角色"))
	intel_tabs.set_tab_title(1, L10n.t("公开记录"))
	intel_tabs.set_tab_title(2, L10n.t("我的记录"))
	game_summary_tabs.set_tab_title(0, L10n.t("角色复盘"))
	game_summary_tabs.set_tab_title(1, L10n.t("对局时间线"))
	game_summary_tabs.set_tab_title(2, L10n.t("解释复盘（赛后）"))
	_update_llm_validation_controls()
	_load_onboarding_preferences()
	_load_session_preferences()
	variant_option.item_selected.connect(_on_variant_option_selected)
	_populate_variant_options()
	_populate_player_role_options(_session_variant)
	npc_policy_option.item_selected.connect(_on_npc_policy_option_selected)
	_populate_npc_policy_options()
	_sync_language_option()
	_apply_ui_translations()
	_update_responsive_layout()
	_update_contextual_panel_visibility()
	_set_wolf_menu_expanded(false, false)
	_set_key_info_expanded(false, false)
	_set_intel_panel_open(false)
	_request_recovery_status()
	call_deferred("_update_npc_roaming")


func _on_wolf_menu_toggle_button_pressed() -> void:
	_set_wolf_menu_expanded(not _wolf_menu_expanded)


func _on_key_info_toggle_button_pressed() -> void:
	_set_key_info_expanded(not _key_info_expanded)


func _on_intel_toggle_button_pressed() -> void:
	_set_intel_panel_open(not _intel_panel_open)


func _phase_uses_night_visual(phase: String) -> bool:
	return phase == "NIGHT"


func _update_world_time(phase: String, immediate: bool = false) -> void:
	town_background.call("set_night", _phase_uses_night_visual(phase), immediate)
	var is_night := _phase_uses_night_visual(phase)
	if is_night != _last_night_visual:
		_last_night_visual = is_night
		_play_sfx("night" if is_night else "day")
	_update_bgm(is_night)


func _setup_audio() -> void:
	_audio_bgm_day = AudioStreamPlayer.new()
	_audio_bgm_day.stream = load("res://assets/audio/day_bgm.wav")
	_audio_bgm_day.volume_db = -18.0
	_audio_bgm_day.finished.connect(_on_day_bgm_finished)
	add_child(_audio_bgm_day)
	_audio_bgm_night = AudioStreamPlayer.new()
	_audio_bgm_night.stream = load("res://assets/audio/night_bgm.wav")
	_audio_bgm_night.volume_db = -20.0
	_audio_bgm_night.finished.connect(_on_night_bgm_finished)
	add_child(_audio_bgm_night)
	_audio_sfx = AudioStreamPlayer.new()
	_audio_sfx.volume_db = -8.0
	add_child(_audio_sfx)
	for sfx_name in ["confirm", "cancel", "vote", "eliminate", "badge", "night", "day"]:
		_sfx_streams[sfx_name] = load("res://assets/audio/sfx_%s.wav" % sfx_name)
	_apply_audio_volumes()
	_update_bgm(false)


func _on_day_bgm_finished() -> void:
	if _sound_enabled and not _last_night_visual:
		_audio_bgm_day.play()


func _on_night_bgm_finished() -> void:
	if _sound_enabled and _last_night_visual:
		_audio_bgm_night.play()


func _update_bgm(is_night: bool) -> void:
	if not _sound_enabled:
		return
	if is_night:
		if _audio_bgm_day.playing:
			_audio_bgm_day.stop()
		if not _audio_bgm_night.playing:
			_audio_bgm_night.play()
	else:
		if _audio_bgm_night.playing:
			_audio_bgm_night.stop()
		if not _audio_bgm_day.playing:
			_audio_bgm_day.play()


func _play_sfx(sfx_name: String) -> void:
	if not _sound_enabled:
		return
	var stream: AudioStream = _sfx_streams.get(sfx_name)
	if stream != null:
		_audio_sfx.stream = stream
		_audio_sfx.play()


func _set_sound_enabled(enabled: bool) -> void:
	_sound_enabled = enabled
	if not enabled:
		_audio_bgm_day.stop()
		_audio_bgm_night.stop()
	else:
		_update_bgm(_last_night_visual)
	_save_session_preferences()


func _on_intel_close_button_pressed() -> void:
	_set_intel_panel_open(false)


func _on_guide_button_pressed() -> void:
	_hide_menu_overlay()
	_show_manual_onboarding()


func _on_setup_toggle_button_pressed() -> void:
	if setup_toggle_button.disabled:
		return
	_show_game_setup()


func _on_setup_close_button_pressed() -> void:
	_hide_game_setup()


func _on_llm_enabled_toggled(_enabled: bool) -> void:
	_update_llm_validation_controls()


func _on_llm_validation_toggled(_enabled: bool) -> void:
	_update_llm_validation_controls()


func _update_llm_validation_controls() -> void:
	var llm_requested: bool = llm_enabled_toggle.button_pressed
	llm_validation_toggle.disabled = not llm_requested
	if not llm_requested:
		llm_settings_hint.text = L10n.t("启用 AI NPC 表达后可选；Python 规则结算始终独立生效")
	elif llm_validation_toggle.button_pressed:
		llm_settings_hint.text = L10n.t("输出校验开启：不合格表达最多纠正 5 次")
	else:
		llm_settings_hint.text = L10n.t("输出校验关闭：生成 1 次、校验 0 次并直出原文；Python 规则结算不变")


func _llm_validation_requested() -> bool:
	return llm_enabled_toggle.button_pressed and llm_validation_toggle.button_pressed


func _show_game_setup() -> void:
	if not game_setup_overlay.visible:
		_setup_focus_return = _current_focus_control()
	if dialog_box.call("is_open"):
		dialog_box.call("hide_dialog", false)
	_set_intel_panel_open(false, false)
	_set_wolf_menu_expanded(false)
	game_setup_overlay.visible = true
	game_setup_overlay.add_to_group("dialog_open")
	setup_status_label.text = L10n.t(
		"上一局已结束，可以调整设置后开始新对局。"
		if _current_wolf_phase == "GAME_OVER"
		else "准备好后开始游戏，也可以先关闭窗口探索小镇。"
	)
	if _current_wolf_game_id.is_empty():
		setup_status_label.text += "\n" + L10n.t("提示：右上角「规则」「战绩」随时可用；「继续上局」可恢复未完成对局。")
	_sync_language_option()
	player.call("set_menu_safe_area", false, 0.0)
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	call_deferred("_focus_control_if_available", player_name_input)


func _sync_language_option() -> void:
	language_option.clear()
	language_option.add_item("中文")
	language_option.add_item("English")
	language_option.select(0 if L10n.language == "zh" else 1)


func _on_language_option_selected(index: int) -> void:
	var language_code := "zh" if index == 0 else "en"
	L10n.set_language(language_code)
	_save_session_preferences()
	_apply_ui_translations()


func _on_language_changed(_language_code: String) -> void:
	_sync_language_option()
	_apply_ui_translations()


func _apply_ui_translations() -> void:
	_translate_control_tree($UI)
	if not _latest_wolf_game_data.is_empty():
		_render_wolf_game(_latest_wolf_game_data)
	else:
		_update_wolf_menu_summary()
		_update_day_speech_controls_from_current_state()


func _translate_control_tree(node: Node) -> void:
	for child in node.get_children():
		_translate_control_tree(child)
	if node is LineEdit:
		var placeholder_source: String = str(node.get_meta("l10n_placeholder_source", ""))
		if (
			placeholder_source.is_empty()
			or (
				node.placeholder_text != placeholder_source
				and node.placeholder_text != L10n.english_of(placeholder_source)
			)
		):
			placeholder_source = L10n.reverse_t(node.placeholder_text)
			node.set_meta("l10n_placeholder_source", placeholder_source)
		node.placeholder_text = L10n.t(placeholder_source)
	elif (node is BaseButton or node is Label) and not (node is OptionButton):
		var text_source: String = str(node.get_meta("l10n_text_source", ""))
		if (
			text_source.is_empty()
			or (
				node.text != text_source
				and node.text != L10n.english_of(text_source)
			)
		):
			text_source = L10n.reverse_t(node.text)
			node.set_meta("l10n_text_source", text_source)
		node.text = L10n.t(text_source)
	if node is Control and not node.tooltip_text.is_empty():
		var tooltip_source: String = str(node.get_meta("l10n_tooltip_source", ""))
		if (
			tooltip_source.is_empty()
			or (
				node.tooltip_text != tooltip_source
				and node.tooltip_text != L10n.english_of(tooltip_source)
			)
		):
			tooltip_source = L10n.reverse_t(node.tooltip_text)
			node.set_meta("l10n_tooltip_source", tooltip_source)
		node.tooltip_text = L10n.t(tooltip_source)


func _hide_game_setup(restore_focus: bool = true) -> void:
	if _is_starting_wolf_game:
		return
	if not game_setup_overlay.visible:
		return
	var return_focus := _setup_focus_return
	_setup_focus_return = null
	game_setup_overlay.visible = false
	game_setup_overlay.remove_from_group("dialog_open")
	setup_close_button.release_focus()
	start_game_button.release_focus()
	_release_movement_actions()
	_update_ui_safe_area()
	if restore_focus:
		call_deferred(
			"_restore_focus_after_close",
			return_focus,
			setup_toggle_button
		)
	else:
		_release_focus_to_world()


func _set_intel_panel_open(open: bool, restore_focus: bool = true) -> void:
	if open and _current_wolf_game_id.is_empty():
		return
	var was_open := _intel_panel_open
	if open:
		if not was_open:
			_intel_focus_return = _current_focus_control()
		_set_wolf_menu_expanded(false)
	_intel_panel_open = open
	intel_panel.visible = open
	intel_toggle_button.text = "关闭情报" if open else "情报"
	intel_toggle_button.tooltip_text = "关闭对局情报" if open else "查看场上角色、公开记录和我的记录"
	if not open:
		intel_close_button.release_focus()
		if was_open and restore_focus:
			call_deferred(
				"_restore_focus_after_close",
				_intel_focus_return,
				intel_toggle_button
			)
		_intel_focus_return = null
	elif not was_open:
		_set_ui_focus_scope(UI_FOCUS_SCOPE_PANEL)
		call_deferred("_focus_control_if_available", intel_close_button)
	_update_ui_safe_area()


func _populate_player_role_options(variant: String = "classic") -> void:
	var previous_role := str(_get_selected_option_metadata(player_role_option, "random"))
	player_role_option.clear()
	var options: Array = [
		[L10n.t("随机身份"), "random"],
		[L10n.t("狼人（测试）"), "werewolf"],
		[L10n.t("预言家（测试）"), "seer"],
		[L10n.t("女巫（测试）"), "witch"],
		[L10n.t("猎人（测试）"), "hunter"],
		[L10n.t("守卫（测试）"), "guard"],
		[L10n.t("村民（测试）"), "villager"],
	]
	if variant == "idiot":
		options.append([L10n.t("白痴（测试）"), "idiot"])
	for option in options:
		player_role_option.add_item(str(option[0]))
		player_role_option.set_item_metadata(player_role_option.get_item_count() - 1, option[1])
	if variant != "idiot" and previous_role == "idiot":
		player_role_option.select(0)


func _populate_variant_options() -> void:
	variant_option.clear()
	variant_option.add_item(L10n.t("经典局"))
	variant_option.set_item_metadata(variant_option.get_item_count() - 1, "classic")
	variant_option.add_item(L10n.t("白痴局"))
	variant_option.set_item_metadata(variant_option.get_item_count() - 1, "idiot")
	for i in range(variant_option.get_item_count()):
		if str(variant_option.get_item_metadata(i)) == _session_variant:
			variant_option.select(i)
			break


func _get_selected_variant() -> String:
	return str(_get_selected_option_metadata(variant_option, "classic"))


func _on_variant_option_selected(_index: int) -> void:
	_session_variant = _get_selected_variant()
	_populate_player_role_options(_session_variant)
	_save_session_preferences()


func _populate_npc_policy_options() -> void:
	npc_policy_option.clear()
	npc_policy_option.add_item(L10n.t("规则模式"))
	npc_policy_option.set_item_metadata(npc_policy_option.get_item_count() - 1, "rule")
	npc_policy_option.add_item(L10n.t("影子模式"))
	npc_policy_option.set_item_metadata(npc_policy_option.get_item_count() - 1, "shadow")
	npc_policy_option.add_item(L10n.t("本地模型"))
	npc_policy_option.set_item_metadata(npc_policy_option.get_item_count() - 1, "local")
	for i in range(npc_policy_option.get_item_count()):
		if str(npc_policy_option.get_item_metadata(i)) == _session_npc_policy_mode:
			npc_policy_option.select(i)
			break


func _get_selected_npc_policy_mode() -> String:
	var mode := str(_get_selected_option_metadata(npc_policy_option, "local"))
	if mode not in ["rule", "shadow", "local"]:
		return "local"
	return mode


func _format_npc_policy_mode(mode: String) -> String:
	match mode:
		"rule":
			return L10n.t("规则模式")
		"shadow":
			return L10n.t("影子模式")
		"local":
			return L10n.t("本地模型")
		_:
			return mode


func _on_npc_policy_option_selected(_index: int) -> void:
	_session_npc_policy_mode = _get_selected_npc_policy_mode()
	_save_session_preferences()


func _on_viewport_size_changed() -> void:
	_update_responsive_layout()


func _responsive_profile_name_for_window(window_size: Vector2i) -> String:
	if window_size.x <= RESPONSIVE_COMPACT_MAX_WINDOW_WIDTH:
		return "compact"
	if (
		window_size.x >= RESPONSIVE_WIDE_MIN_WINDOW_WIDTH
		and window_size.y >= RESPONSIVE_WIDE_MIN_WINDOW_HEIGHT
	):
		return "wide"
	return "default"


func _update_responsive_layout() -> void:
	var window_size := get_window().size
	var viewport_size := get_viewport().get_visible_rect().size
	_responsive_layout_profile_name = _responsive_profile_name_for_window(window_size)
	var profile: Dictionary = RESPONSIVE_LAYOUT_PROFILES.get(
		_responsive_layout_profile_name,
		RESPONSIVE_LAYOUT_PROFILES["default"]
	)
	_wolf_menu_width = float(profile.get("wolf_menu_width", 440.0))
	_intel_panel_width = float(profile.get("intel_panel_width", 600.0))
	_character_card_min_width = float(profile.get("card_min_width", 160.0))

	var hud_width := minf(
		float(profile.get("hud_width", 540.0)),
		maxf(360.0, viewport_size.x - 32.0)
	)
	phase_hud.anchor_left = 0.5
	phase_hud.anchor_right = 0.5
	phase_hud.offset_left = hud_width * -0.5
	phase_hud.offset_right = hud_width * 0.5
	phase_title_label.visible = _responsive_layout_profile_name != "compact"

	identity_panel.offset_right = (
		identity_panel.offset_left
		+ float(profile.get("identity_width", 294.0))
	)
	wolf_panel.offset_left = -_wolf_menu_width - 16.0
	wolf_panel.offset_right = -16.0
	intel_panel.offset_left = -_intel_panel_width - 16.0
	intel_panel.offset_right = -16.0
	character_grid.columns = int(profile.get("intel_columns", 3))
	player_action_history_text.custom_minimum_size.y = minf(
		float(profile.get("history_min_height", 420.0)),
		maxf(280.0, viewport_size.y - 300.0)
	)
	_apply_character_card_sizes()

	var setup_width := minf(
		float(profile.get("setup_width", 600.0)),
		maxf(320.0, viewport_size.x - 32.0)
	)
	var setup_height := minf(450.0, maxf(400.0, viewport_size.y - 32.0))
	game_setup_panel.offset_left = setup_width * -0.5
	game_setup_panel.offset_right = setup_width * 0.5
	game_setup_panel.offset_top = setup_height * -0.5
	game_setup_panel.offset_bottom = setup_height * 0.5

	var summary_margin_horizontal := minf(
		float(profile.get("summary_margin_horizontal", 48.0)),
		maxf(16.0, (viewport_size.x - 320.0) * 0.5)
	)
	var summary_margin_vertical := minf(
		float(profile.get("summary_margin_vertical", 36.0)),
		maxf(16.0, (viewport_size.y - 360.0) * 0.5)
	)
	game_summary_panel.offset_left = summary_margin_horizontal
	game_summary_panel.offset_right = -summary_margin_horizontal
	game_summary_panel.offset_top = summary_margin_vertical
	game_summary_panel.offset_bottom = -summary_margin_vertical

	_update_wolf_menu_size()
	_set_key_info_expanded(_key_info_expanded, false)
	_update_onboarding_layout()
	if dialog_box.has_method("_update_responsive_layout"):
		dialog_box.call("_update_responsive_layout")
	_update_ui_safe_area()


func _apply_character_card_sizes() -> void:
	for child in character_grid.get_children():
		if child is Control:
			child.custom_minimum_size = Vector2(_character_card_min_width, 205.0)


func _load_onboarding_preferences() -> void:
	var config := ConfigFile.new()
	if config.load(ONBOARDING_SETTINGS_PATH) != OK:
		return
	if str(config.get_value(ONBOARDING_SETTINGS_SECTION, "schema_version", "")) != ONBOARDING_SCHEMA_VERSION:
		return
	var completed_value: Variant = config.get_value(
		ONBOARDING_SETTINGS_SECTION,
		"automatic_guide_completed",
		false
	)
	if typeof(completed_value) != TYPE_BOOL:
		return
	_onboarding_automatic_guide_completed = bool(completed_value)
	_onboarding_automatic_enabled = not _onboarding_automatic_guide_completed
	_onboarding_status = (
		"completed" if _onboarding_automatic_guide_completed else "inactive"
	)


func _save_onboarding_preferences() -> void:
	var config := ConfigFile.new()
	config.set_value(
		ONBOARDING_SETTINGS_SECTION,
		"schema_version",
		ONBOARDING_SCHEMA_VERSION
	)
	config.set_value(
		ONBOARDING_SETTINGS_SECTION,
		"automatic_guide_completed",
		_onboarding_automatic_guide_completed
	)
	var save_error := config.save(ONBOARDING_SETTINGS_PATH)
	if save_error != OK:
		push_warning("无法保存新手引导偏好；本次运行仍会保留当前选择。")


func _update_onboarding_layout() -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	var panel_width := minf(680.0, maxf(300.0, viewport_size.x - 32.0))
	var panel_height := minf(500.0, maxf(360.0, viewport_size.y - 32.0))
	onboarding_panel.offset_left = panel_width * -0.5
	onboarding_panel.offset_right = panel_width * 0.5
	onboarding_panel.offset_top = panel_height * -0.5
	onboarding_panel.offset_bottom = panel_height * 0.5


func _show_manual_onboarding() -> void:
	if dialog_box.call("is_open"):
		return
	_onboarding_manual_mode = true
	_onboarding_pending_step_ids.clear()
	_onboarding_manual_step_index = _manual_onboarding_start_index()
	_open_onboarding_step(
		str(ONBOARDING_STEPS[_onboarding_manual_step_index].get("step_id", "")),
		true
	)


func _manual_onboarding_start_index() -> int:
	if _current_wolf_game_id.is_empty():
		return 0
	for index in range(ONBOARDING_STEPS.size()):
		var step: Dictionary = ONBOARDING_STEPS[index]
		var phases: Variant = step.get("phases", [])
		if typeof(phases) == TYPE_ARRAY and _current_wolf_phase in phases:
			return index
	return 0


func _evaluate_automatic_onboarding(game_data: Dictionary) -> void:
	if (
		not _onboarding_automatic_enabled
		or _onboarding_automatic_guide_completed
		or onboarding_overlay.visible
		or game_setup_overlay.visible
		or game_summary_overlay.visible
		or dialog_box.call("is_open")
	):
		return
	var private_info: Variant = game_data.get("player_private_info", null)
	if (
		typeof(private_info) != TYPE_DICTIONARY
		or str(private_info.get("role", "")).is_empty()
	):
		# GameStartResponse deliberately has no player-private projection.  Only
		# the complete GET /state response may activate automatic onboarding.
		return
	var incoming_game_id := str(game_data.get("game_id", ""))
	if incoming_game_id.is_empty():
		return
	_reset_onboarding_for_game(incoming_game_id)

	var eligible_step_ids: Array[String] = []
	for raw_step in ONBOARDING_STEPS:
		var step: Dictionary = raw_step
		var step_id := str(step.get("step_id", ""))
		if step_id.is_empty() or _onboarding_seen_step_ids.has(step_id):
			continue
		if _onboarding_step_is_eligible(step):
			eligible_step_ids.append(step_id)
	if eligible_step_ids.is_empty():
		return

	_onboarding_pending_step_ids.clear()
	for index in range(1, eligible_step_ids.size()):
		_onboarding_pending_step_ids.append(eligible_step_ids[index])
	_open_onboarding_step(eligible_step_ids[0], false)


func _reset_onboarding_for_game(game_id: String) -> void:
	if game_id == _onboarding_game_id:
		return
	_onboarding_game_id = game_id
	_onboarding_seen_step_ids.clear()
	_onboarding_pending_step_ids.clear()
	_onboarding_current_step_id = ""
	if not _onboarding_automatic_guide_completed:
		_onboarding_status = "inactive"


func _onboarding_step_is_eligible(step: Dictionary) -> bool:
	var roles: Variant = step.get("roles", [])
	if (
		typeof(roles) == TYPE_ARRAY
		and not roles.is_empty()
		and _current_player_role not in roles
	):
		return false
	var phases: Variant = step.get("phases", [])
	var phase_matches: bool = (
		typeof(phases) == TYPE_ARRAY
		and _current_wolf_phase in phases
	)
	match str(step.get("trigger_kind", "")):
		"full_state":
			return not _current_player_role.is_empty()
		"phase":
			return phase_matches
		"alive_phase":
			return _current_player_alive and phase_matches
		"player_speech_turn":
			if not _current_player_alive or not phase_matches:
				return false
			if _current_wolf_phase == "DAY_MEETING":
				return _current_meeting_speaker_id == _current_player_character_id
			return _current_sheriff_speaker_id == _current_player_character_id
		_:
			return false


func _open_onboarding_step(step_id: String, manual_mode: bool) -> void:
	var step := _find_onboarding_step(step_id)
	if step.is_empty():
		return
	if not onboarding_overlay.visible:
		_onboarding_focus_return = _current_focus_control()
	_onboarding_manual_mode = manual_mode
	_onboarding_current_step_id = step_id
	_onboarding_status = "active"
	if not manual_mode:
		_onboarding_seen_step_ids[step_id] = true
	onboarding_overlay.visible = true
	if not onboarding_overlay.is_in_group("dialog_open"):
		onboarding_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	_render_onboarding_step(step)
	_release_movement_actions()
	call_deferred("_focus_onboarding_primary_action")


func _find_onboarding_step(step_id: String) -> Dictionary:
	for raw_step in ONBOARDING_STEPS:
		var step: Dictionary = raw_step
		if str(step.get("step_id", "")) == step_id:
			return step
	return {}


func _onboarding_step_index(step_id: String) -> int:
	for index in range(ONBOARDING_STEPS.size()):
		if str(ONBOARDING_STEPS[index].get("step_id", "")) == step_id:
			return index
	return 0


func _render_onboarding_step(step: Dictionary) -> void:
	var step_index := _onboarding_step_index(_onboarding_current_step_id)
	onboarding_progress_label.text = (
		"新手引导 · %d / %d" % [step_index + 1, ONBOARDING_STEPS.size()]
		if _onboarding_manual_mode
		else "新手引导 · 当前阶段提示"
	)
	onboarding_title_label.text = str(step.get("title", "新手引导"))
	onboarding_scope_label.text = _onboarding_scope_text(
		str(step.get("information_scope", "public_action"))
	)
	var body := str(step.get("body", ""))
	if _onboarding_current_step_id in ["identity_and_scope", "night_skill"]:
		body += _current_role_onboarding_text(
			_onboarding_current_step_id == "identity_and_scope"
		)
	if not _current_wolf_game_id.is_empty():
		body += "\n\n当前阶段：" + _format_summary_phase(_current_wolf_phase)
	onboarding_body_label.text = body
	onboarding_body_scroll.scroll_vertical = 0

	onboarding_back_button.visible = _onboarding_manual_mode
	onboarding_back_button.disabled = (
		not _onboarding_manual_mode or _onboarding_manual_step_index <= 0
	)
	if _onboarding_manual_mode:
		onboarding_next_button.text = (
			"完成"
			if _onboarding_manual_step_index >= ONBOARDING_STEPS.size() - 1
			else "下一步"
		)
	else:
		onboarding_next_button.text = (
			"下一条" if not _onboarding_pending_step_ids.is_empty() else "知道了"
		)
	onboarding_skip_button.text = (
		"跳过全部" if _onboarding_automatic_enabled else "自动引导已关闭"
	)
	onboarding_skip_button.disabled = not _onboarding_automatic_enabled


func _onboarding_scope_text(scope: String) -> String:
	match scope:
		"player_private":
			return "信息范围：[仅你可见] 不会自动成为公开事实"
		"public_unverified":
			return "信息范围：[全场公开 · 未验真] 公开说法不等于身份真值"
		"public_action":
			return "信息范围：[全场公开行动] 以 Python 结算后的状态为准"
		"post_game_truth":
			return "信息范围：[仅赛后解锁] 不参与进行中的角色判断"
		_:
			return "信息范围：以当前 Python 状态投影为准"


func _current_role_onboarding_text(include_goal: bool) -> String:
	var role_guide: Dictionary = ONBOARDING_ROLE_GUIDES.get(
		_current_player_role,
		{}
	)
	if role_guide.is_empty():
		return "\n\n开始游戏并完成状态同步后，这里只会显示你自己的身份说明。"
	var lines: Array[String] = [
		"\n\n你的身份：" + _format_role_name(_current_player_role),
	]
	if include_goal:
		lines.append("目标：" + str(role_guide.get("goal", "")))
	lines.append("技能：" + str(role_guide.get("skill", "")))
	lines.append("[仅你可见] " + str(role_guide.get("private_note", "")))
	return "\n".join(lines)


func _focus_onboarding_primary_action() -> void:
	if onboarding_overlay.visible:
		onboarding_next_button.grab_focus()


func _move_onboarding_focus(direction: int) -> void:
	_move_focus_in_scope(onboarding_overlay, direction)


func _on_onboarding_close_button_pressed() -> void:
	_close_onboarding(false)


func _on_onboarding_skip_button_pressed() -> void:
	if not _onboarding_automatic_enabled:
		return
	_onboarding_automatic_enabled = false
	_onboarding_automatic_guide_completed = true
	_onboarding_status = "completed"
	_save_onboarding_preferences()
	_close_onboarding(true)


func _on_onboarding_back_button_pressed() -> void:
	if not _onboarding_manual_mode or _onboarding_manual_step_index <= 0:
		return
	_onboarding_manual_step_index -= 1
	_open_onboarding_step(
		str(ONBOARDING_STEPS[_onboarding_manual_step_index].get("step_id", "")),
		true
	)


func _on_onboarding_next_button_pressed() -> void:
	if _onboarding_manual_mode:
		if _onboarding_manual_step_index >= ONBOARDING_STEPS.size() - 1:
			_close_onboarding(false)
			return
		_onboarding_manual_step_index += 1
		_open_onboarding_step(
			str(ONBOARDING_STEPS[_onboarding_manual_step_index].get("step_id", "")),
			true
		)
		return

	if not _onboarding_pending_step_ids.is_empty():
		var next_step_id: String = str(_onboarding_pending_step_ids.pop_front())
		_open_onboarding_step(next_step_id, false)
		return
	if _onboarding_current_step_id == "post_game_review":
		_onboarding_automatic_enabled = false
		_onboarding_automatic_guide_completed = true
		_onboarding_status = "completed"
		_save_onboarding_preferences()
	_close_onboarding(_onboarding_automatic_guide_completed)


func _close_onboarding(completed: bool) -> void:
	if not onboarding_overlay.visible:
		return
	var was_manual_mode := _onboarding_manual_mode
	var return_focus := _onboarding_focus_return
	var show_pending_summary := _game_summary_pending_after_onboarding
	_onboarding_focus_return = null
	onboarding_overlay.visible = false
	onboarding_overlay.remove_from_group("dialog_open")
	for button in [
		onboarding_close_button,
		onboarding_skip_button,
		onboarding_back_button,
		onboarding_next_button,
	]:
		button.release_focus()
	_onboarding_pending_step_ids.clear()
	_onboarding_manual_mode = false
	_onboarding_status = "completed" if completed else "dismissed"
	_release_movement_actions()
	if show_pending_summary:
		_game_summary_pending_after_onboarding = false
		call_deferred("_show_game_summary")
	else:
		call_deferred(
			"_restore_focus_after_close",
			return_focus,
			guide_button
		)
	if was_manual_mode and _onboarding_full_state_pending_after_manual:
		_onboarding_full_state_pending_after_manual = false
		call_deferred("_evaluate_latest_automatic_onboarding")


func _evaluate_latest_automatic_onboarding() -> void:
	if (
		_latest_wolf_game_data.is_empty()
		or not _onboarding_automatic_enabled
		or _onboarding_automatic_guide_completed
	):
		return
	var manually_viewed_step_id := _onboarding_current_step_id
	var incoming_game_id := str(_latest_wolf_game_data.get("game_id", ""))
	if not incoming_game_id.is_empty():
		_reset_onboarding_for_game(incoming_game_id)
	var manually_viewed_step := _find_onboarding_step(manually_viewed_step_id)
	if (
		not manually_viewed_step.is_empty()
		and _onboarding_step_is_eligible(manually_viewed_step)
	):
		_onboarding_seen_step_ids[manually_viewed_step_id] = true
	_evaluate_automatic_onboarding(_latest_wolf_game_data)


func _key_info_target_bottom() -> float:
	if not _key_info_expanded:
		return IDENTITY_PANEL_COLLAPSED_BOTTOM
	return max(
		IDENTITY_PANEL_COLLAPSED_BOTTOM,
		min(IDENTITY_PANEL_EXPANDED_BOTTOM, get_viewport_rect().size.y - 16.0)
	)


func _update_key_info_toggle_text() -> void:
	var count_text := "暂无" if _key_info_count == 0 else str(_key_info_count) + "条"
	key_info_toggle_button.text = (
		"关键公开信息 · " + count_text + ("  ▲" if _key_info_expanded else "  ▼")
	)
	key_info_toggle_button.tooltip_text = (
		"收起关键公开信息" if _key_info_expanded else "展开场上已经公开的身份、验人和技能信息"
	)


func _set_key_info_expanded(expanded: bool, animate: bool = true) -> void:
	_key_info_expanded = expanded
	_update_key_info_toggle_text()
	if _key_info_tween != null and _key_info_tween.is_valid():
		_key_info_tween.kill()

	var target_bottom := _key_info_target_bottom()
	if expanded:
		key_info_content_panel.visible = true
	else:
		key_info_content_panel.visible = false

	if animate and identity_panel.visible:
		_key_info_tween = create_tween()
		_key_info_tween.set_trans(Tween.TRANS_QUAD)
		_key_info_tween.set_ease(Tween.EASE_OUT)
		_key_info_tween.tween_property(identity_panel, "offset_bottom", target_bottom, 0.18)
	else:
		identity_panel.offset_bottom = target_bottom
		key_info_content_panel.visible = expanded


func _update_key_public_info(game_data: Dictionary) -> void:
	key_info_safety_label.text = (
		"[全场公开] ◇ 公开说法（真假未确认） · ◆ 公开承诺（未验真） · ● 已确认公开动作\n"
		+ "! 矛盾候选仅供核对，不代表说谎或阵营判断"
	)
	var incoming_game_id := str(game_data.get("game_id", ""))
	if incoming_game_id != _key_info_game_id:
		_key_info_game_id = incoming_game_id
		_key_info_count = 0
		_set_key_info_expanded(false, false)

	var lines: Array[String] = []
	var public_items: Variant = []
	var public_timeline = game_data.get("public_evidence_timeline", {})
	if (
		typeof(public_timeline) == TYPE_DICTIONARY
		and str(public_timeline.get("schema_version", "")) == "public_evidence_timeline.v1"
	):
		public_items = public_timeline.get("items", [])
	else:
		public_items = game_data.get("public_intel", [])
	if typeof(public_items) == TYPE_ARRAY:
		for item in public_items:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var display_text := str(item.get("display_text", "")).strip_edges()
			if display_text.is_empty():
				continue
			var day := int(item.get("day", _current_wolf_day))
			var marker := _public_evidence_marker(str(item.get("category", "claim")))
			lines.append(marker + " 第" + str(day) + "天 · " + display_text)

	key_info_label.text = (
		"\n".join(lines)
		if not lines.is_empty()
		else "暂无关键公开声明或确认动作。"
	)
	var previous_count := _key_info_count
	_key_info_count = lines.size()
	_update_key_info_toggle_text()
	if previous_count == 0 and _key_info_count > 0:
		_set_key_info_expanded(true)


func _set_wolf_menu_expanded(expanded: bool, animate: bool = true) -> void:
	if not expanded and speech_preview_panel.visible:
		return
	if expanded and _intel_panel_open:
		_set_intel_panel_open(false)
	_wolf_menu_expanded = expanded
	if not expanded:
		_release_wolf_panel_focus()
	if _wolf_menu_tween != null and _wolf_menu_tween.is_valid():
		_wolf_menu_tween.kill()

	var target_bottom := WOLF_MENU_TOP + _get_wolf_menu_target_height()
	if expanded:
		wolf_content_panel.visible = true

	if animate:
		_wolf_menu_tween = create_tween()
		_wolf_menu_tween.set_trans(Tween.TRANS_QUAD)
		_wolf_menu_tween.set_ease(Tween.EASE_OUT)
		_wolf_menu_tween.tween_property(wolf_panel, "offset_bottom", target_bottom, 0.22)
		if not expanded:
			_wolf_menu_tween.finished.connect(func(): wolf_content_panel.visible = false)
	else:
		wolf_panel.offset_bottom = target_bottom
		wolf_content_panel.visible = expanded

	wolf_menu_toggle_button.text = "▲" if expanded else "▼"
	wolf_menu_toggle_button.tooltip_text = "收起当前行动" if expanded else "展开当前行动"
	_update_ui_safe_area()


func _update_ui_safe_area() -> void:
	var safe_width := 0.0
	if _intel_panel_open:
		safe_width = _intel_panel_width
	elif _wolf_menu_expanded:
		safe_width = _wolf_menu_width
	player.call("set_menu_safe_area", safe_width > 0.0, safe_width)


func _update_wolf_menu_size() -> void:
	var target_bottom := WOLF_MENU_TOP + _get_wolf_menu_target_height()
	if _wolf_menu_tween != null and _wolf_menu_tween.is_valid():
		_wolf_menu_tween.kill()
	wolf_panel.offset_bottom = target_bottom


func _get_wolf_menu_target_height() -> float:
	if not _wolf_menu_expanded:
		return WOLF_MENU_COLLAPSED_HEIGHT
	var viewport_height := float(get_viewport().get_visible_rect().size.y)
	var profile: Dictionary = RESPONSIVE_LAYOUT_PROFILES.get(
		_responsive_layout_profile_name,
		RESPONSIVE_LAYOUT_PROFILES["default"]
	)
	var height_ratio := float(profile.get("wolf_height_ratio", 0.62))
	return clampf(
		viewport_height * height_ratio,
		WOLF_MENU_MIN_EXPANDED_HEIGHT,
		WOLF_MENU_MAX_EXPANDED_HEIGHT
	)


func _input(event: InputEvent) -> void:
	if (
		event is InputEventKey
		and event.pressed
		and not event.echo
		and event.keycode == KEY_F1
	):
		if not onboarding_overlay.visible:
			_show_manual_onboarding()
		get_viewport().set_input_as_handled()
		return

	if onboarding_overlay.visible:
		if event.is_action_pressed("ui_cancel"):
			_close_onboarding(false)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_prev"):
			_move_onboarding_focus(-1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_next"):
			_move_onboarding_focus(1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_left"):
			_on_onboarding_back_button_pressed()
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_right"):
			_on_onboarding_next_button_pressed()
			get_viewport().set_input_as_handled()
		elif _handle_modal_focus_direction(event, onboarding_overlay):
			get_viewport().set_input_as_handled()
		return

	if game_summary_overlay.visible:
		if event.is_action_pressed("ui_cancel"):
			_hide_game_summary()
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_prev"):
			_move_focus_in_scope(game_summary_overlay, -1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_next"):
			_move_focus_in_scope(game_summary_overlay, 1)
			get_viewport().set_input_as_handled()
		elif _handle_modal_focus_direction(event, game_summary_overlay):
			get_viewport().set_input_as_handled()
		return

	if game_setup_overlay.visible:
		if event.is_action_pressed("ui_cancel"):
			_hide_game_setup()
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_prev"):
			_move_focus_in_scope(game_setup_overlay, -1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_next"):
			_move_focus_in_scope(game_setup_overlay, 1)
			get_viewport().set_input_as_handled()
		elif _handle_modal_focus_direction(event, game_setup_overlay):
			get_viewport().set_input_as_handled()
		return

	if speech_preview_panel.is_visible_in_tree():
		if event is InputEventMouseButton and event.pressed:
			var mouse_event := event as InputEventMouseButton
			var visible_preview_rect := speech_preview_panel.get_global_rect().intersection(
				wolf_scroll_container.get_global_rect()
			)
			if not visible_preview_rect.has_point(mouse_event.position):
				get_viewport().set_input_as_handled()
				return
		if event.is_action_pressed("ui_cancel"):
			_on_speech_preview_edit_button_pressed()
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_prev"):
			_move_focus_in_scope(speech_preview_panel, -1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_focus_next"):
			_move_focus_in_scope(speech_preview_panel, 1)
			get_viewport().set_input_as_handled()
		elif _handle_modal_focus_direction(event, speech_preview_panel):
			get_viewport().set_input_as_handled()
		return

	if dialog_box.call("is_open"):
		return

	if event is InputEventMouseButton and event.pressed:
		_release_focus_to_world()
		return

	if _is_wasd_key_event(event) and not _current_focus_is_editable_text():
		_release_focus_to_world()
		return

	if event.is_action_pressed("ui_focus_prev"):
		_move_focus_in_active_panel(-1)
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_focus_next"):
		_move_focus_in_active_panel(1)
		get_viewport().set_input_as_handled()
		return

	var focus_owner := get_viewport().gui_get_focus_owner()
	if (
		_ui_focus_scope == UI_FOCUS_SCOPE_PANEL
		and focus_owner is BaseButton
		and not focus_owner is OptionButton
	):
		if event.is_action_pressed("ui_left") or event.is_action_pressed("ui_up"):
			_move_focus_in_active_panel(-1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("ui_right") or event.is_action_pressed("ui_down"):
			_move_focus_in_active_panel(1)
			get_viewport().set_input_as_handled()


func _unhandled_input(event: InputEvent) -> void:
	if onboarding_overlay.visible:
		# The guide is a modal input boundary.  In particular, the world
		# interaction action also contains E/Enter/Space and must not open an NPC
		# dialog behind the onboarding overlay.
		get_viewport().set_input_as_handled()
		return

	if game_summary_overlay.visible:
		get_viewport().set_input_as_handled()
		return

	if game_setup_overlay.visible:
		get_viewport().set_input_as_handled()
		return

	if speech_preview_panel.is_visible_in_tree() or dialog_box.call("is_open"):
		get_viewport().set_input_as_handled()
		return

	if event.is_action_pressed("ui_cancel") and _intel_panel_open:
		_set_intel_panel_open(false)
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_cancel") and menu_overlay.visible:
		_on_menu_close_button_pressed()
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_cancel") and archive_overlay.visible:
		_on_archive_close_button_pressed()
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_cancel") and replay_overlay.visible:
		_on_replay_close_button_pressed()
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_cancel") and knowledge_overlay.visible:
		_on_knowledge_close_button_pressed()
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_cancel") and stats_overlay.visible:
		_on_stats_close_button_pressed()
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("ui_cancel") and _ui_focus_scope != UI_FOCUS_SCOPE_WORLD:
		_release_focus_to_world()
		get_viewport().set_input_as_handled()
		return

	if not event.is_action_pressed("interact"):
		return
	if _ui_focus_scope != UI_FOCUS_SCOPE_WORLD or _current_focus_control() != null:
		get_viewport().set_input_as_handled()
		return

	var nearby_door = _get_nearby_venue_door()
	if nearby_door != null:
		nearby_door.call("request_entry")
		get_viewport().set_input_as_handled()
		return

	var nearby_npc = _get_nearby_npc()
	if nearby_npc != null:
		nearby_npc.call("request_dialog")
		get_viewport().set_input_as_handled()


func _get_nearby_venue_door():
	for door in get_tree().get_nodes_in_group("venue_door"):
		if door.call("is_player_nearby"):
			return door
	return null


func _get_nearby_npc():
	for npc in get_tree().get_nodes_in_group("npc"):
		if npc.call("is_player_nearby"):
			return npc
	return null


func _on_npc_dialog_requested(npc_name: String, dialog_text: String, wolf_character_id: int) -> void:
	if _wolf_menu_expanded:
		_set_wolf_menu_expanded(false)
	if _intel_panel_open:
		_set_intel_panel_open(false, false)
	_fallback_npc_name = npc_name
	_fallback_dialog_text = dialog_text
	_current_npc_name = npc_name
	_current_npc_character_id = wolf_character_id

	if _current_wolf_game_id.is_empty() or wolf_character_id <= 0:
		var prompt_text := "随时都可以聊！配置了 DeepSeek 时我会以我的性格和你对话，失败时也会安全回退。"
		dialog_box.call("show_prompt", npc_name, prompt_text)
		return

	if not bool(_wolf_character_alive.get(wolf_character_id, true)):
		dialog_box.call("show_notice", npc_name, "我已经出局，不能再参与本局发言和投票。")
		return

	match _current_wolf_phase:
		"NIGHT":
			dialog_box.call("show_notice", npc_name, "现在是夜晚，不能进行普通交谈。请在控制面板完成夜晚行动。")
		"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH":
			if wolf_character_id != _current_sheriff_speaker_id:
				var sheriff_speaker_name := str(_wolf_character_names.get(_current_sheriff_speaker_id, "当前候选人"))
				dialog_box.call("show_notice", npc_name, "还没轮到我进行警上发言。当前请先听 " + sheriff_speaker_name + "。")
			else:
				_request_current_npc_sheriff_speech(wolf_character_id, npc_name)
		"DAY_MEETING":
			if wolf_character_id != _current_meeting_speaker_id:
				var current_name := str(_wolf_character_names.get(_current_meeting_speaker_id, "当前角色"))
				dialog_box.call("show_notice", npc_name, "还没轮到我。当前请先听 " + current_name + " 发言。")
			else:
				_request_current_npc_meeting_speech(wolf_character_id, npc_name)
		"FREE_ACTIVITY":
			if not _current_player_alive:
				dialog_box.call("show_notice", npc_name, "你已经出局，不能进行私密追问。")
				return
			var used := bool(_wolf_private_question_used.get(wolf_character_id, false))
			var prompt := "这是今天第一次有效私密追问。原文不会自动公开，但会影响我的后续判断。"
			if used:
				prompt = "你今天已经向我进行过有效追问。原文不会自动公开；可以继续问，但不会再次改变我的决策。"
			dialog_box.call("show_private_prompt", npc_name, prompt)
		"VOTE":
			dialog_box.call("show_notice", npc_name, "现在是投票阶段，请在控制面板完成投票。")
		"GAME_OVER":
			dialog_box.call("show_notice", npc_name, "本局游戏已经结束，可以在控制面板开始新游戏。")
		_:
			dialog_box.call("show_notice", npc_name, "当前阶段暂时不能交谈。")


func _request_current_npc_sheriff_speech(character_id: int, npc_name: String) -> void:
	if _is_sheriff_speech_requesting or _current_wolf_game_id.is_empty():
		return
	_is_sheriff_speech_requesting = true
	_update_sheriff_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在生成 " + npc_name + " 的警上发言..."
	dialog_box.call("show_notice", npc_name, "正在整理警上竞选发言...")
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": character_id,
	}
	body = _prepare_idempotent_body("sheriff_speech", "npc_sheriff_speech", body)
	var headers = ["Content-Type: application/json"]
	var error = sheriff_speech_request.request(WOLF_SHERIFF_NPC_SPEECH_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_sheriff_speech_requesting = false
		_update_sheriff_controls_from_current_state()
		wolf_status_label.text = "后端状态：生成警上发言失败"
		dialog_box.call("show_notice", npc_name, "暂时无法生成警上发言，请确认后端已启动。")


func _request_current_npc_meeting_speech(character_id: int, npc_name: String) -> void:
	if _is_generating_npc_speeches or _current_wolf_game_id.is_empty():
		return

	_is_generating_npc_speeches = true
	_update_day_speech_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在生成 " + npc_name + " 的发言..."
	dialog_box.call("show_notice", npc_name, "正在结合前序发言整理判断...")

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": character_id
	}
	body = _prepare_idempotent_body("npc_speech", "npc_day_speech", body)
	var headers = ["Content-Type: application/json"]
	var error = npc_speech_request.request(WOLF_NPC_SPEECH_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_generating_npc_speeches = false
		_update_day_speech_controls_from_current_state()
		wolf_status_label.text = "后端状态：生成 NPC 发言失败"
		dialog_box.call("show_notice", npc_name, "无法连接 Python 后端。")


func _on_dialog_message_submitted(message: String) -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return
	if _current_wolf_phase == "FREE_ACTIVITY" and _current_npc_character_id > 0:
		_submit_private_chat(message)
		return

	_is_requesting = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在连接 Python 后端...")

	var body = {
		"npc_name": _current_npc_name,
		"message": message,
		"player_id": PLAYER_ID,
		"game_phase": _current_wolf_phase if not _current_wolf_phase.is_empty() else "TOWN"
	}
	var headers = ["Content-Type: application/json"]
	var error = chat_request.request(CHAT_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		dialog_box.call("show_dialog", _fallback_npc_name, _fallback_dialog_text)
		dialog_box.call("set_ready_for_input")
		_is_requesting = false


func _submit_private_chat(message: String) -> void:
	_is_private_chat_requesting = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在结合会议内容和私有记忆回答...")

	var body = {
		"game_id": _current_wolf_game_id,
		"npc_character_id": _current_npc_character_id,
		"question": message
	}
	body = _prepare_idempotent_body("private_chat", "private_chat", body)
	var headers = ["Content-Type: application/json"]
	var error = private_chat_request.request(WOLF_PRIVATE_CHAT_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_private_chat_requesting = false
		dialog_box.call("show_private_prompt", _current_npc_name, "私密追问失败：无法连接 Python 后端。")


func _on_memory_view_requested() -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return

	_is_viewing_memory = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在读取这个 NPC 对你的记忆...")

	var url = MEMORY_URL + "/" + PLAYER_ID.uri_encode() + "/" + _current_npc_name.uri_encode()
	var error = memory_view_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		_is_viewing_memory = false
		dialog_box.call("set_ready_for_input")
		dialog_box.call("show_dialog", _current_npc_name, "查看记忆失败：无法连接 Python 后端。")


func _on_memory_reset_requested() -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return

	_is_resetting_memory = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在清空这个 NPC 对你的记忆...")

	var url = MEMORY_URL + "/" + PLAYER_ID.uri_encode() + "/" + _current_npc_name.uri_encode()
	var error = memory_reset_request.request(url, [], HTTPClient.METHOD_DELETE)
	if error != OK:
		_is_resetting_memory = false
		dialog_box.call("set_ready_for_input")
		dialog_box.call("show_dialog", _current_npc_name, "清空记忆失败：无法连接 Python 后端。")


func _on_config_reload_requested() -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return

	_is_reloading_config = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在重新加载 NPC 人设和知识库...")

	var error = config_reload_request.request(CONFIG_RELOAD_URL, [], HTTPClient.METHOD_POST)
	if error != OK:
		_is_reloading_config = false
		dialog_box.call("set_ready_for_input")
		dialog_box.call("show_dialog", _current_npc_name, "重载配置失败：无法连接 Python 后端。")


func _on_start_game_button_pressed() -> void:
	if _is_starting_wolf_game:
		return
	_play_sfx("confirm")

	_reset_idempotency_commands()
	_is_starting_wolf_game = true
	_reset_game_summary()
	wolf_menu_summary_label.text = "正在开始..."
	start_game_button.disabled = true
	setup_close_button.disabled = true
	setup_status_label.text = "正在连接后端并创建十二人局..."
	wolf_status_label.text = "后端状态：正在创建 12 人局..."
	wolf_game_info_label.text = "正在随机分配身份。"
	night_action_label.text = "夜晚行动：等待游戏创建。"
	sheriff_action_label.text = "警长操作：等待游戏创建。"
	day_speech_label.text = "白天发言：等待游戏创建。"
	vote_action_label.text = "白天投票：等待游戏创建。"
	vote_result_label.text = "票型：尚未公布"
	public_log_label.text = "公开日志：等待后端返回。"
	_disable_night_controls()
	_disable_sheriff_controls()
	_disable_day_speech_controls()
	_disable_vote_controls()
	_clear_character_grid()

	var player_name := player_name_input.text.strip_edges()
	if player_name.is_empty():
		player_name = "玩家"

	var body = {
		"player_name": player_name,
		"npc_count": 11,
		"variant": _get_selected_variant(),
		"npc_policy_mode": _get_selected_npc_policy_mode(),
		"player_role": str(_get_selected_option_metadata(player_role_option, "random")),
		"enable_llm": llm_enabled_toggle.button_pressed,
		"enable_llm_validation": _llm_validation_requested(),
		"enable_rag": true
	}
	var headers = ["Content-Type: application/json"]
	var error = game_start_request.request(WOLF_GAME_START_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_starting_wolf_game = false
		start_game_button.disabled = false
		setup_close_button.disabled = false
		setup_status_label.text = "连接失败：请先手动启动 FastAPI 后端。"
		wolf_status_label.text = "后端状态：连接失败"
		wolf_game_info_label.text = "请先启动 FastAPI 后端。"
		night_action_label.text = "夜晚行动：后端未连接。"
		day_speech_label.text = "白天发言：后端未连接。"
		vote_action_label.text = "白天投票：后端未连接。"
		public_log_label.text = "公开日志：暂无"


func _on_refresh_state_button_pressed() -> void:
	if _is_loading_wolf_state:
		return

	if _current_wolf_game_id.is_empty():
		wolf_status_label.text = "后端状态：还没有可刷新的游戏"
		return

	_hide_menu_overlay()
	_request_wolf_game_state()


func _on_review_game_button_pressed() -> void:
	_hide_menu_overlay()
	if not _game_summary_data.is_empty():
		_show_game_summary()
	elif _current_wolf_phase == "GAME_OVER":
		_request_game_summary()
	else:
		wolf_status_label.text = L10n.t("后端状态：") + L10n.t("游戏结束后才能查看复盘")
		dialog_box.call("show_notice", L10n.t("本局复盘"), L10n.t("游戏结束后才能查看复盘。"))


func _on_submit_night_action_button_pressed() -> void:
	if _is_submitting_night_action or _current_wolf_game_id.is_empty() or _current_player_character_id <= 0:
		return

	if _current_wolf_phase != "NIGHT":
		wolf_status_label.text = "后端状态：当前不是夜晚阶段"
		return

	var action_type := _get_selected_night_action_type()
	var target_id = null
	if _night_action_requires_target(action_type):
		if night_target_option.get_item_count() == 0:
			wolf_status_label.text = "后端状态：没有可选目标"
			return
		target_id = night_target_option.get_selected_id()

	_is_submitting_night_action = true
	_set_night_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在提交夜晚行动..."

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"action_type": action_type,
		"target_id": target_id
	}
	body = _prepare_idempotent_body("night_action", "night_action", body)
	var headers = ["Content-Type: application/json"]
	var error = night_action_request.request(WOLF_NIGHT_ACTION_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_submitting_night_action = false
		_update_night_controls_from_current_state()
		wolf_status_label.text = "后端状态：提交夜晚行动失败"


func _on_night_action_option_selected(_index: int) -> void:
	if not _latest_wolf_game_data.is_empty():
		_refresh_night_target_options(_latest_wolf_game_data)


func _on_hunter_shoot_button_pressed() -> void:
	if hunter_target_option.get_item_count() == 0:
		wolf_status_label.text = "后端状态：猎人没有可选目标"
		return
	_submit_hunter_shot(hunter_target_option.get_selected_id())


func _on_hunter_pass_button_pressed() -> void:
	_submit_hunter_shot(null)


func _submit_hunter_shot(target_id: Variant) -> void:
	if (
		_is_submitting_hunter_shot
		or _current_wolf_game_id.is_empty()
		or _current_wolf_phase != "HUNTER_SHOT"
	):
		return
	_is_submitting_hunter_shot = true
	hunter_target_option.disabled = true
	hunter_shoot_button.disabled = true
	hunter_pass_button.disabled = true
	wolf_status_label.text = "后端状态：正在提交猎人选择..."
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"target_id": target_id
	}
	body = _prepare_idempotent_body("hunter_shot", "hunter_shot", body)
	var headers = ["Content-Type: application/json"]
	var error = hunter_shot_request.request(
		WOLF_HUNTER_SHOT_URL,
		headers,
		HTTPClient.METHOD_POST,
		JSON.stringify(body)
	)
	if error != OK:
		_is_submitting_hunter_shot = false
		wolf_status_label.text = "后端状态：猎人选择提交失败"
		_update_hunter_controls(_latest_wolf_game_data)


func _on_resolve_night_button_pressed() -> void:
	_play_sfx("confirm")
	if _is_resolving_night or _current_wolf_game_id.is_empty():
		return

	if _current_wolf_phase != "NIGHT":
		wolf_status_label.text = "后端状态：当前不是夜晚阶段"
		return

	_is_resolving_night = true
	_set_night_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在结算夜晚..."

	var body = {"game_id": _current_wolf_game_id}
	body = _prepare_idempotent_body("night_resolve", "night_resolve", body)
	var headers = ["Content-Type: application/json"]
	var error = night_resolve_request.request(WOLF_NIGHT_RESOLVE_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_resolving_night = false
		_update_night_controls_from_current_state()
		wolf_status_label.text = "后端状态：结算夜晚失败"


func _on_submit_speech_button_pressed() -> void:
	if (
		_is_previewing_player_speech
		or _is_submitting_player_speech
		or speech_preview_panel.visible
		or _current_wolf_game_id.is_empty()
		or _current_player_character_id <= 0
	):
		return

	if not _is_day_speech_phase():
		wolf_status_label.text = "后端状态：当前不是白天发言阶段"
		return

	if not _current_player_alive:
		wolf_status_label.text = "后端状态：玩家已出局，不能发言"
		return

	var speech := player_speech_input.text.strip_edges()
	if speech.is_empty():
		wolf_status_label.text = "后端状态：请输入白天发言"
		return
	var badge_flow: Dictionary = {}
	if badge_flow_include_toggle.button_pressed:
		badge_flow = _build_selected_badge_flow()
		if badge_flow.is_empty():
			return

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"speech": speech,
		"temporary_nomination_target_id": null,
	}
	if not badge_flow.is_empty():
		body["badge_flow"] = badge_flow
	if _current_sheriff_id == _current_player_character_id:
		var temporary_target = _get_selected_option_metadata(temporary_nomination_option, 0)
		if int(temporary_target) > 0:
			body["temporary_nomination_target_id"] = int(temporary_target)
	_request_player_speech_preview("day", body)


func _on_player_speech_input_submitted(_speech: String) -> void:
	_on_submit_speech_button_pressed()


func _request_player_speech_preview(kind: String, submission_body: Dictionary) -> void:
	if _is_previewing_player_speech or player_speech_preview_request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return
	_is_previewing_player_speech = true
	_pending_speech_preview_kind = kind
	_pending_speech_preview_body = submission_body.duplicate(true)
	_pending_speech_preview_fingerprint = ""
	_pending_speech_submission_confirmed = false
	_speech_preview_focus_return = _current_focus_control()
	speech_preview_panel.visible = false
	speech_preview_panel.remove_from_group("dialog_open")
	var preview_body := submission_body.duplicate(true)
	preview_body["speech_kind"] = kind
	preview_body.erase("preview_fingerprint")
	_update_day_speech_controls_from_current_state()
	_update_sheriff_controls_from_current_state()
	_update_badge_flow_enabled_state()
	wolf_status_label.text = "后端状态：正在解析发言预览..."
	var headers = ["Content-Type: application/json"]
	var error = player_speech_preview_request.request(
		WOLF_PLAYER_SPEECH_PREVIEW_URL,
		headers,
		HTTPClient.METHOD_POST,
		JSON.stringify(preview_body)
	)
	if error != OK:
		_is_previewing_player_speech = false
		_clear_speech_preview()
		wolf_status_label.text = "后端状态：读取发言预览失败"


func _on_speech_preview_edit_button_pressed() -> void:
	var kind := _pending_speech_preview_kind
	_pending_speech_submission_confirmed = false
	_clear_speech_preview(true, false)
	if kind == "sheriff":
		sheriff_speech_input.grab_focus()
	else:
		player_speech_input.grab_focus()
	wolf_status_label.text = "后端状态：请修改发言后重新预览"


func _on_speech_preview_confirm_button_pressed() -> void:
	if (
		_pending_speech_preview_body.is_empty()
		or _pending_speech_preview_fingerprint.is_empty()
		or speech_preview_confirm_button.disabled
	):
		return
	var kind := _pending_speech_preview_kind
	var body := _pending_speech_preview_body.duplicate(true)
	body["preview_fingerprint"] = _pending_speech_preview_fingerprint
	_pending_speech_submission_confirmed = true
	_close_speech_preview_focus(false)
	speech_preview_confirm_button.disabled = true
	var headers = ["Content-Type: application/json"]
	if kind == "day":
		body = _prepare_idempotent_body("player_speech", "player_day_speech", body)
		_is_submitting_player_speech = true
		_pending_player_speech_text = str(body.get("speech", ""))
		_finish_gameplay_text_submission(player_speech_input)
		_set_day_speech_buttons_disabled(true)
		wolf_status_label.text = "后端状态：正在提交已确认的玩家发言..."
		var day_error = player_speech_request.request(
			WOLF_PLAYER_SPEECH_URL,
			headers,
			HTTPClient.METHOD_POST,
			JSON.stringify(body)
		)
		if day_error != OK:
			_is_submitting_player_speech = false
			_restore_failed_gameplay_text(
				player_speech_input,
				_pending_player_speech_text
			)
			_restore_confirmed_speech_preview()
			_update_day_speech_controls_from_current_state()
			wolf_status_label.text = "后端状态：提交发言失败"
		return
	if kind == "sheriff":
		body = _prepare_idempotent_body("sheriff_speech", "player_sheriff_speech", body)
		_is_sheriff_speech_requesting = true
		_pending_sheriff_speech_text = str(body.get("speech", ""))
		_finish_gameplay_text_submission(sheriff_speech_input)
		_update_sheriff_controls_from_current_state()
		_update_badge_flow_enabled_state()
		wolf_status_label.text = "后端状态：正在提交已确认的警上发言..."
		var sheriff_error = sheriff_speech_request.request(
			WOLF_SHERIFF_PLAYER_SPEECH_URL,
			headers,
			HTTPClient.METHOD_POST,
			JSON.stringify(body)
		)
		if sheriff_error != OK:
			_is_sheriff_speech_requesting = false
			_restore_failed_gameplay_text(
				sheriff_speech_input,
				_pending_sheriff_speech_text
			)
			_restore_confirmed_speech_preview()
			_update_sheriff_controls_from_current_state()
			_update_badge_flow_enabled_state()
			wolf_status_label.text = "后端状态：提交警上发言失败"


func _clear_speech_preview(
	update_controls: bool = true,
	restore_focus: bool = true,
) -> void:
	_close_speech_preview_focus(restore_focus)
	speech_preview_confirm_button.disabled = true
	speech_preview_summary.text = "等待 Python 解析。"
	_pending_speech_preview_kind = ""
	_pending_speech_preview_body = {}
	_pending_speech_preview_fingerprint = ""
	_pending_speech_submission_confirmed = false
	if update_controls:
		_update_day_speech_controls_from_current_state()
		_update_sheriff_controls_from_current_state()
		_update_badge_flow_enabled_state()


func _restore_confirmed_speech_preview() -> void:
	if (
		not _pending_speech_submission_confirmed
		or _pending_speech_preview_body.is_empty()
		or _pending_speech_preview_fingerprint.is_empty()
	):
		return
	speech_preview_confirm_button.disabled = false
	if _speech_preview_focus_return == null:
		_speech_preview_focus_return = (
			sheriff_speech_input
			if _pending_speech_preview_kind == "sheriff"
			else player_speech_input
		)
	_show_speech_preview_focus(speech_preview_confirm_button)
	_update_day_speech_controls_from_current_state()
	_update_sheriff_controls_from_current_state()
	_update_badge_flow_enabled_state()


func _show_speech_preview_focus(preferred: Control) -> void:
	if not _wolf_menu_expanded:
		_set_wolf_menu_expanded(true)
	speech_preview_panel.visible = true
	if not speech_preview_panel.is_in_group("dialog_open"):
		speech_preview_panel.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	call_deferred("_focus_control_if_available", preferred)


func _close_speech_preview_focus(restore_focus: bool) -> void:
	var return_focus := _speech_preview_focus_return
	var had_focus_context := speech_preview_panel.visible or return_focus != null
	var fallback: Control = (
		sheriff_speech_input
		if _pending_speech_preview_kind == "sheriff"
		else player_speech_input
	)
	_speech_preview_focus_return = null
	speech_preview_panel.visible = false
	speech_preview_panel.remove_from_group("dialog_open")
	speech_preview_edit_button.release_focus()
	speech_preview_confirm_button.release_focus()
	if not had_focus_context:
		return
	if restore_focus:
		call_deferred(
			"_restore_focus_after_close",
			return_focus,
			fallback
		)
	else:
		call_deferred("_repair_focus_after_modal_close")


func _on_fast_forward_button_pressed() -> void:
	if _is_fast_forwarding_speeches or _current_wolf_game_id.is_empty():
		return

	if _current_wolf_phase != "DAY_MEETING":
		wolf_status_label.text = "后端状态：当前不是白天会议"
		return

	_request_current_npc_speeches_batch()


func _on_end_free_activity_button_pressed() -> void:
	if _is_ending_free_activity or _current_wolf_game_id.is_empty():
		return

	if _current_wolf_phase != "FREE_ACTIVITY":
		wolf_status_label.text = "后端状态：当前不是自由活动阶段"
		return

	_is_ending_free_activity = true
	_update_day_speech_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在结束自由活动..."

	var body = {"game_id": _current_wolf_game_id}
	body = _prepare_idempotent_body("end_free_activity", "end_free_activity", body)
	var headers = ["Content-Type: application/json"]
	var error = end_free_activity_request.request(WOLF_END_FREE_ACTIVITY_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_ending_free_activity = false
		_update_day_speech_controls_from_current_state()
		wolf_status_label.text = "后端状态：结束自由活动失败"


func _on_sheriff_action_button_pressed() -> void:
	_submit_sheriff_action()


func _on_sheriff_continue_button_pressed() -> void:
	_submit_sheriff_action(false)


func _on_sheriff_withdraw_button_pressed() -> void:
	_submit_sheriff_action(true)


func _submit_sheriff_action(withdraw_choice: Variant = null) -> void:
	if _is_sheriff_action_requesting or _current_wolf_game_id.is_empty():
		return

	var body: Dictionary = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
	}
	var url := ""
	var operation := ""
	_pending_sheriff_action = _current_wolf_phase
	match _current_wolf_phase:
		"SHERIFF_SIGNUP":
			url = WOLF_SHERIFF_SIGNUP_URL
			operation = "sheriff_signup"
			body["run_for_sheriff"] = bool(_get_selected_option_metadata(sheriff_option, false))
		"SHERIFF_WITHDRAWAL":
			if withdraw_choice == null:
				return
			url = WOLF_SHERIFF_WITHDRAW_URL
			operation = "sheriff_withdrawal"
			body["withdraw"] = bool(withdraw_choice)
		"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE":
			url = WOLF_SHERIFF_VOTE_URL
			operation = "sheriff_vote"
			body["target_id"] = (
				_get_selected_option_metadata(sheriff_option, null)
				if bool(_current_sheriff_data.get("player_can_vote", false))
				else null
			)
		"MEETING_ORDER":
			url = WOLF_SHERIFF_MEETING_ORDER_URL
			operation = "sheriff_meeting_order"
			body["side"] = str(_get_selected_option_metadata(sheriff_option, "left"))
		"SHERIFF_NOMINATION":
			url = WOLF_SHERIFF_NOMINATE_URL
			operation = "sheriff_nomination"
			body["target_id"] = int(_get_selected_option_metadata(sheriff_option, 0))
		"BADGE_TRANSFER":
			url = WOLF_SHERIFF_TRANSFER_URL
			operation = "sheriff_badge_transfer"
			var transfer_target = _get_selected_option_metadata(sheriff_option, null)
			body["target_id"] = transfer_target if transfer_target != 0 else null
		_:
			return

	body = _prepare_idempotent_body("sheriff_action", operation, body)
	_is_sheriff_action_requesting = true
	_update_sheriff_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在提交警长操作..."
	var headers = ["Content-Type: application/json"]
	var error = sheriff_action_request.request(url, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_sheriff_action_requesting = false
		_update_sheriff_controls_from_current_state()
		wolf_status_label.text = "后端状态：警长操作提交失败"


func _on_sheriff_speech_button_pressed() -> void:
	if (
		_is_previewing_player_speech
		or _is_sheriff_speech_requesting
		or speech_preview_panel.visible
		or _current_wolf_game_id.is_empty()
	):
		return
	if _current_wolf_phase not in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]:
		return
	if _current_sheriff_speaker_id != _current_player_character_id:
		wolf_status_label.text = "后端状态：当前不是你的警上发言回合"
		return
	var speech := sheriff_speech_input.text.strip_edges()
	if speech.is_empty():
		wolf_status_label.text = "后端状态：警上发言不能为空"
		return
	if _is_sheriff_badge_flow_required() and not badge_flow_include_toggle.button_pressed:
		_badge_flow_collapsed = false
		_update_badge_flow_collapsed_state()
		wolf_status_label.text = "后端状态：警上首次跳预言家时必须同时发布警徽流"
		return
	var badge_flow: Dictionary = {}
	if badge_flow_include_toggle.button_pressed:
		badge_flow = _build_selected_badge_flow()
		if badge_flow.is_empty():
			return

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"speech": speech,
	}
	if not badge_flow.is_empty():
		body["badge_flow"] = badge_flow
	_request_player_speech_preview("sheriff", body)


func _on_sheriff_speech_input_submitted(_speech: String) -> void:
	_on_sheriff_speech_button_pressed()


func _on_submit_vote_button_pressed() -> void:
	_play_sfx("vote")
	if _is_submitting_vote or _current_wolf_game_id.is_empty() or _current_player_character_id <= 0:
		return

	if not _is_vote_phase():
		wolf_status_label.text = "后端状态：当前不是白天投票阶段"
		return

	if _current_player_alive and vote_target_option.get_item_count() == 0:
		wolf_status_label.text = "后端状态：没有可投票目标"
		return

	_is_submitting_vote = true
	_set_vote_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在同时生成并结算全部投票..."

	var vote_reason := vote_reason_input.text.strip_edges()
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"target_id": vote_target_option.get_selected_id() if _current_player_alive else null,
		"reason": vote_reason,
	}
	body = _prepare_idempotent_body("combined_vote", "combined_vote", body)
	_pending_vote_reason_text = vote_reason
	_finish_gameplay_text_submission(vote_reason_input)
	var headers = ["Content-Type: application/json"]
	var error = combined_vote_request.request(WOLF_COMBINED_VOTE_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_submitting_vote = false
		_restore_failed_gameplay_text(vote_reason_input, _pending_vote_reason_text)
		_update_vote_controls_from_current_state()
		wolf_status_label.text = "后端状态：同时投票失败"


func _on_vote_reason_input_submitted(_reason: String) -> void:
	_on_submit_vote_button_pressed()


func _get_selected_option_metadata(option: OptionButton, fallback: Variant) -> Variant:
	if option.get_item_count() == 0 or option.selected < 0:
		return fallback
	var metadata = option.get_item_metadata(option.selected)
	return metadata if metadata != null else fallback


func _build_selected_badge_flow() -> Dictionary:
	if not badge_flow_panel.visible or not _is_player_badge_flow_speech_turn():
		wolf_status_label.text = "后端状态：当前不能发布或调整警徽流"
		return {}
	if not _player_publicly_claimed_seer and not _current_badge_flow_speech_declares_seer():
		wolf_status_label.text = "后端状态：首次发布警徽流时，请在本次发言中明确写出“我是预言家”“我跳预言家”或“我起跳预言家”"
		return {}

	var primary_target_id := int(_get_selected_option_metadata(badge_flow_primary_option, 0))
	var secondary_target_id := int(_get_selected_option_metadata(badge_flow_secondary_option, 0))
	var claimed_good_anchor_id := int(_get_selected_option_metadata(badge_flow_wolf_option, 0))
	var revision_reason := str(_get_selected_option_metadata(badge_flow_reason_option, ""))
	var reason_target_id := int(_get_selected_option_metadata(badge_flow_reason_target_option, 0))

	if primary_target_id <= 0:
		wolf_status_label.text = "后端状态：请选择第一警徽流验人目标"
		return {}
	if secondary_target_id == primary_target_id:
		wolf_status_label.text = "后端状态：两个警徽流验人目标不能相同"
		return {}
	if revision_reason.is_empty():
		wolf_status_label.text = "后端状态：请选择警徽流发布或调整理由"
		return {}

	return {
		"primary_target_id": primary_target_id,
		"secondary_target_id": secondary_target_id if secondary_target_id > 0 else null,
		"claimed_good_anchor_id": claimed_good_anchor_id if claimed_good_anchor_id > 0 else null,
		"revision_reason": revision_reason,
		"reason_target_id": reason_target_id if reason_target_id > 0 else null,
	}


func _on_chat_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_requesting = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _fallback_npc_name, _fallback_dialog_text)
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY or not json.data.has("reply"):
		dialog_box.call("show_dialog", _fallback_npc_name, _fallback_dialog_text)
		return

	var response_npc_name = json.data.get("npc_name", _fallback_npc_name)
	var knowledge_titles = json.data.get("knowledge_titles", [])
	if knowledge_titles.is_empty() and json.data.get("knowledge_title", "") != "":
		knowledge_titles = [json.data["knowledge_title"]]
	var memory_count = json.data.get("memory_count", 0)
	var relationship_level = json.data.get("relationship_level", "")
	var retrieval_mode = str(json.data.get("retrieval_mode", "keyword"))
	var llm_used := bool(json.data.get("llm_used", false))
	var llm_provider := str(json.data.get("llm_provider", "rule"))
	var llm_fallback_reason := str(json.data.get("llm_fallback_reason", ""))
	dialog_box.call(
		"show_response",
		response_npc_name,
		json.data["reply"],
		knowledge_titles,
		memory_count,
		relationship_level,
		retrieval_mode,
		llm_used,
		llm_provider,
		llm_fallback_reason
	)


func _on_memory_view_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_viewing_memory = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _current_npc_name, "查看记忆失败，请确认 Python 后端已启动。")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_ARRAY:
		dialog_box.call("show_dialog", _current_npc_name, "查看记忆失败：后端返回的数据格式不正确。")
		return

	dialog_box.call("show_dialog", _current_npc_name, _format_memory_preview(json.data))


func _on_memory_reset_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_resetting_memory = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _current_npc_name, "清空记忆失败，请确认 Python 后端已启动。")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		dialog_box.call("show_dialog", _current_npc_name, "记忆已清空。")
		return

	var deleted_count = json.data.get("deleted_count", 0)
	dialog_box.call("show_dialog", _current_npc_name, "记忆已清空，共删除 " + str(deleted_count) + " 条记录。")


func _on_config_reload_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_reloading_config = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _current_npc_name, "重载配置失败，请确认 Python 后端已启动。")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		dialog_box.call("show_dialog", _current_npc_name, "配置已重新加载。")
		return

	var npc_count = json.data.get("npc_count", 0)
	var knowledge_count = json.data.get("knowledge_count", 0)
	dialog_box.call("show_dialog", _current_npc_name, "配置已重新加载：NPC " + str(npc_count) + " 个，知识 " + str(knowledge_count) + " 条。")


func _on_game_start_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_starting_wolf_game = false
	start_game_button.disabled = false
	setup_close_button.disabled = false

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		setup_status_label.text = "创建失败：请确认 FastAPI 后端已手动启动。"
		wolf_status_label.text = "后端状态：创建游戏失败"
		wolf_game_info_label.text = "请确认 FastAPI 后端已启动。"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		setup_status_label.text = "创建失败：后端响应格式不正确。"
		wolf_status_label.text = "后端状态：响应格式错误"
		wolf_game_info_label.text = "后端没有返回有效的游戏数据。"
		return

	_render_wolf_game(json.data)
	_current_wolf_game_id = str(json.data.get("game_id", ""))
	_save_session_preferences()
	refresh_state_button.disabled = _current_wolf_game_id.is_empty()
	if not _current_wolf_game_id.is_empty():
		_hide_game_setup()
		_set_wolf_menu_expanded(true)
		_request_wolf_game_state()
	else:
		setup_status_label.text = "创建失败：后端响应缺少游戏编号。"
		wolf_status_label.text = "后端状态：响应缺少游戏编号"


func _on_game_state_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_loading_wolf_state = false
	refresh_state_button.disabled = _current_wolf_game_id.is_empty()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_preserve_wolf_game_info_once = false
		if _resume_pending_game:
			_resume_pending_game = false
			_current_wolf_game_id = ""
			_request_recovery_status()
			return
		wolf_status_label.text = "后端状态：刷新状态失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		_preserve_wolf_game_info_once = false
		wolf_status_label.text = "后端状态：状态响应格式错误"
		return

	_render_wolf_game(json.data)
	if _resume_pending_game:
		_resume_pending_game = false
		_save_session_preferences()
		_hide_game_setup()
		_set_wolf_menu_expanded(true)
	if onboarding_overlay.visible and _onboarding_manual_mode:
		var current_manual_step := _find_onboarding_step(_onboarding_current_step_id)
		if not current_manual_step.is_empty():
			_render_onboarding_step(current_manual_step)
		var private_info: Variant = json.data.get("player_private_info", null)
		_onboarding_full_state_pending_after_manual = (
			typeof(private_info) == TYPE_DICTIONARY
			and not str(private_info.get("role", "")).is_empty()
		)
	_evaluate_automatic_onboarding(json.data)


func _load_session_preferences() -> void:
	var config := ConfigFile.new()
	if config.load(SESSION_SETTINGS_PATH) != OK:
		return
	# Migrate the legacy single-slot keys into slot 1 on first load.
	var legacy_game_id: Variant = config.get_value(SESSION_SETTINGS_SECTION, "last_game_id", "")
	var legacy_player_name: Variant = config.get_value(SESSION_SETTINGS_SECTION, "player_name", "")
	if typeof(legacy_game_id) == TYPE_STRING and not str(legacy_game_id).is_empty():
		config.set_value(SESSION_SETTINGS_SECTION, "slot_1_game_id", str(legacy_game_id))
		config.set_value(SESSION_SETTINGS_SECTION, "last_game_id", "")
	if typeof(legacy_player_name) == TYPE_STRING and not str(legacy_player_name).is_empty():
		config.set_value(SESSION_SETTINGS_SECTION, "slot_1_player_name", str(legacy_player_name))
		config.set_value(SESSION_SETTINGS_SECTION, "player_name", "")
	_apply_session_slot(config)
	var sound_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "sound_enabled", true)
	_sound_enabled = true if typeof(sound_value) != TYPE_BOOL else bool(sound_value)
	sound_enabled_toggle.button_pressed = _sound_enabled
	var bgm_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "bgm_volume", 70.0)
	_bgm_volume = 70.0 if typeof(bgm_value) != TYPE_FLOAT else float(bgm_value)
	bgm_volume_slider.value = _bgm_volume
	var sfx_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "sfx_volume", 80.0)
	_sfx_volume = 80.0 if typeof(sfx_value) != TYPE_FLOAT else float(sfx_value)
	sfx_volume_slider.value = _sfx_volume
	var tutorial_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "tutorial_hints", true)
	_tutorial_hints = true if typeof(tutorial_value) != TYPE_BOOL else bool(tutorial_value)
	tutorial_hints_toggle.button_pressed = _tutorial_hints
	var variant_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "variant", "classic")
	_session_variant = (
		str(variant_value)
		if typeof(variant_value) == TYPE_STRING and str(variant_value) in ["classic", "idiot"]
		else "classic"
	)
	var npc_policy_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "npc_policy_mode", "local")
	_session_npc_policy_mode = (
		str(npc_policy_value)
		if typeof(npc_policy_value) == TYPE_STRING
		and str(npc_policy_value) in ["rule", "shadow", "local"]
		else "local"
	)
	var language_value: Variant = config.get_value(SESSION_SETTINGS_SECTION, "language", "zh")
	L10n.set_language(str(language_value) if typeof(language_value) == TYPE_STRING else "zh")


func _apply_session_slot(config: ConfigFile) -> void:
	var game_id: Variant = config.get_value(
		SESSION_SETTINGS_SECTION,
		"slot_" + str(_session_slot) + "_game_id",
		"",
	)
	_current_wolf_game_id = (
		str(game_id) if typeof(game_id) == TYPE_STRING else ""
	)
	var player_name: Variant = config.get_value(
		SESSION_SETTINGS_SECTION,
		"slot_" + str(_session_slot) + "_player_name",
		"",
	)
	if typeof(player_name) == TYPE_STRING and not str(player_name).is_empty():
		player_name_input.text = str(player_name)
	slot_option.selected = _session_slot - 1
	continue_game_button.disabled = _current_wolf_game_id.is_empty()


func _on_slot_selected(index: int) -> void:
	_session_slot = index + 1
	var config := ConfigFile.new()
	config.load(SESSION_SETTINGS_PATH)
	_apply_session_slot(config)
	_save_session_preferences()


func _save_session_preferences() -> void:
	var config := ConfigFile.new()
	config.load(SESSION_SETTINGS_PATH)
	config.set_value(SESSION_SETTINGS_SECTION, "schema_version", "agent_town_session.v2")
	config.set_value(
		SESSION_SETTINGS_SECTION,
		"slot_" + str(_session_slot) + "_game_id",
		_current_wolf_game_id,
	)
	config.set_value(
		SESSION_SETTINGS_SECTION,
		"slot_" + str(_session_slot) + "_player_name",
		player_name_input.text.strip_edges(),
	)
	config.set_value(SESSION_SETTINGS_SECTION, "sound_enabled", _sound_enabled)
	config.set_value(SESSION_SETTINGS_SECTION, "bgm_volume", _bgm_volume)
	config.set_value(SESSION_SETTINGS_SECTION, "sfx_volume", _sfx_volume)
	config.set_value(SESSION_SETTINGS_SECTION, "tutorial_hints", _tutorial_hints)
	config.set_value(SESSION_SETTINGS_SECTION, "variant", _session_variant)
	config.set_value(SESSION_SETTINGS_SECTION, "npc_policy_mode", _session_npc_policy_mode)
	config.set_value(SESSION_SETTINGS_SECTION, "language", L10n.language)
	var save_error := config.save(SESSION_SETTINGS_PATH)
	if save_error != OK:
		push_warning("无法保存会话设置；本次运行内仍可继续上局。")


func _request_recovery_status() -> void:
	var error := recovery_status_request.request(
		WOLF_RECOVERY_STATUS_URL,
		[],
		HTTPClient.METHOD_GET
	)
	if error != OK:
		continue_game_button.disabled = false


func _on_recovery_status_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	_recovered_game_ids.clear()
	if (
		result == HTTPRequest.RESULT_SUCCESS
		and response_code >= 200
		and response_code < 300
	):
		var json := JSON.new()
		if (
			json.parse(body.get_string_from_utf8()) == OK
			and typeof(json.data) == TYPE_DICTIONARY
		):
			var ids: Variant = json.data.get("restored_game_ids", [])
			if typeof(ids) == TYPE_ARRAY:
				for id_value in ids:
					if typeof(id_value) == TYPE_STRING:
						_recovered_game_ids.append(str(id_value))
	continue_game_button.disabled = (
		_current_wolf_game_id.is_empty() and _recovered_game_ids.is_empty()
	)
	if _resume_pending_game:
		_resume_pending_game = false
		if _recovered_game_ids.is_empty():
			setup_status_label.text = "没有找到可恢复的对局；请开始新一局。"
			wolf_status_label.text = "后端状态：没有可恢复的对局"
		else:
			_current_wolf_game_id = _recovered_game_ids[0]
			setup_status_label.text = "正在恢复上局..."
			_request_wolf_game_state()


func _on_continue_game_button_pressed() -> void:
	if _is_starting_wolf_game or _is_loading_wolf_state:
		return
	_play_sfx("confirm")
	var resume_id := _current_wolf_game_id
	if resume_id.is_empty() and not _recovered_game_ids.is_empty():
		resume_id = _recovered_game_ids[0]
	if resume_id.is_empty():
		setup_status_label.text = "没有可继续的对局；请开始新一局。"
		return
	_current_wolf_game_id = resume_id
	_resume_pending_game = true
	_reset_game_summary()
	wolf_menu_summary_label.text = "正在恢复上局..."
	setup_status_label.text = "正在恢复上局..."
	wolf_status_label.text = "后端状态：正在恢复上局..."
	_request_wolf_game_state()


func _on_knowledge_button_pressed() -> void:
	_hide_menu_overlay()
	knowledge_overlay.visible = true
	knowledge_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	call_deferred("_focus_control_if_available", knowledge_search_input)


func _on_knowledge_close_button_pressed() -> void:
	knowledge_overlay.visible = false
	knowledge_overlay.remove_from_group("dialog_open")
	knowledge_search_input.release_focus()
	_release_focus_to_world()


func _on_knowledge_search_submitted(_submitted_text: String = "") -> void:
	var query := knowledge_search_input.text.strip_edges()
	if query.is_empty():
		knowledge_status_label.text = "请输入要查询的问题。"
		return
	knowledge_status_label.text = "正在搜索知识库..."
	_clear_knowledge_results()
	var url := (
		KNOWLEDGE_SEARCH_URL
		+ "?npc_name=Guide&message=" + query.uri_encode() + "&limit=8"
	)
	var error := knowledge_search_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		knowledge_status_label.text = "搜索失败：请确认后端已启动。"


func _on_knowledge_search_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		knowledge_status_label.text = "搜索失败：后端不可用，请先启动 FastAPI。"
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK or typeof(json.data) != TYPE_DICTIONARY:
		knowledge_status_label.text = "搜索失败：后端响应格式不正确。"
		return
	var results: Variant = json.data.get("results", [])
	if typeof(results) != TYPE_ARRAY or results.is_empty():
		knowledge_status_label.text = "没有找到相关内容，换个说法再试试。"
		return
	knowledge_status_label.text = (
		"找到 " + str(results.size()) + " 条相关内容（检索模式："
		+ str(json.data.get("retrieval_mode", "keyword")) + "）"
	)
	for item in results:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var knowledge_item: Variant = item.get("item", {})
		if typeof(knowledge_item) != TYPE_DICTIONARY:
			continue
		_append_knowledge_result(knowledge_item)


func _append_knowledge_result(knowledge_item: Dictionary) -> void:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.96, 0.97, 0.99, 1)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.55, 0.62, 0.72, 1)
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_right = 8
	style.corner_radius_bottom_left = 8
	panel.add_theme_stylebox_override("panel", style)
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 5)
	margin.add_child(box)
	var title := Label.new()
	title.text = str(knowledge_item.get("title", "未命名条目"))
	title.add_theme_font_size_override("font_size", 16)
	title.add_theme_color_override("font_color", Color(0.05, 0.2, 0.45, 1))
	box.add_child(title)
	var content := Label.new()
	content.text = str(knowledge_item.get("content", ""))
	content.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	content.add_theme_color_override("font_color", Color(0.12, 0.16, 0.22, 1))
	box.add_child(content)
	knowledge_results_list.add_child(panel)


func _clear_knowledge_results() -> void:
	for child in knowledge_results_list.get_children():
		child.queue_free()


func _on_stats_button_pressed() -> void:
	_hide_menu_overlay()
	stats_overlay.visible = true
	stats_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	_render_stats_overlay()
	call_deferred("_focus_control_if_available", stats_close_button)


func _on_stats_close_button_pressed() -> void:
	stats_overlay.visible = false
	stats_overlay.remove_from_group("dialog_open")
	stats_close_button.release_focus()
	_release_focus_to_world()


func _load_game_stats() -> Dictionary:
	var result: Dictionary = {"games": []}
	if not FileAccess.file_exists(STATS_PATH):
		return result
	var file := FileAccess.open(STATS_PATH, FileAccess.READ)
	if file == null:
		return result
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) == TYPE_DICTIONARY and typeof(parsed.get("games", [])) == TYPE_ARRAY:
		result = parsed
	return result


func _write_game_stats(stats: Dictionary) -> void:
	var file := FileAccess.open(STATS_PATH, FileAccess.WRITE)
	if file == null:
		push_warning("无法保存战绩文件。")
		return
	file.store_string(JSON.stringify(stats, "  "))


func _save_game_stats(summary: Dictionary) -> void:
	var stats := _load_game_stats()
	var games: Array = stats.get("games", [])
	var by_id := _summary_character_lookup(summary)
	var player_character: Dictionary = by_id.get(_current_player_character_id, {})
	if player_character.is_empty():
		return
	var mvp := _compute_mvp_from_summary(summary, by_id)
	var player_camp := str(player_character.get("camp", ""))
	var winner := str(summary.get("winner", ""))
	var record := {
		"game_id": str(summary.get("game_id", "")),
		"date": Time.get_datetime_string_from_system(),
		"player_role": str(player_character.get("role", "")),
		"player_camp": player_camp,
		"won": player_camp == winner,
		"total_days": int(summary.get("total_days", 0)),
		"mvp_name": str(mvp.get("name", "")),
		"mvp_role": str(mvp.get("role_label", "")),
		"mvp_score": int(mvp.get("score", 0)),
		"player_score": _compute_character_score(player_character, by_id),
		"action_counts": _collect_player_action_counts(player_character, by_id),
	}
	games.append(record)
	if games.size() > 200:
		games = games.slice(games.size() - 200, games.size())
	stats["games"] = games
	_write_game_stats(stats)
	_check_new_achievements()


func _summary_character_lookup(summary: Dictionary) -> Dictionary:
	var by_id := {}
	var characters: Variant = summary.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) == TYPE_DICTIONARY:
				by_id[int(character.get("character_id", 0))] = character
	return by_id


func _compute_mvp_from_summary(summary: Dictionary, by_id: Dictionary) -> Dictionary:
	var best := {}
	var characters: Variant = summary.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			var score := _compute_character_score(character, by_id)
			if best.is_empty() or score > int(best.get("score", -99999)):
				best = {
					"name": str(character.get("name", "")),
					"role_label": str(character.get("role_label", "")),
					"score": score,
				}
	return best


func _compute_character_score(character: Dictionary, by_id: Dictionary) -> int:
	var score := 0
	var good_camp := str(character.get("camp", "")) == "good"
	for text in _character_action_texts(character):
		if text.contains("查验") and text.contains("结果为狼人"):
			score += 2
		elif text.contains("成功挡下狼刀"):
			score += 2
		elif text.contains("使用毒药"):
			score += _camp_target_score(text, "对", good_camp, 2, by_id)
		elif text.contains("使用解药"):
			score += 1
		elif text.contains("开枪，"):
			score += _camp_target_score(text, "开枪，", good_camp, 2, by_id)
		elif text.contains("投给"):
			score += _camp_target_score(text, "投给", good_camp, 1, by_id)
		elif text.contains("选择袭击"):
			score += 1
	if str(character.get("outcome", "")).contains("胜利"):
		score += 1
	return score


func _camp_target_score(
	action_text: String,
	marker: String,
	good_voter: bool,
	base: int,
	by_id: Dictionary
) -> int:
	var target_id := _extract_target_id(action_text, marker)
	if target_id <= 0:
		return 0
	var target_camp := str(by_id.get(target_id, {}).get("camp", ""))
	var target_wolf := target_camp == "werewolf"
	if good_voter:
		return base if target_wolf else -base
	return base if not target_wolf else -base


func _extract_target_id(action_text: String, marker: String) -> int:
	var regex := RegEx.new()
	regex.compile(marker + "(\\d+)号")
	var match := regex.search(action_text)
	return int(match.get_string(1)) if match != null else 0


func _character_action_texts(character: Dictionary) -> Array[String]:
	var texts: Array[String] = []
	var actions: Variant = character.get("actions", [])
	if typeof(actions) == TYPE_ARRAY:
		for action in actions:
			if typeof(action) == TYPE_DICTIONARY:
				texts.append(str(action.get("text", "")))
	return texts


func _collect_player_action_counts(character: Dictionary, by_id: Dictionary) -> Dictionary:
	var counts := {
		"wolf_checks": 0,
		"poisons_on_wolves": 0,
		"saves": 0,
		"blocks": 0,
		"hunter_kills": 0,
		"votes_on_wolves": 0,
	}
	var good_camp := str(character.get("camp", "")) == "good"
	for text in _character_action_texts(character):
		if text.contains("查验") and text.contains("结果为狼人"):
			counts["wolf_checks"] = int(counts["wolf_checks"]) + 1
		elif text.contains("成功挡下狼刀"):
			counts["blocks"] = int(counts["blocks"]) + 1
		elif text.contains("使用毒药"):
			var tid := _extract_target_id(text, "对")
			if str(by_id.get(tid, {}).get("camp", "")) == "werewolf":
				counts["poisons_on_wolves"] = int(counts["poisons_on_wolves"]) + 1
		elif text.contains("使用解药"):
			counts["saves"] = int(counts["saves"]) + 1
		elif text.contains("开枪，"):
			var hid := _extract_target_id(text, "开枪，")
			if str(by_id.get(hid, {}).get("camp", "")) == "werewolf":
				counts["hunter_kills"] = int(counts["hunter_kills"]) + 1
		elif text.contains("投给") and good_camp:
			var vid := _extract_target_id(text, "投给")
			if str(by_id.get(vid, {}).get("camp", "")) == "werewolf":
				counts["votes_on_wolves"] = int(counts["votes_on_wolves"]) + 1
	return counts


func _render_stats_overlay() -> void:
	_clear_control_children(stats_body_list)
	var stats := _load_game_stats()
	var games: Array = stats.get("games", [])
	if games.is_empty():
		_append_stats_line("还没有狼人杀对局记录。", false)
		_append_stats_line("", false)
		_render_poker_stats_section(stats)
		return
	var total := games.size()
	var wins := 0
	var by_role := {}
	var action_totals := {
		"wolf_checks": 0, "poisons_on_wolves": 0, "saves": 0,
		"blocks": 0, "hunter_kills": 0, "votes_on_wolves": 0,
	}
	for game in games:
		if bool(game.get("won", false)):
			wins += 1
		var role := str(game.get("player_role", "unknown"))
		var entry: Dictionary = by_role.get(role, {"played": 0, "won": 0})
		entry["played"] = int(entry["played"]) + 1
		if bool(game.get("won", false)):
			entry["won"] = int(entry["won"]) + 1
		by_role[role] = entry
		var counts: Dictionary = game.get("action_counts", {})
		for key in action_totals:
			action_totals[key] = int(action_totals[key]) + int(counts.get(key, 0))
	_append_stats_line(
		"总对局 " + str(total) + " 局 | 胜 " + str(wins) + " 局 | 胜率 "
		+ str(int(round(float(wins) / float(total) * 100))) + "%",
		true
	)
	_append_stats_line("", false)
	_append_stats_line("各身份战绩：", true)
	for role in by_role:
		var entry: Dictionary = by_role[role]
		_append_stats_line(
			_role_display_name(role) + "：" + str(entry["played"]) + " 局 "
			+ str(entry["won"]) + " 胜",
			false
		)
	var last_game: Dictionary = games[games.size() - 1]
	_append_stats_line("", false)
	_append_stats_line(
		"最近一局 MVP：" + str(last_game.get("mvp_name", "无")) + "（"
		+ str(last_game.get("mvp_role", "")) + "，+"
		+ str(last_game.get("mvp_score", 0)) + "）",
		true
	)
	_append_stats_line("", false)
	_append_stats_line("我的常用操作（累计）：", true)
	var action_labels := {
		"wolf_checks": "验到狼",
		"poisons_on_wolves": "毒到狼",
		"saves": "解药救人",
		"blocks": "成功挡刀",
		"hunter_kills": "猎人带走狼",
		"votes_on_wolves": "放逐票命中狼",
	}
	var parts: Array[String] = []
	for key in action_totals:
		if int(action_totals[key]) > 0:
			parts.append(str(action_labels[key]) + " " + str(action_totals[key]) + " 次")
	if parts.is_empty():
		_append_stats_line("暂无记录", false)
	else:
		_append_stats_line("、".join(parts), false)
	_append_stats_line("", false)
	_append_stats_line("成就：", true)
	for achievement in _compute_achievements(stats):
		_append_stats_line(achievement, false)
	_append_stats_line("", false)
	_render_poker_stats_section(stats)


func _render_poker_stats_section(stats: Dictionary) -> void:
	var poker: Dictionary = stats.get("poker", {})
	_append_stats_line(L10n.t("德州扑克战绩："), true)
	_append_stats_line(
		L10n.t("完成 ")
		+ str(poker.get("hands", 0))
		+ L10n.t(" 手 | 净输赢 ")
		+ str(poker.get("chips_net", 0))
		+ L10n.t(" | 单手最大赢 ")
		+ str(poker.get("biggest_win", 0)),
		false,
	)
	_append_stats_line(
		L10n.t("最佳牌型 ")
		+ _poker_category_label(int(poker.get("best_category", -1)))
		+ L10n.t(" | 顺子/同花/葫芦/四条/同花顺胜场 ")
		+ str(poker.get("straight_wins", 0))
		+ "/"
		+ str(poker.get("flush_wins", 0))
		+ "/"
		+ str(poker.get("full_house_wins", 0))
		+ "/"
		+ str(poker.get("quads_wins", 0))
		+ "/"
		+ str(poker.get("straight_flush_wins", 0)),
		false,
	)
	_append_stats_line(
		L10n.t("横扫全场 ")
		+ str(poker.get("sweeps", 0))
		+ L10n.t(" 次 | 单手 500+ ")
		+ str(poker.get("big_wins", 0))
		+ L10n.t(" 次"),
		false,
	)


func _poker_category_label(category: int) -> String:
	match category:
		0: return L10n.t("高牌")
		1: return L10n.t("一对")
		2: return L10n.t("两对")
		3: return L10n.t("三条")
		4: return L10n.t("顺子")
		5: return L10n.t("同花")
		6: return L10n.t("葫芦")
		7: return L10n.t("四条")
		8: return L10n.t("同花顺")
		_:
			return L10n.t("暂无")


func _role_display_name(role: String) -> String:
	match role:
		"seer": return L10n.t("预言家")
		"witch": return L10n.t("女巫")
		"hunter": return L10n.t("猎人")
		"guard": return L10n.t("守卫")
		"werewolf": return L10n.t("狼人")
		"villager": return L10n.t("村民")
		"idiot": return L10n.t("白痴")
		_: return role


func _append_stats_line(text: String, bold: bool) -> void:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_color_override("font_color", Color(0.1, 0.14, 0.2, 1))
	if bold:
		label.add_theme_font_size_override("font_size", 17)
	stats_body_list.add_child(label)


func _build_review_suggestions(summary: Dictionary) -> Array[String]:
	var suggestions: Array[String] = []
	var by_id := _summary_character_lookup(summary)
	var player_character: Dictionary = by_id.get(_current_player_character_id, {})
	if player_character.is_empty():
		return suggestions
	var role := str(player_character.get("role", ""))
	var player_camp := str(player_character.get("camp", ""))
	var won := str(summary.get("winner", "")) == player_camp
	var actions := _character_action_texts(player_character)
	var wolf_checks := 0
	var blocked := false
	var saved := false
	var poisoned_wolf := false
	var shot_wolf := false
	var shot_good := false
	var votes_on_good := 0
	var votes_on_wolf := 0
	for text in actions:
		if text.contains("查验") and text.contains("结果为狼人"):
			wolf_checks += 1
		elif text.contains("成功挡下狼刀"):
			blocked = true
		elif text.contains("使用解药"):
			saved = true
		elif text.contains("使用毒药"):
			var pid := _extract_target_id(text, "对")
			if str(by_id.get(pid, {}).get("camp", "")) == "werewolf":
				poisoned_wolf = true
		elif text.contains("开枪，"):
			var hid := _extract_target_id(text, "开枪，")
			var shot_camp := str(by_id.get(hid, {}).get("camp", ""))
			if shot_camp == "werewolf":
				shot_wolf = true
			elif shot_camp == "good":
				shot_good = true
		elif text.contains("投给"):
			var vid := _extract_target_id(text, "投给")
			var vote_camp := str(by_id.get(vid, {}).get("camp", ""))
			if vote_camp == "werewolf":
				votes_on_wolf += 1
			elif vote_camp == "good":
				votes_on_good += 1
	match role:
		"seer":
			if wolf_checks == 0:
				suggestions.append("预言家：本局没有验到狼。可以优先查验对跳/高嫌疑对象，并在警徽流里提前规划验人顺序。")
			elif not won:
				suggestions.append("预言家：你验到了 " + str(wolf_checks) + " 名狼人但好人最终失利；复盘时可以检查验人信息是否在白天被持续推动。")
		"guard":
			if not blocked and not won:
				suggestions.append("守卫：本局没有成功挡刀。可以优先守护唯一一致预言家或已经明身份的神职。")
		"witch":
			if not saved and not won:
				suggestions.append("女巫：本局没有使用解药。留药太久容易错过节奏，首夜自救与否要结合狼刀习惯判断。")
			if not poisoned_wolf and not won:
				suggestions.append("女巫：本局毒药没有命中狼人。第二夜后可以根据公开票型焦点压毒。")
		"hunter":
			if shot_good:
				suggestions.append("猎人：本局开枪带走了好人。开枪前建议再核对公开证据链与自己的怀疑对象。")
			elif not shot_wolf and not won:
				suggestions.append("猎人：本局没有带走狼人。可以在生前通过发言明确自己的怀疑对象。")
		"villager":
			if votes_on_good > votes_on_wolf and not won:
				suggestions.append("村民：本局放逐票更多落在了好人身上。放逐前建议核对公开证据链、警长归票与对跳关系。")
			elif votes_on_wolf > 0 and won:
				suggestions.append("村民：本局关键放逐票命中了狼人，继续保持对公开证据链的追踪。")
	if player_camp == "werewolf" and not won:
		var exiled_day := _player_exiled_day(player_character)
		if exiled_day == 1:
			suggestions.append("狼人：第一天就被放逐说明暴露过快。可以检查悍跳叙事、站边与队友的公开一致性。")
		else:
			suggestions.append("狼人：本局失利。可以复盘控场时机、刀口选择与卖队友的公开叙事是否一致。")
	return suggestions


func _player_exiled_day(character: Dictionary) -> int:
	var outcome := str(character.get("outcome", ""))
	if not outcome.contains("被放逐出局"):
		return 0
	var regex := RegEx.new()
	regex.compile("第 (\\d+) 天")
	var match := regex.search(outcome)
	return int(match.get_string(1)) if match != null else 0


func _handle_elimination_animation(characters: Variant) -> void:
	var current_alive := {}
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) == TYPE_DICTIONARY:
				current_alive[int(character.get("id", 0))] = bool(character.get("alive", true))
	if _animate_eliminations_on_next_render:
		_animate_eliminations_on_next_render = false
		for character_id in _last_alive_ids:
			if not bool(current_alive.get(int(character_id), false)):
				_animate_character_eliminated(int(character_id))
	_last_alive_ids = current_alive


func _play_night_pulse() -> void:
	var rect := ColorRect.new()
	rect.color = Color(0.02, 0.03, 0.08, 0.0)
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	var parent := get_tree().current_scene
	if parent == null:
		return
	parent.add_child(rect)
	var tween := create_tween()
	tween.tween_property(rect, "color:a", 0.42, 0.35)
	tween.tween_property(rect, "color:a", 0.0, 0.9)
	tween.tween_callback(rect.queue_free)


func _animate_character_eliminated(character_id: int) -> void:
	var target: Node2D = null
	if character_id == _current_player_character_id:
		target = player
	else:
		for npc in get_tree().get_nodes_in_group("npc"):
			if int(npc.call("get_wolf_character_id")) == character_id:
				target = npc
				break
	if target == null:
		return
	var original_modulate := target.modulate
	var original_scale := target.scale
	var flash := create_tween()
	for i in range(3):
		flash.tween_property(target, "modulate", Color(1, 0.25, 0.25, original_modulate.a), 0.12)
		flash.tween_property(target, "modulate", original_modulate, 0.12)
	flash.tween_property(target, "scale", original_scale * 0.8, 0.2)
	flash.tween_property(target, "scale", original_scale, 0.25)
	await get_tree().create_timer(0.35).timeout
	var label := Label.new()
	label.text = "出局"
	label.add_theme_font_size_override("font_size", 26)
	label.add_theme_color_override("font_color", Color(1, 0.25, 0.25, 1))
	label.add_theme_constant_override("outline_size", 8)
	label.add_theme_color_override("font_outline_color", Color(0.08, 0.04, 0.04, 1))
	label.z_index = 100
	var parent := get_tree().current_scene
	if parent != null:
		parent.add_child(label)
		label.global_position = target.global_position + Vector2(-20, -70)
		var float_tween := create_tween()
		float_tween.tween_property(
			label,
			"global_position",
			label.global_position + Vector2(0, -38),
			1.0
		)
		float_tween.parallel().tween_property(label, "modulate:a", 0.0, 1.0)
		float_tween.tween_callback(label.queue_free)
	_play_sfx("eliminate")


func _on_save_button_pressed() -> void:
	if _current_wolf_game_id.is_empty():
		wolf_status_label.text = "后端状态：还没有可保存的对局"
		return
	if _is_requesting:
		return
	_is_requesting = true
	wolf_status_label.text = "后端状态：正在保存进度..."
	var url := WOLF_GAME_STATE_URL_PREFIX + _current_wolf_game_id.uri_encode() + "/save"
	var error := save_game_request.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, "{}")
	if error != OK:
		_is_requesting = false
		wolf_status_label.text = "后端状态：保存失败"


func _on_save_game_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	_is_requesting = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：保存失败"
		return
	wolf_status_label.text = "后端状态：已保存到本地存档"
	_hide_menu_overlay()
	dialog_box.call("show_notice", L10n.t("存盘"), L10n.t("进度已保存到本地存档。"))


func _on_bgm_volume_changed(value: float) -> void:
	_bgm_volume = value
	_apply_audio_volumes()
	_save_session_preferences()


func _on_sfx_volume_changed(value: float) -> void:
	_sfx_volume = value
	_apply_audio_volumes()
	_save_session_preferences()


func _apply_audio_volumes() -> void:
	if _audio_bgm_day != null:
		_audio_bgm_day.volume_db = lerpf(-28.0, -6.0, _bgm_volume / 100.0)
	if _audio_bgm_night != null:
		_audio_bgm_night.volume_db = lerpf(-30.0, -8.0, _bgm_volume / 100.0)
	if _audio_sfx != null:
		_audio_sfx.volume_db = lerpf(-20.0, -2.0, _sfx_volume / 100.0)


func _on_menu_button_pressed() -> void:
	menu_overlay.visible = true
	menu_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	call_deferred("_focus_control_if_available", menu_close_button)


func _on_menu_close_button_pressed() -> void:
	menu_overlay.visible = false
	menu_overlay.remove_from_group("dialog_open")
	menu_close_button.release_focus()
	_release_focus_to_world()


func _hide_menu_overlay() -> void:
	if menu_overlay.visible:
		_on_menu_close_button_pressed()


func _on_load_button_pressed() -> void:
	_hide_menu_overlay()
	_render_load_slots()
	load_overlay.visible = true
	load_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	call_deferred("_focus_control_if_available", load_close_button)


func _on_load_close_button_pressed() -> void:
	load_overlay.visible = false
	load_overlay.remove_from_group("dialog_open")
	load_close_button.release_focus()
	_release_focus_to_world()


func _render_load_slots() -> void:
	var config := ConfigFile.new()
	config.load(SESSION_SETTINGS_PATH)
	for slot_index in range(load_slot_info_labels.size()):
		var game_id: Variant = config.get_value(
			SESSION_SETTINGS_SECTION,
			"slot_" + str(slot_index + 1) + "_game_id",
			"",
		)
		var player_name: Variant = config.get_value(
			SESSION_SETTINGS_SECTION,
			"slot_" + str(slot_index + 1) + "_player_name",
			"",
		)
		var game_id_text := (
			str(game_id)
			if typeof(game_id) == TYPE_STRING and not str(game_id).is_empty()
			else ""
		)
		var has_save := not game_id_text.is_empty()
		var info := L10n.t("空") if not has_save else game_id_text
		var name_text := (
			str(player_name)
			if typeof(player_name) == TYPE_STRING and not str(player_name).is_empty()
			else ""
		)
		if has_save and not name_text.is_empty():
			info += " · " + name_text
		load_slot_info_labels[slot_index].text = info
		load_slot_buttons[slot_index].disabled = not has_save


func _on_load_slot_pressed(slot_index: int) -> void:
	if _is_starting_wolf_game or _is_loading_wolf_state:
		return
	_session_slot = slot_index
	var config := ConfigFile.new()
	config.load(SESSION_SETTINGS_PATH)
	_apply_session_slot(config)
	_save_session_preferences()
	_on_load_close_button_pressed()
	if _current_wolf_game_id.is_empty():
		wolf_status_label.text = L10n.t("后端状态：") + L10n.t("这个存档槽位是空的")
		return
	_on_continue_game_button_pressed()


func _on_spectate_button_pressed() -> void:
	_hide_menu_overlay()
	spectate_overlay.visible = true
	spectate_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	_request_spectate_games()
	call_deferred("_focus_control_if_available", spectate_close_button)


func _on_spectate_close_button_pressed() -> void:
	spectate_poll_timer.stop()
	_spectate_current_game_id = ""
	spectate_overlay.visible = false
	spectate_overlay.remove_from_group("dialog_open")
	spectate_close_button.release_focus()
	_release_focus_to_world()


func _on_spectate_refresh_button_pressed() -> void:
	_request_spectate_games()


func _request_spectate_games() -> void:
	var error := spectate_games_request.request(SPECTATE_GAMES_URL, [], HTTPClient.METHOD_GET)
	if error != OK:
		spectate_phase_label.text = L10n.t("后端未连接")


func _on_spectate_games_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		spectate_phase_label.text = L10n.t("后端未连接")
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK or typeof(json.data) != TYPE_ARRAY:
		spectate_phase_label.text = L10n.t("暂无进行中的对局")
		return
	var games: Array = json.data
	spectate_game_select.clear()
	if games.is_empty():
		spectate_game_select.add_item(L10n.t("暂无进行中的对局"), 0)
		spectate_phase_label.text = L10n.t("暂无进行中的对局")
		spectate_poll_timer.stop()
		_spectate_current_game_id = ""
		_clear_spectate_view()
		return
	for game in games:
		var label := (
			str(game.get("game_id", ""))
			+ " · "
			+ L10n.t("第 ")
			+ str(game.get("day", 1))
			+ L10n.t(" 天")
			+ " · "
			+ str(game.get("player_name", ""))
		)
		spectate_game_select.add_item(label)
		spectate_game_select.set_item_metadata(
			spectate_game_select.get_item_count() - 1,
			str(game.get("game_id", "")),
		)
	_spectate_current_game_id = str(spectate_game_select.get_item_metadata(0))
	spectate_game_select.selected = 0
	_request_spectate_snapshot()
	spectate_poll_timer.start()


func _on_spectate_game_selected(_index: int) -> void:
	if spectate_game_select.get_item_count() == 0:
		return
	_spectate_current_game_id = str(spectate_game_select.get_item_metadata(spectate_game_select.selected))
	_request_spectate_snapshot()
	if spectate_poll_timer.is_stopped():
		spectate_poll_timer.start()


func _request_spectate_snapshot() -> void:
	if _spectate_current_game_id.is_empty():
		return
	spectate_request.request(
		SPECTATE_URL_PREFIX + _spectate_current_game_id.uri_encode(),
		[],
		HTTPClient.METHOD_GET,
	)


func _on_spectate_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		spectate_phase_label.text = L10n.t("读取失败")
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK or typeof(json.data) != TYPE_DICTIONARY:
		return
	_render_spectate_view(json.data)


func _clear_spectate_view() -> void:
	_clear_control_children(spectate_character_grid)
	_clear_control_children(spectate_timeline_list)
	spectate_day_label.text = ""
	spectate_winner_label.text = ""
	spectate_phase_label.text = L10n.t("等待对局")


func _spectate_phase_label(phase: String) -> String:
	match phase:
		"NIGHT":
			return "🌙 " + L10n.t("夜晚")
		"HUNTER_SHOT":
			return "🔫 " + L10n.t("猎人开枪")
		"SHERIFF_SIGNUP":
			return "🚨 " + L10n.t("警上报名")
		"SHERIFF_SPEECH":
			return "🚨 " + L10n.t("警上发言")
		"SHERIFF_WITHDRAWAL":
			return "🚨 " + L10n.t("退水阶段")
		"SHERIFF_VOTE":
			return "🗳 " + L10n.t("警长投票")
		"SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE":
			return "⚖️ " + L10n.t("警上 PK")
		"MEETING_ORDER":
			return "🗣 " + L10n.t("警长选发言侧")
		"DAY_MEETING":
			return "☀️ " + L10n.t("白天会议")
		"SHERIFF_NOMINATION":
			return "🗣 " + L10n.t("警长归票")
		"FREE_ACTIVITY":
			return "🚶 " + L10n.t("自由活动")
		"VOTE":
			return "🗳 " + L10n.t("投票阶段")
		"BADGE_TRANSFER":
			return "🎖 " + L10n.t("移交警徽")
		"GAME_OVER":
			return "🏁 " + L10n.t("游戏结束")
		_:
			return phase


func _render_spectate_view(data: Dictionary) -> void:
	spectate_phase_label.text = _spectate_phase_label(str(data.get("phase", "")))
	spectate_day_label.text = L10n.t("第 ") + str(data.get("day", 0)) + L10n.t(" 天")
	var winner := str(data.get("winner", ""))
	spectate_winner_label.text = (
		L10n.t("好人胜利")
		if winner == "good"
		else (L10n.t("狼人胜利") if winner == "werewolf" else "")
	)

	_clear_control_children(spectate_character_grid)
	var characters: Array = data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) == TYPE_DICTIONARY:
				spectate_character_grid.add_child(_build_spectate_character_card(character))

	_clear_control_children(spectate_timeline_list)
	var rows: Array[String] = []
	var timeline: Dictionary = data.get("public_evidence_timeline", {})
	var timeline_items: Variant = timeline.get("items", [])
	if typeof(timeline_items) == TYPE_ARRAY:
		for item in timeline_items:
			if typeof(item) == TYPE_DICTIONARY and not str(item.get("display_text", "")).is_empty():
				rows.append("◇ " + str(item.get("display_text", "")))
	var intel: Array = data.get("public_intel", [])
	if typeof(intel) == TYPE_ARRAY:
		for claim in intel:
			if typeof(claim) == TYPE_DICTIONARY and not str(claim.get("display_text", "")).is_empty():
				rows.append("◆ " + str(claim.get("display_text", "")))
	var logs: Array = data.get("public_logs", [])
	if typeof(logs) == TYPE_ARRAY:
		for log in logs:
			rows.append("● " + str(log))
	if rows.is_empty():
		rows.append(L10n.t("暂无时间线。"))
	for row in rows:
		var label := Label.new()
		label.text = row
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		spectate_timeline_list.add_child(label)


func _build_spectate_character_card(character: Dictionary) -> Control:
	var box := VBoxContainer.new()
	var name_line := Label.new()
	name_line.text = str(character.get("id", "?")) + L10n.t("号 ") + str(character.get("name", "?"))
	var tags: Array[String] = []
	if bool(character.get("is_player", false)):
		tags.append(L10n.t("玩家"))
	if bool(character.get("is_sheriff", false)):
		tags.append(L10n.t("警长"))
	if bool(character.get("idiot_flipped", false)):
		tags.append(L10n.t("白痴翻牌"))
	if not tags.is_empty():
		name_line.text += " [" + ", ".join(tags) + "]"
	if not bool(character.get("alive", true)):
		name_line.add_theme_color_override("font_color", Color(0.55, 0.6, 0.68))
	box.add_child(name_line)
	var meta := Label.new()
	var status := L10n.t("存活") if bool(character.get("alive", true)) else L10n.t("已出局")
	var claimed_role := str(character.get("claimed_role", ""))
	if not claimed_role.is_empty():
		status += " · " + L10n.t("声明：") + _role_display_name(claimed_role)
	meta.text = status
	meta.add_theme_font_size_override("font_size", 12)
	box.add_child(meta)
	return box


func _on_venue_door_requested(door_kind: String) -> void:
	if door_kind == "boardgame":
		_show_game_setup()
	else:
		_open_poker_table()


func _open_poker_table() -> void:
	if _poker_requesting:
		return
	_poker_requesting = true
	_close_secondary_overlays()
	poker_overlay.visible = true
	poker_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	poker_phase_label.text = L10n.t("正在开桌...")
	_set_poker_controls_enabled(false)
	var player_name := str(player_name_input.text.strip_edges())
	if player_name.is_empty():
		player_name = "玩家"
	var body := {
		"player_name": player_name,
		"npc_count": 5,
		"buy_in": 1000,
	}
	var error := poker_request.request(
		POKER_TABLE_URL,
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		JSON.stringify(body),
	)
	if error != OK:
		_poker_requesting = false
		poker_phase_label.text = L10n.t("后端未连接")
	call_deferred("_focus_control_if_available", poker_close_button)


func _close_secondary_overlays() -> void:
	_hide_menu_overlay()
	stats_overlay.visible = false
	archive_overlay.visible = false
	knowledge_overlay.visible = false
	load_overlay.visible = false
	spectate_overlay.visible = false
	spectate_poll_timer.stop()
	game_summary_overlay.visible = false
	if game_setup_overlay.visible:
		game_setup_overlay.visible = false
		game_setup_overlay.remove_from_group("dialog_open")


func _on_poker_close_button_pressed() -> void:
	_poker_table_id = ""
	_poker_state = {}
	poker_overlay.visible = false
	poker_overlay.remove_from_group("dialog_open")
	poker_close_button.release_focus()
	_update_npc_roaming()
	_release_focus_to_world()


func _on_poker_action_pressed(action: String, amount: int) -> void:
	if _poker_requesting or _poker_table_id.is_empty():
		return
	_poker_requesting = true
	_set_poker_controls_enabled(false)
	var body := {"action": action, "amount": amount}
	var error := poker_request.request(
		POKER_URL_PREFIX + _poker_table_id.uri_encode() + "/act",
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		JSON.stringify(body),
	)
	if error != OK:
		_poker_requesting = false
		_set_poker_controls_from_state(_poker_state)


func _on_poker_raise_pressed() -> void:
	_on_poker_action_pressed("raise", int(poker_raise_slider.value))


func _on_poker_all_in_pressed() -> void:
	var player := _poker_player_dict(_poker_state)
	var total := int(player.get("street_bet", 0)) + int(player.get("stack", 0))
	_on_poker_action_pressed("raise", total)


func _on_poker_raise_slider_changed(value: float) -> void:
	poker_raise_value_label.text = L10n.t("加注到 ") + str(int(value))


func _on_poker_next_hand_pressed() -> void:
	if _poker_requesting or _poker_table_id.is_empty():
		return
	_poker_requesting = true
	_set_poker_controls_enabled(false)
	var error := poker_request.request(
		POKER_URL_PREFIX + _poker_table_id.uri_encode() + "/next-hand",
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		"{}",
	)
	if error != OK:
		_poker_requesting = false
		_set_poker_controls_from_state(_poker_state)


func _on_poker_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray,
) -> void:
	_poker_requesting = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		poker_phase_label.text = L10n.t("后端未连接")
		_set_poker_controls_from_state(_poker_state)
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK or typeof(json.data) != TYPE_DICTIONARY:
		return
	var data: Dictionary = json.data
	if data.has("table_id"):
		_poker_table_id = str(data.get("table_id", ""))
		_poker_state = data.get("state", {})
	else:
		_poker_state = data
	_render_poker_state(_poker_state)
	_update_npc_roaming()


func _poker_player_dict(state: Dictionary) -> Dictionary:
	for player in state.get("players", []):
		if typeof(player) == TYPE_DICTIONARY and bool(player.get("is_player", false)):
			return player
	return {}


func _poker_phase_label(phase: String) -> String:
	match phase:
		"preflop":
			return L10n.t("翻牌前")
		"flop":
			return L10n.t("翻牌")
		"turn":
			return L10n.t("转牌")
		"river":
			return L10n.t("河牌")
		"showdown":
			return L10n.t("摊牌")
		"finished":
			return L10n.t("本手结束")
		_:
			return phase


func _render_poker_state(state: Dictionary) -> void:
	poker_phase_label.text = _poker_phase_label(str(state.get("phase", "")))
	poker_pot_label.text = L10n.t("底池：") + str(state.get("pot", 0))
	poker_hand_label.text = L10n.t("手牌 ") + str(state.get("hand_number", 0))
	poker_result_label.text = str(state.get("result_message", ""))

	var community: Array = state.get("community", [])
	if typeof(community) == TYPE_ARRAY and not community.is_empty():
		poker_community_label.text = L10n.t("公共牌：") + " ".join(community)
	else:
		poker_community_label.text = L10n.t("公共牌：—")

	_clear_control_children(poker_players_list)
	var current_actor := int(state.get("current_actor", -1))
	var phase := str(state.get("phase", ""))
	for player in state.get("players", []):
		if typeof(player) != TYPE_DICTIONARY:
			continue
		poker_players_list.add_child(_build_poker_player_row(player, current_actor, phase))
	_set_poker_controls_from_state(state)
	_record_poker_result(state)


func _record_poker_result(state: Dictionary) -> void:
	var showdown: Variant = state.get("last_showdown", null)
	if typeof(showdown) != TYPE_DICTIONARY:
		return
	var hand_number := int(state.get("hand_number", 0))
	if hand_number == _poker_recorded_hand_number:
		return
	_poker_recorded_hand_number = hand_number
	var player_won := bool(showdown.get("player_won", false))
	var player_net := int(showdown.get("player_net", 0))
	var category := int(showdown.get("category", -1))
	var player_category := int(showdown.get("player_category", -1))
	var stats := _load_game_stats()
	var poker: Dictionary = stats.get("poker", {})
	poker["hands"] = int(poker.get("hands", 0)) + 1
	poker["chips_net"] = int(poker.get("chips_net", 0)) + player_net
	poker["wins"] = int(poker.get("wins", 0)) + (1 if player_won else 0)
	poker["biggest_win"] = maxi(int(poker.get("biggest_win", 0)), maxi(0, player_net))
	poker["best_category"] = maxi(
		int(poker.get("best_category", -1)),
		maxi(player_category, category if player_won else -1),
	)
	if player_won:
		if category >= 4:
			poker["straight_wins"] = int(poker.get("straight_wins", 0)) + 1
		if category >= 5:
			poker["flush_wins"] = int(poker.get("flush_wins", 0)) + 1
		if category >= 6:
			poker["full_house_wins"] = int(poker.get("full_house_wins", 0)) + 1
		if category >= 7:
			poker["quads_wins"] = int(poker.get("quads_wins", 0)) + 1
		if category >= 8:
			poker["straight_flush_wins"] = int(poker.get("straight_flush_wins", 0)) + 1
		if _poker_sweep(state):
			poker["sweeps"] = int(poker.get("sweeps", 0)) + 1
		if player_net >= 500:
			poker["big_wins"] = int(poker.get("big_wins", 0)) + 1
	var history: Array = poker.get("history", [])
	history.append({
		"hand": hand_number,
		"net": player_net,
		"won": player_won,
		"category": player_category,
	})
	if history.size() > 20:
		history = history.slice(history.size() - 20, history.size())
	poker["history"] = history
	stats["poker"] = poker
	_write_game_stats(stats)
	_check_new_achievements()


func _poker_sweep(state: Dictionary) -> bool:
	for player in state.get("players", []):
		if typeof(player) == TYPE_DICTIONARY and not bool(player.get("is_player", false)):
			if int(player.get("stack", 0)) > 0:
				return false
	return true


func _build_poker_player_row(player: Dictionary, current_actor: int, phase: String) -> Control:
	var row := HBoxContainer.new()
	var name_label := Label.new()
	var is_player := bool(player.get("is_player", false))
	name_label.text = (
		(L10n.t("玩家") if is_player else str(player.get("name", "?")))
		+ " "
		+ L10n.t("筹码：")
		+ str(player.get("stack", 0))
	)
	if bool(player.get("won_this_hand", false)):
		name_label.text += " " + L10n.t("已胜出")
	if int(player.get("seat", -1)) == current_actor and phase not in ["showdown", "finished"]:
		name_label.text += " " + L10n.t("行动中")
	row.add_child(name_label)
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var detail := Label.new()
	var parts: Array[String] = []
	if bool(player.get("folded", false)):
		parts.append(L10n.t("已弃牌"))
	if bool(player.get("all_in", false)):
		parts.append(L10n.t("全下"))
	if int(player.get("street_bet", 0)) > 0:
		parts.append(L10n.t("本街 ") + str(player.get("street_bet", 0)))
	if is_player:
		var hole: Array = player.get("hole_cards", [])
		if typeof(hole) == TYPE_ARRAY and not hole.is_empty():
			parts.append(L10n.t("手牌：") + " ".join(hole))
	detail.text = "  ".join(parts)
	row.add_child(detail)
	if bool(player.get("folded", false)):
		for child in [name_label, detail]:
			child.add_theme_color_override("font_color", Color(0.55, 0.6, 0.68))
	return row


func _set_poker_controls_enabled(enabled: bool) -> void:
	poker_fold_button.disabled = not enabled
	poker_check_call_button.disabled = not enabled
	poker_raise_button.disabled = not enabled
	poker_all_in_button.disabled = not enabled
	poker_raise_slider.editable = enabled
	poker_next_hand_button.disabled = not enabled


func _set_poker_controls_from_state(state: Dictionary) -> void:
	if state.is_empty():
		_set_poker_controls_enabled(false)
		return
	var phase := str(state.get("phase", ""))
	if phase in ["showdown", "finished"]:
		poker_fold_button.disabled = true
		poker_check_call_button.disabled = true
		poker_raise_button.disabled = true
		poker_all_in_button.disabled = true
		poker_raise_slider.editable = false
		poker_next_hand_button.disabled = false
		return
	var player := _poker_player_dict(state)
	var is_turn := int(state.get("current_actor", -1)) == int(player.get("seat", -1))
	var can_act := is_turn and not bool(player.get("folded", false)) and not bool(player.get("all_in", false))
	poker_fold_button.disabled = not can_act
	poker_check_call_button.disabled = not can_act
	poker_raise_button.disabled = not can_act
	poker_all_in_button.disabled = not can_act
	poker_raise_slider.editable = can_act
	poker_next_hand_button.disabled = true
	if can_act:
		var to_call := maxi(0, int(state.get("current_bet", 0)) - int(player.get("street_bet", 0)))
		if to_call == 0:
			poker_check_call_button.text = L10n.t("过牌")
		else:
			poker_check_call_button.text = L10n.t("跟注 ") + str(to_call)
		var min_raise := maxi(20, int(state.get("min_raise", 20)))
		var max_raise := int(player.get("street_bet", 0)) + int(player.get("stack", 0))
		poker_raise_slider.min_value = float(mini(min_raise, max_raise))
		poker_raise_slider.max_value = float(maxi(min_raise, max_raise))
		poker_raise_slider.value = float(mini(min_raise, max_raise))
		poker_raise_value_label.text = L10n.t("加注到 ") + str(int(poker_raise_slider.value))


func _on_archive_button_pressed() -> void:
	_hide_menu_overlay()
	archive_overlay.visible = true
	archive_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	archive_status_label.text = "加载中..."
	_clear_control_children(archive_list_box)
	var error := archive_request.request(NPCS_URL, [], HTTPClient.METHOD_GET)
	if error != OK:
		archive_status_label.text = "加载失败：请确认后端已启动。"
	call_deferred("_focus_control_if_available", archive_close_button)


func _on_archive_close_button_pressed() -> void:
	archive_overlay.visible = false
	archive_overlay.remove_from_group("dialog_open")
	archive_close_button.release_focus()
	_release_focus_to_world()


func _on_archive_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		archive_status_label.text = "加载失败：后端不可用。"
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK or typeof(json.data) != TYPE_ARRAY:
		archive_status_label.text = "加载失败：响应格式不正确。"
		return
	var profiles: Array = json.data
	archive_status_label.text = "共 " + str(profiles.size()) + " 位角色"
	for profile in profiles:
		if typeof(profile) != TYPE_DICTIONARY:
			continue
		_append_archive_card(profile)


func _append_archive_card(profile: Dictionary) -> void:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.96, 0.97, 0.99, 1)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.55, 0.62, 0.72, 1)
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_right = 8
	style.corner_radius_bottom_left = 8
	panel.add_theme_stylebox_override("panel", style)
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)
	margin.add_child(box)
	var title := Label.new()
	title.text = str(profile.get("npc_name", "未知")) + " · " + str(profile.get("role", ""))
	title.add_theme_font_size_override("font_size", 16)
	title.add_theme_color_override("font_color", Color(0.05, 0.2, 0.45, 1))
	box.add_child(title)
	var personality := Label.new()
	personality.text = str(profile.get("personality", ""))
	personality.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	personality.add_theme_color_override("font_color", Color(0.12, 0.16, 0.22, 1))
	box.add_child(personality)
	var catchphrases: Variant = profile.get("catchphrases", [])
	if typeof(catchphrases) == TYPE_ARRAY and not catchphrases.is_empty():
		var tags := Label.new()
		var phrase_list: Array[String] = []
		for phrase in catchphrases:
			phrase_list.append(str(phrase))
		tags.text = "口头禅：" + "、".join(phrase_list)
		tags.add_theme_color_override("font_color", Color(0.3, 0.35, 0.45, 1))
		box.add_child(tags)
	archive_list_box.add_child(panel)


func _build_highlights(summary: Dictionary) -> Array[String]:
	var highlights: Array[String] = []
	var by_id := _summary_character_lookup(summary)
	var seer_wolf: String = ""
	var hunter_wolf: String = ""
	var witch_wolf: String = ""
	var characters: Variant = summary.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			var role := str(character.get("role", ""))
			var label := str(character.get("character_id", "?")) + "号 " + str(character.get("name", ""))
			for action in character.get("actions", []):
				if typeof(action) != TYPE_DICTIONARY:
					continue
				var text := str(action.get("text", ""))
				if role == "seer" and text.contains("查验") and text.contains("结果为狼人") and seer_wolf.is_empty():
					seer_wolf = label
				elif role == "hunter" and text.contains("开枪，"):
					var hid := _extract_target_id(text, "开枪，")
					if str(by_id.get(hid, {}).get("camp", "")) == "werewolf" and hunter_wolf.is_empty():
						hunter_wolf = label
				elif role == "witch" and text.contains("使用毒药"):
					var pid := _extract_target_id(text, "对")
					if str(by_id.get(pid, {}).get("camp", "")) == "werewolf" and witch_wolf.is_empty():
						witch_wolf = label
	var first_exile_wolf: String = ""
	var timeline: Variant = summary.get("timeline", [])
	if typeof(timeline) == TYPE_ARRAY:
		for event in timeline:
			if typeof(event) != TYPE_DICTIONARY:
				continue
			var text := str(event.get("text", ""))
			if text.contains("在白天被投票放逐出局"):
				var regex := RegEx.new()
				regex.compile("(\\d+)号")
				var match := regex.search(text)
				if match != null:
					var tid := int(match.get_string(1))
					if str(by_id.get(tid, {}).get("camp", "")) == "werewolf":
						first_exile_wolf = str(tid) + "号 " + str(by_id.get(tid, {}).get("name", ""))
				break
	if not seer_wolf.is_empty():
		highlights.append("🌟 预言家 " + seer_wolf + " 验出了狼人。")
	if not hunter_wolf.is_empty():
		highlights.append("🌟 猎人 " + hunter_wolf + " 一枪带走了狼人。")
	if not witch_wolf.is_empty():
		highlights.append("🌟 女巫 " + witch_wolf + " 毒中了狼人。")
	if not first_exile_wolf.is_empty():
		highlights.append("🌟 开局首日就放逐了狼人 " + first_exile_wolf + "。")
	if highlights.is_empty():
		highlights.append("本局平稳推进，没有特别戏剧性的场面。")
	return highlights


func _achievement_entries(stats: Dictionary) -> Array:
	var entries: Array = []
	var games: Array = stats.get("games", [])
	var total := games.size()
	if total >= 1:
		entries.append({"key": "first_game", "label": "✅ 初来乍到：完成 1 局"})
	if total >= 10:
		entries.append({"key": "veteran_10", "label": "✅ 十局老兵：完成 10 局"})
	var wins := 0
	var best_streak := 0
	var streak := 0
	var role_wins := {}
	var player_mvp := 0
	var wolf_checks := 0
	var votes_on_wolves := 0
	for game in games:
		var won := bool(game.get("won", false))
		if won:
			wins += 1
			streak += 1
		else:
			streak = 0
		best_streak = maxi(best_streak, streak)
		if won:
			var role := str(game.get("player_role", ""))
			role_wins[role] = int(role_wins.get(role, 0)) + 1
		var counts: Dictionary = game.get("action_counts", {})
		wolf_checks += int(counts.get("wolf_checks", 0))
		votes_on_wolves += int(counts.get("votes_on_wolves", 0))
		if (
			int(game.get("mvp_score", 0)) > 0
			and int(game.get("player_score", 0)) >= int(game.get("mvp_score", 0))
		):
			player_mvp += 1
	if wins >= 1:
		entries.append({"key": "first_win", "label": "✅ 首胜"})
	if best_streak >= 3:
		entries.append({"key": "streak_3", "label": "✅ 常胜将军：连胜 3 局"})
	if int(role_wins.get("seer", 0)) >= 1:
		entries.append({"key": "seer_win", "label": "✅ 预言家之光"})
	if int(role_wins.get("witch", 0)) >= 1:
		entries.append({"key": "witch_win", "label": "✅ 女巫救世"})
	if int(role_wins.get("werewolf", 0)) >= 1:
		entries.append({"key": "wolf_win", "label": "✅ 狼王加冕"})
	if player_mvp >= 1:
		entries.append({"key": "mvp", "label": "✅ 关键先生：成为本局 MVP"})
	if wolf_checks >= 3:
		entries.append({"key": "seer_checks_3", "label": "✅ 火眼金睛：累计验到 3 名狼人"})
	if votes_on_wolves >= 10:
		entries.append({"key": "exile_votes_10", "label": "✅ 放逐大师：累计 10 次放逐票命中狼人"})
	var poker: Dictionary = stats.get("poker", {})
	if int(poker.get("hands", 0)) >= 1:
		entries.append({"key": "poker_first_hand", "label": "🃏 第一手牌：完成 1 手扑克"})
	if int(poker.get("hands", 0)) >= 100:
		entries.append({"key": "poker_100_hands", "label": "🃏 百手老手：累计 100 手扑克"})
	if int(poker.get("wins", 0)) >= 1:
		entries.append({"key": "poker_first_win", "label": "🃏 扑克首胜"})
	if int(poker.get("straight_wins", 0)) >= 1:
		entries.append({"key": "poker_straight_win", "label": "♠️ 顺子赢家：用顺子及以上赢下一手"})
	if int(poker.get("flush_wins", 0)) >= 1:
		entries.append({"key": "poker_flush_win", "label": "♥️ 同花赢家"})
	if int(poker.get("full_house_wins", 0)) >= 1:
		entries.append({"key": "poker_full_house_win", "label": "🂡 葫芦赢家"})
	if int(poker.get("quads_wins", 0)) >= 1:
		entries.append({"key": "poker_quads_win", "label": "🃏 四条赢家"})
	if int(poker.get("straight_flush_wins", 0)) >= 1:
		entries.append({"key": "poker_straight_flush_win", "label": "✨ 同花顺赢家"})
	if int(poker.get("sweeps", 0)) >= 1:
		entries.append({"key": "poker_sweep", "label": "💰 横扫全场：单局赢光所有 NPC"})
	if int(poker.get("big_wins", 0)) >= 1:
		entries.append({"key": "poker_big_win", "label": "💎 筹码大亨：单手净赢 500+"})
	return entries


func _compute_achievements(stats: Dictionary) -> Array[String]:
	var achievements: Array[String] = []
	for entry in _achievement_entries(stats):
		achievements.append(str(entry.get("label", "")))
	if achievements.is_empty():
		achievements.append("🔒 完成第一局解锁成就")
	return achievements


func _load_unlocked_achievements() -> Dictionary:
	var unlocked := {}
	var config := ConfigFile.new()
	if config.load(ACHIEVEMENTS_PATH) == OK:
		var keys: Variant = config.get_value(ACHIEVEMENTS_SECTION, "unlocked", [])
		if typeof(keys) == TYPE_ARRAY:
			for key in keys:
				unlocked[str(key)] = true
	return unlocked


func _save_unlocked_achievements(keys: Array) -> void:
	var config := ConfigFile.new()
	config.load(ACHIEVEMENTS_PATH)
	config.set_value(ACHIEVEMENTS_SECTION, "unlocked", keys)
	config.save(ACHIEVEMENTS_PATH)


func _check_new_achievements() -> void:
	var stats := _load_game_stats()
	var unlocked := _load_unlocked_achievements()
	var entries := _achievement_entries(stats)
	var all_keys: Array = []
	var new_labels: Array[String] = []
	for entry in entries:
		var key := str(entry.get("key", ""))
		all_keys.append(key)
		if not key.is_empty() and not unlocked.has(key):
			new_labels.append(str(entry.get("label", "")))
	if new_labels.is_empty():
		return
	_save_unlocked_achievements(all_keys)
	for label in new_labels:
		_achievement_toast_queue.append(label)
	_show_next_achievement_toast()


func _show_next_achievement_toast() -> void:
	if _achievement_toast_queue.is_empty():
		return
	achievement_toast_label.text = _achievement_toast_queue.pop_front()
	achievement_toast.pivot_offset = achievement_toast.size / 2.0
	achievement_toast.visible = true
	achievement_toast.modulate.a = 1.0
	achievement_toast.position = Vector2(achievement_toast.position.x, -90.0)
	achievement_toast.scale = Vector2(0.82, 0.82)
	_play_achievement_chime()
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(achievement_toast, "position:y", 10.0, 0.30).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(achievement_toast, "scale", Vector2(1.0, 1.0), 0.30).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.chain().tween_interval(2.6)
	tween.chain().tween_property(achievement_toast, "modulate:a", 0.0, 0.5)
	tween.chain().tween_callback(func() -> void:
		achievement_toast.visible = false
		_show_next_achievement_toast()
	)


func _build_achievement_chime() -> AudioStreamWAV:
	var mix_rate := 22050
	var sample_count := int(mix_rate * 1.1)
	var data := PackedByteArray()
	data.resize(sample_count * 2)
	var notes := [523.25, 659.25, 783.99, 1046.5]
	var note_samples := int(mix_rate * 0.22)
	var index := 0
	for note_index in range(notes.size()):
		var freq := float(notes[note_index])
		for i in range(note_samples):
			if index >= sample_count:
				break
			var t := float(i) / mix_rate
			var decay := exp(-3.0 * t)
			var envelope := minf(1.0, float(note_samples - i) / (note_samples * 0.2))
			var sample_value := sin(TAU * freq * t) * envelope * decay * 0.42
			data.encode_s16(index * 2, int(clampf(sample_value, -1.0, 1.0) * 32767.0))
			index += 1
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = mix_rate
	wav.stereo = false
	wav.data = data
	return wav


func _play_achievement_chime() -> void:
	if not _sound_enabled or _audio_sfx == null:
		return
	if _achievement_chime == null:
		_achievement_chime = _build_achievement_chime()
	_audio_sfx.stream = _achievement_chime
	_audio_sfx.play()


func _export_text_file(path_name: String, content: String) -> String:
	var dir := DirAccess.open("user://")
	if dir == null or not dir.dir_exists("exports"):
		if dir != null:
			dir.make_dir_recursive("exports")
	var path := "user://exports/" + path_name
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return ""
	file.store_string(content)
	return ProjectSettings.globalize_path(path)


func _on_export_review_pressed() -> void:
	var summary := _game_summary_data
	if summary.is_empty():
		wolf_status_label.text = "后端状态：还没有本局复盘可导出"
		return
	var lines: Array[String] = ["Agent Town Demo 复盘", "=================="]
	lines.append(str(summary.get("winner_label", "")) + "胜利 | 共 " + str(summary.get("total_days", 0)) + " 天")
	lines.append("")
	lines.append("【高光】")
	for highlight in _build_highlights(summary):
		lines.append(str(highlight))
	lines.append("")
	lines.append("【时间线】")
	var timeline: Variant = summary.get("timeline", [])
	if typeof(timeline) == TYPE_ARRAY:
		for event in timeline:
			if typeof(event) == TYPE_DICTIONARY:
				lines.append(_format_summary_event(event))
	var path := _export_text_file(
		"review_" + str(summary.get("game_id", "game")) + ".txt",
		"\n".join(lines),
	)
	if path.is_empty():
		wolf_status_label.text = "后端状态：导出失败"
	else:
		wolf_status_label.text = "已导出复盘：" + path


func _on_export_stats_pressed() -> void:
	var stats := _load_game_stats()
	var games: Array = stats.get("games", [])
	var lines: Array[String] = ["Agent Town Demo 战绩", "=================="]
	lines.append("总对局 " + str(games.size()) + " 局")
	var wins := 0
	var role_played := {}
	for game in games:
		if bool(game.get("won", false)):
			wins += 1
		var role := str(game.get("player_role", ""))
		var entry: Dictionary = role_played.get(role, {"played": 0, "won": 0})
		entry["played"] = int(entry["played"]) + 1
		if bool(game.get("won", false)):
			entry["won"] = int(entry["won"]) + 1
		role_played[role] = entry
	lines.append("胜场 " + str(wins) + "（胜率 " + str(int(round(float(wins) / maxf(1.0, float(games.size())) * 100))) + "%）")
	lines.append("")
	lines.append("【各身份】")
	for role in role_played:
		var entry: Dictionary = role_played[role]
		lines.append(_role_display_name(role) + "：" + str(entry["played"]) + " 局 " + str(entry["won"]) + " 胜")
	lines.append("")
	lines.append("【成就】")
	for achievement in _compute_achievements(stats):
		lines.append(str(achievement))
	var path := _export_text_file(
		"stats_" + str(Time.get_datetime_string_from_system()).replace(":", "-").replace(" ", "_") + ".txt",
		"\n".join(lines),
	)
	if path.is_empty():
		_append_stats_line("导出失败", false)
	else:
		_append_stats_line("已导出：" + path, false)


func _on_replay_button_pressed() -> void:
	_replay_events = []
	var timeline: Variant = _game_summary_data.get("timeline", [])
	if typeof(timeline) == TYPE_ARRAY:
		_replay_events = timeline
	_replay_index = 0
	_replay_playing = false
	replay_play_button.text = "播放"
	replay_overlay.visible = true
	replay_overlay.add_to_group("dialog_open")
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	_render_replay_step()
	call_deferred("_focus_control_if_available", replay_next_button)


func _on_replay_close_button_pressed() -> void:
	_replay_playing = false
	replay_overlay.visible = false
	replay_overlay.remove_from_group("dialog_open")
	replay_close_button.release_focus()
	_release_focus_to_world()


func _render_replay_step() -> void:
	if _replay_events.is_empty():
		replay_progress_label.text = "本局没有可回放的事件"
		replay_body_label.text = ""
		return
	var index := clampi(_replay_index, 0, _replay_events.size() - 1)
	replay_progress_label.text = "第 " + str(index + 1) + " / " + str(_replay_events.size()) + " 步"
	var event: Dictionary = _replay_events[index]
	var text := _format_summary_event(event)
	var day := int(event.get("day", 0))
	var phase := str(event.get("phase", ""))
	var is_night := phase == "NIGHT" or phase == "NIGHT_RESULT"
	var prefix := "🌙 " if is_night else ""
	replay_body_label.text = prefix + text


func _on_replay_prev_pressed() -> void:
	if _replay_events.is_empty():
		return
	_replay_index = maxi(0, _replay_index - 1)
	_render_replay_step()


func _on_replay_next_pressed() -> void:
	if _replay_events.is_empty():
		return
	_replay_index = mini(_replay_events.size() - 1, _replay_index + 1)
	_render_replay_step()


func _on_replay_play_pressed() -> void:
	_replay_playing = not _replay_playing
	replay_play_button.text = L10n.t("暂停") if _replay_playing else L10n.t("播放")
	if _replay_playing:
		_replay_autoplay_loop()


func _replay_autoplay_loop() -> void:
	while _replay_playing:
		await get_tree().create_timer(1.4).timeout
		if not _replay_playing:
			return
		if _replay_index >= _replay_events.size() - 1:
			_replay_playing = false
			replay_play_button.text = L10n.t("播放")
			return
		_replay_index += 1
		_render_replay_step()


func _on_tutorial_hints_toggled(enabled: bool) -> void:
	_tutorial_hints = enabled
	_save_session_preferences()


func _phase_tutorial_hint(phase: String) -> String:
	match phase:
		"NIGHT":
			return L10n.t("🌙 夜晚：按你的身份选择行动目标，然后点“结算夜晚”。")
		"HUNTER_SHOT":
			return L10n.t("🔫 猎人触发：选择开枪目标或选择不开枪。")
		"SHERIFF_SIGNUP":
			return L10n.t("🚨 警上报名：决定是否上警竞选警长。")
		"SHERIFF_SPEECH":
			return L10n.t("🚨 竞选发言：轮到你在面板填写警上发言。")
		"SHERIFF_WITHDRAWAL":
			return L10n.t("🚨 退水阶段：点“继续竞选”或“退水”。")
		"SHERIFF_VOTE":
			return L10n.t("🗳 警长投票：警下玩家为候选人投票。")
		"SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE":
			return L10n.t("⚖️ 平票 PK：候选人再次发言并重新投票。")
		"MEETING_ORDER":
			return L10n.t("🗣 警长选择发言方向（出局左/右或警左/右）。")
		"DAY_MEETING":
			return L10n.t("☀️ 白天会议：轮到你时在面板发言，NPC 轮到走近按 E。")
		"SHERIFF_NOMINATION":
			return L10n.t("🗣 警长确认暂时/最终归票。")
		"FREE_ACTIVITY":
			return L10n.t("🚶 自由活动：走近 NPC 按 E 私聊追问，结束点“结束自由活动”。")
		"VOTE":
			return L10n.t("🗳 放逐投票：选择目标并写下理由后一次提交。")
		"BADGE_TRANSFER":
			return L10n.t("🎖 警长出局：移交或撕毁警徽。")
		"GAME_OVER":
			return L10n.t("🏁 游戏结束：查看复盘与高光。")
		_:
			return ""


func _on_night_action_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_night_action = false
	_update_night_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：提交夜晚行动失败"
		return

	_complete_idempotent_command("night_action")
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "行动已记录。"))
	else:
		wolf_status_label.text = "后端状态：行动已记录"


func _on_night_resolve_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_resolving_night = false
	_update_night_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：结算夜晚失败"
		return

	_complete_idempotent_command("night_resolve")
	_play_sfx("eliminate")
	_play_night_pulse()
	_animate_eliminations_on_next_render = true
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var public_message = json.data.get("public_message", "夜晚已结算。")
		var private_result = _format_player_private_night_result(json.data.get("player_private_result", {}))
		wolf_game_info_label.text = str(public_message) + private_result
	else:
		wolf_game_info_label.text = "夜晚已结算。"

	_request_wolf_game_state()


func _on_hunter_shot_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_hunter_shot = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：猎人选择提交失败"
		_update_hunter_controls(_latest_wolf_game_data)
		return

	_complete_idempotent_command("hunter_shot")
	_animate_eliminations_on_next_render = true
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "猎人选择已结算。"))
	else:
		wolf_status_label.text = "后端状态：猎人选择已结算"
	_request_wolf_game_state()


func _on_player_speech_preview_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_previewing_player_speech = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_clear_speech_preview()
		wolf_status_label.text = "后端状态：" + _get_http_error_message(
			body,
			"读取发言预览失败"
		)
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		_clear_speech_preview()
		wolf_status_label.text = "后端状态：发言预览格式无效"
		return

	var accepted := bool(json.data.get("accepted", false))
	_pending_speech_preview_fingerprint = (
		str(json.data.get("preview_fingerprint", ""))
		if accepted
		else ""
	)
	speech_preview_summary.text = _format_player_speech_preview(json.data)
	speech_preview_confirm_button.disabled = (
		not accepted
		or _pending_speech_preview_fingerprint.is_empty()
	)
	_show_speech_preview_focus(
		speech_preview_confirm_button
		if not speech_preview_confirm_button.disabled
		else speech_preview_edit_button
	)
	_update_day_speech_controls_from_current_state()
	_update_sheriff_controls_from_current_state()
	_update_badge_flow_enabled_state()
	wolf_status_label.text = (
		"后端状态：请确认 Python 的发言理解"
		if accepted
		else "后端状态：当前发言未通过校验，请返回修改"
	)
	wolf_scroll_container.ensure_control_visible(speech_preview_panel)


func _on_player_speech_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_player_speech = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_restore_failed_gameplay_text(player_speech_input, _pending_player_speech_text)
		_restore_confirmed_speech_preview()
		wolf_status_label.text = "后端状态：提交发言失败"
		return

	_complete_idempotent_command("player_speech")
	_clear_speech_preview(false, false)
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：玩家发言已记录"
		wolf_game_info_label.text = _format_player_speech_result(json.data)
	else:
		wolf_status_label.text = "后端状态：玩家发言已记录"
		wolf_game_info_label.text = "玩家发言已记录。"

	_pending_player_speech_text = ""
	_request_wolf_game_state(true)


func _on_npc_speech_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_generating_npc_speeches = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：生成 NPC 发言失败"
		if dialog_box.call("is_open"):
			dialog_box.call("show_notice", _current_npc_name, _get_http_error_message(body, "当前不能生成这名 NPC 的发言。"))
		return

	_complete_idempotent_command("npc_speech")
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var speech_data = json.data.get("speech", {})
		if typeof(speech_data) == TYPE_DICTIONARY:
			var speaker_name := str(speech_data.get("name", _current_npc_name))
			var speech_text := str(speech_data.get("speech", "暂时没有发言。"))
			var evidence_titles = speech_data.get("evidence_titles", [])
			var retrieval_mode := str(speech_data.get("retrieval_mode", "keyword"))
			var llm_used := bool(speech_data.get("llm_used", false))
			var llm_provider := str(speech_data.get("llm_provider", "rule"))
			var llm_fallback_reason := str(speech_data.get("llm_fallback_reason", ""))
			wolf_status_label.text = "后端状态：" + speaker_name + " 已完成发言"
			wolf_game_info_label.text = speaker_name + "：" + speech_text
			if dialog_box.call("is_open"):
					dialog_box.call(
					"show_public_evidence_notice",
					speaker_name,
					speech_text,
					evidence_titles,
					retrieval_mode,
					llm_used,
					llm_provider,
					llm_fallback_reason,
					speech_data.get("llm_validation_failure", {})
				)
	else:
		wolf_status_label.text = "后端状态：NPC 发言已生成"

	_request_wolf_game_state(true)


func _request_current_npc_speeches_batch() -> void:
	if _is_fast_forwarding_speeches or _current_wolf_game_id.is_empty():
		return

	_is_fast_forwarding_speeches = true
	_update_day_speech_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在快进会议（批量生成 NPC 发言）..."
	dialog_box.call("show_notice", "会议快进", "正在批量生成 NPC 发言，轮到你会自动停下。")

	var body := {
		"game_id": _current_wolf_game_id
	}
	body = _prepare_idempotent_body("npc_speech", "npc_day_speech", body)
	var headers = ["Content-Type: application/json"]
	var error = npc_speeches_batch_request.request(
		WOLF_NPC_SPEECHES_BATCH_URL,
		headers,
		HTTPClient.METHOD_POST,
		JSON.stringify(body)
	)
	if error != OK:
		_is_fast_forwarding_speeches = false
		_update_day_speech_controls_from_current_state()
		wolf_status_label.text = "后端状态：快进会议失败"
		dialog_box.call("show_notice", "会议快进", "无法连接 Python 后端。")


func _on_npc_speeches_batch_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_fast_forwarding_speeches = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：快进会议失败"
		if dialog_box.call("is_open"):
			dialog_box.call("show_notice", "会议快进", _get_http_error_message(body, "当前不能快进会议。"))
		return

	_complete_idempotent_command("npc_speech")
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var speeches = json.data.get("speeches", [])
		wolf_game_info_label.text = _format_npc_speeches(speeches)
		wolf_status_label.text = "后端状态：会议已快进到你的回合"
		if dialog_box.call("is_open"):
			dialog_box.call("show_notice", "会议快进", "NPC 发言已完成，轮到你了。")
	else:
		wolf_status_label.text = "后端状态：会议已快进"

	_request_wolf_game_state(true)


func _on_end_free_activity_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_ending_free_activity = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：结束自由活动失败"
		return

	_complete_idempotent_command("end_free_activity")
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "已进入投票阶段。"))
	else:
		wolf_status_label.text = "后端状态：已进入投票阶段"

	_request_wolf_game_state()


func _on_private_chat_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_private_chat_requesting = false

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		if dialog_box.call("is_open"):
			dialog_box.call("show_private_prompt", _current_npc_name, _get_http_error_message(body, "私密追问失败，请稍后重试。"))
		return

	_complete_idempotent_command("private_chat")
	if not dialog_box.call("is_open"):
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		dialog_box.call("show_private_prompt", _current_npc_name, "后端返回的私密回答格式不正确。")
		return

	var npc_name := str(json.data.get("npc_name", _current_npc_name))
	var reply := str(json.data.get("reply", "暂时没有回答。"))
	var effective := bool(json.data.get("effective", false))
	var can_influence_again := bool(json.data.get("can_influence_again", false))
	var knowledge_titles = json.data.get("knowledge_titles", [])
	var retrieval_mode := str(json.data.get("retrieval_mode", "keyword"))
	var llm_used := bool(json.data.get("llm_used", false))
	var llm_provider := str(json.data.get("llm_provider", "rule"))
	var llm_fallback_reason := str(json.data.get("llm_fallback_reason", ""))
	var easter_egg_triggered := bool(json.data.get("easter_egg_triggered", false))
	var easter_egg_first_time := bool(json.data.get("easter_egg_first_time", false))
	var effect_note := "\n\n本次追问已影响该 NPC 的判断。"
	if easter_egg_triggered:
		effect_note = (
			"\n\n发现新的角色彩蛋。本次不会消耗今天的有效追问机会。"
			if easter_egg_first_time
			else "\n\n这个角色彩蛋已经触发过。本次仍不会消耗有效追问机会。"
		)
	elif not effective and can_influence_again:
		effect_note = "\n\n本次追问尚未影响该 NPC 的判断，明确对象后仍可进行今天的有效追问。"
	elif not effective:
		effect_note = "\n\n本次是追加追问，不会再次改变该 NPC 的决策。"
	if effective:
		_wolf_private_question_used[_current_npc_character_id] = true
	dialog_box.call(
		"show_private_response",
		npc_name,
		reply + effect_note,
		knowledge_titles,
		retrieval_mode,
		llm_used,
		llm_provider,
		llm_fallback_reason,
		json.data.get("llm_validation_failure", {})
	)
	_request_wolf_game_state()


func _on_sheriff_action_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_sheriff_action_requesting = false
	_update_sheriff_controls_from_current_state()
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：" + _get_http_error_message(body, "警长操作失败")
		return

	_complete_idempotent_command("sheriff_action")
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "警长操作已完成。"))
		if _pending_sheriff_action in ["SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"]:
			wolf_game_info_label.text = _format_sheriff_vote_result(json.data)
	else:
		wolf_status_label.text = "后端状态：警长操作已完成"
	_pending_sheriff_action = ""
	_request_wolf_game_state(true)


func _on_sheriff_speech_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_sheriff_speech_requesting = false
	_update_sheriff_controls_from_current_state()
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		if not _pending_sheriff_speech_text.is_empty():
			_restore_failed_gameplay_text(sheriff_speech_input, _pending_sheriff_speech_text)
		_restore_confirmed_speech_preview()
		wolf_status_label.text = "后端状态：" + _get_http_error_message(body, "警上发言失败")
		if dialog_box.call("is_open"):
			dialog_box.call("show_notice", _current_npc_name, _get_http_error_message(body, "警上发言失败，请稍后重试。"))
		return

	_complete_idempotent_command("sheriff_speech")
	if _pending_speech_preview_kind == "sheriff":
		_clear_speech_preview(false, false)
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var speech = json.data.get("speech", {})
		if typeof(speech) == TYPE_DICTIONARY:
			var speaker_name := str(speech.get("name", _current_npc_name))
			var content := str(speech.get("speech", "警上发言已完成。"))
			if dialog_box.call("is_open"):
					dialog_box.call(
					"show_public_evidence_notice",
					speaker_name,
					content,
					speech.get("evidence_titles", []),
					str(speech.get("retrieval_mode", "keyword")),
					bool(speech.get("llm_used", false)),
					str(speech.get("llm_provider", "rule")),
					str(speech.get("llm_fallback_reason", "")),
					speech.get("llm_validation_failure", {})
				)
		_pending_sheriff_speech_text = ""
		sheriff_speech_input.text = ""
		wolf_status_label.text = "后端状态：警上发言已记录"
	else:
		wolf_status_label.text = "后端状态：警上发言已记录"
	_request_wolf_game_state(true)


func _on_combined_vote_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_vote = false
	_update_vote_controls_from_current_state()
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_restore_failed_gameplay_text(vote_reason_input, _pending_vote_reason_text)
		wolf_status_label.text = "后端状态：" + _get_http_error_message(body, "同时投票失败")
		return

	_complete_idempotent_command("combined_vote")
	_play_sfx("eliminate")
	_animate_eliminations_on_next_render = true
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		vote_result_label.text = _format_combined_vote_result(json.data)
		wolf_game_info_label.text = str(json.data.get("public_message", "投票已结算。"))
		wolf_status_label.text = "后端状态：全部票型已同时公布并结算"
		_pending_vote_reason_text = ""
		vote_reason_input.text = ""
	else:
		vote_result_label.text = "票型：后端返回格式不正确"
		wolf_status_label.text = "后端状态：投票已结算"
	_request_wolf_game_state(true)


func _on_game_summary_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_loading_game_summary = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_summary_requested_game_id = ""
		review_game_button.disabled = false
		wolf_status_label.text = "后端状态：读取本局复盘失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		_summary_requested_game_id = ""
		review_game_button.disabled = false
		wolf_status_label.text = "后端状态：复盘数据格式错误"
		return

	_game_summary_data = json.data
	_save_game_stats(_game_summary_data)
	_render_game_summary(_game_summary_data)
	review_game_button.disabled = false
	_show_game_summary()


func _is_busy() -> bool:
	return (
		_is_requesting
		or _is_viewing_memory
		or _is_resetting_memory
		or _is_reloading_config
		or _is_starting_wolf_game
		or _is_loading_wolf_state
		or _is_submitting_night_action
		or _is_resolving_night
		or _is_submitting_hunter_shot
		or _is_previewing_player_speech
		or speech_preview_panel.visible
		or _is_submitting_player_speech
		or _is_generating_npc_speeches
		or _is_ending_free_activity
		or _is_private_chat_requesting
		or _is_sheriff_action_requesting
		or _is_sheriff_speech_requesting
		or _is_submitting_vote
		or _is_loading_game_summary
	)


func _request_wolf_game_state(preserve_info: bool = false) -> void:
	_is_loading_wolf_state = true
	_preserve_wolf_game_info_once = preserve_info
	refresh_state_button.disabled = true
	wolf_status_label.text = "后端状态：正在刷新状态..."

	var url = WOLF_GAME_STATE_URL_PREFIX + _current_wolf_game_id.uri_encode() + "/state"
	var error = game_state_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		_is_loading_wolf_state = false
		_preserve_wolf_game_info_once = false
		refresh_state_button.disabled = false
		wolf_status_label.text = "后端状态：刷新状态失败"


func _request_game_summary() -> void:
	if _is_loading_game_summary or _current_wolf_game_id.is_empty():
		return
	_is_loading_game_summary = true
	_summary_requested_game_id = _current_wolf_game_id
	review_game_button.disabled = true
	wolf_status_label.text = "后端状态：正在生成本局复盘..."
	var url = WOLF_GAME_STATE_URL_PREFIX + _current_wolf_game_id.uri_encode() + "/summary"
	var error = game_summary_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		_is_loading_game_summary = false
		_summary_requested_game_id = ""
		review_game_button.disabled = false
		wolf_status_label.text = "后端状态：读取本局复盘失败"


func _render_wolf_game(game_data: Dictionary) -> void:
	_latest_wolf_game_data = game_data.duplicate(true)
	var game_id = game_data.get("game_id", "")
	var day = game_data.get("day", 1)
	var phase = game_data.get("phase", "")
	var phase_changed := _current_wolf_phase != str(phase)
	var message = game_data.get("message", "游戏已开始。")
	if _tutorial_hints:
		var hint := _phase_tutorial_hint(str(phase))
		if not hint.is_empty():
			message = hint + "\n" + message
	var characters = game_data.get("characters", [])
	var public_logs = game_data.get("public_logs", [])
	var llm_enabled: bool = bool(game_data.get("llm_enabled", false))
	var llm_validation_enabled: bool = bool(
		game_data.get("llm_validation_enabled", false)
	)

	_current_wolf_game_id = str(game_id)
	_current_wolf_phase = str(phase)
	_current_wolf_day = int(day)
	if phase_changed:
		if _is_previewing_player_speech:
			player_speech_preview_request.cancel_request()
		_is_previewing_player_speech = false
		if not _pending_speech_submission_confirmed:
			_clear_speech_preview(false, false)
		_update_world_time(_current_wolf_phase)
	_update_player_private_state(game_data)
	_update_player_identity_display(game_data)
	_update_key_public_info(game_data)
	_update_player_action_history(game_data)
	_update_sheriff_state(game_data)
	_update_meeting_state(game_data)
	_sync_world_npcs(characters)
	_handle_elimination_animation(characters)

	wolf_status_label.text = L10n.t("后端状态：") + "connected"
	if _preserve_wolf_game_info_once:
		_preserve_wolf_game_info_once = false
	else:
		var private_note := _format_player_private_state_note(game_data.get("player_private_info", {}))
		var llm_label: String = L10n.t("LLM：规则模板")
		if llm_enabled:
			llm_label = (
				L10n.t("LLM：已启用 · 校验开启（最多5轮）")
				if llm_validation_enabled
				else L10n.t("LLM：已启用 · 原文直出（0次校验）")
			)
		wolf_game_info_label.text = (
			L10n.t("游戏 ")
			+ str(game_id)
			+ " | "
			+ L10n.t("第 ")
			+ str(day)
			+ L10n.t(" 天")
			+ " | "
			+ str(phase)
			+ " | "
			+ llm_label
			+ " | "
			+ L10n.t("策略：")
			+ _format_npc_policy_mode(str(game_data.get("npc_policy_mode", "")))
			+ "\n"
			+ str(message)
			+ private_note
		)
	public_log_label.text = _format_public_evidence_timeline(
		game_data.get("public_evidence_timeline", {}),
		game_data.get("public_evidence_analysis", {}),
		public_logs
	)
	_clear_character_grid()

	if typeof(characters) != TYPE_ARRAY:
		wolf_game_info_label.text = "角色数据格式不正确。"
		return

	for character in characters:
		if typeof(character) == TYPE_DICTIONARY:
			character_grid.add_child(_build_character_card(character))

	_update_night_controls(game_data)
	_update_hunter_controls(game_data)
	_update_sheriff_controls(game_data)
	_update_sheriff_overview()
	_update_day_speech_controls()
	_update_badge_flow_controls(game_data)
	_update_vote_controls(game_data)
	_update_contextual_panel_visibility()
	_update_wolf_menu_summary()
	_update_npc_roaming()
	if phase_changed:
		if _current_wolf_phase in [
			"SHERIFF_SIGNUP", "SHERIFF_SPEECH", "SHERIFF_WITHDRAWAL",
			"SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE",
			"MEETING_ORDER", "SHERIFF_NOMINATION", "BADGE_TRANSFER",
		]:
			call_deferred("_keep_sheriff_controls_visible")
		else:
			call_deferred("_reset_wolf_panel_scroll")
		if not game_setup_overlay.visible and not _intel_panel_open:
			_set_wolf_menu_expanded(true)
	review_game_button.disabled = _current_wolf_phase != "GAME_OVER" or _is_loading_game_summary
	if (
		_current_wolf_phase == "GAME_OVER"
		and _game_summary_data.is_empty()
		and _summary_requested_game_id != _current_wolf_game_id
	):
		_request_game_summary()


func _update_wolf_menu_summary() -> void:
	if _current_wolf_game_id.is_empty():
		wolf_menu_summary_label.text = L10n.t("等待开始")
		return

	match _current_wolf_phase:
		"NIGHT":
			wolf_menu_summary_label.text = L10n.t("夜晚 ") + str(_current_wolf_day)
		"HUNTER_SHOT":
			wolf_menu_summary_label.text = L10n.t("猎人开枪")
		"SHERIFF_SIGNUP":
			wolf_menu_summary_label.text = L10n.t("警上报名")
		"SHERIFF_SPEECH":
			wolf_menu_summary_label.text = L10n.t("警上发言")
		"SHERIFF_WITHDRAWAL":
			wolf_menu_summary_label.text = L10n.t("退水阶段")
		"SHERIFF_VOTE":
			wolf_menu_summary_label.text = L10n.t("警长投票")
		"SHERIFF_RUNOFF_SPEECH":
			wolf_menu_summary_label.text = L10n.t("警上 PK")
		"SHERIFF_RUNOFF_VOTE":
			wolf_menu_summary_label.text = L10n.t("PK 投票")
		"MEETING_ORDER":
			wolf_menu_summary_label.text = L10n.t("警长选发言侧")
		"SHERIFF_NOMINATION":
			wolf_menu_summary_label.text = L10n.t("警长归票")
		"BADGE_TRANSFER":
			wolf_menu_summary_label.text = L10n.t("移交警徽")
		"DAY_MEETING":
			var speaker_name := str(_wolf_character_names.get(_current_meeting_speaker_id, L10n.t("等待发言")))
			wolf_menu_summary_label.text = L10n.t("会议 · ") + speaker_name
		"FREE_ACTIVITY":
			wolf_menu_summary_label.text = L10n.t("自由活动")
		"VOTE":
			wolf_menu_summary_label.text = L10n.t("投票阶段")
		"GAME_OVER":
			wolf_menu_summary_label.text = L10n.t("游戏结束")
		_:
			wolf_menu_summary_label.text = _current_wolf_phase


func _update_meeting_state(game_data: Dictionary) -> void:
	_current_meeting_speaker_id = 0
	_current_meeting_order.clear()
	_current_meeting_direction = ""

	var meeting = game_data.get("meeting", {})
	if typeof(meeting) != TYPE_DICTIONARY:
		return

	_current_meeting_speaker_id = int(meeting.get("current_speaker_id", 0))
	_current_meeting_direction = str(meeting.get("direction", ""))
	var order = meeting.get("order", [])
	if typeof(order) == TYPE_ARRAY:
		for character_id in order:
			_current_meeting_order.append(int(character_id))


func _update_sheriff_state(game_data: Dictionary) -> void:
	_current_sheriff_data.clear()
	_current_sheriff_speaker_id = 0
	_current_sheriff_id = 0
	var sheriff = game_data.get("sheriff", {})
	if typeof(sheriff) != TYPE_DICTIONARY:
		return
	_current_sheriff_data = sheriff.duplicate(true)
	_current_sheriff_speaker_id = int(sheriff.get("current_speaker_id", 0))
	var sheriff_id = sheriff.get("sheriff_id", null)
	if sheriff_id != null:
		_current_sheriff_id = int(sheriff_id)


func _sync_world_npcs(characters: Variant) -> void:
	_wolf_character_names.clear()
	_wolf_character_alive.clear()
	_wolf_character_is_sheriff.clear()
	_wolf_private_question_used.clear()
	_wolf_campaign_status.clear()
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			var character_id := int(character.get("id", 0))
			_wolf_character_names[character_id] = str(character.get("name", "未知"))
			_wolf_character_alive[character_id] = bool(character.get("alive", true))
			_wolf_character_is_sheriff[character_id] = bool(
				character.get("is_sheriff", character_id == _current_sheriff_id)
			)
			_wolf_private_question_used[character_id] = bool(character.get("private_question_used_today", false))
			_wolf_campaign_status[character_id] = str(character.get("sheriff_campaign_status", ""))

	for npc in get_tree().get_nodes_in_group("npc"):
		var character_id := int(npc.call("get_wolf_character_id"))
		if character_id <= 0:
			continue
		var alive := bool(_wolf_character_alive.get(character_id, true))
		var is_current_speaker := (
			character_id == _current_meeting_speaker_id
			or character_id == _current_sheriff_speaker_id
		)
		var is_sheriff := bool(
			_wolf_character_is_sheriff.get(character_id, character_id == _current_sheriff_id)
		)
		npc.call(
			"set_wolf_game_state",
			alive,
			is_current_speaker,
			is_sheriff,
			str(_wolf_campaign_status.get(character_id, ""))
		)
	if _current_player_character_id > 0:
		var player_is_sheriff := bool(
			_wolf_character_is_sheriff.get(
				_current_player_character_id,
				_current_player_character_id == _current_sheriff_id
			)
		)
		player.call(
			"set_wolf_game_state",
			_current_player_alive,
			player_is_sheriff,
			str(_wolf_campaign_status.get(_current_player_character_id, ""))
		)


func _update_player_private_state(game_data: Dictionary) -> void:
	_current_player_character_id = 0
	_current_player_role = ""
	_current_player_alive = false

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY or not character.get("is_player", false):
				continue
			_current_player_character_id = int(character.get("id", 0))
			_current_player_alive = bool(character.get("alive", true))
			var visible_role = character.get("role_visible_to_player", null)
			if visible_role != null:
				_current_player_role = str(visible_role)

	var private_info = game_data.get("player_private_info", {})
	if typeof(private_info) == TYPE_DICTIONARY:
		var role = private_info.get("role", "")
		if not str(role).is_empty():
			_current_player_role = str(role)


func _update_player_identity_display(game_data: Dictionary) -> void:
	identity_panel.visible = not _current_wolf_game_id.is_empty() and not _current_player_role.is_empty()
	player_identity_block.visible = identity_panel.visible
	if not player_identity_block.visible:
		wolf_teammates_label.visible = false
		_set_key_info_expanded(false, false)
		return

	var role_text := _format_role_name(_current_player_role)
	var player_private_info = game_data.get("player_private_info", {})
	if (
		_current_player_role == "idiot"
		and typeof(player_private_info) == TYPE_DICTIONARY
		and bool(player_private_info.get("idiot_flipped", false))
	):
		role_text += L10n.t("（已翻牌，不能投票）")
	player_role_label.text = role_text
	player_role_label.add_theme_color_override("font_color", Color(0, 0, 0, 1))

	wolf_teammates_label.visible = _current_player_role == "werewolf"
	if not wolf_teammates_label.visible:
		return

	var teammate_parts: Array[String] = []
	var private_info = game_data.get("player_private_info", {})
	var teammates = private_info.get("wolf_teammates", []) if typeof(private_info) == TYPE_DICTIONARY else []
	if typeof(teammates) == TYPE_ARRAY:
		for teammate in teammates:
			if typeof(teammate) == TYPE_DICTIONARY:
				teammate_parts.append(str(teammate.get("id", "?")) + "号 " + str(teammate.get("name", "未知")))
	if teammate_parts.is_empty():
		var characters = game_data.get("characters", [])
		if typeof(characters) == TYPE_ARRAY:
			for character in characters:
				if (
					typeof(character) == TYPE_DICTIONARY
					and not bool(character.get("is_player", false))
					and str(character.get("role_visible_to_player", "")) == "werewolf"
				):
					teammate_parts.append(str(character.get("id", "?")) + "号 " + str(character.get("name", "未知")))
	wolf_teammates_label.text = "仅你可见 · 狼队友：" + ("、".join(teammate_parts) if not teammate_parts.is_empty() else "等待状态同步")


func _update_npc_roaming() -> void:
	# Wolf games lock everyone to the meeting ring; an open poker session moves
	# its five participants to the poker hall; otherwise NPCs roam their venues.
	# A saved slot's game id alone must NOT lock anyone: the game has to be
	# actually loaded (state rendered) for the ring to activate.
	var wolf_locked := (
		not _current_wolf_game_id.is_empty()
		and _current_wolf_phase != "GAME_OVER"
		and not _latest_wolf_game_data.is_empty()
	)
	var poker_names: Array = _poker_npc_names()
	venue_props.set_active(not wolf_locked)
	for npc in get_tree().get_nodes_in_group("npc"):
		var npc_name := str(npc.get("npc_name"))
		if wolf_locked:
			npc.call("lock_to_ring")
			npc.call("set_poker_indicator", false)
		elif not poker_names.is_empty() and poker_names.has(npc_name):
			npc.call("lock_to_position", _poker_spot_for(poker_names.find(npc_name)))
			npc.call("set_poker_indicator", true)
		else:
			npc.call("unlock_roaming")
			npc.call("set_poker_indicator", false)


func _poker_npc_names() -> Array:
	var names: Array = []
	if not _poker_state.is_empty():
		for player in _poker_state.get("players", []):
			if typeof(player) == TYPE_DICTIONARY and not bool(player.get("is_player", false)):
				names.append(str(player.get("name", "")))
	return names


func _poker_spot_for(index: int) -> Vector2:
	# A row in front of the poker hall entrance.
	return Vector2(1800, -500) + Vector2((index - 2) * 48.0, 0.0)


func _update_player_action_history(game_data: Dictionary) -> void:
	player_action_history_block.visible = not _current_wolf_game_id.is_empty()
	if not player_action_history_block.visible:
		player_action_history_text.text = "暂无行动记录。"
		return

	var private_info = game_data.get("player_private_info", {})
	var history = private_info.get("action_history", []) if typeof(private_info) == TYPE_DICTIONARY else []
	var lines: Array[String] = []
	if typeof(history) == TYPE_ARRAY:
		for item in history:
			var item_text := str(item).strip_edges()
			if not item_text.is_empty():
				lines.append(item_text)
	player_action_history_text.text = "\n".join(lines) if not lines.is_empty() else "暂无行动记录。"
	call_deferred("_scroll_player_action_history_to_end")


func _scroll_player_action_history_to_end() -> void:
	if player_action_history_block.visible:
		player_action_history_text.scroll_vertical = player_action_history_text.get_line_count()


func _reset_wolf_panel_scroll() -> void:
	wolf_scroll_container.scroll_vertical = 0


func _keep_sheriff_controls_visible() -> void:
	if not sheriff_action_label.visible:
		return
	wolf_scroll_container.ensure_control_visible(sheriff_action_label)
	if sheriff_withdrawal_row.visible:
		wolf_scroll_container.ensure_control_visible(sheriff_withdrawal_row)
	elif sheriff_choice_row.visible:
		wolf_scroll_container.ensure_control_visible(sheriff_choice_row)
	elif sheriff_speech_row.visible:
		wolf_scroll_container.ensure_control_visible(sheriff_speech_row)
		if badge_flow_panel.visible:
			wolf_scroll_container.ensure_control_visible(badge_flow_panel)


func _update_contextual_panel_visibility() -> void:
	var has_game := not _current_wolf_game_id.is_empty()
	wolf_panel.visible = has_game
	intel_toggle_button.disabled = not has_game
	setup_toggle_button.disabled = has_game and _current_wolf_phase != "GAME_OVER"
	if not has_game and _intel_panel_open:
		_set_intel_panel_open(false)
	var night_visible := has_game and _current_wolf_phase == "NIGHT"
	var hunter_visible := has_game and _current_wolf_phase == "HUNTER_SHOT" and _current_player_role == "hunter"
	var sheriff_visible := _current_wolf_phase in [
		"SHERIFF_SIGNUP", "SHERIFF_SPEECH", "SHERIFF_WITHDRAWAL",
		"SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE",
		"MEETING_ORDER", "SHERIFF_NOMINATION", "BADGE_TRANSFER",
	]
	var sheriff_speech_visible := _current_wolf_phase in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]
	var sheriff_withdrawal_visible := false
	if _current_wolf_phase == "SHERIFF_WITHDRAWAL":
		var candidates = _current_sheriff_data.get("candidates", [])
		var withdrawn = _current_sheriff_data.get("withdrawn", [])
		sheriff_withdrawal_visible = (
			_array_has_int(candidates, _current_player_character_id)
			and not _array_has_int(withdrawn, _current_player_character_id)
		)
	var day_visible := _current_wolf_phase in ["DAY_MEETING", "FREE_ACTIVITY"]
	var vote_visible := _current_wolf_phase == "VOTE"

	night_action_label.visible = night_visible
	night_action_row.visible = night_visible
	hunter_action_label.visible = hunter_visible
	hunter_action_row.visible = hunter_visible
	sheriff_action_label.visible = sheriff_visible
	sheriff_choice_row.visible = (
		sheriff_visible
		and not sheriff_speech_visible
		and _current_wolf_phase != "SHERIFF_WITHDRAWAL"
	)
	sheriff_withdrawal_row.visible = sheriff_withdrawal_visible
	sheriff_speech_row.visible = sheriff_visible and sheriff_speech_visible
	day_speech_label.visible = day_visible
	day_speech_row.visible = day_visible
	player_speech_input.visible = _current_wolf_phase == "DAY_MEETING"
	submit_speech_button.visible = _current_wolf_phase == "DAY_MEETING"
	end_free_activity_button.visible = _current_wolf_phase == "FREE_ACTIVITY"
	fast_forward_button.visible = (
		_current_wolf_phase == "DAY_MEETING"
		and _current_meeting_speaker_id != 0
		and _current_meeting_speaker_id != _current_player_character_id
	)
	temporary_nomination_row.visible = (
		_current_wolf_phase == "DAY_MEETING"
		and _current_meeting_speaker_id == _current_player_character_id
		and _current_sheriff_id == _current_player_character_id
		and _current_player_alive
	)
	vote_action_label.visible = vote_visible
	vote_reason_input.visible = vote_visible
	vote_action_row.visible = vote_visible
	vote_result_label.visible = vote_visible or vote_result_label.text != "票型：尚未公布"
	call_deferred("_repair_focus_in_top_scope")


func _update_night_controls(game_data: Dictionary) -> void:
	night_action_option.clear()
	night_target_option.clear()

	if _current_wolf_game_id.is_empty():
		_disable_night_controls()
		night_action_label.text = "夜晚行动：开始游戏后可用"
		return

	if _current_wolf_phase != "NIGHT":
		_disable_night_controls()
		night_action_label.text = "夜晚行动：当前阶段不是 NIGHT"
		return

	_populate_night_action_options(game_data)
	_refresh_night_target_options(game_data)
	var action_type := _get_selected_night_action_type()
	var action_name := _format_night_action_name(action_type)
	night_action_label.text = "夜晚行动：" + action_name
	var has_active_night_skill := _current_player_alive and _current_player_role in ["werewolf", "seer", "witch", "guard"]
	night_action_option.visible = has_active_night_skill
	night_target_option.visible = has_active_night_skill
	submit_night_action_button.visible = has_active_night_skill
	resolve_night_button.visible = true
	if not has_active_night_skill:
		night_action_label.text = "夜晚行动：今夜没有主动技能，可以直接结算"
	if _current_player_role == "witch" and has_active_night_skill:
		var private_info = game_data.get("player_private_info", {})
		if typeof(private_info) == TYPE_DICTIONARY:
			var attacked = private_info.get("witch_attacked_target", null)
			var attacked_text := "今晚没有明确刀口"
			if typeof(attacked) == TYPE_DICTIONARY:
				attacked_text = "今晚刀口：" + str(attacked.get("id", "?")) + "号 " + str(attacked.get("name", "未知"))
			var antidote_text := "解药可用" if bool(private_info.get("witch_antidote_available", false)) else "解药已用"
			var poison_text := "毒药可用" if bool(private_info.get("witch_poison_available", false)) else "毒药已用"
			night_action_label.text = "女巫行动：" + attacked_text + " | " + antidote_text + " | " + poison_text

	submit_night_action_button.disabled = (
		not _current_player_alive
		or _is_submitting_night_action
		or _is_resolving_night
		or (_night_action_requires_target(action_type) and night_target_option.get_item_count() == 0)
	)
	resolve_night_button.disabled = _is_submitting_night_action or _is_resolving_night


func _populate_night_action_options(game_data: Dictionary) -> void:
	night_action_option.clear()
	if _current_player_role == "witch":
		var private_info = game_data.get("player_private_info", {})
		if typeof(private_info) == TYPE_DICTIONARY:
			var attacked = private_info.get("witch_attacked_target", null)
			if bool(private_info.get("witch_antidote_available", false)) and typeof(attacked) == TYPE_DICTIONARY:
				_add_night_action_option("使用解药", "witch_save")
			if bool(private_info.get("witch_poison_available", false)):
				_add_night_action_option("使用毒药", "witch_poison")
		_add_night_action_option("不使用药", "none")
	else:
		var action_type := _get_player_night_action_type(_current_player_role)
		_add_night_action_option(_format_night_action_name(action_type), action_type)
	night_action_option.disabled = night_action_option.get_item_count() <= 1


func _add_night_action_option(label: String, action_type: String) -> void:
	var index := night_action_option.get_item_count()
	night_action_option.add_item(label)
	night_action_option.set_item_metadata(index, action_type)


func _get_selected_night_action_type() -> String:
	if night_action_option.get_item_count() == 0:
		return _get_player_night_action_type(_current_player_role)
	var metadata = night_action_option.get_item_metadata(night_action_option.selected)
	return str(metadata) if metadata != null else "none"


func _refresh_night_target_options(game_data: Dictionary) -> void:
	night_target_option.clear()
	var action_type := _get_selected_night_action_type()
	if not _night_action_requires_target(action_type):
		night_target_option.add_item("无需选择目标", 0)
		night_target_option.disabled = true
		return

	var private_info = game_data.get("player_private_info", {})
	var witch_save_target_id := 0
	if action_type == "witch_save" and typeof(private_info) == TYPE_DICTIONARY:
		var attacked = private_info.get("witch_attacked_target", null)
		if typeof(attacked) == TYPE_DICTIONARY:
			witch_save_target_id = int(attacked.get("id", 0))

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY or not character.get("alive", true):
				continue
			var character_id := int(character.get("id", 0))
			if action_type == "witch_save" and character_id != witch_save_target_id:
				continue
			if action_type in ["seer_check", "witch_poison"] and character_id == _current_player_character_id:
				continue
			if (
				action_type == "werewolf_kill"
				and str(character.get("role_visible_to_player", "")) == "werewolf"
				and character_id != _current_player_character_id
			):
				continue
			night_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")),
				character_id
			)
	night_target_option.disabled = night_target_option.get_item_count() == 0


func _update_night_controls_from_current_state() -> void:
	if _current_wolf_phase == "NIGHT":
		var action_type := _get_selected_night_action_type()
		submit_night_action_button.disabled = (
			not _current_player_alive
			or _is_submitting_night_action
			or _is_resolving_night
			or (_night_action_requires_target(action_type) and night_target_option.get_item_count() == 0)
		)
		resolve_night_button.disabled = _is_submitting_night_action or _is_resolving_night
	else:
		_disable_night_controls()


func _disable_night_controls() -> void:
	night_action_option.clear()
	night_action_option.disabled = true
	night_target_option.clear()
	night_target_option.disabled = true
	submit_night_action_button.disabled = true
	resolve_night_button.disabled = true


func _set_night_buttons_disabled(disabled: bool) -> void:
	night_action_option.disabled = disabled or night_action_option.get_item_count() <= 1
	night_target_option.disabled = disabled or not _night_action_requires_target(_get_selected_night_action_type())
	submit_night_action_button.disabled = disabled
	resolve_night_button.disabled = disabled


func _update_hunter_controls(game_data: Dictionary) -> void:
	hunter_target_option.clear()
	var private_info = game_data.get("player_private_info", {})
	var can_shoot := (
		_current_wolf_phase == "HUNTER_SHOT"
		and typeof(private_info) == TYPE_DICTIONARY
		and bool(private_info.get("hunter_can_shoot", false))
	)
	if not can_shoot:
		hunter_action_label.text = "猎人开枪：出局后可用"
		hunter_target_option.disabled = true
		hunter_shoot_button.disabled = true
		hunter_pass_button.disabled = true
		return

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY or not character.get("alive", true):
				continue
			var character_id := int(character.get("id", 0))
			if character_id == _current_player_character_id:
				continue
			hunter_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")),
				character_id
			)
	hunter_action_label.text = "猎人开枪：选择一名仍在场的角色，或选择不开枪"
	hunter_target_option.disabled = _is_submitting_hunter_shot or hunter_target_option.get_item_count() == 0
	hunter_shoot_button.disabled = _is_submitting_hunter_shot or hunter_target_option.get_item_count() == 0
	hunter_pass_button.disabled = _is_submitting_hunter_shot


func _update_sheriff_controls(game_data: Dictionary) -> void:
	sheriff_option.clear()
	sheriff_speech_input.editable = false
	sheriff_speech_button.disabled = true
	sheriff_action_button.disabled = true
	sheriff_option.disabled = true
	sheriff_continue_button.disabled = true
	sheriff_withdraw_button.disabled = true

	var busy := (
		_is_sheriff_action_requesting
		or _is_sheriff_speech_requesting
		or _is_previewing_player_speech
		or speech_preview_panel.visible
	)
	var characters = game_data.get("characters", [])
	match _current_wolf_phase:
		"SHERIFF_SIGNUP":
			sheriff_action_label.text = "警上报名：选择是否参加第一天警长竞选"
			_add_sheriff_option("上警竞选", true)
			_add_sheriff_option("不上警", false)
			sheriff_action_button.text = "确认报名"
			sheriff_option.disabled = busy or not _current_player_alive
			sheriff_action_button.disabled = busy or not _current_player_alive
		"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH":
			var current_name := str(_wolf_character_names.get(_current_sheriff_speaker_id, "当前候选人"))
			var stage_name := "警上 PK" if _current_wolf_phase == "SHERIFF_RUNOFF_SPEECH" else "警上竞选"
			if _current_sheriff_speaker_id == _current_player_character_id:
				sheriff_action_label.text = stage_name + "：轮到你发言"
				sheriff_speech_input.editable = not busy
				sheriff_speech_button.disabled = busy
			else:
				sheriff_action_label.text = stage_name + "：请走近 " + current_name + " 按 E"
		"SHERIFF_WITHDRAWAL":
			var candidates = _current_sheriff_data.get("candidates", [])
			var withdrawn = _current_sheriff_data.get("withdrawn", [])
			var player_is_candidate := _array_has_int(candidates, _current_player_character_id)
			var player_withdrawn := _array_has_int(withdrawn, _current_player_character_id)
			if player_is_candidate and not player_withdrawn:
				sheriff_action_label.text = "退水阶段：请选择继续竞选或退水"
				sheriff_continue_button.disabled = busy
				sheriff_withdraw_button.disabled = busy
			elif player_withdrawn:
				sheriff_action_label.text = "退水阶段：你已退水，正在等待其他候选人"
			else:
				sheriff_action_label.text = "退水阶段：正在自动结算候选人的选择"
		"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE":
			var can_vote := bool(_current_sheriff_data.get("player_can_vote", false))
			var ineligible_reason := str(_current_sheriff_data.get("player_vote_ineligible_reason", ""))
			sheriff_action_label.text = "警长投票：票型将在提交后同时公布"
			if can_vote:
				_add_character_options(sheriff_option, characters, _current_sheriff_data.get("vote_targets", []))
			else:
				_add_sheriff_option(
					ineligible_reason if not ineligible_reason.is_empty() else "当前不能参与警长投票",
					null
				)
			sheriff_action_button.text = "投警长并公布" if can_vote else "公布警长票型"
			sheriff_option.disabled = busy or not can_vote
			sheriff_action_button.disabled = busy or (can_vote and sheriff_option.get_item_count() == 0)
		"MEETING_ORDER":
			var anchor_type := str(_current_sheriff_data.get("order_anchor_type", "sheriff"))
			var anchor_id := int(_current_sheriff_data.get("order_anchor_id", 0))
			var anchor_name := str(_wolf_character_names.get(anchor_id, "警长"))
			var prefix := "出局" if anchor_type == "out" else "警"
			sheriff_action_label.text = "发言顺序：锚点为 " + str(anchor_id) + "号 " + anchor_name
			_add_sheriff_option(prefix + "左发言", "left")
			_add_sheriff_option(prefix + "右发言", "right")
			sheriff_action_button.text = "确认发言侧"
			sheriff_option.disabled = busy
			sheriff_action_button.disabled = busy
		"SHERIFF_NOMINATION":
			sheriff_action_label.text = "警长归票：你的正式投票将锁定为同一目标"
			_add_alive_character_options(sheriff_option, characters, [_current_sheriff_id])
			sheriff_action_button.text = "确认归票"
			sheriff_option.disabled = busy or sheriff_option.get_item_count() == 0
			sheriff_action_button.disabled = busy or sheriff_option.get_item_count() == 0
		"BADGE_TRANSFER":
			sheriff_action_label.text = "警徽移交：先完成猎人技能，再选择继任者或撕毁"
			_add_alive_character_options(sheriff_option, characters, [])
			_add_sheriff_option("撕毁警徽", 0)
			sheriff_action_button.text = "确认警徽去向"
			sheriff_option.disabled = busy
			sheriff_action_button.disabled = busy
		_:
			if _current_sheriff_id > 0:
				var sheriff_name := str(_wolf_character_names.get(_current_sheriff_id, "未知"))
				sheriff_action_label.text = "当前警长：" + str(_current_sheriff_id) + "号 " + sheriff_name
			else:
				sheriff_action_label.text = "警长操作：当前没有可执行操作"


func _update_sheriff_controls_from_current_state() -> void:
	if not _latest_wolf_game_data.is_empty():
		_update_sheriff_controls(_latest_wolf_game_data)
		_update_sheriff_overview()
	_update_badge_flow_enabled_state()


func _update_sheriff_overview() -> void:
	var sheriff_phases := [
		"SHERIFF_SIGNUP",
		"SHERIFF_SPEECH",
		"SHERIFF_WITHDRAWAL",
		"SHERIFF_VOTE",
		"SHERIFF_RUNOFF_SPEECH",
		"SHERIFF_RUNOFF_VOTE",
	]
	sheriff_overview_label.visible = _current_wolf_phase in sheriff_phases
	if not sheriff_overview_label.visible:
		return

	var lines: Array[String] = []
	lines.append("上警名单：" + _format_sheriff_character_ids(_current_sheriff_data.get("candidates", [])))
	lines.append("发言顺序：" + _format_sheriff_character_ids(_current_sheriff_data.get("speech_order", []), " → "))
	var current_speaker_id := int(_current_sheriff_data.get("current_speaker_id", 0))
	if current_speaker_id > 0:
		lines.append("当前发言：" + _format_sheriff_character_ids([current_speaker_id]))
	var withdrawn = _current_sheriff_data.get("withdrawn", [])
	if typeof(withdrawn) == TYPE_ARRAY and not withdrawn.is_empty():
		lines.append("已退水：" + _format_sheriff_character_ids(withdrawn))
	var runoff_candidates = _current_sheriff_data.get("runoff_candidates", [])
	if typeof(runoff_candidates) == TYPE_ARRAY and not runoff_candidates.is_empty():
		lines.append("PK名单：" + _format_sheriff_character_ids(runoff_candidates))
	sheriff_overview_label.text = "\n".join(lines)


func _format_sheriff_character_ids(values: Variant, separator: String = "、") -> String:
	if typeof(values) != TYPE_ARRAY or values.is_empty():
		return "暂无"
	var labels: Array[String] = []
	for value in values:
		var character_id := int(value)
		labels.append(
			str(character_id) + "号" + str(_wolf_character_names.get(character_id, "未知"))
		)
	return separator.join(labels)


func _disable_sheriff_controls() -> void:
	sheriff_option.clear()
	sheriff_option.disabled = true
	sheriff_action_button.disabled = true
	sheriff_speech_input.editable = false
	sheriff_speech_button.disabled = true


func _is_player_badge_flow_speech_turn() -> bool:
	if not _current_player_alive:
		return false
	if _current_wolf_phase in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]:
		return _current_sheriff_speaker_id == _current_player_character_id
	if _current_wolf_phase == "DAY_MEETING":
		return _current_meeting_speaker_id == _current_player_character_id
	return false


func _current_badge_flow_speech_declares_seer() -> bool:
	var speech := ""
	if _current_wolf_phase in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]:
		speech = sheriff_speech_input.text
	elif _current_wolf_phase == "DAY_MEETING":
		speech = player_speech_input.text
	var compact_speech := speech.replace(" ", "").replace("　", "")
	return (
		"我是预言家" in compact_speech
		or "我跳预言家" in compact_speech
		or "我起跳预言家" in compact_speech
		or "我报预言家" in compact_speech
		or "我认预言家" in compact_speech
		or "预言家在这里" in compact_speech
	)


func _can_edit_badge_flow_draft() -> bool:
	return _player_publicly_claimed_seer or _current_badge_flow_speech_declares_seer()


func _is_sheriff_badge_flow_required() -> bool:
	return (
		_current_wolf_phase in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]
		and _player_badge_flow_version == 0
		and (_player_publicly_claimed_seer or _current_badge_flow_speech_declares_seer())
	)


func _get_unpublished_badge_flow_status_text() -> String:
	if _player_publicly_claimed_seer:
		return "你已经公开跳预言家，可以随本次发言首次发布警徽流。"
	if _current_badge_flow_speech_declares_seer():
		return "本次发言会同时完成预言家起跳与首次警徽流发布。"
	return "首次发布：请先在本次发言中明确写出“我是预言家”“我跳预言家”或“我起跳预言家”。"


func _find_latest_player_badge_flow(game_data: Dictionary) -> Dictionary:
	var latest: Dictionary = {}
	var latest_version := 0
	var sheriff = game_data.get("sheriff", {})
	var flows = sheriff.get("badge_flows", []) if typeof(sheriff) == TYPE_DICTIONARY else []
	if typeof(flows) != TYPE_ARRAY:
		return latest
	for flow in flows:
		if typeof(flow) != TYPE_DICTIONARY:
			continue
		if int(flow.get("character_id", 0)) != _current_player_character_id:
			continue
		var version := int(flow.get("version", 0))
		if version > latest_version:
			latest_version = version
			latest = flow.duplicate(true)
	return latest


func _player_has_public_seer_claim(game_data: Dictionary) -> bool:
	var characters = game_data.get("characters", [])
	if typeof(characters) != TYPE_ARRAY:
		return false
	for character in characters:
		if typeof(character) != TYPE_DICTIONARY:
			continue
		if int(character.get("id", 0)) != _current_player_character_id:
			continue
		return str(character.get("claimed_role", "")) == "seer"
	return false


func _update_badge_flow_controls(game_data: Dictionary) -> void:
	var incoming_game_id := str(game_data.get("game_id", ""))
	if incoming_game_id != _badge_flow_game_id:
		_badge_flow_game_id = incoming_game_id
		_player_badge_flow_version = 0
		badge_flow_include_toggle.button_pressed = false
		_badge_flow_collapsed = true

	_player_publicly_claimed_seer = _player_has_public_seer_claim(game_data)
	badge_flow_panel.visible = _is_player_badge_flow_speech_turn()
	if not badge_flow_panel.visible:
		_update_badge_flow_enabled_state()
		return

	var latest_flow := _find_latest_player_badge_flow(game_data)
	var latest_version := int(latest_flow.get("version", 0))
	var keep_draft := (
		badge_flow_include_toggle.button_pressed
		and latest_version == _player_badge_flow_version
	)
	var draft_primary := int(_get_selected_option_metadata(badge_flow_primary_option, 0)) if keep_draft else 0
	var draft_secondary := int(_get_selected_option_metadata(badge_flow_secondary_option, 0)) if keep_draft else 0
	var draft_anchor := int(_get_selected_option_metadata(badge_flow_wolf_option, 0)) if keep_draft else 0
	var draft_reason := str(_get_selected_option_metadata(badge_flow_reason_option, "")) if keep_draft else ""
	var draft_reason_target := int(_get_selected_option_metadata(badge_flow_reason_target_option, 0)) if keep_draft else 0

	if latest_version > _player_badge_flow_version:
		badge_flow_include_toggle.button_pressed = false
	_player_badge_flow_version = latest_version
	badge_flow_include_toggle.text = (
		"随本次发言发布" if latest_version == 0 else "随本次发言更新"
	)
	if _is_sheriff_badge_flow_required():
		badge_flow_include_toggle.text = "警上跳预言家：必须发布"
		badge_flow_include_toggle.set_pressed_no_signal(true)
		_badge_flow_collapsed = false
	badge_flow_current_label.text = (
		str(latest_flow.get("display_text", "已发布警徽流 v" + str(latest_version)))
		if latest_version > 0
		else _get_unpublished_badge_flow_status_text()
	)

	_populate_badge_flow_target_options(
		game_data,
		draft_primary if keep_draft else _optional_character_id(latest_flow.get("primary_target_id", null)),
		draft_secondary if keep_draft else (
			_optional_character_id(latest_flow.get("secondary_target_id", null))
			if latest_version > 0
			else -1
		),
	)
	_populate_badge_flow_reason_options(latest_version, draft_reason)
	_populate_badge_flow_reason_target_options(game_data, draft_reason_target)
	_refresh_badge_flow_recipient_options(
		game_data,
		draft_anchor if keep_draft else (
			_optional_character_id(latest_flow.get("claimed_good_anchor_id", null))
			if latest_version > 0
			else -1
		),
	)
	_update_badge_flow_collapsed_state()
	_update_badge_flow_enabled_state()


func _populate_badge_flow_target_options(
	game_data: Dictionary,
	preferred_primary: int,
	preferred_secondary: int,
) -> void:
	badge_flow_primary_option.clear()
	badge_flow_secondary_option.clear()
	badge_flow_secondary_option.add_item("不设置第二验人")
	badge_flow_secondary_option.set_item_metadata(0, 0)
	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if (
				typeof(character) != TYPE_DICTIONARY
				or not bool(character.get("alive", true))
				or int(character.get("id", 0)) == _current_player_character_id
			):
				continue
			var character_id := int(character.get("id", 0))
			var label := str(character_id) + "号 " + str(character.get("name", "未知"))
			badge_flow_primary_option.add_item(label)
			badge_flow_primary_option.set_item_metadata(
				badge_flow_primary_option.get_item_count() - 1,
				character_id
			)
			badge_flow_secondary_option.add_item(label)
			badge_flow_secondary_option.set_item_metadata(
				badge_flow_secondary_option.get_item_count() - 1,
				character_id
			)

	if not _select_option_by_metadata(badge_flow_primary_option, preferred_primary):
		if badge_flow_primary_option.get_item_count() > 0:
			badge_flow_primary_option.select(0)
	if not _select_option_by_metadata(badge_flow_secondary_option, preferred_secondary):
		badge_flow_secondary_option.select(0)
	var primary := int(_get_selected_option_metadata(badge_flow_primary_option, 0))
	var secondary := int(_get_selected_option_metadata(badge_flow_secondary_option, 0))
	if secondary == primary:
		badge_flow_secondary_option.select(0)
	elif secondary == 0 and preferred_secondary < 0 and badge_flow_secondary_option.get_item_count() > 2:
		var default_secondary_index := 1
		if int(badge_flow_secondary_option.get_item_metadata(default_secondary_index)) == primary:
			default_secondary_index = 2
		badge_flow_secondary_option.select(default_secondary_index)


func _populate_badge_flow_reason_options(version: int, preferred_reason: String) -> void:
	badge_flow_reason_option.clear()
	if version == 0:
		badge_flow_reason_option.add_item("首次公开警徽流")
		badge_flow_reason_option.set_item_metadata(0, "initial")
		return
	for reason_option in BADGE_FLOW_REVISION_REASON_OPTIONS:
		var index := badge_flow_reason_option.get_item_count()
		badge_flow_reason_option.add_item(str(reason_option[0]))
		badge_flow_reason_option.set_item_metadata(index, str(reason_option[1]))
	var reason_to_select := preferred_reason if not preferred_reason.is_empty() else "other_public_reason"
	_select_option_by_metadata(badge_flow_reason_option, reason_to_select)


func _populate_badge_flow_reason_target_options(game_data: Dictionary, preferred_target: int) -> void:
	badge_flow_reason_target_option.clear()
	badge_flow_reason_target_option.add_item("无具体对象")
	badge_flow_reason_target_option.set_item_metadata(0, 0)
	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			var character_id := int(character.get("id", 0))
			if character_id == _current_player_character_id:
				continue
			var alive_suffix := "" if bool(character.get("alive", true)) else "（已出局）"
			var index := badge_flow_reason_target_option.get_item_count()
			badge_flow_reason_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")) + alive_suffix
			)
			badge_flow_reason_target_option.set_item_metadata(index, character_id)
	if not _select_option_by_metadata(badge_flow_reason_target_option, preferred_target):
		badge_flow_reason_target_option.select(0)


func _refresh_badge_flow_recipient_options(
	game_data: Dictionary,
	preferred_anchor: int = -1,
) -> void:
	if preferred_anchor < 0 and badge_flow_wolf_option.get_item_count() > 0:
		preferred_anchor = int(_get_selected_option_metadata(badge_flow_wolf_option, 0))
	var primary_target_id := int(_get_selected_option_metadata(badge_flow_primary_option, 0))
	var secondary_target_id := int(_get_selected_option_metadata(badge_flow_secondary_option, 0))
	if secondary_target_id == primary_target_id:
		badge_flow_secondary_option.select(0)
		secondary_target_id = 0

	badge_flow_good_option.clear()
	badge_flow_wolf_option.clear()
	var primary_label := (
		str(primary_target_id) + "号 " + str(_wolf_character_names.get(primary_target_id, "未知"))
		if primary_target_id > 0
		else "尚未选择今晚验人"
	)
	badge_flow_good_option.add_item("自动给 " + primary_label)
	badge_flow_good_option.set_item_metadata(0, primary_target_id)
	badge_flow_wolf_option.add_item("自动：最近存活公开金水；没有则撕徽")
	badge_flow_wolf_option.set_item_metadata(0, 0)

	var alive_ids: Array[int] = []
	for character in game_data.get("characters", []):
		if typeof(character) == TYPE_DICTIONARY and bool(character.get("alive", true)):
			alive_ids.append(int(character.get("id", 0)))
	var latest_result_by_target := {}
	var claim_order: Array[int] = []
	for item in game_data.get("public_intel", []):
		if (
			typeof(item) != TYPE_DICTIONARY
			or str(item.get("kind", "")) != "seer_check"
			or int(item.get("actor_id", 0)) != _current_player_character_id
		):
			continue
		var target_id := int(item.get("target_id", 0))
		claim_order.erase(target_id)
		claim_order.append(target_id)
		latest_result_by_target[target_id] = str(item.get("result", ""))
	claim_order.reverse()
	for target_id in claim_order:
		if (
			target_id <= 0
			or target_id == primary_target_id
			or target_id not in alive_ids
			or str(latest_result_by_target.get(target_id, "")) != "good"
		):
			continue
		var label := str(target_id) + "号 " + str(_wolf_character_names.get(target_id, "未知"))
		badge_flow_wolf_option.add_item("查杀时给公开金水 " + label)
		badge_flow_wolf_option.set_item_metadata(
			badge_flow_wolf_option.get_item_count() - 1,
			target_id
		)

	badge_flow_good_option.select(0)
	if preferred_anchor < 0 or not _select_option_by_metadata(badge_flow_wolf_option, preferred_anchor):
		badge_flow_wolf_option.select(0)


func _select_option_by_metadata(option: OptionButton, target: Variant) -> bool:
	for index in range(option.get_item_count()):
		if option.get_item_metadata(index) == target:
			option.select(index)
			return true
	return false


func _optional_character_id(value: Variant) -> int:
	return int(value) if value != null else 0


func _on_badge_flow_include_toggled(enabled: bool) -> void:
	if not enabled and _is_sheriff_badge_flow_required():
		badge_flow_include_toggle.set_pressed_no_signal(true)
		wolf_status_label.text = "后端状态：警上首次跳预言家必须发布警徽流"
		return
	if enabled:
		_badge_flow_collapsed = false
	_update_badge_flow_collapsed_state()
	_update_badge_flow_enabled_state()


func _on_badge_flow_speech_draft_changed(_speech: String) -> void:
	if not badge_flow_panel.visible:
		return
	if _is_sheriff_badge_flow_required():
		badge_flow_include_toggle.set_pressed_no_signal(true)
		badge_flow_include_toggle.text = "警上跳预言家：必须发布"
		_badge_flow_collapsed = false
	elif _player_badge_flow_version == 0:
		badge_flow_include_toggle.text = "随本次发言发布"
		if not _can_edit_badge_flow_draft():
			badge_flow_include_toggle.set_pressed_no_signal(false)
			_badge_flow_collapsed = true
	if _player_badge_flow_version > 0:
		_update_badge_flow_collapsed_state()
		_update_badge_flow_enabled_state()
		return
	badge_flow_current_label.text = _get_unpublished_badge_flow_status_text()
	_update_badge_flow_collapsed_state()
	_update_badge_flow_enabled_state()


func _on_badge_flow_target_selected(_index: int) -> void:
	_refresh_badge_flow_recipient_options(_latest_wolf_game_data)
	_update_badge_flow_enabled_state()


func _on_badge_flow_collapse_pressed() -> void:
	_badge_flow_collapsed = not _badge_flow_collapsed
	_update_badge_flow_collapsed_state()
	_update_badge_flow_enabled_state()


func _update_badge_flow_collapsed_state() -> void:
	badge_flow_collapse_button.text = "展开" if _badge_flow_collapsed else "收起"
	badge_flow_form_grid.visible = not _badge_flow_collapsed
	badge_flow_hint_label.visible = not _badge_flow_collapsed


func _update_badge_flow_enabled_state() -> void:
	var busy := (
		_is_sheriff_speech_requesting
		or _is_submitting_player_speech
		or _is_previewing_player_speech
		or speech_preview_panel.visible
	)
	var can_edit := (
		badge_flow_panel.visible
		and _is_player_badge_flow_speech_turn()
		and _can_edit_badge_flow_draft()
		and not busy
	)
	badge_flow_include_toggle.disabled = not can_edit
	var details_enabled := (
		can_edit
		and badge_flow_include_toggle.button_pressed
		and not _badge_flow_collapsed
	)
	badge_flow_primary_option.disabled = not details_enabled
	badge_flow_secondary_option.disabled = not details_enabled
	badge_flow_good_option.disabled = true
	badge_flow_wolf_option.disabled = not details_enabled
	badge_flow_reason_option.disabled = not details_enabled
	badge_flow_reason_target_option.disabled = not details_enabled


func _add_sheriff_option(label: String, metadata: Variant) -> void:
	var index := sheriff_option.get_item_count()
	sheriff_option.add_item(label)
	sheriff_option.set_item_metadata(index, metadata)


func _add_character_options(option: OptionButton, characters: Variant, allowed_ids: Variant) -> void:
	if typeof(characters) != TYPE_ARRAY or typeof(allowed_ids) != TYPE_ARRAY:
		return
	for character in characters:
		if typeof(character) != TYPE_DICTIONARY:
			continue
		var character_id := int(character.get("id", 0))
		if not _array_has_int(allowed_ids, character_id):
			continue
		option.add_item(str(character_id) + "号 " + str(character.get("name", "未知")))
		option.set_item_metadata(option.get_item_count() - 1, character_id)


func _add_alive_character_options(option: OptionButton, characters: Variant, excluded_ids: Array) -> void:
	if typeof(characters) != TYPE_ARRAY:
		return
	for character in characters:
		if typeof(character) != TYPE_DICTIONARY or not bool(character.get("alive", true)):
			continue
		var character_id := int(character.get("id", 0))
		if _array_has_int(excluded_ids, character_id):
			continue
		option.add_item(str(character_id) + "号 " + str(character.get("name", "未知")))
		option.set_item_metadata(option.get_item_count() - 1, character_id)


func _array_has_int(values: Variant, target: int) -> bool:
	if typeof(values) != TYPE_ARRAY:
		return false
	for value in values:
		if int(value) == target:
			return true
	return false


func _update_day_speech_controls() -> void:
	temporary_nomination_option.clear()
	if _current_wolf_game_id.is_empty():
		_disable_day_speech_controls()
		day_speech_label.text = "小镇会议：开始游戏后可用"
		return

	if _current_wolf_phase == "GAME_OVER":
		_disable_day_speech_controls()
		day_speech_label.text = "小镇会议：游戏已结束"
		return

	if _current_wolf_phase == "FREE_ACTIVITY":
		player_speech_input.editable = false
		submit_speech_button.disabled = true
		end_free_activity_button.disabled = _is_ending_free_activity
		day_speech_label.text = "会后自由活动：走近存活 NPC 按 E 私密追问；原文不会自动公开"
		return

	if _current_wolf_phase != "DAY_MEETING":
		_disable_day_speech_controls()
		day_speech_label.text = "小镇会议：当前阶段不可发言"
		return

	var current_name := str(_wolf_character_names.get(_current_meeting_speaker_id, "未知角色"))
	var direction_label := "顺时针" if _current_meeting_direction == "clockwise" else "逆时针"
	if _current_meeting_speaker_id == _current_player_character_id and _current_player_alive:
		day_speech_label.text = "小镇会议（" + direction_label + "）：轮到你公开发言"
	else:
		day_speech_label.text = "小镇会议（" + direction_label + "）：请走近 " + current_name + " 按 E"

	var is_player_turn := _current_meeting_speaker_id == _current_player_character_id and _current_player_alive
	var can_temporarily_nominate := is_player_turn and _current_sheriff_id == _current_player_character_id
	if can_temporarily_nominate:
		temporary_nomination_option.add_item("暂不提出归票")
		temporary_nomination_option.set_item_metadata(0, 0)
		_add_alive_character_options(
			temporary_nomination_option,
			_latest_wolf_game_data.get("characters", []),
			[_current_player_character_id]
		)
	temporary_nomination_option.disabled = not can_temporarily_nominate or _is_day_speech_requesting()
	player_speech_input.editable = is_player_turn and not _is_day_speech_requesting()
	submit_speech_button.disabled = not is_player_turn or _is_day_speech_requesting()
	end_free_activity_button.disabled = true


func _update_day_speech_controls_from_current_state() -> void:
	if _current_wolf_phase == "FREE_ACTIVITY":
		player_speech_input.editable = false
		submit_speech_button.disabled = true
		end_free_activity_button.disabled = _is_ending_free_activity
		fast_forward_button.disabled = true
		_update_badge_flow_enabled_state()
		return
	if _current_wolf_phase != "DAY_MEETING":
		_disable_day_speech_controls()
		return

	var is_player_turn := _current_meeting_speaker_id == _current_player_character_id and _current_player_alive
	player_speech_input.editable = is_player_turn and not _is_day_speech_requesting()
	submit_speech_button.disabled = not is_player_turn or _is_day_speech_requesting()
	temporary_nomination_option.disabled = (
		not is_player_turn
		or _current_sheriff_id != _current_player_character_id
		or _is_day_speech_requesting()
	)
	fast_forward_button.disabled = (
		is_player_turn
		or _current_meeting_speaker_id == 0
		or _is_day_speech_requesting()
	)
	end_free_activity_button.disabled = true
	_update_badge_flow_enabled_state()


func _disable_day_speech_controls() -> void:
	player_speech_input.editable = false
	submit_speech_button.disabled = true
	end_free_activity_button.disabled = true
	fast_forward_button.disabled = true
	temporary_nomination_option.disabled = true
	_update_badge_flow_enabled_state()


func _set_day_speech_buttons_disabled(disabled: bool) -> void:
	var is_player_turn := _current_meeting_speaker_id == _current_player_character_id and _current_player_alive
	player_speech_input.editable = not disabled and is_player_turn
	submit_speech_button.disabled = disabled or not is_player_turn
	end_free_activity_button.disabled = true
	fast_forward_button.disabled = true
	temporary_nomination_option.disabled = disabled or not is_player_turn or _current_sheriff_id != _current_player_character_id
	_update_badge_flow_enabled_state()


func _is_day_speech_phase() -> bool:
	return _current_wolf_phase == "DAY_MEETING"


func _is_day_speech_requesting() -> bool:
	return (
		_is_previewing_player_speech
		or speech_preview_panel.visible
		or _is_submitting_player_speech
		or _is_generating_npc_speeches
		or _is_fast_forwarding_speeches
		or _is_ending_free_activity
	)


func _update_vote_controls(game_data: Dictionary) -> void:
	vote_target_option.clear()

	if _current_wolf_game_id.is_empty():
		_disable_vote_controls()
		vote_action_label.text = "白天投票：开始游戏后可用"
		return

	if _current_wolf_phase == "GAME_OVER":
		_disable_vote_controls()
		vote_action_label.text = "白天投票：游戏已结束"
		return

	if not _is_vote_phase():
		_disable_vote_controls()
		vote_action_label.text = "白天投票：当前阶段不是白天"
		return

	var locked_nomination_id := 0
	var meeting = game_data.get("meeting", {})
	if _current_sheriff_id == _current_player_character_id and typeof(meeting) == TYPE_DICTIONARY:
		var nomination_target = meeting.get("nomination_target_id", null)
		if nomination_target != null:
			locked_nomination_id = int(nomination_target)

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			if not character.get("alive", true):
				continue
			var character_id := int(character.get("id", 0))
			if character_id == _current_player_character_id:
				continue
			if locked_nomination_id > 0 and character_id != locked_nomination_id:
				continue
			vote_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")),
				character_id
			)

	if _current_player_alive:
		vote_action_label.text = "白天投票：填写理由后一次性公布全部票型"
		if locked_nomination_id > 0:
			vote_action_label.text = "白天投票：警长票已锁定为公开归票目标"
	else:
		vote_action_label.text = "白天投票：玩家已出局，可直接公布并结算 NPC 票型"

	vote_target_option.disabled = (
		not _current_player_alive
		or vote_target_option.get_item_count() == 0
		or _is_vote_requesting()
	)
	vote_reason_input.editable = _current_player_alive and not _is_vote_requesting()
	submit_vote_button.disabled = _is_vote_requesting() or (_current_player_alive and vote_target_option.get_item_count() == 0)


func _update_vote_controls_from_current_state() -> void:
	if _is_vote_phase():
		_update_vote_controls(_latest_wolf_game_data)
	else:
		_disable_vote_controls()


func _disable_vote_controls() -> void:
	vote_target_option.clear()
	vote_target_option.disabled = true
	vote_reason_input.editable = false
	submit_vote_button.disabled = true


func _set_vote_buttons_disabled(disabled: bool) -> void:
	vote_target_option.disabled = disabled or not _current_player_alive or vote_target_option.get_item_count() == 0
	vote_reason_input.editable = not disabled and _current_player_alive
	submit_vote_button.disabled = disabled or (_current_player_alive and vote_target_option.get_item_count() == 0)


func _is_vote_phase() -> bool:
	return _current_wolf_phase == "VOTE"


func _is_vote_requesting() -> bool:
	return _is_submitting_vote


func _get_player_night_action_type(role: String) -> String:
	match role:
		"werewolf":
			return "werewolf_kill"
		"seer":
			return "seer_check"
		"guard":
			return "guard_protect"
		"witch":
			return "none"
		_:
			return "none"


func _night_action_requires_target(action_type: String) -> bool:
	return action_type in ["werewolf_kill", "seer_check", "guard_protect", "witch_save", "witch_poison"]


func _format_night_action_name(action_type: String) -> String:
	match action_type:
		"werewolf_kill":
			return "狼人袭击"
		"seer_check":
			return "预言家查验"
		"guard_protect":
			return "守卫保护"
		"witch_save":
			return "女巫使用解药"
		"witch_poison":
			return "女巫使用毒药"
		_:
			return "无行动"


func _format_player_private_night_result(player_private_result: Variant) -> String:
	if typeof(player_private_result) != TYPE_DICTIONARY:
		return ""

	var seer_check = player_private_result.get("seer_check", null)
	if typeof(seer_check) == TYPE_DICTIONARY:
		var target_id = seer_check.get("target_id", "?")
		var result = "狼人" if seer_check.get("result", "") == "werewolf" else "好人"
		return "\n查验结果：" + str(target_id) + "号是" + result + "。"
	var witch_action = player_private_result.get("witch_action", null)
	if typeof(witch_action) == TYPE_DICTIONARY:
		return "\n女巫行动已结算：" + _format_night_action_name(str(witch_action.get("action_type", "none"))) + "。"
	return ""


func _format_player_private_state_note(private_info: Variant) -> String:
	if typeof(private_info) != TYPE_DICTIONARY:
		return ""

	var notes: Array[String] = []
	var last_check_result = private_info.get("last_check_result", null)
	if typeof(last_check_result) == TYPE_DICTIONARY:
		var target_id = last_check_result.get("target_id", "?")
		var result = "狼人" if last_check_result.get("result", "") == "werewolf" else "好人"
		notes.append("最近查验：" + str(target_id) + "号是" + result + "。")

	var wolf_teammates = private_info.get("wolf_teammates", [])
	if typeof(wolf_teammates) == TYPE_ARRAY and not wolf_teammates.is_empty():
		var teammate_parts: Array[String] = []
		for teammate in wolf_teammates:
			if typeof(teammate) != TYPE_DICTIONARY:
				continue
			var state := "存活" if bool(teammate.get("alive", true)) else "已出局"
			teammate_parts.append(str(teammate.get("id", "?")) + "号 " + str(teammate.get("name", "未知")) + "（" + state + "）")
		if not teammate_parts.is_empty():
			notes.append("狼队友：" + _join_inline(teammate_parts))

	if _current_player_role == "witch":
		var antidote := "可用" if bool(private_info.get("witch_antidote_available", false)) else "已使用"
		var poison := "可用" if bool(private_info.get("witch_poison_available", false)) else "已使用"
		notes.append("女巫药品：解药" + antidote + "，毒药" + poison + "。")
	return "" if notes.is_empty() else "\n" + _join_lines(notes)


func _format_player_speech_result(speech_data: Dictionary) -> String:
	var lines: Array[String] = ["玩家发言已记录。"]
	var public_log = str(speech_data.get("public_log", ""))
	if not public_log.is_empty():
		lines.append(public_log)

	var parsed = speech_data.get("parsed", {})
	if typeof(parsed) == TYPE_DICTIONARY:
		var mentioned = parsed.get("mentioned_characters", [])
		if typeof(mentioned) == TYPE_ARRAY and not mentioned.is_empty():
			var mentioned_parts: Array[String] = []
			for character_id in mentioned:
				mentioned_parts.append(str(character_id) + "号")
			lines.append("提到角色：" + _join_inline(mentioned_parts))
		lines.append("语气：" + _format_speech_tone(str(parsed.get("tone", "neutral"))))

	return _join_lines(lines)


func _format_player_speech_preview(preview_data: Dictionary) -> String:
	var accepted := bool(preview_data.get("accepted", false))
	var lines: Array[String] = [
		"解析结果：" + ("可以提交" if accepted else "不能提交")
	]
	var errors = preview_data.get("errors", [])
	if typeof(errors) == TYPE_ARRAY:
		for error in errors:
			lines.append("拒绝原因：" + str(error))

	var canonical_speech := str(preview_data.get("canonical_speech", ""))
	if not canonical_speech.is_empty():
		lines.append("将公开的规范文本：" + canonical_speech)

	var public_facts = preview_data.get("public_facts_to_write", [])
	if typeof(public_facts) == TYPE_ARRAY and not public_facts.is_empty():
		lines.append("会写入的公开事实：")
		for item in public_facts:
			if typeof(item) == TYPE_DICTIONARY:
				lines.append("• " + str(item.get("summary", "")))
	else:
		lines.append("会写入的公开事实：无")

	var strategic_signals = preview_data.get(
		"strategic_signals_to_apply",
		[]
	)
	if (
		typeof(strategic_signals) == TYPE_ARRAY
		and not strategic_signals.is_empty()
	):
		lines.append("会影响本局理解的策略信号：")
		for item in strategic_signals:
			if typeof(item) == TYPE_DICTIONARY:
				lines.append("• " + str(item.get("summary", "")))
	else:
		lines.append("策略信号：无")

	var text_only_notes = preview_data.get("text_only_notes", [])
	if typeof(text_only_notes) == TYPE_ARRAY and not text_only_notes.is_empty():
		lines.append("仅文本表达：")
		for note in text_only_notes:
			lines.append("• " + str(note))
	return _join_lines(lines)


func _format_speech_tone(tone: String) -> String:
	match tone:
		"suspicious":
			return L10n.t("怀疑")
		"claiming":
			return L10n.t("身份声明")
		_:
			return L10n.t("中性")


func _format_rag_retrieval_mode(retrieval_mode: String) -> String:
	return L10n.t("向量 + 关键词") if retrieval_mode == "hybrid" else L10n.t("关键词降级")


func _format_npc_speeches(speeches: Variant) -> String:
	if typeof(speeches) != TYPE_ARRAY or speeches.is_empty():
		return L10n.t("NPC 发言：暂无可显示的发言。")

	var lines: Array[String] = [L10n.t("NPC 发言：")]
	for speech in speeches:
		if typeof(speech) != TYPE_DICTIONARY:
			continue

		var character_id = speech.get("character_id", "?")
		var character_name = speech.get("name", "")
		var content = str(speech.get("speech", ""))
		lines.append(str(character_id) + L10n.t("号 ") + str(character_name) + "：" + content)

	if lines.size() == 1:
		return L10n.t("NPC 发言：后端已返回，但格式暂时无法显示。")

	return _join_lines(lines)


func _format_npc_vote_decisions(npc_votes: Variant) -> String:
	if typeof(npc_votes) != TYPE_ARRAY or npc_votes.is_empty():
		return L10n.t("NPC 投票：暂无可显示的投票。")

	var lines: Array[String] = [L10n.t("NPC 投票：")]
	for vote in npc_votes:
		if typeof(vote) != TYPE_DICTIONARY:
			continue

		var voter_id = vote.get("character_id", "?")
		var target_id = vote.get("target_id", "?")
		var reason = str(vote.get("reason", ""))
		lines.append(str(voter_id) + L10n.t("号 ") + "-> " + str(target_id) + L10n.t("号 ") + "：" + reason)
		var evidence_titles = vote.get("evidence_titles", [])
		if typeof(evidence_titles) == TYPE_ARRAY and not evidence_titles.is_empty():
			var evidence_parts: Array[String] = []
			for title in evidence_titles:
				evidence_parts.append(str(title))
			var mode := _format_rag_retrieval_mode(str(vote.get("retrieval_mode", "keyword")))
			lines.append(L10n.t("依据：") + _join_inline(evidence_parts) + " | " + mode)

	if lines.size() == 1:
		return L10n.t("NPC 投票：后端已返回，但格式暂时无法显示。")

	return _join_lines(lines)


func _format_sheriff_vote_result(vote_data: Dictionary) -> String:
	var lines: Array[String] = ["警长票型："]
	var ballots = vote_data.get("ballots", [])
	if typeof(ballots) == TYPE_ARRAY:
		for ballot in ballots:
			if typeof(ballot) != TYPE_DICTIONARY:
				continue
			lines.append(str(ballot.get("voter_id", "?")) + "号 -> " + str(ballot.get("target_id", "?")) + "号")
	lines.append(str(vote_data.get("message", "警长投票已完成。")))
	return _join_lines(lines)


func _format_combined_vote_result(vote_data: Dictionary) -> String:
	var lines: Array[String] = ["票型总览"]
	var ballots = vote_data.get("ballots", [])
	if typeof(ballots) == TYPE_ARRAY:
		for ballot in ballots:
			if typeof(ballot) != TYPE_DICTIONARY:
				continue
			var weight := float(ballot.get("weight", 1.0))
			var sheriff_mark := " [警长 " + str(weight) + "票]" if bool(ballot.get("is_sheriff", false)) else ""
			lines.append(
				str(ballot.get("voter_id", "?")) + "号 " + str(ballot.get("voter_name", "未知"))
				+ " -> " + str(ballot.get("target_id", "?")) + "号 " + str(ballot.get("target_name", "未知"))
				+ sheriff_mark
			)

	var totals = vote_data.get("vote_totals", {})
	if typeof(totals) == TYPE_DICTIONARY and not totals.is_empty():
		var total_parts: Array[String] = []
		var total_ids = totals.keys()
		total_ids.sort_custom(func(a, b): return int(a) < int(b))
		for target_id in total_ids:
			total_parts.append(str(target_id) + "号=" + str(totals[target_id]) + "票")
		lines.append("合计：" + _join_inline(total_parts))

	lines.append("")
	lines.append("详细理由")
	if typeof(ballots) == TYPE_ARRAY:
		for ballot in ballots:
			if typeof(ballot) != TYPE_DICTIONARY:
				continue
			lines.append(
				str(ballot.get("voter_id", "?")) + "号投给" + str(ballot.get("target_id", "?"))
				+ "号：" + str(ballot.get("reason", "未提供理由。"))
			)
			var evidence_titles = ballot.get("evidence_titles", [])
			if typeof(evidence_titles) == TYPE_ARRAY and not evidence_titles.is_empty():
				var evidence_parts: Array[String] = []
				for title in evidence_titles:
					evidence_parts.append(str(title))
				lines.append(
					"依据：" + _join_inline(evidence_parts)
					+ " | " + _format_rag_retrieval_mode(str(ballot.get("retrieval_mode", "keyword")))
				)
	lines.append(str(vote_data.get("public_message", "投票已结算。")))
	return _join_lines(lines)


func _format_vote_resolve_result(vote_data: Dictionary) -> String:
	var lines: Array[String] = [str(vote_data.get("public_message", "投票已结算。"))]
	var vote_result = vote_data.get("vote_result", {})
	if typeof(vote_result) == TYPE_DICTIONARY and not vote_result.is_empty():
		var vote_parts: Array[String] = []
		for voter_id in vote_result.keys():
			vote_parts.append(str(voter_id) + "->" + str(vote_result[voter_id]))
		lines.append("投票结果：" + _join_inline(vote_parts))

	var winner = vote_data.get("winner", null)
	if winner != null:
		lines.append("胜利阵营：" + _format_winner_name(str(winner)))

	return _join_lines(lines)


func _format_winner_name(winner: String) -> String:
	match winner:
		"good":
			return "好人阵营"
		"werewolf":
			return "狼人阵营"
		_:
			return winner


func _format_public_logs(public_logs: Variant) -> String:
	if typeof(public_logs) != TYPE_ARRAY or public_logs.is_empty():
		return "公开日志：暂无"

	var lines: Array[String] = ["公开日志："]
	var start_index = max(0, public_logs.size() - 4)
	for index in range(start_index, public_logs.size()):
		lines.append("- " + str(public_logs[index]))

	var output := ""
	for line_index in range(lines.size()):
		if line_index > 0:
			output += "\n"
		output += lines[line_index]
	return output


func _public_evidence_marker(category: String) -> String:
	match category:
		"confirmed_action":
			return "●"
		"commitment", "public_commitment":
			return "◆"
		_:
			return "◇"


func _public_commitment_status_marker(status: String) -> String:
	match status:
		"active":
			return "○"
		"superseded":
			return "↻"
		"fulfilled":
			return "✓"
		"invalidated":
			return "—"
		"undetermined":
			return "?"
		"contradicted":
			return "!"
		_:
			return "?"


func _public_commitment_status_label(status: String) -> String:
	match status:
		"active":
			return "进行中"
		"superseded":
			return "已被公开修订替代"
		"fulfilled":
			return "已有一致的公开后续"
		"invalidated":
			return "公开条件已失效"
		"undetermined":
			return "公开信息不足"
		"contradicted":
			return "后续记录不一致 · 待核对"
		_:
			return "未知状态"


func _format_public_evidence_analysis(analysis: Variant) -> Array[String]:
	var lines: Array[String] = []
	if (
		typeof(analysis) != TYPE_DICTIONARY
		or str(analysis.get("schema_version", "")) != "public_evidence_analysis.v1"
	):
		return lines

	lines.append("公开承诺状态与矛盾候选：")
	var disclaimer := str(analysis.get("disclaimer", "")).strip_edges()
	if disclaimer.is_empty():
		disclaimer = "仅依据公开记录，不引入隐藏身份或赛后真相。"
	lines.append("说明：" + disclaimer)
	lines.append("! 矛盾候选仅供核对，不代表说谎或阵营判断。")

	var commitments = analysis.get("commitments", [])
	var has_commitments: bool = (
		typeof(commitments) == TYPE_ARRAY and not commitments.is_empty()
	)
	if has_commitments:
		lines.append("承诺状态：")
		for commitment in commitments:
			if typeof(commitment) != TYPE_DICTIONARY:
				continue
			var display_text := str(commitment.get("display_text", "")).strip_edges()
			if display_text.is_empty():
				continue
			var sequence := int(commitment.get("sequence", 0))
			var day := int(commitment.get("day", _current_wolf_day))
			var effective_night_day := int(commitment.get("effective_night_day", day))
			var status := str(commitment.get("status", "undetermined"))
			var marker := _public_commitment_status_marker(status)
			var status_label := _public_commitment_status_label(status)
			lines.append(
				"C#" + str(sequence) + " " + marker + " " + status_label
				+ " · 第" + str(day) + "天公开 / 第" + str(effective_night_day) + "夜生效"
				+ " · " + display_text
			)

	var candidates = analysis.get("contradiction_candidates", [])
	var has_candidates: bool = (
		typeof(candidates) == TYPE_ARRAY and not candidates.is_empty()
	)
	if has_candidates:
		lines.append("矛盾候选（待核对）：")
		for candidate in candidates:
			if typeof(candidate) != TYPE_DICTIONARY:
				continue
			var display_text := str(candidate.get("display_text", "")).strip_edges()
			if display_text.is_empty():
				continue
			var sequence := int(candidate.get("sequence", 0))
			var day := int(candidate.get("day", _current_wolf_day))
			lines.append(
				"X#" + str(sequence) + " ! 待核对 · 第" + str(day) + "天 · " + display_text
			)

	if not has_commitments and not has_candidates:
		lines.append("暂无公开承诺状态或矛盾候选。")
	return lines


func _format_public_evidence_timeline(
	timeline: Variant,
	analysis: Variant,
	public_logs: Variant
) -> String:
	if (
		typeof(timeline) != TYPE_DICTIONARY
		or str(timeline.get("schema_version", "")) != "public_evidence_timeline.v1"
	):
		return _format_public_logs(public_logs)

	var projected_sequence := int(timeline.get("projected_event_sequence", 0))
	var lines: Array[String] = [
		"公开证据时间线 · 规则事件 #" + str(projected_sequence),
		"◇ 公开说法（真假未确认） · ◆ 公开承诺（未验真） · ● 已确认公开动作",
	]
	var items = timeline.get("items", [])
	if typeof(items) == TYPE_ARRAY:
		for item in items:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var display_text := str(item.get("display_text", "")).strip_edges()
			if display_text.is_empty():
				continue
			var sequence := int(item.get("sequence", lines.size() - 1))
			var day := int(item.get("day", _current_wolf_day))
			var marker := _public_evidence_marker(str(item.get("category", "claim")))
			lines.append(
				"#" + str(sequence) + " " + marker + " 第" + str(day) + "天 · " + display_text
			)
	if lines.size() == 2:
		lines.append("暂无结构化公开证据。")

	var analysis_lines := _format_public_evidence_analysis(analysis)
	if not analysis_lines.is_empty():
		lines.append("")
		for analysis_line in analysis_lines:
			lines.append(analysis_line)

	var recent_logs := _format_public_logs(public_logs)
	if recent_logs != "公开日志：暂无":
		lines.append("")
		lines.append(recent_logs)
	return "\n".join(lines)


func _join_lines(lines: Array[String]) -> String:
	var output := ""
	for line_index in range(lines.size()):
		if line_index > 0:
			output += "\n"
		output += lines[line_index]
	return output


func _join_inline(parts: Array[String]) -> String:
	var output := ""
	for part_index in range(parts.size()):
		if part_index > 0:
			output += ", "
		output += parts[part_index]
	return output


func _get_http_error_message(body: PackedByteArray, fallback: String) -> String:
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var detail := str(json.data.get("detail", "")).strip_edges()
		if not detail.is_empty():
			return detail
	return fallback


func _reset_game_summary() -> void:
	if _is_loading_game_summary:
		game_summary_request.cancel_request()
	_is_loading_game_summary = false
	_summary_requested_game_id = ""
	_game_summary_pending_after_onboarding = false
	_game_summary_data.clear()
	review_game_button.disabled = true
	_hide_game_summary()
	_clear_control_children(game_summary_character_list)
	game_summary_timeline_label.text = "暂无时间线。"
	game_summary_review_label.text = "仅在游戏结束后生成解释复盘。"


func _show_game_summary() -> void:
	if _game_summary_data.is_empty():
		return
	if onboarding_overlay.visible:
		_game_summary_pending_after_onboarding = (
			not _onboarding_manual_mode
			and _onboarding_status == "active"
		)
		return
	if not game_summary_overlay.visible:
		_summary_focus_return = _current_focus_control()
	if dialog_box.call("is_open"):
		dialog_box.call("hide_dialog", false)
	if game_setup_overlay.visible:
		_hide_game_setup(false)
	if _intel_panel_open:
		_set_intel_panel_open(false, false)
	if _wolf_menu_expanded:
		_set_wolf_menu_expanded(false)
	game_summary_overlay.visible = true
	game_summary_overlay.add_to_group("dialog_open")
	game_summary_tabs.current_tab = 0
	_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	call_deferred("_focus_control_if_available", game_summary_close_button)


func _hide_game_summary() -> void:
	if not game_summary_overlay.visible:
		return
	var return_focus := _summary_focus_return
	_summary_focus_return = null
	game_summary_overlay.visible = false
	game_summary_overlay.remove_from_group("dialog_open")
	game_summary_close_button.release_focus()
	_release_movement_actions()
	call_deferred(
		"_restore_focus_after_close",
		return_focus,
		review_game_button
	)


func _render_game_summary(summary: Dictionary) -> void:
	var winner_label := str(summary.get("winner_label", "未知阵营"))
	var total_days := int(summary.get("total_days", 0))
	var winner_message := str(summary.get("winner_message", "游戏结束。"))
	game_summary_winner_label.text = (
		winner_label + "胜利 | 共 " + str(total_days) + " 天\n" + winner_message
	)
	highlights_label.text = "\n".join(_build_highlights(summary))

	_clear_control_children(game_summary_character_list)
	var characters = summary.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) == TYPE_DICTIONARY:
				game_summary_character_list.add_child(_build_summary_character_item(character))

	var timeline = summary.get("timeline", [])
	var timeline_lines: Array[String] = []
	if typeof(timeline) == TYPE_ARRAY:
		for event in timeline:
			if typeof(event) == TYPE_DICTIONARY:
				timeline_lines.append(_format_summary_event(event))
	var validation_failures = summary.get("llm_validation_failures", [])
	if typeof(validation_failures) == TYPE_ARRAY and not validation_failures.is_empty():
		timeline_lines.append(_format_summary_llm_failures(validation_failures))
	game_summary_timeline_label.text = (
		"暂无行动记录。" if timeline_lines.is_empty() else "\n\n".join(timeline_lines)
	)
	var suggestions := _build_review_suggestions(summary)
	var review_text := _format_post_game_explainable_review(
		summary.get("explainable_review", {})
	)
	if not suggestions.is_empty():
		review_text = "【复盘建议】\n" + "\n".join(suggestions) + "\n\n" + review_text
	game_summary_review_label.text = review_text


func _format_post_game_explainable_review(review: Variant) -> String:
	if (
		typeof(review) != TYPE_DICTIONARY
		or str(review.get("schema_version", "")) != "post_game_explainable_review.v1"
	):
		return "本局没有可用的解释复盘。"

	var lines: Array[String] = [
		"【赛后真值已解锁】以下身份与阵营仅用于复盘，不代表角色当时可见。",
		str(review.get("disclaimer", "")),
	]
	var counts = review.get("assessment_counts", {})
	if typeof(counts) == TYPE_DICTIONARY:
		lines.append(
			"共 " + str(review.get("review_count", 0)) + " 条决定"
			+ " · 判断正确 " + str(counts.get("accurate", 0))
			+ " · 判断错误 " + str(counts.get("mistaken", 0))
			+ " · 狼人策略 " + str(counts.get("strategic", 0))
			+ " · 中性/不可评分 "
			+ str(int(counts.get("neutral", 0)) + int(counts.get("unscored", 0)))
		)

	var items = review.get("items", [])
	if typeof(items) != TYPE_ARRAY or items.is_empty():
		lines.append("\n本局没有保存可解释的发言、投票或技能决定。")
		return "\n".join(lines)

	for item in items:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var assessment := str(item.get("assessment", "unscored"))
		var error_category := str(item.get("error_category", "not_applicable"))
		lines.append("")
		lines.append(
			"#" + str(item.get("sequence", "?"))
			+ " · 第" + str(item.get("day", "?")) + "天"
			+ " · " + _post_game_decision_kind_label(
				str(item.get("decision_kind", ""))
			)
			+ " · " + str(item.get("actor_id", "?")) + "号"
			+ str(item.get("actor_name", "未知"))
		)
		lines.append("选择：" + str(item.get("decision_summary", "未记录")))

		var prior_evidence = item.get("prior_public_evidence", [])
		lines.append("当时可核对（仅更早日期的公开证据）：")
		if typeof(prior_evidence) == TYPE_ARRAY and not prior_evidence.is_empty():
			for reference in prior_evidence:
				if typeof(reference) == TYPE_DICTIONARY:
					lines.append(
						"  - 第" + str(reference.get("day", "?")) + "天："
						+ str(reference.get("display_text", ""))
					)
		else:
			lines.append("  - 没有匹配到更早日期的相关公开证据。")

		var recorded_basis = item.get("recorded_basis", [])
		lines.append("提交时保存的依据：")
		if typeof(recorded_basis) == TYPE_ARRAY and not recorded_basis.is_empty():
			for basis in recorded_basis:
				lines.append("  - " + str(basis))
		else:
			lines.append("  - 未保存结构化依据。")

		lines.append(
			"赛后评价：" + _post_game_assessment_label(assessment)
			+ " / " + _post_game_error_category_label(error_category)
		)
		lines.append(str(item.get("truth_summary", "赛后真值缺失。")))
		lines.append("解释：" + str(item.get("explanation", "未生成解释。")))

		var later_evidence = item.get("later_public_evidence", [])
		lines.append("后来可核对（仅更晚日期的公开证据）：")
		if typeof(later_evidence) == TYPE_ARRAY and not later_evidence.is_empty():
			for reference in later_evidence:
				if typeof(reference) == TYPE_DICTIONARY:
					lines.append(
						"  - 第" + str(reference.get("day", "?")) + "天："
						+ str(reference.get("display_text", ""))
					)
		else:
			lines.append("  - 没有匹配到更晚日期的相关公开记录。")

	return "\n".join(lines)


func _post_game_decision_kind_label(kind: String) -> String:
	match kind:
		"public_speech":
			return "公开发言"
		"exile_vote":
			return "放逐投票"
		"night_action":
			return "夜间技能"
		"hunter_shot":
			return "猎人开枪"
		_:
			return "其他决定"


func _post_game_assessment_label(assessment: String) -> String:
	match assessment:
		"accurate":
			return "方向正确"
		"mistaken":
			return "判断错误"
		"strategic":
			return "狼人阵营策略"
		"neutral":
			return "中性结果"
		"unscored":
			return "依据不足，无法评分"
		_:
			return "无法评分"


func _post_game_error_category_label(category: String) -> String:
	match category:
		"none":
			return "无错误"
		"deceived":
			return "受到欺骗"
		"insufficient_evidence":
			return "证据不足"
		"continuity_break":
			return "连续性断裂"
		"skill_misuse":
			return "角色技能误用"
		"deterministic_variance":
			return "确定性概率扰动"
		"not_applicable":
			return "不适用"
		_:
			return "未分类"


func _format_summary_llm_failures(failures: Array) -> String:
	var lines: Array[String] = ["LLM 校验失败完整记录"]
	for failure in failures:
		if typeof(failure) != TYPE_DICTIONARY:
			continue
		var character_id := int(failure.get("character_id", 0))
		var character_name := str(_wolf_character_names.get(character_id, "未知"))
		lines.append(
			str(character_id) + "号" + character_name + " | "
			+ str(failure.get("context_kind", "npc_text"))
		)
		var attempts = failure.get("attempts", [])
		if typeof(attempts) != TYPE_ARRAY:
			continue
		for attempt in attempts:
			if typeof(attempt) != TYPE_DICTIONARY:
				continue
			lines.append(
				"第 " + str(attempt.get("attempt", "?")) + " 次："
				+ str(attempt.get("text", "[无返回内容]"))
				+ "\n原因：" + str(attempt.get("rejection_reason", "未知"))
			)
	return "\n\n".join(lines)


func _build_summary_character_item(character: Dictionary) -> Control:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.12, 0.145, 0.17, 0.96)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.34, 0.41, 0.48, 1)
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_right = 6
	style.corner_radius_bottom_left = 6
	panel.add_theme_stylebox_override("panel", style)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_bottom", 8)
	panel.add_child(margin)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 6)
	margin.add_child(content)

	var title := (
		str(character.get("character_id", "?")) + "号 "
		+ str(character.get("name", "未知")) + " | "
		+ str(character.get("role_label", "未知身份")) + " | "
		+ str(character.get("camp_label", "未知阵营")) + " | "
		+ str(character.get("outcome", "未知结果"))
	)
	var header := Button.new()
	header.text = "▶ " + title
	header.alignment = HORIZONTAL_ALIGNMENT_LEFT
	header.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.set_meta("summary_title", title)
	content.add_child(header)

	var actions_label := Label.new()
	actions_label.visible = false
	actions_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	actions_label.add_theme_color_override("font_color", Color(0.84, 0.88, 0.9, 1))
	actions_label.add_theme_font_size_override("font_size", 13)
	var action_lines: Array[String] = []
	var actions = character.get("actions", [])
	if typeof(actions) == TYPE_ARRAY:
		for action in actions:
			if typeof(action) == TYPE_DICTIONARY:
				action_lines.append(_format_summary_event(action))
	actions_label.text = "本局没有单独行动记录。" if action_lines.is_empty() else "\n\n".join(action_lines)
	content.add_child(actions_label)
	header.pressed.connect(_toggle_summary_character_item.bind(header, actions_label))
	return panel


func _toggle_summary_character_item(header: Button, actions_label: Label) -> void:
	actions_label.visible = not actions_label.visible
	var marker := "▼ " if actions_label.visible else "▶ "
	header.text = marker + str(header.get_meta("summary_title", "角色复盘"))


func _format_summary_event(event: Dictionary) -> String:
	var day := int(event.get("day", 0))
	var phase := _format_summary_phase(str(event.get("phase", "")))
	var private_mark := " [私密]" if bool(event.get("is_private", false)) else ""
	return "第 " + str(day) + " 天 · " + phase + private_mark + "\n" + str(event.get("text", ""))


func _format_summary_phase(phase: String) -> String:
	match phase:
		"NIGHT":
			return "夜晚行动"
		"NIGHT_RESULT":
			return "夜晚结果"
		"HUNTER_SHOT":
			return "猎人开枪"
		"SHERIFF", "SHERIFF_SPEECH":
			return "警上竞选"
		"SHERIFF_RUNOFF_SPEECH":
			return "警上 PK"
		"DAY_MEETING":
			return "小镇会议"
		"FREE_ACTIVITY":
			return "会后私聊"
		"VOTE":
			return "投票"
		"VOTE_RESULT":
			return "放逐结果"
		"GAME_OVER":
			return "游戏结果"
		_:
			return phase


func _clear_control_children(container: Control) -> void:
	for child in container.get_children():
		child.queue_free()


func _release_movement_actions() -> void:
	for action in ["move_left", "move_right", "move_up", "move_down"]:
		if InputMap.has_action(action):
			Input.action_release(action)
	_lock_player_movement_until_release()


func _finish_gameplay_text_submission(input: LineEdit) -> void:
	_play_sfx("confirm")
	input.clear()
	input.release_focus()
	_release_focus_to_world()
	_release_movement_actions()


func _restore_failed_gameplay_text(input: LineEdit, text: String) -> void:
	if text.is_empty():
		return
	input.text = text
	input.grab_focus()
	_lock_player_movement_until_release()


func _lock_player_movement_until_release() -> void:
	if player.has_method("lock_movement_until_release"):
		player.call("lock_movement_until_release")


func _configure_ui_focus_navigation() -> void:
	var ui_roots: Array[Control] = [
		phase_hud,
		identity_panel,
		wolf_panel,
		intel_panel,
		game_setup_overlay,
		game_summary_overlay,
		onboarding_overlay,
		dialog_box,
		knowledge_overlay,
		stats_overlay,
		menu_overlay,
		archive_overlay,
		replay_overlay,
	]
	for ui_root in ui_roots:
		for node in ui_root.find_children("*", "BaseButton", true, false):
			if node is Control:
				node.focus_mode = Control.FOCUS_ALL
		for node in ui_root.find_children("*", "ScrollContainer", true, false):
			if node is Control:
				node.focus_mode = Control.FOCUS_ALL
	var tab_containers: Array[TabContainer] = [intel_tabs, game_summary_tabs]
	for tab_container in tab_containers:
		var tab_bar: TabBar = tab_container.get_tab_bar()
		tab_bar.focus_mode = Control.FOCUS_ALL
	player_action_history_text.focus_mode = Control.FOCUS_ALL

	for ui_root in ui_roots:
		for node in ui_root.find_children("*", "Control", true, false):
			if node is Control and node.focus_mode != Control.FOCUS_NONE:
				var focus_callback := _on_ui_control_focus_entered.bind(node)
				if not node.focus_entered.is_connected(focus_callback):
					node.focus_entered.connect(focus_callback)
				var blur_callback := _on_ui_control_focus_exited.bind(node)
				if not node.focus_exited.is_connected(blur_callback):
					node.focus_exited.connect(blur_callback)


func _on_ui_control_focus_entered(control: Control) -> void:
	if control is ScrollContainer:
		_set_scroll_focus_outline(control, true)
	if _control_is_in_visible_modal(control):
		_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
	elif _control_is_editable_text(control):
		_set_ui_focus_scope(UI_FOCUS_SCOPE_TEXT_ENTRY)
	else:
		_set_ui_focus_scope(UI_FOCUS_SCOPE_PANEL)
	_ensure_focused_control_visible(control)


func _on_ui_control_focus_exited(control: Control) -> void:
	if control is ScrollContainer:
		_set_scroll_focus_outline(control, false)
	call_deferred("_repair_focus_after_modal_close")


func _set_scroll_focus_outline(scroll: ScrollContainer, focused: bool) -> void:
	if not focused:
		scroll.remove_theme_stylebox_override("panel")
		return
	var outline := StyleBoxFlat.new()
	outline.draw_center = false
	outline.border_width_left = 3
	outline.border_width_top = 3
	outline.border_width_right = 3
	outline.border_width_bottom = 3
	outline.border_color = Color(1.0, 0.78, 0.24, 1.0)
	outline.corner_radius_top_left = 7
	outline.corner_radius_top_right = 7
	outline.corner_radius_bottom_right = 7
	outline.corner_radius_bottom_left = 7
	scroll.add_theme_stylebox_override("panel", outline)


func _set_ui_focus_scope(scope: String) -> void:
	_ui_focus_scope = scope
	if player.has_method("set_ui_navigation_locked"):
		player.call("set_ui_navigation_locked", scope != UI_FOCUS_SCOPE_WORLD)


func _current_focus_control() -> Control:
	var focus_owner := get_viewport().gui_get_focus_owner()
	return focus_owner if focus_owner is Control else null


func _control_is_editable_text(control: Control) -> bool:
	if control is LineEdit:
		return control.editable
	if control is TextEdit:
		return control.editable
	return false


func _current_focus_is_editable_text() -> bool:
	var focus_owner := _current_focus_control()
	return focus_owner != null and _control_is_editable_text(focus_owner)


func _control_is_in_visible_modal(control: Control) -> bool:
	for modal_root in [
		onboarding_overlay,
		game_summary_overlay,
		game_setup_overlay,
		speech_preview_panel,
		dialog_box,
	]:
		var modal_control := modal_root as Control
		if (
			modal_control != null
			and modal_control.is_visible_in_tree()
			and (control == modal_control or modal_control.is_ancestor_of(control))
		):
			return true
	return false


func _is_wasd_key_event(event: InputEvent) -> bool:
	if not event is InputEventKey or not event.pressed or event.echo:
		return false
	var key_event := event as InputEventKey
	return key_event.physical_keycode in [KEY_W, KEY_A, KEY_S, KEY_D]


func _handle_modal_focus_direction(event: InputEvent, scope: Control) -> bool:
	var focus_owner := _current_focus_control()
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
	if focus_owner is TabBar:
		if event.is_action_pressed("ui_left") or event.is_action_pressed("ui_right"):
			return false
	if event.is_action_pressed("ui_left") or event.is_action_pressed("ui_up"):
		_move_focus_in_scope(scope, -1)
		return true
	if event.is_action_pressed("ui_right") or event.is_action_pressed("ui_down"):
		_move_focus_in_scope(scope, 1)
		return true
	return false


func _move_focus_in_active_panel(direction: int) -> void:
	_move_focus_in_roots(
		[phase_hud, identity_panel, wolf_panel, intel_panel],
		direction
	)


func _move_focus_in_scope(scope: Control, direction: int) -> void:
	_move_focus_in_roots([scope], direction)


func _move_focus_in_roots(roots: Array, direction: int) -> void:
	var focusable := _focusable_controls_in_roots(roots)
	if focusable.is_empty():
		return
	var focus_owner := _current_focus_control()
	var current_index := focusable.find(focus_owner)
	if current_index < 0:
		current_index = 0 if direction >= 0 else focusable.size() - 1
	else:
		current_index = posmod(current_index + direction, focusable.size())
	focusable[current_index].grab_focus()


func _focusable_controls_in_roots(roots: Array) -> Array[Control]:
	var focusable: Array[Control] = []
	for root in roots:
		var control_root := root as Control
		if control_root == null or not control_root.is_visible_in_tree():
			continue
		if _is_focus_candidate(control_root):
			focusable.append(control_root)
		for node in control_root.find_children("*", "Control", true, false):
			if node is Control and _is_focus_candidate(node):
				focusable.append(node)
	return focusable


func _is_focus_candidate(control: Control) -> bool:
	if not control.is_visible_in_tree() or control.focus_mode == Control.FOCUS_NONE:
		return false
	if control is BaseButton and control.disabled:
		return false
	if control is LineEdit and not control.editable:
		return false
	return true


func _focus_control_if_available(control: Control) -> void:
	if control != null and is_instance_valid(control) and _is_focus_candidate(control):
		control.grab_focus()
		return
	_repair_focus_in_top_scope()


func _restore_focus_after_close(
	preferred: Control,
	fallback: Control,
) -> void:
	for candidate in [preferred, fallback]:
		if (
			candidate != null
			and is_instance_valid(candidate)
			and _is_focus_candidate(candidate)
		):
			candidate.grab_focus()
			return
	_release_focus_to_world()


func _on_dialog_closed() -> void:
	call_deferred("_repair_focus_after_modal_close")


func _repair_focus_after_modal_close() -> void:
	if (
		onboarding_overlay.visible
		or game_summary_overlay.visible
		or game_setup_overlay.visible
		or speech_preview_panel.is_visible_in_tree()
		or dialog_box.call("is_open")
	):
		_set_ui_focus_scope(UI_FOCUS_SCOPE_MODAL)
		_repair_focus_in_top_scope()
		return
	var focus_owner := _current_focus_control()
	if focus_owner != null and _is_focus_candidate(focus_owner):
		_on_ui_control_focus_entered(focus_owner)
		return
	_release_focus_to_world()


func _repair_focus_in_top_scope() -> void:
	var scope: Control
	if onboarding_overlay.visible:
		scope = onboarding_overlay
	elif game_summary_overlay.visible:
		scope = game_summary_overlay
	elif game_setup_overlay.visible:
		scope = game_setup_overlay
	elif speech_preview_panel.is_visible_in_tree():
		scope = speech_preview_panel
	elif dialog_box.call("is_open"):
		scope = dialog_box
	else:
		if _ui_focus_scope == UI_FOCUS_SCOPE_WORLD:
			return
		var panel_focusable := _focusable_controls_in_roots(
			[phase_hud, identity_panel, wolf_panel, intel_panel]
		)
		if panel_focusable.is_empty():
			_release_focus_to_world()
		else:
			panel_focusable[0].grab_focus()
		return
	var focus_owner := _current_focus_control()
	if (
		focus_owner != null
		and (focus_owner == scope or scope.is_ancestor_of(focus_owner))
		and _is_focus_candidate(focus_owner)
	):
		return
	var focusable := _focusable_controls_in_roots([scope])
	if not focusable.is_empty():
		focusable[0].grab_focus()


func _ensure_focused_control_visible(control: Control) -> void:
	var ancestor := control.get_parent()
	while ancestor != null:
		if ancestor is ScrollContainer:
			ancestor.ensure_control_visible(control)
		ancestor = ancestor.get_parent()


func _release_focus_to_world() -> void:
	var focus_owner := _current_focus_control()
	if focus_owner != null:
		focus_owner.release_focus()
	get_viewport().gui_release_focus()
	_set_ui_focus_scope(UI_FOCUS_SCOPE_WORLD)


func _release_wolf_panel_focus() -> void:
	var focus_owner := get_viewport().gui_get_focus_owner()
	if focus_owner == null:
		return
	if focus_owner == wolf_panel or wolf_panel.is_ancestor_of(focus_owner):
		_release_focus_to_world()


func _build_character_card(character: Dictionary) -> Control:
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(_character_card_min_width, 205.0)
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.95, 0.985, 1.0, 0.98)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.38, 0.69, 0.82, 1)
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_right = 6
	style.corner_radius_bottom_left = 6

	if character.get("is_player", false):
		style.bg_color = Color(1.0, 0.95, 0.7, 0.99)
		style.border_color = Color(0.88, 0.61, 0.08, 1)

	card.add_theme_stylebox_override("panel", style)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_top", 6)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_bottom", 6)
	card.add_child(margin)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 4)
	margin.add_child(content)

	var portrait := TextureRect.new()
	portrait.custom_minimum_size = Vector2(52, 52)
	portrait.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	portrait.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	var skin_path := "res://assets/characters/player.svg" if character.get("is_player", false) else str(CHARACTER_SKIN_PATHS.get(str(character.get("name", "")), ""))
	if not skin_path.is_empty() and ResourceLoader.exists(skin_path):
		var skin_texture = load(skin_path)
		if skin_texture is Texture2D:
			portrait.texture = skin_texture
	portrait.modulate = Color(0.45, 0.45, 0.45, 0.65) if not character.get("alive", true) else Color.WHITE
	content.add_child(portrait)

	var label := Label.new()
	label.text = _format_character_card_text(character)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_color_override("font_color", Color(0, 0, 0, 1))
	label.add_theme_font_size_override("font_size", 12)
	content.add_child(label)

	return card


func _format_character_card_text(character: Dictionary) -> String:
	var character_id = character.get("id", "?")
	var character_name = character.get("name", "未知")
	var sheriff_text := " [警长]" if character.get("is_sheriff", false) else ""
	var alive_text = "存活" if character.get("alive", true) else "出局"
	var role = character.get("role_visible_to_player", null)
	var role_text = "身份：隐藏"
	if role != null:
		role_text = "身份：" + _format_role_name(str(role))
	var suspicion_score := int(character.get("suspicion_score", 0))
	var suspicion_level := str(character.get("suspicion_level", "无"))
	var suspicion_text := "关注：" + suspicion_level
	if suspicion_score > 0:
		suspicion_text += "(" + str(suspicion_score) + ")"
	var trust_text := "信任：自己"
	if not character.get("is_player", false):
		var trust_level := str(character.get("trust_level", "中"))
		var trust_value = character.get("trust_to_player", null)
		trust_text = "信任：" + trust_level
		if trust_value != null:
			trust_text += "(" + str(snapped(float(trust_value), 0.01)) + ")"
	var memory_text := "记忆：" + str(int(character.get("memory_count", 0)))
	var private_chat_text := "私聊：自己"
	if not character.get("is_player", false):
		private_chat_text = "私聊：已影响" if character.get("private_question_used_today", false) else "私聊：未追问"
	var claim_text := "公开：无身份声明"
	var public_claims = character.get("public_claims", [])
	if typeof(public_claims) == TYPE_ARRAY and not public_claims.is_empty():
		var claim_parts: Array[String] = []
		for claim in public_claims:
			claim_parts.append(str(claim))
		claim_text = "公开：" + "；".join(claim_parts)

	return str(character_id) + "号 " + str(character_name) + sheriff_text + "\n" + role_text + " | " + alive_text + "\n" + claim_text + "\n" + suspicion_text + "\n" + trust_text + "\n" + memory_text + " | " + private_chat_text


func _format_role_name(role: String) -> String:
	match role:
		"werewolf":
			return L10n.t("狼人")
		"seer":
			return L10n.t("预言家")
		"witch":
			return L10n.t("女巫")
		"hunter":
			return L10n.t("猎人")
		"guard":
			return L10n.t("守卫")
		"villager":
			return L10n.t("村民")
		"idiot":
			return L10n.t("白痴")
		_:
			return role


func _clear_character_grid() -> void:
	for child in character_grid.get_children():
		child.queue_free()


func _format_memory_preview(memories: Array) -> String:
	if memories.is_empty():
		return "这个 NPC 还没有记住任何对话。"

	var start_index = max(0, memories.size() - 3)
	var lines: Array[String] = ["最近记忆："]
	for index in range(start_index, memories.size()):
		var memory = memories[index]
		if typeof(memory) != TYPE_DICTIONARY:
			continue

		var message = str(memory.get("player_message", "")).strip_edges()
		if message.is_empty():
			message = "空消息"
		lines.append(str(index + 1) + ". 你说：" + message)

	if lines.size() == 1:
		return "这个 NPC 有记忆记录，但暂时无法显示内容。"

	var output := ""
	for line_index in range(lines.size()):
		if line_index > 0:
			output += "\n"
		output += lines[line_index]
	return output
