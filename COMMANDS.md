# Agent Town 常用命令

所有命令默认从项目根目录执行。请把 `<project-root>` 替换为本机克隆目录：

```bash
cd <project-root>
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

## 运行 V3 无 HTTP 批量对局

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

写入文件时，终端会同时显示核心 M02 指标，例如：

```text
[METRICS] good_win_rate=6.0%; exile_entropy=22.6%; good_misvote_rate=61.0%; fake_seer_sheriff_support=48.3%; fake_black_check_follow=41.6%
[BALANCE] winner_reasons={...}; first_exile_camps={...}
[WITCH] first_night_save=...; second_night_poison=...; accepted_hold=...; poison_wolf_hit=...
[SEER] fake_campaign=...; fake_elected=...; fake_black_checked_true=...; true_first_exiled=...
[EXILE-CHAIN] first_wolf_exile=...; next_exile_wolf=...; npc_correct_retention=...; after_first_wolf_retention=...
```

完整 JSON 的根级 `metrics` 使用 `agent_town_metrics.v4`，除原有阵营胜率、局长、票熵、好人误票和假预言家采信外，`balance_diagnostics` 还包含终局原因、首放阵营/身份、按出局原因/阵营计数，以及女巫救人、用毒、压毒、建议采信和毒药命中；`seer_claim_balance` 记录真假预言家链路；`cross_day_exile_chain.v1` 记录首放狼人条件胜负、下一次放逐阵营和非玩家好人 NPC 的四类跨轮选票转移。无适用样本的比率是 `null`，不是 0。

V3.1-L 的 NPC 女巫第一夜本人被刀必定自救，其他合法刀口确定性 99% 使用解药；第二夜有毒且存活时默认毒本人最怀疑的合法目标。玩家或 NPC 在公开正式发言（警上或白天会议）中可明确建议女巫毒单一目标，或以公开信息不足为理由建议压毒；Python 保存 `witch_directive.v1`，女巫按自己的合法怀疑、信任和公开信息独立决定是否采信。含糊多目标、过去用药声明和无理由压毒不会被自动当成可靠指令。

V3.1-M 使用 `fake_seer_campaign.v1` 决定最强 NPC 狼是否参加警长悍跳，不再每局强制参选；参选概率由既有 NPC tuning 和对局 seed 确定。`fake_seer_check_mix.v1` 在合法的队友金水、非狼查杀、非狼金水以及既有高压队友查杀之间混合。狼人只知道谁是狼队友，不读取非狼的预言家/女巫等精确身份；同一 seed 可重放，好人精确身份互换不得改变策略结果。

V3.1-N 的 `cross_day_exile_chain.v1` 是纯赛后 shadow。它可以在 `GAME_OVER` 后用真实阵营评价“投狼后是否继续投狼”和“误投后是否纠正”，但被放逐者的隐藏身份不会因此进入实时 NPC belief、投票器、LLM 或公开 API。下一阶段不得直接消费该真值标签，只能使用当时已经公开的票型、声明、本人 stance 与合法新证据。

默认报告还包含 `belief_state.v2` 影子信念轨迹：证据台账、每次分数变化和 11 名 NPC 的最后信念。公开软证据逐日乘以 `0.75`，公开票型/警徽动作和合法私有知识不衰减；有效私聊只按已保存的结构化目标与方向进入对应 NPC 的私有视角，不解析自由文本。100 局文件可能达到数十 MB，其中包含所有 NPC 依法拥有的赛后私有视角，不要把它直接返回给进行中的游戏客户端。

M04-A 默认还输出 `stance_summary.v1`：每名 NPC 的统一立场变化，以及公开发言、警长票、放逐票相对决定前摘要的 `aligned / explained_change / unexplained_change / unscored` 对照。完整 100 局 belief + stance 样本约 101MB；只分析 belief 时应使用 `--no-stance-trace`。终端写文件时会显示：

```text
[STANCE] mode=shadow; observations=...; alignment=...; unexplained_change=...
```

M04-B 把普通非警长白天发言接入 `public_speech_continuity.v1`，计划升级为 `public_speech_plan.v3`；警长票和放逐票仍保留 stance 对照。V3.1-N 后当前模拟结果为 `agent_town_simulation.v11` / `agent_town_simulation_batch.v11`，并继续输出不含私有 belief 内容的 `speech_continuity_metrics.v1` 原因计数：

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

默认批量模拟会在每次 NPC 警长票和放逐票前记录 `vote_probability_trace.v2`，并在批量根级输出 `vote_probability_summary.v2`。只有 `VOTE` 阶段非警长好人 NPC 放逐票使用 `consumer_mode=controlled` / `good_exile_calibration.v1`；警长票、狼人票和规则硬约束继续为 shadow。推荐用 100 个 seed 回归，同时关闭更大的 belief/stance 明细：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 100 \
  --no-belief-trace \
  --output /tmp/agent-town-vote-calibration.json
```

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

## 汇总 M09-A 脱敏 LLM 观测

后端实际发生 LLM 调用或语义校验时，会把 `llm_observation.v1` 事件追加到 `backend/data/llm_observability.jsonl`。无需启动后端即可汇总已有文件：

```bash
backend/.venv/bin/python scripts/summarize_llm_observability.py
```

指定输入并同时保存 `llm_observability_summary.v1`：

```bash
backend/.venv/bin/python scripts/summarize_llm_observability.py \
  --input backend/data/llm_observability.jsonl \
  --output /tmp/agent-town-llm-summary.json
```

输出汇总请求成功率、语义校验恢复/回退、平均尝试、重试次数、平均/P95/最大延迟、provider 已返回的 token、主要 fallback/rejection 类别，并提供 `by_task` 和 `by_provider_model` 分组。日志不存在时会输出计数为 0 的合法空摘要；坏行被跳过并计入 `invalid_event_count`。

该文件采用严格脱敏字段，不记录 API Key、prompt、上下文、回复、fallback 文本、game/character ID 或原始拒绝原因。`backend/data/llm_validation_failures.jsonl` 是另一份可能包含原始候选的敏感审计日志，不要把它当作 M09-A 指标源。provider 未返回 `usage` 时不猜 token；M09-A 也不估算费用，版本化价格口径留给 M09-B。

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
```

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

## 查看 LLM 校验失败日志

只要出现被结构化事实校验拒绝的 LLM 候选文本，就会生成或追加该文件；日志会列出全部原因，并区分后续恢复成功和五轮全部失败。自然同义改写不要求与规则模板逐字一致：

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
