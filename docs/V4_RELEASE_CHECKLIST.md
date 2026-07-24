# Agent Town Demo V4 源码封版记录

## 当前状态与范围

V4 已由用户在 `2026-07-24` 批准结束开发，并归档到公开源码仓库
[`KEswy/agent-town-demo-v4.0`](https://github.com/KEswy/agent-town-demo-v4.0)
的不可移动注解标签 `v4.0.0`。V4 只通过专用 `v4-origin` 发布；历史 `origin`、
`v2-origin`、`v3-origin` 没有接收 V4 代码或标签。

V4.0.0 的归档范围是源码与自动化基线。当前没有 `export_presets.cfg`，因此不承诺
Linux 或 macOS 可执行包；第 4 节未勾选的桌面人工项目保留为明确的非声明范围，不被
自动 CI 冒充。根目录没有项目 LICENSE，本次封版继续记录为“未授予再分发许可”，
不能从字体的 `OFL.txt` 推断项目许可。

## 1. 仓库治理门禁

- [x] 已获得用户对“结束 V4、开始 V5 并创建封版 tag”的单独明确批准。
- [x] 当前分支是 `v4-development`，且没有指向历史 remote 的 upstream。
- [x] `v3.0.0^{}` 精确等于 V3 基线
  `7a44dd598a62739e450bebe56198a6fe1f505ebd`，并且是候选提交的祖先。
- [x] `origin`、`v2-origin`、`v3-origin` 仍只作为历史只读来源；没有执行任何针对它们
  的 push、force-push、mirror 或 tag push。
- [x] `v4-origin` 只指向公开开发仓库，不是任何历史仓库。
- [x] `v4.0.0` 只在最终候选提交 CI 全绿后创建，并且不得移动。

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

- [x] 候选提交树与发布范围一致；除明确排除的未跟踪 `3.0总结/` 外，没有意外
  工作区改动。不要使用 `git add .`。
- [x] 当前开发快照排除并保留未跟踪的 `3.0总结/`，没有删除本地历史资料。
- [x] V4.0.0 源码归档继续排除 `3.0总结/`。
- [x] Godot 的 `.gd.uid` 已跟踪，`game/.godot/` 仍被忽略。
- [x] 没有意外大文件、开发者绝对路径、临时补丁、调试输出或未解释的生成文件。
- [x] `.env`、`backend/data/`、游戏存档、数据库、向量缓存、`.godot/`、虚拟环境、
  `__pycache__` 和 `*.pyc` 均未进入候选提交。
- [x] 字体文件与 `game/assets/fonts/OFL.txt` 同时存在。
- [x] 当前开发快照记录为没有项目 LICENSE、未授予再分发许可。
- [x] V4.0.0 继续采用无项目 LICENSE、未授予再分发许可的状态。

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

- [x] Linux 两个 job 通过。
- [x] macOS 两个 job 通过。
- [x] `git diff --check` 通过，测试后 tracked files 没有变化。
- [x] GitHub fresh checkout、fresh dependency install 与分层 smoke 通过。

## 4. 手工桌面验收

FastAPI 和 Godot 由验收者手动启动，使用隔离的空存档目录。至少检查：

V4.0.0 是源码归档，不是桌面发行包。下列未勾选项目没有被自动测试替代；尤其只声明
“Linux headless/后端已验证，Linux 图形交互为候选支持”。

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

- [x] source archive 中没有 `.env`、API Key、带凭据 URL、私聊原文、隐藏身份存档、
  `backend/data/`、LLM 原文日志、数据库、向量模型缓存或 Godot import cache。
- [x] `git grep` 中出现的示例 key 只是明确占位符，不是真实凭据。
- [x] `git archive --format=tar HEAD` 的文件列表与源码交付范围一致。
- [x] 候选 commit、规则/存档/事件/仿真 schema 可由 tag 和版本化输出反查。
- [x] README、backend README、COMMANDS、V4 roadmap 与本记录指向同一版本事实。

## 7. 封版前签署

- [x] 自动 CI：最终候选提交的 Ubuntu 两项通过，run URL 可从 tag commit checks 反查。
- [x] 自动 CI：最终候选提交的 macOS 两项通过，run URL 可从 tag commit checks 反查。
- [ ] macOS 手工验收：执行者、时间、工具版本已记录。
- [x] Linux 支持范围记录为 headless/后端已验证，图形交互为候选支持。
- [x] 隐私/发布物检查已完成，排除项与许可证边界已记录。
- [x] 用户已确认结束 V4、继续无项目 LICENSE，并批准 `v4.0.0` tag 与 tag push。

## 8. 已执行的源码封版步骤

公开源码仓库和 `v4-origin` 已存在。最终候选提交的自动门禁通过后，逐条执行：

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
