# Agent Town V4 改进与开发路线表

## 基线与仓库治理

- V4 从 V3.0 封版标签 `v3.0.0` 和提交
  `7a44dd598a62739e450bebe56198a6fe1f505ebd` 开始。
- V4 只在本地 `v4-development` 开发；开发快照只允许推送到专用
  `v4-origin`，不向 `origin`、`v2-origin` 或 `v3-origin` 推送。
- 公开开发仓库
  [`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0)
  已创建，但尚无 `v4.0.0` 正式封版标签。
- `READMEv1.md` 是历史设计稿；当前代码、自动化检查、本路线表和
  README 才是实现事实。

## V4 目标

V4 的主题是：

> 让真人玩家水平、发言和私聊真实影响对局，并使整局可以存档、重放、
> 解释和复盘。

不可改变的规则边界：

- Python 唯一决定身份、合法知识、行动是否合法、夜间结算、票型、警徽、
  出局和胜负。
- LLM 只能在 Python 提供的合法上下文和结构化契约内选择 NPC 策略与表达，
  不能改写规则结果。
- 好人不能读取隐藏身份；合法推理可以正确，也可以被骗、误判和投错。
- 玩家自由文本必须先经过 Python 解析、权限和事实校验，不能靠措辞绕过规则。
- 赛后指标可以读取真实身份评价已经发生的行动，但真值不得倒灌进实时策略。
- 每个功能里程碑同步维护根 README、后端 README、`COMMANDS.md`、本路线表
  和自动化自检。

## 里程碑总览

| ID | 状态 | 目标 | 主要依赖 |
| --- | --- | --- | --- |
| V4.1-A | 已完成 | 三档离线玩家策略与按身份配对基准 | V3 确定性仿真 |
| V4.1-B | 已完成 | 玩家发言结构化理解与提交前预览 | V4.1-A 基准边界 |
| V4.2 | 已完成 | 单一追加事件日志与确定性重放 | 规则入口梳理 |
| V4.3-A | 已完成 | 原子存档、手动恢复与启动恢复 | V4.2 |
| V4.3-B | 已完成 | 幂等命令与重复结算保护 | V4.3-A |
| V4.4-A | 已完成 | 统一公开证据时间线 | V4.2 |
| V4.4-B | 已完成 | 承诺生命周期和中立矛盾候选 | V4.4-A |
| V4.5-A | 已完成 | 可解释赛后决策复盘 | V4.2、V4.4-B |
| V4.6-A | 已完成 | NPC 重复率、信息增量、证据引用与人设差异基线 | 稳定公开发言记录 |
| V4.6-B | 已完成 | Prompt/配置指纹、LLM 成本与 artifact 配对 A/B | V4.6-A 质量基线 |
| V4.7-A | 已完成 | 首局分阶段引导、角色说明和公开/私密边界提示 | 前述 schema 稳定 |
| V4.7-B | 已完成 | 1100×650 起的三档响应式、整局键盘导航、字体与对比度 | V4.7-A |
| V4.7-C | 已完成（待人工封版） | CI、封版清单和跨平台源码交付 | V4.7-B |
| V4.8-A | 已完成 | 开局选择 LLM 输出校验或 0 次校验原文直出 | V4.6-B、V4.7-C |

## V4.1-A 三档玩家策略与身份配对基准

### 目标与非目标

本阶段为离线仿真增加可复现的合成玩家水平，用同一 seed、同一固定玩家身份
比较不同策略。它用于建立诊断基线，不把“合成专家”冒充真人研究结论。

本阶段不修改：

- 实时 `GameStartRequest` 或其他 FastAPI 对局接口。
- Godot 的开局、行动和发言 UI。
- NPC 决策、belief、stance、投票校准、LLM 或 RAG。
- 自由文本发言预览和玩家私聊仿真；前者属于 V4.1-B，后者在事件与证据链
  稳定后单独接入。

### 策略契约

`player_strategy.v1` 定义三档：

| tier | policy version | 行为边界 |
| --- | --- | --- |
| `beginner` | `basic_legal.v1` | 只做合法、简单、低规划的选择 |
| `standard` | `legal_public_baseline.v1` | 冻结 V3 自动玩家行为，作为兼容锚点 |
| `expert` | `evidence_guided.v1` | 综合公开压力、历史票型、公开声明和本人合法私有信息 |

三档策略都只能消费 `player_strategy_context.v1`：

- `self` 只包含玩家本人的身份、阵营、存活和警长状态。
- `public.characters` 只有存活、公开声明、公开怀疑分、公开说服力、既往公开票、
  公开验人说法和警长状态；不含其他角色真实 `role/camp`。
- `lawful_private` 只包含狼人队友、本人预言家查验、本人女巫刀口/药品、
  本人守卫上次守护和猎人开枪权限。
- 策略函数只接收净化 context 和合法候选 ID；`WolfGameState` 不进入纯排序函数。

### Schema 注册

| schema | 生产者 | 用途 |
| --- | --- | --- |
| `player_strategy.v1` | `app/player_strategy.py` | tier、策略版本和知识范围 |
| `player_strategy_context.v1` | `app/player_strategy.py` | 离线玩家合法视图 |
| `player_decision_trace.v1` | `app/simulation.py` | 玩家夜间、警长、发言、投票和猎人行动 |
| `player_performance.v1` | `app/simulation_metrics.py` | 纯赛后玩家表现计数与比率 |
| `agent_town_simulation.v14` | `app/simulation.py` | 单局策略、布局摘要、决策轨迹和指标 |
| `agent_town_simulation_batch.v14` | `app/simulation.py` | 单策略连续 seed 批量报告 |
| `agent_town_metrics.v5` | `app/simulation_metrics.py` | V3 指标加玩家表现 |
| `agent_town_player_benchmark.v1` | `app/simulation.py` | 三档 × 六身份配对报告 |

### 配对协议

- 固定身份：
  `werewolf / seer / witch / hunter / guard / villager`。
- `random` 只用于普通单策略批量，不进入正式身份配对。
- 同一个 `seed + player_role` 是一个 cohort；三档策略必须有同一个
  `initial_layout_digest`。
- smoke 使用 `2 seeds × 6 roles × 3 tiers = 36` 局。
- 正式最小基准使用
  `56 seeds × 6 roles × 3 tiers = 1008` 局。
- 配对基准默认关闭 belief、stance 和 vote-calibration 明细，避免输出膨胀；
  规则和玩家赛后指标仍完整保留。
- 不同起始 seed 区间必须单独保留原始报告，不能只保留合并胜率。

### 首个正式基准

`2026-07-20` 使用 `20260719–20260774` 完成 1008 局：

| tier | 总胜局 | 狼人 | 预言家 | 女巫 | 猎人 | 守卫 | 村民 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `beginner` | 88 | 32 | 7 | 10 | 9 | 15 | 15 |
| `standard` | 106 | 34 | 15 | 14 | 11 | 16 | 16 |
| `expert` | 107 | 35 | 13 | 13 | 11 | 17 | 18 |

配对胜率差为 `standard-beginner +5.4%`、`expert-beginner +5.7%`、
`expert-standard +0.3%`；336 个 cohort 均满足三档初始布局摘要一致。
benchmark digest 为
`577e0860e3129cf66f3006f0bda025dbd88594813e64b23310b185938a9bdb13`。
该样本显示三档存在可测差异，但仍不把单个 seed 区间的胜率排序升级为永久门槛。

### 指标

`player_performance.v1` 保留原始分子与分母，覆盖：

- 玩家胜负、放逐票和警长票目标阵营。
- 预言家查验数量、重复查验和查狼率。
- 女巫救人、用毒及毒狼/毒好人。
- 守卫保护与实际拦截、猎人开枪与命中狼人。
- 狼人刀口选择及神职目标比例。
- 玩家公开票意向后 NPC 同目标选票，明确标记为影响代理而非严格因果。

benchmark 按策略、策略 × 身份聚合，并对每对策略输出：

- A 独赢、B 独赢、同赢、同输 cohort 数。
- `player_win_rate_delta_b_minus_a`。
- 全部四类之和必须等于 cohort 数。

### 验收标准

1. 同 seed、身份、策略重复运行得到完全相同结果。
2. `standard` 保持 V3 固定 6-seed 的好人 `2`、狼人 `4` 回归结果。
3. 每个 cohort 恰好包含三档策略，且初始布局摘要唯一。
4. 36 局 smoke 全部合法终局；正式命令可生成 1008 局报告。
5. 三档好人策略在只交换不可见 NPC 真实身份时保持 context 和选择不变。
6. 角色私有事实只在对应玩家依法拥有时进入 context。
7. 玩家表现、策略组、身份组和成对胜负全部计数守恒；无分母为 `null`。
8. 至少一个构造夹具和一个完整 cohort 能观察到不同策略的合法行动差异。
9. `hunter + seed 20260765 + beginner` 固定回归双查杀边界：NPC 狼保留狼队友
   互踩来源为主目标，同时以次目标和公开信号回应另一名预言家，并到达合法终局。
10. 仿真不启动 HTTP、Godot、LLM、RAG 或写入居民记忆。

首版不设置“expert 胜率必须高于 beginner”的硬门槛。先记录配对结果，再用多个
seed 区间检查稳定性，避免为了通过排序而读取隐藏身份或过拟合固定样本。

### 风险

- 赛后真实身份误入策略上下文。
- 策略 tier 被加入身份洗牌随机盐，使 cohort 初始布局不可比。
- 只看总体胜率掩盖身份差异。
- 固定 seed 过拟合，或把影响代理误写成因果。
- schema 元数据变化被误认为 V3 规则行为变化。
- 1008 局报告过大；正式基准必须默认关闭高容量 shadow 明细。

## V4.1-B 玩家发言结构化理解与提交前预览

### 已完成范围

- `app/player_speech.py` 定义严格、额外字段拒绝的
  `player_speech_understanding.v1` 与 `player_speech_preview.v1`。
- `POST /api/player-speech/preview` 共用白天和警上草稿，只解析、规范化和校验，
  不写入发言、声明、警徽流、怀疑值、暂归票或阶段进度。
- 返回身份声明、验人说法、怀疑/支持、投票意向、女巫建议、警长暂归票和
  警徽流规范化结果，并分成 `public_facts_to_write`、
  `strategic_signals_to_apply` 与 `text_only_notes`。
- 拒绝也返回可显示的 `errors`，但 `accepted=false` 且没有指纹，不能确认提交。
- 接受的预览生成 SHA-256 指纹，绑定草稿、规范化结果、当前天数、阶段、发言者
  与相关公开状态。
- 白天和警上提交都在 `GAME_LOCK` 内重新运行同一准备函数。提供指纹时不一致
  返回 409；旧客户端不提供指纹时仍会锁内重解析，不能绕过权限校验。
- Godot 共用一块提交前预览面板，展示规范文本、公开事实、策略信号、仅文本范围
  和拒绝原因；玩家只能选择“确认提交”或“返回修改”。
- 验人解析按逗号拆分子句，修复“验 3 号、怀疑 4 号”误把 4 号登记为验人的问题。

### Schema 与端点

| 契约 | 用途 |
| --- | --- |
| `player_speech_understanding.v1` | 严格表达解析，不含其他角色隐藏身份 |
| `player_speech_preview.v1` | 预览结果、规则效果分类、错误与指纹 |
| `POST /api/player-speech/preview` | 白天/警上共享的无副作用预览 |
| `preview_fingerprint` | 两类最终提交的可选一致性字段 |

### 验收结果

1. 接受和拒绝预览前后的完整 `WolfGameState` 序列化结果一致。
2. 同一草稿、同一公开局面重复预览得到相同理解和指纹。
3. 修改文字或相关对局状态后复用旧指纹返回 409，且提交状态零写入。
4. 警上首次跳预言家但缺警徽流时返回可展示拒绝；补齐后预览规范化分支和锚点。
5. 白天暂归票、角色/验人声明、女巫建议和策略信号与最终提交结果一致。
6. 只交换不可见 NPC `role/camp` 时，理解、效果分类与指纹不变。
7. Godot 静态检查覆盖预览请求、摘要、确认和返回修改控件。

### 风险边界

- 指纹是请求一致性证明，不是身份授权；最终权限仍由 Python 锁内状态决定。
- 预览只解释当前确定性解析器能识别的结构，不宣称完整理解所有自然语言。
- `strategic_signals_to_apply` 可能影响 NPC 判断，但不等于该判断正确。
- Godot 运行时加载仍由开发者手动验证，自动化只做静态 UI 契约检查。

## V4.2 单一事件日志与确定性重放

### 已完成范围

- `app/event_log.py` 定义 `game_rule_event.v1`、`game_rule_event_log.v1`、
  `game_rule_replay.v1` 与 `agent_town_rules.v4.2`。
- `WolfGameState.rule_events` 从 `game_created` 开始，为全部狼人杀规则写入口记录
  成功命令：夜间行动/结算、猎人、警长、白天发言、私聊、自由活动结束、兼容和
  主流程投票、警徽移交。玩家发言 preview 保持只读，不产生事件。
- 事件含稳定连续序号、内容派生 command/event ID、原始请求 payload、actor、
  `public / player_private / system_private` 可见范围、前后 day/phase、前后规则
  状态 SHA-256、上一事件 SHA-256 和是否可执行重放。
- 规则状态摘要排除 game ID、墙钟时间和事件列表本身；其余公开、合法私有、隐藏
  状态都保留。链校验同时检查事件哈希和相邻状态摘要，因此直接修改已封印事件或
  在命令外改规则状态都会被检测。
- 普通 `GET state` 不再回写派生私有信息；角色资源读取不再用 `setdefault` 产生
  空资源写入，消除两条未记录状态变化。

### 重放协议

- `GET /api/game/{game_id}/events` 仅终局导出完整事件链；进行中拒绝，避免 seed、
  夜间命令和私聊泄露。
- `POST /api/game/{game_id}/replay` 在锁内复制原局事件和终局投影后释放锁，使用
  独立临时 game ID、原始开局请求与 seed 重建状态，再逐条调用现有 Python 规则
  函数。玩家发言旧 preview 指纹在重放中移除并重新执行同一解析/权限校验。
- 每条命令执行前后比较状态摘要和 day/phase/actor/visibility 边界；终局额外比较
  winner、winner reason、警长、撕徽状态、警徽流、警长票、放逐票、出局记录和
  完整状态摘要。临时局最后必定从 `GAME_STORE` 清理，不覆盖原局。
- 只有实际 `llm_enabled=false` 且 `rag_enabled=false` 的规则模板局执行确定性
  重放。启用 LLM/RAG 的事件链仍可审计，但明确 `supported=false`；本阶段不重调
  外部模型并伪称文本确定。
- 仿真升级为 `agent_town_simulation.v15` /
  `agent_town_simulation_batch.v15`，每局总是保存事件摘要和重放报告。单局默认带
  完整日志；批量和 1008 局策略基准默认省略事件数组，可用
  `--include-event-logs` 显式保留。
- `gameplay_digest` 使用 `agent_town_simulation.v14` 兼容投影，事件和重放字段只
  改变 `result_digest`；固定 `werewolf + standard + seed 20260719` 仍为
  `0f6a4316e1458fee20fafd349706a0313d24f4de6a7bb6d231f99a8211567227`。

### 验收结果

1. 固定单局 59 个规则事件逐条重放通过；固定 6-seed 共 291 个事件全部通过，
   胜负仍为好人 `2` / 狼人 `4`。
2. 同 seed 在改变 Python 全局随机状态后，事件、重放报告和完整归一化结果完全一致。
3. 事件序号、command ID、event ID 唯一；三类 visibility 均有覆盖，修改封印事件
   会使链校验失败。
4. 开局、终局摘要和 winner/票型/出局/警徽投影全部一致；首个不一致事件会返回
   `first_mismatch_sequence`，而不是只给最终布尔值。
5. 普通 state GET 前后完整状态一致；进行中事件导出返回 400。
6. LLM/RAG 局返回可审计但不可执行重放，不把外部生成结果包装成确定性。
7. 36 局三档 × 六身份 smoke 全部合法终局并逐局通过重放；默认批量结果不携带
   大体积事件数组。

### 风险边界

- 事件已随 V4.3-A 的完整私有快照持久化；V4.2 自身的事件 schema 仍不承担
  文件原子性或启动恢复职责。
- `public_logs`、`sheriff_events`、行动和票型列表仍由既有规则代码同步生成，
  V4.2 用命令事件和状态摘要封印这些投影；后续证据时间线将从事件统一投影。
- 完整终局事件含私有信息，不是进行中公开 API；visibility 是投影依据，不等于
  当前已有多用户鉴权系统。
- command ID 当前由序号、payload 和前序摘要派生；客户端提供的幂等 command key
  留待 V4.3-B，不能把当前 ID 当作重复请求去重承诺。
- V4.3-A 的 `recovery_config_fingerprint.v1` 只用于判断未完成存档能否安全继续；
  V4.6-B 已另行实现完整实验、Prompt/config、价格表和 A/B 指纹；两种指纹用途
  不同，不能互相替代。

## V4.3-A 原子存档与恢复

### 已完成范围

- `app/game_persistence.py` 为真实 FastAPI 生命周期中的新局和全部成功规则命令
  保存一份完整私有状态；`GAME_STORE` 继续作为活动缓存，不再是唯一恢复来源。
- 新局先保存再发布进缓存。20 个规则写入口使用统一 transaction guard；任一
  pre-commit helper/模型构造异常或原子写失败都会恢复命令前完整 checkpoint。
- 同目录临时文件从创建起为 `0600`，flush/fsync 后使用 `os.replace`；目录为
  `0700`。替换成功后的目录同步只做 best effort，不会让内存反向回滚。
- FastAPI lifespan 启动时先验证全部存档，再一次性恢复合法未完成局；任何活动
  存档失败都会拒绝激活并阻止服务启动，不做部分恢复。
- 终局归档完整校验后计入 skipped，不要求当前配置相同；它不会自动占用活动缓存，
  但仍可手动恢复用于 summary/event/replay。
- 进行中持久局存在时禁止热重载配置。离线 simulation、隔离 replay 和直接导入
  规则模块不激活自动保存。

### Schema 与端点

| 契约 | 用途 |
| --- | --- |
| `game_save.v1` | 完整私有状态、最后事件、规则/快照摘要和配置指纹 envelope |
| `game_save_response.v1` | 手动保存结果 |
| `game_restore.v1` | 手动恢复或 already-cached 结果 |
| `game_recovery.v1` | 启动扫描、恢复、终局跳过与失败报告 |
| `recovery_config_fingerprint.v1` | 开局冻结的恢复兼容指纹，不含 API Key |
| `POST /api/game/{game_id}/save` | 显式原子检查点 |
| `POST /api/game/{game_id}/restore` | 校验后手动恢复 |
| `GET /api/game/recovery-status` | 最近一次启动恢复报告 |

### 保存与恢复协议

`game_save.v1` 同时绑定：

1. 文件名、envelope、state 与每个 rule event 的 game ID。
2. `game_created` 中封印的恢复配置指纹、state 字段与 envelope 指纹。
3. 完整原始 state 的 `snapshot_digest` 及 Pydantic round-trip 后的同一摘要。
4. `rule_state_digest`、最后事件 `state_digest_after` 和 envelope 状态摘要。
5. 连续事件序号、上一事件摘要、事件自身摘要、最后事件序号与摘要。

进行中恢复还要求指纹与当前规则、角色、NPC 人设/知识/调参及安全 LLM 配置一致。
配置指纹在开局冻结，不能通过修改 state 为旧局重新贴标签；完整存档包含 seed、
隐藏身份、夜间行动和私聊，目录已被 Git 忽略且不得公开。

V4.3-A 与 V4.3-B 之间曾生成过一种早期 `game_save.v1`：其合法快照还没有
`command_results` 字段。恢复器先按文件内原摘要验证原始 payload，随后只在“唯一
差异恰好是缺少默认空对象、事件链中没有任何 `idempotency_key`”时做内存归一化；
读取/启动恢复不改文件，下一次正常持久化才写入新字段。缺少非空台账、已有带 key
事件、未知字段、其他默认字段差异或任意摘要不一致仍 fail closed。

### 验收结果

1. 创建、成功命令和显式保存均原子推进事件序号；目录/文件权限为 `0700/0600`，
   无遗留临时文件。
2. 注入 `os.replace` 失败时旧文件逐字节不变，内存完整回滚，原命令可重试成功。
3. 注入 mutation 后 helper 失败与非法同步投票均零状态残留；事件构造异常也在
   统一 commit point 前回滚。
4. 清空活动缓存后恢复结果与原完整 JSON 相同，并可继续提交合法规则命令。
5. 非法 JSON、未知/额外 schema、未知 state 字段、快照修改、事件链篡改、末事件
   序号、三层 game ID、三层配置指纹和当前配置漂移均被拒绝。
6. 一个合法文件加一个坏文件时启动恢复不部分写入；移除坏文件后完整恢复。
7. 启动跳过终局归档且手动恢复有效；旧终局指纹不阻塞新配置启动。
8. 新 game ID 同时避开内存和磁盘；simulation/replay 前后文件集合与内容完全一致。
9. OpenAPI、根 README、后端 README、`COMMANDS.md` 和独立自动化检查同步。

### 风险边界

- 当前仅支持单进程、单 uvicorn worker；进程内锁不提供跨 worker 协调。
- 原子替换和 transaction guard 处理 commit 前失败；V4.3-B 已为携带外部 key 的
  请求补齐提交后响应丢失重试。无 key 请求仍没有该保证。
- 启动恢复 fail closed 意味着损坏的未完成存档必须先修复、隔离或移除，服务才会
  接受新局；不会静默降级为只在内存运行。

## V4.3-B 幂等命令与重复结算

### 已完成范围

- `app/idempotency.py` 定义外部 `game_command_idempotency.v1` 和持久
  `game_command_result.v1`；18 个请求模型以可选字段覆盖 20 个开局后规则写入口。
- 统一 transaction guard 在业务/阶段校验前查找同局结果。相同 key、端点和去 key
  payload 摘要返回原响应；端点或 payload 不同返回 409，且零状态变化。
- 第一次带 key 的规则函数必须恰好追加一个事件。响应模型校验通过后，事件、响应
  payload 及摘要、结果台账和完整 `WolfGameState` 在同一 `game_save.v1` 中原子替换。
- 替换前失败恢复命令前完整 checkpoint；替换成功但响应丢失时，服务重启恢复台账，
  重试在阶段校验前返回原结果，不重复夜间结算、猎人、警长、放逐、发言或私聊。
- 结束对局的最后响应丢失时，启动仍把终局作为 skipped 归档；重复 key 只读加载并
  校验该结果，不重新激活终局、不改写存档。
- 结果台账逐项绑定 game ID、映射 key、请求摘要、端点、事件序号/类型/摘要、响应
  模型和响应摘要；恢复时在完整快照和事件链校验之外再次验证。
- `command_results` 是传输/提交层事实，不进入 `rule_state_digest`；它进入完整
  `snapshot_digest`，带 key 的规则模板事件仍通过同一隔离 replay。
- Godot 的 10 个请求通道覆盖 11 条当前客户端规则调用：按 operation + payload
  复用 key，网络错误/非 2xx 保留，2xx 清理，payload 变化或新局生成新 key。
- 身份池按固定角色顺序构造，不再依赖 JSON 对象键顺序；存档排序后恢复仍可用同一
  seed 重建相同角色、夜间行动和资源。

### Schema 与协议

| 契约/字段 | 用途 |
| --- | --- |
| `game_command_idempotency.v1` | 同一对局内外部命令去重规则 |
| `idempotency_key` | 可选 body 字段；8–160 位，首位字母/数字，其余限安全 ASCII 集合 |
| `game_command_result.v1` | 请求、事件和原响应的持久绑定记录 |
| HTTP 409 | 同一 key 被不同端点或不同 payload 使用 |
| HTTP 503 | 第一次带 key 的命令未能完成原子持久提交，内存已回滚 |

key 的作用域和保留周期是“一份 `game_id` 的完整存档生命周期”。重复命中返回第一
次响应模型的同一 JSON payload，不承诺复现首次 HTTP 传输头。`POST /api/game/start`、
玩家发言 preview、GET、显式 save/restore 和 replay 不使用外部 key；事件
`command_id` 继续只用于审计。

### 验收结果

1. OpenAPI 中 18 个请求 schema 均有可选 key，20 个规则写函数均注册响应模型；
   `GameStartRequest` 明确没有该字段。
2. 同 key 顺序重复和两个线程并发重复都只追加一个事件、一个结果记录和一次状态
   效果，并返回完全相同的响应 payload。
3. 同 key 改 payload 或跨端点复用返回 409；完整内存 JSON 与存档字节不变。
4. 注入 `os.replace` 失败时，新事件与结果记录一并回滚，旧文件逐字节不变；相同
   请求随后可成功重试。
5. 夜间结算响应被视为丢失后清空缓存并启动恢复；对局已离开 `NIGHT`，相同 key
   仍返回原响应，事件数和文件内容不变。
6. 修改响应、请求摘要、事件序号/摘要、端点或结果映射 key，并重算快照摘要，恢复
   仍以 409 拒绝且不进入活动缓存。
7. 无 key 的旧客户端继续追加原 V4.2 事件，事件 payload 不出现空 key，仿真结果
   和规则摘要保持兼容。
8. 带 key 事件链逐条 replay 验证通过，临时 replay 不注册为持久局、零文件变化。
9. Godot 静态契约覆盖每个通道的 key 准备和 2xx 清理；运行时仍由开发者手动联调。
10. 全流程把每条仿真命令都改为唯一外部 key 直至合法终局；重启扫描保持终局
    skipped，最后命令仍可从归档返回原响应，跨端点复用返回 409 且零写入。

### 风险边界

- exactly-once 指同一持久对局、同一外部 key 的规则效果；依赖原子存档仍存在且能
  通过恢复校验。无 key、删除存档或另一个 game ID 不在保证内。
- 仍只支持单进程、单 worker；没有数据库唯一约束、跨 worker 锁或分布式去重。
- 结果台账本阶段随对局永久保留，不做 TTL/压缩；它包含私有响应，不能公开。
- Godot 待处理 key 只在客户端进程内存中；后端重启/网络失败可重试，Godot 自身
  崩溃后的待处理命令恢复留待后续客户端存档设计。
- 持久记录包含 Python 端点/响应模型名；不兼容重命名会 fail closed，版本迁移必须
  显式处理，不能静默接受旧结果。

## V4.4 公开证据、承诺和矛盾时间线

### V4.4-A 已完成范围

- `app/public_evidence.py` 定义 `public_evidence_item.v1` 和
  `public_evidence_timeline.v1`；模型禁止额外字段并校验连续 sequence、唯一 ID、
  item_count 以及 category/verification 配对。
- `GET /api/game/{game_id}/state` 新增 `public_evidence_timeline`，统一身份/技能
  声明、验人说法、警徽流、报名/退水、警长票、警长当选、发言方向、暂时/最终归票、
  警徽动作、猎人动作、已公布放逐票和公开出局结果。
- 每项 `evidence_id` 只由公开结构、来源集合内稳定位置和 schema 版本生成，不读取
  声明内部 source、真实身份/阵营、夜间行动者或赛后胜负。根级
  `projected_event_sequence` 把整份投影绑定到当前事件游标。
- V3/V4.1 的公开集合没有逐条规则事件 provenance；V4.4-A 明确不猜测来源事件，
  不把近似匹配包装成审计事实。未来需要逐项 provenance 时必须新增版本化契约。
- `claim / commitment / confirmed_action` 对应公开说法、公开承诺和规则已确认的公开
  动作。前两类必须 `unverified`；第三类 `confirmed` 只确认动作发生，不确认角色或
  声明真伪。
- 未结算的 `game_state.votes` 不公开；只有同日存在 `exile_vote_resolved` 或
  `all_votes_submitted_and_resolved` 事件后才生成 `exile_ballot`。夜间死亡统一投影
  为 `night_out`，不区分狼刀和毒药、不返回责任席位。
- NPC `build_actor_legal_knowledge()` 与玩家 UI 使用相同 evidence ID；Godot 身份卡
  和公开记录页显示 `◇ / ◆ / ●`，旧响应降级到 `public_intel/public_logs`。
- 投影不写回 `WolfGameState`，因此不改变 `rule_state_digest`、`game_save.v1`、
  幂等台账或 V4.2 replay。重复投影零状态变化且 JSON 完全相同。

### V4.4-A 验收结果

1. 两个 schema 进入 OpenAPI，状态响应返回最后事件游标、准确 item_count、连续
   sequence 和唯一稳定 ID。
2. 公开声明、警徽流、警长动作、猎人动作、夜间公开出局均按三类语义输出；玩家和
   NPC 引用同一证据 ID。
3. 未结算票型不出现；追加公开结算事件后，同日票型才出现。
4. 交换不可见 `role/camp`、声明内部来源和同一公开夜死结果的狼刀/毒药内部原因，
   时间线逐字节不变。
5. 递归检查输出键，不含 `role / camp / winner / cause / source / source_action /
   source_actor_ids`。
6. Python 编译、狼人杀规则 smoke、Godot 静态 UI 契约和文档契约通过；Godot 运行时
   仍由开发者手动验证，本阶段不自动启动。

### V4.4-B 已完成范围

- `app/public_evidence.py` 新增 `public_commitment_state.v1`、
  `public_contradiction_candidate.v1` 和 `public_evidence_analysis.v1`；模型禁止额外
  字段并校验计数、连续 sequence、稳定唯一 ID、状态/原因配对和证据链接。
- `GET /api/game/{game_id}/state` 新增 `public_evidence_analysis`。它与 V4.4-A 时间线
  绑定同一 `game_id / projected_event_sequence`，根级固定
  `truth_scope=public_only_no_post_game_truth` 和明确免责声明。
- 每个警徽流版本独立生成一条 commitment，保留原始 `source_evidence_id`、首段与
  次段目标、公开金水锚点或撕徽分支，以及替代/解决它的公开 evidence ID。本阶段只
  检查首段验人目标和警徽分支；次段目标保留为上下文，不提前制造独立到期判断。
- 生命周期为 `active / superseded / fulfilled / invalidated / undetermined /
  contradicted`：到期前正常修订是 superseded；公开验人目标或警徽动作符合计划是
  fulfilled；承诺人、目标或公开分支不可用是 invalidated；没有足够公开后续是
  undetermined；只有公开后续直接落在计划外才是 contradicted。
- 中立候选仅含 `identity_claim_changed / seer_result_changed /
  badge_flow_target_mismatch / badge_flow_action_mismatch`。每项保存前后 evidence
  ID，固定 `review_status=needs_review`、`judgment=none`；不会生成狼人概率或自动
  阵营结论。
- 警徽流修订本身、暂时/最终归票变化、目标公开出局、分支不可用和没有公开报告都
  不作为矛盾候选。`fulfilled` 也只确认公开记录关系匹配，不确认声明内容真实。
- NPC 合法知识消费状态 API 同一批 commitment/candidate ID；Godot 公开记录页显示
  承诺状态、候选和“需核对，不代表阵营判断”提示，旧响应继续安全降级。
- 整层为确定性只读投影，不写回 `WolfGameState`，不改变规则摘要、存档、幂等结果
  或 replay；交换隐藏身份/阵营、声明内部来源或同一公开夜死结果的内部原因不会改变
  输出。

### V4.4-B 验收结果

1. 三个新 schema 进入 OpenAPI；状态响应的计数、连续 sequence、稳定 ID、时间线
   evidence 引用和根级事件游标一致。
2. 合成场景覆盖六种 commitment 状态，以及验人目标匹配、警徽分支匹配、目标/
   分支失效、到期无公开后续和到期前/后的修订边界。
3. 四类候选均有正样本；正常警徽流修订、暂时/最终归票变化和公开条件失效均有
   反例，确保不会把合理变化自动升级成矛盾或阵营结论。
4. 全部候选固定 `needs_review / judgment=none`；递归检查进行中输出不含真实
   `role / camp / winner / cause / source`、赛后验真或狼人概率字段。
5. 重复投影完全一致且状态摘要不变；隐藏身份/阵营、声明内部来源和夜死内部原因
   差分不改变输出；NPC 引用相同分析 ID。
6. Python 编译、狼人杀 smoke、OpenAPI、Godot 静态展示和四份文档契约通过；未自动
   启动 FastAPI 或 Godot，运行时 UI 仍由开发者手动验证。

### 风险边界

- `sequence` 是当前投影展示顺序，不是旧记录的精确事件序号；根级事件游标只声明
  整份投影时点。
- evidence ID 对当前 schema 和追加式公开集合稳定；若未来迁移/重写历史集合，必须
  升级 schema 并提供显式映射，不能静默复用旧 ID。
- `confirmed_action` 不是“内容为真”。例如按警徽流移交已经发生，但由此表达的金水/
  查杀仍是声明者故事。
- `fulfilled / contradicted` 都只描述公开记录之间的关系；候选不能作为规则判定、
  狼人概率、投票硬约束或赛后事实标签使用。
- commitment 是当前事件游标下对每个警徽流版本的只读状态快照。未来若需要记录
  每次状态跃迁的精确时点，必须从新规则事件或新版本 schema 建立 provenance，不能
  把当前投影 sequence 冒充历史事件序号。

## V4.5-A 可解释赛后决策复盘

### 已完成范围

- `app/post_game_review.py` 定义严格、禁止额外字段的
  `post_game_evidence_reference.v1`、`post_game_decision_review.v1` 和
  `post_game_explainable_review.v1`。复盘根级固定
  `truth_scope=post_game_truth_unlocked`，每条决定也固定
  `post_game_truth_unlocked=true`。
- 现有 `GET /api/game/{game_id}/summary` 继续只在 `GAME_OVER` 且 Python 已封印
  winner 后开放，并新增 `explainable_review`；进行中的 `/state`、NPC 合法知识和
  公开证据接口不增加角色/阵营真值。
- 投影覆盖已保存的 `public_speech / exile_vote / night_action / hunter_shot`。每条
  包含稳定 `review_id`、源集合坐标、行动者/目标、决定摘要、提交时记录的 RAG/
  signal/立场/连续性或技能依据、跨日公开证据引用、赛后身份真值、评价与解释。
- `knowledge_scope=recorded_basis_plus_prior_day_public_evidence` 是保守边界：只把更早
  日期的公开证据称为“当时可核对”；同日只有随决定持久保存的 signal/plan 才能作为
  依据。V3 旧集合没有逐条同日事件序号，复盘明确披露这一限制，不补写心理活动。
- 好人方向与赛后阵营一致记为 `accurate`；狼人决定记为 `strategic`，不冒充好人
  识狼评分；查验好人、未挡刀守护、不开枪等不能可靠判错的选择保持 `neutral` 或
  `unscored`。
- `mistaken` 必须且只能归入 `deceived / insufficient_evidence /
  continuity_break / skill_misuse / deterministic_variance` 之一。受骗要求该决定确实
  保存了狼人失实验人 signal；连续性断裂要求偏离已保存立场/暂票且缺少结构化改动
  依据；不会仅凭自由文本猜测因果。
- 根级保存完整评价/错误分类计数，模型校验计数、连续 sequence、唯一 ID 和评价-
  错误类别组合。Godot 终局复盘新增“解释复盘（赛后）”页，分开展示当时依据、
  赛后真值、分类解释和后来跨日证据。

### 验收结果

1. 非终局摘要仍返回 400；进行中状态/OpenAPI 状态模型不含 `explainable_review`。
2. 同一终局重复投影 JSON 完全相同且 `WolfGameState` 零变化；review ID 不依赖展示
   文案，根级计数与条目严格一致。
3. 合成终局分别锁住受骗、证据不足、连续性断裂、技能误用和确定性概率扰动五类；
   正确、狼人策略、中性与不可评分路径也通过模型约束。
4. 早日/晚日 evidence reference 严格满足日期边界且不重复；同日记录不会被伪装成
   精确的先验知识或后续因果。
5. OpenAPI 注册三个复盘 schema；Godot 静态契约覆盖第三页、赛后真值警告、五类
   中文标签与空数据降级。

### 风险边界

- 本阶段解释“存档中实际保留了什么”，不是完整思维链，也不声称恢复 LLM 隐藏
  推理。没有结构化目标/方向的旧发言只能 `unscored`。
- 旧集合只有日级和阶段级顺序。若以后需要同日逐决定精确 provenance，必须在新
  规则事件/payload 中封印引用并升级 schema，不能回填假事件序号。
- `accurate/mistaken` 是赛后审计标签，不参与实时 belief、NPC 策略、投票、胜负或
  重放；任何未来消费者都不得把它倒灌为进行中角色知识。

## V4.6-A NPC 表达质量离线基线

### 已完成范围

- `app/speech_quality.py` 定义六个版本化契约；五个报告 payload 模型使用严格类型、
  禁止额外字段与非有限数，normalization 契约固定算法口径：
  `npc_speech_normalization.v1`、`npc_speech_quality_observation.v1`、
  `npc_speech_actor_quality.v1`、`npc_speech_quality.v1`、
  `npc_speech_actor_quality_batch.v1` 和 `npc_speech_quality_batch.v1`。
- 单局/批量仿真升级为 `agent_town_simulation.v16` /
  `agent_town_simulation_batch.v16`。质量字段在冻结的玩法摘要之后生成，
  `gameplay_digest_projection_version=agent_town_simulation.v14` 与
  `agent_town_metrics.v5` 保持不变。
- 统计只接受已经 `GAME_OVER` 的对局，固定
  `scope=npc_public_speeches_only`、`truth_scope=public_only_no_role_truth`。
  它读取 NPC 公开发言、随该条发言保存的公开结构化立场/计划/引用；玩家公开
  发言只作为“此前公开信息”参与增量基线。真实 `role/camp`、胜负标签和私有 belief
  不进入评分，也不输出原始发言。
- `npc_speech_normalization.v1` 先做 NFKC、转小写并移除非字母数字字符；模板比较还会
  替换公开姓名、座位号和数字。质量子报告只保存归一化文本/模板的 SHA-256、字符数
  和结构化信息原子，不保存可直接回放的发言正文；仿真既有赛后审计字段不属于该
  truth scope。
- 重复指标同时保留全局逐字归一化重复、去目标模板重复、跨角色模板重复，以及字符
  trigram Jaccard 近重复。近重复阈值固定
  `near_duplicate_threshold=0.82`；pair 原始计数、分母和比率同时输出。
- 信息增量只由随 speech 持久化的公开结构字段构造原子，例如主次目标、支持/怀疑、
  问题、验证点、暂票、claim option 和女巫建议。证据引用率独立统计 RAG 标题、
  signal、plan 与公开立场引用；不会从自由文本猜测新事实。终局按天聚合的
  `public_claims` 没有逐发言 provenance，不会被回填到更早发言。
- 人设代理包含配置口头禅/彩蛋命中，以及
  `persona_differentiation_score = 1 - mean_cross_actor_template_similarity`。
  它只衡量文本表面差异，不等同于真人能否辨认角色，也不评价发言真伪。
- 批量聚合先累加原始 count 与相似度 sum，再按真实分母计算加权比率；同时保留按
  NPC 的跨局聚合。普通 CLI 新增 `[SPEECH-QUALITY]` 摘要，不请求 LLM、不启动
  FastAPI/Godot，也不写对局存档。

### 验收结果

1. 合成终局锁住逐字/模板/跨角色/近重复计数、公开证据引用、信息原子增量和人设
   marker；所有 count 守恒，比率为 `0..1` 或无分母时的 `null`。
2. 交换 NPC 隐藏 `role/camp` 后整份质量报告完全相同；序列化结果不含角色真值键或
   原始发言文本，未结束对局明确拒绝生成。
3. 同 seed 在 belief、stance、vote-calibration trace 开关变化时，逐局质量报告和
   同局数批量聚合完全相同；质量统计不改变冻结的 v14 `gameplay_digest`。
4. 批量 schema 从逐局原始计数重算，阶段计数、actor-game 计数、pair 数与信息原子
   数全部守恒；人设差异分与跨角色平均模板相似度互为补数。
5. Python 编译、定向无 HTTP 仿真、自检文档契约和 CLI JSON/终端摘要通过；本阶段
   没有新增实时 API 或 Godot 页面，也没有自动启动服务。

### 风险边界

- 这些数值是诊断基线，不是自动上线门槛，不会进入 NPC belief、策略、发言生成、
  投票、技能、胜负或实时 UI。
- 字符 trigram 和结构化信息原子是可复现代理，不具备完整语义理解；同义改写可能被
  低估，固定套话加少量改写也可能漏检。阈值变化必须升级版本，不能静默修改。
- 人设 marker 受当前配置覆盖率影响；高 marker 命中不自动代表自然，高表面差异也
  不自动代表内容有价值。需要真人盲评时应建立独立标注集和版本化协议。
- 规则模板仿真建立的是确定性基线，不代表真实 LLM 输出质量。V4.6-B 已补齐
  Prompt/配置指纹、版本化成本和 artifact 配对 A/B，但规则 artifact 报告仍明确
  不评价 LLM/Prompt 效果。
- 人设 marker 使用当前 NPC profile；V4.6-B 已把 profile 纳入完整和 active-only
  实验指纹，跨时间比较必须先核对指纹或明确分成不同 arm。

## V4.6-B 指纹、成本与配对 A/B

### 已完成范围

- `app/llm_fingerprinting.py` 定义
  `llm_prompt_fingerprint.v1`、`llm_config_fingerprint.v1` 和
  `experiment_fingerprint.v1`。所有对外字段只含 canonical JSON SHA-256，不包含
  Prompt、知识库正文、endpoint 用户信息/query/fragment 或 API Key。
- `LLMClient` 在 adapter 边界对每次实际使用的最终 system prompt、task、operation、
  请求/重试契约计算 digest；安全配置摘要只读取 provider、model、temperature、
  max tokens、timeout/retry、脱敏 endpoint identity 和 provider 请求模式等 allowlist。
- 实验 manifest 同时保存完整 `configuration_fingerprint` 与 active-only
  `effective_fingerprint`。规则模板模式中 rules/roles、NPC profiles、tuning、输出
  schema 和当前 player policy 为 active；Prompt catalog、知识库、LLM request config
  和 RAG 为 inactive。完整配置漂移可追踪，但 inactive 组件不进入规则效果身份。
- 单局/批量仿真升级为 `agent_town_simulation.v17` /
  `agent_town_simulation_batch.v17`，根级和每局封印同一实验 manifest；冻结的
  `gameplay_digest_projection_version=agent_town_simulation.v14` 与
  `agent_town_metrics.v5` 保持不变。普通 CLI 增加 `[EXPERIMENT]`。
- `app/llm_observability.py` 升级到 `llm_observation.v2` 与
  `llm_observability_summary.v2`，继续严格读取历史 v1。request 事件增加
  prompt/config digest、token usage 四态、已报告/未报告 usage 的 provider attempt
  数与 billing model 来源；汇总拆分 adapter attempt/retry 和 semantic
  validation attempt/retry，并报告 legacy、usage 与 fingerprint 覆盖率。
- `app/llm_pricing.py` 严格校验 `llm_price_catalog.v1` 的 provider/model/billing
  mode、生效时间窗、known/unknown 状态和无重叠价格区间；价格表本身有稳定
  fingerprint。`llm_cost_summary.v1` 保留 request/attempt、usage、raw token、已知/
  未知价格、完整/未知成本与原因，并按 configured/billing model 分组。
- 默认 `config/llm_pricing.json` 的 `deepseek-v4-flash` 明确为 unknown；这不是官方
  报价也不是零成本。任一可计费请求的 billing model、全部 attempt usage 或有效
  input/output 价格未知时，完整 `total_cost_usd_micros` 为 `null`，可证明的
  `known_cost_usd_micros` 仍独立保留。
- `app/experiment.py` 和 `scripts/compare_simulation_artifacts.py` 只读校验并比较
  两组 v17 batch artifact，输出 `agent_town_artifact_ab.v1`。每侧允许重复传入多个
  固定身份文件，但必须共享一个指纹；两侧必须有不同的完整和 active-only 指纹。
- A/B cohort 固定为 `seed + actual player role`，两边集合必须完全相同；逐对验证
  initial layout、player strategy/policy、ruleset、schema 和 trace 开关。胜负、局长和
  五项 V4.6-A 指标保留 raw numerator/denominator/similarity sum，跨局聚合后才计算
  rate 和 B-A delta，不平均每局百分比、不静默丢样本。
- artifact 报告固定 `comparison_mode=rule_only_artifacts_no_llm`、
  `llm_evaluated=false`、`prompt_effect_evaluated=false`。比较器不切换代码/配置、
  不运行游戏且不调用模型；CLI 打印 `[ARTIFACT-A/B]` 和五项 `[QUALITY-A/B]`。

### 验收结果

1. 相同输入得到相同 digest；Prompt、active 配置和 inactive 配置的受控变化分别只
   改变预期摘要。API Key、URL 凭据/query/fragment 不进入摘要输入或序列化 manifest。
2. exact system prompt 在 `LLMClient` 边界被摘要；观测事件/汇总严格拒绝未知字段，
   v1/v2 可混合读取，成功请求至少一次 provider attempt，adapter retry、semantic
   retry 与 provider attempt usage 数严格守恒；公开状态只返回脱敏 endpoint identity。
3. 合成 known/unknown、完整/部分/缺失 usage、provider billing model 与多 attempt
   样本锁住成本守恒；价格表变更会改变 catalog fingerprint，未知总成本保持 `null`，
   不会被当作零。
4. 同 seed 在 trace 开关变化时玩法摘要保持冻结 v14；v17 单局/批量 manifest 一致，
   artifact 与嵌套单局 digest 可以离线重新验证。
5. 合法的固定身份 A/B 完整配对并由 raw count 得到五项质量 delta；缺 cohort、重复
   cohort、random role、相同指纹、布局/策略/规则/schema/trace 不一致或摘要篡改均
   fail closed。
6. Python 编译、定向 simulation、价格/观测/指纹/A-B 自动化和三个 CLI 契约通过；
   本阶段未启动 FastAPI 或 Godot，也未新增实时 API/UI。

### 风险边界

- SHA-256 证明“被摘要的输入是否相同”，不证明配置安全、Prompt 优质或运行结果正确；
  它也不是 API Key、存档兼容性或用户授权机制。
- 默认价格表只陈述“未知”。维护者填入价格前必须核对来源、币种、token 单位、
  billing model 与有效时间窗并升级 catalog version；汇总是基于 provider telemetry 的
  保守估算，不替代供应商账单。
- v1 多 attempt 日志缺少逐 attempt usage 覆盖，不能被追溯性地当作完整成本；v2 若
  provider 不返回 usage 也保持 unknown，禁止靠字符数猜 token。
- 规则模板 A/B 的 LLM、Prompt、知识库和 RAG 都 inactive。仅修改这些组件会改变
  full configuration fingerprint，但不会改变 effective fingerprint，也不能通过当前
  比较器声称规则或 Prompt 效果；真实模型 A/B 需要后续独立的调用与配对协议。
- 五项表达质量和胜负 delta 是诊断，不是自动门槛。比较器要求调用方先在两个明确的
  代码/配置快照生成固定身份 artifact；比较器本身不会管理 checkout 或实验分流。

## V4.7 新手体验与交付

### V4.7-A 已完成：首局分阶段引导

Godot 增加客户端-only `agent_town_onboarding.v1`。它不是 Python 规则状态，不写入
对局事件、存档、重放或幂等台账，也不新增 HTTP/LLM 请求。自动引导只从完整
`GET /api/game/{game_id}/state` 的玩家可见投影触发；`GameStartResponse` 没有
`player_private_info`，因此不能触发身份提示。

步骤使用固定字段 `step_id / trigger_kind / phases / roles / information_scope / title /
body`，allowlist 为：

| step_id | 触发 | 信息边界 |
| --- | --- | --- |
| `identity_and_scope` | 首次完整状态且本人身份已同步 | 仅玩家可见 |
| `night_skill` | 首次夜晚；猎人窗口是否出现仍由 Python 决定 | 仅玩家可见；目标仍由 Python 限定 |
| `sheriff_flow` | 首次警长相关阶段 | 全场公开但声明未验真 |
| `public_speech` | 首次真正轮到玩家公开发言 | 公开行动；先预览后确认 |
| `private_chat` | 首次自由活动 | 原文不会自动公开，但会影响该 NPC 后续判断 |
| `exile_vote` | 玩家存活时首次进入放逐投票 | 公开行动；Python 统一结算 |
| `post_game_review` | `GAME_OVER` | 仅赛后真值，不能倒灌实时策略 |

每局 `seen_step_ids` 在内存中去重；关闭当前步骤不会让轮询立即重弹，下一阶段仍可
继续提示。完成赛后步骤或“跳过全部”后，`user://agent_town_onboarding.cfg` 只保存
`schema_version=agent_town_onboarding.v1` 和 `automatic_guide_completed` 布尔值，明确
禁止保存 game id、身份、阵营、队友、验人、刀口、药品、守护目标、聊天或行动历史。
顶部 `?` / F1 始终可以手动重开。

引导 overlay 使用 `dialog_open` 阻止玩家移动，尺寸随 viewport 在安全上下限内调整；
弹窗内部支持 Tab / Shift+Tab 循环焦点、Enter / Space 确认、方向键翻页和 Esc 暂时
关闭。身份卡同步增加“仅你可见”，公开证据增加“全场公开”，私聊提示明确原文不会
自动公开。赛后 summary 若与最后一步同时到达会等待引导关闭再展示，避免双层焦点。

静态验收锁住七步与字段全集、六身份安全文案、完整 `/state` 接入点、GameStart 零
触发、seen 去重、`dialog_open`、F1/键盘闭环、严格布尔读取、手动引导/终局复盘竞态、
偏好保存函数的两字段 allowlist，以及没有新增 onboarding HTTPRequest。后端回归通过
真实固定身份开局逐一验证六身份的本人角色、狼队友和 `player_private_info` 投影；原有
OpenAPI、存档、事件和重放检查继续通过。

### V4.7-B 已完成：响应式与整局无障碍

Godot 客户端增加 `agent_town_responsive_layout.v1`。判档只读取物理窗口尺寸，Control
offset、弹窗 clamp 和安全边距继续使用 stretch 后的逻辑 viewport，避免把物理像素
直接写进逻辑坐标。固定分档为：

| profile | 物理窗口条件 | 当前行动宽度 | 情报抽屉宽度 | 角色卡列数 |
| --- | --- | ---: | ---: | ---: |
| `compact` | 宽度 `< 1200` | `420` | `520` | `2` |
| `default` | 宽度 `1200–1439`；或宽屏高度不足时回退 | `440` | `600` | `3` |
| `wide` | 宽度 `>= 1440` 且高度 `>= 820` | `480` | `736` | `4` |

验收样本固定为项目最小窗口 1100×650、默认窗口 1280×720 和宽屏 1600×900。
统一 resize 入口同步调整 HUD、身份卡、当前行动、情报抽屉、角色卡、开局设置、赛后
复盘、首局引导和对话框；摄像机安全区读取当前 profile 的实际侧栏宽度。角色卡保持
`160` 的逻辑最小宽度，内容过长继续在垂直滚动区内查看。该契约面向桌面 Demo，
不承诺手机布局。

整局焦点契约为 `agent_town_focus_navigation.v1`，状态固定为 `WORLD / PANEL /
TEXT_ENTRY / MODAL`：

- `WORLD` 下 WASD 和方向键控制角色；Tab / Shift+Tab 从当前可见 HUD 或面板进入并
  循环遍历可用控件。
- `PANEL` 覆盖技能、猎人、警长、发言、投票、情报和复盘。焦点只收集当前可见、
  未禁用的控件，动态显隐后修复无效焦点，并把焦点控件滚动到可见区域。
- `TEXT_ENTRY` 是明确例外：LineEdit/TextEdit 编辑时 WASD、方向键和 Space 属于文本
  输入，不会被解释成角色移动；提交或 Esc 退出后再恢复调用方或世界控制。
- `MODAL` 覆盖开局设置、NPC 对话、发言预览、赛后复盘和首局引导。模态陷阱
  （modal trap）把 Tab / Shift+Tab 限制在最上层 modal，Enter / Space 激活当前控件，
  Esc 只关闭最上层；关闭后优先
  焦点回还到打开者，打开者已隐藏或禁用时使用合法 fallback，最后才回到 `WORLD`。
- 鼠标点击控件可以切入 `PANEL` 或 `MODAL`；在非文本、非 modal 状态按 WASD 会释放
  面板焦点并切回 `WORLD`。modal 使用输入边界阻止鼠标、E、Enter 或 Space 穿透到
  小镇交互和下层面板。

浅色与深色主题都提供明确的 focus 样式；浅色控件保持黑字和浅底，UI 字号统一
`>= 12`。角色记录、公开时间线、赛后解释、引导正文和 NPC 对话内容都保留只读滚动与
键盘焦点，不要求鼠标滚轮才能查看。静态验收锁住两个 schema、三个 profile、物理窗口
判档、动态侧栏/列数、安全区、四态焦点、modal trap、焦点回还、文本输入例外、可见
focus 样式和只读滚动；Python API、规则状态、事件、存档、重放、幂等和 LLM 均未修改。

输入恢复补丁修复了 Godot 4.7 warning-as-error 下三处不安全类型推断：引导阶段匹配、
待显示引导步骤和分页 `TabBar`。此前 `main.gd` 整体加载失败时，独立 `player.gd` 仍可
处理 WASD，因而表面上像鼠标和 E 键同时失效；实际按钮连接与 E 交互回调都未注册。
core 静态检查现要求显式类型并拒绝三种已知旧写法，Godot 4.7.1 headless profile 继续
作为通用脚本加载门禁。本补丁不改变焦点契约或 Python 事实边界。

### V4.7-C 已完成（待人工封版）：CI 与源码交付

新增 `.github/workflows/ci.yml`，在 Ubuntu 24.04 与 macOS 15 上各执行两个 job：

- `offline-core` 固定 Python 3.12，从 fresh environment 安装直接依赖、执行
  `pip check` 和 `scripts/smoke_check.py --profile core`。它覆盖 Python 编译、规则、
  仿真、存档/恢复、幂等、文档与静态 Godot 契约。
- `godot-headless` 固定 Godot 4.7.1 standard（非 .NET、无 export templates），执行
  `scripts/smoke_check.py --profile godot`，验证资源导入、字体、昼夜脚本和主场景。
  无参数入口继续代表完整 smoke，保持本地命令兼容。

workflow 只有 `contents: read` 权限，checkout 不保留凭据，全部 actions 固定完整 commit
SHA。测试执行阶段设置 `ENABLE_LLM=false`、`LLM_PROVIDER=mock`、
`AGENT_TOWN_DISABLE_VECTOR_RAG=1`、`HF_HUB_OFFLINE=1`，不读取 secret、不访问真实 LLM、
不下载向量模型、不启动 FastAPI、Godot 编辑器或常驻进程；依赖和 Godot 安装阶段仍需
访问软件源。存档与 pycache 写 runner 临时目录。

Godot 4.7 的七个 `.gd.uid` 纳入源码，`.godot/` 继续忽略；`.gitattributes` 固定 LF 与
二进制字体。`docs/V4_RELEASE_CHECKLIST.md` 明确源码交付、Linux/macOS 验证、三尺寸
手工检查、隐私/存档边界、工具与完整依赖记录、LICENSE 决策、V4 开发仓库和
不可移动 tag/补丁策略。当前尚未封版；公开
[`agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0) 已由
`v4-origin` 承载开发快照，但尚未创建 `v4.0.0`。历史三个 remote 仍禁止推送，项目
当前没有根级 `LICENSE`，明确为未授予再分发许可。

### V4.8-A 已完成：开局 LLM 输出校验开关

#### 目标与契约

- `GameStartRequest` 增加默认 `true` 的 `enable_llm_validation`。旧客户端省略字段时
  保持默认最多 5 轮语义校验与纠错；关闭时只请求 1 份最终模型文本，语义校验与纠错
  均为 0 次，提取出的 `text` 直接显示。
- `GameStartResponse` 和 `GameStateResponse` 以 `llm_validation_enabled` 返回实际
  生效模式。LLM 总开关关闭或 provider 未配置时，该值固定为 `false`。
- 关闭校验时不让未校验结构化 JSON 决定游戏：Python 先生成合法计划，再把规则正文、
  公开证据和安全人物信息交给一次最终表达调用。普通白天与警上 NPC 的权威声明、
  `public_position`、怀疑值、说服力、低信息信号和技能建议都不解析未校验原文。
- 原文直出固定只有 1 次适配器请求。网络、配置、JSON 或非空 `text` 提取失败仍回退
  规则文本；传输格式解析不计作语义校验。坏坏、然然的居民 `/chat` 不读取该开关。

#### 事件、存档与重放

- 选择封印在首个 `game_created.command.start_request.enable_llm_validation`。旧事件
  缺少字段时按 `true`，不允许通过修改客户端显示在局中热切换。
- 不增加 `WolfGameState` 字段，避免旧存档的 snapshot digest、规则状态摘要和最终
  事件摘要漂移；现有旧存档无需迁移或写回即可恢复。
- 实际启用 LLM 的对局即使关闭校验仍为非确定性，只支持事件审计；
  `enable_llm=false` 且 `enable_rag=false` 的规则模板局继续支持执行式重放。

#### 验收标准

1. 省略字段与显式 `true` 均最多校验 5 轮；显式 `false` 的语义校验上限严格为 0。
2. 关闭校验时只请求 1 份最终文本并直接显示，`validation_attempts` 和
   `validation_failure_id` 为空，不写 validation failure JSONL；普通请求 observability
   仍记录这 1 次生成。
3. 未校验原文可以包含错误、矛盾、隐藏身份猜测或伪造动作，但不会成为 Python 的
   结构化计划、公开声明、立场卡、怀疑/说服力、技能建议、私聊指代或规则结算输入。
4. 四种开局组合覆盖 LLM 关闭、LLM+校验、LLM+原文直出及 provider 未配置；Godot
   请求字段、两个响应状态和局内标签保持一致。
5. `game_created` 封印请求值，旧事件缺字段默认为开启；旧存档恢复、事件链和规则
   模板 replay 均保持兼容，LLM 局不会因关闭校验而被标为可重放。
6. 常驻居民 `/chat`、玩家自由文本 Python 校验以及身份、行动、
   投票、警徽、出局和胜负规则均不改变。

#### 风险边界

- “关闭”明确代表信任并显示第一份可解析模型原文。它可能错误、矛盾或越界，也会进入
  玩家看到的公开日志、私聊记录和 NPC 文本记忆，因此可以影响真人判断和后续 LLM
  表达；这是玩家主动选择的体验取舍。
- 为保持 Python 权威边界，原文不得被任何 parser、说服力/低信息评分或私聊指代逻辑
  升级为规则事实。新增消费者若需要读取发言，必须优先使用 `decision_plan`、
  `public_position`、`planned_claims` 和其他 Python 结构化字段。

## 依赖顺序

1. V4.1-A/B 先证明玩家输入和水平边界可测。
2. V4.2 已建立单一事件事实源和规则模板重放。
3. V4.3-A 已在事件事实源上完成原子存档与恢复。
4. V4.3-B 已增加外部幂等 key、结果台账与重复结算保护。
5. V4.4-A/B 已生成统一公开证据投影、承诺生命周期和中立矛盾候选。
6. V4.5-A 已使用保存的决定、公开证据和明确标注的赛后真值生成保守解释。
7. V4.6-A/B 已建立公开-only 表达质量基线、完整/生效配置指纹、保守 LLM 成本口径
   和规则 artifact 配对 A/B。
8. V4.7-A/B 已完成客户端首局安全引导、三档响应式与整局键盘无障碍；V4.7-C 已完成
   Python 3.12 / Godot 4.7.1 双平台 CI、分层 smoke、封版清单和跨平台源码交付准备。
   开发仓库与首次开发快照由用户在 2026-07-23 批准；正式 `v4.0.0` tag 仍等待门禁
   完成后另行批准。
9. V4.8-A 已把狼人杀局内 LLM 输出做成开局最多 5 轮校验或生成 1 次、校验 0 次的
   原文直出选择，同时保持 Python 规则结算、事件封印、旧存档兼容和居民聊天边界。

## 变更记录

- `2026-07-23`：完成 V4.8-A `enable_llm_validation` 开局选择；默认最多 5 轮，
  关闭时生成 1 次、语义校验与纠错 0 次并直出原文，`llm_validation_enabled` 返回
  实际模式。选择封印在
  `game_created.command.start_request.enable_llm_validation`，不修改 `WolfGameState`，
  旧存档与旧事件默认兼容；未校验文本与 Python 权威规则消费者隔离，居民 `/chat`
  保持不变。
- `2026-07-20`：从 `v3.0.0` 创建本地 `v4-development`。
- `2026-07-20`：完成 V4.1-A 三档策略、合法玩家视图、simulation v14、
  metrics v5、身份配对 benchmark v1、CLI 和自动化验收。
- `2026-07-20`：正式矩阵补出双查杀规则边界；合并狼队互踩主叙事与通用验人
  回应的优先级，并增加固定 seed 回归。
- `2026-07-20`：完成 V4.1-B 严格玩家发言理解、无副作用预览、锁内指纹复验、
  Godot 确认/修改流程，以及逗号子句验人纠错。
- `2026-07-20`：完成 V4.2 统一规则事件、SHA-256 链、终局导出、隔离执行式重放、
  v15 仿真集成及 LLM/RAG 审计边界。
- `2026-07-20`：完成 V4.3-A 私有原子存档、规则入口事务回滚、严格多层完整性/
  恢复配置校验、手动与 lifespan 启动恢复、终局归档边界及 simulation/replay 隔离。
- `2026-07-20`：完成 V4.3-B 全部规则写入口外部幂等 key、持久结果台账、冲突与
  响应丢失恢复、Godot 失败复用/成功清理、账本篡改测试及存档后固定身份池重放。
- `2026-07-20`：完成 V4.4-A 版本化公开证据时间线、公开安全稳定 ID、已公布票型
  门控、夜死原因脱敏、NPC/UI 同源消费和隐藏信息不变性测试。
- `2026-07-20`：完成 V4.4-B 警徽流承诺六态、四类中立矛盾候选、公开-only 无
  真值关系层、NPC/UI 同源分析 ID，以及合理修订/条件失效不误报测试。
- `2026-07-20`：完成 V4.5-A 终局决定解释、三份严格 schema、五类错误归因、
  跨日公开证据引用、赛后真值隔离、Godot 第三复盘页和旧空台账存档兼容。
- `2026-07-20`：完成 V4.6-A 六个版本化表达质量契约、严格报告 schema、公开-only 隐藏身份不变性、
  逐字/模板/近重复、信息增量、证据引用、人设代理、simulation v16 聚合和 CLI 摘要。
- `2026-07-21`：完成 V4.6-B 完整/active-only 实验指纹、LLM exact Prompt/config
  脱敏摘要、v1 兼容观测 v2、provider attempt usage、版本化 unknown-safe 成本、
  simulation v17 和严格固定身份 artifact A/B；规则报告明确不评价 LLM/Prompt 效果。
- `2026-07-21`：完成 V4.7-A 客户端-only `agent_town_onboarding.v1`，七步只在完整
  `/state` 后按阶段去重触发，六身份说明与公开/私密/赛后边界明确；增加 F1 手动重开、
  弹窗键盘闭环和只保存完成布尔值的本地偏好，后端规则与 schema 保持不变。
- `2026-07-22`：完成 V4.7-B `agent_town_responsive_layout.v1` 与
  `agent_town_focus_navigation.v1`；按物理窗口选择 compact / default / wide 三档，
  同步侧栏、角色卡列数和弹窗安全边距，并以 WORLD / PANEL / TEXT_ENTRY / MODAL
  四态完成整局焦点陷阱、焦点回还、鼠标/WASD 切换、文本输入例外、可见焦点样式和
  只读键盘滚动。
- `2026-07-22`：完成 V4.7-C Ubuntu 24.04 / macOS 15 CI，固定 Python 3.12 与
  Godot 4.7.1；smoke 增加 `--profile core` / `--profile godot`，测试执行期禁真实
  LLM、向量下载和服务启动。纳管 Godot UID、LF 规则并新增
  `docs/V4_RELEASE_CHECKLIST.md`。交付机制已完成但项目尚未封版；当时尚未创建 V4
  remote、仓库或 tag。
- `2026-07-22`：修复 Godot 4.7 将三处类型推断警告视为错误而导致 `main.gd` 整体
  加载失败的问题；恢复鼠标按钮和 E 键 NPC 交互，并用 core 静态断言与 Godot
  headless 加载门禁防止回归。Python 规则、接口和身份权限均未改变。
- `2026-07-23`：创建公开开发仓库
  [`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0)，只以
  `v4-origin` 推送 `v4-development` 开发快照。未创建 `v4.0.0`，历史三个 remote
  继续禁推；`3.0总结/` 保留为未跟踪本地历史资料，项目未添加根级 `LICENSE`，明确
  为未授予再分发许可。
