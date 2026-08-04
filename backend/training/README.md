# NPC 策略数据入口（V5）

这里训练的是“在 Python 已生成的合法候选中，如何排序/投票”，不是
DeepSeek 语言表达，也不是端到端重写规则。运行时仍由 Python 负责身份、权限、
候选集合、确定性采样、事件链和失败回退。

仓库自带的 `npc_policy_v1.jsonl` 只有 10 局、280 条规则教师记录，作用是证明训练、
加载、shadow/local 和重放链路可运行，不代表模型已经超过规则，也不能作为生产质量
结论。实际训练应增加独立局数、人工/专家标签和未见 episode 的评估集。

## 最安全的喂数方式：观察与标签分离

先用仿真导出 observation（每行一条 NPC 决策），再单独维护人工/专家标签。
用户不需要手改 25 维特征：

```bash
backend/.venv/bin/python backend/training/generate_policy_dataset.py \
  --seed 1001 --games 200 \
  --output backend/training/datasets/teacher_200.jsonl

backend/.venv/bin/python backend/training/validate_policy_dataset.py \
  --input backend/training/datasets/teacher_200.jsonl \
  --output /tmp/teacher_200.normalized.jsonl

backend/.venv/bin/python backend/training/merge_policy_labels.py \
  --observations /tmp/teacher_200.normalized.jsonl \
  --labels my_labels.jsonl \
  --output /tmp/my_policy_labeled.jsonl

backend/.venv/bin/python backend/training/train_policy.py \
  --dataset /tmp/my_policy_labeled.jsonl \
  --model-type mlp --hidden-size 32 \
  --output-dir backend/policy_artifacts

backend/.venv/bin/python backend/training/evaluate_policy.py \
  --dataset /tmp/my_policy_labeled.jsonl \
  --artifact-dir backend/policy_artifacts \
  --output /tmp/my_policy_evaluation.json
```

标签文件的每一行必须是 `npc_policy_label.v1`：

```json
{
  "schema_version": "npc_policy_label.v1",
  "observation_digest": "来自 observation 的 64 位摘要",
  "preferred_action_id": "exile_vote:9",
  "label_type": "human_preference",
  "confidence": 1.0,
  "weight": 1.0,
  "source_id": "reviewer_001",
  "rationale": "可选，仅离线审计",
  "tags": ["logic_conflict"]
}
```

也可以用 `target_distribution` 代替 `preferred_action_id`，例如
`{"exile_vote:7":0.25,"exile_vote:9":0.75}`。两者只能选一个。`confidence`
会把首选动作设为该概率，其余合法候选均分剩余概率。
同一 observation 可以由多个不同 `source_id` 独立标注；训练器按 `weight` 使用这些
记录，但同一 `observation_digest + source_id` 的重复/冲突标签会被拒绝。

## 直接导入完整记录

外部采集器也可直接写 `npc_policy_training_record.v1`（示例见
`examples/policy_training_record.example.jsonl`）。一行至少包含：

- `seed`、`game_index`、`game_id`、`trace_index`、`day`、`phase`、`actor_id`、`faction`
- `observation_digest`、`reasoning_digest`
- 严格固定顺序的 `feature_names`（当前 25 个，见 `app/npc_policy.py`）
- `candidates[]`：`action_id`、`action_type`、`target_id`、25 个有限数值
- `rule_probabilities`：按 target ID 的 soft target

验证器会把 V1 规范化成 `npc_policy_training_record.v2`。V2 的标签字段是
`target_distribution`、`label_type`、`source_id`、`weight`。候选 action/target
必须唯一；概率有限、非负且和为 1；摘要过期、未知字段、重复 observation、
重复 `(game_id,trace_index)` 都会逐行报错，并且验证失败时不会写输出文件。
整数特征会先规范化成浮点后再计算摘要，所以手写 `0` 和 `0.0` 等价。
规范化文件头的 `content_sha256` 是整个 JSONL 文件（不含任何隐式换行转换）的
SHA-256；它用于审计数据是否被替换，不是模型质量指标。

## 隐私和标签边界

`candidates.feature_values` 是 actor-scoped observation。不要把真实角色、完整
role assignment、狼队名单、终局 winner 或其他隐藏真值塞进去；这些只能放在
离线评估器的独立标签文件，不能进入实时 observation。`rationale` 只用于审计，
不会发送给 Godot，也不会改变规则状态。结构校验能拒绝明显的字段泄漏，但不能
自动证明任意外部数据在语义上没有隐藏信息；优先使用脚本生成的观察，再做人工抽样审计。

## 推理场景格式

要给“NPC 是否发现某个逻辑矛盾”喂评测数据，使用
`npc_reasoning_scenario.v1`，每行包含一份完整的 actor-scoped observation 和期望：

```json
{
  "schema_version": "npc_reasoning_scenario.v1",
  "scenario_id": "same_window_gold",
  "observation": { "这里放 npc_reasoning_observation.v1，字段严格校验" },
  "expect": {
    "required_signal_kinds": [
      "seer_golded_persistent_counterclaim",
      "sole_consistent_seer_claimant"
    ],
    "forbidden_signal_kinds": [],
    "supported_seer_id": 1,
    "hidden_world_consistent": false,
    "min_seer_probability": {"1": 0.9}
  }
}
```

运行评测：

```bash
backend/.venv/bin/python backend/training/reasoning_scenarios.py \
  --input reasoning_scenarios.jsonl \
  --output /tmp/reasoning_report.json
```

建议至少维护三条反事实样本：同窗 A/B 都继续且 B 给 A 金水；只有 A 单独跳预言家；
以及把同一批 day1 证据搬到 day2（后两者不应错误地产生 hard conflict）。场景期望只
检查 signal、概率和可能世界摘要，永远不直接写入或修改规则真值。

## 从逻辑场景挑选人工决策样本

可以从规则教师 JSONL 中筛选带有 `candidate_logic_conflict` 或
`candidate_sole_consistent_seer` 特征的放逐决策，生成待审阅队列：

```bash
backend/.venv/bin/python backend/training/generate_policy_review_queue.py \
  --input backend/training/datasets/npc_policy_v1.jsonl \
  --output /tmp/logic_review_queue.jsonl
```

审阅者只填写 `preferred_action_id` 或完整的 `target_distribution`（二选一）、
`rationale`、`source_id` 和 `tags`。队列中的候选已经由 Python 生成，不能新增动作。
填写后转换为严格标签，再按 digest 合并：

```bash
backend/.venv/bin/python backend/training/convert_policy_review_queue.py \
  --queue /tmp/logic_review_queue.jsonl \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --output /tmp/logic_labels.jsonl
backend/.venv/bin/python backend/training/merge_policy_labels.py \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --labels /tmp/logic_labels.jsonl \
  --output /tmp/logic_labeled.jsonl
```

转换器会拒绝未填写的队列、非法动作、缺失候选、重复或过期 observation digest。

如果只是要先跑通管线，可用 `fill_policy_review_queue.py` 生成一份明确标记为
`imported`、`needs_human_review` 的启发式 bootstrap 标签；它不是人工金标准，不能直接
据此宣称模型质量提升：

```bash
backend/.venv/bin/python backend/training/fill_policy_review_queue.py \
  --input backend/training/inbox/logic_review_queue.jsonl \
  --output backend/training/inbox/codex_logic_review.jsonl
```

如果有多名审阅者，应先分别使用不同 `source_id` 转换，再生成共识标签。默认至少两名
审阅者且最高动作一致率达到 `0.67` 才进入训练集；其余记录只写入冲突报告：

```bash
backend/.venv/bin/python backend/training/consensus_policy_labels.py \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --labels reviewer_a.jsonl reviewer_b.jsonl \
  --output /tmp/consensus_labels.jsonl \
  --report /tmp/consensus_report.json
```

正式训练前可比较标签与 Python soft teacher 的偏离程度：

```bash
backend/.venv/bin/python backend/training/compare_teacher_labels.py \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --dataset backend/training/datasets/logic_policy_labeled.jsonl \
  --output /tmp/teacher_label_comparison.json
```

该报告只衡量标注分歧，不代表胜率、平衡或模型质量。

可生成离线可视化审计台：

```bash
backend/.venv/bin/python backend/training/review_dashboard.py \
  --input backend/training/inbox/logic_review_queue.jsonl \
  --output backend/training/inbox/review_dashboard.html
```

直接用浏览器打开生成的 HTML。它支持筛选、候选卡片、冲突/唯一预言家可视化、首选动作、
概率分布、置信度、理由和标签编辑；草稿保存在浏览器本地，点击“导出已填写 JSONL”后再
交给 `convert_policy_review_queue.py`。

如果由 Codex 按“聪明好人 v2 / 聪明狼人 v1”原则生成可解释审计，可运行：

```bash
backend/.venv/bin/python backend/training/audit_policy_review_queue.py \
  --queue backend/training/inbox/logic_review_queue.jsonl \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --output backend/training/inbox/codex_smart_audit.jsonl \
  --report backend/training/inbox/codex_smart_audit_report.json
```

好人 `codex_smart_good_audit_v2` 是 teacher-anchored 标签：没有
`candidate_logic_conflict` 或 `candidate_sole_consistent_seer` 时逐项等于 rule teacher；
有硬公开逻辑冲突时保留 85% teacher，只把 15% 质量集中到公开冲突候选、已有暂时/
最终归票或 teacher 首选，并把唯一一致预言家的合计票仓封顶为 2%。这样只在有公开硬
依据时明显偏离、减少无谓分票。狼人继续使用 `codex_smart_audit_v1` 的原分布、温度、
来源 ID 和理由。脚本输出仍只是离线审计标签，不是隐藏身份真值或平衡结论。

重生成后应先验证狼人行逐条未变，再转换、合并并训练：

```bash
backend/.venv/bin/python backend/training/convert_policy_review_queue.py \
  --queue backend/training/inbox/codex_smart_audit.jsonl \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --output backend/training/inbox/codex_smart_labels.jsonl
backend/.venv/bin/python backend/training/merge_policy_labels.py \
  --observations backend/training/datasets/npc_policy_v1.jsonl \
  --labels backend/training/inbox/codex_smart_labels.jsonl \
  --include-teacher-records \
  --output backend/training/datasets/codex_smart_policy_labeled.jsonl
backend/.venv/bin/python backend/training/train_policy.py \
  --dataset backend/training/datasets/codex_smart_policy_labeled.jsonl \
  --model-type mlp --hidden-size 32 \
  --output-dir backend/policy_artifacts
```

模型概率温度先离线扫描，不直接改运行时：

```bash
backend/.venv/bin/python backend/training/calibrate_policy_temperature.py \
  --input /tmp/smart_shadow_50.json \
  --output /tmp/smart_temperature_calibration.json
```
运行 shadow/local 时可显式封印温度，例如：

```bash
AGENT_TOWN_NPC_POLICY_TEMPERATURE=0.65 \
  AGENT_TOWN_NPC_POLICY_MODE=shadow \
  backend/.venv/bin/python scripts/simulate_games.py \
  --seed 20260727 --games 50 --npc-policy-mode shadow \
  --include-policy-traces --output /tmp/shadow_t065.json
```
温度会写入 policy trace，并参与 shadow/local 存档配置指纹；rule 模式仍固定为 1.0。
local 还支持 `AGENT_TOWN_NPC_POLICY_BLEND`（`0.0–1.0`）：最终概率是 rule 与 model 的
请求混合，默认 `1.0`；`npc_policy_entropy_guard.v1` 再按上下文收紧有效混合。普通
好人逐项等于 teacher，只有方向正确的硬公开逻辑纠偏才会放行；所有 trace 都保留原始
模型概率、护栏后概率、熵、总变差和有效混合。低于 `1.0` 仍只能作为保守金丝雀参数，
必须单独 shadow/local 验证。

local 的夜间目标（狼刀、守卫、查验、女巫毒、猎人）消费 actor-scoped belief 前还会
经过 `AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE` 置信度门禁（默认 `0.80`）：只有目标角色
信念 `confidence` 达到阈值才使用信念评分，否则回退到与 rule 完全一致的选择。
`rule/shadow` 不受该变量影响。

正式数据集 SHA-256 为
`194db719c381d3371fc35b5ac18dc46b19c0de1195b95bfa29c408a171f324f7`：
280 条 rule teacher + 40 条好人 v2 + 59 条狼人 v1，共 379 条。32 隐层 MLP 的全量
离线 top-1 一致率为好人 `90.68%`、狼人 `70.63%`，合法率和覆盖率均为 `100%`。

当前已完成 seed `20260727–20260736` 的 10 局 shadow 和 local 金丝雀，以及
seed `20260601–20260630` 的扩展 30 局 local 金丝雀。Shadow 有 205 条策略轨迹、
零 fallback；原始 MLP 有 38 条会改变 teacher 首选，护栏后为 0。消融确认
`blend=0.10` 与 `blend=0.00` 的 local 轨迹完全一致，即放逐 MLP 尚未改变任何采样票，
此前金丝雀的指标变化全部来自 V5.4-A 夜间信念消费。加入
`AGENT_TOWN_NIGHT_BELIEF_CONFIDENCE=0.80` 置信度门禁后：10 局金丝雀好人胜场
`2→3`、误投 `62.0%→58.3%`、投狼概率质量 `38.3%→43.8%`、跨日保持
`80.6%→87.5%`、放逐熵 `25.8%→26.3%`（唯一未变好的单项，由单局轨迹翻转主导）；
扩展 30 局六项核心指标全部改善：胜场 `43.3%→60.0%`、误投 `47.7%→40.6%`、
投狼概率质量 `53.5%→60.5%`、放逐熵 `29.1%→28.5%`、跨日保持 `67.0%→83.3%`；
重放 `30/30`、零 fallback，金丝雀门槛通过。默认模式仍为 `rule`，待人工标签清洗
与模型重训后正式切换 `local`。

100 局 shadow 后可提取模型与规则分歧最大的 actor-scoped 样本：

```bash
backend/.venv/bin/python backend/training/extract_policy_disagreements.py \
  --input /tmp/smart_shadow_100_t065.json \
  --output /tmp/smart_policy_disagreements_100.json \
  --limit 50
```

`npc_policy_disagreement_report.v2` 按护栏后 KL 偏离排序，并分别保留规则、原始模型、
护栏后概率及三者 top action、候选特征和 observation digest，不包含隐藏身份；
KL 只表示策略差异，不是游戏质量分数。

可进一步按聪明阵营不变量分类分歧：

```bash
backend/.venv/bin/python backend/training/analyze_policy_disagreements.py \
  --input /tmp/smart_policy_disagreements_100.json \
  --output /tmp/smart_policy_disagreement_analysis_100.json
```

当前 `smart_wolf_targets_stable_core_without_teammate` 表示狼人模型优先处理稳定核心且
没有投狼队友，属于预期分歧；未分类或投狼队友样本必须人工复核。

目前 `exile_vote` 是唯一开放 local 接管面的任务。`--model-type linear` 生成
可回读的 `npc_policy_artifact.v1`；`--model-type mlp` 生成带架构、SHA-256 和
特征封印的 `npc_policy_artifact.v2`。建议先 `shadow`，确认合法性、重放和指标后
再使用 `local`。

## 目录约定

- 原始外部文件：放在项目外或 `backend/training/inbox/`，不要自动提交
- 规范化数据：`backend/training/datasets/`
- 可加载模型：`backend/policy_artifacts/good_policy_v1/` 和
  `wolf_policy_v1/`
- 示例：`backend/training/examples/`
