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
```

完整 JSON 的根级 `metrics` 使用 `agent_town_metrics.v1`，包含阵营胜率、平均局长、警长/放逐票熵、好人正确票与误票、假预言家采信代理，以及按玩家身份、投票者角色和天数的聚合。无适用样本的比率是 `null`，不是 0。

默认报告还包含 `belief_state.v2` 影子信念轨迹：证据台账、每次分数变化和 11 名 NPC 的最后信念。公开软证据逐日乘以 `0.75`，公开票型/警徽动作和合法私有知识不衰减；有效私聊只按已保存的结构化目标与方向进入对应 NPC 的私有视角，不解析自由文本。100 局文件可能达到数十 MB，其中包含所有 NPC 依法拥有的赛后私有视角，不要把它直接返回给进行中的游戏客户端。

M04-A 默认还输出 `stance_summary.v1`：每名 NPC 的统一立场变化，以及公开发言、警长票、放逐票相对决定前摘要的 `aligned / explained_change / unexplained_change / unscored` 对照。完整 100 局 belief + stance 样本约 101MB；只分析 belief 时应使用 `--no-stance-trace`。终端写文件时会显示：

```text
[STANCE] mode=shadow; observations=...; alignment=...; unexplained_change=...
```

M04-B 把普通非警长白天发言接入 `public_speech_continuity.v1`，计划升级为 `public_speech_plan.v3`；警长票和放逐票仍只做 shadow 对照。模拟结果为 `agent_town_simulation.v6` / `agent_town_simulation_batch.v6`，并始终输出不含私有 belief 内容的 `speech_continuity_metrics.v1` 原因计数：

```text
[CONTINUITY] controlled_speeches=...; reasons={'stance_aligned': ..., 'new_public_evidence': ..., 'deterministic_variance': ..., 'authorized_claim': ..., 'mandatory_rule_response': ..., 'unscored': ...}
```

规则 fallback 会对齐 stance；启用 LLM 后，偏离必须引用本次已选的新增公开 signal，或命中内部 seed 与 NPC 参数决定的确定性扰动。合法声明和规则强制回应使用独立原因，不会把私有 belief evidence ID 写入持久化计划或公开台词。

M06-A 的隐藏信息不变性矩阵已并入完整 smoke。`hidden_info_projection.v1` 会比较普通村民玩家的公开/API 等价投影，以及所有普通 NPC 村民的 belief、stance、决策上下文、连续性和规则 fallback；`hidden_info_invariance.v1` 只输出摘要、计数和首个差异路径，不保存隐藏身份正文。

矩阵自动覆盖隐藏身份真值、悍跳内部标记、声明内部来源、未公布夜间结果和组合变体。固定夹具执行 96 项无权视角差分，并用公开查验结果变化作为必须被检测到的负对照。M06-A 只接受普通村民玩家和无警徽 NPC 村民。

M06-B 同样并入 smoke。`hidden_info_authorization.v1` 使用 `role_scoped_private_npc` 模式，在同一普通村民玩家基线上对 11 名 NPC 检查三类合法私有变化：

- 预言家把未公开验人从好人目标改为狼人目标，只允许该预言家的五层投影变化。
- 女巫看到的未公开刀口改变，只允许该女巫的 belief、stance、continuity 和 fallback 变化；decision context 保持不变。
- 一名非悍跳狼与守卫/猎人交换隐藏身份，只允许其他三名狼人更新私有狼队视角；两个本人身份已经变化的 actor 不参与对比。

三类授权案例合计执行 158 项检查，所有公开投影和未授权 NPC/layer 必须不变。测试还会故意把预言家授权错配给村民，确认矩阵同时检测缺失授权与越权传播。报告不保存变体状态或私有 evidence 正文。

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

只需要胜负和 M02 指标、或者准备运行 1000 局时，可关闭详细信念轨迹：

```bash
backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260719 \
  --games 1000 \
  --no-belief-trace \
  --output /tmp/agent-town-simulation-1000.json
```

关闭 belief 轨迹不会改变 `gameplay_digest`、胜负或指标，会把每局 `belief_trace / stance_trace` 和批量 `belief_summary / stance_summary` 设为 `null`。单独使用 `--no-stance-trace` 时，只有 stance 两项为 `null`；两种精简模式都保留体积很小的 `speech_continuity` 原因汇总。

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
