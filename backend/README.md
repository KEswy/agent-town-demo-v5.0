# Backend

Agent Town Demo 的 Python FastAPI 后端，负责小镇 NPC 对话、知识检索、长期记忆，以及狼人杀规则和对局内 NPC 状态。

## V4.8-A 开局 LLM 输出校验开关

`GameStartRequest` 新增 `enable_llm_validation: bool = true`。旧客户端省略该字段时继续
使用默认最多 5 轮语义校验与纠错。设为 `false` 时，后端跳过 LLM 结构化策略选择，
先采用 Python 生成的合法计划，再请求 1 份最终模型文本；该文本的语义校验与纠错次数
为 0，并直接用于显示。网络、配置、JSON 或 `text` 提取失败时仍回退规则文本。
`GameStartResponse` 与 `GameStateResponse` 通过 `llm_validation_enabled` 返回本局实际
生效模式；LLM 未实际启用时该值为 `false`。

原文直出可能包含错误、矛盾、越界或虚构信息。为了不让显示文本篡改规则，关闭校验时
普通白天和警上 NPC 的权威公开立场、声明、怀疑值与技能建议只从 Python 计划或规则
文本生成，未校验原文不再被解析成这些字段；身份、行动、投票、警徽、出局和胜负仍由
Python 结算。原文仍进入玩家可见台词、公开日志或私聊记录，因而能够影响玩家判断。
原文直出固定只有 1 次适配器请求，不执行网络重试或语义纠错。坏坏、然然的普通
`/chat` 使用全局居民聊天链路，不受 `enable_llm_validation` 影响。

选择由首个 `game_created.command.start_request.enable_llm_validation` 封印。后端不向
`WolfGameState` 新增字段，旧事件缺少该键时按 `true` 读取，因此现有旧存档的完整快照、
规则状态摘要和事件链不会因为本功能变化；下一次保存也不需要迁移状态字段。实际启用
LLM 的局无论开启校验还是原文直出都保持 `replayable=false`，只提供事件审计，不能声称
确定性重放。

## V4.7-C CI 与后端封版边界

V4.7-C 的交付机制已经完成，但项目尚未封版。新增 workflow 在 Ubuntu 24.04 与
macOS 15 上固定 Python 3.12，并用 `scripts/smoke_check.py --profile core` 从 fresh
install 验证编译、规则、仿真、存档/恢复、幂等、文档和静态 Godot 契约；另以 Godot
4.7.1 运行 `--profile godot`。默认无参数仍是完整 smoke。

CI 测试阶段固定 `ENABLE_LLM=false`、`LLM_PROVIDER=mock`、
`AGENT_TOWN_DISABLE_VECTOR_RAG=1` 和 `HF_HUB_OFFLINE=1`，存档写 runner 临时目录；不读取
secret、不请求真实 LLM、不下载向量模型、不启动 FastAPI、Godot 编辑器或常驻游戏。
依赖与 Godot 安装阶段仍需访问软件源。该阶段不修改任何 Pydantic/HTTP、规则状态、
事件、存档或 LLM schema。

`runner.temp` 只在 runner 已启动后的两个 smoke step `env` 中解析，不能放在 job 级
`env`；静态检查会拒绝后者，避免 workflow 在创建四个矩阵 job 之前直接失败。
内联 Python smoke 同样统一通过 stdin 交给 `python -`，避免 Linux 较小的 `ARG_MAX`
因超长 `python -c` 参数而在狼人杀完整契约检查启动前失败。

完整源码交付、POSIX 本地存档范围、依赖记录、隐私检查和正式标签门禁见
[`V4 封版清单`](../docs/V4_RELEASE_CHECKLIST.md)。公开开发仓库
[`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0) 已由专用
`v4-origin` 承载开发快照，但尚未创建 `v4.0.0` 正式封版标签；历史 `origin`、
`v2-origin`、`v3-origin` 仍禁止推送 V4 代码。项目当前没有根级 `LICENSE`，明确为
未授予再分发许可。

## V4.7-B 客户端响应式布局与键盘焦点边界

V4.7-B 的 `agent_town_responsive_layout.v1` 和 `agent_town_focus_navigation.v1`
完全位于 Godot 客户端。本轮不新增或修改 HTTP 路由、Pydantic model、
`WolfGameState`、规则判定、规则事件、存档、重放、幂等台账、LLM/RAG 请求或响应
字段；Python 仍是身份、合法知识、行动、投票、警徽、出局和胜负的唯一事实来源。

响应式布局按物理窗口选择三个客户端 profile，并继续使用原有 Python 状态投影：

- `compact`：窗口宽度小于 `1200`，以 `1100×650` 最小窗口验收；行动区宽
  `420`、情报区宽 `520`，角色卡为两列。
- `default`：窗口宽度为 `1200–1439`，或未同时满足 wide 的宽高条件；以
  `1280×720` 默认窗口验收，行动区宽 `440`、情报区宽 `600`，角色卡为三列。
- `wide`：窗口宽度至少 `1440` 且高度至少 `820`，以 `1600×900` 窗口验收；
  行动区宽 `480`、情报区宽 `736`，角色卡为四列。

键盘焦点只管理客户端 `WORLD / PANEL / TEXT_ENTRY / MODAL` 四种作用域。Tab 与
Shift+Tab 在当前可见范围内循环，方向键保留选项、滚动和面板导航，Enter/Space
执行当前按钮，Esc 关闭最上层面板；非文本面板中的 WASD 或世界点击归还世界控制，
文本输入和 modal 不允许按键穿透到玩家移动。设置、引导、发言预览、NPC 对话和赛后
复盘在关闭后优先归还打开前焦点，无合法目标时才回到世界。字体、深浅色焦点描边、
可滚动长文本和动态可见控件的焦点修复也只属于 Godot 展示层，不改变任何后端事实。

Godot 4.7 的 warning-as-error 曾使 `main.gd` 因三处不安全类型推断而整份加载失败，
表现为独立 `player.gd` 的 WASD 仍可用，但主脚本负责的按钮和 E 键 NPC 交互均无响应。
客户端现已为引导阶段判断、待显示步骤和分页栏添加显式类型，并把旧写法加入 core
smoke 禁止列表；本修复没有改动任何后端 API、schema、事实或权限边界。

## V4.7-A Godot 首局引导的后端边界

V4.7-A 的 `agent_town_onboarding.v1` 完全位于 Godot 客户端，不新增 Pydantic model、
HTTP 路由、`WolfGameState`、规则事件、存档或幂等字段。自动引导只在完整
`GET /api/game/{game_id}/state` 成功后评估，因为 `GameStartResponse` 刻意不包含
`player_private_info`；开局精简响应不能触发身份或技能提示。

七个客户端白名单步骤为 `identity_and_scope`、`night_skill`、`sheriff_flow`、
`public_speech`、`private_chat`、`exile_vote` 和 `post_game_review`。它们只消费
`day / phase`、玩家存活与轮次、脱敏 `CharacterView`、公开证据，以及
`PlayerPrivateInfo` 中已经授权给玩家本人的身份和技能状态：

- 非狼人玩家仍只能看到自己的身份；狼人玩家只能额外看到自己的三名狼队友。
- 公开 claim、承诺和矛盾候选继续是“全场公开但未验真”，不能被引导说成身份真值。
- 私聊原文不会自动进入公开事实，但可以进入该 NPC 的私密记忆并影响后续判断。
- `post_game_review` 只说明赛后复盘入口，不读取 `/summary` 内容；完整身份真值仍必须
  等 Python 已经进入 `GAME_OVER` 后由原有 summary 接口提供。

`user://agent_town_onboarding.cfg` 只保存 `schema_version=agent_town_onboarding.v1` 和
`automatic_guide_completed` 布尔值，不保存 game id、role、队友、查验、刀口、聊天或
访问凭据。顶部 `?` / F1 可手动重开；Tab、Shift+Tab、Enter、Space、方向键和 Esc
均在客户端弹窗内处理。注意本地 Demo 没有多用户鉴权，包含玩家私密投影的 game id
应被当作本地访问凭据，不应对外共享。

## V4.6-B 实验指纹、LLM 成本与 artifact A/B

`app/llm_fingerprinting.py` 定义三层 digest-only 契约：

- `llm_prompt_fingerprint.v1` 在 `LLMClient` 收到最终 system prompt 的边界对 exact
  prompt、task、operation 和请求契约做 SHA-256；原文只参与内存中的摘要计算。
- `llm_config_fingerprint.v1` 只读取 provider、model、temperature、max tokens、
  timeout/retry 和脱敏 endpoint identity 等 allowlist 配置，明确不读取 API Key。
- `experiment_fingerprint.v1` 同时给出完整 `configuration_fingerprint` 和只包含
  active 组件的 `effective_fingerprint`。规则仿真把 rules/roles、NPC profiles、
  tuning、输出 schema 与当前 player policy 标为 active；Prompt catalog、知识库、
  LLM request config 和 RAG 标为 inactive，但仍保留完整配置漂移摘要。

`app/llm_observability.py` 当前写 `llm_observation.v2` 并输出
`llm_observability_summary.v2`，读取器继续接受历史 v1。request 事件增加
`prompt_fingerprint / config_fingerprint`、token usage 状态、已报告/未报告 usage 的
provider attempt 数和 billing model 来源；汇总将 adapter attempt/retry 与 validation
产生的 semantic attempt/retry 分开，避免把语义重试重复算成云端重试。日志仍不允许
API Key、Prompt/上下文/回复原文、game/character ID 或原始拒绝内容。request 成功必须
至少发生一次 provider attempt，adapter/semantic retry 必须严格等于各自 attempt 数减一；
零 attempt 只允许非计费 fallback。`/api/llm/status` 保留 `base_url` 兼容字段，但其值只
是移除 userinfo、query 和 fragment 的安全 endpoint identity。

config fingerprint 表示“实际请求参数身份”，因此明确不读取 API Key、`enabled` 或
`configured`；是否执行 LLM 由观测 outcome/attempt 和实验 execution mode 单独表达。

`app/llm_pricing.py` 严格校验 `llm_price_catalog.v1`，生成
`llm_cost_summary.v1`、按 provider/configured model/billing model 分组的原始计数和
price catalog fingerprint。默认 `config/llm_pricing.json` 中
`deepseek-v4-flash` 明确为 `pricing_status=unknown`：它不是官方报价，也不是零成本。
只有 billing model、完整 attempt usage、有效时间窗和 input/output price 都已知时，
请求才完整计价；存在任一未知可计费请求时 `total_cost_usd_micros=null`，可证明的
`known_cost_usd_micros` 与原始 token 仍保留。

`app/experiment.py` 与 `scripts/compare_simulation_artifacts.py` 只读比较两个或多份
`agent_town_simulation_batch.v17` artifact，输出 `agent_town_artifact_ab.v1`：

- 每个 arm 必须只有一个不同的 configuration/effective fingerprint；所有 artifact
  digest、内嵌 game digest 与 schema 都会重新校验。
- cohort 固定为 `seed + actual player role`，且两侧必须完整相同；配对还要求相同
  initial layout、player strategy/policy、ruleset、schema 和 trace 开关，不会静默丢样本。
- 胜负/局长与五项 V4.6-A 质量指标同时保存原始计数。质量比较先跨局累积分子、分母
  与 similarity sum，再计算 rate 和 B-A delta。
- 比较器不运行仿真、不切换代码/配置，也不调用 LLM；报告固定
  `comparison_mode=rule_only_artifacts_no_llm`、`llm_evaluated=false`、
  `prompt_effect_evaluated=false`。Prompt 指纹不同只说明
  artifact 的完整配置不同，不能证明真实 Prompt 效果。

`app/simulation.py` 当前输出 `agent_town_simulation.v17` /
`agent_town_simulation_batch.v17` 并嵌入同一 `experiment_fingerprint.v1`；冻结的
`gameplay_digest_projection_version=agent_town_simulation.v14` 和
`agent_town_metrics.v5` 不变。CLI 写 artifact 时打印 `[EXPERIMENT]`，比较器打印
`[ARTIFACT-A/B]` 与逐项 `[QUALITY-A/B]`。

## V4.6-A NPC 表达质量离线基线

`app/speech_quality.py` 为已经结束的无 HTTP 对局生成确定、只读的 NPC 公开发言质量
报告。它固定六个版本化契约；其中五个报告 payload 模型都使用严格类型、拒绝非有限
数和额外字段，normalization 契约固定算法口径：

| schema | 用途 |
| --- | --- |
| `npc_speech_normalization.v1` | NFKC、大小写、标点与去目标模板的固定口径 |
| `npc_speech_quality_observation.v1` | 单条 NPC 发言摘要、公开信息原子、引用和重复关系 |
| `npc_speech_actor_quality.v1` | 单局单 NPC 的原始计数与比率 |
| `npc_speech_quality.v1` | 单局质量报告 |
| `npc_speech_actor_quality_batch.v1` | 跨局单 NPC 加权汇总 |
| `npc_speech_quality_batch.v1` | 批量原始计数、分母和加权比率 |

单局 simulation 增加 `npc_speech_quality_schema_version` 与
`npc_speech_quality`；批量增加 `npc_speech_quality_schema_version`、
`npc_speech_quality_batch_schema_version` 和 `npc_speech_quality_summary`。
构建器只接受 `GAME_OVER + winner`，并固定
`scope=npc_public_speeches_only`、`truth_scope=public_only_no_role_truth`。

- 输入只含 NPC 已公开发言、随该条 speech 保存的公开结构化 position/plan 和
  evidence/signal 引用；玩家公开发言只参与“此前公开信息”基线。终局按天聚合的
  `public_claims` 没有逐发言 provenance，因此不会回填到更早发言。真实 `role/camp`、私有
  belief、夜间秘密和赛后阵营标签不进入统计。
- `normalize_speech_text()` 做 NFKC、转小写并仅保留字母数字；模板还替换公开姓名、
  座位号和数字。observation 只保存规范文本/模板 SHA-256 与字符数，不保存原始台词。
- 精确表面重复、去目标模板重复、跨角色模板重复分别计数。近重复使用字符 trigram
  Jaccard，固定 `near_duplicate_threshold=0.82`，同时保存所有 speech pair 与跨角色
  pair 的分子、分母和比率。
- 公开结构信息会变成稳定 atom；`information_increment_rate` 是新信息原子数除以
  全部信息原子数，`zero_information_increment_rate` 是没有新增原子的 NPC 发言数
  除以 NPC 发言数。自由文本本身不会被猜成规则事实。
- 证据引用统计保存的 RAG 标题、decision signal、plan 引用和立场 basis；人设代理
  统计配置口头禅/彩蛋命中，并以
  `1 - mean_cross_actor_template_similarity` 得到
  `persona_differentiation_score`。两者都不证明引用正确或人设自然。
- 批量聚合先累加 count、pair denominator 和 similarity sum，再计算加权 rate；不
  平均每局百分比。trace 开关不会改变质量结果。

V4.6-A 当时输出 `agent_town_simulation.v16` /
`agent_town_simulation_batch.v16`；V4.6-B 当前为 v17。`agent_town_metrics.v5` 和冻结的
`gameplay_digest_projection_version=agent_town_simulation.v14` 不变。该报告不进入
实时 FastAPI schema、NPC 决策、LLM 请求、存档、重放或 Godot。本阶段不设置自动
通过阈值；字符相似度、信息原子和 marker 都只是可复现诊断代理。普通 CLI 使用
`[SPEECH-QUALITY]` 打印紧凑摘要。人设 marker 读取当前 NPC profile；V4.6-B 已把
profiles 纳入完整和 active-only 实验指纹，跨时间比较必须先核对指纹口径。

## V4.5-A 可解释赛后决策复盘

`app/post_game_review.py` 定义严格的 `post_game_evidence_reference.v1`、
`post_game_decision_review.v1` 和 `post_game_explainable_review.v1`。
`GET /api/game/{game_id}/summary` 在原角色/时间线复盘旁新增
`explainable_review`，但仍由 Python 强制要求 `phase=GAME_OVER` 且 winner 已确定。

投影读取已保存的发言、公开立场卡、结构化 plan/signal、RAG 标题、投票理由、夜间
行动、女巫策略、猎人动作和 V4.4-A 公开证据时间线，覆盖
`public_speech / exile_vote / night_action / hunter_shot` 四类决定。每条包含稳定
`review_id`、源集合坐标、决定摘要、行动者/目标的赛后身份真值、提交时保存的依据、
最多六条更早和六条更晚日期的相关公开证据、评价、错误类别与解释。

安全边界如下：

- 根级固定 `truth_scope=post_game_truth_unlocked`，每条固定
  `post_game_truth_unlocked=true`；`GameStateResponse`、公开证据和 NPC 合法知识没有
  新增复盘字段。
- `knowledge_scope=recorded_basis_plus_prior_day_public_evidence`。只有更早日期的公开
  evidence 可称为一般先验；同日信息只有确实持久化在该决定中的 signal/plan 才能
  作为依据。旧集合没有逐条同日 provenance 时不猜顺序或心理活动。
- `mistaken` 只能配对 `deceived / insufficient_evidence / continuity_break /
  skill_misuse / deterministic_variance`。受骗必须有被选择的狼人失实验人 signal；
  连续性断裂必须能看到已保存立场/暂票偏离；其余不从自由文本强推因果。
- `accurate` 只配 `none`；狼人阵营决定为 `strategic`；获取信息或没有可评分方向的
  决定为 `neutral/unscored`，统一配 `not_applicable`。
- 根模型重新核对连续 sequence、唯一 ID、完整计数词表和条目计数。生成函数只读且
  确定，不改变 `WolfGameState`、规则摘要、存档、幂等台账或 replay。

Godot 终局摘要继续调用同一 `/summary`，第三个“解释复盘（赛后）”页明确警告身份
真值只在赛后解锁，并分栏式展示当时依据、赛后评价和后来证据。自动化覆盖五类
错误、终局门禁、OpenAPI、只读决定性和 UI 静态契约。

## V4.4-B 承诺生命周期与中立矛盾候选

`app/public_evidence.py` 在 V4.4-A 时间线之上新增严格的
`public_commitment_state.v1`、`public_contradiction_candidate.v1` 和
`public_evidence_analysis.v1`。`GET /api/game/{game_id}/state` 的
`public_evidence_analysis` 与时间线绑定同一 `game_id` 和
`projected_event_sequence`，根级固定
`truth_scope=public_only_no_post_game_truth`。

每个警徽流版本都有稳定 `commitment_id`、原始 `source_evidence_id`、首段/次段
验人目标、公开金水锚点或撕徽分支，以及相关替代/解决 evidence ID。当前只评价
“首段验人目标 + 警徽分支”，次段目标作为上下文保留，不被提前当作独立到期承诺。
六种生命周期状态为：

- `active`：尚未到生效夜，或仍在等待承诺人的公开后续。
- `superseded`：生效夜前已有公开修订，并链接替代它的 evidence ID。
- `fulfilled`：公开验人报告命中首段目标，或实际警徽动作符合已公布分支。
- `invalidated`：承诺人、首段目标或可用警徽分支在兑现前已因公开出局而失效。
- `undetermined`：到期后没有足够公开后续，或到期后的修订不能反推旧承诺结果。
- `contradicted`：公开验人目标不同，或警徽动作落在已公布分支之外；它只是关系
  标记，不是事实验真或阵营结论。

分析只生成 `identity_claim_changed / seer_result_changed /
badge_flow_target_mismatch / badge_flow_action_mismatch` 四类
`public_contradiction_candidate.v1`。候选同时保存前后 evidence ID，固定
`review_status=needs_review` 和 `judgment=none`。警徽流正常修订、目标/分支不可用、
缺少公开后续，以及警长暂时归票改为最终归票都不会单独制造候选。

`build_actor_legal_knowledge()` 消费与状态 API 相同的 commitment/candidate ID；
Godot 公开记录页显示生命周期和候选，并附“需核对，不代表阵营判断”的提示。
投影重复调用 JSON 相同且零状态变化，不进入 `WolfGameState`、`game_save.v1`、
规则摘要、幂等台账或 replay。交换隐藏 `role/camp`、声明内部来源和同一公开夜死
结果的内部原因，不会改变分析输出；赛后身份验真由 V4.5-A 的终局摘要独立完成。

## V4.4-A 公开证据投影

`app/public_evidence.py` 定义严格、额外字段禁止的
`public_evidence_item.v1` 与 `public_evidence_timeline.v1`。
`GET /api/game/{game_id}/state` 的 `public_evidence_timeline` 把当前规则事件游标下的
公开记录投影成连续、稳定、可供 UI 和 NPC 共用的条目；它不是新的规则状态，也不
落入存档。

单项字段包括 `evidence_id / sequence / day / category / kind / verification`、公开
行动者/目标、所有公开关联席位、`public_result` 和中立 `display_text`。ID 的摘要
输入只含公开结构和追加集合内的稳定位置，不含 `PublicClaimState.source`、真实
`role/camp`、夜间责任人或出局内部来源。时间线根级
`projected_event_sequence` 表示本次投影对应的最后规则事件；V3/V4.1 已有公开记录
没有精确逐项事件 provenance，因此本阶段不猜测或伪造该字段。

投影来源和安全规则如下：

- `public_claims` 中已公开的神职、验人、女巫和守卫说法进入 `claim`，始终
  `unverified`。
- `badge_flows` 进入 `commitment`，版本、两段验人目标、公开金水锚点和修改理由
  都只代表声明者公开承诺，始终 `unverified`。
- `sheriff_events`、猎人开枪、已经公开结算的警长/放逐票和出局结果进入
  `confirmed_action`；这里的 `confirmed` 只确认动作/结果发生。
- `game_state.votes` 只有在同日存在 `exile_vote_resolved` 或
  `all_votes_submitted_and_resolved` 规则事件后才投影为 `exile_ballot`。夜间出局合并为
  `night_out`，不区分狼刀和毒药；猎人目标不重复生成第二条出局记录。
- `build_actor_legal_knowledge()` 直接引用最近 24 条相同 `evidence_id`，Godot 的
  关键信息折叠区和公开记录页也读取同一时间线；旧后端响应仍降级到
  `public_intel/public_logs`。

投影函数是完全只读的；重复调用 JSON 相同，交换不可见身份/阵营、声明内部来源，
或在同一公开夜死结果之间交换狼刀/毒药内部原因都不改变输出。V4.4-B 已增加承诺
生命周期与中立矛盾候选，但仍不验真或自动判断阵营。

## V4.3-B 幂等规则命令

`app/idempotency.py` 定义 `game_command_idempotency.v1` 与严格的
`game_command_result.v1`。全部 20 个开局后规则写函数共用同一个
`transactional_rule_endpoint`：对应 18 个请求模型新增可选 body 字段
`idempotency_key`，旧客户端不传仍按原协议执行。

key 以 `game_id` 为作用域，长度 8–160；首位必须是 ASCII 字母或数字，其余只允许
字母、数字、`.`、`_`、`:`、`-`。第一次成功执行时，装饰器要求该函数恰好追加一个
规则事件，先验证响应模型，再创建结果记录。结果记录包含端点、去掉 key 后的请求
摘要、事件序号/类型/摘要、响应模型、响应摘要和完整响应 payload。

- 同 key、同端点、同请求摘要在进入阶段和业务校验前返回已保存的响应模型，不执行
  规则函数、不追加事件、不更新时间，也不写盘。
- 同 key 的端点或 payload 不同返回 HTTP 409。key 在同一局的完整存档生命周期内
  保留，本阶段不做 TTL 或删除。
- 第一次带 key 的命令只有在“规则状态 + 新事件 + 新结果记录”通过完整校验并完成
  同一次 `game_save.v1` 原子替换后才算提交；替换前异常恢复完整 checkpoint。
- 服务在响应提交后中断时，重启会恢复结果台账；重试先命中结果，所以即使原命令
  已把 `NIGHT` 推进到下一阶段，仍返回原 `NightResolveResponse`。
- 终局存档继续在启动时 skipped；若最后一条带 key 命令的响应丢失，guard 会只读
  加载并完整校验归档中的结果，返回原响应而不把终局放回 `GAME_STORE`。
- 结果记录必须与其事件内的 key/payload、事件摘要和当前注册响应模型逐项一致；
  篡改响应、请求摘要、事件引用、端点或映射 key 都会令恢复 fail closed。
- 带 key 的事件仍可执行规则模板重放。`command_results` 不参与规则状态摘要，避免
  传输层台账改变玩法摘要，但参与完整快照摘要和恢复校验。
- `build_role_pool()` 使用固定角色顺序，不依赖 JSON 对象键顺序；排序后的存档事件
  仍能用原 seed 重建相同身份、夜间行动和角色资源。

Godot 在 10 个 HTTPRequest 通道上覆盖夜间、猎人、两类发言、私聊、警长操作和
合并投票：同一 operation + payload 在非 2xx 或网络失败后复用 key，2xx 后清理；
payload 改变时创建新 key，开新局清空旧局待处理项。待处理 key 目前仅在 Godot
进程内存中，不承诺客户端自身崩溃后的自动续传。

边界：`POST /api/game/start` 没有外部幂等 key；玩家发言 preview、GET、显式
save/restore 和 replay 也不属于这 20 条命令。无 key 请求保持兼容，但不提供响应
丢失后的 exactly-once 效果保证。事件 `command_id` 是审计标识，不可代替外部 key。
跨进程/多 worker 协调仍未实现。

## V4.3-A 原子存档与启动恢复

`app/game_persistence.py` 定义严格的 `game_save.v1`、
`game_save_response.v1`、`game_restore.v1`、`game_recovery.v1` 和
`recovery_config_fingerprint.v1`。`WolfGameState.recovery_config_fingerprint`
在开局时冻结，并写入 `game_created` 事件、完整状态和存档 envelope 三处；它覆盖
规则版本、角色配置、NPC 人设/知识/调参与不含密钥的 LLM 状态，不保存 API Key。

每份私有存档同时校验四个边界：完整快照 SHA-256 防止任意序列化字段被改；规则
状态 SHA-256 对齐最后规则事件；最后事件序号/摘要对齐追加链；恢复配置指纹阻止
未完成局在不兼容配置下继续。恢复还严格核对 schema、文件名/envelope/state/event
中的 game ID、首个 `game_created`、事件链、模型 round-trip 和额外字段。

- 只有 FastAPI `lifespan` 会启用自动持久化。直接导入 `app.main`、离线 simulation
  和隔离 replay 不注册为持久局，也不会创建或改写存档。
- 新局发布进 `GAME_STORE` 前先完成首次保存；之后全部 20 个规则写入口共享事务
  guard。命令提交前任何 helper/校验异常恢复完整 checkpoint；事件封印后若写盘
  失败，则旧文件保持不变、内存回滚并返回 503。
- `GameSaveStore` 在同目录以 `0600` 独占创建临时文件，flush/fsync 后
  `os.replace`；保存目录使用 `0700`。替换一旦成功，后续 best-effort 目录同步不再
  反向报告失败，避免磁盘已前进而内存回退。
- 服务启动先校验整个目录，再一次性恢复所有合法未完成局；任一活动存档损坏或
  配置漂移都会使 lifespan fail closed，不做部分恢复。终局归档计入 skipped，
  不要求当前配置相同，仍可通过手动 restore 加载查看。
- 进行中持久局存在时，`POST /admin/reload-config` 返回 409。当前实现依靠进程内
  `RLock/Lock` 和单份 `GAME_STORE`，因此只支持一个 uvicorn worker。
- 恢复兼容一类早期 V4.3-A 快照：原始 `snapshot_digest` 必须先通过，归一化后的
  唯一差异必须是缺少默认空 `command_results`，且事件链中不得有任何
  `idempotency_key`。读取/启动恢复只在内存补空台账，不改原文件；下次正常持久化
  才升级。任何其他 round-trip 差异、缺失非空台账或带 key 事件仍 fail closed。

默认目录为 `data/games/`，也可在 `.env` 设置
`AGENT_TOWN_GAME_SAVE_DIR=data/games`。文件包含隐藏身份、seed、夜间行动和私聊，
必须视为私有运行数据；`backend/data/` 已被 Git 忽略。

接口为 `POST /api/game/{game_id}/save`、
`POST /api/game/{game_id}/restore` 与 `GET /api/game/recovery-status`。
V4.3-B 已在 V4.3-A 的原子提交边界上加入外部 key 和结果台账。完整 Prompt/实验/
成本指纹已由 V4.6-B 另行实现，不应与恢复指纹混用，也不改变存档兼容规则。

## V4.2 规则事件链与执行式重放

`app/event_log.py` 定义严格的 `game_rule_event.v1`、
`game_rule_event_log.v1` 和 `game_rule_replay.v1`。`WolfGameState.rule_events`
从 `game_created` 开始，只在成功的规则命令末尾追加；每项封印稳定序号、命令 ID、
`agent_town_rules.v4.2`、可见范围、请求 payload、前后 day/phase、前后规则状态
SHA-256 和上一事件 SHA-256。状态摘要排除 game ID、墙钟时间和事件数组本身，保留
所有会影响后续规则的公开、合法私有和隐藏状态。

`GET /api/game/{game_id}/events` 与 `POST /api/game/{game_id}/replay` 都只允许
终局调用。重放复制事件后释放原局锁，在独立临时 `GAME_STORE` 槽位重建开局并调用
同一组规则函数；每条命令前后都核对摘要，最终再核对胜负、警长票、放逐票、出局、
警徽流和完整状态摘要，最后清理临时局。读取普通 state 不再隐式回写
`player_private_info`，角色资源读取也不再以 `setdefault` 产生无事件写入。

只有实际关闭 LLM 与 RAG 的规则模板局标记为可执行重放。含模型或检索输出的局仍
记录完整哈希链，但响应明确说明只支持审计；当前实现不会重调模型并假装文本确定。
执行式重放要求代码和 NPC 配置不变；V4.3-A 已增加窄范围恢复配置指纹，完整
Prompt、模型实验和 A/B 指纹已由 V4.6-B 作为独立离线实验契约补齐。
V4.2 当时把仿真升级为 `agent_town_simulation.v15` /
`agent_town_simulation_batch.v15`；V4.6-A 为 v16，V4.6-B 当前为 v17。每局默认重放；批量默认省略完整事件数组，使用
`--include-event-logs` 才保留。磁盘持久化和恢复已由 V4.3-A 完成；V4.3-B 已把
外部幂等 key 和原响应绑定到同一事件提交。
`gameplay_digest` 继续使用 `agent_town_simulation.v14` 兼容投影，事件 schema、日志
和重放报告进入 `result_digest`，避免把纯审计元数据变化误判为玩法变化。

## V4.1-B 玩家发言理解与提交前预览

`app/player_speech.py` 定义严格的 `player_speech_understanding.v1` 与
`player_speech_preview.v1`。`POST /api/player-speech/preview` 接受白天或警上
草稿、可选暂归票和警徽流，在 `GAME_LOCK` 内复用最终提交的解析与权限校验，
但不调用任何写状态函数。

预览返回规范化公开文本、会写入的公开声明/暂归票/警徽流、会应用的怀疑/支持/
反对/票意向/女巫建议、仅文本说明及拒绝原因。合法预览的 SHA-256 指纹绑定输入、
当前天数、阶段、发言者和相关公开状态；两类提交接口新增可选
`preview_fingerprint`。携带指纹时，后端锁内重算不一致会返回 409；未携带时仍
锁内重新解析，保持旧客户端兼容且不能绕过 Python 校验。

预览响应不包含其他角色真实 `role/camp`。自动化测试覆盖预览前后完整状态一致、
警上缺失警徽流的可展示拒绝、警徽流规范化、逗号子句验人边界、修改草稿后的旧
指纹拒绝，以及不可见 NPC 身份互换不变性。

## V4.1-A 三档玩家策略与身份配对基准

V4.1-A 只扩展离线仿真，不修改实时请求/响应 schema 或 Godot。正式矩阵同时
补齐 `app/main.py` 的一个既有规则兜底边界：NPC 狼同日既被狼队友互踩查杀、
又被另一名预言家查杀时，主目标继续反对互踩来源，次目标和两条公开信号完整
回应另一声明；不改变任何验人事实、隐藏身份权限或实时接口。
`app/player_strategy.py` 定义：

- `player_strategy.v1`：`beginner / standard / expert` 以及各自策略版本。
- `player_strategy_context.v1`：净化后的公开事实、玩家自身身份和角色依法拥有的
  狼队友/验人/女巫刀口/技能资源。
- `basic_legal.v1`：简单合法策略。
- `legal_public_baseline.v1`：冻结 V3 自动玩家行为的 standard 策略。
- `evidence_guided.v1`：综合公开压力、既往票型、声明和合法私有信息的 expert 策略。

公开角色条目采用精确字段集合，不含其他席位真实 `role/camp`。纯策略排序函数
只接收该 context 和规则已经给出的合法候选 ID，不接收 `WolfGameState`。赛后
`player_performance.v1` 可以读取真实身份评价已经发生的投票和技能，但指标不会
进入实时 API 或任何策略输入。

`app/simulation.py` 在 V4.1-A 使用 v14、V4.2 使用 v15、V4.6-A 使用 v16，
V4.6-B 当前输出：

- `agent_town_simulation.v17` / `agent_town_simulation_batch.v17`
- `experiment_fingerprint.v1`
- `player_decision_trace.v1`
- `initial_layout_digest`
- `agent_town_player_benchmark.v1`
- `game_rule_event_log.v1` 摘要或完整日志，以及 `game_rule_replay.v1`
- `npc_speech_quality.v1` 与批量 `npc_speech_quality_batch.v1`

`app/simulation_metrics.py` 当前为 `agent_town_metrics.v5`，在全部 V3 指标之外
增加玩家胜负、放逐/警长票目标、预言家查验、女巫用药、守卫拦截、猎人命中、
狼人刀口价值及 NPC 跟随玩家公开目标的代理指标。所有比率保留计数分子/分母，
无分母时为 `null`。

三档完整配对使用相同 `seed + player_role`，覆盖六种固定身份，并要求每个
cohort 的 `initial_layout_digest` 唯一。轻量命令：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 2 \
  --benchmark-player-strategies \
  --output /tmp/agent-town-v4-player-benchmark.json
```

这里的 `--games` 表示每种固定身份使用多少个连续 seed；上述命令共
`2 × 6 × 3 = 36` 局。正式最小基准使用 `--games 56`，共 1008 局。
配对模式默认关闭 belief、stance 和 vote-calibration 明细，不启动 HTTP、
Godot、LLM 或向量 RAG。单策略批量可使用
`--player-strategy beginner|standard|expert`。

固定 `20260719–20260774` 的正式结果为三档各 336 局，玩家获胜数
`88 / 106 / 107`；`standard-beginner`、`expert-beginner`、
`expert-standard` 的配对胜率差分别为 `+5.4% / +5.7% / +0.3%`。
336 个 cohort 均只有一个初始布局摘要；benchmark digest 为
`577e0860e3129cf66f3006f0bda025dbd88594813e64b23310b185938a9bdb13`。

完整边界和后续依赖见
[`V4 改进与开发路线表`](../docs/V4_ROADMAP.md)；V3 封版历史保留在
[`V3 改进与开发路线表`](../docs/V3_ROADMAP.md)。

## V3.2-B 精炼 NPC 发言 M13-A

`app/main.py` 现在把警徽流的结构版本与自然文案分开：`BadgeFlowState.version`、历史记录和 signal ID 继续使用版本号，`build_badge_flow_display_text()`、公开立场卡、移徽推理和 NPC 台词则统一显示“X 号的警徽流 / 我的警徽流”，不把 `v1`、`v2` 念给玩家。

结构化白天发言仍保留目标、公开依据、追问、暂票和改票条件，但使用紧凑的分号句，不再把相同立场完整说三遍。公开 RAG 只引用证据标题；警上模板、身份/验人声明、警徽流分支和女巫建议均缩短。`apply_npc_voice()` 遇到 96 字以上的规则正文不再追加口头禅，结构化 LLM 语气前缀限制为 4–10 字。

非结构化公开 LLM 候选由 `PUBLIC_SPEECH_LLM_MAX_CHARS = 120` 同时约束 prompt 和语义校验，超过预算会重试并最终回退到 Python 规则文本。私聊仍使用原 320 字校验边界，不受本轮公开发言预算影响。规则文本不会为了长度被截断，因此查验、警徽分支、投票和女巫建议等 Python 事实不会丢失。

20 个固定 seed 的 555 条 NPC 规则发言从平均 `158.2` / P95 `225` / 最大 `293` 字，下降到平均 `93.4` / P95 `128` / 最大 `196` 字。同口径 100 seeds 为好人 `37`、狼人 `63`，平均 `3.45` 天；公开措辞仍会作为可观察说服力参与后续判断，因此不把接近的胜负结果描述成逐局 gameplay digest 不变。V3.2-B 封版 simulation 为 v13，因为该轮规范化 schema 与规则契约未升级。

## V3.2-A 智能警徽流 M16-A

`app/main.py` 现在把下一夜查验计划、既有公开金水和死亡后的警徽动作分开建模。`BadgeFlowInput` 只接收下一夜 `primary_target_id`、可选后续 `secondary_target_id`、可选 `claimed_good_anchor_id` 及改流理由；服务端固定将金水分支指向 `primary_target_id`，查杀分支只能指向声明者仍存活的公开金水。未指定锚点时自动选最近公开的合法金水，没有时固定撕徽。公开金水只是该角色此前的验人说法，不读取目标真实身份。

警上竞选和 PK 接口会在任何状态写入前检查投影后的公开身份：首次跳预言家但没有 `badge_flow` 时返回 400，身份声明、发言、日志和发言进度均不改变；已有有效流的 PK 延续发言不强制改流。普通 `DAY_MEETING` 仍允许警下预言家选择首次发布或修改。NPC 真预言家和悍跳狼都通过 `plan_npc_badge_flow_input()` 生成同形公开记录，警上起跳时必须带规范警徽流文本。

第二夜后死亡时，给当夜验人表达该目标“金水”，给既有公开金水或在无金水时撕徽表达该目标“查杀”；只有与对应夜晚和版本精确匹配的动作才生成中立推理。真预言家依法按自己的实际查验选择分支，假预言家只按公开局势构造可错故事。NPC 可信度只评估公开验人、改流理由和实际警徽动作的连续性，不读取真假身份。

Godot 当前行动区的警徽流表单默认折叠；警上输入预言家声明时自动展开并必填，普通白天的公开预言家可按需更新。金水分支只读显示为“给今晚验人”，查杀分支只列出合法公开金水并提供自动最近金水/无金水撕徽选项。

无 HTTP 模拟器同步升级为 `agent_town_simulation.v13` / `agent_town_simulation_batch.v13`：自动玩家若以预言家身份上警，会从未验存活位置中确定性生成合法首版流；PK 已有流时不重复发布。

固定 `20260719–20260818` 的 100 局轻量复验仍为好人 `38`、狼人 `62`，平均局长 `3.44` 天，与 V3.1-O 胜负计数一致。

## V3.1-O 公开票型连续追查与平衡修复

`app/main.py` 新增 `get_public_contested_exile_dissent_focus_id()`。它只读取最近一次公开放逐、公开选票和当前存活状态：放逐目标的未加权票数不超过全部票的 `75%` 时，在存活反对票者中找到投向最集中的公开小团体，并用最小席位号得到唯一焦点；超过 `75%`、没有放逐或没有反对票时返回 `None`。函数不读取被放逐者、投票者或候选者的角色/阵营。

`app/vote_calibration.py` 将普通非警长好人 NPC 的实时策略升级为 `good_exile_cross_day.v1`。原 M15-B 合法候选、五分量、温度、私有预言家知识和失败回退均保留；争议票焦点作为强公开连续性信号进入 `public_influence_utility`，同一反对票阵营的其他席位只获得较弱审查权重。玩家票、警长票、狼人票、警长竞选和胜负结算不消费该策略。

NPC 女巫第二夜及以后也把这个公开焦点放在个人怀疑排序首位；V3.1-L 的 `witch_directive.v1` 采信逻辑随后运行，所以理由合理的压毒或指定毒人仍可覆盖。`fake_seer_campaign.v2` 同时把指定悍跳狼参选概率校准到 `28%–62%`；配对回归继续使用冻结的确定性随机流，避免策略版本升级把同一批 seed 重新抽样。

自动化用一组 `75%` 争议票、超过 `75%` 的压倒性票和隐藏身份互换验证：公开焦点唯一、普通好人概率收敛、女巫默认毒同一焦点，且三者不随隐藏角色/阵营互换变化。simulation 升级为 `agent_town_simulation.v12` / `agent_town_simulation_batch.v12`。

固定 `20260719–20260818` 的 100 局结果为好人 `38`、狼人 `62`，相比 V3.1-N 的 `5/95` 不再畸形；好人误投率 `51.80%`，首放狼人后下一次继续放狼 `28/31`（`90.32%`），对应正确票保持率 `91.57%`；女巫毒狼率 `71.01%`，悍跳参选/当选 `51/39`。这些是真值赛后验收指标，不会倒灌进实时焦点。

## V3.1-N 跨日放逐链 shadow 诊断 M02-D

`app/simulation_metrics.py` 新增 `cross_day_exile_chain.v1`，并把总指标升级为 `agent_town_metrics.v4`。它只在终局后读取真实阵营，实时 `app/main.py`、NPC belief/stance、LLM 上下文和公开 API 均不消费该结果。

每局指标包含：

- 按实际发生顺序保存放逐阵营序列，标记首放狼人及其下一次放逐阵营。
- 只对非玩家好人 NPC 比较相邻两个有票日；同一名仍能投票的 NPC 被归入 `correct_to_correct / correct_to_misvote / misvote_to_correct / misvote_to_misvote` 四类之一。
- `correct_retention_rate` 以此前投狼者为分母；`misvote_correction_rate` 以此前投好人者为分母。无分母时为 `null`。
- “首放狼人”子样本只比较首放当日与下一次实际投票日，并按胜负、后续放逐阵营和同一批 NPC 选票转移单独守恒。

simulation 同步升级为 `agent_town_simulation.v11` / `agent_town_simulation_batch.v11`，CLI 新增 `[EXILE-CHAIN]`。固定 `20260719–20260818` 共 100 个 seed 的身份、胜负、票型、出局与阶段轨迹均和 V3.1-M 一致：好人仍为 5 胜。861 次好人 NPC 跨轮转移中，正确票保持率 24.72%，误投纠正率 33.50%；首放狼人 29 局的下一次放逐为 27 好人、2 狼人，该子样本正确票保持率仅 18.18%。这些是真值赛后评价，不表示 NPC 依法知道被放逐者身份；下一阶段必须从公开票型、本人 stance 和合法新证据构造消费者。

## V3.1-M 真假预言家策略与链路诊断 M02-C

`app/main.py` 现在用两个显式版本的 Python 策略控制 NPC 狼人悍跳，不把选择权交给表达 LLM：

- `fake_seer_campaign.v1` 先按既有 deception、team coordination、leadership 和 logic tuning 选出最强 NPC 狼，再按团队参数形成 `40%–88%` 的参选概率。概率只由对局 seed 和候选席位确定；未命中时 `wolf_fake_seer_id=None`，本局没有指定悍跳狼。
- `fake_seer_check_mix.v1` 先保留既有的高压队友查杀分支，再在低压力队友金水、非狼查杀和非狼金水之间选择。目标只来自狼队依法知道的队友集合、actor 自身怀疑/关系及公开压力；交换两个好人的精确神民身份不得改变结果。

`app/simulation_metrics.py` 升级为 `agent_town_metrics.v3`，新增 post-game-only `seer_claim_balance`。单局记录真假预言家参选、当选、公开起跳、首放/被放逐和四类假验人计数；批量追加参选率、真假预言家当选率，以及悍跳、悍跳当选、假查真预言家、真预言家首放四种条件的胜负守恒。该指标可以在赛后读取真实身份做评价，但不进入 `GameStateResponse`、NPC 上下文或任何实时决策。

simulation 同步升级为 `agent_town_simulation.v10` / `agent_town_simulation_batch.v10`，CLI 写文件时新增 `[SEER]`。同一组 `20260719–20260818` 共 100 个 seed 中，悍跳参选/当选为 76/55，假查杀真预言家 12 局，真预言家首放 27 局，首放好人 71 局，好人误投 67.19%；相比 V3.1-L 的 100/72、31、34、75 和 68.34% 均有改善，好人由 3 胜升至 5 胜。但无悍跳 24 局仅 3 局好人胜，首放狼人 29 局仅 2 局好人胜，说明 5% 仍严重失衡，后续应审计跨日公开证据、站边和连续放逐，而不是继续单调降低悍跳率。

## V3.1-L 女巫策略与失衡诊断 M02-B

`app/main.py` 新增两个严格 schema：公开的 `witch_directive.v1` 只允许 `poison + 单一存活目标` 或不带目标的 `hold`；内部 `witch_strategy_decision.v1` 记录 NPC 女巫最终行动、原因、采信来源和分数。两者都拒绝额外隐藏字段，审计记录不进入 `GameStateResponse` 等进行中 API。

公开正式发言（警上或白天会议）是本阶段唯一建议入口。玩家自由文本只有明确要求女巫毒一个角色，或明确要求压毒时才会生成结构化建议；多目标、含糊表述和对过去用药的身份声明不会被猜测。普通非警长 NPC 可在已经通过合法校验的 `public_speech_plan.v3` 后，由 Python 根据该 NPC 自己的怀疑、公开压力、置信度和 tuning 追加规范句；LLM 不决定建议事实。

NPC 女巫策略按夜晚分层：

- 第一夜若本人被刀，100% 自救；其他合法刀口按内部 seed 以 99% 使用解药；第一夜绝不使用毒药。
- 第二夜及以后，有毒且有合法目标时默认选择本人 `suspicion` 最高的存活角色，公开压力只参与同分排序，不读取角色真值。
- 上一白天的毒人建议按女巫自己的怀疑、公开压力、对建议者的关系、建议者公开说服力和本人 tuning 评分；建议可能来自任何阵营，也可能被接受后毒错。
- 压毒建议必须明确给出“公开信息不足”一类理由并达到独立阈值。第二夜每次合法机会严格守恒为“用毒”或“采信压毒”。

`app/simulation_metrics.py` 升级为 `agent_town_metrics.v2`，新增 `balance_diagnostics`：终局原因、首放阵营/身份、按 cause/camp 的出局数，以及女巫首夜救人、第二夜用毒/压毒、建议数量/采信、毒药目标阵营。simulation 升级为 `agent_town_simulation.v9` / `agent_town_simulation_batch.v9`；`scripts/simulate_games.py` 写文件时额外显示 `[BALANCE]` 和 `[WITCH]`。

seed `20260719–20260818` 的 100 局中，95 局由 NPC 女巫控制：首夜 95 个救人机会全部救下，9 次本人被刀全部自救；第二夜 90 个用毒机会中 67 次用毒、23 次合理压毒。全局 72 次毒药命中狼人 42 次、好人 30 次，狼人命中率 58.33%。但好人仍仅 3 胜，首放好人 75 局、首放预言家 34 局，73 局因狼人控场结束；当前瓶颈仍是白天 belief、真假预言家可信度与放逐链。

## V3.1-K 普通好人放逐概率校准 M15-B

`app/vote_calibration.py` 现在同时承担实时受控策略和离线诊断。`app/main.py` 只在 `phase == "VOTE"`、投票者为存活非玩家好人 NPC、且不是当前警长时调用当前 `good_exile_cross_day.v1`；V3.1-K 的首版为 `good_exile_calibration.v1`。警长竞选票、警长本人的最终归票、`ignore_sheriff_lock` 的归票规划、狼人票、玩家票、结算和胜负都保留原路径；V3.1-O 仅额外让 NPC 女巫消费公开票型焦点。

M15-A 的纯 shadow 契约升级为 `vote_probability_trace.v2`：每份观察使用 `consumer_mode=controlled/shadow` 和 `policy_version` 明确实际消费者。普通好人放逐使用 controlled；警长票、狼人放逐和警长硬归票继续使用 `shadow_vote_baseline.v1`。

每个候选人的 `total_utility` 必须严格等于五项分量之和：

| component | 输入边界 |
| --- | --- |
| `belief_utility` | controlled：Python 维护的 actor 合法怀疑值加 3% 的 `belief_state.v2` 置信修正；shadow：M15-A 席位分数与 reasoning tuning |
| `public_influence_utility` | 公开竞选表现、本人结构化公开立场、警长公开归票 |
| `social_utility` | 该 NPC 自己的目标信任和对警长的信任 |
| `coordination_utility` | 普通好人恒为 0；狼人可使用依法知道的队友、公开狼队故事线和可复现团队策略 |
| `variance_utility` | 由 game seed、阶段、actor、候选人与 tuning 派生的确定性个体读法 |

同一观察还保存 consumer mode、策略版本、softmax 温度、候选概率、Shannon 熵、有效候选数、top 目标，以及实际票的概率、排名和是否命中 top。候选概率必须相加为 1；警长本人已有公开归票目标时使用 `sheriff_nomination` one-hot 硬约束。轨迹不保存 evidence 正文、角色名称、真实阵营或随机 seed，但它仍含角色依法拥有的私有 belief/协同派生值，只能用于本地赛后分析。

controlled 分布把既有合法好人评分器拆回上述分量，加入小幅置信 belief 修正，并在原 softmax 温度上增加 `5.0`。它不改变合法候选；预言家私有金水仍被排除，私有查杀仍可形成高概率共识。若严格构造拒绝输入，实时路径确定性回退到原评分器，保证校准层不能阻断合法选票。

M15-B 当时的 simulation 为 v8，V3.1-L/M/N/O 为 v9/v10/v11/v12；V3.2-A 当时升级为 `agent_town_simulation.v13` / `agent_town_simulation_batch.v13`。批量 `vote_probability_summary.v2` 除投票类型、投票者阵营和交叉维度外，还按 consumer mode 汇总观察/候选数、平均个体熵、top 概率、实际 top 命中率、实际目标概率/排名及五项分量平均绝对值。赛后角色真值只用于评价好人放逐概率质量落在狼人/好人目标上的比例，不会倒灌进候选分布。

M15-A 的 100-seed 基线有 3,264 次观察、23,209 个候选评估；普通好人放逐个体熵为 8.56%，排除警长硬归票后的可比值为 9.01%，好人误投为 64.46%，狼人目标概率质量为 34.76%。M15-B 同 seed 验收有 1,482 次 controlled 观察：个体熵 9.82%、top 概率 93.45%，总体好人误投 63.69%，好人胜场保持 2/100，狼人目标概率质量 36.14%。固定 seed 只用于回归，不是期望胜率。

`VoteCalibrationTraceRecorder` 在 `gameplay_digest` 之后附加结果。命令行用 `--no-vote-calibration-trace` 关闭轨迹；该开关不关闭实时 M15-B 策略，所以 on/off 必须得到相同 digest。它独立于 belief/stance 明细开关，即使使用 `--no-belief-trace` 也能保留小得多的投票诊断。

## V3.1-I / V4.6-B 脱敏 LLM 可观测性 M09-A/B

M09-A 的 v1 追加日志由 V4.6-B 兼容升级为 `llm_observation.v2` 与
`llm_observability_summary.v2`。全局 `LLMClient` 对每个结果最多写一条 request
event：task、`json_text/json_object`、provider/configured model、
`success/fallback`、provider attempt、adapter retry、端到端延迟、usage 覆盖、
billing model 来源、prompt/config digest 和稳定 fallback category。禁用、mock、
未配置仍作为零次 provider 请求的规则 fallback 统计。

`app/main.py` 的语义校验另写 validation event：多次候选最终通过为 `recovered`，
耗尽后使用规则计划为 `fallback`。semantic attempt/retry 独立于 adapter retry；事件
只保存 `schema_invalid`、`hidden_information`、`fact_mismatch`、`continuity` 等类别
计数，原始候选和具体理由不复制到脱敏日志。

日志默认追加到 `data/llm_observability.jsonl`。v2 使用精确字段 allowlist；读取器
继续接受 v1，并在 summary 中报告 legacy 数量。API Key、prompt、上下文、模型响应、
fallback 文本、game/character ID 和原始验证内容都不得进入事件。写文件或汇总失败
不会抛回游戏链路，因此可观测性不能改变 Python 规则或 LLM fallback。

从项目根目录离线汇总并使用默认版本化价格表：

```bash
backend/.venv/bin/python scripts/summarize_llm_observability.py
```

也可用 `--price-catalog` 选择另一份严格 `llm_price_catalog.v1`。summary 包含请求
成功率、adapter/semantic attempt 与 retry、平均/P95/最大延迟、四态 token usage、
prompt/config digest 覆盖、失败类别、`by_task`、`by_provider_model`、
`by_prompt_config` 和 `llm_cost_summary.v1`。provider usage 或有效价格未知时不猜；
总成本保持 `null`，已知部分、原始 token 与未知原因分别保留。

旧 `data/llm_validation_failures.jsonl` 仍保留原始候选用于受限审计，敏感等级高于
脱敏统计文件，不能作为日常指标输出或提供给进行中的客户端。

## V3.1-H 授权私有视角矩阵 M06-B

`app/invariance.py` 现同时提供 `hidden_info_authorization.v1`，其模式为 `role_scoped_private_npc`。M06-A 要求无权普通村民的投影完全相同；M06-B 则声明每个私有事实的 required/allowed actor projection，要求合法观察者至少出现指定变化，同时禁止变化传播给公开视角或其他 NPC。

三个规范案例为：

| authorization kind | 内部变化 | 必须变化 | 允许变化 |
| --- | --- | --- | --- |
| `seer_private_check` | 同一 NPC 预言家的未公开验人由好人目标改为狼人目标 | 该预言家的 belief、decision context | 该预言家全部五层 M04-B 投影 |
| `witch_private_attack` | 女巫依法看到的未公开刀口换为另一个存活目标 | 该女巫的 belief | belief、stance、continuity；decision context 与首夜固定概率 fallback 必须不变 |
| `wolf_team_membership` | 一名非悍跳狼与守卫/猎人交换内部 `role/camp` | 其余狼人的 belief、decision context | 其余狼人全部五层；两个被换身份 actor 不参与对比 |

固定 seed 的实际传播为：预言家五层全部变化；V3.1-L 后女巫变化 belief、stance、continuity 三层，旧的好感救人 fallback 已被首夜 99% 策略替代；其余三名狼人均变化 belief、stance、decision context、continuity，fallback 在该夹具中保持不变。三类案例合计 `158/158` 项满足授权契约，包含每案一个必须不变的玩家公开投影，以及所有角色未变 NPC 的五层策略投影。

矩阵会校验 checked actor 的 `role/camp` 在变体前后相同，required 必须属于 allowed，observer/projection 必须存在且唯一。负对照把预言家的授权故意声明给普通村民，报告必须同时捕获真正预言家的越权变化和普通村民缺失的必需变化。报告不序列化 `WolfGameState` 或 belief evidence 正文，只保留授权类别、计数、摘要和首个差异路径。

M06-B 仍是离线测试模块；实时后端不导入它，模拟 schema、规则结果、LLM 输入和 Godot 均未改变。新增角色私有字段时，应同时声明它允许影响的 observer/layer，并加入该矩阵。

## V3.1-G 隐藏信息不变性矩阵 M06-A

`app/invariance.py` 是离线测试模块，实时 `app/main.py`、API 路由和规则结算不会导入它。它提供两个版本化层次：

- `hidden_info_projection.v1`：普通村民玩家可见的角色/日志/情报/会议/警长/公开信号投影，以及每名普通村民 NPC 的 `belief_state.v2`、`stance_summary.v1`、`NPCDecisionContextV1`、`public_speech_continuity.v1` 和规则 `public_speech_plan.v3` fallback。
- `hidden_info_invariance.v1`：按变体和观察者比较上述投影，只保存 SHA-256 摘要、首个差异路径与守恒计数，不序列化角色真值、阵营、声明内部来源或 belief 正文。

`build_m06a_hidden_variants()` 从同一公开局面生成六个规范样本：改写 `PublicClaimState.source`、替换 `wolf_fake_seer_id`、交换一个 NPC 狼人与一个 NPC 神职的隐藏 `role/camp`、组合身份与内部悍跳标记、注入尚未公布的夜间结算，以及组合全部隐藏变化。公开日志、声明内容、存活状态和已经公布的行动保持不变。

`build_hidden_info_invariance_report()` 只接受普通村民玩家和存活、无警徽的 NPC 村民观察者。固定 seed 自检用 3 名观察者 × 6 个变体，逐个检查 1 个公开投影和 5 个 actor 投影，共 `96/96` 项一致；倒序输入仍产生完全相同的报告。自动化还把公开查验结果从查杀改为金水作为负对照，要求矩阵报告差异，并验证神职/狼人、警长和角色特权玩家均被拒绝。

M06-A 只锁定“无权视角不应变化”。预言家查验、女巫刀口和狼人队友等依法应随隐藏事实变化的私有投影不属于本阶段，留给 M06-B 建立授权正向矩阵。该测试边界不改变 Python 规则事实、现有模拟 schema 或 NPC 玩法。

## V3.1-F 普通白天发言受控消费 M04-B

普通非警长 `DAY_MEETING` 现在是 `stance_summary.v1` 的第一个实时消费者。`app/main.py` 在进入既有结构化发言决策前，用当前 speaker 的单 actor `belief_state.v2` 构造 `public_speech_continuity.v1`；警长发言、警长票、放逐票和夜间/结算路径不调用该入口。

消费边界如下：

- continuity 只含当前 actor 的信任、主次怀疑、暂定票、验证条件、置信度与私有策略可见的 belief evidence ID；随后再和本次 `NPCDecisionContextV1.legal_targets` 求交。好人对未公开目标身份互换保持输入不变，狼人依法知道的队友也不能绕过发言 allowlist。
- 当前实时计划为 `public_speech_plan.v3`，继承 v2 全部策略字段，并要求 `continuity_reason` 和最多三个 `continuity_signal_ids`。旧 `public_speech.v1` / `public_speech_plan.v2` 仍可解析，但进入实时链路后必须由 Python 升级成 v3 再校验。
- `stance_aligned` 必须完全符合摘要的主导承诺；`new_public_evidence` 必须引用同时存在于计划 `signal_ids` 和 continuity 新公开信号 allowlist 的 ID；`deterministic_variance` 只在内部 seed 与 NPC `decision_variance × (1 - plan_consistency)` 门限命中时允许。
- `authorized_claim` 仅随已选择的 allowlisted `claim_option_ids` 使用，声明选项存在但未选择时不能借此改口；`mandatory_rule_response` 仅用于必须回应的公开验人和规则已有的狼队故事线；没有可比目标时使用 `unscored`。
- 规则 fallback 主动对齐 stance。LLM 仍可做合法策略选择并允许判断错误，但未给出合法连续性原因的计划会进入既有重试/回退链。持久化 v3 计划只保存公开 signal ID 和原因，不保存私有 belief evidence ID；表达层仍只收到无事实的短语气任务。

M04-B 当时的离线结果为 v6，M15-A/B 为 v7/v8，V3.1-L/M/N 为 v9/v10/v11，当前 V3.1-O 为 simulation v12，并完整保留 `speech_continuity_metrics.v1`。该统计按上述六类原因守恒，不记录私有证据内容；M04-A 的 `stance_trace` 继续以 shadow 模式观察发言、警长票和放逐票。

seed `20260719–20260818` 的 100 局规则模拟统计 2,163 次受控发言：`stance_aligned=1831`、`authorized_claim=141`、`mandatory_rule_response=139`、`unscored=52`，关闭 LLM 时另外两类为 0。公开发言 `unexplained_change` 从 112 次降到 3 次，整体未解释率为 1.68%；但好人胜率只有 2%，好人误投率为 64.46%。这些数值只证明连续性约束生效，不证明 NPC 判断更准确。

## V3.1-E 统一立场摘要与连续性 shadow M04-A

`app/stance.py` 提供 `stance_summary.v1`。在 M04-A 时它只由离线模拟导入；M04-B 起普通非警长白天发言通过局部导入受控读取单 actor 摘要，而 `StanceTraceRecorder`、警长票、放逐票、夜间技能和规则结算仍保持 `STANCE_MODE="shadow"`。

`ActorStanceSummaryV1` 的输入只有 `belief_state.v2` actor snapshot、公开存活状态和本人当天最新的 `public_position.v1`：

- `trusted_target_ids`：最多两个负向怀疑分目标。
- `primary_suspect_id / secondary_suspect_id`：按怀疑分、置信度和席位号稳定排序。
- `provisional_vote_target_id`：优先保留本人当天公开的结构化暂定票，否则使用当前主怀疑。
- `verification_target_id / verification_condition`：只复制本人当天公开立场卡里的 allowlist 验证条件。
- `confidence / basis_evidence_ids`：所选目标的最高 belief 置信度及排序去重后的合法证据引用。

摘要不保存 actor 的 `role / camp`，不解析 `SpeechState.speech`，也不读取其他 NPC 的私聊。普通好人隐藏身份互换、公开自由文本改写均不得改变摘要；狼人依法拥有的队友 belief 仍可改变自己的内部 stance。

`StanceTraceRecorder` 在每次规则推进前后使用同一组 belief capture：

| alignment | 含义 |
| --- | --- |
| `aligned` | 实际目标符合决定前统一摘要 |
| `explained_change` | 实际目标不同，但自上次本人决定后出现了摘要引用的新合法证据 |
| `unexplained_change` | 实际目标不同，且没有新的摘要证据 ID |
| `unscored` | 决定前没有可比较目标，或发言没有结构化目标 |

对照覆盖 `public_speech / sheriff_vote / exile_vote`。一次决定完成后使用包含该决定公开结果的摘要更新基线，避免把决定自身当成未来变化的理由。分类只用于离线诊断，不证明新证据与改票存在因果，也不在 M04-A 阻止任何合法选择。

M04-A 当时的模拟 schema 为 `agent_town_simulation.v5` / `agent_town_simulation_batch.v5`，M04-B 为 v6，M15-A/B 为 v7/v8，V3.1-L/M/N 为 v9/v10/v11，当前 V3.1-O 为 v12；后续版本继续保留 `stance_trace.changes / observations / final_states` 和批量 `stance_summary`。`--no-stance-trace` 保留 belief 但关闭 stance；`--no-belief-trace` 同时关闭二者，受控发言原因汇总和独立投票校准轨迹仍保留。

seed `20260719–20260818` 的首份 100 局 shadow 诊断包含 6,133 次观察、4,516 次可评分观察和 1,617 次 `unscored`；可评分样本一致率 88.93%，未解释变化率 4.78%。放逐票、公开发言、警长票分别有 62、112、42 次未解释变化；警长票有 661 次因摘要没有信任任何当轮合法候选人而不评分。完整 JSON 约 101MB，不能把这批数值设成硬阈值或直接返回进行中客户端。

## V3.1-D 信念衰减与结构化私聊 M03-B

`app/belief.py` 提供 `belief_state.v2`。轨迹记录仍为 `BELIEF_MODE="shadow"`；M04-B 起只有普通非警长白天发言会为当前 actor 即时构造 belief 并通过 stance 间接消费，技能、警长票、放逐票和胜负规则仍不读取这些分数。

证据权限：

| visibility | 内容 | 可见者 |
| --- | --- | --- |
| `public` | 公开声明、结构化公开立场、警长事件、已经公布的放逐票 | 所有仍有决策权的 NPC |
| `actor_private` | 本人预言家查验、本人女巫看到的刀口、玩家对该 NPC 的结构化有效私聊影响 | `observer_ids` 指定的唯一行动者 |
| `wolf_team` | 狼人依法知道的队友 | `observer_ids` 指定的唯一狼人观察者 |

每个 `SeatBeliefV1` 包含目标席位、`-100–100` 怀疑分、`0–1` 置信度、`trusted / uncertain / suspected` 立场和带权证据引用。`BeliefChangeV1` 记录捕获序号、阶段、前后分数、delta、新增证据、同 ID 权重更新及移除证据；台账始终只追加，跨日衰减写入 `updated_contributions`，不会修改证据含义。

衰减边界：

- `public_role_claim`、公开真假查验说法、`public_position.v1` 立场和低信息发言属于软证据，年龄每增加一天，权重乘以 `PUBLIC_SOFT_EVIDENCE_DAILY_DECAY=0.75`。
- 已公布的警长/放逐票、退水、当选、归票和警徽移交是已观察到的公开动作，不按软发言衰减。
- 预言家查验、女巫刀口、狼队友和结构化私聊是行动者依法持有的私有事实，不使用公开软证据衰减。角色本人面对他人冒认自己的唯一角色时，自知冲突同样不衰减。

私聊边界：

- `PrivateConversationState.belief_influences` 保存 Python 规则实际造成的 `target_id`、`suspect / trust` 与稳定 `evidence_id`，支持一次明确表达影响多个目标。
- 只有 `effective=true` 且实际产生明确怀疑或明确信任的影响才进入台账；指代不明、无明确目标、彩蛋和当日重复追问均为空列表。
- 信念构造不解析 `question` 或 `reply`；自由文本变化不改变证据。该证据仅授权给被私聊 NPC，其他 NPC 和公开视角不可见。

公开证据构造刻意忽略真实角色/阵营、`PublicClaimState.source`、`wolf_fake_seer_id`、未公布 `night_resolutions` 和旧 `CharacterState.suspicion/relationships`。私有真实信息只在对应角色依法拥有时转换成 actor-scoped 证据。NPC 出局后停止吸收新证据，结果保留其最后一份存活时信念并标记 `alive=false`。

模拟 schema 升级为 `agent_town_simulation.v4` / `agent_town_simulation_batch.v4`：

- `belief_trace.evidence_ledger`：去重事实台账，包含 visibility 与合法观察者。
- `belief_trace.changes`：每次席位分数变化及其证据 ID/权重。
- `belief_trace.final_states`：11 名 NPC 的最后信念状态。
- `belief_summary`：批量证据数、变化数、visibility/kind 分布和平均终局置信度。
- `gameplay_digest`：加入信念轨迹前的规则与指标摘要；shadow on/off 必须相同。

M03-A 的 100 局完整轨迹约 46MB，平均每局 116.5 条证据、323.43 次变化，终局平均置信度 33.26%；M03-B 改变信念权重和变化记录格式后，不把这组旧轨迹数冒充新基线。需要大量跑平衡而不分析信念时使用：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 1000 \
  --no-belief-trace \
  --output /tmp/agent-town-simulation-1000.json
```

完整轨迹包含全部 NPC 的合法私有视角，只能作为本地赛后审计文件，不能直接作为进行中对局 API 响应。

## V3.1-B NPC 核心指标 M02-A

`app/simulation_metrics.py` 当前为离线模拟提供 `agent_town_metrics.v5`。入口会拒绝任何非 `GAME_OVER` 状态；该模块不被实时决策链调用，允许在赛后使用真实身份评价已经发生的投票、用毒、真假预言家、跨日放逐链路和模拟玩家表现，但不会把答案倒灌给好人或公开 API。

逐局 `metrics` 包含：

- `sheriff_vote`：按初选/PK 轮次保存票数、目标数、Shannon 熵、归一化熵和有效目标数。
- `exile_vote`：按天保存相同的分散度指标，批量均值以“投票轮次”为样本，不把不同天的候选池混成一轮。
- `good_exile_vote`：好人选票总数、投狼数、投好人数、正确率和误投率；警长 1.5 权重不重复计为多个决策者。
- `fake_seer_acceptance`：指定悍跳狼是否公开起跳/参选/当选、适用的好人警长票支持率，以及公开假查杀出现后好人放逐票的同目标率。后者是相关性代理，不是因果证明。
- `seer_claim_balance`：真假预言家参选、当选、公开起跳、首放/出局，假验人的结果-目标阵营组合，以及批量条件胜负；真实目标阵营只在赛后计数。
- `cross_day_exile_chain`：首放狼人后的条件胜负/下一次放逐阵营，以及非玩家好人 NPC 相邻轮选票的正确保持和误投纠正；只做赛后真值评价。
- `by_voter_role` 和逐日明细，便于区分预言家合法私有查验与普通好人的公开判断表现。

批量 `metrics` 额外提供阵营胜率、平均局长、`by_player_role`、`by_voter_role` 和 `by_day`。所有率都保留计数分子/分母；无样本率为 JSON `null`。归一化票熵定义为 `H / log2(ballot_count)`，范围 `0–1`：全员同投为 0，每票目标都不同时为 1。

100 局基线（seed `20260719–20260818`）为：好人胜率 `6.00%`、平均 `3.42` 天、警长票归一化熵 `28.25%`、放逐票归一化熵 `22.62%`、好人误投率 `60.95%`、假预言家适用好人警长票支持率 `48.29%`、假预言家当选率 `72.00%`。这些是诊断数据，不是平衡目标。

## V3.1-A 可复现模拟基础

V3.1-A 在 V2.0 规则边界上增加了不启动 HTTP 的离线对局驱动：

- `app/main.py` 的每局内部状态持有显式 `random_seed`，所有影响规则结果的随机选择都由该 seed 和阶段上下文稳定派生。
- 正常 `POST /api/game/start` 仍由系统随机源生成 seed，且公开请求 schema 不提供可控 seed 字段、响应也不暴露 seed，防止从 seed 重建隐藏身份。
- `app/simulation.py` 直接调用现有规则函数，以只读取玩家身份、合法私有知识和公开状态的基线玩家策略跑完整局。
- 模拟固定 `enable_llm=false`、`enable_rag=false`，并由 CLI 强制设置 `AGENT_TOWN_DISABLE_VECTOR_RAG=1`；不会发网络请求、加载向量模型、写入居民聊天记忆或启动 FastAPI/Godot。
- 结果使用 `agent_town_simulation.v1`，批量外层使用 `agent_town_simulation_batch.v1`，并记录 `legal_public_baseline.v1` 玩家策略版本。逐局结果移除时间戳和随机 game ID，包含稳定 SHA-256 摘要。

从项目根目录运行 100 个连续 seed：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 100 \
  --output /tmp/agent-town-simulation.json
```

可用 `--player-role` 固定模拟玩家身份，可选 `werewolf / seer / witch / hunter / guard / villager`；默认 `random`。相同代码、配置、策略版本和 seed 必须生成完全相同的逐局 JSON。V3.1-B 已在这份原始审计结果上增加版本化指标。

## V2.0 后端封版与 V3 交接

V2.0 基线来自 [`Agent Town Demo V2.0`](https://github.com/KEswy/agent-town-demo-v2.0) 的提交 `6af73f54844b4e1471c6d9fb582431a7ee892592`。稳定边界继续保持：Python 规则引擎唯一决定身份、合法知识、技能、警徽、票型结算、出局与胜负；LLM 只能消费规则整理后的上下文，并在结构化白名单或安全表达契约内输出。

进入 V3 时的历史限制包括进程内对局、缺少价格/配置指纹和仅覆盖普通好人放逐票
的校准。V4.3-A/B 已补齐持久化与幂等结算，V4.6-B 已补齐版本化价格、Prompt/config
摘要和只读 artifact 对比；当前 A/B 仍只评价规则模板 artifact，不代表真实 LLM 或
Prompt 效果，M15-B 也仍未建立自动平衡阈值。

V3.1-O 已用公开票型消费者把固定 100 局好人胜场从 5 提升到 38，并通过隐藏身份互换锁住普通好人放逐和女巫用毒边界。V4.1-A/B 进一步提供三档玩家、身份配对基准和玩家发言提交前预览；V4.2 已完成规则事件链和规则模板执行式重放，V4.3-A/B 已完成原子存档、恢复和幂等重复结算保护，V4.4-A/B 已完成统一公开证据、承诺生命周期和中立矛盾候选，V4.5-A 已完成终局决定解释与五类错误归因，V4.6-A/B 已完成 NPC 公开发言质量基线、完整/生效配置指纹、保守 LLM 成本口径和规则 artifact 配对 A/B，V4.7-A/B 已完成客户端首局安全引导、`compact / default / wide` 响应式布局、整局键盘焦点、字体与对比度检查，V4.7-C 已完成 Python 3.12 + Godot 4.7.1 双平台 CI、分层 smoke 和源码封版清单，V4.8-A 已完成开局 `enable_llm_validation` 输出校验选择、5 轮校验/0 次校验原文直出、事件封印和旧存档兼容。公开开发仓库和首次开发快照已获批准，但项目仍尚未封版；最终 commit、许可证状态、`v4.0.0` tag 与正式封版 push 必须按 [`V4 封版清单`](../docs/V4_RELEASE_CHECKLIST.md) 单独批准。V4 完整拆分见 [`V4 改进与开发路线表`](../docs/V4_ROADMAP.md)，V3.1 至 V3.2-B 的封版实施状态见 [`V3 改进与开发路线表`](../docs/V3_ROADMAP.md)。

## 运行

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：`http://127.0.0.1:8000/docs`

V4.3-A 当前只支持一个 uvicorn worker；不要增加 `--workers`，也不要运行多个指向
同一存档目录的后端进程。默认私有存档目录是 `backend/data/games/`；从
`backend/` 启动时可在 `.env` 设置 `AGENT_TOWN_GAME_SAVE_DIR=data/games`。

第一次知识检索会懒加载 `BAAI/bge-small-zh-v1.5`，模型约 90MB。FastEmbed 或模型不可用时，接口会自动使用关键词检索。

## LLM API

`app/llm.py` 已经实现 `mock` 和 OpenAI-compatible provider。普通非警长 `DAY_MEETING` NPC 发言使用结构化决策；警上、警长和对局私聊等既有路径继续使用安全改写，默认关闭。坏坏和然然的普通 `/chat` 独立使用全局 LLM 配置，不依赖某一局狼人杀的 `enable_llm`。

```bash
cp .env.example .env
```

以当前使用的 DeepSeek 为例：

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的_DEEPSEEK_API_KEY
LLM_MODEL=deepseek-v4-flash
```

不要使用即将弃用的 `deepseek-chat` 或 `deepseek-reasoner` 别名，本项目直接使用 `deepseek-v4-flash`。

也可以使用以下配置组合：

| Provider | `LLM_BASE_URL` | 示例 `LLM_MODEL` |
| --- | --- | --- |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-20b` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-3.5-flash` |
| OpenRouter | `https://openrouter.ai/api/v1` | `openrouter/free` |

修改 `.env` 后需要重启后端。`GET /api/llm/status` 用于检查启用状态、provider、模型、
配置完整性和安全的 `config_fingerprint`，不会返回 API Key。

当前 DeepSeek 可靠性设置：

```dotenv
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=0.35
```

- DeepSeek 请求使用非思考模式和 `json_object` 输出，避免思考内容占用短回答预算或返回格式漂移。
- 默认调用遇到超时、限流、临时服务错误、空内容和坏 JSON 时按
  `LLM_MAX_RETRIES` 重试；V4.8-A 原文直出路径固定只请求 1 次。
- 以下语义比对、归一和拒绝描述只适用于“输出校验开启”；关闭校验时仅保留 JSON 与非空 `text` 传输解析，提取后的原文直接显示。
- 输出校验开启时，返回文本按“声明者 → 目标 → 结果”比对验人，并校验自称身份、女巫/守卫技能行动及信息权限；引用已公开的他人验人不会被算成当前角色新增验人。
- “我验了4号”会被视为预言家起跳；“我是预言家 / 我起跳预言家”“好人 / 金水”等自然同义改写不需要与规则模板逐字一致。
- “我拿的是村民牌”“7号，查杀”等省略表达，以及“4号起跳预言家，验了7号”这种逗号后延续主语的转述会被归一到结构化事实；并列引用他人的阵营判断不会算成当前 NPC 的直接断言。
- 普通白天的结构化 `intent` 直接用于规则状态更新，表达层不再要求命中固定意图关键词；“不足以直接定性”“回答我的问题”等自然同义说法可以保留。公开的“4号是狼/好人”和“我是好人”按可错观点处理，不会与角色表中的真实阵营比对；第一人称“我是狼”只有规则声明已授权时才可通过。
- 输出校验开启时，“狼队友”不再是关键词黑名单：条件推理、双狼猜测、他人转述、反问、否定和普通“我的队友”可以通过；未经授权的“3号是我的狼队友”“我们狼队”等第一人称明确狼队关系仍会拒绝。篡改目标或结果、凭空增加查验/技能事实、断言未公开神职或明确自曝隐藏狼队时，会携带全部结构化校验原因继续纠正，最多产生 5 份候选。
- 开启校验的候选达到 5 轮上限仍失败后使用规则模板；所有被拒绝的原始返回都会写入 `data/llm_validation_failures.jsonl`，即使后续轮次成功也保留恢复记录。关闭校验时原文直接显示，不创建 validation failure。
- 新日志带 UTC `recorded_at` 与 `validator_version`，用于区分旧版本记录和当前 `semantic-v3` 校验行为。
- 进行中的对局只返回失败原因和统一脱敏占位，不返回被拒绝的 DeepSeek 原文；是否脱敏只取决于失败类型，不会查询原文提到的角色是否真狼。服务端 JSONL 和 `GAME_OVER` 后的复盘仍保留完整原文。

结构化公开发言计划 v3（兼容 v1/v2 输入）：

- 本节的两段 LLM 决策与严格拒绝流程适用于输出校验开启；关闭时 Python 直接使用合法规则计划，只调用一次最终表达。
- `app/npc_decision.py` 定义严格的 `npc_decision_context.v1`、`public_speech_continuity.v1` 与 `public_speech_plan.v3`。普通非警长 `DAY_MEETING` 使用“决策层 → 语气层”两次调用；旧 v1/v2 输入会先升级为 v3，再经过相同连续性校验。
- 每次决策都整理当前 NPC 的真实身份、阵营、性格、合法知识、近期公开日志、自身私有记忆、阶段、合法目标、声明事实包、带可见性的证据和公开动作信号。`decision_signals` 覆盖上警/不上警、退水/继续竞选、警长票与警徽结果、公开验人说法、上一天放逐票、已公布出局和保守的低信息量评价；验人信号只表示“某人公开这样说过”，不包含内部 `source` 或真假答案，夜间来源与仍待公布的首夜结果也不会进入公开投影。
- 第一段只能返回扁平策略 JSON，不得包含 `text` 或 `fields` 包装。提示中的 `output_contract` 会给出根级必填键和完整 `flat_json_example`，所有字段都必须直接出现在根级，可空项也必须显式写 `null`。后端只展开键恰好为 `schema_version + fields` 的 v2/v3 包装；额外顶层键和展开后的额外内层键仍会被严格拒绝：

| 字段 | 含义与边界 |
| --- | --- |
| `schema_version` | 当前固定为 `public_speech_plan.v3`；v1/v2 仅作为兼容输入 |
| `intent` | 从本次 `allowed_intents` 选择 `observe / pressure / defend / counterclaim / reveal` |
| `primary_target_id` / `secondary_target_id` | 主判断位与对照位；只能来自 `legal_targets`，且不能相同 |
| `stance` / `stance_target_id` | `support / oppose / undecided` 及其对象；对象必须是已选主次目标，`undecided` 必须配 `null` |
| `confidence` | `0–100` 的整数，仅表达当前把握，不会覆盖规则事实 |
| `signal_read` | 对已选公开动作的白名单解读；选择信号时不能填 `none`，没有信号时必须填 `none` |
| `question` | `null` 或 `{target_id, topic}`；目标必须是主次目标，topic 只能从追问白名单选择 |
| `verification` | `null` 或 `{target_id, criterion}`；指定之后用发言一致性、票型、回应、公开结果等哪项事实复核 |
| `provisional_vote_target_id` | `null` 或当天合法暂定票；不能投自己正在支持的对象 |
| `tactic` | 从通用或狼人战术白名单选择；`wolf_*` 仅狼人可用，队友战术还必须指向上下文允许的狼队友 |
| `claim_option_ids` / `evidence_ids` / `signal_ids` | 各最多三项、不得重复，只能选本次 allowlist；声明包不可拆，证据必须是 public，动作信号要与所选目标相关 |
| `continuity_reason` / `continuity_signal_ids` | 必须说明沿用、公开新证据、确定性扰动、合法声明、规则强制回应或无可评分立场；持久化 ID 只能来自公开 signal |

- `signal_read` 可选 `raises_suspicion / reduces_suspicion / needs_explanation / uncertain / mixed / none`。
- `question.topic` 可选 `claim_basis / action_motive / stance / vote_intent / timeline / contradiction / role_result / response_to_pressure`；`verification.criterion` 可选 `next_speech_consistency / claim_consistency / vote_alignment / response_quality / role_result / night_result / badge_action / follow_up_action`。
- 通用 `tactic` 包括 `information_probe / action_audit / direct_pressure / conditional_defense / consistency_check / vote_test / role_reveal / role_counterclaim`；狼人额外可选 `wolf_distance_teammate / wolf_bus_teammate / wolf_fake_check_teammate / wolf_rescue_teammate / wolf_frame_good / wolf_counterpush_good / wolf_fake_seer / wolf_deep_cover / wolf_misdirection`。

- `observe / pressure / defend` 必须有具体主目标；在存在公开信息时，还必须选择至少一项公开信号、公开证据或合法声明。施压/对跳必须反对主目标，辩护必须支持主目标；未知枚举、额外字段、字符串数字 ID、越权/重复 ID、互相矛盾的目标与战术都会被拒绝。
- 如果当天有人公开给当前 NPC 发金水或查杀，上下文会额外提供 `response_requirements`：计划必须选中对应 `seer_check_claim` 信号，并把声明者放进主目标或次目标。收到查杀时必须质疑或反对来源；收到金水时可以支持、保留或质疑，但不能把“自己确实是好人”推导成“对方一定是真预言家”。规则回退也遵守同一要求。
- 私有知识和完整公开历史只进入第一段决策，可影响“NPC 相信什么”，但不能作为公开证据。计划通过后，第二段只拿人物口吻和阶段，返回 4–18 个中文字符、不含座位号、身份、动作或票型事实的语气前缀；不会收到真实身份、狼队、夜间记忆、私聊原文、计划内容、未选信息、私有战术名或第一段 raw output。
- 输出校验开启时，Python 把已校验计划渲染成包含判断、问题、验证点和暂定票的规则正文，再拼接语气前缀。正文可以体现错误判断，也允许好人被狼人的公开叙事骗到，但 LLM 无法反转计划或伪造动作、身份、查验、技能、出局和胜负事实；“没信息，过”不会成为正式发言。
- 通过校验的计划保存在当天 `SpeechState.decision_plan`。普通好人的警长票和放逐票只综合怀疑、公开压力、关系、公开声明可信度、警长归票、公开查杀、计划暂定票与本局参数，不读取候选人的真实 `role/camp`；因此可以选中假预言家、在真假预言家间分票或投出真预言家。真预言家自己的查验和狼人的队友知识仍属于各自合法私有信息。`plan_consistency` 只给暂定票加权，后续公开证据仍能推翻，旧日期计划不会复用。
- 决策与表达都读取本局 `enable_llm_validation`：默认分别最多纠正 5 轮；关闭时不调用 LLM 结构化决策，Python 先选合法计划，再请求 1 份最终表达并进行 0 次语义校验。未经校验的显示文本不会回写权威 `public_claims`、`public_position`、怀疑值或技能建议。
- 输出校验开启时，只有普通非警长 `DAY_MEETING` 进入 v3 决策层并消费 stance；警上、警长、夜间、投票和私聊保持原规则决策边界，LLM 只做已批准内容的角色化改写。关闭校验时所有这些可见表达都可能偏离提示，但仍不成为权威规则输入。

### 本轮决策契约（已完成）

下列小里程碑已经实现，并通过完整自动化回归：

- `public_position.v1` 是发言完成后的公开精炼立场卡，覆盖信任、不信/怀疑、暂定票、追问和改票条件。后续公开 RAG、决策和发言只引用这个摘要，不把长段 `text` 重新送入决策层，也不读取只对行动者开放的 `decision_plan`；否定句按对象解析，避免“不怀疑 / 不会投”被反向记录。
- 警徽流使用追加版本，每版包含声明者、版本号、发布日、`effective_night_day`、下一夜目标、后续顺验、合法公开金水锚点和公开改流理由。金水分支固定给当夜目标，查杀分支给锚点或撕徽。场上形势变化时可以换流；“改变警徽流”本身的可信度调整为零，只评估理由是否可由公开状态验证、前后叙事是否冲突。真预言家夜间选择只对当夜有效版本做软参考，不强制锁定查验。
- 警徽移交/撕毁只能对命中的明确分支生成中立推理，例如“按 4 号自己的警徽流，此次移徽表达其声称 7 号为金水”。这是公开角色声明，不是规则验真；普通角色只因“没接徽”不会被推定为好人或狼人。
- 玩家警上同次跳预言家+发布首版警徽流会先归一化最终公开身份并整体校验，缺失流时整次拒绝；警下首次发布和后续调整通过 Godot 折叠 UI 可选提交。Python 始终用结构化字段计算警徽分支并替换冲突自由文本，事实型换流理由必须能由公开记录验证。警长当选、移徽或撕徽后，服务端 `sheriff` 投影与玩家/NPC 头顶警长标识保持一致。
- 警长票和放逐票的普通好人评分只读取公开表现、个人关系/怀疑和该角色的合法私有知识，不读候选人隐藏 `role/camp`。服务端对所有合法候选做可复现的概率抽样；强证据允许自然共识，不强制分票，也不强制按真实阵营站边。
- 狼队的集中、分票、倒钩、救援、卖狼和切割作为公开局势与 `team_coordination` 等参数驱动的软策略，通过评分倾向而不是直接 `return` 固定票。已公开“狼查杀狼”后的反对与投票/警徽一致性仍是硬约束。
- Python 规则引擎仍是身份、知识权限、行动、票型结算、出局和胜负的唯一事实源；LLM 可以选策略、做可错判断和生成台词，但不定规则、不执行票型和胜负。

填入 Key 后，可以先在项目根目录发送一次小请求验证连接，不需要启动后端：

```bash
backend/.venv/bin/python scripts/check_llm_connection.py
```

- Godot 开始游戏时勾选“启用 LLM”，才会为该局启用生成；全局环境变量与单局开关必须同时开启。
- 配置只从 `.env` 或环境变量读取，不提交真实 API Key。
- LLM 只接收当前行动角色有权知道的状态；私有知识可用于策略，但不能作为公开证据或进入公开文本。
- 规则代码生成合法目标和声明事实；普通白天 LLM 只能在白名单内选择。夜晚行动、投票、身份、出局和胜负仍完全由规则代码处理。
- 请求失败、超时、无效 JSON、替换字符或缺少非空 `text` 时，自动退回当前模板逻辑；输出校验开启时语义越界也会回退，关闭时语义越界原文直接显示。

## 狼人杀状态机

```text
NIGHT → SHERIFF_SIGNUP → SHERIFF_SPEECH → SHERIFF_WITHDRAWAL（第一天）
  → SHERIFF_VOTE → SHERIFF_RUNOFF_SPEECH/VOTE（平票时至多一次）
  → 首夜结果公布 → HUNTER_SHOT（可选）→ BADGE_TRANSFER（可选）
  → MEETING_ORDER → DAY_MEETING → SHERIFF_NOMINATION（玩家警长时）
  → FREE_ACTIVITY → VOTE → HUNTER_SHOT（可选）
  → BADGE_TRANSFER（警长出局时）→ NIGHT / GAME_OVER
```

- `NIGHT`：狼人、预言家、女巫和守卫执行身份行动。
- `HUNTER_SHOT`：玩家猎人因狼袭或放逐出局后选择开枪目标或不开枪；被毒出局不能开枪。
- `SHERIFF_SIGNUP`：第一天玩家选择是否上警，NPC 同步形成候选人列表。
- `SHERIFF_SPEECH`：候选人按随机顺序发言；NPC 真预言家必须报出真实验人。
- `SHERIFF_WITHDRAWAL`：候选玩家通过独立按钮明确继续或退水；玩家未上警时由后端直接结算 NPC 选择，不要求玩家代为推进。
- `SHERIFF_VOTE`：警下角色同时投票；最高票平局时只进行一次 PK 发言和重投。
- 首夜结果公布：竞选全部结束后才执行狼刀、解药、毒药和守卫结果；后续夜晚不延迟。
- `MEETING_ORDER`：警长选择出局左/右或警左/右，没有警长时使用随机首位和方向。
- `DAY_MEETING`：存活角色逐个公开发言；有夜间出局锚点时警长按自然座次发言，并可提出暂时归票。
- `SHERIFF_NOMINATION`：全员发言后，玩家警长维持或调整最终归票，自己的正式投票随之锁定。
- `FREE_ACTIVITY`：走近存活 NPC 私密追问，每名 NPC 每天第一次追问会影响决策。
- `VOTE`：玩家提交目标和理由后，全部票同时产生并立即结算。
- `BADGE_TRANSFER`：警长出局后移交或撕毁警徽；若同时触发猎人，先完成开枪。

固定 12 人身份池为狼人 x4、预言家 x1、女巫 x1、猎人 x1、守卫 x1、村民 x4。固定座次为：玩家、梅西、C罗、周深、梅长苏、塞尔达、小骑士、大黄蜂、喜羊羊、懒羊羊、洛洛、奇异博士。`POST /api/game/start` 默认随机身份，也接受 `player_role` 指定玩家身份用于测试；服务端会从原身份池中取出该身份后再随机其余 11 人。

玩家是狼人时会在私有状态和角色卡中看到三名狼队友，NPC 狼人也会在内部关系中互认。玩家狼人提交的夜袭目标拥有最终决定权；全为 NPC 狼人时按多数目标结算。狼人公开计划可以选择深水伪装、误导、框好人、反推好人、救援队友、与队友拉开距离或在高公开压力下卖队友；队友关系只用于私有策略，不能被写进公开依据。

好人不是“读取答案”的完美机器人。公开预言家故事的可信度由声明是否完整、候选人实际说出的警上内容、听者关系与 `deception_susceptibility`、`social_susceptibility`、`reasoning_skill` 共同计算，不会先看声明者究竟是真预言家还是狼人。候选人的固定性格只保留很小的表达先验，玩家和 NPC 的同质量警上发言按同一套可观察标准评分；信任相同时也不再因为声明先后顺序让所有好人统一惩罚同一个人。

每名听者还会对同一份公开表现产生可复现的个体解读；分数接近时，`decision_variance` 允许选择次优合法目标，因此自然票型可以分开。收到金水只会带来有限、因人而异的正向影响，不是锁票或验真器；收到查杀则形成直接冲突并显著降低对来源的警长支持。真预言家若已有与公开查杀相反的自身查验，可以依据这项合法私有知识拒绝受骗。所有扰动都由对局状态确定，方便复现和测试，不会把错票变成完全无依据的随机投票。

第一天 NPC 真预言家必定上警并公布真实查验；玩家预言家可以不上警，也不强制公开真实信息。指定悍跳狼会根据玩家狼人的警上发言选择让跳、继续悍跳或退水，少数高策略局面允许双狼起跳。狼队可以发队友金水，并在高公开压力且局势允许时全局至多一次“狼查杀狼”。一旦这个查杀公开，被查杀的狼人就进入硬叙事约束：警长票不得再支持查杀来源，后续发言和放逐票必须反对来源；若查杀来源成为警长，移交警徽时也不会选择被它查杀的队友。该约束优先于一般狼队抱团评分。

参加过竞选的所有角色都不能投警长票，退水者仍保留竞选参与记录并继续禁投。首夜待公布角色在竞选期间仍视为存活，不会通过公开状态、日志或 RAG 泄露结果。

警下 NPC 的票仍由 Python 规则层一次结算，但输入只包含合法公开信息和该 NPC 的个体参数：关系、怀疑、实际警上发言质量、公开身份/验人故事、本人是否收到该候选人的金水或查杀，以及确定性的个体差异。候选人的隐藏 `role/camp` 不参与好人评分；交换两个候选人的后台身份而保持公开桌面不变时，好人的候选分数也必须保持不变。

前夜有人出局时，警长选择出局左或出局右后按自身座位自然进入发言顺序；前夜无人出局时，选择警左或警右并自然最后发言。警长在自身轮次可以提出 `temporary_nomination_target_id`，后续 NPC 会把它作为公开判断因素；全员发言后再产生 `nomination_target_id`，可以维持或调整。

警长白天拥有 1.5 票。最终归票表示其正式投票目标，服务端会拒绝警长投给其他角色；其他角色只受到归票影响而不会被强制跟票。警长出局后可以移交或撕毁警徽。

女巫每局各有一瓶解药和毒药，每晚最多使用一瓶，仅第一夜可以自救；同一刀口被守卫和解药同时保护仍会出局。守卫不能连续两晚守同一目标。全部狼人出局则好人获胜；全部村民、全部神职出局，或存活狼人数不少于存活好人数形成控场时，狼人获胜。可开枪猎人因狼袭或放逐出局时先结算猎人技能，再检查控场。

正式出局记录包含 `source_action`、`source_actor_ids` 和 `source_target_id`。规则引擎会验证来源与本轮狼刀、毒药、猎人开枪或投票是否匹配，拒绝无来源、过期目标或目标不一致的出局。

## 狼人杀接口

- `GET /api/health`
- `GET /api/llm/status`
- `GET /api/rag/status`
- `POST /api/game/start`
- `POST /api/game/{game_id}/save`
- `POST /api/game/{game_id}/restore`
- `GET /api/game/recovery-status`
- `GET /api/game/{game_id}/state`
- `GET /api/game/{game_id}/summary`
- `GET /api/game/{game_id}/events`
- `POST /api/game/{game_id}/replay`
- `POST /api/night/action`
- `POST /api/night/resolve`
- `POST /api/hunter/shot`
- `POST /api/sheriff/signup`
- `POST /api/sheriff/player-speech`
- `POST /api/sheriff/npc-speech`
- `POST /api/sheriff/withdraw`
- `POST /api/sheriff/vote`
- `POST /api/sheriff/meeting-order`
- `POST /api/sheriff/nominate`
- `POST /api/sheriff/transfer`
- `POST /api/day/player-speech`
- `POST /api/day/npc-speech`
- `POST /api/day/npc-speeches`
- `POST /api/day/private-chat`
- `POST /api/day/end-free-activity`
- `POST /api/vote/submit-and-resolve`

旧的 `POST /api/vote/npc-decisions`、`POST /api/vote/player` 与 `POST /api/vote/resolve` 仍保留兼容，但 Godot 主流程只调用同步结算接口。

上述开局后的规则写接口（含兼容的批量 NPC 发言和三段投票接口）都可在 JSON body
携带 `idempotency_key`；相同 key 只能绑定同一端点和同一 payload。`game/start`、
查询、preview、save/restore 与 replay 不使用该字段。

`GET /api/game/{game_id}/state` 的 `meeting` 字段包含：

- `direction`：`clockwise` 或 `counterclockwise`。
- `order`：当天所有存活角色的发言顺序。
- `current_speaker_id`：当前允许发言的角色。
- `current_position` 与 `total_speakers`：会议进度。
- `completed`：会议是否完成。

同一响应的 `sheriff` 字段包含完整候选人、活跃候选人、退水名单、当前竞选发言者、轮次、投票资格及原因、可投目标、警长、发言锚点、暂时归票和最终归票目标。角色视图的 `sheriff_campaign_status` 为 `candidate`、`withdrawn`、`pk` 或空字符串，供 Godot 显示头顶标记。

同一响应的 `player_private_info.action_history` 是只对玩家可见的本局累计记录，包含夜间技能与结算结果、猎人开枪、警上操作、完整公开发言、私聊问题、首次触发彩蛋及放逐投票；新游戏使用新的状态数组，因此记录自动清空。

同一响应的 `public_intel` 是左上角关键公开信息面板使用的安全投影，包含日期、公开类型、声明者、可选目标、公开结果和中立显示文本。预言家验人、女巫救毒和守卫成功均使用“称/声称”措辞；猎人开枪属于规则已向全场确认的公开动作。该投影刻意不包含 `PublicClaimState.source`、真假标记、真实身份/阵营、狼刀、真实守护或女巫用药结算，因此真假声明在前端具有相同结构。

同一响应的 `public_evidence_timeline` 是 V4.4-A 统一公开证据；
`public_evidence_analysis` 是 V4.4-B 只读关系层。后者的 commitment/candidate 都
引用时间线 evidence ID，并固定 `judgment=none`；它们可以供玩家和 NPC 核对公开
前后关系，但不能当作角色真值、狼人概率或 Python 规则判定。

服务端会验证发言者。玩家和 NPC 都不能跳过顺序，也不能在同一天重复正式发言。

NPC 正式发言会检索知识库和当前已经发生的公开发言。返回的 `speech` 包含 `evidence_titles` 和 `retrieval_mode`；普通白天结构化决策只能引用自己选择且标记为公开的证据与规则投影的公开动作信号。若 NPC 当天被公开发金水或查杀，它的首轮白天发言必须回应该说法；若警长票投给了别人，规则正文会同时说明这张票，避免角色收到金水后完全失忆。

公开发言会解析并记录身份与验人声明。真预言家可以公布实际查验；每局指定一名 NPC 狼人作为悍跳候选，可以起跳预言家并维护跨轮假验人记录；女巫、守卫和猎人也会根据已知信息、公开压力与性格决定是否公开技能信息。公共状态返回角色卡使用的中立 `public_claims` 标签和左上角面板使用的完整安全 `public_intel` 列表，两者都不标记真假。

`config/npc_profiles.json` 中的 `speech_style`、`catchphrases`、`easter_eggs` 和 `trigger_easter_eggs` 控制角色化表达。触发彩蛋只在 `FREE_ACTIVITY` 私聊中匹配，忽略大小写、空格和标点；每名狼人杀 NPC 当前配置一个关键词彩蛋。输出校验开启时，规则文本和 LLM 输出必须保留已选择公开声明中的身份、目标、结果与技能行动；校验器按事实而非模板字面判断，姓名、座位号、“好人/金水”等同义词和合法私聊代词会归一到同一事实。候选达到 5 轮上限仍失败时，响应返回 `llm_validation_failure`；关闭校验时不生成该失败视图，原文直接显示但不成为权威规则字段。

`POST /api/day/private-chat` 只允许在 `FREE_ACTIVITY` 使用。私聊不会写入 `public_logs`；同一 NPC 当天只有第一次普通提问会修改怀疑、信任和内部记忆，后续追问只返回回答。关键词彩蛋不消耗这次有效提问，首次发现会写入玩家私密行动记录。

梅长苏的 `mei_changsu_lin_shu` 彩蛋是当前唯一允许透露真实游戏身份的触发项。输出校验开启时，后端把实际身份作为 `required_self_role` 写入 LLM 校验契约；回复遗漏身份、改成其他身份、增加其他角色身份或泄露狼队友时会拒绝，最终规则回退保留正确身份。关闭校验时彩蛋文本同样原文直出，Python 仍单独记录真实彩蛋状态。

私聊回复使用当前会话视角：NPC 以“我”自称、称玩家为“你”，其他角色显示“号码 + 名字”。玩家消息里的“我/自己”映射到玩家，“你”映射到当前 NPC；无法从本句或同一 NPC 最近私聊中解析的“他/她/TA”会触发澄清，并且不消耗当天的有效追问次数。

`GET /api/game/{game_id}/summary` 只允许在 `GAME_OVER` 后调用，返回：

- 获胜阵营和总天数。
- 每名角色的真实身份、阵营、胜负、生存结果和关联行动。
- 按阶段排序的全局时间线，包括夜间技能、查验、实际挡刀、公开身份声明、发言、完整私聊、投票理由和出局结果。
- `post_game_explainable_review.v1`：四类已保存决定的当时依据、跨日公开证据、
  明确标注的赛后真值、评价计数和五类错误归因。
- 本局全部 LLM 校验失败记录；赛后响应包含未脱敏的原始返回。

## 小镇 NPC 接口

- `GET /health`
- `GET /npcs`
- `GET /knowledge`
- `GET /knowledge/search`
- `POST /chat`
- `GET /memory/{player_id}/{npc_name}`
- `DELETE /memory/{player_id}/{npc_name}`
- `DELETE /memory/{player_id}`
- `DELETE /memory`
- `POST /admin/reload-config`

坏坏和然然是常驻居民，只存在 NPC 配置和普通 `/chat`，不在 `NPC_NAMES`、十二人角色列表或规则状态中。她们在所有狼人杀阶段都可以聊天，但不能行动、竞选、正式发言、投票或获知隐藏身份。

当前人物设定中，坏坏是点心屋的嫩绿色小恐龙，然然是心情邮局的黑白熊猫邮差。物种、服饰和习惯写入 `npc_profiles.json` 的 `role / personality / speech_style / knowledge`，会随普通聊天上下文交给 DeepSeek；规则兜底回复也保留少量尾巴、邮差包等角色细节，但不会让造型设定越过狼人杀知识边界。

两名居民的 `/chat` 会整理人物性格、说话风格、当前昼夜/游戏阶段、当前问题、命中知识、关系阶段和最近 8 轮同一玩家/同一居民的历史，以严格 JSON `{"text": "..."}` 请求全局 DeepSeek。校验只处理空文本、长度、乱码和明显的提示词/密钥泄露，不使用狼人杀身份与目标语义规则拦截自然聊天。网络请求在 `MEMORY_LOCK` 外执行。

`ChatResponse` 返回 `llm_used`、`llm_provider` 和 `llm_fallback_reason`。禁用、mock、未配置、超时、限流、JSON 异常或轻量校验失败时，服务端使用对应居民的自然规则回复，并照常保存本轮记忆。

普通聊天完整历史保存在 `data/memory.json`，按 `player_id::npc_name` 隔离并可跨后端重启读取；只有最近 8 轮进入 LLM 上下文。狼人杀的身份、关系、私有记忆和 `private_conversations` 存在活动 `GAME_STORE` 以及 `data/games/*.json` 私有完整存档中；合法未完成局会在真实服务重启时恢复。两类记忆不会混用，狼人杀存档也不会进入公开对话上下文。

`POST /admin/reload-config` 会先完整校验、再原子替换人设、知识库和 NPC 智能参数。任何文件无效时返回 `400` 并保留整套旧配置；存在可恢复的未完成局时返回 `409`，避免其冻结恢复指纹与运行配置分叉。响应中的 `tuning_schema_version` 为 `npc_tuning.v1`，`applies_to` 为 `new_games`。智能参数在创建角色时写入本局快照，所以重载只影响之后创建的新对局。修改 `.env` 中的 API Key、provider 或模型后仍需手动重启后端，且本项目不会自动启动后端。

## 配置

- `config/npc_profiles.json`：15 名 NPC 的人设与基础知识；11 名参赛 NPC 保留角色化和彩蛋配置，坏坏和然然使用 `use_llm_for_chat` 开启常驻聊天生成。
- `config/knowledge_base.json`：111 条静态知识，包括开发资料、十二人狼人杀规则、完整警长规则、身份声明规则、11 名参赛 NPC 的判断风格和 4 条常驻居民专属知识。
- `config/npc_tuning.json`：11 名参赛 NPC 的版本化智能参数；不包含玩家、坏坏或然然。
- `data/memory.json`：运行时普通对话记忆。
- `data/games/*.json`：V4.3-A 完整私有对局存档，包含隐藏信息且不会提交 Git。
- `AGENT_TOWN_GAME_SAVE_DIR`：覆盖存档目录；`.env.example` 默认写为 `data/games`。

### NPC 智能参数

`config/npc_tuning.json` 使用严格 schema `npc_tuning.v1`。覆盖优先级为：

```text
global_defaults < factions.good / factions.werewolf < roles.<role> < npcs.<name>
```

后一级只覆盖它明确填写的字段。例如村民先继承全局值，再叠加好人阵营和村民身份值，最后叠加对应 NPC 的个人值。未知顶层/参数字段、范围外数值、拼错的 NPC 名称，以及身份与阵营不匹配都会被拒绝，不会静默套用半份配置。

| 字段 | 范围 | 调高后的效果 |
| --- | --- | --- |
| `reasoning_skill` | `0.0–1.0` | 更重视矛盾、证据和自身已知信息，相近候选间误判更少 |
| `social_susceptibility` | `0.0–1.0` | 更容易受警长、公开共识、关系和他人站边影响 |
| `decision_variance` | `0.0–1.0` | 更可能在评分接近的合法候选人中选择次优项；不会忽略明显分差 |
| `plan_consistency` | `0.0–1.0` | 当天投票更愿意延续自己发言计划中的暂定票 |
| `deception_susceptibility` | `0.0–1.0` | 更容易接受完整但虚假的查验和狼人叙事 |
| `deception_strength` | `0.0–1.0` | 狼人的悍跳、误导和公开说服更有影响力；好人值通常保持低位 |
| `team_coordination` | `0.0–1.0` | 狼队更重视分工、让跳、配合和一致行动 |
| `teammate_bus_pressure_threshold` | `0–100` | 队友公开压力达到此值后才考虑卖队友；值越低越早切割 |
| `teammate_black_check_chance` | `0.0–1.0` | 其他局势条件满足、但队友尚未达到压力阈值时，提前尝试“狼查杀狼”的机会更高 |
| `teammate_black_check_min_pressure` | `0–100` | 队友达到该公开压力后直接触发“狼查杀狼”分支；值越低越激进 |

本轮与投票分布直接相关的四组调整方向是：`reasoning_skill` 控制强证据与矛盾的权重，`decision_variance` 控制接近候选间的个体温度，`social_susceptibility` / `deception_susceptibility` 分别控制社交站边和虚假叙事的影响，`team_coordination` 控制狼队软策略的协同强度。这些值可以改变概率分布，但不会绕过合法目标、信息权限或“狼查杀狼”硬叙事。

推荐微调流程：

1. 先记录基线的 10–20 局结果，例如好人误投率、假查杀被采信率、暂定票兑现率、狼人卖队友时机和胜率。
2. 一次只改一个维度；概率/能力值建议每次增减 `0.05–0.10`，压力阈值建议每次增减 `5–10`。先调阵营或身份层，只有一个角色明显偏离时再写 `npcs` 覆盖。
3. 保持后端由你手动运行，保存 JSON 后调用：

   ```bash
   curl -X POST http://127.0.0.1:8000/admin/reload-config
   ```

4. 确认响应包含 `"tuning_schema_version": "npc_tuning.v1"` 和 `"applies_to": "new_games"`，然后创建新对局；旧对局不会热变参数。
5. 从项目根目录执行 `backend/.venv/bin/python scripts/smoke_check.py`，再用同样的局数和观察指标比较，不要凭单局输赢连续大幅调参。

几个常见目标：好人太“全知”，优先小幅降低 `reasoning_skill` 或提高 `deception_susceptibility`；NPC 总是机械跟自己上一轮发言，降低 `plan_consistency`；票型过于整齐，提高少量 `decision_variance`；狼人过早卖队友，提高 `teammate_bus_pressure_threshold`；“狼查杀狼”太频繁，则降低 chance 或提高 min pressure。硬规则边界和“狼查杀狼”后的叙事一致性不会被这些参数关闭。

## 混合 RAG

- `app/rag.py` 使用 FastEmbed `0.7.4` 和 `BAAI/bge-small-zh-v1.5`。
- 静态知识在首次查询时生成向量并保存在内存中。
- 综合关键词分数与余弦相似度返回 Top-K 结果。
- `/chat` 使用静态知识；坏坏和然然还会把最近 8 轮普通聊天记忆交给 LLM，狼人杀私聊则检索公开日志和当前参赛 NPC 的对局内私有记忆。
- 私有记忆来源不会通过响应标题泄露。
- NPC 正式发言和投票理由使用独立的公开决策检索器，只读取静态知识和正式公开发言。
- 私聊、查验结果和 NPC 内部记忆不会进入可引用的公开决策证据；普通白天决策只把当前 NPC 的合法私有知识作为不可公开的策略输入。
- `NpcSpeechItem` 与 `NpcVoteDecision` 会返回 `evidence_titles` 和 `retrieval_mode`，便于 Godot 展示来源。
- `GET /api/rag/status` 返回 `hybrid` 或 `keyword`、模型名、索引状态和错误信息。
- 设置 `AGENT_TOWN_DISABLE_VECTOR_RAG=1` 可以强制测试关键词降级。

## 自检

在项目根目录运行：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

CI 或不希望调用 Godot 时运行核心 profile；只验证 Godot 静态布局和短暂 headless 加载时
运行 Godot profile：

```bash
backend/.venv/bin/python scripts/smoke_check.py --profile core
GODOT_BIN=/Applications/Godot.app/Contents/MacOS/Godot \
  backend/.venv/bin/python scripts/smoke_check.py --profile godot
```

V4.3-A/B 检查覆盖原子替换、`0700/0600` 权限、旧文件保护、任意
pre-commit helper 异常回滚、同 key 顺序/并发去重、跨端点和 payload 冲突、带 key
写盘失败回滚、响应丢失后重启恢复、结果台账篡改、无 key 兼容、固定身份池顺序，
以及带 key replay 零落盘。V4.4–V4.6 的公开证据、赛后解释、表达质量、指纹与成本
契约继续回归；V4.7-A 还静态检查七步引导、完整状态入口、六身份隐私投影、弹窗输入
边界和本地偏好 allowlist。V4.7-B 新增对 `agent_town_responsive_layout.v1`、
`agent_town_focus_navigation.v1`、`compact / default / wide` 物理窗口断点、
`1100×650 / 1280×720 / 1600×900` 三档布局、项目最小窗口、动态卡片列数、长文本滚动、
可见焦点样式、玩家移动锁、modal 焦点圈定与关闭后归还的静态回归；同时锁定本轮没有
新增 HTTP/Pydantic/规则/事件/存档/重放/LLM 字段。既有 V4.1/V4.2、规则、LLM/RAG
和 UI 回归全部保留。V4.7-C 继续验证 `.github/workflows/ci.yml` 的 Python 3.12、
Godot 4.7.1、Linux/macOS、完整 action SHA、只读权限和离线环境，以及
`docs/V4_RELEASE_CHECKLIST.md`、Godot UID 与 LF 源码交付边界。

V4.7-B 输入恢复回归还要求 `phase_matches`、引导队列 `pop_front()` 返回值及分页
`TabBar` 使用 Godot 4.7 可解析的显式类型，并拒绝已知的三种不安全推断写法。core
profile 提供快速静态保险，`godot` / 完整 profile 继续负责真正加载全部 GDScript。

批量模拟不启动 FastAPI/Godot。完整 smoke 会短暂运行 Godot headless 资源检查，但不会启动编辑器或常驻服务；实际服务由开发者按“运行”一节手动启动。
