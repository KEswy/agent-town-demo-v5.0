# Backend

Agent Town Demo 的 Python FastAPI 后端，负责小镇 NPC 对话、知识检索、长期记忆，以及狼人杀规则和对局内 NPC 状态。

## V2.0 后端封版与 V3 交接

本目录是 [`Agent Town Demo V2.0`](https://github.com/KEswy/agent-town-demo-v2.0) 的后端快照。V2.0 的稳定边界是：Python 规则引擎唯一决定身份、合法知识、技能、警徽、票型结算、出局与胜负；LLM 只能消费规则整理后的上下文，并在结构化白名单或安全表达契约内输出。

进入 V3 前仍有四项明确限制：当前对局主要保存在进程内存中；严格结构化策略重点覆盖普通非警长白天发言，其他路径仍以规则决策加角色化改写为主；LLM 校验、回退、延迟和成本只有日志，没有统一指标面板；NPC 平衡依赖人工试玩，尚无批量种子模拟与自动回归阈值。

V3 推荐先补齐可复现模拟、指标采集、合法视角信念状态和发言/投票一致性，再扩展全部阶段的结构化策略。完整拆分见 [`V3 改进与开发路线表`](../docs/V3_ROADMAP.md)。路线表是规划，不属于本封版已经实现的能力。

## 运行

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：`http://127.0.0.1:8000/docs`

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

修改 `.env` 后需要重启后端。`GET /api/llm/status` 用于检查启用状态、provider、模型和配置完整性，不会返回 API Key。

当前 DeepSeek 可靠性设置：

```dotenv
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=0.35
```

- DeepSeek 请求使用非思考模式和 `json_object` 输出，避免思考内容占用短回答预算或返回格式漂移。
- 超时、限流、临时服务错误、空内容和坏 JSON 会自动重试一次。
- 返回文本按“声明者 → 目标 → 结果”比对验人，并校验自称身份、女巫/守卫技能行动及信息权限；引用已公开的他人验人不会被算成当前角色新增验人。
- “我验了4号”会被视为预言家起跳；“我是预言家 / 我起跳预言家”“好人 / 金水”等自然同义改写不需要与规则模板逐字一致。
- “我拿的是村民牌”“7号，查杀”等省略表达，以及“4号起跳预言家，验了7号”这种逗号后延续主语的转述会被归一到结构化事实；并列引用他人的阵营判断不会算成当前 NPC 的直接断言。
- 普通白天的结构化 `intent` 直接用于规则状态更新，表达层不再要求命中固定意图关键词；“不足以直接定性”“回答我的问题”等自然同义说法可以保留。公开的“4号是狼/好人”和“我是好人”按可错观点处理，不会与角色表中的真实阵营比对；第一人称“我是狼”只有规则声明已授权时才可通过。
- “狼队友”不再是关键词黑名单：条件推理、双狼猜测、他人转述、反问、否定和普通“我的队友”可以通过；未经授权的“3号是我的狼队友”“我们狼队”等第一人称明确狼队关系仍会拒绝。篡改目标或结果、凭空增加查验/技能事实、断言未公开神职或明确自曝隐藏狼队时，会携带全部结构化校验原因继续纠正，最多产生五份候选文本，成功即停止。
- 五轮全部失败后使用规则模板；所有被拒绝的原始返回都会写入 `data/llm_validation_failures.jsonl`，即使后续轮次成功也保留恢复记录。
- 新日志带 UTC `recorded_at` 与 `validator_version`，用于区分旧版本记录和当前 `semantic-v3` 校验行为。
- 进行中的对局只返回失败原因和统一脱敏占位，不返回被拒绝的 DeepSeek 原文；是否脱敏只取决于失败类型，不会查询原文提到的角色是否真狼。服务端 JSONL 和 `GAME_OVER` 后的复盘仍保留完整原文。

结构化公开发言计划 v2：

- `app/npc_decision.py` 定义严格的 `npc_decision_context.v1` 与 `public_speech_plan.v2`。普通非警长 `DAY_MEETING` 使用“决策层 → 语气层”两次调用；旧 `public_speech.v1` 仍可升级为 v2 计划，但新请求统一要求 v2。
- 每次决策都整理当前 NPC 的真实身份、阵营、性格、合法知识、近期公开日志、自身私有记忆、阶段、合法目标、声明事实包、带可见性的证据和公开动作信号。`decision_signals` 覆盖上警/不上警、退水/继续竞选、警长票与警徽结果、公开验人说法、上一天放逐票、已公布出局和保守的低信息量评价；验人信号只表示“某人公开这样说过”，不包含内部 `source` 或真假答案，夜间来源与仍待公布的首夜结果也不会进入公开投影。
- 第一段只能返回扁平策略 JSON，不得包含 `text` 或 `fields` 包装。提示中的 `output_contract` 会给出根级必填键和完整 `flat_json_example`，所有字段都必须直接出现在根级，可空项也必须显式写 `null`。为兼容旧提示造成的模型惯性，后端只展开键恰好为 `schema_version + fields` 的 v2 包装；额外顶层键和展开后的额外内层键仍会被严格拒绝：

| 字段 | 含义与边界 |
| --- | --- |
| `schema_version` | 固定为 `public_speech_plan.v2` |
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

- `signal_read` 可选 `raises_suspicion / reduces_suspicion / needs_explanation / uncertain / mixed / none`。
- `question.topic` 可选 `claim_basis / action_motive / stance / vote_intent / timeline / contradiction / role_result / response_to_pressure`；`verification.criterion` 可选 `next_speech_consistency / claim_consistency / vote_alignment / response_quality / role_result / night_result / badge_action / follow_up_action`。
- 通用 `tactic` 包括 `information_probe / action_audit / direct_pressure / conditional_defense / consistency_check / vote_test / role_reveal / role_counterclaim`；狼人额外可选 `wolf_distance_teammate / wolf_bus_teammate / wolf_fake_check_teammate / wolf_rescue_teammate / wolf_frame_good / wolf_counterpush_good / wolf_fake_seer / wolf_deep_cover / wolf_misdirection`。

- `observe / pressure / defend` 必须有具体主目标；在存在公开信息时，还必须选择至少一项公开信号、公开证据或合法声明。施压/对跳必须反对主目标，辩护必须支持主目标；未知枚举、额外字段、字符串数字 ID、越权/重复 ID、互相矛盾的目标与战术都会被拒绝。
- 如果当天有人公开给当前 NPC 发金水或查杀，上下文会额外提供 `response_requirements`：计划必须选中对应 `seer_check_claim` 信号，并把声明者放进主目标或次目标。收到查杀时必须质疑或反对来源；收到金水时可以支持、保留或质疑，但不能把“自己确实是好人”推导成“对方一定是真预言家”。规则回退也遵守同一要求。
- 私有知识和完整公开历史只进入第一段决策，可影响“NPC 相信什么”，但不能作为公开证据。计划通过后，第二段只拿人物口吻和阶段，返回 4–18 个中文字符、不含座位号、身份、动作或票型事实的语气前缀；不会收到真实身份、狼队、夜间记忆、私聊原文、计划内容、未选信息、私有战术名或第一段 raw output。
- Python 把已校验计划渲染成包含判断、问题、验证点和暂定票的规则正文，再拼接语气前缀。正文可以体现错误判断，也允许好人被狼人的公开叙事骗到，但 LLM 无法反转计划或伪造动作、身份、查验、技能、出局和胜负事实；“没信息，过”不会成为正式发言。
- 通过校验的计划保存在当天 `SpeechState.decision_plan`。普通好人的警长票和放逐票只综合怀疑、公开压力、关系、公开声明可信度、警长归票、公开查杀、计划暂定票与本局参数，不读取候选人的真实 `role/camp`；因此可以选中假预言家、在真假预言家间分票或投出真预言家。真预言家自己的查验和狼人的队友知识仍属于各自合法私有信息。`plan_consistency` 只给暂定票加权，后续公开证据仍能推翻，旧日期计划不会复用。
- 决策与表达分别最多纠正五轮。决策失败时使用可验证的规则计划；表达失败时保留已校验计划并使用规则话术。全部完成后才写入 `speeches`、`public_claims`、`public_logs` 和 NPC 记忆。
- 当前只有普通非警长 `DAY_MEETING` 进入 v2 决策层；警上、警长、夜间、投票和私聊保持原规则决策边界，LLM 只做已批准内容的角色化改写。

### 本轮决策契约（已完成）

下列小里程碑已经实现，并通过完整自动化回归：

- `public_position.v1` 是发言完成后的公开精炼立场卡，覆盖信任、不信/怀疑、暂定票、追问和改票条件。后续公开 RAG、决策和发言只引用这个摘要，不把长段 `text` 重新送入决策层，也不读取只对行动者开放的 `decision_plan`；否定句按对象解析，避免“不怀疑 / 不会投”被反向记录。
- 警徽流使用追加版本，每版包含声明者、版本号、发布日、`effective_night_day`、顺验目标、金水/查杀分支和公开改流理由。场上形势变化时可以换流；“改变警徽流”本身的可信度调整为零，只评估理由是否可由公开状态验证、前后叙事是否冲突。真预言家夜间选择只对当夜有效版本做软参考，不强制锁定查验。
- 警徽移交/撕毁只能对命中的明确分支生成中立推理，例如“按 4 号自己的警徽流，此次移徽表达其声称 7 号为金水”。这是公开角色声明，不是规则验真；普通角色只因“没接徽”不会被推定为好人或狼人。
- 玩家同次跳预言家+发布首版警徽流会先归一化最终公开身份并整体校验，再原子写入公开状态；后续调整通过 Godot 当前行动 UI 提交版本和理由。Python 始终用结构化字段替换自由文本中的警徽流目标/分支，并展示 `effective_night_day`；事实型换流理由必须能由公开记录验证。警长当选、移徽或撕徽后，服务端 `sheriff` 投影与玩家/NPC 头顶警长标识保持一致。
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
- 请求失败、超时、无效 JSON、替换字符或输出越界时，自动退回当前模板逻辑，游戏仍可完整运行。

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
- `GET /api/game/{game_id}/state`
- `GET /api/game/{game_id}/summary`
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
- `POST /api/day/private-chat`
- `POST /api/day/end-free-activity`
- `POST /api/vote/submit-and-resolve`

旧的 `POST /api/vote/npc-decisions`、`POST /api/vote/player` 与 `POST /api/vote/resolve` 仍保留兼容，但 Godot 主流程只调用同步结算接口。

`GET /api/game/{game_id}/state` 的 `meeting` 字段包含：

- `direction`：`clockwise` 或 `counterclockwise`。
- `order`：当天所有存活角色的发言顺序。
- `current_speaker_id`：当前允许发言的角色。
- `current_position` 与 `total_speakers`：会议进度。
- `completed`：会议是否完成。

同一响应的 `sheriff` 字段包含完整候选人、活跃候选人、退水名单、当前竞选发言者、轮次、投票资格及原因、可投目标、警长、发言锚点、暂时归票和最终归票目标。角色视图的 `sheriff_campaign_status` 为 `candidate`、`withdrawn`、`pk` 或空字符串，供 Godot 显示头顶标记。

同一响应的 `player_private_info.action_history` 是只对玩家可见的本局累计记录，包含夜间技能与结算结果、猎人开枪、警上操作、完整公开发言、私聊问题、首次触发彩蛋及放逐投票；新游戏使用新的状态数组，因此记录自动清空。

同一响应的 `public_intel` 是左上角关键公开信息面板使用的安全投影，包含日期、公开类型、声明者、可选目标、公开结果和中立显示文本。预言家验人、女巫救毒和守卫成功均使用“称/声称”措辞；猎人开枪属于规则已向全场确认的公开动作。该投影刻意不包含 `PublicClaimState.source`、真假标记、真实身份/阵营、狼刀、真实守护或女巫用药结算，因此真假声明在前端具有相同结构。

服务端会验证发言者。玩家和 NPC 都不能跳过顺序，也不能在同一天重复正式发言。

NPC 正式发言会检索知识库和当前已经发生的公开发言。返回的 `speech` 包含 `evidence_titles` 和 `retrieval_mode`；普通白天结构化决策只能引用自己选择且标记为公开的证据与规则投影的公开动作信号。若 NPC 当天被公开发金水或查杀，它的首轮白天发言必须回应该说法；若警长票投给了别人，规则正文会同时说明这张票，避免角色收到金水后完全失忆。

公开发言会解析并记录身份与验人声明。真预言家可以公布实际查验；每局指定一名 NPC 狼人作为悍跳候选，可以起跳预言家并维护跨轮假验人记录；女巫、守卫和猎人也会根据已知信息、公开压力与性格决定是否公开技能信息。公共状态返回角色卡使用的中立 `public_claims` 标签和左上角面板使用的完整安全 `public_intel` 列表，两者都不标记真假。

`config/npc_profiles.json` 中的 `speech_style`、`catchphrases`、`easter_eggs` 和 `trigger_easter_eggs` 控制角色化表达。触发彩蛋只在 `FREE_ACTIVITY` 私聊中匹配，忽略大小写、空格和标点；每名狼人杀 NPC 当前配置一个关键词彩蛋。规则文本和 LLM 输出都必须保留已选择公开声明中的身份、目标、结果与技能行动；校验器按事实而非模板字面判断，姓名、座位号、“好人/金水”等同义词和合法私聊代词会归一到同一事实。五轮均失败时响应返回 `llm_validation_failure`，进行中的 Godot 视图只展示失败原因和脱敏占位。

`POST /api/day/private-chat` 只允许在 `FREE_ACTIVITY` 使用。私聊不会写入 `public_logs`；同一 NPC 当天只有第一次普通提问会修改怀疑、信任和内部记忆，后续追问只返回回答。关键词彩蛋不消耗这次有效提问，首次发现会写入玩家私密行动记录。

梅长苏的 `mei_changsu_lin_shu` 彩蛋是当前唯一允许透露真实游戏身份的触发项。后端把实际身份作为 `required_self_role` 写入 LLM 校验契约；回复遗漏身份、改成其他身份、增加其他角色身份或泄露狼队友时仍会拒绝，最终规则回退始终保留正确身份。

私聊回复使用当前会话视角：NPC 以“我”自称、称玩家为“你”，其他角色显示“号码 + 名字”。玩家消息里的“我/自己”映射到玩家，“你”映射到当前 NPC；无法从本句或同一 NPC 最近私聊中解析的“他/她/TA”会触发澄清，并且不消耗当天的有效追问次数。

`GET /api/game/{game_id}/summary` 只允许在 `GAME_OVER` 后调用，返回：

- 获胜阵营和总天数。
- 每名角色的真实身份、阵营、胜负、生存结果和关联行动。
- 按阶段排序的全局时间线，包括夜间技能、查验、实际挡刀、公开身份声明、发言、完整私聊、投票理由和出局结果。
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

普通聊天完整历史保存在 `data/memory.json`，按 `player_id::npc_name` 隔离并可跨后端重启读取；只有最近 8 轮进入 LLM 上下文。狼人杀的身份、关系、私有记忆和 `private_conversations` 只存在当前 `GAME_STORE`，两类记忆不会混用。

`POST /admin/reload-config` 会先完整校验、再原子替换人设、知识库和 NPC 智能参数。任何文件无效时返回 `400` 并保留整套旧配置；响应中的 `tuning_schema_version` 为 `npc_tuning.v1`，`applies_to` 为 `new_games`。智能参数在创建角色时写入本局快照，所以重载只影响之后创建的新对局，不改变进行中的 NPC。修改 `.env` 中的 API Key、provider 或模型后仍需手动重启后端，且本项目不会自动启动后端。

## 配置

- `config/npc_profiles.json`：15 名 NPC 的人设与基础知识；11 名参赛 NPC 保留角色化和彩蛋配置，坏坏和然然使用 `use_llm_for_chat` 开启常驻聊天生成。
- `config/knowledge_base.json`：111 条静态知识，包括开发资料、十二人狼人杀规则、完整警长规则、身份声明规则、11 名参赛 NPC 的判断风格和 4 条常驻居民专属知识。
- `config/npc_tuning.json`：11 名参赛 NPC 的版本化智能参数；不包含玩家、坏坏或然然。
- `data/memory.json`：运行时普通对话记忆。

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

本轮自动化已覆盖：`public_position.v1` 严格字段与摘要引用；警徽流版本/`effective_night_day`/换流/夜间软参考；明确分支下的移徽、撕徽声明与普通未接徽不推断；警长票和放逐票的多种子概率分布、候选顺序不变、可复现重放、隐藏身份互换不变与强证据共识；狼队软策略与狼查杀狼硬叙事；玩家同次起跳+警徽流的原子提交、后续调整 UI 和角色头顶警长标识。

这些命令只运行连接检查或自检，不会自动启动 FastAPI/Godot；服务由开发者按“运行”一节手动启动。
