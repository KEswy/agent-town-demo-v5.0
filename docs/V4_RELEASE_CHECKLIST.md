# Agent Town Demo V4 封版清单

## 当前状态与范围

这是一份未来正式封版操作清单，不代表 V4 已经发布。当前仍在
`v4-development` 开发；公开开发仓库
[`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0)
和专用 `v4-origin` 已创建，用于开发快照，但尚未创建 `v4.0.0`。任何 V4 代码仍不得
向历史 `origin`、`v2-origin`、`v3-origin` 推送。

V4.0 的交付范围是源码仓库。当前没有 `export_presets.cfg`，因此不承诺 Linux 或
macOS 可执行包。根目录目前也没有项目 LICENSE；当前公开开发快照明确记录为
“未授予再分发许可”，不能从字体的 `OFL.txt` 推断项目许可。正式封版前，所有者仍可
选择并加入合适的项目许可证。

## 1. 仓库治理门禁

- [ ] 已获得用户对“开始正式封版并创建 tag”的单独明确批准。
- [x] 当前分支是 `v4-development`，且没有指向历史 remote 的 upstream。
- [ ] `v3.0.0^{}` 精确等于 V3 基线
  `7a44dd598a62739e450bebe56198a6fe1f505ebd`，并且是候选提交的祖先。
- [ ] `origin`、`v2-origin`、`v3-origin` 仍只作为历史只读来源；没有执行任何针对它们
  的 push、force-push、mirror 或 tag push。
- [x] `v4-origin` 只指向公开开发仓库，不是任何历史仓库。
- [ ] 正式封版前不存在 `v4.0.0`；它只在本清单第 8 节创建。

候选阶段只读核对：

```bash
git status --short
git branch -vv
git remote -v
git tag --points-at HEAD
git merge-base --is-ancestor v3.0.0 HEAD
git rev-parse HEAD
git rev-parse 'v3.0.0^{}'
```

## 2. 候选提交内容

- [ ] 候选提交树与发布范围一致；除明确排除的未跟踪 `3.0总结/` 外，没有意外
  工作区改动。不要使用 `git add .`。
- [x] 当前开发快照排除并保留未跟踪的 `3.0总结/`，没有删除本地历史资料。
- [ ] 正式 V4.0 发布前，用户已明确决定 `3.0总结/` 是否属于最终发布内容。
- [ ] Godot 的 `.gd.uid` 已跟踪，`game/.godot/` 仍被忽略。
- [ ] 没有意外大文件、开发者绝对路径、临时补丁、调试输出或未解释的生成文件。
- [ ] `.env`、`backend/data/`、游戏存档、数据库、向量缓存、`.godot/`、虚拟环境、
  `__pycache__` 和 `*.pyc` 均未进入候选提交。
- [ ] 字体文件与 `game/assets/fonts/OFL.txt` 同时存在。
- [x] 当前开发快照记录为没有项目 LICENSE、未授予再分发许可。
- [ ] 正式 V4.0 发布前，仓库所有者已决定继续无许可证或加入明确的项目 LICENSE。

## 3. 自动验证矩阵

`.github/workflows/ci.yml` 必须在同一候选提交上全部通过：

| job | 平台 | 固定工具 | 内容 |
| --- | --- | --- | --- |
| `offline-core` | Ubuntu 24.04、macOS 15 | Python 3.12 | fresh install、`pip check`、编译、规则/存档/文档 smoke |
| `godot-headless` | Ubuntu 24.04、macOS 15 | Python 3.12、Godot 4.7.1 | 资源导入、字体、昼夜脚本、主场景加载 |

依赖安装和 Godot 安装阶段需要访问软件源；测试执行阶段固定
`ENABLE_LLM=false`、`LLM_PROVIDER=mock`、`AGENT_TOWN_DISABLE_VECTOR_RAG=1`、
`HF_HUB_OFFLINE=1`，不读取 GitHub secrets、不请求真实 LLM、不下载向量模型、不启动
FastAPI、Godot 编辑器或常驻游戏进程。存档必须写到 runner 临时目录。

本地等价命令：

```bash
ENABLE_LLM=false LLM_PROVIDER=mock AGENT_TOWN_DISABLE_VECTOR_RAG=1 HF_HUB_OFFLINE=1 \
  backend/.venv/bin/python scripts/smoke_check.py --profile core

GODOT_BIN=/Applications/Godot.app/Contents/MacOS/Godot \
  backend/.venv/bin/python scripts/smoke_check.py --profile godot
```

- [ ] Linux 两个 job 通过。
- [ ] macOS 两个 job 通过。
- [ ] `git diff --check` 通过，测试后 tracked files 没有变化。
- [ ] 从 fresh clone 或 GitHub source archive 再执行一次完整 smoke。

## 4. 手工桌面验收

FastAPI 和 Godot 由验收者手动启动，使用隔离的空存档目录。至少检查：

- [ ] `1100×650`、`1280×720`、`1600×900` 三档没有遮挡，长内容可滚动。
- [ ] 鼠标与整局键盘路径可完成设置、夜间技能、警长、发言预览、放逐、情报、
  NPC 对话和赛后复盘。
- [ ] 中文输入、字体、焦点框、Esc 关闭与关闭后焦点归还正常。
- [ ] LLM 关闭时可完整进行一局，不发生网络请求。
- [ ] 开局分别验证 LLM 输出校验与原文直出：前者最多校验 5 轮；后者生成 1 次、
  语义校验与纠错 0 次，原文即使错误或越界也直接显示，状态栏显示实际生效模式。
- [ ] 原文直出不产生 validation failure，且文本中的虚构目标、身份、技能建议和
  私聊指代不会进入权威声明、立场、怀疑值、票型、技能或胜负结算。
- [ ] 省略 `enable_llm_validation` 时仍默认多轮；首个
  `game_created.command.start_request` 封存选择且局中不可热切换，旧事件/旧存档恢复
  时缺键偏好按 `true`（LLM 实际未启用时 effective 仍为 `false`）；原文直出固定只
  请求 1 次。
- [ ] 手动保存/恢复、启动恢复、相同幂等 key 重试和终局重复请求符合文档。
- [ ] macOS 桌面流程通过。
- [ ] Linux 桌面流程通过；若只完成 Linux headless，则发布说明必须写
  “Linux headless/后端已验证，Linux 图形交互为候选支持”。

## 5. 工具与依赖记录

在候选提交的发布记录中保存下列输出；不要把本机 `.venv` 提交进仓库：

```bash
python3 --version
backend/.venv/bin/python --version
backend/.venv/bin/python -m pip --version
backend/.venv/bin/python -m pip check
backend/.venv/bin/python -m pip freeze --all
godot --version
uname -a
shasum -a 256 backend/requirements.txt
git rev-parse HEAD
```

CI 基线是 Python 3.12 和 Godot 4.7.1。`backend/requirements.txt` 固定直接依赖，
传递依赖没有跨平台 lock；所以每次封版都必须保留 fresh install 的完整 `pip freeze`
记录，不能把旧本机环境当成依赖事实。V4.0 只承诺 Linux/macOS 的 POSIX 本地文件系统；
不宣称 Windows、NFS 或 CIFS 存档语义受支持。

## 6. 隐私与发布物检查

- [ ] source archive 中没有 `.env`、API Key、带凭据 URL、私聊原文、隐藏身份存档、
  `backend/data/`、LLM 原文日志、数据库、向量模型缓存或 Godot import cache。
- [ ] `git grep` 中出现的示例 key 只是明确占位符，不是真实凭据。
- [ ] `git archive --format=tar HEAD` 的文件列表与源码交付范围一致。
- [ ] 保存 source archive 的 SHA-256，并记录候选 commit、规则/存档/事件/仿真 schema。
- [ ] README、backend README、COMMANDS、V4 roadmap 与本清单指向同一版本事实。

## 7. 封版前签署

- [ ] 自动 CI：Ubuntu 通过者、时间、run URL 已记录。
- [ ] 自动 CI：macOS 通过者、时间、run URL 已记录。
- [ ] macOS 手工验收：执行者、时间、工具版本已记录。
- [ ] Linux 手工或 headless 支持范围：执行者、时间、结论已记录。
- [ ] 隐私/发布物检查：执行者、时间、结论已记录。
- [ ] 用户已确认最终 commit 和许可证选择，并批准创建正式 `v4.0.0` tag 与 tag push。

## 8. 未来人工封版步骤

公开开发仓库和 `v4-origin` 已存在。以下正式封版命令现在禁止执行；只有第 1–7 节
全部完成且用户再次明确批准后，才逐条执行：

```bash
git switch v4-development
git status --short
git merge-base --is-ancestor v3.0.0 HEAD
git rev-parse HEAD

git remote get-url v4-origin
git tag -a v4.0.0 -m "Agent Town Demo V4.0.0" HEAD

git push v4-origin refs/heads/v4-development:refs/heads/main
git push v4-origin refs/tags/v4.0.0:refs/tags/v4.0.0
```

不得使用不带 remote 名称的 `git push`，不得使用 `git push --all`、`git push --tags`、
`git push --mirror` 或任何 `--force`。正式封版 push 后只读反查：

```bash
git rev-parse HEAD
git rev-parse 'v4.0.0^{}'
git ls-remote v4-origin refs/heads/main refs/tags/v4.0.0 'refs/tags/v4.0.0^{}'
```

HEAD、annotated tag 解引用和远端 `main` 必须指向同一提交。随后在新仓库启用 main
branch protection，并把 CI 设为必需检查。

## 9. 回滚与补丁

一旦公开，`v4.0.0` 不移动、不删除、不 force-push。发现问题时保留证据，在修复分支
验证后发布 `v4.0.1`。如需暂时运行旧版本，先复制并隔离 `backend/data/games`；旧程序
不得直接打开或覆盖新版私有存档目录。
