# Agent Town 常用命令

所有命令默认从项目根目录执行。请把 `<project-root>` 替换为本机克隆目录：

```bash
cd "<project-root>"
```

## 首次安装后端依赖

已经存在 `backend/.venv` 时不需要重复创建虚拟环境，只需安装或更新依赖：

```bash
backend/.venv/bin/pip install -r backend/requirements.txt
```

如果 `backend/.venv` 不存在：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

## 验收 V4.8-A 开局 LLM 输出校验开关

V4.8-A 只在创建狼人杀对局时读取 `enable_llm_validation`。字段省略或设为 `true`
表示默认最多 5 轮语义校验与纠错；设为 `false` 时，Python 先选定合法计划，再请求
1 份最终模型文本，语义校验与纠错均为 0 次并直接显示。原文可能错误、矛盾、越界或
虚构信息，但不会被解析成权威声明、怀疑值、技能建议或规则动作；身份、行动、投票、
警徽、出局和胜负仍由 Python 结算。网络、配置或响应解析失败仍回退规则文本。原文直出
固定只请求 1 次，坏坏、然然的居民 `/chat` 不读取这个局内选项。

以下命令只供你已经手动启动 FastAPI 后做 API 验收；本文档不会自动启动后端或 Godot。
创建默认输出校验局：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "输出校验测试",
    "npc_count": 11,
    "player_role": "random",
    "enable_llm": true,
    "enable_llm_validation": true,
    "enable_rag": true
  }'
```

创建关闭输出校验的原文直出局：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "原文直出测试",
    "npc_count": 11,
    "player_role": "random",
    "enable_llm": true,
    "enable_llm_validation": false,
    "enable_rag": true
  }'
```

保存返回的 `game_id`，再读取完整状态：

```bash
curl -sS \
  http://127.0.0.1:8000/api/game/替换为当前游戏编号/state
```

开局响应和状态响应都应包含 `llm_validation_enabled`。只有后端实际启用且已配置 LLM
时它才会随请求显示为 `true`；LLM 总开关关闭或 provider 未配置时应为 `false`。
手工启动 Godot 后，还应验证以下四种组合：

| AI NPC 表达 | 输出校验选择 | 预期 |
| --- | --- | --- |
| 关 | 任意 | 规则模板；校验选项不生效 |
| 开 | 开 | 语义校验与纠错最多 5 轮，失败后规则回退 |
| 开 | 关 | 生成 1 份、校验 0 次并直出原文；Python 规则结算不解析原文 |
| 开但 provider 未配置 | 任意 | 规则模板，`llm_validation_enabled=false` |

同一局开始后不能热切换。开局选择封印在首个
`game_created.command.start_request.enable_llm_validation` 中；旧事件
缺少 `enable_llm_validation` 时默认按开启读取。实现没有向 `WolfGameState` 新增字段，
所以旧存档无需手工补字段或改摘要。实际使用 LLM 的局即使关闭输出校验仍不能执行
确定性重放。开启校验时若候选被拒绝，可按本文后面的“查看 LLM 校验失败日志”检查，
最多记录 5 次；关闭校验时不创建 validation failure，原文直接显示。

## 验收 V4.7-C CI 与源码交付

V4.7-C 已完成交付机制，但项目尚未封版。CI 固定 Python 3.12 和 Godot 4.7.1，在
Ubuntu 24.04 与 macOS 15 分别执行两个 profile。当前本地可运行 CI 的核心等价命令：

```bash
ENABLE_LLM=false LLM_PROVIDER=mock AGENT_TOWN_DISABLE_VECTOR_RAG=1 HF_HUB_OFFLINE=1 \
  backend/.venv/bin/python scripts/smoke_check.py --profile core
```

该命令不启动 FastAPI 或 Godot，也不请求真实 LLM、下载向量模型或读取 secret。CI
从空环境安装 `backend/requirements.txt` 并额外执行 `python -m pip check`；依赖安装本身
仍需要网络。只执行静态 Godot UI 与短暂 headless 资源检查：

```bash
GODOT_BIN=/Applications/Godot.app/Contents/MacOS/Godot \
  backend/.venv/bin/python scripts/smoke_check.py --profile godot
```

Linux 或 PATH 已包含 `godot` 时可省略 `GODOT_BIN`。无参数命令仍是兼容的完整 smoke。
GitHub workflow 只读源码、actions 固定完整 commit SHA，测试存档使用 runner 临时目录；
不会启动 Godot 编辑器或常驻游戏进程。

GitHub 的 `runner.temp` 上下文在 job 创建前不可用，因此临时存档与 pycache 变量必须
位于各 smoke step 的 `env`，不能上移到 job 级；core smoke 会静态锁住这个边界。

源码交付、双平台矩阵、三尺寸手工验收、隐私、依赖记录、LICENSE 决策和未来封版命令
见 [`docs/V4_RELEASE_CHECKLIST.md`](docs/V4_RELEASE_CHECKLIST.md)。公开开发仓库
[`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0) 已创建，
本地专用 remote 是 `v4-origin`；开发快照只能用完整 refspec
`git push v4-origin refs/heads/v4-development:refs/heads/main` 推送到该 remote。
当前尚未创建 `v4.0.0`，禁止向 `origin`、`v2-origin`、`v3-origin` 推送，也禁止
`git push --all`、`git push --tags`、mirror 或 force push。只有用户以后明确批准正式
封版时，才执行清单中的 tag 步骤；项目当前没有根级 `LICENSE`，明确为未授予再分发
许可。

## 验收 V4.7-B 响应式与整局键盘导航

V4.7-B 是 Godot 客户端改动，不需要新增后端配置、HTTP 请求或 LLM 调用。布局契约
`agent_town_responsive_layout.v1` 使用物理窗口尺寸选择 `compact / default / wide`，焦点
契约 `agent_town_focus_navigation.v1` 负责世界、普通面板、文本输入和模态窗口之间的
键盘焦点与移动隔离：

| 手工窗口尺寸 | profile | 当前行动 / 情报宽度 | 角色卡列数 |
| --- | --- | --- | --- |
| `1100×650` | `compact` | `420 / 520` | 2 |
| `1280×720` | `default` | `440 / 600` | 3 |
| `1600×900` | `wide` | `480 / 736` | 4 |

请由开发者手动启动 FastAPI 和 Godot，再分别把游戏窗口调整为以上三种尺寸。本文档和
自动化命令都不会自动启动 FastAPI 或 Godot 常驻服务。每种尺寸依次确认：

1. 阶段 HUD、左侧身份卡、右侧当前行动、情报抽屉、开局设置、复盘和 NPC 对话框均
   留在可见范围内；当前行动与情报抽屉不会互相覆盖，长内容可以滚动。
2. `Tab` / `Shift+Tab` 在当前可见范围内正向/反向循环焦点；方向键可以继续导航按钮，
   下拉选项保留自身选择行为；`Enter` / `Space` 激活当前控件。
3. `Esc` 优先关闭最上层引导、设置、发言预览、复盘或 NPC 对话；没有模态窗口时，
   关闭情报抽屉或把普通面板焦点交还世界。
4. 普通按钮获得焦点时，按 `WASD` 会把焦点交还世界并恢复角色移动；编辑发言、理由、
   玩家名或 NPC 消息时，`WASD` 仍输入文字，不会移动角色。鼠标点击世界也会交还焦点。
5. 焦点边框在浅色和深色面板上都清楚可见；只读行动记录、公开记录、引导正文和复盘
   内容可以用键盘进入并滚动，正文最小字号保持可读。

整局至少覆盖以下入口，不要只检查首页按钮：

- 开局设置：玩家名、测试身份、LLM 表达开关、LLM 输出校验开关、开始和关闭。
- 夜间技能：狼人刀口、预言家查验、女巫用药、守卫守护和猎人窗口中实际可见的控件。
- 警长流程：报名、退水、发言、投票、归票和警徽流中当前阶段允许的控件。
- 发言预览：返回修改、确认提交和 `Esc` 回到原输入框。
- 放逐投票：目标、理由和统一提交。
- 情报：三个分页、角色卡、公开记录、我的只读记录和关闭按钮。
- 赛后复盘：三个分页、滚动正文和关闭后焦点回还。
- NPC 对话：输入、发送、记忆/配置按钮、长回复滚动和关闭后焦点回还。

V4.7-B 的静态契约包含在文末完整 smoke 中；响应式是否无重叠及焦点是否符合实际操作
仍按上述三个尺寸手工验收。V4.7-C 已在其后补齐 CI、封版清单和跨平台源码交付。

若运行后出现“只有 WASD 能动，鼠标按钮和靠近 NPC 按 E 都无效”，先关闭并重新运行
Godot 项目，再看运行输出中是否存在 `Failed to load script` 或 `Parse Error`。这个组合
症状表示 `player.gd` 已加载、`main.gd` 没有加载，并不等于鼠标或 `interact` 映射坏了。
本次修复已为三处 Godot 4.7 类型推断补上显式类型；重开后至少确认：顶部按钮可点击、
开局设置可操作、靠近 NPC 按 E 会打开对话、关闭对话后按钮和移动都能恢复。

## 使用 V4.7-A 首局分阶段引导

`agent_town_onboarding.v1` 不需要单独启动或配置。手动启动后端和 Godot、创建一局后，
客户端会等完整 `GET /api/game/{game_id}/state` 返回，再按实际阶段显示以下七步；开局
POST 的精简响应不会触发引导：

```text
identity_and_scope → night_skill → sheriff_flow → public_speech
→ private_chat → exile_vote → post_game_review
```

步骤只在条件满足时出现，并通过本局 seen 集合避免状态刷新重复弹出。顶部 `?` 或 F1
可随时手动查看；弹窗内使用 Tab / Shift+Tab 循环按钮、Enter / Space 确认、方向键
翻页、Esc 暂时关闭。“跳过全部”只关闭后续自动提示，F1 仍可重开。

Godot 的 `user://agent_town_onboarding.cfg` 只保存
`schema_version=agent_town_onboarding.v1` 和 `automatic_guide_completed` 布尔值；不会保存 game id、
身份、队友、验人、刀口、药品、守护目标、聊天或其他对局事实。身份信息标记为
“仅你可见”，claim/承诺标记为“全场公开但未验真”，私聊原文不会自动公开但会影响
该 NPC 后续判断。此功能不发送额外 HTTP 请求，也不调用 LLM。

V4.7-A 的契约验收包含在文末静态 Godot UI 检查中；实现与验证不会自动启动 FastAPI
或 Godot 常驻服务。完整 smoke 的末段仍会短暂运行 Godot headless 资源检查，应由
开发者手动执行。V4.7-B 已补齐整体响应式和整局键盘导航，V4.7-C 已补齐 CI、
封版清单和跨平台源码交付。

## 启用 DeepSeek LLM

DeepSeek 是云端 API，不需要在本机单独启动 LLM 进程。确认 `backend/.env` 包含以下配置，并把 Key 只保存在这个文件中：

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的_DEEPSEEK_API_KEY
LLM_MODEL=deepseek-v4-flash
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=0.35
```

修改 `.env` 后需要重启后端。

## 测试 LLM 连接

下面的命令不启动 FastAPI，但会发送一次很小的真实 DeepSeek 请求：

```bash
backend/.venv/bin/python scripts/check_llm_connection.py
```

成功时会看到：

```text
[OK] deepseek returned: ...
```

## 预览 V4.1-B 玩家发言

服务由开发者手动启动后，可对当前轮到玩家的白天或警上发言做只读预览：

```bash
curl -s http://127.0.0.1:8000/api/player-speech/preview \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "替换为当前游戏编号",
    "character_id": 1,
    "speech_kind": "day",
    "speech": "我怀疑3号，今天准备投3号。",
    "temporary_nomination_target_id": null
  }'
```

警上发言把 `speech_kind` 改为 `sheriff`；需要发布警徽流时，在同一请求加入
现有 `badge_flow` 对象。返回根级为 `player_speech_preview.v1`，其中：

- `accepted / errors`：是否可提交及拒绝原因。
- `canonical_speech`：Python 最终会保存的规范文本。
- `understanding`：`player_speech_understanding.v1` 的声明、验人、怀疑/支持、
  投票意向和女巫建议。
- `public_facts_to_write`：会写入的公开声明、暂归票和警徽流。
- `strategic_signals_to_apply`：会影响规则内理解的结构化信号。
- `text_only_notes`：只保留为公开文本、不会自动成为规则事实的范围。
- `preview_fingerprint`：接受时为 64 位 SHA-256；拒绝时为空。

最终调用 `/api/day/player-speech` 或 `/api/sheriff/player-speech` 时可把该值放入
`preview_fingerprint`。后端会在锁内重新解析；草稿或局面改变会返回 HTTP 409，
且不会留下声明、发言、怀疑值、警徽流、暂归票或阶段进度。Godot 控制面板会
自动执行预览，并显示“确认提交 / 返回修改”。

## 查看 V4.4-A 与 V4.4-B 公开证据与关系分析

后端由开发者手动启动且已经有一局游戏时，读取普通状态接口：

```bash
curl -s \
  http://127.0.0.1:8000/api/game/替换为当前游戏编号/state
```

返回的 `public_evidence_timeline` 根级 schema 是
`public_evidence_timeline.v1`，每项为 `public_evidence_item.v1`：

- `evidence_id / sequence`：公开结构生成的稳定 ID 与当前时间线顺序。
- `projected_event_sequence`：整份投影对应的最后规则事件序号；不是逐项来源声明。
- `category=claim`、`verification=unverified`：身份、验人、女巫或守卫公开说法。
- `category=commitment`、`verification=unverified`：警徽流等公开承诺。
- `category=confirmed_action`、`verification=confirmed`：已经发生并公开的警长、
  归票、票型、警徽、猎人或出局动作；只确认发生，不确认相关身份说法为真。

未公开结算的放逐票不会出现。夜间出局只显示 `night_out`，不会返回狼刀/毒药原因、
责任人、隐藏 `role/camp` 或声明内部 `source`。

同一状态响应的 `public_evidence_analysis` 根级 schema 为
`public_evidence_analysis.v1`，并固定
`truth_scope=public_only_no_post_game_truth`：

- `commitments` 每项为 `public_commitment_state.v1`，用 `commitment_id` 和
  `source_evidence_id` 关联一个警徽流版本；`status` 可为 `active / superseded /
  fulfilled / invalidated / undetermined / contradicted`。
- `contradiction_candidates` 每项为 `public_contradiction_candidate.v1`，只可能是
  `identity_claim_changed / seer_result_changed / badge_flow_target_mismatch /
  badge_flow_action_mismatch`，并保留 `earlier_evidence_id` 与
  `later_evidence_id`。
- 所有候选固定 `review_status=needs_review`、`judgment=none`。`fulfilled` 只表示
  公开后续与承诺相符，`contradicted` 只表示公开记录表面不同；两者都不验真、
  不判狼，也不读取赛后身份。
- 到期前的警徽流修订、公开目标/分支不可用、缺少公开后续，以及暂时归票改为最终
  归票，不会被自动当作矛盾候选。

Godot 的关键信息与公开记录面板、NPC 合法公开知识使用同一批 evidence、commitment
和 candidate ID；公开记录页会显示生命周期与“需核对，不代表阵营判断”的提示。
旧后端响应仍回退到 V4.4-A 时间线或 `public_intel/public_logs`。

## 查看 V4.5-A 可解释赛后复盘

该接口只在 Python 已把对局推进到 `GAME_OVER` 并确定 winner 后开放：

```bash
curl -s \
  http://127.0.0.1:8000/api/game/替换为当前游戏编号/summary
```

原有角色和时间线字段旁会出现 `explainable_review`，根级 schema 为
`post_game_explainable_review.v1`；每条 `items` 为
`post_game_decision_review.v1`，跨日公开证据引用为
`post_game_evidence_reference.v1`。

- `truth_scope=post_game_truth_unlocked` 与条目
  `post_game_truth_unlocked=true` 表示身份/阵营只在赛后解锁。
- `knowledge_scope=recorded_basis_plus_prior_day_public_evidence` 表示“当时知道什么”
  只来自随决定保存的结构化依据和更早日期的公开证据。同日旧集合没有精确事件
  顺序时不会被冒充为先验或后续因果。
- `decision_kind` 覆盖 `public_speech / exile_vote / night_action /
  hunter_shot`；`recorded_basis` 保存当时实际留下的 RAG、signal、立场、连续性、
  投票理由或技能策略摘要。
- 错误分类为 `deceived / insufficient_evidence / continuity_break /
  skill_misuse / deterministic_variance`；狼人阵营策略、中性行动和无法评分的旧记录
  不会被硬塞进好人判断错误。
- `assessment_counts / error_category_counts` 保留完整词表和原始计数；条目还提供稳定
  `review_id`、赛后 `truth_summary` 和保守 `explanation`。

进行中的对局调用会返回 HTTP 400；请使用普通 `/state` 查看公开记录。Godot 在
终局复盘的第三个“解释复盘（赛后）”页读取同一字段，并首先显示真值解锁警告。

## 运行 V4.6-A NPC 表达质量诊断

表达质量基线属于无 HTTP 终局 simulation；它不需要启动后端或 Godot，也不会请求
LLM/RAG。推荐关闭不相关的大体积 shadow trace：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 100 \
  --no-belief-trace \
  --no-stance-trace \
  --no-vote-calibration-trace \
  --output /tmp/agent-town-v4-speech-quality.json
```

单局结果中的 `npc_speech_quality` 为 `npc_speech_quality.v1`；批量根级
`npc_speech_quality_summary` 为 `npc_speech_quality_batch.v1`。嵌套契约还包括
`npc_speech_normalization.v1`、`npc_speech_quality_observation.v1`、
`npc_speech_actor_quality.v1` 和 `npc_speech_actor_quality_batch.v1`。

- 根级固定 `scope=npc_public_speeches_only`、
  `truth_scope=public_only_no_role_truth`；只统计终局 NPC 公开发言和保存的公开结构化
  依据，不读取真实身份或阵营，observation 也不保存原始台词。
- `surface_repeat` 是规范化后逐字重复；`template_repeat` 会再去掉姓名、座位和数字；
  近重复使用字符 trigram Jaccard，固定 `near_duplicate_threshold=0.82`。
- `information_increment_rate` 的分母是全部结构化公开信息原子；
  `zero_information_increment_rate` 的分母是 NPC 发言数。`evidence_citation_rate` 与
  人设 marker/跨角色表面差异分独立报告。信息原子只来自随 speech 保存的结构，
  不会把终局按天聚合、缺少逐发言 provenance 的 `public_claims` 回填到历史发言。
- 批量先累加原始计数、pair 分母和相似度 sum，再计算加权比率；无分母时返回
  `null`，不是 0。关闭 belief/stance/vote-calibration trace 不会关闭质量报告。

普通单策略模式写完 JSON 后会显示：

```text
[SPEECH-QUALITY] speeches=...; template_repeat=...; cross_actor_near_duplicate=...; information_increment=...; evidence_citation=...; persona_differentiation=...
```

这只是诊断摘要，不是自动失败门槛，也不会反向影响 NPC 发言、投票、技能或胜负。
benchmark 的嵌套单局仍含质量 JSON，但当前不额外打印这行。V4.6-B 已封印完整配置
和 active-only 指纹；跨时间比较应先核对指纹，或明确把两个结果作为不同 arm。

## 导出并重放 V4.2 规则事件

以下两个接口都只允许在游戏结束后调用。完整日志包含开局 seed、夜间命令和
私聊原文，不要在进行中展示或当作普通公开状态返回：

```bash
curl -s http://127.0.0.1:8000/api/game/替换为当前游戏编号/events
```

返回 `game_rule_event_log.v1`，其中每项为 `game_rule_event.v1`。
`chain_valid=true` 表示连续序号、上一事件摘要、事件自身摘要和相邻状态摘要全部
匹配；每项 `visibility` 为
`public / player_private / system_private` 之一。

规则模板局可执行隔离重放：

```bash
curl -s -X POST http://127.0.0.1:8000/api/game/替换为当前游戏编号/replay
```

`game_rule_replay.v1` 的 `verified=true` 表示从 `game_created` 开始逐命令通过
同一 Python 规则入口，并匹配 winner、警长票、放逐票、出局、警徽和终局状态
摘要。启用 LLM 或 RAG 的局仍有完整事件审计链，但当前返回 `supported=false`，
不会重新请求模型后声称确定性。重放还要求代码和 NPC 配置未改变；配置漂移会在
首事件摘要校验时失败。

## 保存、恢复与检查 V4.3-A/B 对局

真实 FastAPI 生命周期中的新局和后续成功规则命令已经自动保存。手动建立一个
显式检查点：

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/game/替换为当前游戏编号/save
```

默认目录是 `backend/data/games/`。从 `backend/` 启动时可在 `.env` 覆盖：

```dotenv
AGENT_TOWN_GAME_SAVE_DIR=data/games
```

重启同一代码和恢复配置的后端后，合法未完成局自动恢复。检查最近一次扫描：

```bash
curl -s \
  http://127.0.0.1:8000/api/game/recovery-status
```

`scanned_count / restored_count / skipped_terminal_count / failure_count` 分别表示扫描、
恢复、跳过终局归档和失败数量。任一进行中存档损坏或配置漂移会让服务启动
fail closed，不会部分恢复。不要手工编辑这些文件。

早期 V4.3-A 曾生成不含 `command_results` 的合法存档。当前恢复器只在原始快照
摘要正确、唯一 schema 差异是缺少默认空对象、且事件链从未出现
`idempotency_key` 时内存兼容；读取不会改文件，下次正常保存才升级。已有带 key
事件却缺台账、未知字段、其他默认差异或摘要不一致仍会拒绝启动，不能靠手工补字段
绕过校验。

手动恢复未进入活动缓存的合法存档，包括启动时跳过的终局归档：

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/game/替换为当前游戏编号/restore
```

存档包含隐藏身份、seed、夜间行动和私聊，不能公开或提交 Git。离线 simulation、
隔离 replay 和直接导入规则模块不会落盘。当前只允许一个 uvicorn worker，也不能
运行多个进程共用该目录。

V4.3-B 的 20 个开局后规则写接口可在 JSON body 传可选 `idempotency_key`。例如在
合法 `NIGHT` 阶段结算一次夜晚（请替换 game ID；这个命令会真实推进对局）：

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/night/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "替换为当前游戏编号",
    "idempotency_key": "manual-night-resolve-0001"
  }'
```

原命令已提交但响应丢失时，原样重跑上面的命令。同一 `game_id`、key、端点和
payload 会返回第一次的 `NightResolveResponse`，即使当前阶段已经不再是 `NIGHT`；
不会追加第二个事件或再次结算。用同一个 key 改 payload，或改到另一个端点，会在
业务校验前返回 HTTP 409。例如下面故意复用已提交 key，必须失败且零状态变化：

如果这条命令直接结束游戏，重启扫描仍会把终局存档列为 skipped；原 key 重试会
只读返回归档中的原响应，不会把终局重新加入活动缓存。

```bash
curl -sS -i -X POST \
  http://127.0.0.1:8000/api/night/action \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "替换为当前游戏编号",
    "character_id": 1,
    "action_type": "none",
    "idempotency_key": "manual-night-resolve-0001"
  }'
```

key 为每局作用域：8–160 位，首位是 ASCII 字母或数字，其余可用字母、数字、
`.`、`_`、`:`、`-`。结果使用 `game_command_result.v1` 与规则事件一起原子保存，
契约为 `game_command_idempotency.v1`。不传 key 的旧客户端仍可调用，但没有响应
丢失后的 exactly-once 效果保证。`game/start`、preview、GET、save/restore、replay
不在范围内，事件 `command_id` 也不能当作外部 key。

## 运行 V4 无 HTTP 批量对局

下面的命令直接调用 Python 规则引擎，固定关闭 LLM 和向量 RAG，不启动 FastAPI 或 Godot：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 100 \
  --output /tmp/agent-town-simulation.json
```

同一代码、配置、策略版本和 seed 会生成完全相同的逐局结果。可用 `--player-role seer` 等方式固定测试身份；完整选项使用：

```bash
backend/.venv/bin/python scripts/simulate_games.py --help
```

单局/批量当前 schema 为 `agent_town_simulation.v17` /
`agent_town_simulation_batch.v17`。每局都生成事件摘要、执行重放、生成 V4.6-A
表达质量报告，并封印 `experiment_fingerprint.v1`；批量 JSON 默认
不保存完整事件数组，以免 100/1008 局报告过大。需要完整数组时显式加入：

`gameplay_digest_projection_version` 固定为 `agent_town_simulation.v14`，所以同一
玩法结果可以继续和 V4.1-A/B 对照；包含事件与重放字段的整份 `result_digest` 会变化。

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 1 \
  --include-event-logs \
  --output /tmp/agent-town-v4-event-replay.json
```

写入文件后会额外打印：

```text
[EXPERIMENT] mode=rule_only_no_llm; configuration=...; effective=...; llm_requests=0
[REPLAY] verified=1/1; events=...; full_logs=yes
[SPEECH-QUALITY] speeches=...; template_repeat=...; cross_actor_near_duplicate=...; information_increment=...; evidence_citation=...; persona_differentiation=...
```

`configuration` 覆盖 rules/roles、profiles、tuning、schema、player policy，以及
Prompt、知识库、LLM 和 RAG 等完整配置；`effective` 只覆盖本次规则模板仿真实际
生效的前五类组件。两者都是 digest，不包含 API Key 或可反查的 Prompt 正文。

单策略默认使用 `standard / legal_public_baseline.v1`，保持 V3 自动玩家行为。
也可以显式选择三档 `player_strategy.v1`：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 20 \
  --player-role villager \
  --player-strategy expert \
  --no-belief-trace \
  --no-vote-calibration-trace \
  --output /tmp/agent-town-v4-expert-villager.json
```

三档策略只消费 `player_strategy_context.v1`：其他角色的真实 `role/camp`
不进入公开角色投影；狼人队友、本人验人、本人女巫刀口和技能资源只进入对应
合法私有区。

按相同 seed 和固定身份运行 `beginner / standard / expert` 配对基准：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 2 \
  --benchmark-player-strategies \
  --output /tmp/agent-town-v4-player-benchmark-smoke.json
```

配对模式中 `--games` 表示每种身份的 seed 数；上例为
`2 × 6 × 3 = 36` 局。正式 V4.1-A 最小基准：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 56 \
  --benchmark-player-strategies \
  --output /tmp/agent-town-v4-player-benchmark-1008.json
```

正式命令共 1008 局，默认关闭 belief、stance 和 vote-calibration 大体积明细。
输出根级为 `agent_town_player_benchmark.v1`，单局为
`agent_town_simulation.v17`，批量为 `agent_town_simulation_batch.v17`；
`initial_layout_digest` 必须在同一个 `seed + player_role` cohort 的三档之间一致。
`player_decision_trace.v1` 保存模拟玩家行动，纯赛后的
`player_performance.v1` 评价投票、技能和 NPC 跟随公开目标代理指标。

正式矩阵还固定回归 `hunter + seed 20260765 + beginner`：同一 NPC 狼同时收到
狼队友互踩查杀和另一名预言家查杀时，规则发言必须在保留互踩主叙事的同时，
通过次目标和公开信号回应两项声明，并合法走到终局。

V4.1-A 的 v14 封存报告对 `20260719–20260774` 的正式输出为：

```text
[OK] benchmarked 1008 games across 336 paired cohort(s); player_wins={'beginner': 88, 'standard': 106, 'expert': 107}
[PAIRED] standard_minus_beginner=5.4%; a_only=32; b_only=50; same_win=56; same_loss=198
[PAIRED] expert_minus_beginner=5.7%; a_only=35; b_only=54; same_win=53; same_loss=194
[PAIRED] expert_minus_standard=0.3%; a_only=20; b_only=21; same_win=86; same_loss=209
```

该 v14 报告摘要为
`577e0860e3129cf66f3006f0bda025dbd88594813e64b23310b185938a9bdb13`。V4.2
增加 v15 事件和重放字段后，重新生成的整份 JSON 摘要会变化，不能拿新摘要与这条
历史报告摘要直接比较；玩法回归使用 `gameplay_digest`、配对计数和胜负原始计数。

轻量样本写入文件时会显示同形摘要：

```text
[OK] benchmarked 36 games across 12 paired cohort(s); player_wins={...}; output=...
[REPLAY] verified=36/36; events=...; full_logs=no
[PAIRED] standard_minus_beginner=...; a_only=...; b_only=...; same_win=...; same_loss=...
[PAIRED] expert_minus_beginner=...; a_only=...; b_only=...; same_win=...; same_loss=...
[PAIRED] expert_minus_standard=...; a_only=...; b_only=...; same_win=...; same_loss=...
```

## 比较 V4.6-B 两组规则仿真 artifact

比较器不会替你切换代码、配置或运行游戏。应先在两个待比较的代码/配置快照中，
用相同 seed、局数、固定玩家身份、策略和 trace 开关分别生成 v17 batch。例如先在
arm A 快照运行：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 20 \
  --player-role villager \
  --player-strategy standard \
  --no-belief-trace \
  --no-stance-trace \
  --no-vote-calibration-trace \
  --output /tmp/agent-town-arm-a-villager.json
```

再在 arm B 快照原样运行，只改变输出文件名：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 20 \
  --player-role villager \
  --player-strategy standard \
  --no-belief-trace \
  --no-stance-trace \
  --no-vote-calibration-trace \
  --output /tmp/agent-town-arm-b-villager.json
```

两个 arm 必须具有不同的完整和 active-only fingerprint；如果只改了在规则模板模式
中 inactive 的 Prompt/LLM 配置，比较器会拒绝把它当成规则效果实验。随后只读比较：

```bash
backend/.venv/bin/python scripts/compare_simulation_artifacts.py \
  --arm-a /tmp/agent-town-arm-a-villager.json \
  --arm-b /tmp/agent-town-arm-b-villager.json \
  --label-a baseline \
  --label-b candidate \
  --output /tmp/agent-town-artifact-ab.json
```

覆盖多个固定身份时，分别生成对应 artifact，再重复传入 `--arm-a` 和 `--arm-b`；
不能使用 `--player-role random`。成功时会打印一条 `[ARTIFACT-A/B]` 和五条
`[QUALITY-A/B]`。输出根级为 `agent_town_artifact_ab.v1`，严格校验每个文件和内嵌
单局 digest、相同 cohort、布局、策略、规则、schema 与 trace 完整性；任一缺失或
重复样本都会失败，不会静默丢弃。五项质量率都由两侧 raw numerator/denominator
先聚合后计算，并保留 B-A delta。

该报告固定 `comparison_mode=rule_only_artifacts_no_llm`、`llm_evaluated=false`、
`prompt_effect_evaluated=false`。它只比较已封印的
规则模板 artifact，不调用 LLM；即使完整配置中的 Prompt digest 不同，也不能据此
声称 Prompt 或模型效果。

写入文件时，终端会同时显示核心 M02 指标，例如：

```text
[METRICS] good_win_rate=6.0%; exile_entropy=22.6%; good_misvote_rate=61.0%; fake_seer_sheriff_support=48.3%; fake_black_check_follow=41.6%
[BALANCE] winner_reasons={...}; first_exile_camps={...}
[WITCH] first_night_save=...; second_night_poison=...; accepted_hold=...; poison_wolf_hit=...
[SEER] fake_campaign=...; fake_elected=...; fake_black_checked_true=...; true_first_exiled=...
[EXILE-CHAIN] first_wolf_exile=...; next_exile_wolf=...; npc_correct_retention=...; after_first_wolf_retention=...
```

完整 JSON 的根级 `metrics` 使用 `agent_town_metrics.v5`，除原有阵营胜率、局长、票熵、好人误票和假预言家采信外，`balance_diagnostics` 还包含终局原因、首放阵营/身份、按出局原因/阵营计数，以及女巫救人、用毒、压毒、建议采信和毒药命中；`seer_claim_balance` 记录真假预言家链路；`cross_day_exile_chain.v1` 记录首放狼人条件胜负、下一次放逐阵营和非玩家好人 NPC 的四类跨轮选票转移；`player_performance.v1` 只在赛后评价模拟玩家。无适用样本的比率是 `null`，不是 0。

V3.1-L 的 NPC 女巫第一夜本人被刀必定自救，其他合法刀口确定性 99% 使用解药；第二夜有毒且存活时默认毒本人最怀疑的合法目标。玩家或 NPC 在公开正式发言（警上或白天会议）中可明确建议女巫毒单一目标，或以公开信息不足为理由建议压毒；Python 保存 `witch_directive.v1`，女巫按自己的合法怀疑、信任和公开信息独立决定是否采信。含糊多目标、过去用药声明和无理由压毒不会被自动当成可靠指令。

V3.1-O 当前使用 `fake_seer_campaign.v2` 决定最强 NPC 狼是否参加警长悍跳，确定性参选区间为 `28%–62%`；用于同 seed 配对比较的随机流保持冻结。`fake_seer_check_mix.v1` 在合法的队友金水、非狼查杀、非狼金水以及既有高压队友查杀之间混合。狼人只知道谁是狼队友，不读取非狼的预言家/女巫等精确身份；同一 seed 可重放，好人精确身份互换不得改变策略结果。

V3.1-N 的 `cross_day_exile_chain.v1` 是纯赛后 shadow。它可以在 `GAME_OVER` 后用真实阵营评价“投狼后是否继续投狼”和“误投后是否纠正”，但被放逐者的隐藏身份不会因此进入实时 NPC belief、投票器、LLM 或公开 API。下一阶段不得直接消费该真值标签，只能使用当时已经公开的票型、声明、本人 stance 与合法新证据。

V3.1-O 的 `good_exile_cross_day.v1` 只让 `VOTE` 阶段非警长好人 NPC 实时消费公开票型：上一轮放逐得票不超过 `75%` 时，统一审查存活反对票中投向最集中的公开小团体；超过 `75%` 不触发。NPC 女巫第二夜起也把同一焦点纳入“最怀疑目标”，但理由合理的结构化压毒/毒人建议仍可覆盖。焦点不读取被放逐者或候选者身份；smoke 会交换隐藏角色/阵营并要求好人概率与女巫选择不变。

## V3.2-B / M13-A 精炼 NPC 发言

公开自然文案不再显示“警徽流 v1 / v2”，只显示“X 号的警徽流”或“我的警徽流”；结构化版本仍保留在后端历史和审计 ID 中。普通白天发言会紧凑表达公开依据、当前目标、追问、暂票与改票条件，公开 LLM 改写硬限制为 `120` 字，较长的规则正文不再叠加口头禅。

20 个固定 seed 的规则样本共 555 条 NPC 发言：平均 `158.2 → 93.4` 字，P95 `225 → 128` 字，最大 `293 → 196` 字。同口径 100 seeds 为好人 `37`、狼人 `63`，平均 `3.45` 天。完整 smoke 会检查自然文案无版本号、结构化版本仍存在、长 LLM 候选被拒绝，以及紧凑正文仍保留目标、依据、追问、暂票和改票条件。该检查不启动 FastAPI 或 Godot 服务：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

分层入口保持同一套检查定义，不复制测试逻辑：

```bash
# Python、规则、存档、文档和静态 UI；不调用 Godot
backend/.venv/bin/python scripts/smoke_check.py --profile core

# 静态 UI + Godot 4.7 stable 的短暂 headless 加载
backend/.venv/bin/python scripts/smoke_check.py --profile godot
```

## V3.2-A / M16-A 智能警徽流

警上竞选或 PK 中首次跳预言家必须随同一发言提交警徽流；警下和普通白天发言可以首次发布或修改，但不强制每次重复。Godot 当前行动区默认折叠该模块，检测到警上预言家声明时会自动展开并锁定必填。

后端的结构化输入使用下一夜 `primary_target_id`、可选下一顺验 `secondary_target_id` 和可选公开金水锚点 `claimed_good_anchor_id`。金水分支固定把警徽交给 `primary_target_id`；查杀分支只允许交给该声明者仍存活的公开金水，未指定时自动选择最近公开金水，没有则撕徽。不要把 `secondary_target_id` 当作查杀分支接徽人。

固定 `20260719–20260818` 的 100 局 v13 轻量复验仍为好人 `38`、狼人 `62`，平均 `3.44` 天。

完整自检会验证警上缺失警徽流的原子拒绝、同次首夜金水自动成为查杀分支锚点、NPC 起跳必带流、公开金水合法集合、两条移徽分支、隐藏角色不变性以及 Godot 折叠控件。命令不启动 FastAPI，但末尾会以 Godot CLI 做资源解析，因此仍由开发者手动运行：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

默认报告还包含 `belief_state.v2` 影子信念轨迹：证据台账、每次分数变化和 11 名 NPC 的最后信念。公开软证据逐日乘以 `0.75`，公开票型/警徽动作和合法私有知识不衰减；有效私聊只按已保存的结构化目标与方向进入对应 NPC 的私有视角，不解析自由文本。100 局文件可能达到数十 MB，其中包含所有 NPC 依法拥有的赛后私有视角，不要把它直接返回给进行中的游戏客户端。

M04-A 默认还输出 `stance_summary.v1`：每名 NPC 的统一立场变化，以及公开发言、警长票、放逐票相对决定前摘要的 `aligned / explained_change / unexplained_change / unscored` 对照。完整 100 局 belief + stance 样本约 101MB；只分析 belief 时应使用 `--no-stance-trace`。终端写文件时会显示：

```text
[STANCE] mode=shadow; observations=...; alignment=...; unexplained_change=...
```

M04-B 把普通非警长白天发言接入 `public_speech_continuity.v1`，计划升级为 `public_speech_plan.v3`；警长票和放逐票仍保留 stance 对照。V4.2 当时模拟结果为 `agent_town_simulation.v15` / `agent_town_simulation_batch.v15`，V4.6-A 为 v16，V4.6-B 当前为 v17；无 HTTP 玩家预言家会自动提交合法警徽流，并继续输出不含私有 belief 内容的 `speech_continuity_metrics.v1` 原因计数：

```text
[CONTINUITY] controlled_speeches=...; reasons={'stance_aligned': ..., 'new_public_evidence': ..., 'deterministic_variance': ..., 'authorized_claim': ..., 'mandatory_rule_response': ..., 'unscored': ...}
```

规则 fallback 会对齐 stance；启用 LLM 后，偏离必须引用本次已选的新增公开 signal，或命中内部 seed 与 NPC 参数决定的确定性扰动。合法声明和规则强制回应使用独立原因，不会把私有 belief evidence ID 写入持久化计划或公开台词。

M06-A 的隐藏信息不变性矩阵已并入完整 smoke。`hidden_info_projection.v1` 会比较普通村民玩家的公开/API 等价投影，以及所有普通 NPC 村民的 belief、stance、决策上下文、连续性和规则 fallback；`hidden_info_invariance.v1` 只输出摘要、计数和首个差异路径，不保存隐藏身份正文。

矩阵自动覆盖隐藏身份真值、悍跳内部标记、声明内部来源、未公布夜间结果和组合变体。固定夹具执行 96 项无权视角差分，并用公开查验结果变化作为必须被检测到的负对照。M06-A 只接受普通村民玩家和无警徽 NPC 村民。

M06-B 同样并入 smoke。`hidden_info_authorization.v1` 使用 `role_scoped_private_npc` 模式，在同一普通村民玩家基线上对 11 名 NPC 检查三类合法私有变化：

- 预言家把未公开验人从好人目标改为狼人目标，只允许该预言家的五层投影变化。
- 女巫看到的未公开刀口改变，只允许该女巫的 belief、stance、continuity 变化；V3.1-L 首夜固定概率救人后，decision context 和 fallback 均保持不变。
- 一名非悍跳狼与守卫/猎人交换隐藏身份，只允许其他三名狼人更新私有狼队视角；两个本人身份已经变化的 actor 不参与对比。

三类授权案例合计执行 158 项检查，所有公开投影和未授权 NPC/layer 必须不变。测试还会故意把预言家授权错配给村民，确认矩阵同时检测缺失授权与越权传播。报告不保存变体状态或私有 evidence 正文。

## 运行 M15-A/B 投票概率校准

默认批量模拟会在每次 NPC 警长票和放逐票前记录 `vote_probability_trace.v2`，并在批量根级输出 `vote_probability_summary.v2`。只有 `VOTE` 阶段非警长好人 NPC 放逐票使用 `consumer_mode=controlled` / `good_exile_cross_day.v1`；警长票、狼人票和规则硬约束继续为 shadow。推荐用固定 100 个 seed 做配对回归，同时关闭更大的 belief/stance 明细：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 100 \
  --no-belief-trace \
  --output /tmp/agent-town-vote-calibration.json
```

V3.1-O 固定 `20260719–20260818` 的验收结果为好人 `38/100`、狼人 `62/100`；好人误投率 `51.80%`，首放狼人后下一次继续放狼 `28/31`，女巫毒狼率 `71.01%`，悍跳参选/当选 `51/39`。这些是真值赛后回归指标，不进入实时策略；后续还需换起始 seed 并扩大到 1000 局。

`--no-belief-trace` 只关闭 belief/stance 轨迹；M15-A/B 会按投票阶段即时构造 actor-scoped `belief_state.v2`，因此仍保留较小的校准轨迹。终端会显示：

```text
[VOTE-CALIBRATION] observations=...; controlled=...; controlled_entropy=...; controlled_top=...; good_mass_on_wolves=...
```

每个候选人的 utility 拆为 `belief_utility / public_influence_utility / social_utility / coordination_utility / variance_utility`，总和与概率均有守恒校验。批量摘要可按投票类型、投票者阵营、consumer mode 及交叉维度查看个体熵、top 概率、实际票概率/排名和分量强度。真实阵营只在赛后汇总“好人概率质量落在狼人/好人目标”的评价指标，不参与候选分布生成。

M15-A 的 100-seed 基线中，普通好人放逐熵为 8.56%，排除警长硬票后的可比值为 9.01%，误投为 64.46%，狼人目标概率质量为 34.76%。M15-B 同 seed 的 1,482 次 controlled 观察熵为 9.82%、top 概率 93.45%；总体误投为 63.69%，狼人目标概率质量为 36.14%，好人胜场保持 2/100。这些数值是固定回归样本，不是平衡目标。

如只需要规则/M02 结果并明确不要 M15-A/B 轨迹：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 1000 \
  --no-belief-trace \
  --no-vote-calibration-trace \
  --output /tmp/agent-town-rule-only.json
```

`--no-vote-calibration-trace` 只关闭 JSON 诊断和汇总，不关闭 M15-B 的实时普通好人放逐策略；相同 seed 的 gameplay digest 必须与保留轨迹时一致。

## 汇总 V4.6-B / M09-A-B 脱敏 LLM 观测与成本

后端实际发生 LLM 调用或语义校验时，会把 `llm_observation.v2` 事件追加到
`backend/data/llm_observability.jsonl`。无需启动后端即可汇总已有文件；读取器也
兼容历史 `llm_observation.v1`：

```bash
backend/.venv/bin/python scripts/summarize_llm_observability.py
```

指定输入、版本化价格表，并同时保存 `llm_observability_summary.v2`：

```bash
backend/.venv/bin/python scripts/summarize_llm_observability.py \
  --input backend/data/llm_observability.jsonl \
  --price-catalog backend/config/llm_pricing.json \
  --output /tmp/agent-town-llm-summary.json
```

输出汇总请求成功率、语义校验恢复/回退、adapter 与 semantic 的 attempt/retry、
平均/P95/最大延迟、`complete / partial / missing / not_applicable` token usage、
provider attempt 覆盖、Prompt/config digest 覆盖、主要 fallback/rejection 类别，并
提供 `by_task`、`by_provider_model` 与 `by_prompt_config` 分组。日志不存在时输出
计数为 0 的合法空摘要；坏行被跳过并计入 `invalid_event_count`。

严格口径要求成功 request 至少一次 provider attempt，retry 必须等于
`max(0, attempt_count - 1)`；零 attempt 只允许 fallback 且不计费。查看
`/api/llm/status` 时，兼容字段 `base_url` 只会显示去掉 URL userinfo、query 和 fragment
后的 endpoint identity，不会回显其中可能携带的用户名、密码或 token。

嵌套 `llm_cost_summary.v1` 会保存价格表 fingerprint、原始 request/attempt/token
计数、已知价格/未知价格请求数、已知成本部分和未知原因。价格文件使用严格的
`llm_price_catalog.v1` schema；默认条目中的 `deepseek-v4-flash` 明确标为
`unknown`，不是官方报价，也不表示 0 成本。只要任一
可计费请求的 billing model、全部 attempt usage、有效价格窗或 input/output price
未知，`total_cost_usd_micros` 就是 `null`；不要把
`known_cost_usd_micros` 误读为完整账单。

观测文件采用严格脱敏字段，只保存 exact Prompt 与安全 config 的 SHA-256，不记录
API Key、prompt、上下文、回复、fallback 文本、game/character ID 或原始拒绝原因。
`backend/data/llm_validation_failures.jsonl` 是另一份可能包含原始候选的敏感审计
日志，不要把它当作日常指标源。provider 未返回 `usage` 时不猜 token。

无需启动后端即可执行，使用文末同一条完整自检命令：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

该命令不会启动 FastAPI 或 Godot 编辑器；末段只会短暂运行 Godot headless 资源加载检查。

只关闭 stance 明细、仍保留 belief 时使用：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 100 \
  --no-stance-trace \
  --output /tmp/agent-town-belief-only.json
```

准备运行 1000 局时，可关闭详细 belief/stance 轨迹，同时保留 M15-A/B 投票校准轨迹：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 1000 \
  --no-belief-trace \
  --output /tmp/agent-town-simulation-1000.json
```

关闭 belief 轨迹不会改变 `gameplay_digest`、胜负或指标，会把每局 `belief_trace / stance_trace` 和批量 `belief_summary / stance_summary` 设为 `null`，但默认继续输出独立的 `vote_calibration_trace / vote_calibration_summary`。单独使用 `--no-stance-trace` 时只有 stance 两项为 `null`；加上 `--no-vote-calibration-trace` 才会关闭 M15-A/B 明细，但 M15-B 实时策略仍启用。所有精简模式都保留体积很小的 `speech_continuity` 原因汇总。

## 启动后端和 LLM

LLM 会随 FastAPI 后端一起工作：

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

V4.3-A/B 只支持单 worker。不要添加 `--workers`，也不要同时运行多个指向同一
`AGENT_TOWN_GAME_SAVE_DIR` 的后端进程。

保持这个终端窗口运行。看到类似下面的输出表示后端已经启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

然后在 Godot 开始新游戏时勾选“启用 LLM”。环境变量开关和单局开关必须同时启用。

## 检查服务状态

另开一个终端执行：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/llm/status
curl http://127.0.0.1:8000/api/rag/status
curl http://127.0.0.1:8000/api/game/recovery-status
```

`/api/llm/status` 会显示安全的 `config_fingerprint`，不会返回 API Key。

浏览器 API 文档：

```text
http://127.0.0.1:8000/docs
```

## 启动 Godot 编辑器

```bash
godot --editor --path game
```

也可以直接用 Godot 4 打开 `game/project.godot`。

## 运行完整自检

完整 smoke 会短暂运行 Godot headless 资源加载检查，但不会启动编辑器、FastAPI 或常驻进程：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

其中 V4.4-A/B 检查覆盖三个分析 schema、承诺六态、四类中立候选、合理修订/
公开条件失效不误报、只读确定性、隐藏信息不变性、OpenAPI 与 NPC 同源 ID；
V4.5-A 另覆盖三个复盘 schema、五类错误、终局真值隔离、稳定 ID/计数和 Godot
第三页静态契约；V4.7-A 覆盖七步 allowlist、仅完整 `/state` 触发、轮询去重、六身份
安全文案、F1/键盘弹窗和只保存完成布尔值的本地偏好。V4.7-B 继续静态检查
`agent_town_responsive_layout.v1` 的三档物理窗口 profile、动态侧栏与角色卡列数、
`agent_town_focus_navigation.v1` 的焦点范围与回还、模态输入隔离、可见焦点样式、字号
下限和只读文本滚动，并锁住曾导致 `main.gd` 整体加载失败的三处类型推断写法。
V4.7-C 额外检查 Python 3.12 / Godot 4.7.1 的 Linux/macOS CI、
离线环境、完整 action SHA、Godot UID、LF 与 `docs/V4_RELEASE_CHECKLIST.md`。完整 smoke
不会启动 FastAPI 或 Godot 编辑器/常驻服务；末段只会短暂执行 Godot headless 资源
加载检查。

只运行 V4.3-A/B 的临时目录存档与幂等检查：

```bash
backend/.venv/bin/python scripts/check_game_persistence.py
```

该检查使用临时目录，覆盖原子失败回滚、同 key 并发、409 冲突、响应丢失后的
未完成局/终局恢复、结果台账篡改、旧空台账存档的窄兼容、固定角色顺序重放和无
key 兼容，不会启动服务。

## 查看 LLM 校验失败日志

输出校验开启时，只要出现被结构化事实校验拒绝的 LLM 候选文本，就会生成或追加该文件；日志会列出全部原因，并区分后续恢复成功和达到 5 轮上限后的规则回退。关闭 `enable_llm_validation` 后校验次数为 0，不会生成 validation failure；自然同义改写不要求与规则模板逐字一致：

```bash
tail -n 5 backend/data/llm_validation_failures.jsonl
```

JSONL 日志和游戏结束后的复盘摘要会保留 DeepSeek 原始返回，可能带有对局隐藏信息；进行中的 Godot 对局只显示失败原因与脱敏占位，不展示原始返回。

当前校验按“声明者 → 目标 → 结果”记录验人；例如“5号给8号金水”只会把8号识别为5号的查验目标。旧日志保留修复前的失败原因，新规则只作用于重启后生成的新回答。

## 停止后端

回到运行 Uvicorn 的终端，按：

```text
Control + C
```

确认 `8000` 端口已经关闭：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

没有输出就表示后端已经停止。
