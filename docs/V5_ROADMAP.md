# Agent Town Demo V5 改进与开发路线表

## V5 主题

V5 的主题是：

> 让每个 NPC 拥有独立、可审计、受公开事实约束的推理链，并用一个轻量本地策略模型替换“候选行动评分”层。

这不是从零重写狼人杀规则，也不是训练语言表达模型。V5 保留 V4 的规则引擎、事件链、
存档、重放、公开证据、LLM 校验和 Godot UI；只把每个 NPC 的
`观察 → 假设 → 信念 → 候选评分` 做成 actor-scoped 的可替换层。

V5 源码从 V4 封版仓库
[`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0) 的
`v4.0.0` 创建；V4 标签、`v4-origin/main` 和历史 remote 均保持只读。

## 永久边界

- Python 唯一决定身份、合法知识、候选行动、权限检查、确定性采样、事件链、出局和胜负。
- 好人观察只能包含自己的身份/合法技能信息以及公开事实；好人不能读取其他人的隐藏
  `role/camp`，但可以正确推理、被骗、误判和投错。
- 狼人可以知道自己的队友和非狼人阵营；预言家只能知道自己的合法查验结果。
- NPC 推理状态不会创建新行动，只能改变已有合法候选的软评分。
- 本地模型输出非有限、过期、摘要不一致、产物缺失或推理异常时，回退到 Python 规则评分。
- DeepSeek 只负责合法上下文内的 NPC 表达/可选语义校验，不直接决定身份、行动、票、
  警徽、出局或胜负。
- 未校验的 LLM 原文可以影响玩家主观判断，但不能进入权威声明、立场、怀疑值、技能、
  投票或结算。
- 投票与决策只读结构化数据（计划、声明、立场卡、公开证据）；发言原文是纯表现层，
  任何文风改动不得改变规则结果。
- 不自动启动 FastAPI/Godot；V5 训练与仿真命令均为离线进程。

## 关键推理例子：双预言家“金水”与退水时序

本项目把警上退水窗口关闭时每个仍在候选列表中的人记录为
`continue_campaign`。因此，若 A、B 都跳预言家，B 给 A 发金水，且 A、B 都没有退水，
每个 NPC 的公开观察都会同时得到：

1. A 与 B 都是持续的预言家候选；
2. B 公开声称查验 A 为好人；
3. 按本局约定，普通好人可以临时跳预言家，但出现持续对跳后必须退水；
4. 唯一真预言家必须在持续对跳中保留其候选资格。

B 为真预言家的假设因此与“B 给持续对跳者发金水”的公开时序冲突；A 是唯一仍一致的
预言家候选。推理层输出 `seer_golded_persistent_counterclaim`、
`sole_consistent_seer_claimant` 等信号，公开证据层只显示
“待核对的矛盾候选”，绝不把它直接当成身份真值。

## 里程碑和优先级

| ID | 优先级 | 状态 | 目标 |
| --- | --- | --- | --- |
| V5.1-A | P0 | 已完成 | 在退水窗口关闭时记录所有活动候选的持续竞选事实，并建立 actor-scoped 推理 observation/belief/signal 契约 |
| V5.1-B | P0 | 已完成 | 按 NPC 身份投影合法知识，禁止好人侧隐藏身份泄漏；将推理调整接入警长候选和放逐评分 |
| V5.1-C | P0 | 已完成 | 将双预言家金水时序冲突加入公共证据候选和 NPC 发言 decision signal |
| V5.2-A | P0 | 已完成 | 从规则仿真捕获固定候选特征、规则 soft target 和 reasoning digest，生成 JSONL 训练集 |
| V5.2-B | P0 | 已完成 | 用 NumPy 轻量线性模型训练好人/狼人两份候选评分 artifact，manifest + SHA-256 + feature schema 封印 |
| V5.2-C | P0 | 已完成 | `rule / shadow / local` 三种模式；local 仅替换评分层，保留规则采样与失败回退 |
| V5.3-A | P0 | 已完成 | 将 NPC 策略模式和 artifact 摘要写入 `game_created`，支持旧存档默认 rule 与事件重放 |
| V5.3-B | P1 | 已完成 | 仿真 CLI、训练数据 CLI、离线验证指标和 smoke 针对性断言 |
| V5.4-A | P1 | 已完成 | 建立完整合法世界边际与 top-world 展示层、修复单 claimant/跨日时序边界；夜间目标 shadow 只计算、local 才消费 belief 且受 `AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE` 置信度门禁约束，rule/shadow 保留既有实际行动基线 |
| V5.4-B | P1 | 已完成第一阶段 | 增加严格 JSONL validator、观察/人工标签分离合并、整局分组切分、MLP V2 artifact 和离线 reasoning scenario runner |
| V5.4-C | P1 | 已完成 | 固化 6 条高价值公开逻辑场景及生成器，覆盖对跳金水、单 claimant、退水、跨日证据、已知角色冲突和改验结果 |
| V5.4-D | P1 | 已完成 | 280 teacher + 99 人工审阅标签（tonystark 确认）重训为 MLP V2，并增加熵/扰动护栏与夜间信念置信度门禁；消融确认放逐 MLP 在 `blend=0.10` 下尚未改变采样票，指标变化来自夜间信念消费；30 局 seed `20260601–20260630` 胜率持平、其余四项核心指标改善，重放 `30/30`、零 fallback，金丝雀复验通过 |
| V5.4-E | P1 | 已完成第一阶段 | 增加 `wolf_sheriff_campaign.v1`，支持单狼悍跳、双狼辅助站边和双狼公开拉开距离；搭档发言后退水 |
| V5.5-A | P2 | 已完成（女巫毒保留信念路径） | 警长投票、警长归票与夜技面（狼刀/守卫/查验/猎人）均已接入独立 task+role artifact：`npc_sheriff_vote_features.v1`（855 条）、`npc_sheriff_nomination_features.v1`（734 条）、`npc_night_target_features.v1`（1323 条，27 维）；女巫毒药沿用 V5.4-A 信念路径；30 局金丝雀零回归，重放 `30/30`、零 fallback；保持 legal mask、shadow 门禁和 replay 不变 |
| V5.5-B | P2 | 待开始 | 本地策略模型的版本升级、灰度 shadow、A/B 报告和可恢复 artifact 注册 |
| V5.5-C | P2 | 已完成 | 四合一体验层：会议快进（`POST /api/day/npc-speeches-batch` 批量发言、快进按钮）、多语言框架（`L10n` autoload + 设置切换中/英、核心 UI 英文化）、白痴变体局（`variant=idiot`，1 名白痴替换 1 名村民，翻牌免死一次且翻牌后不能投票）、实时观战（`/spectate` 页面 + `/api/spectate/*` 公开快照，不泄漏隐藏身份/私密信息）；白痴局 30 局金丝雀 50:50，经典 6-seed 夹具零回归，local 模式兼容 |
| V5.5-D | P2 | 已完成 | 狼战术库扩充与 NPC 个性化：新增自刀银水（`wolf_self_kill.v1`，团队确定性决策，女巫救则成银水、不救则狼出局）与假跳神职（`wolf_fake_god_claim.v1`，狼在压力/后期可跳守卫/女巫/猎人）；怀疑累积、公开声明影响与投票评分接入 aggressiveness/cautiousness 个性（C罗激进、梅西保守等）；设置弹窗新增 NPC 策略模式（规则/影子/本地）切换并持久化，对局信息栏显示当前模式；30 局规则金丝雀好人 43.3%（基线 46.7%），local 53.3%，6-seed 夹具随意图更新 |
| V5.5-E | P2 | 已完成 | 成就解锁反馈与游戏内观战：新解锁成就在赛后弹出横幅动画（滑入+缩放+淡出，排队逐条展示）并播放合成上行琶音音效，成就已解锁集合持久化到 `agent_town_achievements.cfg`；菜单新增“观战”，游戏内直接轮询 `/api/spectate/*` 渲染角色/阶段/公开时间线，不跳浏览器（浏览器 `/spectate` 页面保留） |
| V6.0-A | P2 | 第一阶段完成 | 德州扑克馆：纯 Python 无限注 Hold'em 引擎（牌力评估、翻前翻后转河、全下、边池、弃牌者筹码留在底池、平分；含同花/顺子/轮子边界修正）与按 NPC 个性打牌的 AI；REST API（开桌/状态/行动自动推进 NPC/下一手）；Godot 牌桌弹层（手牌/公共牌/筹码/弃牌过牌跟注加注全下滑杆/下一手）；小镇右上角“德州扑克馆”可交互入口（走近按 E 进馆） |
| V6.0-B | P2 | 已完成 | 世界氛围与扑克深化：场馆系统（球场/至圣所/点心屋/心情邮局/练歌台等 12 处场地，`town_background._draw` 绘制 + 标签）、NPC 漫游 AI（idle→walk_to→stay 状态机，速度/停留按性格，主场 58% 概率，世界边界内）；对局互斥（狼人杀进行中 NPC 锁定会议环位，扑克开桌时 5 名对局 NPC 移到扑克馆门口并显示“牌局中”）；扑克战绩接入本地统计（手数/净输赢/最大单手/最佳牌型/各牌型胜场/横扫次数/最近 20 手）与 10 个新成就（复用弹窗动画）；AI 翻牌前位置感知（早位收紧/后位偷池/盲注防守）与两轮加注读牌（re-raise 后弱牌弃牌率上升、激进加注者收紧、强牌 4-bet 反制保守者）；2000 手仿真无卡死、筹码守恒、决策分布合理，玩家输光自动收桌、赢光判定横扫 |

## 当前实现契约

| 文件/契约 | 用途 |
| --- | --- |
| `backend/app/npc_reasoning.py` | 严格 observation、belief、hypothesis、signal、plan 模型 |
| `backend/app/npc_policy.py` | 候选特征、策略分数、artifact 完整性、trace ContextVar |
| `backend/app/npc_policy_data.py` | V1/V2 JSONL、标签 join、摘要/候选/概率严格校验 |
| `backend/app/main.py` | 合法知识投影、推理状态缓存、规则评分包装、模式封印、时序事实和夜间信念置信度门禁 |
| `backend/app/simulation.py` | 离线 trace 捕获、模式指纹、重放兼容和批量报告 |
| `backend/training/generate_policy_dataset.py` | 规则教师 JSONL 数据生成 |
| `backend/training/train_policy.py` | NumPy 线性/小型 MLP 候选评分器训练与 manifest 生成 |
| `backend/training/validate_policy_dataset.py` | 外部 JSONL 严格验证和规范化 |
| `backend/training/merge_policy_labels.py` | 按 observation digest 合并人工/专家标签 |
| `backend/training/evaluate_policy.py` | 离线交叉熵、Top-1、候选覆盖和有限输出评估 |
| `backend/training/reasoning_scenarios.py` | 版本化推理场景离线评测 |
| `backend/training/generate_reasoning_scenarios.py` | 生成高价值公开逻辑场景 JSONL |
| `backend/training/examples/reasoning_scenarios.v1.jsonl` | 当前 6 条推理场景基线 |
| `backend/training/generate_policy_review_queue.py` | 从逻辑冲突候选生成不含隐藏真值的人工审阅队列 |
| `backend/training/convert_policy_review_queue.py` | 将已填写队列转换为严格策略标签 |
| `backend/training/consensus_policy_labels.py` | 按审阅者独立来源生成共识标签并隔离分歧 |
| `backend/training/fill_policy_review_queue.py` | 生成明确标注需人工复核的启发式 bootstrap 标签 |
| `backend/training/compare_teacher_labels.py` | 比较审阅标签与规则 soft teacher 的差异 |
| `backend/training/review_dashboard.py` | 生成离线极简审阅向导：逐条 teacher/审计对照、一键采纳或手填目标号、进度本地保存并导出 JSONL |
| `backend/training/audit_policy_review_queue.py` | 生成 teacher-anchored 聪明好人 v2；聪明狼人逐项保留 v1 rubric |
| `backend/training/calibrate_policy_temperature.py` | 离线扫描候选概率温度，不直接修改运行时 |
| `backend/training/extract_policy_disagreements.py` | 从 shadow 轨迹提取规则/模型分歧样本 |
| `backend/training/analyze_policy_disagreements.py` | 按聪明阵营不变量分类分歧并隔离异常 |
| `backend/policy_artifacts/*_policy_v1` | 当前可加载的好人/狼人 32 隐层 MLP（`npc_policy_artifact.v2`） |

V5 当前仿真输出为 `agent_town_simulation.v18` /
`agent_town_simulation_batch.v18`，游戏摘要使用
`gameplay_digest_projection_version=agent_town_simulation.v15`；V4 的 v17/v14 记录仍
按历史 artifact 口径保留，不被移动或覆盖。

候选评分模型的输入是 25 个固定特征，包含公开怀疑/压力、actor 的推理调优、推理信号、
合法已知阵营和当前日程；模型不能添加候选、改变候选顺序、跳过权限检查或直接提交票。

## 数据和训练协议

1. 规则模式生成 teacher distribution；不调用 HTTP、DeepSeek、RAG 或 Godot。
2. validator 将 V1 记录规范化为 V2；人工/专家标签通过 `observation_digest` 单独
   合并，避免用户直接编辑特征或误传隐藏身份。
3. 训练按 faction 分开，并按整局 `episode_id/game_id` 分组划分训练/验证，避免同一局
   的相邻决策泄漏到两侧。
4. 目标可以是规则 soft distribution、人工偏好或 self-play 标签；不把某一次确定性
   采样结果自动当成唯一真标签。
5. 训练只使用 actor-scoped 候选特征和离线标签；真实角色/终局结果不能进入好人侧
   runtime observation。
6. manifest 固定模型 ID、feature/schema 版本、数据摘要、模型 SHA-256、训练/验证样本
   数和验证指标。
7. 生产开局从环境读取 `AGENT_TOWN_NPC_POLICY_MODE`；缺省为 `local`（2026-08-04
   起）。`shadow` 计算
   本地分数但仍按规则行动，`local` 才接管候选概率。
8. 任意产物校验失败都回到规则分布；不能静默使用未封印或过期模型。
9. 聪明好人审计默认逐项等于 rule teacher；只有硬公开逻辑冲突才使用有界纠偏，
   保护唯一一致预言家并减少无谓分票。聪明狼人标签保持
   `codex_smart_audit_v1` 不变。
10. 狼人警上阵容可以包含假预言家和一名搭档；搭档只能基于当时公开声明发言，
    不新增角色 claim，发言后退水。隐藏策略名不进入公开状态。
11. 正式训练集保留 280 条 teacher 与 99 条审计标签；`npc_policy_entropy_guard.v1`
    让普通好人逐项等于 teacher，只放行方向正确的硬逻辑纠偏，并封顶熵与总变差。
12. local 夜间目标（狼刀、守卫、查验、女巫毒、猎人）消费 actor-scoped belief 前
    必须通过 `AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE` 置信度门禁（默认 `0.80`），
    低置信场景与 rule 完全一致；`shadow` 只计算不消费。

金丝雀分两档：seed `20260727–20260736` 的 10 局与 seed `20260601–20260630` 的
扩展 30 局，均使用默认 `temperature=1.0`、请求 `blend=1.0`（狼侧护栏封顶有效混合
约 `0.5`）、`AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE=0.80`。消融确认 `blend≤0.25`
时放逐 MLP 尚未改变采样票；放宽狼侧熵/总变差护栏并提高到 `0.5` 后模型开始真正
参与投票。温度校准确认 softmax 首选与温度无关，`1.0` 时模型与 teacher 的 KL
最低。10 局金丝雀：胜场 `2→3`、误投 `62.6%→58.3%`、放逐熵 `25.1%→26.4%`、
跨日保持 `77.4%→87.5%`。扩展 30 局胜率持平、其余四项核心指标改善：胜场 `46.7%→46.7%`（持平）、
误投 `47.0%→45.4%`、投狼概率质量 `54.4%→56.8%`、放逐熵 `30.3%→28.8%`、跨日
保持 `69.5%→76.9%`；重放 `30/30`、零 fallback，金丝雀门槛
通过。人工标签清洗（tonystark 确认 99 条）与模型重训已于 2026-08-04 完成，
默认模式已切换为 `local`；同日平衡微调（6 名偏好人 NPC `decision_variance`
+0.20）后好人胜率约 43%（更接近五五开）；`rule` 仍可通过环境变量或开局选项
显式选择。规则发言模板已加入确定性变体，模板重复率 `25.2%→13.1%`、跨角色近
重复 `5.7%→2.2%`。

### V5.5-A 实施计划（警长投票面已完成，归票/夜技待做）

把 `rule/shadow/local` 策略面从放逐投票扩展到警长投票、警长归票与全部夜技，每
个任务维护独立 task+role 策略产物：

1. ✅ 契约：新增 `npc_sheriff_vote_features.v1`（26 维 actor-scoped 特征），
   建立 `build_sheriff_vote_policy_observation` 与 task 感知的记录/产物校验；
   `npc_night_target_features.v1` 待做。
2. ✅ 数据：`generate_policy_dataset.py --task sheriff_vote` 产出 130 局 855 条
   rule teacher；按 faction 分组切分。
3. ✅ 训练：`train_policy.py --task sheriff_vote` 输出
   `backend/policy_artifacts/sheriff_vote/` 好人/狼人产物；manifest 记录任务、
   特征 schema、数据摘要与 SHA-256。
4. ✅ 运行时：`main.py` 在 local 模式用 sheriff_vote artifact 替换警长票评分层，
   复用熵/总变差护栏与失败回退；`shadow` 只记录不消费；开局封印校验覆盖全部任务。
5. ✅ 金丝雀：30 局协议下六项核心指标与基线完全一致（零回归），重放 `30/30`、
   零 fallback；后续归票与夜技面复用同一管线。

## 验收门槛

- `py_compile` 覆盖新增推理、策略和训练脚本。
- 双预言家金水/双方继续竞选的定向 smoke 必须发现冲突、选出唯一一致候选，并确认
  好人 observation 不含其他角色隐藏身份。
- `rule`、`shadow`、`local` 单局都必须到达 `GAME_OVER`；local 事件链 replay 必须通过。
- 至少分别有好人和狼人 artifact；模型摘要、特征顺序和 `.npz` 内容必须严格校验。
- 外部数据 validator 必须拒绝未知字段、过期摘要、NaN/Inf、重复候选、非法概率和
  冲突标签；整数/浮点等价输入的摘要必须稳定。隐藏身份语义泄漏无法仅凭数值格式
  自动证明，因此生产喂数必须来自受信 observation 生成器或另行人工审计。
- 单 claimant、跨日旧证据、双预言家金水/双继续三类 reasoning scenario 必须通过；
  possible-world 无解时不能把 hidden world 伪装成确定答案。
- `npc_policy_artifact.v1` 线性产物和 `npc_policy_artifact.v2` MLP 产物都必须能安全
  加载；候选顺序、有限输出、shadow/local 重放和失败回退必须通过。
- local 金丝雀必须同时在 10 局 seed `20260727–20260736` 与扩展 30 局
  seed `20260601–20260630` 上比较 rule 对照，且放逐熵、跨日正确票保持、误投率、
  投狼概率质量、好人胜场五项全部不恶化；重放 `30/30`、零 fallback。
- `AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE` 必须限定在 `0.0–1.0`，smoke 必须覆盖
  置信/低置信两类信念的门禁行为。
- 修改 V5 功能时同步更新根 README、`backend/README.md`、`COMMANDS.md`、本路线表和
  `scripts/smoke_check.py`。
- V5 不移动、删除或 force-push V4 的 `v4.0.0`、`v4-origin/main` 或历史 remote。
