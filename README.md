# Agent Town Demo V5

一个用于学习游戏开发的 Godot 4 + Python FastAPI AI NPC 原型。

后端、DeepSeek LLM、Godot 和自检命令统一记录在 [`COMMANDS.md`](COMMANDS.md)。

项目当前把两条玩法合并到同一个 Demo 中：玩家可以在扩建后的 2D 小镇里移动、随时和坏坏、然然两名常驻居民聊天，也可以通过控制面板进行一局 1 名玩家 + 11 名 NPC 的十二人狼人杀。

## V5 NPC 独立推理与本地策略模型

V5 从不可移动的 `v4.0.0` 源码基线开始，主题不是重写狼人杀规则或训练语言表达，而是
让每个 NPC 在自己的合法视野内维护独立的
`观察 → 假设 → 信念 → 候选行动评分`。Python 仍是身份、权限、合法候选、确定性采样、
事件、出局和胜负的唯一权威；DeepSeek 只负责合法上下文内的表达和可选输出校验。

当前已完成的 V5 最小闭环：

- 退水窗口关闭时，为所有仍在警上候选列表的人追加公开
  `continue_campaign` 事实，避免 NPC 只能在警长投票后才看到时序。
- `backend/app/npc_reasoning.py` 为每个 NPC 生成 actor-scoped hypothesis、role belief、
  contradiction signal 和下一步 plan；`shadow/local` 与离线场景会额外计算有界可能世界
  边际。好人观察不会带入其他人的隐藏身份。单个预言家 claimant 会保留“未公开真
  预言家”世界，退水证据只在同一警上窗口生效，不会跨天重复推理。
- 双预言家“B 给 A 金水、A/B 都继续竞选”会生成
  `seer_golded_persistent_counterclaim` 与 `sole_consistent_seer_claimant`，公开证据只
  标记待核对矛盾，不把它直接当身份真值。
- `backend/app/npc_policy.py` 只接收已有合法放逐候选的固定特征。`rule` 使用原规则，
  `shadow` 计算本地模型但仍按规则行动，`local` 才由本地模型接管候选概率；模型失败
  自动回退规则。
- 已提供 NumPy 训练/数据脚本和好人/狼人 `backend/policy_artifacts` 产物，模型只替换
  “候选行动评分”层，不生成新规则动作；V1 线性 artifact 保持兼容，当前正式产物为
  V2 32 隐层 `tanh` MLP。四个策略面各拥有独立的好人/狼人产物：放逐投票
  （`exile_vote`）、警长投票（`sheriff_vote`）、警长归票（`sheriff_nomination`，
  均 26 维 sheriff 风格特征）与夜间目标（`night_target`，27 维
  `npc_night_target_features.v1`，覆盖狼刀/守卫/查验/猎人；女巫毒药仍保持 V5.4-A
  信念路径）。local 模式按任务替换候选评分层，护栏与规则回退保持一致。放逐训练集
  保留 280 条规则 teacher，并叠加 40 条聪明好人 v2
  与 59 条原聪明狼人 v1 审计标签，共 379 条；其中 99 条审计标签已于 2026-08-04
  由 tonystark 逐条人工确认纳入训练集；警长投票/归票/夜技训练集各为 130 局规则
  仿真 855 / 734 / 1323 条。
- `backend/training/README.md`、严格 validator 和 label merger 留出了外部喂数口：
  observation 与人工标签按 `observation_digest` 分离合并，拒绝过期摘要、非法候选、
  概率错误和重复样本；validator 能拒绝结构性非法输入，但无法从 25 个数值语义上
  证明用户没有编码隐藏身份，因此推荐只使用脚本生成的 actor-scoped observation。
- `backend/training/generate_reasoning_scenarios.py` 固化 6 条高价值逻辑场景，覆盖对跳
  金水、单 claimant、退水、跨日证据、已知角色冲突和改验结果，并可由离线 runner 自动
  检查必需/禁止 signal 与预言家概率边界。
- `generate_policy_review_queue.py` 可从规则教师记录中筛选逻辑冲突候选，生成不含隐藏
  真值的人工决策审阅队列；填写后由 `convert_policy_review_queue.py` 转成严格标签。
- 多名审阅者的标签可通过 `consensus_policy_labels.py` 计算共识；分歧样本会进入报告，
  不会静默混入训练集。
- 当前已生成一份 `codex_logic_review` 启发式 bootstrap 标签用于验证管线，但明确标记为
  `needs_human_review`，不会被当作人工金标准。
- `compare_teacher_labels.py` 可在训练前量化人工标签与规则 soft teacher 的差异，帮助
  发现“标签只是重复规则”或“启发式偏离过大”的问题。
- `review_dashboard.py` 提供离线浏览器审阅向导：逐条展示 teacher 与审计推荐，支持
  一键采纳或手填目标号回车确认，进度本地保存并导出 JSONL。
- `audit_policy_review_queue.py` 的聪明好人标签已升级为 teacher-anchored v2：无硬公开
  逻辑冲突时逐项保持 rule teacher；出现冲突或唯一一致预言家信号时才小幅纠偏、保护
  唯一一致预言家并向已有归票锚点收拢。聪明狼人仍逐项保留 v1 标签与 rubric。
- `calibrate_policy_temperature.py` 可在 shadow 轨迹上扫描模型概率温度；温度尚未封入正式
  游戏配置。
- `AGENT_TOWN_NPC_POLICY_TEMPERATURE=0.65` 已支持 shadow/local 的显式温度封印，默认值仍为
  `1.0`，不会影响 rule 模式。
- `AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE=0.80` 已支持 local 夜间信念消费的置信度门禁：
  狼刀、守卫、预言家查验、女巫用毒和猎人开枪只有在目标角色信念 `confidence` 达到阈值
  时才消费 actor-scoped belief，否则回退到与 rule 完全一致的选择；`rule/shadow`
  行为不受影响，所有夜间候选和最终结算仍经过 Python 门禁。
- `npc_policy_entropy_guard.v1` 在采样前约束模型扰动：普通好人逐项等于 teacher；
  只有模型确实增加公开冲突对象票仓、且不增加唯一一致预言家票仓时，硬逻辑场景才
  允许有界纠偏；所有阵营继续受归一化熵与总变差上限约束。trace 同时保留原始模型、
  护栏后概率与实际有效混合比例。
- 当前 379 条 MLP 使用同 seed `20260727–20260736`、默认温度 `1.0`、请求混合 `1.0`
  完成 10 局 shadow 和 local 金丝雀。Shadow 共 205 条轨迹、0 fallback，原始模型
  38 次改变 teacher 首选，护栏后为 0；温度校准确认 softmax 首选与温度无关，`1.0`
  时模型与规则 teacher 的 KL 最低。消融确认 `blend≤0.25` 时放逐 MLP 尚未改变
  采样票（指标变化来自 V5.4-A 夜间信念消费）；放宽狼侧熵/总变差护栏并提高混合到
  `0.5`（护栏封顶）后，模型开始真正参与投票。10 局金丝雀为好人胜场 `2→3`、误投
  `62.6%→58.3%`，放逐熵 `25.1%→26.4%`、跨日保持 `77.4%→87.5%`；扩展 30 局
  seed `20260601–20260630` 胜率持平、其余四项核心指标改善：胜场 `43.3%→43.3%`（持平）、误投
  `48.3%→43.8%`、投狼概率质量 `53.3%→58.2%`、放逐熵 `30.3%→28.0%`、跨日保持
  `66.2%→78.2%`，重放 `30/30`、零 fallback，金丝雀门槛通过。默认模式已随人工
  标签清洗（tonystark 确认 99 条）与模型重训于 2026-08-04 正式切换为 `local`；
  `rule` 仍可通过环境变量或开局选项显式选择。同日完成平衡微调：6 名偏好人 NPC
  的 `decision_variance` +0.20，好人胜率约 43%（更接近五五开），误投率仍远低于
  rule。
- 规则发言模板已加入确定性变体：同一意图（查杀回应/防守/施压/观察）按局内种子与
  发言者稳定选择不同措辞。30 局离线基线模板重复率从 `25.2%` 降到 `13.1%`、跨角色
  近重复从 `5.7%` 降到 `2.2%`，人设区分度从 `75.0%` 升到 `81.0%`，玩法指标不变。
- `extract_policy_disagreements.py` 可从大批量 shadow 轨迹中提取规则与模型分歧最大的样本，
  用于下一轮重点审计。
- `analyze_policy_disagreements.py` 会检查分歧是否符合聪明好人/聪明狼人的基本不变量，
  把投狼队友或未分类样本单独标出。
- 夜间查验、守护、狼刀、女巫用毒和猎人目标在 `shadow` 中计算 actor-scoped belief，
  只有 `local` 才消费该评分，并受 `AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE` 置信度门禁
  约束；`rule/shadow` 保留 V4 实际行动基线，所有夜间候选和最终结算继续经过
  Python 门禁。
- `wolf_sheriff_campaign.v1` 把狼人警上阵容扩为三种可复现编排：单狼悍跳、双狼辅助
  站边、双狼公开拉开距离。双狼局由假预言家和一名非玩家狼同时上警；辅助狼不跳
  预言家，只根据当时已经公开的声明表达支持或质疑，发言后固定退水，避免占用最终
  警长票仓。白天原有的集中、分票掩护、倒钩、救队友、卖队友和放弃悍跳狼策略保留。
- V5 当前离线仿真 schema 为 `agent_town_simulation.v18` /
  `agent_town_simulation_batch.v18`，游戏摘要 digest 投影为
  `agent_town_simulation.v15`；V4 的 v17/v14 只作为历史 artifact 口径保留。

完整 V5 主题、里程碑、数据划分和验收门槛见 [`docs/V5_ROADMAP.md`](docs/V5_ROADMAP.md)。

## macOS 试玩包

当前 V5 可以从项目根目录生成 Apple Silicon 试玩包：

```bash
backend/.venv/bin/pip install -r backend/requirements-packaging.txt
scripts/package_macos.sh
```

构建结果写入 `dist/AgentTownDemo-V5-macOS-arm64/`，同时生成同名 zip 和 SHA-256。
包内包含 Universal 2 Godot 客户端、arm64 FastAPI 独立后端、双击启动器和配置说明；
默认关闭真实 LLM 与向量下载，断网可运行，且不会打包 `backend/.env`、API Key、私有
存档或聊天记忆。存档写入
`~/Library/Application Support/Agent Town Demo/`。

本地测试包使用 ad-hoc 签名，没有 Apple Developer ID 公证；通过网络分发时仍可能触发
Gatekeeper。完整构建、模板安装、启动和验收说明见
[`packaging/macos/README.md`](packaging/macos/README.md) 与 [`COMMANDS.md`](COMMANDS.md)。

## Windows x64 试玩包

在已安装 Godot 4.7 Windows x86_64 Export Templates 的 macOS 构建机上运行：

```bash
scripts/package_windows.sh
```

构建结果为 `dist/AgentTownDemo-V5-Windows-x64/`、同名 ZIP 和 SHA-256。ZIP 内包含
64 位 Godot 客户端、Python 3.12 便携后端和双击启动器；玩家无需安装 Godot、Python
或 pip。解压完整 ZIP 后双击 `Start Agent Town Demo.bat`，存档和日志写入
`%LOCALAPPDATA%\Agent Town Demo\`。

默认配置断网可玩且不包含 `.env`、API Key 或私有存档。当前 EXE 未做 Authenticode
签名，可能触发 SmartScreen；跨平台构建、PE 架构和归档完整性已在 macOS 验证，
正式分享前仍应在 Windows 10/11 真机完成启动与图形交互验收。完整说明见
[`packaging/windows/README.md`](packaging/windows/README.md) 与
[`COMMANDS.md`](COMMANDS.md)。

## V4.0.0 源码封版

V4 于 `2026-07-24` 归档到公开仓库
[`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0)，封版标签为
`v4.0.0`。封版只代表源码与自动化基线冻结，不包含可执行包：V4 标签中没有
`export_presets.cfg`，Linux 图形交互也没有单独的人工签署；Ubuntu 24.04 与 macOS 15
上的 core/Godot headless 矩阵在标签创建前必须全部通过。当前 V5 工作区已另行增加
macOS 与 Windows 导出预设和本地试玩包，不回写或移动 V4 标签。

根目录没有项目级 `LICENSE`，因此源码公开可读不代表获得开源或再分发许可；字体的
`OFL.txt` 只覆盖对应字体。`3.0总结/` 继续作为本地历史资料排除在 V4 源码归档之外。
`origin`、`v2-origin`、`v3-origin` 没有接收任何 V4 提交或标签，V4 只发布到
`v4-origin`。后续 V5 必须从 `v4.0.0` 新建本地开发分支，不能继续修改或移动 V4 标签。

## V4.8-A 开局 LLM 输出校验开关

狼人杀开局设置现在把“启用 AI NPC 表达”和“启用 LLM 输出校验”分开。开局请求新增
`enable_llm_validation`，默认 `true`，因此旧客户端继续使用最多 5 轮语义校验与纠错。
设为 `false` 时只请求 1 份模型文本，语义校验与纠错均为 0 次，提取出的 `text` 会直接
显示；网络、配置、JSON 或 `text` 提取失败时仍使用 Python 规则文本。开局和完整状态
响应使用 `llm_validation_enabled` 返回本局实际生效的模式。

关闭输出校验后，原文可能出现错误、矛盾、越界或虚构信息，这是玩家主动选择的体验
模式。Python 会先确定合法的结构化策略，并且不会把未校验原文重新解析成权威声明、
公开立场、怀疑值、技能建议或规则动作；身份、合法行动、投票、警徽、出局和胜负仍只
由 Python 结算。原文仍会作为玩家实际看到的台词进入公开日志或私聊记录，因此可能真实
影响玩家判断，但不能直接改写规则状态。原文直出路径只发起 1 次适配器请求，不执行
第 2 次网络重试或语义纠错。

选择会随 `game_created.command.start_request.enable_llm_validation` 封印在事件链中；实现不向
`WolfGameState` 增加字段，旧事件缺少该键时按开启处理，所以旧存档的快照和规则状态
摘要不会因本功能漂移。实际启用 LLM 的局即使关闭输出校验仍只支持事件审计，不会被
误标为确定性重放。坏坏、然然等常驻居民使用的普通 `/chat` 不属于某一局狼人杀，
不受 `enable_llm_validation` 影响。

## V4.7-C CI 与封版交付

V4.7-C 的交付机制已经完成，并作为 `v4.0.0` 源码封版门禁。新增的
`.github/workflows/ci.yml` 在 Ubuntu 24.04 与 macOS 15 上使用 Python 3.12，分别运行
离线核心检查和固定 Godot 4.7.1 的 headless 检查：

- `offline-core` 从空环境安装 `backend/requirements.txt`、执行 `pip check` 和
  `scripts/smoke_check.py --profile core`，覆盖 Python 编译、规则、仿真、存档、幂等、
  文档和静态 Godot 契约。
- `godot-headless` 执行 `scripts/smoke_check.py --profile godot`，覆盖资源导入、中文
  字体、昼夜脚本和主场景加载。默认无参数仍是兼容的完整 smoke。
- 测试阶段固定关闭真实 LLM 和向量模型下载，不读取 secret、不启动 FastAPI、Godot
  编辑器或常驻游戏进程；依赖和 Godot 安装阶段仍需要正常访问软件源。
- Godot 4.7 的七个 `.gd.uid` 进入源码交付，`.godot/` import cache 继续忽略；
  `.gitattributes` 固定文本 LF，降低 Linux/macOS fresh clone 差异。

完整治理、双平台、隐私、手工三尺寸、许可证边界和封版记录见
[`V4 封版清单`](docs/V4_RELEASE_CHECKLIST.md)。公开源码仓库仅由 `v4-origin` 指向，
`v4.0.0` 是不可移动的 V4 封版标签；三个历史 remote 保持只读。根目录没有项目
`LICENSE`，因此源码公开可读不代表获得再分发许可。

## V4.7-B 响应式布局与整局键盘导航

Godot 客户端现在同时发布 `agent_town_responsive_layout.v1` 和
`agent_town_focus_navigation.v1`。本轮只调整显示与输入边界，不改变 Python 返回的身份、
知识权限、合法行动、投票、警徽、出局或胜负：

- 布局按物理窗口而不是拉伸后的逻辑画布选择 `compact / default / wide`：宽度小于
  `1200` 为 compact，`1200–1439` 为 default，宽度至少 `1440` 且高度至少 `820` 为
  wide。项目最小、默认和宽屏验收尺寸分别是 `1100×650`、`1280×720`、`1600×900`。
- 三档“当前行动”宽度为 `420 / 440 / 480px`，“情报”宽度为
  `520 / 600 / 736px`，角色卡为 `2 / 3 / 4` 列；HUD、身份卡、设置窗口、复盘边距、
  行动面板高度和历史记录高度也由同一 profile 调整，并按可用逻辑高度限幅。
- 焦点分为 `WORLD`、`PANEL`、`TEXT_ENTRY`、`MODAL`。Tab / Shift+Tab 在当前范围
  循环，方向键在按钮间移动或滚动正文，Enter / Space 激活控件，Esc 关闭当前面板或
  弹窗；非文本状态按 WASD 或点击世界会立即回到角色移动。
- 设置、首局引导、发言提交前预览、NPC 对话和赛后复盘都会锁住世界输入、限制焦点
  不离开弹窗，并在关闭后还给打开它的控件；原控件已隐藏或禁用时使用安全入口，仍
  不可用时才回到世界。发言预览和 NPC 对话也会阻止鼠标穿透到底层 UI。
- 默认 UI 字号提升到 `14px`，显式字号不低于 `12px`；浅色、深色和对话控件都有
  高对比金色焦点框。情报、关键公开信息、引导、复盘和 NPC 回复滚动区均可用键盘
  到达，玩家行动记录保持只读但可聚焦滚动。
- Godot 4.7 会把部分从 `Variant` 或集合返回值推断类型的警告升级为脚本加载失败；
  `main.gd` 的引导阶段判断、待显示步骤和分页栏现已使用显式类型。这样主脚本不会因
  这三处推断失败而整体失效，避免出现“独立玩家脚本仍能 WASD，但按钮和 E 交互全部
  无响应”的假性输入故障。

本轮不新增 HTTP、Pydantic、规则、事件、存档、重放或 LLM 字段，也不承诺手机布局。
V4.7-C 已在其后补齐 CI、封版清单与跨平台源码交付边界。

## V4.7-A 首局分阶段引导

Godot 现在提供客户端专属的 `agent_town_onboarding.v1`，不新增后端规则状态，也不
改变任何对局接口：

- 自动引导只在完整 `GET /api/game/{game_id}/state` 成功后评估；开局 POST 的精简
  响应不会触发。轮询刷新使用每局 `seen_step_ids` 去重，不会反复弹出同一步。
- 七个白名单步骤按真实流程出现：`identity_and_scope`、`night_skill`、
  `sheriff_flow`、`public_speech`、`private_chat`、`exile_vote` 和
  `post_game_review`。只有轮到玩家发言、玩家仍可投票等条件满足时才显示对应提示。
- 六种身份说明只根据 Python 已经合法投影给玩家本人的身份选择文案；身份、狼队友、
  验人、刀口、药品、守护和行动历史均标记为“仅你可见”。公开声明明确标记为
  “全场公开但未验真”，私聊原文不会自动公开，但会影响该 NPC 后续判断。
- 引导弹窗加入现有 `dialog_open` 安全区，打开时玩家停止移动。支持 Tab / Shift+Tab
  循环焦点、Enter / Space 确认、方向键翻页、Esc 暂时关闭；顶部 `?` 或 F1 可随时
  手动重开全部步骤。
- `user://agent_town_onboarding.cfg` 只保存
  `schema_version=agent_town_onboarding.v1` 和 `automatic_guide_completed` 布尔值，不保存
  game id、身份、队友、验人、聊天或
  其他对局事实。完成或跳过后仍可按 F1 手动查看。

本阶段没有新增 HTTP 请求、LLM 调用、Python 规则、事件、存档或幂等字段。全局
响应式布局与整局键盘导航已由 V4.7-B 完成，CI 和封版清单已由 V4.7-C 补齐。

## V4.6-B 指纹、LLM 成本与只读配对 A/B

离线仿真和脱敏 LLM 观测现在共享一套可复现、不可反查原文的实验身份：

- `experiment_fingerprint.v1` 只输出组件 SHA-256，不输出 Prompt、知识库正文、endpoint
  凭据或 API Key。`configuration_fingerprint` 覆盖完整配置，
  `effective_fingerprint` 只覆盖当前执行模式真正生效的组件。
- 规则模板仿真的 rules/roles、NPC profiles、tuning、输出 schema 和玩家 policy 为
  active；Prompt catalog、知识库、LLM 请求配置和 RAG 为 inactive。这样完整配置漂移
  仍可追踪，但未启用的 LLM/Prompt 变化不会被冒充成规则玩法变化。
- 真实 LLM 请求在 `LLMClient` 边界对本次最终 system prompt 和安全配置计算摘要，
  写入 `llm_observation.v2`；不保存 prompt 本身。`llm_observability_summary.v2`
  兼容读取历史 v1，并拆分 adapter retry 与 semantic retry，报告 token usage 状态、
  provider attempt 覆盖率和 prompt/config 指纹覆盖率。成功请求必须至少有一次 provider
  attempt，retry 数严格等于 `attempt_count - 1`；公开 LLM 状态只返回移除 URL 用户信息、
  query 和 fragment 后的 endpoint identity，避免配置 URL 中的凭据泄漏。
- `llm_price_catalog.v1` 与 `llm_cost_summary.v1` 使用版本化本地价格口径，并封印
  price catalog 指纹。默认 `deepseek-v4-flash` 条目明确为 `unknown`，不是官方报价、
  也不是零成本；只要任一可计费请求的模型、usage 或价格未知，总成本就是 `null`，
  已知部分仍单独保留。
- `agent_town_artifact_ab.v1` 只比较两组已经生成并通过完整性校验的 v17 规则仿真
  artifact。它严格按固定 `seed + actual player role` 配对，并要求同布局、策略、规则、
  schema 和 trace 口径；五项 V4.6-A 指标先汇总原始分子/分母再比较。报告固定
  `comparison_mode=rule_only_artifacts_no_llm`、`llm_evaluated=false`、
  `prompt_effect_evaluated=false`，不会把规则模板差异说成真实
  Prompt 或模型效果。

仿真已升级为 `agent_town_simulation.v17` /
`agent_town_simulation_batch.v17`，CLI 会打印 `[EXPERIMENT]`。冻结的
`gameplay_digest_projection_version=agent_town_simulation.v14` 与
`agent_town_metrics.v5` 不变。A/B 比较器本身不切换代码或配置；应分别在两个配置或
代码快照生成固定 `--player-role` artifact，再用
`scripts/compare_simulation_artifacts.py` 做只读比较。具体命令见
[`COMMANDS.md`](COMMANDS.md)。

## V4.6-A NPC 表达质量离线基线

无 HTTP 仿真现在会在终局生成严格的 `npc_speech_quality.v1`，批量聚合为
`npc_speech_quality_batch.v1`。底层还固定
`npc_speech_normalization.v1`、`npc_speech_quality_observation.v1`、
`npc_speech_actor_quality.v1` 和 `npc_speech_actor_quality_batch.v1`，便于后续版本
对比时明确口径。

- 统计固定 `scope=npc_public_speeches_only`、
  `truth_scope=public_only_no_role_truth`：只评价已经公开的 NPC 发言及其结构化公开
  依据。玩家发言只作为此前公开信息参与增量比较，不读取其他席位真实
  `role/camp`、私有 belief 或赛后阵营标签。
- 文本先按 NFKC、大小写和标点归一化；模板比较进一步去掉公开姓名、座位号和数字。
  `npc_speech_quality` 子报告只保存 SHA-256、字符数和结构化信息原子，不保存原始
  发言正文；仿真其他既有赛后审计字段不属于该 truth scope。
- 指标同时保留逐字重复、去目标模板重复、跨角色模板重复，以及阈值
  `near_duplicate_threshold=0.82` 的字符 trigram Jaccard 近重复。原始 count、pair
  分母和 rate 同时输出，避免只看百分比误判小样本。
- 信息增量只从随该条发言保存的 position/plan 中提取目标、立场、追问、验证点、
  暂票、claim option 和女巫建议；证据引用独立统计 RAG 标题和 signal/plan/立场引用，
  不从自由文本猜事实，也不把终局按天聚合的 `public_claims` 回填到更早发言。
- 人设代理统计配置口头禅/彩蛋命中，并以跨角色模板平均相似度的补数给出
  `persona_differentiation_score`。它只是可复现的表面差异代理，不等同于真人盲评。
- 批量报告先累加原始计数与相似度 sum 再计算加权比率，并保留按 NPC 聚合；CLI 会
  打印 `[SPEECH-QUALITY]` 摘要。

V4.6-A 当时把仿真升级为 `agent_town_simulation.v16` /
`agent_town_simulation_batch.v16`；V4.6-B 当前为 v17。冻结的
`gameplay_digest_projection_version=agent_town_simulation.v14` 和
`agent_town_metrics.v5` 保持不变。该层只在终局离线诊断，不请求 LLM、不改变
FastAPI/Godot 实时接口、规则决策、存档或重放。V4.6-B 已把 NPC 人设等完整配置
纳入实验指纹，跨时间比较应先核对相同的配置或明确作为两个实验 arm。

## V4.5-A 可解释赛后决策复盘

终局 `GET /api/game/{game_id}/summary` 新增严格的
`post_game_explainable_review.v1`，每条决定为 `post_game_decision_review.v1`，引用
跨日公开记录时使用 `post_game_evidence_reference.v1`。只有 Python 已把阶段封印为
`GAME_OVER` 并确定 winner 后才会生成；进行中的 `/state`、NPC 知识和公开证据接口
不含这份赛后真值。

- 解释覆盖公开发言、放逐投票、夜间技能和猎人开枪，展示“当时保存了哪些依据、
  做了什么选择、赛后真实身份是什么、后来有哪些跨日公开记录可核对”。
- 每条有稳定 `review_id`，固定 `post_game_truth_unlocked=true`；根级
  `truth_scope=post_game_truth_unlocked`，并保存完整评价和错误分类计数。
- `knowledge_scope=recorded_basis_plus_prior_day_public_evidence`：只把更早日期的公开
  证据称为当时可见；同日只有随决定保存的 RAG、signal、立场卡和连续性理由可作为
  依据。旧集合没有逐条同日事件序号时会明确写出限制，不推测隐藏思维链。
- 错误严格区分 `deceived / insufficient_evidence / continuity_break /
  skill_misuse / deterministic_variance`。只有实际保存了狼人失实验人信号才归为
  受骗；狼人决定按阵营策略单列，不用好人识狼标准评分。
- Godot 全屏复盘新增“解释复盘（赛后）”页，先显示赛后真值警告，再分开展示当时
  依据、评价、真实身份、解释和后来证据。

投影只读且确定，不写回 `WolfGameState`，不会改变规则摘要、存档、幂等结果、重放
或任何实时决定。V4.6-A 已在独立的离线仿真层建立表达质量基线。

## V4.4-B 承诺生命周期与中立矛盾候选

进行中的 `GET /api/game/{game_id}/state` 在 V4.4-A 时间线旁新增只读的
`public_evidence_analysis.v1`。它只比较同一局已经公开的说法、修订和规则动作，
根级 `truth_scope=public_only_no_post_game_truth`；不会读取真实身份、阵营、夜间
责任人、声明内部来源、胜负或赛后真值。

- 每个警徽流版本生成一条 `public_commitment_state.v1`，用稳定
  `commitment_id` 关联原始 `source_evidence_id`，并保留替代或解决它的公开证据
  ID。生命周期状态为 `active / superseded / fulfilled / invalidated /
  undetermined / contradicted`。
- 生命周期只检查警徽流的首段验人目标与公开移徽/撕徽分支。到期前正常修订记为
  `superseded`；承诺人、目标或公开分支不可用记为 `invalidated`；缺少可观察到的
  公开后续记为 `undetermined`，都不会自动生成矛盾结论。
- `public_contradiction_candidate.v1` 只生成四类待人工核对项：身份声明变化、同一
  目标验人结果变化、实际公开验人目标与警徽流首段目标不同，以及警徽动作落在
  已公布分支之外。每项保存前后两个 evidence ID，固定
  `review_status=needs_review`、`judgment=none`；合理修订和暂时/最终归票变化不算
  矛盾候选。
- `fulfilled` 只表示公开后续与公开计划相符，`contradicted` 只表示两条公开记录
  表面不一致；两者都不证明声明为真或角色属于任何阵营。
- NPC 合法知识直接引用同一批 commitment/candidate ID。Godot 公开记录页分开展示
  承诺状态和矛盾候选，并明确提示“需核对，不代表阵营判断”。
- 分析绑定与时间线相同的 `projected_event_sequence`，重复生成结果相同且不写回
  `WolfGameState`，因此不改变规则摘要、存档、幂等结果或确定性重放。

V4.5-A 已在游戏结束后把保存的决定、公开证据和明确标注的赛后真值组合成解释；
V4.4-B 的进行中接口仍保持无真值边界。

## V4.4-A 统一公开证据时间线

进行中的 `GET /api/game/{game_id}/state` 现在返回
`public_evidence_timeline.v1`；其中每条记录为 `public_evidence_item.v1`。它把原先分散
在身份/技能声明、验人说法、警徽流、警长报名与退水、警长票、暂时/最终归票、
警徽动作、猎人动作、已公布放逐票和出局结果中的公开信息合并为一个只读投影。

- `claim / commitment / confirmed_action` 分别显示为 `◇ / ◆ / ●`。声明和承诺的
  `verification` 永远是 `unverified`；`confirmed` 只确认公开动作已经发生，不确认
  声明者身份、验人说法或警徽流推断为真。
- 每项有只由公开结构生成的稳定 `evidence_id` 和连续 `sequence`；整条时间线以
  `projected_event_sequence` 绑定当前规则事件游标。旧公开记录没有逐项事件来源时，
  API 不伪造 provenance。
- 尚未结算的玩家/NPC 放逐票不会进入时间线；公布后才生成 `exile_ballot`。
  狼刀与毒药统一显示为“夜间出局（公开结果不区分原因）”，不返回隐藏原因、
  行动者或声明内部来源。
- NPC 的合法公开知识与 Godot 的关键信息/公开记录面板消费同一批证据 ID。Godot
  仍在时间线下方保留最近公开播报，方便查看阶段提示。
- 时间线由现有事件封印后的规则状态即时生成，不写回 `WolfGameState`，不改变
  `rule_state_digest`、存档 schema、幂等结果或确定性重放。

V4.4-B 已在这份稳定公共基线上增加承诺生命周期和中立矛盾候选，同时继续禁止
自动判狼或把赛后身份真值混入进行中接口。

## V4.3-B 幂等命令与重复结算保护

狼人杀 20 个开局后规则写入口现在都接受可选 `idempotency_key`。契约版本为
`game_command_idempotency.v1`：key 在同一 `game_id` 内唯一，必须是 8–160 位，
首位为 ASCII 字母或数字，其余可用字母、数字、点、下划线、冒号或连字符。第一次带 key 的请求会把规则事件、
`game_command_result.v1` 结果台账和完整状态放入同一次原子存档提交。

- 同一局中，同 key、同端点、同 payload 会直接返回第一次提交的响应 payload，
  不重新检查已推进的阶段、不追加事件，也不重写存档。
- 同 key 被不同端点或不同 payload 复用时返回 HTTP 409，状态、事件和磁盘零变化。
- 结果台账绑定请求摘要、响应摘要、响应模型、事件序号/类型/摘要和原响应；恢复时
  逐项校验。台账、事件或响应任一被改，即使重算完整快照摘要也会拒绝恢复。
- 如果原子替换前失败，内存事件和结果台账一起回滚；如果存档已经提交但响应丢失，
  后端重启恢复后仍会在阶段校验前命中原结果，因此夜间结算、猎人、警长、投票、
  发言和私聊不会产生第二次效果。
- 如果丢失的是结束对局的最后响应，终局归档仍不会进入活动缓存；带原 key 的重试
  会只读校验该归档并返回原结果，不重新激活终局或改写文件。
- Godot 会为每条待处理逻辑命令生成 key；网络错误或非 2xx 响应后保留，同 payload
  重试继续复用，收到 2xx 才清理。payload 改变或开始新局时使用新 key。

未携带 key 的 V4.2 客户端继续可用，但没有响应丢失后的 exactly-once 效果保证。
`POST /api/game/start`、玩家发言 preview、GET、显式 save/restore 不在本契约范围；
事件 `command_id` 也不是外部幂等 key。当前保证仍以单进程、单 worker 和未损坏的
私有存档为边界；Godot 待处理 key 只保存在本次客户端进程内。

## V4.3-A 原子存档与恢复

真实 FastAPI 服务生命周期中的狼人杀对局现在会把完整私有状态保存到
`backend/data/games/`；可用 `AGENT_TOWN_GAME_SAVE_DIR` 覆盖目录。开局及每个
成功的规则命令都生成严格的 `game_save.v1`：除完整 `WolfGameState` 外，还封印
最后事件序号/摘要、规则状态摘要、完整快照摘要，以及开局时冻结的
`recovery_config_fingerprint.v1`。指纹不含 API Key；进行中对局恢复时必须与当前
规则、NPC 人设、知识、调参及安全的 LLM 配置一致。

- 存档先写同目录、从创建起即为 `0600` 的临时文件，经 flush/fsync 后用
  `os.replace` 原子替换；目录权限为 `0700`。替换前失败会保留旧文件，并把本次
  内存规则命令精确回滚到命令前快照。
- 服务启动按一个批次校验全部存档。任何进行中存档损坏、事件链不一致、快照被改、
  game ID 不一致或配置漂移都会拒绝激活持久化，不会只恢复一部分后继续运行。
- 校验通过的未完成局自动回到活动缓存。终局归档启动时跳过，但仍可手动恢复，且
  配置升级不会阻塞终局归档扫描。
- `POST /api/game/{game_id}/save` 建立显式检查点，
  `POST /api/game/{game_id}/restore` 手动恢复，
  `GET /api/game/recovery-status` 返回最近一次启动扫描报告；对应响应为
  `game_save_response.v1`、`game_restore.v1` 和 `game_recovery.v1`。
- 完整存档含 seed、隐藏身份、夜间行动、合法私聊等敏感事实，不是公开事件接口，
  不应提交或发布。离线 simulation、隔离 replay 和直接导入规则模块不会自动落盘。
- 当前文件锁和活动缓存只支持单进程、单 worker。存在可恢复的未完成局时，配置热
  重载会以 409 拒绝，避免活动局指纹与实际配置分叉。
- V4.3-A 到 V4.3-B 之间生成、且唯一差异是缺少默认空 `command_results` 的早期
  存档可安全读取，但前提是原始快照摘要正确且事件中从未出现幂等 key。读取不会
  改盘，下一次正常保存才升级字段。V4 公开声明缺少后来加入的 `phase`、
  `window_day`、`event_sequence` 时，也只接受 `"" / null / 0` 这组精确默认值；
  默认来源字段不改变旧规则摘要。其他 schema、非默认值或摘要差异继续 fail closed。

V4.3-B 已在这份原子快照上增加客户端幂等 key 与持久结果台账。恢复指纹仍只服务
于存档兼容性；V4.6-B 的实验、Prompt/config 和价格表指纹是独立契约，不替代恢复
校验，也不改变进行中存档的兼容性判断。

## V4.2 单一追加事件日志与确定性重放

狼人杀规则写入口现在共享 `game_rule_event.v1` 追加事件链：开局、夜间行动与
结算、猎人开枪、警长流程、公开发言、私聊、投票、警徽移交和终局都按稳定序号
记录命令。每个事件包含命令 ID、`agent_town_rules.v4.2` 规则版本、
`public / player_private / system_private` 可见范围、前后阶段、前后规则状态
SHA-256 和上一事件摘要；修改任一已封印事件或绕过命令链修改状态都会使链校验失败。

- `GET /api/game/{game_id}/events` 仅在终局后导出
  `game_rule_event_log.v1`，避免进行中泄露 seed、夜间行动或私聊。
- `POST /api/game/{game_id}/replay` 从 `game_created` 的开局请求与内部 seed
  建立隔离的临时内存局，逐条调用同一 Python 规则入口，并逐事件比较状态摘要。
- `game_rule_replay.v1` 最后同时核对 winner、警长票、放逐票、出局、警徽流和
  完整规则状态摘要；重放临时局不会覆盖原局。
- 规则模板局（`enable_llm=false`、`enable_rag=false`）支持执行式确定性重放。
  启用 LLM 或 RAG 的局仍写入完整审计链，但本阶段明确返回“不支持确定性重放”，
  不会重新调用模型后声称逐字一致。
- 执行式重放还要求相同代码和 NPC 配置；V4.3-A 已增加窄范围的恢复配置指纹，
  V4.6-B 另为离线实验补齐完整配置与 active-only 指纹；两者用途不同。
- V4.2 当时把无 HTTP 仿真升级为 `agent_town_simulation.v15` /
  `agent_town_simulation_batch.v15`；V4.6-A 为 v16，V4.6-B 当前为 v17。每局总是验证重放；单局默认保留完整事件，
  批量默认只保留事件摘要与重放报告，可用 `--include-event-logs` 显式保留事件数组。
- `gameplay_digest_projection_version=agent_town_simulation.v14` 继续对同一玩法字段
  计算兼容摘要；新的事件/重放元数据只进入 `result_digest`。

`public_logs`、`sheriff_events`、行动和投票列表仍是现有 UI/规则投影，但其每次
成功变化都被同一命令事件及状态摘要封印。磁盘存档和进程重启恢复已由 V4.3-A
完成；V4.3-B 进一步把外部幂等 key、事件和原响应绑定为同一次提交。

## V4.1-B 玩家发言理解与提交前预览

白天和警上自由发言现在共用 Python 的只读预览链路：

- `player_speech_understanding.v1` 把身份声明、验人说法、怀疑/支持、投票意向和
  女巫建议转换为严格结构；其他措辞不会自动升级为身份、技能或行动事实。
- `POST /api/player-speech/preview` 返回 `player_speech_preview.v1`，明确区分
  “会写入的公开事实”“会应用的策略信号”“仅文本表达”和拒绝原因。
- 预览会规范化警长暂归票和警徽流，但不写入发言、声明、怀疑值、警徽流或阶段进度。
- 接受的预览带 64 位 SHA-256 指纹。Godot 确认提交时携带指纹，后端仍在锁内
  重新解析；文字或对局状态变化会以 409 拒绝旧预览。
- Godot 同时支持白天与警上发言的“确认提交 / 返回修改”；未通过的预览不能确认。
- 解析器按逗号拆分验人子句，避免“查验 3 号是狼人，我怀疑 4 号”把 4 号误登记为验人。

预览契约不返回其他角色真实 `role/camp`；只交换不可见 NPC 身份时，理解结果、
规则效果和预览指纹保持一致。

## V4.1-A 三档玩家策略与身份配对基准

V4 从 V3.0 封版标签 `v3.0.0`、提交
`7a44dd598a62739e450bebe56198a6fe1f505ebd` 开始。V4 开发只使用
`v4-development`，并且只推送到专用 `v4-origin`；任何 V4 代码都没有推送到
`origin`、`v2-origin` 或 `v3-origin`。V4 已以 `v4.0.0` 冻结，后续只保留历史读取。
完整计划见
[`docs/V4_ROADMAP.md`](docs/V4_ROADMAP.md)，V3 路线表
继续作为历史实施记录保留在
[`docs/V3_ROADMAP.md`](docs/V3_ROADMAP.md)。

V4.1-A 只扩展无 HTTP 离线仿真，不修改实时 FastAPI 对局 schema 或 Godot：

- `backend/app/player_strategy.py` 定义 `beginner / standard / expert` 三档；
  `standard` 继续使用 V3 的 `legal_public_baseline.v1`。
- 三档只消费 `player_strategy_context.v1`。公开角色投影不含其他席位真实
  `role/camp`；狼人队友、本人验人、本人女巫刀口和技能资源只进入对应合法私有区。
- V4.1-A 当时把单局/批量升级为 `agent_town_simulation.v14` /
  `agent_town_simulation_batch.v14`；V4.2 为 v15，V4.6-A 为 v16，V4.6-B 当前为
  v17。指标保持
  `agent_town_metrics.v5`，
  并增加 `player_decision_trace.v1` 与纯赛后的 `player_performance.v1`。
- `agent_town_player_benchmark.v1` 按相同 `seed + player_role` 配对三档策略；
  六种固定身份均覆盖，并要求三档拥有相同 `initial_layout_digest`。
- 正式矩阵覆盖到“同一 NPC 狼同时收到狼队友互踩查杀与真预言家查杀”的
  合法双验人状态；规则兜底保留狼队既有互踩主叙事，并以次目标和公开信号回应另一声明。
- smoke 使用 `2 × 6 × 3 = 36` 局；正式最小基准建议
  `56 × 6 × 3 = 1008` 局。首版报告配对胜负差，不把
  “expert 胜率必须高于 beginner”设成硬门槛。

运行一个轻量配对样本：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 2 \
  --benchmark-player-strategies \
  --output /tmp/agent-town-v4-player-benchmark.json
```

该命令固定关闭 LLM/RAG，不启动 FastAPI 或 Godot；配对模式也默认关闭
belief、stance 和 vote-calibration 大体积明细。单策略批量可使用
`--player-strategy beginner|standard|expert`。

`20260719–20260774` 的正式 1008 局基准已通过：三档各 336 局，玩家获胜数为
`beginner 88 / standard 106 / expert 107`；配对胜率差为
`standard-beginner +5.4%`、`expert-beginner +5.7%`、
`expert-standard +0.3%`。336 个 cohort 的布局摘要均一致，报告摘要为
`577e0860e3129cf66f3006f0bda025dbd88594813e64b23310b185938a9bdb13`。

## V2.0 封版信息

| 项目 | 内容 |
| --- | --- |
| 版本 | `V2.0` |
| 封版日期 | `2026-07-19` |
| 发布仓库 | [`KEswy/agent-town-demo-v2.0`](https://github.com/KEswy/agent-town-demo-v2.0) |
| 技术边界 | Godot 4 负责 2D 交互；Python 负责规则事实；RAG/LLM 负责 NPC 决策辅助与角色化表达 |
| 运行方式 | 后端和 Godot 均由开发者手动启动，本项目不会自动拉起服务 |
| V3 规划 | [`docs/V3_ROADMAP.md`](docs/V3_ROADMAP.md) |
| V4 规划 | [`docs/V4_ROADMAP.md`](docs/V4_ROADMAP.md) |

V2.0 基线提交为 `6af73f54844b4e1471c6d9fb582431a7ee892592`。它已覆盖十二人规则状态机、警长与警徽流、结构化普通白天发言、合法视角校验、NPC 智能参数、RAG、分层 UI、昼夜场景，以及坏坏和然然两名非参赛常驻居民。

## V3.2-B 精炼 NPC 发言 M13-A

本轮只调整公开表达，不改变 Python 已决定的身份、知识、行动、票型、警徽或胜负：

- 自然台词、公开立场摘要和警徽动作解释不再出现“警徽流 v1 / v2”。玩家看到的是“X 号的警徽流”或 NPC 自述“我的警徽流”；`BadgeFlowState.version`、signal ID 和复盘结构仍保留版本，供跨日审计使用。
- Python 规则发言把重复的立场卡、当前判断、追问、暂票和改票条件压成短句；RAG 只口头引用证据标题，不再逐字复述整张公开立场卡。警徽流与女巫建议也改为更短的规范句，但目标、分支和建议事实仍由 Python 固定。
- 公开 LLM 改写从最多 170 字收紧到 120 字，并由校验器硬性拒绝超长候选；结构化发言的角色化开场最多 10 字。规则正文较长时不再额外叠加口头禅或彩蛋。

固定 20 局规则样本共 555 条 NPC 发言，平均长度由 `158.2` 降至 `93.4` 字，P95 由 `225` 降至 `128` 字，最长由 `293` 降至 `196` 字。最长样本同时包含警徽流和女巫建议，因此不对事实句做破坏性截断。同口径 100 seeds 为好人 `37`、狼人 `63`，平均 `3.45` 天，与 V3.2-A 的 `38/62` 接近但不宣称表达改动完全不影响后续公开说服力。V3.2-B 封版 simulation schema 使用 v13。

## V3.2-A 智能警徽流 M16-A

本轮把警徽流从“手填两条传徽分支”改为由公开验人故事约束的狼人杀语义：

- 警上竞选或 PK 发言中首次跳预言家时必须同时发布警徽流；玩家缺失时服务端整次拒绝且不写入身份声明、发言或日志，NPC 真预言家和悍跳狼也走同一套要求。警下或普通白天发言中的预言家仍可选择首次发布或附公开理由修改，不要求每次重复。
- `primary_target_id` 表示下一夜实际要验的位置，`secondary_target_id` 只表示再下一顺验。若当夜目标为金水，警徽分支固定交给该目标；若为查杀，只能交给该声明者此前公开、当前仍存活的金水 `claimed_good_anchor_id`，没有合法金水时自动撕徽。多个金水默认取最近公布者，也允许在合法公开金水中选择。
- 例如首夜公开 2 号金水、第二夜警徽流验 3 号：第二夜后死亡时，给 3 号表达“3 号金水”，给 2 号表达“3 号查杀”。这仍只是该预言家的公开声明，不是 Python 验真；好人 NPC 可以根据是否按流验人、是否合理改流和移徽是否兑现来判断，也可能被自洽悍跳欺骗。
- Godot“警徽流”改为默认折叠摘要。警上输入预言家声明时自动展开并锁定必填；警下已公开的预言家可按需展开更新。面板只让玩家选择今晚验人、下一顺验和合法公开金水锚点，金水分支由 Python 固定计算，不再允许把下一顺验误当成查杀接徽人。

固定 `20260719–20260818` 的 100 局无 HTTP 复验仍为好人 `38`、狼人 `62`，平均 `3.44` 天；新警徽流没有把 V3.1-O 修复后的胜负重新打回失衡基线。

## V3.1-A 可复现模拟基础

V3 的第一个最小里程碑已完成 M01 的第一阶段，并为 M06 增加一条基础护栏：

- 每局规则状态持有内部显式随机种子；身份洗牌、夜间目标、发言顺序、平票和概率策略都从该种子确定性派生，不再消费进程全局伪随机状态。
- `backend/app/simulation.py` 直接调用既有 Python 规则入口，自动完成玩家的合法操作和完整阶段流，不经过 HTTP。
- `scripts/simulate_games.py` 支持起始 seed、连续局数、固定玩家身份、终局上限和 JSON 输出；模拟固定关闭 LLM/RAG，不启动 FastAPI 或 Godot。
- 输出包含规则/策略 schema 版本、逐局 seed、胜负、身份、警长票、放逐票、出局来源、阶段轨迹和稳定摘要哈希，可用于精确重放与后续指标采集。
- 公开开局 API 不提供可控 seed 字段，也不返回 seed，避免玩家据此重建隐藏身份；显式 seed 只供内部测试与离线开发工具使用。
- 自动化覆盖同 seed 逐字段重放、外部 `random` 状态隔离、合法终局、模拟内存清理、RAG 未初始化，以及好人基线决策对不可见 NPC 身份互换保持不变。

V3.1-A 的 100 局规则基线全部合法结束，但只得到好人 6 胜、狼人 94 胜。V3.1-B 继续把这项异常拆成可追溯指标；它仍不是目标胜率，M15 校准也尚未开始。

## V3.1-B NPC 核心指标

M02-A 已在可复现模拟上增加独立的赛后指标层：

- `backend/app/simulation_metrics.py` 只接受已经进入 `GAME_OVER` 的状态；真实身份只用于评价已经发生的选择，不会进入实时 API、NPC 上下文或玩家决策。
- 每局和批量报告当前使用 `agent_town_metrics.v5`；M02-A 当时为 metrics v1 / simulation v2，M03-A/B 为 simulation v3/v4，M04-A/B 为 v5/v6，M15-A/B 为 v7/v8，V3.1-L/M/N/O 为 v9/v10/v11/v12，V3.2-A 为 v13，V4.1-A 为 simulation v14 / metrics v5，并完整保留旧指标。
- 指标覆盖阵营胜率、平均局长、警长票熵、逐日放逐票熵、好人正确投狼率/误投好人率、假预言家好人警长票支持率与公开查杀跟票率。
- 报告按模拟玩家身份、投票者角色和游戏天数聚合；所有比率保留原始分子/分母，无适用样本使用 `null`，不伪装成 0%。
- 票熵按每张未加权选票计算，归一化口径为 `H / log2(选票数)`；它衡量选择是否集中，不把警长的 1.5 票重复视作多个玩家。
- “假预言家公开查杀跟票率”只表示好人票与此前公开查杀目标一致，是影响代理指标，不宣称单一因果。

同一组 `20260719–20260818` 共 100 个 seed 的首份 M02-A 基线为：

| 指标 | 结果 |
| --- | ---: |
| 好人胜率 | `6.00%` |
| 平均局长 | `3.42` 天 |
| 警长票归一化熵 | `28.25%` |
| 放逐票归一化熵 | `22.62%` |
| 好人正确投狼率 | `39.05%` |
| 好人误投好人率 | `60.95%` |
| 假预言家获得适用好人警长票 | `48.29%` |
| 假预言家当选率 | `72.00%` |
| 好人跟随假预言家公开查杀 | `41.57%` |

这些数值只建立诊断基线，不是自动平衡阈值。当前最明显的问题是票型集中、普通好人识狼率偏低、假预言家竞选优势过强；应在 M03 合法信念状态和 M04 连续性可解释后，再通过 M15 做多种子校准。

## V3.1-C 合法视角影子信念 M03-A

M03-A 新增 `belief_state.v1`，但暂不让它驱动发言、行动或投票：

- `backend/app/belief.py` 为 11 名 NPC 分别生成其他 11 个席位的怀疑分、置信度、立场和证据权重；分数范围为 `-100–100`，置信度范围为 `0–1`。
- 公开证据只来自公开声明、`public_position.v1`、警长事件和已经公布的放逐票；证据 ID、来源席位、目标、公开结果和中立摘要均可追溯。
- 私有证据第一阶段仅允许行动者自己的预言家查验、女巫当夜刀口和狼人队友知识，并用 `actor_private / wolf_team` 标记唯一合法观察者。
- 好人信念不读取角色表、`PublicClaimState.source`、悍跳内部指定、未公布夜间结算或旧的可变 `suspicion/relationship`；狼人和预言家仍能依法消费自己的队友/查验知识。
- 模拟结果升级为 `agent_town_simulation.v3`，保存去重证据台账、每次变化引用的证据 ID/权重和 NPC 出局前最后一份信念状态；批量报告提供证据与变化规模摘要。
- `gameplay_digest` 在采集 shadow 信念前生成。相同 seed 开启/关闭信念轨迹时该摘要完全一致，用于证明影子层没有改变规则结果。
- 完整 belief 轨迹约占 `46MB / 100局`。高容量平衡任务可加 `--no-belief-trace`，保留规则结果、M02 指标和独立的 M15-A/B 投票校准轨迹；再加 `--no-vote-calibration-trace` 只关闭诊断明细，不会关闭 M15-B 实时投票策略。

100 局影子基线共记录 11,650 条去重证据和 32,343 次有依据的席位变化，平均每局 116.5 条证据、323.43 次变化，终局平均置信度为 33.26%。其中公开证据 10,209 条、行动者私有证据 358 条、狼队证据 1,083 条。开启影子层后，100 局胜负、身份、阶段、票型、出局和全部 M02 指标与 V3.1-B 逐项一致。

M03-A 尚未从自由文本私聊猜测证据，也未实现证据衰减或把新分数接入 NPC 决策；这些边界留给后续小里程碑，避免不可审计文本和新策略同时进入。

## V3.1-D 信念衰减与结构化私聊 M03-B

M03-B 将影子 schema 升级为 `belief_state.v2`；在该阶段仍不驱动任何发言、行动或投票，M04-B 后只有普通非警长白天发言通过 stance 间接消费：

- 公开声明、公开查验说法、结构化公开立场和低信息发言属于软证据；每跨一天，当前权重乘以 `0.75`。公开投票、警徽动作等已观察到的硬事实不衰减。
- 本人预言家查验、本人女巫刀口、狼人队友知识和结构化私聊均不使用公开软证据衰减；角色本人面对他人冒认自己的唯一角色时，合法自知冲突也保留原权重。
- 有效私聊把规则实际应用的目标和 `suspect / trust` 方向保存为稳定 evidence ID。证据只授权给被私聊 NPC；自由文本问题和回复不参与信念构造。
- 指代不明、没有明确目标、彩蛋和当日重复追问不产生私聊信念证据；目标隐藏身份互换不会改变普通好人的私聊信念。
- `BeliefChangeV1.updated_contributions` 记录同一证据因跨日衰减而发生的权重更新；证据台账仍只追加，不修改旧证据含义。
- 模拟结果升级为 `agent_town_simulation.v4` / `agent_town_simulation_batch.v4`。shadow on/off 的 `gameplay_digest` 继续一致，M02 指标和规则结果不受影响。

## V3.1-E 统一立场摘要与连续性 shadow M04-A

M04-A 新增 `stance_summary.v1`，把合法信念与本人已经公开的结构化承诺归并成统一摘要，但仍不让摘要驱动实时决策：

- 每名 NPC 的摘要包含最多两个信任目标、主/次怀疑、暂定票、结构化验证目标/条件、置信度和 belief evidence ID。存活目标来自 `belief_state.v2`；暂定票和验证条件优先保留本人当天最新 `public_position.v1`。
- `backend/app/stance.py` 只读取合法视角 belief snapshot 和结构化公开立场，不解析发言自由文本，不读取好人无权知道的角色或阵营标签。
- shadow 对照在决定发生前保存摘要，再观察 NPC 的公开发言、警长票和放逐票；结果分为 `aligned / explained_change / unexplained_change / unscored`。新证据必须来自两次本人决定之间新增的合法 belief evidence ID。
- 一次决定自身生成的公开证据会进入“决定后基线”，不能在下一次改口时循环充当新理由。阶段变化但没有新信息时不会产生立场变化。
- 这些分类是诊断代理，不是平衡阈值，也不会禁止狼人欺骗、概率扰动或合法改票。M04-A 不修改 `choose_npc_*`、发言计划、投票或胜负规则。
- 模拟 schema 升级为 `agent_town_simulation.v5` / `agent_town_simulation_batch.v5`，输出 `stance_trace` 与批量 `stance_summary`；可用 `--no-stance-trace` 仅关闭连续性明细，`--no-belief-trace` 会同时关闭依赖 belief 的 stance 轨迹。

同一组 100 个 seed 共得到 6,133 次对照，其中 4,516 次有可比较目标：一致率 88.93%，未解释变化率 4.78%，另有 1,617 次明确记为 `unscored`。按类型看，放逐票/公开发言/警长票分别有 62/112/42 次未解释变化；警长票另有 661 次因统一摘要没有信任任何合法候选人而不评分。完整 belief + stance 报告约 101MB，这些数值只用于后续 M04-B 审查，不作为自动门槛。

## V3.1-F 普通白天发言受控消费 M04-B

M04-B 让普通非警长 `DAY_MEETING` 成为第一个读取 `stance_summary.v1` 的实时策略入口；警长发言、警长票、放逐票、夜间技能和胜负结算保持原路径：

- `public_speech_continuity.v1` 只投影当前 actor 的合法 belief 立场，并再次按本次 `legal_targets` 过滤。普通好人看不到其他角色的隐藏身份；狼人依法知道的队友也不能绕过公开发言目标白名单。
- 当前发言计划升级为 `public_speech_plan.v3`。除了 v2 的目标、立场、证据、问题、验证和暂定票外，必须给出 `continuity_reason`：`stance_aligned / new_public_evidence / deterministic_variance / authorized_claim / mandatory_rule_response / unscored`。
- 偏离主导 stance 只能引用本次已选中的新增公开 signal，或命中由内部 seed、`decision_variance` 和 `plan_consistency` 共同决定的可复现个体扰动。合法声明单列为 `authorized_claim`；收到必须回应的公开验人或既有狼队故事线单列为 `mandatory_rule_response`。
- 规则兜底会主动对齐 stance；LLM 仍可在合法目标、公开证据、声明包和战术白名单内选择策略。私有 belief evidence ID 只进入策略上下文，不会写入公开计划、台词或进行中 API。
- M04-B 当时把模拟升级为 v6；M15-A/B 为 v7/v8，V3.1-L/M/N/O 为 v9/v10/v11/v12，V3.2-A 当时升级到 `agent_town_simulation.v13` / `agent_town_simulation_batch.v13`，并继续保留 `speech_continuity_metrics.v1`。该统计不包含私有 belief 内容；M04-A 的警长票和放逐票 stance 对照继续保留。

同一组 `20260719–20260818` 共 100 个 seed 产生 2,163 次受控普通发言：1,831 次 `stance_aligned`、141 次 `authorized_claim`、139 次 `mandatory_rule_response`、52 次 `unscored`。规则模拟关闭 LLM，所以 `new_public_evidence / deterministic_variance` 均为 0；这两个分支由合成正反样本覆盖。公开发言未解释变化由 M04-A 基线的 112 次降为 3 次，全部决策的未解释率由 4.78% 降为 1.68%。但好人胜率同时由 6% 降至 2%，好人误投率由 60.95% 升至 64.46%；连续性改善不等于判断质量改善，M15 仍需独立做投票概率校准。

## V3.1-G 隐藏信息不变性矩阵 M06-A

M06-A 把此前分散的隐藏身份单点断言整理为可复用差分矩阵，不修改实时 API、NPC 策略或规则结果：

- `backend/app/invariance.py` 自动生成六类仅改变内部状态的变体：声明内部来源、悍跳内部标记、隐藏身份真值互换、身份与悍跳标记组合互换、未公开夜间结算，以及这些变化的组合样本。
- `hidden_info_projection.v1` 同时覆盖玩家可见角色卡、公开日志/情报、普通村民玩家私有卡、会议/警长视图、公开决策信号，以及每名普通村民 NPC 的 `belief → stance → decision_context → continuity → fallback_plan` 完整 M04-B 链路。
- `hidden_info_invariance.v1` 只输出 schema、观察者/变体 ID、检查计数、SHA-256 摘要和首个差异路径，不把真实角色、阵营、声明内部来源或私有 belief 内容写入报告。
- 固定 seed 夹具含 3 名无警徽 NPC 村民、6 个隐藏变体和每观察者 5 层策略投影，共 `96/96` 项一致；反向输入顺序必须得到同一报告。另用公开查验结果变化作为负对照，证明矩阵能捕获真实的公开输入变化。
- M06-A 会拒绝角色特权玩家、神职/狼人 NPC 和持有警徽的观察者。本阶段只验证无权村民视角；预言家、女巫、狼人等依法应变化的私有投影留给 M06-B 分开验收。

该模块是离线测试基础设施，实时 `app/main.py` 不导入它；Python 仍是隐藏身份、合法知识、行动与胜负的唯一事实源。

## V3.1-H 授权私有视角矩阵 M06-B

M06-B 在 M06-A 的“无权视角必须不变”之外，补上角色私有事实“只在合法观察者中变化”的正向矩阵，仍不修改实时玩法：

- `hidden_info_authorization.v1` 使用 `role_scoped_private_npc` 模式，逐一改变 NPC 预言家的私有验人目标、NPC 女巫依法看到的未公开刀口，以及一名未参与对比的狼队成员身份。
- 每个案例同时比较普通村民玩家公开投影和所有角色未变的存活、无警徽 NPC；只有声明过授权的 observer/layer 可以变化。狼队案例排除被直接交换真实身份的两名角色，防止把“本人身份已变”误当成私有知识传播。
- 固定 seed 共执行 `158/158` 项检查：预言家变化贯穿 belief、stance、decision context、continuity 和 fallback；V3.1-L 后女巫刀口只进入 belief、stance 和 continuity，首夜 99% 救人不再由旧好感阈值改变 fallback；其余 3 名狼人对狼队成员变化更新 belief、stance、decision context 和 continuity。
- 所有其他 NPC 的五层决策投影和三类案例的公开投影必须逐项不变。把预言家授权故意错配给村民的负对照，必须同时报告“真正预言家的变化未获授权”和“村民被要求变化却没有变化”。
- 报告只保存授权类别、观察者/投影计数、摘要和首个差异路径，不保存变体对局状态或私有 evidence 正文；该报告仅供离线测试，不进入进行中 API、LLM 上下文或 Godot。

至此 M06-A/B 分别锁住不应变化和依法应变化的两侧边界。后续新增私有状态或策略入口时，必须先把对应 projection 和授权规则加入矩阵。

## V3.1-I / V4.6-B 脱敏 LLM 可观测性 M09-A/B

M09-A 建立的本地、只追加诊断层由 V4.6-B 升级为严格的
`llm_observation.v2` 与 `llm_observability_summary.v2`，仍不改变 NPC 策略、
规则回退或任何游戏状态：

- 每次 adapter request 记录 task、操作类型、provider/configured model、成功或回退、
  provider attempt、adapter retry、延迟、token usage 状态和分类后的回退原因。
  结构化候选校验另记 validation event；它的 semantic attempt/retry 独立统计，不能
  当成额外云端重试或重复计费。
- `LLMClient` 对本次最终 system prompt 与安全 LLM 配置计算 64 位 SHA-256。日志只
  保存 `prompt_fingerprint / config_fingerprint`；API Key、prompt、上下文、玩家问题、
  模型回复、fallback 文本、game/character ID 和原始拒绝内容都不进入 allowlist。
- v2 明确保存 `complete / partial / missing / not_applicable` usage 状态、已报告和未
  报告 usage 的 attempt 数，以及 provider 返回的 billing model 来源；汇总仍兼容
  读取历史 v1，不改写旧 JSONL。
- `backend/config/llm_pricing.json` 使用严格的 `llm_price_catalog.v1`；汇总嵌入
  `llm_cost_summary.v1` 和价格表指纹。只有 model、有效时间窗、完整 usage 和价格
  均已知的请求才进入完整总成本；任一可计费请求未知时
  `total_cost_usd_micros=null`，`known_cost_usd_micros` 仍保留可证明部分。
- 默认 `deepseek-v4-flash` 条目状态是 `unknown`。这不是官方价格，也不表示免费；
  需要成本值时应先维护有来源、有效时间窗和独立版本号的本地价格表，并在汇总命令
  用 `--price-catalog` 显式选择。

已有 `llm_validation_failures.jsonl` 继续承担受限的原始语义审计，敏感等级高于脱敏
统计文件，不能作为日常指标源。观测或成本汇总失败时跳过/返回未知，绝不能影响
Python 规则结果、LLM 返回或既有确定性 fallback。

## V3.1-J 投票概率 shadow M15-A

M15-A 没有替换当前警长票或放逐票，只在离线模拟中于 NPC 投票前构造另一份可解释分布，并在规则完成投票后附上实际目标用于比较：

- `backend/app/vote_calibration.py` 定义 `vote_probability_shadow.v1`，把每个合法候选人的 utility 分成 `belief / public_influence / social / coordination / variance` 五项。belief 只来自该 NPC 的 `belief_state.v2`；普通好人的 coordination 永远为 0，狼人只消费依法知道的队友和狼队策略。
- 每份观察保存温度、候选概率、熵、top 目标、实际目标的 shadow 概率/排名，以及警长公开归票造成的硬约束。候选概率严格守恒为 1，各分量严格守恒为 total utility。
- `vote_probability_summary.v1` 按 `sheriff_vote / exile_vote`、投票者阵营及两者交叉汇总个体分布熵、top 概率、实际票命中 shadow top 的比率、实际目标概率/排名和各分量平均绝对值。
- 逐局轨迹只进入离线 simulation v7 报告，不进入实时 API、LLM、Godot 或规则状态。`gameplay_digest` 在加入 shadow 结果前生成；开启/关闭轨迹必须完全相同。
- 普通好人对 M06-A 的声明来源、悍跳标记、隐藏身份、未公布夜间结果和组合变体保持逐字段相同；狼人面对队友身份变化则依法改变自己的分布。

seed `20260719–20260818` 的 100 局首份 shadow 基线包含 3,264 次 NPC 观察和 23,209 个候选评估。好人警长票平均归一化个体熵为 87.45%、top 概率为 55.76%；好人放逐票个体熵只有 8.56%、top 概率达到 93.95%，且实际票与 shadow top 一致率为 94.03%。好人放逐概率质量平均只有 34.76% 落在狼人目标、65.24% 落在好人目标，与实际 35.54% 正确投狼率接近。

这些数值说明当前主要问题集中在普通好人放逐分布，而不是好人警长票；它们仍是诊断基线，不是自动平衡阈值。M15-B 应只选择普通好人放逐票作为首个受控消费者，先校准 belief 强度与温度，保留警长票、狼人协同、强私有证据和规则硬约束。

## V3.1-K 普通好人放逐概率校准 M15-B

M15-B 把唯一实时改动限制在 `VOTE` 阶段的非玩家、非警长、好人阵营 NPC 放逐票。玩家票、警长本人归票、警长竞选、狼人票、夜间技能、选票结算和胜负继续走原 Python 路径：

- `vote_probability_trace.v2` 使用 `consumer_mode=controlled/shadow` 和独立 `policy_version` 标明是否真正驱动选票。只有普通好人放逐观察使用 `good_exile_calibration.v1`；其他观察继续使用 `shadow_vote_baseline.v1`。
- 受控五分量分解既有合法评分器的个人怀疑、公开影响、关系和确定性个体读法，并加入很小的 `belief_state.v2` 置信度修正；softmax 温度在原 NPC 参数结果上增加 `5.0`，不改变候选白名单或规则硬约束。
- 真实选票与轨迹读取同一份概率。若严格概率契约拒绝输入，Python 会确定性回退到原合法评分器，避免校准层阻断投票。
- 预言家依法验出的好人仍从其候选中排除；私有查杀仍保持强影响。好人面对相同公开输入时，对 M06-A 的隐藏身份、悍跳标记、内部来源和未公布夜间结果互换保持逐字段不变。
- simulation 升级为 v8；`vote_probability_summary.v2` 新增 controlled/shadow 数量及分组。关闭轨迹只移除离线诊断，不会关闭实时 M15-B 策略，也不会改变 gameplay digest。

同一组 `20260719–20260818` 的 100 局验收中，受控普通好人放逐观察为 1,482 次，平均归一化个体熵为 `9.82%`，可比 M15-A 非警长基线为 `9.01%`；top 概率为 `93.45%`。总体好人误投率由 M15-A 基线 `64.46%` 降至 `63.69%`，好人胜场保持 `2/100`，好人放逐概率质量落在狼人目标的比例由 `34.76%` 升至 `36.14%`。这些仍是固定 seed 回归结果，不是目标胜率或自动调参阈值。

## V3.1-L 女巫策略与失衡诊断 M02-B

V3.1-L 没有继续盲调投票温度，而是先把女巫策略和终局根因变成可审计数据：

- NPC 女巫第一夜被刀时必定自救；其他合法刀口以由 game seed 派生的确定性 `99%` 概率使用解药，第一夜不使用毒药。玩家女巫仍由玩家通过原夜间接口决定行动。
- 从第二夜开始，只要 NPC 女巫存活且有毒，默认毒掉她自己合法视角中最怀疑的存活目标；目标排序不读取真实身份。
- 玩家发言只在明确出现“女巫毒掉某一人”或“女巫压毒”时生成 `witch_directive.v1`。多目标、含糊说法和“我昨晚毒了谁”不会被猜成未来行动。
- 普通 NPC 可根据自己的公开计划追加同一结构化建议。女巫用自己的怀疑、公开压力、对建议者的信任、公开说服力和 NPC tuning 独立评分；因此可以采信、拒绝，也可以被狼人或判断错误的好人骗到。
- 只有理由属于“当前公开信息不足”的压毒建议可能被采信。`witch_strategy_decision.v1` 记录行动、采信来源和原因，但不进入进行中公开 API。
- `agent_town_metrics.v2` 新增终局原因、首个放逐阵营/身份、按出局原因与阵营计数，以及女巫首夜救人、第二夜毒/压毒、建议采信和毒药命中指标；simulation 同步升级为 v9。

同一组 100 seeds 中有 95 局为 NPC 女巫：首夜存在救人机会的 `95/95` 局均使用解药（策略配置仍是 99%，该固定样本恰好没有命中 1% 跳过）；9 次女巫本人被刀全部自救。第二夜有毒且存活的 90 局中，67 局用毒、23 局因合理建议压毒；整批共 72 次用毒，命中狼人 42 次、好人 30 次，狼人命中率 `58.33%`。

平衡仍未修复：好人仅胜 `3/100`；首轮放逐好人仍为 `75/100`，其中首放预言家 `34` 局；终局原因为狼人控场 73、神职出尽 17、村民出尽 7、全狼出局 3。好人误投率为 `68.34%`。这些数据证明女巫策略已按合法视角工作，也进一步把主因指向白天 belief/假预言家可信度与放逐链，而不是继续依靠女巫单点补偿。

## V3.1-M 真假预言家策略与链路诊断 M02-C

V3.1-M 只修改两个狼人策略入口，并为结果补赛后指标；警长计票、狼队合法协同、好人知识边界、玩家操作和胜负规则不变：

- `fake_seer_campaign.v1` 不再让最强 NPC 狼每局强制悍跳。Python 先沿用 deception、team coordination、leadership 等既有 tuning 选出唯一候选，再以 `40%–88%` 的确定性策略概率决定是否参选；同一配置和 seed 必须重放一致。
- `fake_seer_check_mix.v1` 保留原有的高压队友查杀机会，并在队友金水、非狼查杀、非狼金水之间确定性混合。狼人只使用依法知道的队友集合、自己的怀疑/关系和公开压力，不读取非狼玩家的预言家、女巫等精确身份。
- `agent_town_metrics.v3` 新增 `seer_claim_balance`：真假预言家参选/当选/起跳/出局、假验人四类目标-结果组合，以及悍跳、悍跳当选、假查真预言家、真预言家首放四种条件下的胜负计数。CLI 新增 `[SEER]` 摘要；simulation 升级为 v10。
- 自动化覆盖参选与不参选都能出现、全局随机状态隔离、好人精确身份互换不变、三种非献祭假验人均可出现，以及单局/批量指标守恒。

同一组 `20260719–20260818` 共 100 个 seed 中，悍跳参选由 `100` 局降至 `76` 局，悍跳当选由 `72` 降至 `55`，假查杀真预言家由 `31` 降至 `12`，真预言家首放由 `34` 降至 `27`；首放好人由 `75` 降至 `71`，好人误投率由 `68.34%` 降至 `67.19%`，好人胜场由 `3/100` 升至 `5/100`。但没有悍跳的 24 局也仅好人 3 胜，首日成功放逐狼人的 29 局仅好人 2 胜。因此真假预言家首轮链条确实改善，但 5% 仍严重失衡，当前终局瓶颈已经转向“首日之后的证据累积、跨日站边和连续放逐”，不能继续只调悍跳概率。

## V3.1-N 跨日放逐链 shadow 诊断 M02-D

V3.1-N 不修改任何实时决策，只增加 post-game-only `cross_day_exile_chain.v1`：

- 单局保存放逐阵营序列、首放是否为狼人及其下一次放逐阵营；真实阵营只在 `GAME_OVER` 后用于评价，进行中的 NPC 和玩家不会知道被放逐者的隐藏身份。
- 对同一名存活好人 NPC 的相邻两轮选票，统计 `投狼→投狼 / 投狼→投好 / 投好→投狼 / 投好→投好` 四种转移，并给出“正确保持率”和“误投纠正率”。玩家票不混入该 NPC 指标。
- 另对“首放狼人”样本单独比较该轮与下一轮选票，避免总体均值掩盖已经出现正确信号后又快速失去判断的情况。
- `agent_town_metrics.v4` 和 simulation v11 对单局/批量转移数、条件胜负、下一次放逐阵营及空样本 `null` 做严格守恒；CLI 新增 `[EXILE-CHAIN]`。

固定 100-seed 的身份、胜负、票型、出局和阶段轨迹与 V3.1-M 逐项一致，好人仍为 `5/100`。共记录 861 次好人 NPC 相邻轮选票转移：此前投狼 267 次，下一轮仍投狼仅 66 次，正确保持率 `24.72%`；此前误投 594 次，下一轮纠正为投狼 199 次，误投纠正率 `33.50%`。29 局首放狼人后，下一次放逐 `27` 个好人、仅 `2` 个狼人；165 名仍可连续投票且此前投狼的好人 NPC 中只有 30 名下一轮继续投狼，保持率 `18.18%`。这把下一候选消费者明确限定为跨日好人 NPC 放逐判断，但本阶段没有授权任何策略改动。

## V3.1-O 公开票型连续追查与平衡修复

V3.1-O 针对 V3.1-N 暴露的跨日断裂修改三个 Python 策略入口，规则真值和 LLM 权限不变：

- `good_exile_cross_day.v1` 只控制 `VOTE` 阶段普通非警长好人 NPC。上一轮放逐票不超过 `75%` 时，所有人都可从公开票单看到存活反对票阵营；策略优先追查其中投向最集中目标的公开小团体，并用席位号稳定打破平手。它不知道被放逐者或被追查者的阵营。
- NPC 女巫从第二夜起把同一公开票型焦点纳入自己的“最怀疑目标”排序；玩家/NPC 的合理压毒或毒人建议仍可按 V3.1-L 的独立阈值覆盖，毒药和目标合法性仍由 Python 决定。
- `fake_seer_campaign.v2` 把指定悍跳狼的参选区间从 `40%–88%` 校准到 `28%–62%`。用于配对回归的确定性随机流保持冻结，因此同一批 seed 比较的是策略阈值变化，不是重新洗牌后的样本。
- 自动化构造 `75%` 争议票、超过 `75%` 的压倒性票和隐藏阵营互换，要求公开焦点、普通好人概率和女巫目标在合法条件下生效，并对隐藏身份逐字段不变。

固定 `20260719–20260818` 的 100 局从 V3.1-N 的好人 `5/100` 提升到 `38/100`。好人误投率为 `51.80%`；首放狼人仍为 31 局，但下一次放逐继续命中狼人达到 `28/31`（`90.32%`），对应好人 NPC 正确票保持率 `91.57%`。NPC 女巫毒药命中狼人 `71.01%`，悍跳参选/当选为 `51/39`。这是一组固定回归样本，不宣称总体期望胜率；它证明此前 5% 的主因是公开票型没有形成跨日共同目标、女巫没有消费同一合法信号，以及悍跳参选过密，而不是 Python 胜负判定错误。

## 当前版本

### 小镇交互

- 世界没有 UI 焦点时可用 WASD 或方向键移动玩家；Tab 进入界面后，方向键改为导航或滚动。
- `Camera2D` 跟随玩家。
- 走近 NPC 后按 `E` 交互。
- 对话框打开时暂停移动，`Esc` 可以关闭。
- 警上发言、白天发言和投票理由支持按 `Enter` 提交；提交后会清空输入框并强制释放文本焦点。
- 移动保护只等待“提交瞬间仍处于按下状态”的 WASD/方向键松开；提交后新按下的移动键会立即生效，不会再把正常移动误判为输入残留。
- 控制面板按钮、下拉菜单、开关、分页和滚动区均可获得可见键盘焦点；WASD 或点击世界会在非文本状态主动退出面板焦点，编辑文字和模态窗口时不会误移动角色。
- NPC 对话框内置 Noto Sans SC 中文字体，避免个别字符显示为带叉方框，并保证换机器后的字形一致。
- 对话文本进入 UI 前会清理 Unicode 替换字符 `U+FFFD`。
- 字体文件来自 Google Fonts，使用 `game/assets/fonts/OFL.txt` 中的 SIL Open Font License。
- 坏坏和然然是独立于狼人杀的常驻居民；无论黑夜、警上、白天、自由活动、投票或游戏结束，都可以走近她们使用普通 `/chat`。
- 两名居民在全局 DeepSeek 配置可用时会结合当前昼夜/游戏阶段使用角色化生成；禁用、未配置、超时、格式异常或轻量安全校验失败时自动使用各自的自然规则回复，聊天不会卡住。
- 普通聊天按 `player_id + NPC 名称` 隔离并持久化；完整历史保存到 `memory.json`，最近 8 轮同一居民对话进入 LLM 上下文。
- Guide、Archivist 和 11 名参赛 NPC 的普通 `/chat` 继续使用原有确定性回复；狼人杀对局内发言与私聊仍遵守各自的规则接口。
- 狼人杀普通白天 NPC 发言和私聊可以按局启用云端 LLM；输出校验开启时，普通白天发言先由 LLM 在规则白名单和 `public_speech_continuity.v1` 内生成 `public_speech_plan.v3` 决策，再由独立表达调用写成角色台词。输出校验关闭时改用 Python 合法计划和一次原文表达。未配置、超时、响应解析失败，或开启校验后输出不安全时自动使用规则计划与模板。

### 窗口与控制菜单

- 默认窗口尺寸为 `1280×720`，可以自由缩放，最小尺寸为 `1100×650`；`1600×900` 作为宽屏验收尺寸。
- 狼人杀界面改为黄色与浅蓝色的分层布局，不再把开局设置、身份、操作、角色卡和日志塞进同一个滚动面板。
- 所有浅色面板、按钮、输入框、下拉框和分页标题统一使用黑色文字；交互控件同时使用浅色底，避免默认浅色文字或深色控件底造成低对比度。
- 顶部常驻阶段 HUD 显示当前阶段摘要，并集中提供刷新、赛后复盘、情报抽屉和新局设置入口。
- 顶部 HUD 收敛为“情报 / 菜单 / 新对局”三个按钮；规则百科、我的战绩、存盘、本局复盘、新手引导与刷新状态统一收进“菜单”浮层，减少顶栏拥挤。
- 菜单新增“角色档案”：展示 11 名参赛 NPC 与 2 名常驻居民的人设、性格与口头禅。
- 开局设置窗口移除了与“关闭”重复的“先逛逛”按钮，直接关闭窗口即可探索小镇。
- 开局设置使用独立模态窗口，可填写玩家名、选择测试身份，并分别决定本局是否启用 LLM 与 LLM 输出校验；也可以先关闭窗口探索小镇。
- 开局设置提供“继续上局”：自动恢复上次未完成的十二人局（优先内存中的活跃对局，未找到时回退到后端启动时从磁盘恢复的对局列表）；会话记录上次游戏 ID、玩家名与音效开关，保存在 `user://agent_town_session.cfg`。
- 开局设置可一键关闭“启用音效与音乐”，偏好随会话保存；下次启动沿用上次设置。
- 顶部 HUD 新增“规则”与“战绩”入口：规则百科直接搜索后端 111 条规则/NPC 知识并展示命中条目；战绩页本地记录各身份胜率、最近一局 MVP 与常用操作累计，保存在 `user://agent_town_stats.json`。
- 顶部 HUD 新增“存盘”：随时把当前对局保存到本地存档（后端原子存档）；“继续上局”仍可恢复最近未完成对局。
- “我的战绩”页新增成就系统（首胜、连胜 3 局、各身份首胜、成为 MVP、累计验狼/放逐狼等），“导出战绩”可把战绩与成就导出为文本文件。
- 音效设置细分为“音乐 / 音效”两档音量滑块（各 0–100），与总开关一起随会话保存。
- 规则百科与战绩面板支持 `Esc` 关闭，并接入整局键盘焦点导航（Tab/方向键）。
- 左上角身份卡只在对局中出现；狼人会在身份下方直接看到三名狼队友的号码和名字。身份卡下方新增“关键公开信息”折叠区，汇总已经在桌面公开的神职起跳、验人说法、女巫用药说法、守卫成功说法和猎人公开开枪；第一条信息出现时自动展开，之后可手动收起。
- 折叠区用 `◇` 标记未经确认的公开说法、用 `●` 标记规则已经向全场确认的公开动作。诸如“某人称验了谁”“某人声称救了谁”只表示这句话公开说过，不表示内容真实。
- 右侧“当前行动”面板只保留本阶段需要查看和提交的操作；compact / default / wide 三档宽度为 `420 / 440 / 480px`，展开高度按各档比例计算并限制在 `320–520px`。
- 点击“当前行动”标题栏右侧箭头可以展开或收起；内容过长时支持鼠标滚轮和触控板上下滚动，标题栏保持固定。
- “情报”使用独立右侧抽屉，三档宽度为 `520 / 600 / 736px`，分为“场上角色”“公开记录”“我的记录”三页；12 张角色卡随窗口切换为 `2 / 3 / 4` 列。
- “我的记录”按本局时间累计显示夜间技能及结果、警上操作、完整公开发言、私聊问题和投票目标/理由，新开一局自动清空。
- 身份技能、猎人开枪、警长、会议和投票控件按当前身份与阶段动态出现，不再常驻显示无关操作栏。
- 阶段 HUD、行动面板、情报抽屉、开局设置和复盘统一使用项目内置 Noto Sans SC，避免“杀”等中文字符依赖系统字体。
- 玩家、11 名参赛 NPC 和 2 名常驻居民使用独立的原创像素角色，对话框同步显示头像；警长只会出现在参赛角色身上。
- 警上候选人头顶显示彩色警察徽章，退水后徽章变灰，进入平票竞选时显示 `PK`；面板同步展示上警名单、发言顺序、当前发言人、退水和 PK 名单。
- 11 名 NPC 围绕会议广场紧凑分布，完成一轮正式发言和自由活动时不需要长距离往返。
- 当前行动和情报抽屉互斥打开；展开任一右侧面板时摄像机会为其留出安全区域，关闭后恢复居中。
- 走近 NPC 打开对话框时，当前行动和情报抽屉都会自动关闭。

### 场景与昼夜

- 小镇背景使用独立 `TownBackground` 场景，替换原来的三块纯色多边形，并继续采用适合 Demo 的 Godot 原生矢量绘制。
- 地图包含横纵石板路、圆形会议广场、池塘与水波、房屋、市场摊位、树木、花坛、围栏、长椅、路牌和四盏广场灯；中央发言区域仍保持开阔。
- 尚未开局时默认白天；Python 规则状态进入 `NIGHT` 后，Godot 将世界平滑切换为蓝色夜景，并显示暖黄色灯晕、萤火与水面月光。
- 只有 `NIGHT` 使用夜景；警上、白天会议、自由活动、投票和游戏结束等其他阶段都恢复白天。昼夜只是规则阶段的视觉反馈，不改变身份、知识、行动、投票、出局或胜负事实。
- 世界使用单独的画布调制，HUD、行动面板、情报抽屉和开局窗口不会随夜色变暗；NPC 名字增加浅色描边，白天与夜晚都保持可读。
- 程序化生成的昼夜两套 BGM 随规则阶段切换（夜晚变奏、白天回归），并配有确认、投票、出局、警徽与昼夜过渡音效；全部为本地生成资源，无外部素材与版权依赖。
- 夜晚结算与投票放逐后会给出局角色播放红色闪烁、缩放脉冲与浮动“出局”标签，并叠加出局音效；玩家自身出局同样生效。
- 夜晚结算时屏幕会叠加一次短暂的暗色脉冲过渡，提示“夜晚结果公布”。

### 狼人杀规则

- 固定 12 人局：玩家 1 人、NPC 11 人。
- 身份池：狼人 x4、预言家 x1、女巫 x1、猎人 x1、守卫 x1、村民 x4。
- NPC 固定为：梅西、C罗、周深、梅长苏、塞尔达、小骑士、大黄蜂、喜羊羊、懒羊羊、洛洛、奇异博士。
- NPC 名称和性格固定；正常开局身份随机，开始菜单也可指定玩家身份用于技能测试。
- 玩家通常只能看到自己的身份；玩家是狼人时还能看到三名狼队友。
- NPC 狼人内部互相知晓，默认避开队友，也会按局势选择伪装深水、误导好人、框好人、反推、救队友、拉开距离或在高压下策略性卖队友。
- 好人只根据自己有权知道的信息、公开声明、动作、关系和证据判断；强悍跳狼可能骗到容易受影响的好人，接近的候选人之间也可能出现可复现的误判和错票，而不是让规则引擎暗中把正确答案喂给好人。
- 警下 NPC 会按候选人实际说出的警上内容、关系、公开验人故事和自身判断参数分别评分；固定人设只保留很小的表达先验，同质量的玩家与 NPC 发言使用同一套标准。每名听者对相近候选人可以有不同但可复现的判断，因此好人票不会机械地全部落给真预言家。
- 收到金水只会软性提高对声明者的认可，不会证明对方是真预言家或锁定警长票；收到查杀会形成直接冲突。两种说法都会成为该 NPC 当天必须正面回应的公开信息。
- 狼队战术必须保持公开叙事一致：若悍跳狼给狼队友发查杀，被查杀的狼人必须公开反对并投向该悍跳狼，不能再投它当警长或替它站台；若悍跳狼成为警长，之后也不会把警徽传给被自己查杀的队友。
- 玩家是狼人时，玩家提交的夜袭目标是当晚狼队最终目标；玩家不是狼人时，由 NPC 狼人按多数意见决定。
- 预言家查验后会保存目标阵营；守卫不能连续两晚守同一人。
- 女巫有一瓶解药和一瓶毒药，每晚最多使用一瓶；只有第一夜可以自救。守卫与解药同时保护同一刀口时，目标仍会出局。
- 猎人被狼袭或投票放逐出局时可以开枪，被女巫毒药淘汰时不能开枪；NPC 猎人会按怀疑值自动决定目标。
- 投票后放逐最高票角色。好人消灭全部狼人获胜；狼人消灭全部村民、全部神职，或存活狼人数不少于存活好人数形成控场时获胜。
- 猎人因狼袭或放逐出局且能够开枪时，优先完成开枪结算，再检查狼人是否已经控场。
- 第一天有完整警上竞选：报名、按序发言、退水、同时投警长和一次平票 PK；只剩一名候选人时自动当选，全部退水或第二次平票时警徽作废。
- 第一夜先在后端计算刀口、解药、毒药和守卫结果，但警上竞选结束前不公布也不执行出局；竞选结束后统一公布。后续夜晚仍在白天会议前正常公布。
- 所有参加过警上竞选的角色都不能投警长票，退水不会恢复投票资格。
- 每次出局都记录合法来源、行动者、目标和轮次；没有狼刀、毒药、猎人开枪或放逐等合法来源时，任何角色都不能无故出局。
- 警长拥有 1.5 票。前夜有人出局时警长按自然座次发言；无人出局时选择警左或警右并自然最后发言。
- 警长在自己的发言中可以提出暂时归票；全员发言结束后可以维持或调整最终归票，只有最终归票会锁定警长自己的正式投票。
- 警长出局时可移交或撕毁警徽；若警长同时触发猎人开枪，先完成开枪再处理警徽。
- 所有玩家可见文案统一使用“出局”，不再用“死亡”描述角色状态。

这些 NPC 是 Demo 中的同名虚构游戏角色，不用于还原现实人物。

### NPC 性格

- 梅西：沉稳观察证据，结论稳定；狼身份偏低调掩护，高压时谨慎切割。
- C罗：自信直接，擅长推动投票；狼身份会争夺主导，也能果断卖掉高危队友。
- 周深：敏锐温和，重视语气与关系；狼身份偏柔和掩护，较少主动切割。
- 梅长苏：谨慎且逻辑性强，综合顺序、票型和跨轮记忆；狼身份擅长多轮布局。
- 塞尔达：勇敢稳健，相信可验证行动；狼身份依赖一致站位，不喜欢复杂谎言。
- 小骑士：寡言坚定，更看重行动与投票；狼身份用沉默和转移目标保护队友。
- 大黄蜂：警觉直接，喜欢连续追问；狼身份会强力施压，也会快速切割暴露队友。
- 喜羊羊：乐观聪明，擅长组织信息和设计验证方案；狼身份善于制造合理共识。
- 懒羊羊：随和而有直觉，留意态度突变；狼身份倾向低调跟票和隐藏信息量。
- 洛洛：系统化分析技能、顺序和票型；狼身份会构造前提错误但形式完整的逻辑链。
- 奇异博士：保留多种假设并推演全局；狼身份擅长预留解释路径和长期取舍。

### 常驻居民

- 坏坏：嫩绿色、黄肚皮、浅蓝背鳍和围巾的原创像素小恐龙；小尖牙只咬饼干，温柔诚恳，先把尾巴盘好倾听感受，再陪玩家找到一件能马上尝试的小事。
- 然然：黑白分明、穿黄色披肩并背浅蓝邮差包的原创像素熊猫；活泼好奇，会把玩家的故事当作一封信收好，再追问关键细节并整理成小计划。
- 两人使用 `wolf_character_id = 0`，不会进入十二人角色列表，不会获得身份、出局、警徽、发言轮次、行动权或投票权，也不会读取隐藏对局事实。
- 她们的长期记忆彼此隔离，普通聊天不会写入狼人杀公开日志或改变 Python 规则引擎状态。
- 长期记忆已深化：除最近 8 轮对话外，居民会维护一份跨对话的紧凑摘要与关键词偏好计数（`memory_meta.json`），LLM 上下文与规则回退都会引用；询问“还记得/上次/之前”时能带出旧话题与常聊主题。
- 常驻居民会按对话节奏偶尔提起“上次寄来的信”与常聊主题，形成跨局故事线。

### 公开身份声明与对跳

- 玩家公开发言支持识别“我是预言家”等身份声明，以及“查验 3 号是狼人”等验人声明。
- NPC 真预言家第一天必须上警，并在竞选发言中公布真实验人；玩家预言家可以不上警，也可以自行决定是否说出或如何描述验人。
- 每局会从 NPC 狼人中指定一名悍跳候选；它可以起跳预言家、编造金水或查杀，也会根据玩家狼人的起跳选择让跳或在独立退水阶段退水。
- 狼队在高压条件下可以全局至多一次“狼查杀狼”；少数局面允许双狼起跳，之后仍需维护各自的假验人记录。
- 女巫、守卫和猎人会根据已发动技能、成功挡刀、公开压力和性格决定是否公开身份或行动信息。
- 身份声明和技能声明会改变其他角色的怀疑与信任，并参与后续发言和投票判断。
- 当天被公开发金水或查杀的 NPC，首轮白天发言必须把声明者纳入主/次目标并回应；它可以接受、保留或质疑金水，也会说明自己若曾把警长票投给其他候选人的事实。公开金水仍只是说法，不是规则确认的身份答案。
- 控制面板角色卡和左上角关键公开信息只显示中立的公开投影，例如“公开跳预言家”“称验 3 号：查杀”，不会标记声明真假。后端不会向这一区域返回声明的内部来源、真实身份、阵营、真实狼刀、守护或女巫用药结算。

### 角色化表达

- 11 名 NPC 都配置了独立的说话风格、口头禅和轻量彩蛋。
- 规则发言会按角色插入确定性选定的个性化开场白（如 C罗“听我说”、梅长苏“从逻辑上看”、懒羊羊“嘛”、洛洛“按顺序看”），同一句不会连续复用；30 局基线模板重复率降到 `10.8%`、人设区分度升到 `81.6%`，玩法指标不变。
- 发言文案去掉了生硬的结构化标签：警徽流说明不再输出“理由：xxx”，而是按原因类别给出自然句（如“原目标已经出局，警徽流顺延到这个位置”）；玩家行动记录里的投票展示也从“；理由：”改为更口语的冒号衔接。
- 自由活动私聊支持输入触发彩蛋：`GOAT`、`Siu`、`少管我`、`林殊`、`林克`、`圣巢`、`Shaw`、`灰太狼`、`青草蛋糕`、`霹雳火`、`多玛姆` 分别对应 11 名 NPC。
- 对梅长苏说出“林殊”会触发一次私密真实身份透露；该信息只写入玩家行动记录，不进入公开日志、不展示在公开角色卡，也不消耗当天的有效追问机会。
- 口头禅按场景低频触发，同一句不会在连续正式发言或私聊中反复出现。
- 以下两段流程、严格 schema 和内容拒绝描述均适用于“输出校验开启”；关闭校验时由 Python 先选合法计划，再生成 1 份最终原文并直接显示。
- 输出校验开启时，普通非警长 `DAY_MEETING` 使用“决策层 → 表达层”两段流程：第一段只生成无台词的 `public_speech_plan.v3`，并消费 `public_speech_continuity.v1`；第二段只生成不含游戏事实的短语气前缀，Python 再把已校验计划渲染成完整正文。警上、警长发言、私聊及其他现有路径仍只做角色化改写。
- `public_speech_plan.v3` 保留 v2 的主/次目标、立场、置信度、动作信号解读、追问、验证条件、暂定票型、战术和三类 ID，并新增结构化连续性原因及最多三个新增公开 signal ID。当天计划仍会随发言保存，后续投票把暂定票作为有权重的依据。
- 决策层字段全部直接位于扁平 JSON 根级。后端仍可升级旧 `public_speech.v1` 和 `public_speech_plan.v2`，也只会安全展开键恰好为 `schema_version + fields` 的 v2/v3 包装；任何额外顶层或内层字段继续由严格 schema 拒绝。
- 身份、验人结果、技能信息和可选范围始终由规则引擎提供，LLM 不能创建或直接写入游戏事实。
- 公开动作信号覆盖上警、不上警、退水、继续竞选、警长票、警长结果、警徽移交、公开验人说法、上一天放逐票、已公布出局和低信息量发言。`seer_check_claim` 只说明谁公开给谁发过金水或查杀，明确标注真假未确认，不包含后台声明来源、真实角色或阵营；夜间出局也只提供已公布的安全摘要。
- 若公开验人当天直接指向当前 NPC，决策上下文会加入 `response_requirements`，要求计划选择对应信号并把声明者纳入目标；规则回退和 LLM 计划使用相同校验，避免好内容生成后又在表达阶段丢掉关键回应。
- 输出校验开启时，普通发言必须选择具体目标，并至少引用一项公开动作、公开 RAG 证据或合法声明；短句“没信息，过”会被拒绝并要求改成明确判断、追问或后续验证点。LLM 可以判断错、被欺骗或错误解读公开动作的动机，但不能改写动作、身份、查验、技能、出局和胜负事实。
- “低信息量发言”是保守评价，不等于狼人身份，也不会自行增加怀疑值；输出校验开启时可以分析已校验文本，关闭时只读取 Python 结构化计划、声明和立场卡，不读取原文。
- 普通白天的结构化意图直接驱动 NPC 状态更新；表达层不再依赖“怀疑 / 回应 / 不足以定性”等固定关键词判定意图，因此自然同义表达不会触发无意义重试。反问、否定、假设和转述中的阵营用词也不会被误认为直接身份声明。
- 输出校验开启时，公开桌面上的“4号就是狼”“我是好人”属于可能正确、也可能错误或撒谎的阵营观点，不会拿角色表里的真实身份判定是否合法。“如果他是狼，那3号可能是狼队友”、双狼猜测、引用、反问、否定，以及普通“我的队友”也允许自然表达；只有未经规则授权的第一人称明确狼队自曝，例如“我是狼”“3号是我的狼队友”“我们狼队”，继续硬拒绝。
- 输出校验开启时，结构化目标和已选动作信号是表达必须保留的下限，不再是排他的措辞上限：LLM 可以用其他公开座位作对照，也可以准确复述规则状态中已经存在的公开动作与公开声明；不存在的动作、身份、查验和技能事实仍会被拒绝。
- “我拿的是村民牌”“4号起跳预言家，验了7号”“7号，查杀”等常见省略说法会按语义归一；同一句转述会延续明确的预言家主语，并列引用他人的阵营判断不会被算成当前 NPC 的直接断言。
- 输出校验开启时，后端按“声明者 → 目标 → 结果”校验验人归属；“5号给8号金水”只会把8号识别为目标，引用他人的公开验人不会变成当前角色新增验人。
- “我是预言家 / 我起跳预言家 / 我验了4号”“好人 / 金水”等自然等价表达都可通过，不再要求复述模板原句。
- 输出校验开启时，真正篡改验人结果、改变目标、凭空增加查验或技能行动、断言未公开神职、未经授权自曝本人或明确狼队名单都会被拒绝，最多纠正 5 轮后回退规则文本。
- 输出校验关闭时不会执行上述文本校验：模型原文可能错误或越界并会直接显示，但 Python 只消费预先确定的合法计划和规则文本，不会把原文解析成权威目标、声明、怀疑值或技能建议。
- 输出校验开启时，梅长苏彩蛋使用独立校验授权：LLM 必须保留规则引擎给出的真实自我身份，遗漏、改错或扩展为其他角色身份时仍会被拒绝；关闭校验后彩蛋文本同样按原文直出，真实彩蛋状态仍由 Python 记录。

### 本轮 NPC 决策里程碑（已完成）

本轮已完成下列边界，并通过后端、Godot 资源与十二人规则流程的自动化回归：

- 每次公开发言会生成 `public_position.v1` 精炼立场卡，只保留“信谁、不信/怀疑谁、暂时想投谁、什么新信息会促使改票”等结构化结论。后续 NPC 的公开 RAG 证据和引用都使用这张摘要，不再把长篇原发言重新送回决策层；立场卡表示角色当时的公开判断，不是规则验真。“不怀疑”“不会投”等否定句按对象解析，不会反向制造立场。
- 跳预言家的角色可以发布版本化警徽流；每个版本记录 `effective_night_day`、下一夜验人、后续顺验和合法公开金水锚点。金水分支固定传给当夜验人，查杀分支传给既有公开金水或撕徽。场上形势变化时允许附公开理由换流，“换流”本身不扣可信度；改流理由、前后叙事和后续行动是 NPC 可以评估的公开信号。真预言家的实际夜间查验只软参考当夜有效警徽流，不被它强制锁定。
- 移交或撕毁警徽只在匹配某个明确金水/查杀分支时，才形成“按该角色自己的警徽流所表达的身份声明”。这不等于规则引擎确认验人真假；对没有写进明确另一分支的普通“没接徽”不做阵营推断。
- 玩家在警上同次跳预言家时必须发布首版警徽流，警下首次发布与后续修改仍可选；服务端在写入公开声明前对整组输入一次性校验。折叠 UI 与 Python 会自动计算金水/查杀分支，玩家或 LLM 的冲突自由文本不会成为第二份事实；“目标已出局 / 出现公开身份”这类事实型换流理由也必须命中公开记录。警长当选、移徽或撕徽后，参赛角色头顶的警长标识会跟随规则状态更新。
- 警长票与白天放逐票改为每名 NPC 先按合法公开信息形成个人信念，再在所有合法候选中进行可复现的概率抽样。强证据仍可以形成共识，系统不会为了“票型好看”强制分票，也不会按隐藏阵营强制站边。
- 狼队的集中投票、分票做身份、倒钩、救援、卖狼和切割都是受公开局势与个体参数影响的软策略，不会每局生硬触发；“狼给狼队友发查杀后，被查杀狼不得反向站台”仍是跨发言、投票和警徽的硬叙事一致性。
- Python 规则引擎继续是身份、权限、行动、票型结算、出局和胜负的唯一事实源；LLM 只提供结构化策略和角色化表达，不定义或改写规则结果。

### 小镇会议

白天不再一次性生成所有 NPC 发言，而是进入有顺序的小镇会议：

1. 第一夜行动完成后先进行警上报名、竞选发言、退水和警长投票；平票只进行一次 PK，首夜出局结果在竞选全部结束后公布。
2. 有警长且前夜有人出局时，从出局者中随机选择锚点，由警长选“出局左”或“出局右”；无人出局时选择“警左”或“警右”。
3. 选择出局左或出局右时，警长按照自身座位自然进入顺序；选择警左或警右时，警长自然最后发言。没有警长时使用随机首位和方向。
4. 固定逻辑座次为：玩家 → 梅西 → C罗 → 周深 → 梅长苏 → 塞尔达 → 小骑士 → 大黄蜂 → 喜羊羊 → 懒羊羊 → 洛洛 → 奇异博士。
5. 轮到玩家时在控制面板提交公开发言；轮到 NPC 时走到对应 NPC 身边按 `E`。
6. 前序发言会影响后续 NPC 的怀疑、发言和投票，NPC 正式发言会显示公开 RAG 依据。
7. 警长发言时可公开暂时归票，后续角色会参考该信息；全员发言结束后警长再确认或调整最终归票。
8. 全员发言结束后进入会后自由活动，结束自由活动后进入同步投票。

### 会后私密追问

- `FREE_ACTIVITY` 阶段可以走近任意存活 NPC，按 `E` 进行私密追问。
- 每名 NPC 每天第一次追问会影响它的怀疑、对玩家的信任和后续投票判断。
- 同一天可以继续追问，但后续问题不会再次修改该 NPC 的决策状态。
- 私密内容不会进入公开日志，也不会影响其他 NPC。
- 狼人可以在私聊中误导玩家。
- 预言家是否透露查验结果取决于对玩家的信任和自身谨慎程度。
- 守卫不会在私聊中直接公开守护目标。
- 狼人杀私聊只保存在当前对局，不会写入普通小镇的 `memory.json`。
- 私聊采用对话视角：NPC 用“我”指自己、用“你”指玩家，第三方统一显示为“号码 + 名字”。
- 玩家输入中的“我/自己”指玩家，“你”指当前 NPC；没有明确上下文的“他/她/TA”会要求补充号码或名字。
- 指代不清的问题不会消耗该 NPC 当天第一次有效追问；同一 NPC 本轮最近一次明确提到的第三方可以被后续代词承接。

### 游戏结束复盘

- 对局进入 `GAME_OVER` 后自动打开全屏复盘，关闭后可从控制菜单点击“查看本局复盘”重新打开。
- 角色复盘会公开全部 12 人的身份、阵营、胜负、生存结果和个人行动，行动详情默认折叠。
- 对局时间线按天数和阶段展示夜晚技能、查验结果、女巫用药、猎人开枪、实际挡刀、公开身份声明、公开发言、完整私聊、投票理由和出局结果。
- “解释复盘（赛后）”按决定展示当时保存的依据、更早/更晚日期的公开证据、赛后
  身份真值和错误类别；它明确不是角色当时可见的隐藏信息或完整思维链。
- “解释复盘”页顶部新增“复盘建议”：根据玩家本局身份与赛后公开事实生成静态建议
  （如预言家验到狼未推动、守卫未挡刀、女巫留药、猎人误伤、村民错票），只基于规则
  不变量与赛后结果，不改变任何规则状态。
- 复盘页新增“本局高光”：自动汇总预言家验到狼、猎人带走狼、女巫毒中狼、首日放逐狼
  等名场面；“导出复盘”可把高光与完整时间线导出为文本文件（`user://exports/`）。
- 私密信息仅在游戏结束后公开；进行中的游戏请求复盘接口会被后端拒绝。
- 输出校验开启且候选达到 5 轮上限仍失败时，对话框提供“LLM校验失败查看”；进行中的对局只显示失败原因并隐藏原始返回，服务端 JSONL 与赛后复盘保留完整原文用于审计。输出校验关闭时校验次数为 0，不生成校验失败记录。

### 公开决策 RAG

- NPC 正式发言和投票理由现在都会使用混合 RAG 证据。
- 没有前序公开发言时，NPC 会使用知识库中的规则或自身判断风格作为依据。
- 存在前序发言时，会优先检索与当前怀疑目标相关的公开发言。
- 正式发言响应和 NPC 投票响应都会返回 `evidence_titles` 与 `retrieval_mode`。
- Godot 正式发言对话框和投票面板会显示证据标题及“向量 + 关键词”或“关键词降级”。
- 私聊、预言家查验和 NPC 内部记忆不会成为可引用的公开 RAG 证据。普通白天结构化决策只会把当前 NPC 有权知道的私有信息作为策略输入，并禁止选择为公开证据或写入发言。

## 游戏流程

```text
NIGHT
  夜晚身份行动与结算
    ↓
HUNTER_SHOT（仅玩家猎人满足开枪条件时）
  选择开枪目标或不开枪，然后返回被中断的流程
    ↓
SHERIFF_SIGNUP → SHERIFF_SPEECH → SHERIFF_WITHDRAWAL（仅第一天）
  报名、竞选发言与明确退水
    ↓
SHERIFF_VOTE → SHERIFF_RUNOFF_SPEECH/VOTE（平票时至多一次）
  警下同时投票，产生警长或撕毁警徽
    ↓
MEETING_ORDER（有警长时）
  警长选择出局左/右或警左/右
    ↓
DAY_MEETING
  逐人公开发言，警长在自身轮次提出暂时归票
    ↓
SHERIFF_NOMINATION（有存活警长时）
  全员发言后确认或调整最终归票
    ↓
FREE_ACTIVITY
  走近存活 NPC 进行私密追问
    ↓
VOTE
  玩家提交目标与理由，全部票同时产生并结算
    ↓
HUNTER_SHOT（可选）→ BADGE_TRANSFER（警长出局时）/ 下一夜 NIGHT / GAME_OVER
```

## 运行

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

已有 `backend/.venv` 的项目也需要重新执行一次 `pip install -r requirements.txt`，安装 FastEmbed、HTTPX 和 python-dotenv。第一次触发知识检索时会下载约 90MB 的中文向量模型，之后使用本地缓存。

### 2. 启动 Godot

用 Godot 4 打开：

```text
game/project.godot
```

运行主场景 `game/scenes/Main.tscn`。

### 3. 开始一局游戏

1. 在开局设置窗口输入玩家名；身份默认随机，也可指定女巫等身份进行测试，然后点击“开始游戏”。关闭窗口后可从顶部“新对局”再次打开。
2. 开局进入 `NIGHT` 时场景切换为夜景；根据身份完成夜晚行动，然后点击“结算夜晚”，进入警上或白天阶段后恢复日景。
3. 第一天在面板选择是否上警；轮到玩家时填写警上发言，轮到 NPC 时走近对应角色按 `E`。
4. 在退水阶段通过两个独立按钮明确选择“继续竞选”或“退水”；未上警玩家无需替 NPC 推进阶段，警下玩家随后在面板提交警长票。
5. 玩家当选警长时选择发言侧；轮到自己发言时可以选择暂时归票目标，全员说完后确认或调整最终归票。
6. 轮到玩家时使用面板发言，轮到 NPC 时走近对应角色并按 `E`；控制面板只展示当前阶段需要的操作。
7. 会议结束后走近 NPC 私聊，再点击“结束自由活动”。
8. 选择放逐目标、填写理由并点击“投票并公布”，直接查看简明票型和详细理由。
9. 玩家猎人满足开枪条件时先处理开枪；玩家警长出局时随后选择警徽去向。
10. 游戏结束后查看自动弹出的复盘；关闭后可从展开菜单再次进入。

## 自检

项目根目录执行：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

自检内容包括：

- V4.3-A/B 的 `0700/0600` 原子存档、旧文件保护、命令事务回滚、快照/事件链/
  配置完整性、同 key 并发单次提交、payload/端点冲突、持久化失败回滚、阶段推进后
  原响应恢复、结果台账篡改拒绝、启动批次 fail closed，以及 simulation/replay
  零落盘。
- V4.4-A/B 的公开证据与分析 schema、稳定/连续 ID、承诺六态转换、正常修订和
  公开条件失效不误报、四类中立矛盾候选、NPC/UI 同源消费、只读确定性、未公布
  票型隔离及隐藏身份/内部来源/夜死原因不变性。
- 无 HTTP 批量模拟的同 seed 精确重放、合法终局、显式 seed 隔离、内存清理、LLM/RAG 禁用和隐藏身份互换不变性。
- `agent_town_metrics.v4` 的赛后权限、schema 版本、空样本 `null`、票数/毒药/第二夜选择/假验人组合/跨日选票转移/条件胜负守恒、数值范围、按玩家身份/投票角色/天数完整聚合及跨进程精确重放。
- `fake_seer_campaign.v2` / `fake_seer_check_mix.v1` 的参选混合、冻结随机流、全局随机隔离、合法验人组合和好人精确身份互换不变性；`good_exile_cross_day.v1` 的争议票收敛、压倒性票禁用、女巫复用及隐藏身份互换不变性。
- `belief_state.v2` 的公开/行动者私有/狼队权限、证据 ID 引用、席位覆盖、分数范围、软证据跨日衰减、硬事实与合法私有知识不衰减、结构化私聊隔离、隐藏身份与未公布夜间结果差分，以及 shadow on/off 玩法摘要一致。
- `stance_summary.v1` 的目标/证据权限、隐藏身份与自由文本不变性、阶段空转稳定性、同目标一致、无新证据变化、新证据后变化、分类计数守恒，以及 stance-on/off belief 与 gameplay 一致。
- JSON 配置格式和知识条目数量。
- Python 后端编译。
- LLM mock、OpenAI-compatible 请求、完整 JSON 对象适配、正式发言与私聊接入，以及超时/限流/坏 JSON 回退。
- 坏坏和然然的 DeepSeek 普通聊天、规则回退、锁外网络请求、跨居民/跨玩家记忆隔离、持久化和最近 8 轮上下文边界。
- 普通白天 NPC 发言的私有策略/公开表达两段隔离、严格结构化 schema、公开行动信号白名单、非法目标/声明/信号/私有证据拒绝、公开人物自然引用、伪造动作拦截、空泛过麦重试、结构化怀疑值更新和无提前规则状态提交。
- `public_speech_plan.v2/v3` 的扁平根级契约、旧 `fields` 包装的安全兼容、额外字段拒绝、连续性原因、主次目标、立场、追问、验证条件、暂定票和战术权限，以及 v1/v2 兼容升级、发言计划到投票的同日闭环和跨日隔离。
- `public_position.v1` 字段/精炼引用、警徽流版本与 `effective_night_day`、公开金水锚点、合理换流零默认惩罚、查验软参考、分支移徽/撕徽声明与普通未接徽不推断的边界。
- 警长票/放逐票的多种子个体公开信念、概率抽样可复现性、候选顺序不变性、强证据可共识与隐藏身份互换不变性，以及狼队软策略与“狼查杀狼”硬叙事边界。
- 玩家警上跳预言家+必填警徽流的原子提交、警下可选修改、智能分支、折叠控件、公开摘要展示和参赛角色头顶警长标识的状态同步。
- 警下相近候选人的自然分票、玩家与 NPC 警上发言统一评分、收到金水的软影响与非锁票、候选隐藏身份互换不变性，以及被发金水/查杀后的信号必选、公开回应和相反警长票说明。
- DeepSeek 声明者/目标归属、隐式预言家起跳、真实自然改写样本、事实篡改反例、服务端原文审计、游戏内脱敏和规则文本兜底。
- 混合向量检索、语义召回和关键词强制降级。
- 12 人预女猎守身份分配、指定玩家女巫、双药状态、固定座次和 11 名 NPC 名称。
- 狼队互认、玩家狼人最终刀口、悍跳欺骗、框人/反推/拉开距离/卖队友，以及“狼查杀狼”后警长票、发言、放逐票和警徽叙事一致性。
- `npc_tuning.v1` 严格配置、四层覆盖、每局参数快照、好人受骗和相近候选误投的可复现边界。
- 随机会议方向、存活角色发言顺序和逐人推进。
- 发言对怀疑状态的影响。
- 玩家身份声明解析、真预言家起跳、狼人悍跳、神职信息公开和对跳决策影响。
- 左上角关键公开信息的折叠节点、计数与首次自动展开，以及公开说法和已确认动作的区分；同一声明仅改变内部来源标签时，前端公开投影必须完全不变。
- 警上报名、强制 NPC 真预言家起跳、玩家预言家自由选择、狼队让跳、退水与一次 PK。
- 首夜结果延迟公布、女巫救人不误伤其他座位、全部出局来源审计，以及退水角色持续禁投。
- 警长发言侧、出局锚点下的自然座次、暂时归票影响、最终改票、1.5 票锁定，以及猎人技能后的警徽移交。
- NPC 角色化口吻、口头禅和彩蛋配置，以及关键声明在 LLM 润色后的完整性。
- 私密追问的决策影响、每日次数限制和公开日志隔离。
- 私聊“我/你/他”的视角转换、跨消息指代和含糊指代次数保护。
- NPC 公开发言与投票理由的 RAG 证据、检索模式和私密来源隔离。
- 对话框和完整控制面板的内置中文字体、关键字形覆盖与 `U+FFFD` 替换字符检查。
- `agent_town_responsive_layout.v1` 的物理窗口三档、动态安全区、HUD/设置/复盘限幅、
  `2 / 3 / 4` 列角色卡、`12px` 字号下限，以及 `1100×650`、`1280×720`、
  `1600×900` 验收尺寸。
- `agent_town_focus_navigation.v1` 的 WORLD/PANEL/TEXT_ENTRY/MODAL 范围、整局
  Tab/方向键导航、滚动区可达、可见焦点框、模态鼠标边界、关闭后焦点回还和 WASD
  恢复，以及玩家本局行动记录和完整公开发言。
- 自由活动进入投票，玩家与 NPC 票同时生成、票型汇总和理由公开。
- 预言家查验、守卫挡刀、女巫药品、同守同救失效、猎人开枪与中毒禁枪。
- 屠边、狼人控场、猎人开枪优先级、跨轮记忆和投票结算。
- 游戏结束后的身份公开、个人行动和全局时间线。
- Godot 分层小镇背景、严格的 `NIGHT` 昼夜映射、夜间文字可读性和主场景 headless 加载。
- 两名常驻居民的非参赛 ID、无重叠摆放、场景皮肤、对话头像和原创 64×64 像素资源。

## 项目结构

```text
agent-town-demo/
  COMMANDS.md
  game/
    assets/
      characters/
        player.svg
        messi.svg
        ... 其余 10 名角色像素素材
      fonts/
        NotoSansSC-Variable.ttf
        OFL.txt
    project.godot
    scenes/
      Main.tscn
      TownBackground.tscn
      Player.tscn
      NPC.tscn
      DialogBox.tscn
    scripts/
      main.gd
      town_background.gd
      day_night_check.gd
      player.gd
      npc.gd
      dialog_box.gd
  backend/
    .env.example
    app/
      belief.py
      config.py
      determinism.py
      event_log.py
      experiment.py
      game_persistence.py
      idempotency.py
      invariance.py
      llm.py
      llm_fingerprinting.py
      llm_observability.py
      llm_pricing.py
      main.py
      npc_decision.py
      npc_policy.py
      npc_policy_data.py
      npc_reasoning.py
      npc_tuning.py
      player_speech.py
      player_strategy.py
      post_game_review.py
      public_evidence.py
      rag.py
      schemas.py
      simulation.py
      simulation_metrics.py
      speech_quality.py
      stance.py
      vote_calibration.py
    config/
      llm_pricing.json
      npc_profiles.json
      knowledge_base.json
      npc_tuning.json
    data/
      memory.json
      games/                 # 运行时私有完整存档，Git 忽略
    requirements.txt
    README.md
  scripts/
    check_game_persistence.py
    compare_simulation_artifacts.py
    simulate_games.py
    summarize_llm_observability.py
    smoke_check.py
  README.md
```

## 后端接口

### 狼人杀

- `GET /api/health`：查看狼人杀后端状态。
- `GET /api/llm/status`：查看 LLM 开关、provider、模型、配置状态和安全配置指纹，
  不返回 API Key。
- `GET /api/rag/status`：查看当前检索模式、向量模型和初始化状态。
- `POST /api/game/start`：创建固定 12 人局。
- `POST /api/game/{game_id}/save`：原子保存当前完整私有状态。
- `POST /api/game/{game_id}/restore`：校验并手动恢复磁盘存档。
- `GET /api/game/recovery-status`：查看最近一次启动恢复扫描结果。
- `GET /api/game/{game_id}/state`：读取阶段、角色、会议、公开日志、统一公开证据时间线，以及只基于公开记录且不含赛后真值的承诺/矛盾分析。
- `GET /api/game/{game_id}/summary`：仅在游戏结束后读取完整身份、行动、时间线和
  `post_game_explainable_review.v1` 决策解释。
- `GET /api/game/{game_id}/events`：仅在游戏结束后导出完整、带可见范围的规则事件链。
- `POST /api/game/{game_id}/replay`：仅在游戏结束后执行隔离的规则模板确定性重放。
- `POST /api/night/action`：提交玩家夜晚行动。
- `POST /api/night/resolve`：自动补齐 NPC 行动并结算夜晚。
- `POST /api/hunter/shot`：玩家猎人出局后选择开枪目标或不开枪。
- `POST /api/sheriff/signup`：玩家提交是否上警并开始候选人发言。
- `POST /api/sheriff/player-speech`：玩家提交警上或 PK 发言。
- `POST /api/sheriff/npc-speech`：生成当前 NPC 候选人的警上或 PK 发言。
- `POST /api/sheriff/withdraw`：提交继续竞选或退水，并推进警长投票。
- `POST /api/sheriff/vote`：一次提交玩家警长票并同时生成警下 NPC 票。
- `POST /api/sheriff/meeting-order`：玩家警长选择出局左/右或警左/右。
- `POST /api/sheriff/nominate`：玩家警长提交归票目标。
- `POST /api/sheriff/transfer`：玩家警长出局后移交或撕毁警徽。
- `POST /api/day/player-speech`：轮到玩家时提交公开发言。
- `POST /api/day/npc-speech`：轮到指定 NPC 时生成一条公开发言。
- `POST /api/day/private-chat`：自由活动期间向指定 NPC 私密追问。
- `POST /api/day/end-free-activity`：结束自由活动并进入投票。
- `POST /api/vote/submit-and-resolve`：提交玩家目标与理由，同时生成全部 NPC 票并结算。

旧的 `POST /api/day/npc-speeches` 和三步投票接口暂时保留兼容，但 Godot 主流程不再使用它们。
以上开局后规则写接口都接受可选 `idempotency_key`；同一局内相同 key 只能对应
同一端点和同一 payload。开局、查询、preview、save/restore 和 replay 不在范围内。

### 小镇 AI NPC

- `POST /chat`：普通小镇对话；坏坏和然然优先使用全局 DeepSeek 并返回 `llm_used`、`llm_provider`、`llm_fallback_reason`，其他 NPC 保持规则回复。
- `GET /npcs`：查看 NPC 人设。
- `GET /knowledge`：查看知识条目。
- `GET /knowledge/search`：调试 Top-K 混合检索，返回关键词分数、向量分数和检索模式。
- `GET /memory/{player_id}/{npc_name}`：查看长期对话记忆。
- `DELETE /memory/{player_id}/{npc_name}`：清空指定 NPC 记忆。
- `POST /admin/reload-config`：原子重载人设、知识库与 NPC 智能参数；调参只影响之后创建的新对局。

## 记忆边界

- `backend/data/memory.json` 保存普通小镇聊天的长期记忆。
- `backend/data/memory_meta.json` 保存两名常驻居民的跨对话摘要与偏好计数（派生自
  memory.json，可随时重建）。
- 狼人杀身份、查验、守护、怀疑、关系和发言记忆保存在活动游戏状态与
  `backend/data/games/*.json` 私有完整存档中。
- 狼人杀私密追问保存在当前对局的 `private_conversations` 和同一私有存档中，
  不进入公开日志。
- NPC 隐藏身份和预言家查验结果不会出现在公共状态里。
- 完整身份、夜间行动和私聊只会通过游戏结束后的复盘接口公开。
- 真实 FastAPI 服务重启会恢复完整性和配置均通过的未完成局；终局存档启动时跳过，
  仍可手动恢复。完整存档包含隐藏事实，不得作为公开数据发布。

## NPC 智能微调

无需改 Python 即可编辑 [`backend/config/npc_tuning.json`](backend/config/npc_tuning.json)。配置采用严格的 `npc_tuning.v1`，数值覆盖顺序固定为 `global_defaults < factions < roles < npcs`：越靠右越具体，也越优先。例如先给全部好人设置容易受骗的基线，再为预言家降低受骗度，最后给梅长苏设置个人差异。

| 字段 | 调高后的主要效果 |
| --- | --- |
| `reasoning_skill` | 更重视证据和矛盾，较少在接近候选人间误判 |
| `social_susceptibility` | 更容易受警长、共识、关系和公开站边影响 |
| `decision_variance` | 在分数接近的合法候选人之间更容易产生错票；不是无视证据的纯随机 |
| `plan_consistency` | 后续投票更愿意延续自己发言时的暂定票 |
| `deception_susceptibility` | 更容易采信看似完整的假验人和狼人叙事 |
| `deception_strength` | 狼人公开说服、悍跳和误导的影响力更强 |
| `team_coordination` | 狼队更重视分工、让跳和一致行动 |
| `teammate_bus_pressure_threshold` | 队友公开压力达到该值后才考虑卖队友；调低会更早切割 |
| `teammate_black_check_chance` | 在其他局势条件满足、但队友尚未达到压力阈值时，提前使用“狼查杀狼”的机会更高 |
| `teammate_black_check_min_pressure` | 队友达到该公开压力后直接触发“狼查杀狼”分支；调低会更激进 |

本轮投票与狼队软策略主要看四组参数：调高 `reasoning_skill` 会让强证据差距更难被随机性推翻；调高 `decision_variance` 会提高接近候选之间的个体差异；`social_susceptibility` 与 `deception_susceptibility` 分别放大共识/关系影响和虚假叙事影响；`team_coordination` 只提高狼队采用集中、分票、倒钩、救援、卖狼或切割的协作倾向，不直接锁定某一票或关闭硬叙事校验。

除两个压力阈值外，其余八项范围为 `0.0–1.0`；两个压力阈值范围为 `0–100`。推荐一次只改一个维度：概率/能力值每次改 `0.05–0.10`，阈值每次改 `5–10`，然后执行：

```bash
curl -X POST http://127.0.0.1:8000/admin/reload-config
backend/.venv/bin/python scripts/smoke_check.py
```

重载成功会返回 `tuning_schema_version: "npc_tuning.v1"` 和 `applies_to: "new_games"`。已经开始的对局保留开局时的参数快照，因此要新开一局再观察；建议同一设置试玩或批量记录 10–20 局后再继续调整。无效 JSON、未知字段、越界值或拼错的 NPC 名称会返回 `400`，当前有效配置会完整保留。修改 `.env` 中的 LLM provider、模型或 Key 仍需手动重启后端。

批量模拟命令不会启动 FastAPI 或 Godot。完整 smoke 会短暂执行 Godot headless 资源加载检查，但不会启动编辑器或常驻服务；需要试玩时请按“运行”一节手动启动。

## RAG 状态

当前已经实现第一版轻量混合 RAG：

- 使用 FastEmbed `0.7.4` 和 `BAAI/bge-small-zh-v1.5` 中文向量模型。
- 模型约 90MB、512 维，使用 ONNX Runtime，不需要安装 PyTorch 或运行大型本地 LLM。
- `backend/app/rag.py` 负责懒加载模型、生成向量和内存索引。
- `backend/config/knowledge_base.json` 目前包含 111 条知识，包含十二人规则、警长机制、公开身份声明、11 名狼人杀 NPC 的判断风格和两名常驻居民的专属知识。
- 检索分数由关键词命中和向量相似度共同组成。
- `/chat` 和狼人杀私密追问都会返回 `retrieval_mode`。
- Godot 对话框会显示“向量 + 关键词”或“关键词降级”。
- 私密追问会检索静态知识、公开日志和当前 NPC 自己的内部记忆。
- 私有记忆只参与对应 NPC 的判断，不会作为可公开来源返回给玩家或其他 NPC。
- 小镇会议正式发言与 NPC 投票会检索静态知识和已有公开发言，生成可展示的公开证据。
- 公开决策检索器不会读取私聊、查验结果或 NPC 内部记忆。
- FastEmbed 未安装、模型下载失败或推理失败时，会自动退回关键词检索。

查看状态：

```bash
curl http://127.0.0.1:8000/api/rag/status
```

需要临时禁用向量模型时：

```bash
AGENT_TOWN_DISABLE_VECTOR_RAG=1 uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

第一版 RAG 使用本地轻量向量模型；大型文本生成交给可选的云端 LLM API，不在 M2 MacBook Air 上运行大型本地 LLM。

## LLM API

后端已经实现统一 `LLMClient`，支持 `mock` 和 OpenAI-compatible provider。狼人杀普通非警长 `DAY_MEETING` NPC 发言使用结构化决策，并由开局选项控制；坏坏和然然的普通小镇聊天则独立使用全局 LLM 配置，不依赖本局狼人杀开关。两条路径都由 Python 保留规则回退。

首次配置：

```bash
cd backend
cp .env.example .env
```

在 `backend/.env` 中选择一个 provider，重启后端使配置生效。下面的 API Key 都只填写在本机 `.env`，不要写入 Godot、JSON、日志或提交到仓库。

### DeepSeek 低价付费（当前推荐）

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的_DEEPSEEK_API_KEY
LLM_MODEL=deepseek-v4-flash
```

不要再使用即将弃用的 `deepseek-chat` 或 `deepseek-reasoner` 别名，本项目直接使用 `deepseek-v4-flash`。

### Gemini 免费层

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=gemini
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_API_KEY=你的_GEMINI_API_KEY
LLM_MODEL=gemini-3.5-flash
```

### OpenRouter 免费模型路由

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=你的_OPENROUTER_API_KEY
LLM_MODEL=openrouter/free
```

### Groq 免费开发额度

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=你的_GROQ_API_KEY
LLM_MODEL=openai/gpt-oss-20b
```

其余通用设置：

```dotenv
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=300
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=0.35
```

`LLM_MAX_RETRIES=1` 表示请求因超时、限流、临时服务错误、空内容或无效 JSON 失败后，再自动请求一次。DeepSeek 请求会显式关闭默认思考模式，并启用官方 JSON Object 输出，适合这里的短文本 NPC 决策任务。

启动后可检查配置，但响应不会暴露密钥：

```bash
curl http://127.0.0.1:8000/api/llm/status
```

也可以不启动后端，先发送一次小请求检查当前 provider 的连通性：

```bash
backend/.venv/bin/python scripts/check_llm_connection.py
```

工作方式：

- 以下两段调用、结构化 allowlist 和语义拒绝描述适用于“输出校验开启”；关闭校验时跳过 LLM 策略调用，由 Python 选定计划后只请求 1 份最终显示文本。
- Python 规则引擎为普通白天发言组装版本化上下文：当前阶段、NPC 真实身份与性格、该角色有权知道的事实、近期公开日志、自身私有记忆、RAG 证据、公开动作信号，以及合法目标和公开声明选项。
- 第一段 LLM 调用只返回扁平的 `public_speech_plan.v3` 策略 JSON，严格禁止 `text` 和 `fields` 包装。除 v2 原有必填字段外，还必须返回 `continuity_reason` 与 `continuity_signal_ids`；所有字段直接位于根级，可空字段也必须显式返回 `null`。后端兼容 v1/v2 计划和键恰好为 `schema_version + fields` 的旧 v2/v3 包装，兼容过程不会放过额外字段。
- 主次目标用来比较发言对象；`stance` 只能支持、反对或未定；`confidence` 为 `0–100`；`question` 和 `verification` 分别给出具体追问与之后可观察的复核标准；`provisional_vote_target_id` 把发言计划接到当天投票；`tactic` 只能从白名单选择。三类 ID 列表各最多三项，所有目标和 ID 都必须来自本次规则上下文，狼人专属战术只允许狼人使用，针对队友的战术还必须指向规则引擎允许暴露的狼队友。
- 当天有人公开给 actor 发金水或查杀时，上下文额外加入 `response_requirements`，列出必须选择的验人信号和必须进入主/次目标的声明者。它只约束“必须回应这件已经公开的事”，不要求相信该声明，更不会暴露真假。
- 私有知识和完整公开历史只进入第一段决策调用。计划通过后，第二段表达调用只接收人物口吻和当前阶段，并返回 4–18 个中文字符、不含座位号、身份、动作或票型事实的语气前缀；Python 根据计划渲染完整判断、追问、验证点和暂定票并与前缀拼接。表达调用不会收到真实身份、狼队、夜间记忆、私聊原文、完整日志、计划内容、私有战术名或第一段 raw output。
- 公开声明以不可拆分的规则事实包提供，LLM 不能自由拼接身份、查验或技能结果。普通观察/施压/辩护必须有合法主目标和至少一项公开依据；追问、验证和立场目标必须落在已选主次目标内，支持对象不能同时成为暂定票，未知枚举、额外字段、重复或越权 ID 都会被拒绝。
- 后端允许策略判断错：普通好人的警长票和放逐票只读取公开声明、公开动作、发言说服力、关系、怀疑与本局智能参数，不读取候选人的真实身份或阵营。好人因此可以把警长票投给假预言家、在真假预言家之间分票，也可以相信狼人的公开查杀而放逐真预言家；真预言家仍可使用自己的真实查验，狼人仍可使用合法狼队知识。允许的是“对公开事实的错误推断”，不是伪造动作、查验、技能或出局事实。
- 已校验计划保存在当天发言中。放逐评分会综合怀疑、公开压力、关系、警长归票、公开查杀、计划暂定票与 NPC 参数；计划是有权重的倾向而非锁票，后续证据可以覆盖它，跨天计划不会复用。
- “狼查杀狼”是硬叙事约束：被队友公开查杀的狼人不能投查杀来源当警长，后续发言和放逐票必须反对来源；若查杀来源成为警长，移交警徽时也不会再选择被它查杀的队友。这个约束优先于一般狼队抱团，避免“被队友查杀却仍投队友当警长”的低级冲突。
- Python 渲染的正文必须保留已选动作事实并作出具体贡献，不能用“没信息，过”结束这一轮；LLM 语气前缀只负责增加人物口吻，不接触、更不能反向决定身份、技能、立场、票型或胜负。
- 两段都读取本局 `enable_llm_validation`：默认最多校验并纠正 5 轮；关闭时跳过 LLM 结构化策略选择，由 Python 使用合法规则计划，再请求 1 份最终表达，语义校验与纠错均为 0 次。
- 警上、警长发言和私聊仍使用 `{"text": "..."}` 安全改写，不在这个小里程碑中扩展策略权限。
- 私聊中的含糊代词仍由规则决定澄清内容，但澄清措辞也会经过 LLM。
- 未勾选本局 LLM、provider 未配置、响应无法解析，或开启校验后 5 轮均失败时会回退规则文本，游戏流程不中断。原文直出模式固定只请求 1 次，不进行网络重试或语义纠错。
- Godot 对话框会显示“LLM（deepseek）”；仅在输出校验开启时，被拒绝的候选原文才会写入 `backend/data/llm_validation_failures.jsonl`。达到 5 轮上限后，进行中的对局只返回脱敏占位和原因，赛后复盘可以查看完整审计原文。
- 新写入的校验日志包含 `recorded_at` 和 `validator_version`，便于区分历史版本的旧误判与当前行为。
- `mock` 不发送网络请求，适合验证开关和回退链路。

保持不变的规则边界：

- Python 规则代码继续决定身份、知识权限、可选目标范围、合法声明事实、夜晚行动、投票结算、出局和胜负；普通白天 LLM 只能在给定范围内选择结构化发言计划，计划中的暂定票只是规则评分的一项输入。
- 输出校验开启时，LLM 文本不得伪造查验结果或越过知识权限；输出校验关闭时原文可能出现这类幻觉，但模型仍拿不到额外隐藏上下文，且原文不能修改游戏状态。
- M2 MacBook Air 继续只运行 Godot、FastAPI 和轻量向量模型，文本生成使用云端 API。

## V4 进度与下一阶段

V3.1-A 至 V3.2-B 已完成封版；V4.1-A/B 已增加三档合法玩家策略、按身份配对基准、玩家赛后表现指标和无副作用的玩家发言结构化预览。V4.2 已增加单一追加事件链、终局导出和规则模板执行式重放；V4.3-A/B 已完成原子存档、启动恢复、外部幂等 key 和重复结算保护；V4.4-A/B 已完成统一公开证据时间线、承诺生命周期和中立矛盾候选；V4.5-A 已完成终局决定解释和五类错误归因；V4.6-A/B 已完成 NPC 公开发言质量基线、完整/生效配置指纹、脱敏 LLM Prompt/config 指纹、保守成本口径和规则 artifact 配对 A/B；V4.7-A/B 已完成首局分阶段安全引导、物理窗口三档响应式和整局键盘焦点范围；V4.7-C 已完成 Python 3.12 + Godot 4.7.1 的 Linux/macOS CI、分层 smoke、源码交付元数据和 [`封版清单`](docs/V4_RELEASE_CHECKLIST.md)；V4.8-A 已增加开局 `enable_llm_validation` 输出校验选择，支持最多 5 轮校验或生成 1 次、校验 0 次的原文直出，并保持 Python 规则结算和旧存档兼容。V4 已于 `2026-07-24` 在 [`V4 源码仓库`](https://github.com/KEswy/agent-town-demo-v4.0) 以 `v4.0.0` 封版；后续开发进入 V5。

V4 完整任务、依赖和验收口径见 [`V4 改进与开发路线表`](docs/V4_ROADMAP.md)；[`V3 改进与开发路线表`](docs/V3_ROADMAP.md) 保留封版历史。身份、合法行动、投票、出局、警徽与胜负仍由 Python 决定；LLM 只接收当前角色可用的上下文，输出校验关闭时显示文本可以越界，但不能成为 Python 规则输入。

## 开发记录

### 2026-07-24 V4.0.0 源码封版

- 用户明确批准结束 V4 并进入 V5；V4 使用不可移动的注解标签 `v4.0.0` 归档到
  `v4-origin`，没有向三个历史 remote 推送。
- 封版范围是源码与自动化基线，不包含桌面可执行包；Linux 图形交互没有单独人工签署，
  支持范围以 [`V4 封版清单`](docs/V4_RELEASE_CHECKLIST.md) 为准。
- V4.0.0 继续采用“没有项目级 LICENSE、未授予再分发许可”的状态，并排除本地
  `3.0总结/`。V5 应从该标签新建分支，不修改 V4 历史。

### 2026-07-23 V4 公开开发快照

- 创建公开仓库 [`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0)，
  并只用 `v4-origin` 承载 V4 开发快照；`origin`、`v2-origin` 和 `v3-origin` 保持历史
  只读边界。
- 本次不创建 `v4.0.0` 标签，不把开发快照描述为正式封版；正式标签仍需完成
  [`V4 封版清单`](docs/V4_RELEASE_CHECKLIST.md) 的 CI 与人工桌面验收。
- `3.0总结/` 作为本地历史资料保留，不进入本次源码快照。项目根目录没有
  `LICENSE`，当前明确为未授予再分发许可。
- 首次远端 Actions 暴露出 job 创建前不能解析 `runner.temp`；临时存档和 pycache
  变量已移到两个 smoke step，并加入静态回归检查，不改变测试隔离范围。
- Ubuntu core 进一步暴露 Linux `ARG_MAX` 较小；七段内联 Python smoke 统一经 stdin
  传给 `python -`，不再把大型测试程序塞进 `python -c` 的单个命令参数。

### 2026-07-23 V4.8-A 开局 LLM 输出校验开关

- `GameStartRequest` 新增默认开启的 `enable_llm_validation`；Godot 开局窗口允许玩家
  选择默认最多 5 轮校验，或生成 1 次、语义校验与纠错 0 次的原文直出；响应以
  `llm_validation_enabled` 显示实际模式。
- 关闭校验时 Python 先确定合法计划，未校验原文只用于显示，不再解析为权威声明、
  公开立场、怀疑值、技能建议或规则动作；原文可能错误、矛盾或越界。
- 选择封印在 `game_created.command.start_request.enable_llm_validation`，不增加
  `WolfGameState` 字段；旧事件缺键默认开启，旧存档无需改写。居民 `/chat` 不受影响。

### 2026-07-22 V4.7-B Godot 4.7 输入恢复修复

- 修复 `main.gd` 三处 Godot 4.7 warning-as-error 类型推断：引导阶段匹配值、待显示
  引导步骤和 `TabBar` 均改为显式类型。根因是主脚本未加载，不是按钮、鼠标过滤或
  `interact` 映射失效；`player.gd` 独立加载才造成只有 WASD 可用的症状。
- core smoke 新增已知安全写法与旧危险写法的双向断言；通用 GDScript 解析仍由
  `--profile godot` / CI 的 Godot 4.7.1 headless 门禁负责。未修改 Python 规则或接口。

### 2026-07-22 V4.7-C CI 与封版交付

- 新增 Ubuntu 24.04 / macOS 15 双平台 CI，固定 Python 3.12 和 Godot 4.7.1；actions
  使用完整 commit SHA，checkout 不保留写凭据，workflow 仅有 `contents: read`。
- smoke 新增 `--profile core` 与 `--profile godot`，默认仍执行完整检查；子检查统一使用
  启动 smoke 的 Python，Godot 支持 `GODOT_BIN` 并拒绝非 4.7 stable。
- CI 测试阶段强制使用 mock LLM、禁用向量模型下载并使用临时存档目录；不需要 secret，
  不启动 FastAPI、Godot 编辑器或常驻进程。
- 纳管 Godot 4.7 `.gd.uid`，增加 LF 规则，并建立
  [`docs/V4_RELEASE_CHECKLIST.md`](docs/V4_RELEASE_CHECKLIST.md)。该里程碑完成时仅完成源码
  交付准备，当时尚未创建 `v4-origin`、`agent-town-demo-v4.0` 或 `v4.0.0`。

### 2026-07-22 V4.7-B 响应式布局与整局键盘导航

- 新增 `agent_town_responsive_layout.v1`，以物理窗口选择 compact / default / wide，
  并统一驱动 HUD、行动面板、情报抽屉、角色卡列数、设置、复盘和对话框尺寸。
- 新增 `agent_town_focus_navigation.v1`，用 WORLD/PANEL/TEXT_ENTRY/MODAL 明确
  世界移动、普通 UI、文本编辑和模态输入边界；关闭设置、引导、预览、对话或复盘后
  恢复来源焦点，失效时安全回退。
- 发言预览与 NPC 对话补齐鼠标阻断，所有滚动区可用键盘到达并显示高对比焦点框；
  默认字号为 14px，显式字号不低于 12px。
- smoke 静态检查改为验证 `1100×650`、`1280×720`、`1600×900` 三档、动态尺寸、
  modal 生命周期、只读滚动和玩家 UI 移动锁；没有启动 FastAPI 或 Godot。

### 2026-07-21 V4.7-A 首局分阶段引导

- 新增客户端-only `agent_town_onboarding.v1`，七个步骤只在完整 `/state` 后按阶段、
  玩家存活与发言轮次触发，并通过每局 seen 集合避免轮询重复弹出。
- 六身份说明只读取玩家自己的合法身份投影；身份卡、公开证据和私聊分别标记
  “仅你可见”“全场公开但未验真”和“原文不会自动公开但会影响 NPC”。
- 增加 `?` / F1 手动重开、弹窗内循环焦点、方向键、Esc 和自适应弹窗尺寸；本地偏好
  只保存 `schema_version=agent_town_onboarding.v1` 与完成布尔值，不保存任何对局事实。
- Python API、规则状态、事件、存档、重放和 LLM 均未修改；全局响应式/无障碍后来由
  V4.7-B 完成，CI 与封版交付后来由 V4.7-C 完成。

### 2026-07-21 V4.6-B 指纹、LLM 成本与只读配对 A/B

- 新增 digest-only `experiment_fingerprint.v1`，同时封印完整配置和当前执行模式的
  active-only 配置；simulation/batch 升级到 v17，冻结的 v14 玩法摘要不变。
- LLM 观测升级为 v2，兼容 v1；在 adapter 边界记录 exact prompt/config 摘要、
  provider attempt usage 覆盖，并把 adapter retry 与 semantic retry 分开。
- 新增版本化价格表和保守成本汇总。默认模型价格明确未知；未知请求不会被当成零
  成本，完整总成本保持 `null`，已知部分和原始 token 计数独立保留。
- 新增只读 `agent_town_artifact_ab.v1` 比较器，严格验证固定身份配对和 artifact
  完整性，以原始分子/分母比较五项 V4.6-A 指标；固定声明未评估 LLM/Prompt 效果。

### 2026-07-20 V4.6-A NPC 表达质量离线基线

- 新增六个版本化契约和严格报告 schema；终局报告只读取公开 NPC 发言与结构化公开
  依据，隐藏身份互换不改变结果，序列化报告不保存原始发言。
- 单局和批量分别统计逐字/模板/跨角色/近重复、信息原子增量、证据引用和人设代理；
  批量先汇总原始计数再计算加权比率。
- simulation 升级到 v16，CLI 增加 `[SPEECH-QUALITY]`；冻结的 v14 玩法摘要、metrics
  v5、实时规则、FastAPI 与 Godot 均保持不变。

### 2026-07-20 V4.5-A 可解释赛后决策复盘

- 新增三份严格 schema，用稳定 ID 串起保存的决定、跨日公开证据与明确标注的赛后
  真值；进行中状态继续零真值泄漏。
- 发言、放逐票、夜间技能和猎人开枪统一生成只读解释，自动化锁住五类错误、计数、
  决定性、OpenAPI 和状态零变更。
- Godot 新增第三个赛后复盘页；同时只兼容旧存档恰好缺少空幂等台账的一种历史
  形态，其余存档差异继续拒绝。

### 2026-07-20 V4.4-B 承诺生命周期与中立矛盾候选

- 新增 `public_commitment_state.v1`、`public_contradiction_candidate.v1` 和
  `public_evidence_analysis.v1`，仅从 V4.4-A 公开 evidence ID 派生关系。
- 警徽流每个版本独立保留，区分等待、被替代、公开履行、条件失效、无法判断和
  表面冲突；修订、目标不可用与缺少公开后续不会被自动当作阵营问题。
- 四类候选始终为 `needs_review / judgment=none`；Godot 和 NPC 共用分析 ID，
  自动化锁定隐藏信息不变性、只读性、OpenAPI 与 UI 契约。

### 2026-07-20 V4.3-B 幂等命令与重复结算保护

- 新增 `game_command_idempotency.v1` 请求契约和 `game_command_result.v1` 持久
  结果台账，覆盖全部 20 个开局后规则写入口。
- 同 key、同端点、同 payload 返回原响应；跨端点或 payload 冲突返回 409。事件、
  响应和状态在同一次原子写入中提交，重启后可在阶段校验前安全重试。
- Godot 对网络失败保留 key、2xx 后清理；自动化覆盖并发、响应丢失、写盘失败、
  账本篡改、旧客户端兼容和带 key 确定性重放。
- 身份池改为固定角色顺序，消除存档 JSON 对象键排序造成的同 seed 恢复重放漂移；
  默认角色配置的原有顺序和规则结果保持不变。

### 2026-07-20 V4.3-A 原子存档与恢复

- 新增 `game_save.v1` 私有完整快照、恢复配置指纹、规则/快照/事件链多层摘要，
  以及 save、restore、recovery-status 接口。
- 真实 FastAPI lifespan 才启用自动保存；启动恢复按批次 fail closed，跳过终局归档；
  simulation、replay 和直接规则导入保持零落盘。
- 同目录 `0600` 临时文件经 fsync 后原子替换；全部规则写入口共享 pre-commit
  transaction guard，写盘失败保留旧文件并恢复完整内存 checkpoint。
- 独立自检覆盖损坏/漂移拒绝、恢复后续玩、配置热重载保护、ID 冲突和单 worker
  边界；V4.3-B 在此原子提交基础上补齐了外部幂等结果台账。

### 2026-07-19 V3.1-O 公开票型连续追查与平衡修复

- 新增 `good_exile_cross_day.v1`：只读取上一轮公开放逐票、公开出局席位和存活状态；争议票下让普通好人 NPC 收敛到同一反对票小团体，压倒性票不触发。
- 第二夜 NPC 女巫复用同一公开焦点；合理的结构化压毒/毒人建议仍可覆盖。隐藏身份互换不得改变焦点、好人概率或女巫选择。
- `fake_seer_campaign.v2` 将参选区间校准为 `28%–62%`，冻结配对回归随机流；simulation 升级为 v12。
- 固定 100 局好人由 5 胜升至 38 胜，首狼后续投狼为 `28/31`，女巫毒狼率 `71.01%`，好人误投率 `51.80%`。

### 2026-07-19 V3.1-N 跨日放逐链 shadow 诊断 M02-D

- 新增 post-game-only `cross_day_exile_chain.v1`，记录放逐阵营序列、首放狼人条件胜负、下一次放逐阵营和好人 NPC 四类跨轮选票转移；不向实时策略暴露出局真值。
- metrics 升级为 v4、simulation 升级为 v11，CLI 新增 `[EXILE-CHAIN]`；单局/批量严格校验转移、条件胜负和后续放逐守恒。
- 固定 100 seeds 的玩法投影与 V3.1-M 一致；好人 NPC 总体正确票保持率 24.72%、误投纠正率 33.50%。
- 首放狼人 29 局中下一次仅 2 局继续放逐狼人；该样本正确票保持率 18.18%，下一步候选范围收敛到合法公开信息驱动的跨日好人 NPC 放逐判断。

### 2026-07-19 V3.1-M 真假预言家策略与链路诊断 M02-C

- 新增 `fake_seer_campaign.v1`，由既有 NPC tuning 与 seed 决定最强 NPC 狼是否参选，不再每局强制悍跳；新增 `fake_seer_check_mix.v1`，合法混合队友金水、非狼查杀和非狼金水。
- metrics 升级为 v3、simulation 升级为 v10；`seer_claim_balance` 和 `[SEER]` 汇总覆盖真假预言家参选、当选、验人组合、出局及条件胜负。
- 自动化锁住确定性、全局随机隔离、好人精确身份不变性、合法假验人组合和单局/批量守恒；进行中 API 不暴露赛后指标或内部悍跳策略。
- 同口径 100 局中悍跳参选 76、当选 55、假查真预言家 12、真预言家首放 27，好人由 3 胜升至 5 胜；无悍跳 24 局仅 3 胜、首放狼人 29 局仅 2 胜，下一步转向跨日证据与连续放逐链。

### 2026-07-19 V3.1-L 女巫策略与失衡诊断 M02-B

- 新增严格 `witch_directive.v1` 与内部 `witch_strategy_decision.v1`；玩家/NPC 只能公开提出单目标毒人或有理由压毒，NPC 女巫按自己的合法视角独立采信。
- NPC 女巫首夜本人被刀 100% 自救、其他刀口确定性 99% 救；第二夜默认毒自己最怀疑的人，只有采信合理压毒建议才保留毒药。
- metrics 升级为 v2、simulation 升级为 v9，增加终局原因、首放、出局来源与女巫救/毒/压毒/命中汇总；命令行新增 `[BALANCE]`、`[WITCH]` 摘要。
- 100 局毒药命中狼人 42/72，但好人仍仅 3 胜，首放好人 75 局且首放预言家 34 局；下一步继续治理白天真假预言家可信度和放逐链。

### 2026-07-19 V3.1-K 普通好人放逐概率校准 M15-B

- `vote_probability_trace.v2` / `vote_probability_summary.v2` 区分 controlled 与 shadow；只有 `VOTE` 阶段非警长好人 NPC 使用 `good_exile_calibration.v1`，simulation 升级至 v8。
- 受控策略复用原合法评分器的五分量解释，叠加小幅置信 belief 修正和 `+5.0` 温度；严格契约失败时确定性回退，不影响合法投票。
- 自动化覆盖作用域、候选顺序、强私有验人、警长/狼人/竞选隔离、回退、consumer-mode 守恒、M06-A 隐藏互换以及 trace on/off gameplay 一致。
- 100 局受控熵 `9.82%`，好人误投 `63.69%`，好人胜场 `2/100`，狼人目标概率质量 `36.14%`；相对 M15-A 基线均通过“不恶化”门槛。

### 2026-07-19 V3.1-J 投票概率 shadow M15-A

- 新增 `vote_probability_shadow.v1`，在每次 NPC 警长票/放逐票前按合法 belief、公开影响、社交、授权狼队协同和确定性个体噪声生成候选分布；规则仍使用原投票函数。
- 新增 `vote_probability_summary.v1`，按投票类型、投票者阵营和交叉维度汇总熵、top 概率、实际票对照及分量强度；simulation 升级至 v7。
- 自动化覆盖 schema 严格性、概率/分量守恒、候选顺序、同 seed、shadow on/off gameplay digest、M06-A 全隐藏变体不变，以及狼人授权队友变化。
- 100 局记录 3,264 次观察：好人警长票/放逐票个体熵分别为 87.45%/8.56%，好人放逐质量仅 34.76% 落在狼人目标，因此 M15-B 应限定为普通好人放逐票。

### 2026-07-19 V3.1-I 脱敏 LLM 可观测性 M09-A

- 新增 `llm_observation.v1` 本地 JSONL，逐次记录请求成功/回退、尝试与重试、延迟、可选 token 和稳定失败类别；不改变 LLM 返回或规则 fallback。
- 语义校验的恢复与最终回退只记录分类计数，不复制原始输出、拒绝原文、私有上下文或游戏标识；严格字段白名单拒绝额外内容。
- 新增 `llm_observability_summary.v1` 离线命令，支持全局、按 task、按 provider/model 查看成功率、P95 延迟、平均尝试和主要失败原因。
- 该历史 v1 契约已由 2026-07-21 的 V4.6-B/M09-B 兼容升级为 v2，并补齐指纹、
  usage 覆盖和版本化成本；旧 JSONL 仍可读取。
- 自动化用秘密标记验证 API Key、prompt、上下文、回复和 fallback 均不落入观测事件，并覆盖真实语义校验恢复/失败路径、坏行隔离和 CLI 输出。

### 2026-07-19 V3.1-H 授权私有视角矩阵 M06-B

- 新增 `hidden_info_authorization.v1`，以声明式 required/allowed 规则比较预言家验人、女巫刀口和狼队成员变化；未授权 observer/layer 必须保持摘要相同。
- 固定 seed 覆盖 11 名 NPC，三类案例共 158 项；V3.1-L 后预言家全部五层变化，女巫三层变化，三名未换身份的狼人各有四层变化，公开投影和其他 NPC 全部不变。
- 狼队案例排除两个直接换身份的 actor；错误地把预言家私有变化授权给村民时，矩阵能同时发现缺失授权和错误授权。
- 报告不保存变体状态或私有 evidence 正文，输入顺序不影响结果；实时 API、LLM 与规则玩法保持不变。

### 2026-07-19 V3.1-G 隐藏信息不变性矩阵 M06-A

- 新增 `hidden_info_invariance.v1` / `hidden_info_projection.v1`，统一比较公开玩家投影和普通村民 NPC 的 belief、stance、发言上下文、连续性与规则 fallback 计划。
- 六类隐藏变体覆盖身份真值、悍跳内部标记、声明内部来源、未公开夜间结算及组合变化；报告只保留摘要和差异路径，不保存隐藏状态正文。
- 固定 seed 下 3 名普通村民观察者的 96 项检查全部一致，反序输入报告保持确定；公开查验结果变化的负对照能稳定失败。
- 角色特权玩家、神职/狼人 NPC 和警长观察者会被明确拒绝；实时规则和 NPC 玩法不导入测试模块，M06-B 再验证依法可见的私有差异。

### 2026-07-19 V3.1-F 普通白天发言受控消费 M04-B

- 新增 `public_speech_continuity.v1` 与 `public_speech_plan.v3`；规则兜底优先沿用合法 stance，LLM 偏离时必须提供新增公开信号、确定性个体扰动、合法声明或规则强制回应中的一个结构化原因。
- 私有 belief 引用不写入持久化发言计划或表达层；好人目标隐藏身份互换保持 continuity 输入不变，狼人内部 stance 再经过公开发言目标 allowlist 过滤。
- simulation schema 升级到 v6，并新增 `speech_continuity_metrics.v1` 原因守恒统计；同 seed 在不同 `PYTHONHASHSEED` 下逐字节一致，警长票和放逐票仍只做 M04-A shadow 诊断。
- 100 局共统计 2,163 次受控发言，公开发言未解释变化降至 3 次；好人胜率仅 2%、误投率 64.46%，因此本阶段只验收连续性和信息边界，不宣称平衡改善。

### 2026-07-19 V3.1-E 统一立场摘要与连续性 shadow M04-A

- 新增 `stance_summary.v1`：从 actor-scoped belief 和本人 `public_position.v1` 生成信任、主次怀疑、暂定票、验证条件、置信度及证据引用，不包含隐藏角色/阵营，也不解析自由文本。
- 离线对照公开发言、警长票和放逐票，区分一致、有新证据变化、无新证据变化与无法评分；每次决定后的摘要成为新基线，决定本身不会为未来改口提供循环理由。
- simulation schema 升级到 v5，并增加 `--no-stance-trace`；合成反例、同 seed、隐藏身份差分、stance-on/off belief/gameplay 及 v4/v5 规则载荷逐项回归均通过，实时决策保持原样。
- 100 局记录 6,133 次连续性观察；4,516 次可评分观察的一致率为 88.93%，未解释变化率为 4.78%。1,617 次无合法可比目标单列为 `unscored`，不伪装成失败。

### 2026-07-19 V3.1-D 信念衰减与结构化私聊 M03-B

- `belief_state.v2` 对公开声明/立场等软证据应用 `0.75` 的逐日权重衰减；公开票型和警徽动作、预言家/女巫/狼队合法私有知识不衰减，权重变化由 `updated_contributions` 审计。
- 有效私聊保存规则实际应用的目标、怀疑/信任方向和 evidence ID，只进入被私聊 NPC 的 actor-private 视角；歧义、无目标、彩蛋、重复追问和自由文本均不生成或改变证据。
- simulation schema 升级到 v4；新增跨日、私聊隔离、自由文本不变、隐藏身份互换和 shadow 玩法不变测试，实时 NPC 决策仍不读取信念分数。

### 2026-07-19 V3.1-C 合法视角影子信念 M03-A

- 新增 `belief_state.v1`：每名 NPC 对其他席位持有怀疑分、置信度、立场和证据贡献；公开事实与预言家/女巫/狼队合法私有知识分层保存，实时决策暂不读取。
- 无权村民对隐藏身份、悍跳内部标记、声明内部来源、未公布夜间结果和旧状态噪声保持不变；狼人队友知识依法变化。每次分数变化都引用稳定证据 ID，证据台账保持只追加。
- 100 局 shadow on/off 的玩法和 M02 指标完全一致；完整轨迹记录 11,650 条证据与 32,343 次变化。CLI 增加 `--no-belief-trace` 供后续高容量模拟减小报告体积。

### 2026-07-19 V3.1-B NPC 核心指标 M02-A

- 新增严格赛后运行的 `agent_town_metrics.v1`，记录阵营胜率、局长、警长/放逐票熵、好人正确票/误票和假预言家采信代理指标，并按模拟玩家身份、投票者角色和天数聚合。
- 警长票事件增加确定性轮次标记，100 局样本覆盖 17 局 PK；模拟结果 schema 升级到 v2，同 seed 在不同进程哈希种子下仍逐字节一致。
- 首份 100 局报告显示好人误投率 60.95%、放逐票归一化熵 22.62%、假预言家好人警长票支持率 48.29% 且当选率 72%，为 M03/M04/M15 提供诊断基线，不把本批 seed 设为硬阈值。

### 2026-07-19 V3.1-A 可复现批量对局模拟器

- 为规则状态增加不公开的显式随机种子，并把身份洗牌、夜间选择、会议顺序、平票和概率策略迁移到独立、稳定的 seed 派生；线上开局仍使用系统随机种子，公共 API 不暴露该值。
- 新增无 HTTP 自动玩家和批量 CLI，固定关闭 LLM/RAG，可输出逐局完整结果与批量胜负/平均局长汇总；100 局验收全部到达合法终局。
- smoke 新增同 seed 精确重放、终局审计、全局 RNG 隔离、模拟清理、RAG 未初始化和好人视角隐藏身份互换不变性；100 局初始样本暴露狼人 94% 胜率，留给 M02/M15 用指标驱动校准。

### 2026-07-19 V2.0 封版与 V3 交接

- 将当前完整功能快照标记为 V2.0，并准备发布到独立公开仓库 `KEswy/agent-town-demo-v2.0`；原有 `origin` 保持不变。
- 新增独立 `docs/V3_ROADMAP.md`，按优先级、里程碑、工作量、依赖和可验收结果整理 29 项后续改进；V3.1 首先建立可复现模拟、指标、合法视角信念状态和投票校准闭环。
- 根 README 与后端 README 明确列出 V2.0 能力、现有限制和 V3 边界；`COMMANDS.md` 移除开发者本机绝对路径，运行时数据与真实 `.env` 继续由 Git 忽略。
- 自动化自检增加发布版本、仓库链接、路线表和可移植命令文档检查；没有自动启动 FastAPI 后端。

### 2026-07-19 坏坏小恐龙与然然熊猫 v2

- 重绘两张 64×64 透明像素 SVG：坏坏使用嫩绿身体、黄色肚皮、浅蓝背鳍/围巾和明显尾巴构成小恐龙轮廓；然然强化黑耳、黑眼圈、黑四肢，并保留黄色披肩和浅蓝邮差包的熊猫邮差形象。
- 两名常驻居民的人物身份、性格、口头禅、知识、场景自我介绍和离线规则回复同步新造型；DeepSeek 上下文会收到“小恐龙居民 / 熊猫居民”身份，但仍限制在自然聊天，不参与狼人杀规则。
- 自动化自检新增居民物种、配色、64×64 SVG 规格、场景介绍和聊天上下文一致性；未启动 FastAPI 后端。

### 2026-07-17 警下分票与收到验人回应

- 警长候选评分改为以实际警上发言质量为主，玩家和 NPC 使用同一套公开标准；削弱固定性格先验，移除同信任下由声明顺序造成的集体偏向，并加入可复现的听者个体解读，让相近候选人的好人票自然分开。
- 收到金水现在只产生有限且因人而异的警长票影响，不再等价于认定真预言家；收到查杀会形成直接冲突。两种验人都会进入当天结构化决策，NPC 必须回应声明者，若警长票投给别人也会在正文中说明。
- 新增不含内部 `source`、真假和隐藏身份的 `seer_check_claim` 安全信号，以及隐藏身份互换、自然分票、金水非锁票、信号来源不变性、金水/查杀强制回应的 smoke 回归；README 与后端说明同步，本次没有自动启动后端。

### 2026-07-17 结构化契约修复与关键公开信息

- 修正 `public_speech_plan.v2` 的提示契约：DeepSeek 现在收到明确的扁平根级 JSON 示例和纠错说明；后端安全兼容旧 `fields` 包装，同时继续严格拒绝缺失字段、未知字段和越权 ID。
- 左上角身份卡新增可折叠的关键公开信息区，按天汇总预言家/女巫/守卫/猎人的公开声明，并单独标记猎人开枪等规则已确认动作；首条信息出现时自动展开。
- 新增不含 `source`、真假标记、真实身份、阵营或真实夜间行动的 `public_intel` API 投影，并用“内部声明来源变化时公开结果不变”的自动化用例锁住信息边界。
- README、后端说明和 smoke 自检已同步；本次没有自动启动后端。

### 2026-07-17 合法视角校验与好人误判

- 公开阵营判断从“隐藏答案校验”改为“表达权限校验”：“某人是狼/好人”和第一人称好人声明可以作为可错观点；条件推理、双狼猜测、引用、否定、反问及普通队友称呼不会再被“狼队友”关键词误杀，只有明确的第一人称狼身份或狼队关系自曝继续拒绝。新审计记录版本升级为 `semantic-v3`。
- 进行中校验记录是否脱敏只由失败类型决定，不再检查原文提到的角色是否恰好是真狼，避免校验结果反向成为身份旁路。
- 普通好人的警长候选与放逐候选评分改为公开说服力、公开预言家声明完整性、关系、怀疑和个体易受骗程度；相同公开状态交换候选人的隐藏身份后评分保持不变，并允许假预言家当选、好人分票和真预言家被误投。
- 自动化 smoke 增加上述正反语义样本、隐藏身份互换不变性、假预言家警长票与假查杀真预言家的回归测试；本次没有自动启动后端。

### 2026-07-17 AI NPC 决策计划 v2 与智能微调

- 普通非警长白天发言升级为 `public_speech_plan.v2` 决策层与受限表达层：计划明确主次目标、立场、信号解读、追问、验证点、暂定票和战术；Python 渲染事实正文，LLM 只提供不含游戏事实的角色化语气前缀。
- 当天计划接入放逐评分；好人可以受悍跳影响，也可能在接近候选人间投错，狼人新增误导、框人、反推、深水、救援、拉开距离和卖队友等白名单战术，所有身份与行动事实仍由 Python 决定。
- “狼查杀狼”增加跨警长票、发言、放逐票与警徽的叙事一致性约束；新增 `npc_tuning.v1` 四层参数覆盖与新对局快照，并同步自动化自检和微调说明。

### 2026-07-17 坏坏与然然常驻居民 v1

- 新增坏坏和然然两名非参赛常驻居民与原创 64×64 像素造型，放在会议广场东西入口；她们不占十二人座位，也不会被规则世界同步为出局、警长或当前发言人。
- 两人的普通 `/chat` 在全局 DeepSeek 可用时整理人物性格、专属知识、关系阶段和最近 8 轮长期记忆生成回复；其他小镇 NPC 的原有普通聊天保持不变。
- DeepSeek 请求移出全局记忆锁；禁用、未配置、网络/JSON 异常或轻量格式安全校验失败时，使用各自的自然规则回复并继续保存记忆。
- Godot 对话框显示 LLM provider 或规则回退原因；README、后端说明、111 条 RAG 知识和自动化 smoke 已同步，开发过程没有自动启动后端。

### 2026-07-17 小镇背景与规则昼夜 v1

- 新增独立 `TownBackground` 场景与矢量绘制脚本，使用地形纹理、双向道路、圆形会议广场、池塘、建筑、摊位、植被、花坛、围栏和广场家具替换原有廉价的三块纯色背景。
- 昼夜严格读取 Python 规则引擎返回的阶段：只有 `NIGHT` 渐变为蓝色夜景，其他阶段及未开局状态均为白天；视觉层不参与任何规则结算。
- 夜景增加暖色灯晕、萤火和池塘反光；UI 保持在独立 CanvasLayer，NPC 名字增加浅色描边，避免背景变暗影响文字可读性。
- README、背景结构、阶段映射、Tween 过渡、旧背景移除和 Godot headless 加载均已加入自动化 smoke 回归；没有修改或启动后端服务。

### 2026-07-16 狼人杀 UI 分层 v1

- 将原有单一大控制面板拆分为顶部阶段 HUD、左上身份卡、右侧当前行动面板、独立情报抽屉和开局设置窗口，保留原规则请求与阶段操作路径。
- 采用黄色与浅蓝色界面色调；当前行动面板只呈现阶段相关控件，情报抽屉用三个分页分别承载角色卡、公开记录和玩家行动记录。
- 浅色 UI 使用独立黑字主题，覆盖普通、悬停、按下、禁用、占位符和只读状态，并为按钮、输入框、下拉框与分页补充浅色背景。
- 当前行动与情报抽屉互斥显示，并同步处理对话框、复盘、开局设置、键盘焦点和摄像机安全区域，避免多层 UI 重叠或抢占移动输入。
- 自动化自检新增新节点层级、三列角色卡、响应式尺寸、模态状态和焦点范围回归；本里程碑没有启动或修改后端服务的运行方式。

### 2026-07-16 LLM 表达校验误判收敛

- 根据真实 `llm_validation_failures.jsonl` 样本收窄硬拒绝范围：选中目标、声明和动作信号改为必须保留的事实下限，公开座位引用不再因“计划外人物”单独失败，规则状态中已存在但本轮未选中的公开动作也可以被准确复述。
- 输出校验开启时空泛过麦仍会被拒绝，但完整保留身份/查验声明的短发言不会仅因结尾出现“先看”；低信息量信号本身不能替“没信息，过”免责。
- 补充“拿的是某身份”、查杀/金水省略句、逗号后的预言家主语延续、并列转述和公开声明复述；同时修复“验了目标，并上警”把上警动作错绑给查验目标的问题。
- 未登记身份、篡改查验、技能行动、狼队泄露和规则状态中不存在的公开动作继续硬拒绝。校验日志新增 UTC 时间与 `semantic-v2` 版本标记，自动化测试覆盖上述正反例。

### 2026-07-16 AI NPC 第二阶段：公开动作信号与有效发言

- 在 `npc_decision_context.v1` 中新增公开安全的 `decision_signals`，由 Python 从警长竞选、警徽、历史票型、已公布出局和低信息量发言构建；不同身份看到相同公开信号，夜间来源与待公布结果不会进入信号。
- `public_speech.v1` 新增最多两个 `signal_ids`。普通观察、施压和辩护必须有合法目标，并从公开信号、公开证据或合法声明中选择依据；未知、重复、超量和与目标无关的信号都会被拒绝。
- 表达层只接收已选信号并必须准确保留动作事实；校验器会规范化动作类型、行动者、目标和已公开出局来源，拒绝调换投票方向、篡改来源或增加规则状态中不存在的动作。允许角色对动机作出可能错误的推断，但不能把“退水”改成“继续竞选”等相反事实。
- 新增空泛过麦保护：“没信息，过”等短句会进入表达纠错；规则回退也会引用具体信号，给出目标、立场和后续发言/票型验证点。
- 低信息量只作为保守评价，不直接证明身份或额外改变怀疑值。自动化自检覆盖公开投影、隐藏来源隔离、信号 allowlist、表达隔离、重试、规则回退与状态更新。

### 2026-07-16 AI NPC 第二阶段：结构化公开发言决策 v1

- 新增角色隔离的 `npc_decision_context.v1`：每次普通白天发言整理身份、合法知识、公开日志、私有记忆、性格、阶段、合法目标、声明包和证据可见性。
- 新增 `public_speech.v1` 严格策略输出；第一段只能选择规则生成的意图、目标、声明包和公开证据，第二段只拿公开投影生成角色化话术，私有上下文不会进入表达调用。
- 后端通过 schema、allowlist、结构化意图/目标、人物/阵营与既有事实校验后才提交；怀疑值更新直接消费结构化策略，不解析 LLM 自由文本来决定规则状态。
- 该阶段对非法结构化输出固定最多纠正五轮，随后使用原有规则方案；V4.8-A 起可关闭输出校验：Python 直接采用合法规则计划，只请求 1 份最终文本并进行 0 次语义校验。进行中审计隐藏开启校验时的失败原文，服务端日志和赛后复盘保留该审计。警上、警长、夜间、投票和私聊策略未在本里程碑扩展。
- README、后端说明与自动化 smoke 自检同步覆盖 JSON 适配、两段上下文隔离、非法选项、私密信息、公开人物引用、结构化状态更新和规则回退。
- 表达校验移除固定意图词表硬门槛，并区分直接阵营断言与反问、否定、假设、转述；自然的 `pressure` / `defend` 同义表达不再耗尽当时固定的五轮重试。V4.8-A 输出校验开启时真实自曝和隐藏狼队信息仍会被拒绝，关闭时则作为未经校验原文直接显示。

### 2026-07-16 大面板与关键词彩蛋

- 右侧控制面板扩大为 `520px` 宽和窗口高度的 `82%`，同步扩大玩家安全区域，继续保留内部滚动。
- 11 名 NPC 各新增一个自由活动关键词彩蛋，忽略大小写、空格和常见标点，重复触发使用简短回应。
- “林殊”彩蛋会让梅长苏私下透露本局真实身份，并只在玩家行动记录中保存一次；所有彩蛋均不消耗有效追问。
- LLM 校验器新增真实自曝身份授权契约，只允许指定彩蛋透露当前 NPC 自身的正确身份。
- 自动化自检覆盖全部彩蛋配置、梅长苏首次与重复触发、追问次数、私密记录和身份校验边界。

### 2026-07-16 退水双按钮与警长面板稳定性

- 候选玩家在退水阶段直接使用“继续竞选”和“退水”两个独立按钮，不再通过含糊的“完成退水”按钮提交。
- 未上警玩家无需代替 NPC 完成退水；最后一名警上角色发言结束后，后端自动结算 NPC 选择并推进阶段。
- 警长阶段切换后保持操作区域可见，警长下拉框和按钮使用固定字号与高度，避免刷新后出现视觉尺寸变化。
- 自动化自检覆盖玩家继续竞选、非候选玩家自动结算和 Godot 双按钮布局。

### 2026-07-15 控制面板紧凑化

- 狼人杀面板统一使用更紧凑的默认字号，身份和狼队友仍保留清晰的视觉层级。
- 玩家行动记录框高度由 132 缩减为 84，去掉记录之间的额外空行，并保留框内滚动查看完整内容。
- 此版本曾让阶段切换后统一回到顶部；2026-07-16 已进一步调整为警长流程保持操作区域可见。
- 自动化自检加入面板字号、行动记录高度与阶段滚动复位回归。

### 2026-07-15 验人归属、面板焦点与玩家行动记录

- LLM 校验改为记录声明者、查验目标和结果，修复“5号给8号金水”被误判成“5号是好人”；“我验了某人”直接视为预言家起跳。
- 控制面板按钮、下拉菜单和开关不再保留键盘焦点，提交和收起面板后立即及延迟清理焦点，避免 WASD 操作白色选中框。
- 面板身份区下方新增只读滚动行动记录，累计夜间技能结果、警上操作、完整公开发言、私聊和投票信息。
- 自动化自检加入真实失败原文、玩家行动历史和 Godot 焦点策略回归。

### 2026-07-15 首夜延迟公布、五轮 LLM 校验与警上标记

- 第一夜出局改为警长竞选结束后统一公布，女巫解药、守卫、毒药和狼刀结果不会在警上阶段提前泄露。
- 全部出局增加合法来源审计，修复退水角色重新获得警长票的问题，并覆盖警长猎人先开枪再移交警徽的顺序。
- DeepSeek 内容校验在该阶段扩展为固定最多五轮，保存原始回答与失败原因；V4.8-A 后可在开局关闭输出校验，改为生成 1 次、校验 0 次并直出原文。当时调试构建曾允许游戏内查看完整记录，2026-07-16 的结构化决策更新已改为进行中脱敏、赛后查看开启校验时的失败原文。
- 玩家和 NPC 增加彩色/灰色警察徽章与 PK 标记，控制面板增加醒目的候选人与发言顺序概览。
- 所有游戏文本提交统一清空输入、释放焦点，并且只等待提交瞬间仍按着的移动键松开；修复输入残留自动移动，也修复回车提交后新按下的 WASD 被误锁。
- README、后端说明、命令文档和自动化冒烟测试已同步。

### 2026-07-15 自然警长座次、身份测试与精简面板

- 前夜有人出局时，警长改为按固定座次自然发言；无人出局时仍自然位于警左/警右顺序末尾。
- 新增警长暂时归票，后续 NPC 会参考该公开意见；全员发言结束后允许调整最终归票。
- 开始菜单新增随机或指定玩家身份，指定女巫时保持原十二人身份池，并完整提供刀口、解药和毒药操作。
- 面板顶部新增醒目身份和狼人队友信息，身份技能与阶段操作改为按需显示。
- 狼人杀面板和复盘统一使用 Noto Sans SC，并将“杀、女巫、狼队友”等加入自动字形检查。
- README、后端文档、107 条 RAG 知识和自动化冒烟测试已同步。

### 2026-07-15 警长竞选、像素角色与同步投票

- 新增第一天警上报名、候选人按序发言、独立退水、警下同时投票和一次平票 PK。
- NPC 真预言家必须起跳报真实验人；玩家保留自由发言，狼队支持让跳、退水、少量双狼起跳和受限的狼查杀狼。
- 新增警长发言侧、归票锁定、1.5 票和猎人技能后的警徽移交。
- 白天放逐改为玩家一次提交后生成全部票，先显示简明票型，再显示详细理由和 RAG 依据。
- 小镇座次收紧，并为玩家和 11 名 NPC 增加原创像素形象、对话头像与警徽标记。
- README、后端文档、107 条 RAG 知识和自动化冒烟测试已同步。

### 2026-07-14 控场、身份起跳与角色化表达

- 新增狼人控场胜利条件，并保证可开枪猎人先完成技能结算。
- 新增玩家公开声明解析、真预言家起跳、NPC 狼人悍跳和跨轮验人声明记录。
- 新增女巫、守卫和猎人的主动身份与行动信息公开，声明会参与后续怀疑和投票判断。
- 为 11 名 NPC 增加角色化说话风格、低频口头禅和彩蛋，并为 LLM 声明文本增加关键内容校验。
- 控制面板、结束复盘、RAG 知识库和自动化冒烟测试已同步。

### 2026-07-14 十二人制预女猎守

- 小镇扩建为 11 名固定 NPC 环绕会议广场，并为当前发言者增加场景箭头。
- 身份扩展为四狼、四民、预言家、女巫、猎人和守卫，胜负改为屠边。
- 完成狼队互认、玩家狼人最终刀口、NPC 掩护与策略性切割。
- 完成女巫双药、首夜自救、同守同救失效，以及猎人开枪和中毒禁枪。
- 控制面板、结束复盘、知识库、NPC 人设和自动化冒烟测试已同步到十二人版本。
