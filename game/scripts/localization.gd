extends Node

## Lightweight client-side localization for the Agent Town demo.
##
## Language is persisted in the session config (see main.gd) and applied by
## re-translating UI text through `t()`.  Backend-generated content (NPC
## speeches, public logs, review bodies, knowledge articles) is authored in
## Chinese and intentionally stays untouched in this milestone.

signal language_changed(language_code: String)

const SUPPORTED_LANGUAGES := ["zh", "en"]
const DEFAULT_LANGUAGE := "zh"

var language := DEFAULT_LANGUAGE

## Reverse mapping so `t()` is fully reversible: switching zh -> en -> zh must
## restore the original Chinese strings.  A few English values are shared by
## more than one Chinese source ("Intel" -> 情报 / 对局情报); those get an
## explicit override, and the UI walker additionally keeps per-node source
## metadata so ambiguous values still round-trip exactly.
const ENGLISH_REVERSE_OVERRIDES := {
	"Intel": "情报",
	"Player name": "玩家名",
	"Free activity": "自由活动",
	"Replay": "重播",
	"Load": "读档",
}
var ENGLISH_REVERSE: Dictionary = {}

const ENGLISH := {
	"上一步": "Back",
	"下一步": "Next",
	"下一顺验（可选）": "Next check (optional)",
	"不开枪": "Don't shoot",
	"仅你可见 · 我的身份": "Private · My identity",
	"仅你可见 · 狼队友：暂无": "Private · Wolf teammates: none",
	"仅你可见的行动记录": "Private action log",
	"仅在后端已配置 LLM 时生效": "Only takes effect when the backend has an LLM configured",
	"仅在游戏结束后生成解释复盘。": "The explanation review is generated after the game ends.",
	"今晚查验": "Check tonight",
	"例如：守卫能不能连续守？狼人怎么赢？": "e.g. Can the Guard guard two nights in a row? How do wolves win?",
	"信息范围：仅你可见": "Scope: visible only to you",
	"先在小镇自由探索": "Explore the town freely first",
	"先认清自己的身份": "First, recognize your identity",
	"公开证据时间线：暂无": "Public evidence timeline: none",
	"关键公开信息 · 暂无  ▼": "Key public info · none  ▼",
	"关闭": "Close",
	"关闭后生成 1 次、校验与纠错 0 次并直接显示；原文可能错误或越界，但 Python 规则结算仍独立生效": "Generates once with zero validation passes and shows the raw text; output may be wrong or out of scope, but Python rule resolution still applies independently",
	"关闭后续自动引导；仍可按 F1 手动查看": "Disables later auto hints; press F1 to open them manually",
	"关闭复盘": "Close review",
	"准备好后开始游戏，也可以先关闭窗口探索小镇。": "Press Start when ready, or close this window and explore the town first.",
	"上一局已结束，可以调整设置后开始新对局。": "The last game ended; adjust settings and start a new game.",
	"提示：右上角「规则」「战绩」随时可用；「继续上局」可恢复未完成对局。": "Tip: “Rulebook” and “Stats” are always available; “Continue last game” restores an unfinished game.",
	"创建 1 名玩家与 11 名 NPC 的十二人局。完整状态同步后会按阶段显示新手引导；测试选项不会改变正式规则。": "Creates a 12-player game with 1 player and 11 NPCs. Phase tutorial hints appear after full state sync; test options never change the real rules.",
	"刷新状态": "Refresh",
	"加载中...": "Loading...",
	"启用 AI NPC 表达": "Enable AI NPC speech",
	"启用 AI NPC 表达后可选；Python 规则结算始终独立生效": "Optional after enabling AI NPC speech; Python rule resolution always applies independently",
	"输出校验开启：不合格表达最多纠正 5 次": "Validation on: invalid speech is corrected up to 5 times",
	"输出校验关闭：生成 1 次、校验 0 次并直出原文；Python 规则结算不变": "Validation off: generates once with zero validation passes and shows raw text; Python rule resolution is unchanged",
	"启用 LLM 输出校验": "Enable LLM output validation",
	"启用音效与音乐": "Enable sound & music",
	"填写投票理由": "Write your vote reason",
	"夜晚行动：开始游戏后可用": "Night action: available after the game starts",
	"存档槽位": "Save slot",
	"存盘": "Save",
	"完整状态同步后，这里会说明你的身份、技能和当前阶段。": "After full state sync, this shows your identity, skills, and current phase.",
	"对局情报": "Intel",
	"对局重播": "Replay",
	"导出复盘": "Export review",
	"导出战绩": "Export stats",
	"尚未发布警徽流。": "Badge flow not announced yet.",
	"展开": "Expand",
	"展开场上已经公开的身份、验人和技能声明": "Expand public identity, check, and skill claims",
	"展开当前行动": "Expand current action",
	"开始一局狼人杀": "Start a Werewolf Game",
	"开始游戏": "Start Game",
	"开枪": "Shoot",
	"当前行动": "Current action",
	"快进会议": "Fast-forward meeting",
	"情报": "Intel",
	"我的战绩": "My stats",
	"打开菜单：规则百科、战绩、存盘、复盘、引导与刷新": "Open menu: rulebook, stats, save, review, guide, refresh",
	"把战绩与成就导出为文本文件": "Export stats & achievements to a text file",
	"把本局高光与时间线导出为文本文件": "Export highlights & timeline to a text file",
	"投票并公布": "Vote & reveal",
	"提交前预览": "Preview before submitting",
	"提交发言": "Submit speech",
	"提交行动": "Submit action",
	"提交警上发言": "Submit campaign speech",
	"搜索": "Search",
	"播放": "Play",
	"暂停": "Pause",
	"新对局": "New Game",
	"新手引导": "Tutorial",
	"新手阶段提示": "Phase tutorial hints",
	"暂无公开身份或技能声明。": "No public identity or skill claims yet.",
	"暂无时间线。": "No timeline yet.",
	"暂无行动记录。": "No action records yet.",
	"暂时关闭引导（Esc）": "Hide hints temporarily (Esc)",
	"暂时归票": "Temporary nomination",
	"本局复盘": "Game review",
	"查看场上角色、公开记录和我的记录": "View characters, public records, and your records",
	"槽位 1": "Slot 1",
	"槽位 2": "Slot 2",
	"槽位 3": "Slot 3",
	"读档": "Load",
	"载入": "Load",
	"空": "Empty",
	"对局": "Game",
	"资料": "Resources",
	"辅助": "Utilities",
	"这个存档槽位是空的": "This save slot is empty",
	"正在恢复上局...": "Resuming last game...",
	"进度已保存到本地存档。": "Progress saved to local storage.",
	"游戏结束后才能查看复盘": "The review is available after the game ends",
	"游戏结束后才能查看复盘。": "The review is available after the game ends.",
	"提示：也可在“新对局”弹窗选择存档槽位后点击“继续上局”恢复。": "Tip: you can also pick a slot in the “New Game” dialog and press “Continue last game”.",
	"正在读取对局结果...": "Reading game result...",
	"测试身份": "Test identity",
	"猎人开枪：出局后可用": "Hunter shot: available after elimination",
	"玩家": "Player",
	"玩家名": "Player name",
	"玩家名字": "Player name",
	"理由对象": "Reason target",
	"白天发言：开始游戏后可用": "Day speech: available after the game starts",
	"白天投票：开始游戏后可用": "Day vote: available after the game starts",
	"确认": "Confirm",
	"确认提交": "Confirm submission",
	"票型：尚未公布": "Vote tally: not revealed yet",
	"第 0 / 0 步": "Step 0 / 0",
	"等待 Python 解析。": "Waiting for Python parsing.",
	"等待分配": "Waiting for assignment",
	"等待开始": "Waiting to start",
	"系统状态：等待开始": "Status: waiting to start",
	"结束自由活动": "End free activity",
	"结算": "Resolve",
	"继续上局": "Continue last game",
	"继续竞选": "Continue campaign",
	"若验出查杀": "If check reveals wolf",
	"若验出金水": "If check reveals good",
	"菜单": "Menu",
	"规则百科": "Rulebook",
	"角色档案": "Character archive",
	"警上名单：暂无": "Campaign list: none",
	"警徽流": "Badge flow",
	"警长操作：第一夜结束后可用": "Sheriff actions: available after night 1",
	"设置并开始新对局": "Configure & start a new game",
	"请从顶部“新对局”开始。": "Start from the “New Game” button at the top.",
	"调整理由": "Adjust reason",
	"跳过全部": "Skip all",
	"输入白天发言": "Enter your day speech",
	"输入警上或 PK 发言": "Enter campaign or runoff speech",
	"输入问题后按回车搜索。": "Type a question and press Enter to search.",
	"返回修改": "Back to edit",
	"退水": "Withdraw",
	"逐步重播本局时间线": "Step through the game timeline",
	"重播": "Replay",
	"随本次发言发布": "Announce with this speech",
	"音乐": "Music",
	"音效": "SFX",
	"默认随机；指定身份仅用于测试角色技能": "Random by default; specifying an identity only tests role skills",
	"语言 / Language": "Language",
	"中文": "中文",
	"English": "English",
	"等待发言": "waiting to speak",
	"会议 · ": "Meeting · ",
	"第 ": "Day ",
	" 天": "",
	"夜晚 ": "Night ",
	" 夜": "",
	"猎人开枪": "Hunter shot",
	"警上报名": "Campaign signup",
	"警上发言": "Campaign speech",
	"退水阶段": "Withdrawal",
	"警长投票": "Sheriff vote",
	"警上 PK": "Campaign runoff",
	"PK 投票": "Runoff vote",
	"警长选发言侧": "Sheriff picks side",
	"警长归票": "Sheriff nomination",
	"移交警徽": "Badge transfer",
	"自由活动": "Free activity",
	"投票阶段": "Vote phase",
	"游戏结束": "Game over",
	"预言家": "Seer",
	"女巫": "Witch",
	"猎人": "Hunter",
	"守卫": "Guard",
	"狼人": "Werewolf",
	"村民": "Villager",
	"白痴": "Idiot",
	"（已翻牌，不能投票）": " (flipped, cannot vote)",
	"随机身份": "Random",
	"狼人（测试）": "Werewolf (test)",
	"预言家（测试）": "Seer (test)",
	"女巫（测试）": "Witch (test)",
	"猎人（测试）": "Hunter (test)",
	"守卫（测试）": "Guard (test)",
	"村民（测试）": "Villager (test)",
	"白痴（测试）": "Idiot (test)",
	"对局变体": "Variant",
	"经典局": "Classic",
	"白痴局": "Idiot game",
	"NPC 策略模式": "NPC strategy mode",
	"规则模式": "Rule mode",
	"影子模式": "Shadow mode",
	"本地模型": "Local model",
	"策略：": "Strategy: ",
	"规则模式：NPC 全部使用 Python 规则评分（确定性、可复现）。本地模型：用已训练的本地策略模型接管候选评分，失败自动回退规则；影子模式只算分不行动，用于对比。": "Rule mode: NPCs use pure Python rule scoring (deterministic and reproducible). Local model: a trained local policy model ranks candidates and falls back to rules on failure. Shadow mode scores with the model but still acts by rules, for comparison.",
	"场上角色": "Characters",
	"公开记录": "Public records",
	"我的记录": "My records",
	"角色复盘": "Character review",
	"对局时间线": "Timeline",
	"解释复盘（赛后）": "Explanation review",
	"游戏 ": "Game ",
	"LLM：规则模板": "LLM: rule template",
	"LLM：已启用 · 校验开启（最多5轮）": "LLM: enabled · validation on (up to 5 rounds)",
	"LLM：已启用 · 原文直出（0次校验）": "LLM: enabled · raw output (0 validation passes)",
	"最近查验：": "Last check: ",
	"狼队友：": "Wolf teammates: ",
	"号 ": "# ",
	"夜晚": "Night",
	"白天会议": "Day meeting",
	"放逐投票": "Exile vote",
	"自由活动阶段": "Free activity",
	"警长竞选": "Sheriff election",
	"🌙 夜晚：按你的身份选择行动目标，然后点“结算夜晚”。": "🌙 Night: pick your action target by identity, then press “Resolve Night”.",
	"🔫 猎人触发：选择开枪目标或选择不开枪。": "🔫 Hunter trigger: pick a target or decline to shoot.",
	"🚨 警上报名：决定是否上警竞选警长。": "🚨 Campaign signup: decide whether to run for sheriff.",
	"🚨 竞选发言：轮到你在面板填写警上发言。": "🚨 Campaign speech: when it's your turn, write your speech in the panel.",
	"🚨 退水阶段：点“继续竞选”或“退水”。": "🚨 Withdrawal: press “Continue campaign” or “Withdraw”.",
	"🗳 警长投票：警下玩家为候选人投票。": "🗳 Sheriff vote: players off the podium vote for candidates.",
	"⚖️ 平票 PK：候选人再次发言并重新投票。": "⚖️ Runoff: tied candidates speak again and are re-voted.",
	"🗣 警长选择发言方向（出局左/右或警左/右）。": "🗣 The sheriff picks the speech direction (left/right of the out or sheriff).",
	"☀️ 白天会议：轮到你时在面板发言，NPC 轮到走近按 E。": "☀️ Day meeting: speak in the panel on your turn; walk to an NPC and press E on theirs.",
	"🗣 警长确认暂时/最终归票。": "🗣 The sheriff confirms the temporary/final nomination.",
	"🚶 自由活动：走近 NPC 按 E 私聊追问，结束点“结束自由活动”。": "🚶 Free activity: walk to an NPC and press E to chat; press “End free activity” when done.",
	"🗳 放逐投票：选择目标并写下理由后一次提交。": "🗳 Exile vote: pick a target, write your reason, and submit once.",
	"🎖 警长出局：移交或撕毁警徽。": "🎖 Sheriff out: transfer or tear up the badge.",
	"🏁 游戏结束：查看复盘与高光。": "🏁 Game over: check the review and highlights.",
	"我是C罗。开始游戏后，会议轮到我时再来听我的判断。": "I'm Ronaldo. Start the game, and come hear my take when the meeting reaches me.",
	"我是周深。我会留意每个人说话时细微的变化。": "I'm Zhou Shen. I notice the small shifts in how people talk.",
	"我是喜羊羊。我喜欢把分散的信息整理成可以验证的方案。": "I'm Pleasant Goat. I like turning scattered clues into plans you can verify.",
	"我是坏坏，点心屋的小恐龙。别怕，我的小尖牙只咬饼干；开心的、别扭的事都可以告诉我。": "I'm Huaihuai, the little dino at the dessert house. Don't worry, my tiny teeth only bite cookies; tell me what's on your mind.",
	"我是塞尔达。我更相信行动和经得住验证的信息。": "I'm Zelda. I trust actions and information that can stand verification.",
	"我是大黄蜂。我会用连续的问题检验你的判断。": "I'm Hornet. I test your judgment with a chain of questions.",
	"我是奇异博士。我会同时保留多种可能，直到证据排除它们。": "I'm Doctor Strange. I keep every possibility alive until the evidence rules it out.",
	"我是小骑士。我更相信行动和投票，而不是空泛的争论。": "I'm Little Knight. I trust actions and votes over empty arguing.",
	"我是懒羊羊。我不爱争论，但我会记住谁的态度突然变了。": "I'm Lazy Goat. I hate arguing, but I remember who suddenly changes their tune.",
	"我是梅长苏。发言顺序本身，也可能是一条线索。": "I'm Mei Changsu. Even the speaking order itself can be a clue.",
	"我是洛洛。我会从行动顺序和投票结构中寻找规律。": "I'm Luoluo. I look for patterns in action order and voting structure.",
	"我是然然，心情邮局的熊猫邮差。想寄存一个故事，或者整理一个小计划，都可以来找我。": "I'm Ranran, the panda mail carrier at the mood post office. Come drop off a story, or plan something small.",
	"我是梅西。没有进行狼人杀时，我们也可以聊聊小镇。": "I'm Messi. When we're not playing Werewolf, we can just chat about the town.",
	"记忆次数：第 ": "Memory: ",
	" 次对话": " conversation(s)",
	"关系阶段：": "Relationship: ",
	"未命中知识": "No knowledge hit",
	"未命中可公开的检索来源": "No public retrieval source matched",
	"本次未命中额外公开证据": "No additional public evidence matched",
	"检索模式：": "Retrieval: ",
	"文本生成：": "Generated by: ",
	"回退原因：": "Fallback reason: ",
	"命中知识：": "Hit: ",
	"公开依据：": "Public basis: ",
	"LLM（": "LLM (",
	"规则模板": "rule template",
	"全局 LLM 未启用": "Global LLM disabled",
	"Mock 模式使用规则回复": "Mock mode uses rule replies",
	"本局未启用 LLM": "LLM disabled for this game",
	"LLM 配置不完整": "LLM configuration incomplete",
	"LLM 服务暂时不可用，重试后仍失败": "LLM service temporarily unavailable; retries still failed",
	"LLM 返回格式异常，重试后仍失败": "LLM returned malformed output; retries still failed",
	"LLM 五次回答均未通过规则校验": "LLM failed rule validation 5 times",
	"向量 + 关键词": "Vector + keyword",
	"关键词降级": "Keyword fallback",
	"怀疑": "Suspicious",
	"身份声明": "Claiming",
	"中性": "Neutral",
	"后端状态：": "Backend: ",
	"NPC 发言：": "NPC speeches:",
	"NPC 发言：暂无可显示的发言。": "NPC speeches: none to show.",
	"NPC 发言：后端已返回，但格式暂时无法显示。": "NPC speeches: the backend returned data that can't be displayed yet.",
	"NPC 投票：暂无可显示的投票。": "NPC votes: none to show.",
	"NPC 投票：后端已返回，但格式暂时无法显示。": "NPC votes: the backend returned data that can't be displayed yet.",
	"依据：": "Basis: ",
	"玩家发言已记录。": "Player speech recorded.",
	"游戏已开始。": "The game has started.",
	"角色数据格式不正确。": "Character data format is invalid.",
}


func _init() -> void:
	for source in ENGLISH:
		ENGLISH_REVERSE[ENGLISH[source]] = source
	for translated in ENGLISH_REVERSE_OVERRIDES:
		ENGLISH_REVERSE[translated] = ENGLISH_REVERSE_OVERRIDES[translated]


func set_language(language_code: String) -> void:
	var normalized := language_code.strip_edges().to_lower()
	if not SUPPORTED_LANGUAGES.has(normalized):
		normalized = DEFAULT_LANGUAGE
	if language == normalized:
		return
	language = normalized
	language_changed.emit(language)


func english_of(source: String) -> String:
	if source.is_empty():
		return source
	var translated: String = ENGLISH.get(source, "")
	if not translated.is_empty():
		return translated
	if source.begins_with("后端状态："):
		return "Backend: " + source.trim_prefix("后端状态：")
	if source.begins_with("记忆次数：第 ") and source.ends_with(" 次对话"):
		return "Memory: " + source.trim_prefix("记忆次数：第 ").trim_suffix(" 次对话") + " conversation(s)"
	return source


func t(source: String) -> String:
	if source.is_empty():
		return source
	if language == "zh":
		if source.begins_with("Backend: "):
			return "后端状态：" + source.trim_prefix("Backend: ")
		var chinese: String = ENGLISH_REVERSE.get(source, "")
		if not chinese.is_empty():
			return chinese
		return source
	return english_of(source)


## Recover the canonical Chinese source for a control whose text may already
## hold the English translation (e.g. after a code path re-assigns it while
## the UI language is English).  Non-English input is returned unchanged.
func reverse_t(source: String) -> String:
	if source.is_empty():
		return source
	if source.begins_with("Backend: "):
		return "后端状态：" + source.trim_prefix("Backend: ")
	var chinese: String = ENGLISH_REVERSE.get(source, "")
	return chinese if not chinese.is_empty() else source
