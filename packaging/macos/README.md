# Agent Town Demo V5 macOS 试玩包

源码构建命令：

```bash
backend/.venv/bin/pip install -r backend/requirements-packaging.txt
scripts/package_macos.sh
```

需要 Godot `4.7.stable` 与同版本 Export Templates。模板可通过
`Editor → Manage Export Templates` 安装。

## 启动

双击 `启动 Agent Town Demo.command`。启动器会先运行内置 FastAPI 后端，通过健康检查后
再打开 Godot 游戏；退出游戏时，由本启动器创建的后端进程会一起退出。

首次运行如果 macOS 阻止未知开发者应用，可在 Finder 中按住 Control 点击启动器，
选择“打开”。这是未使用 Apple Developer ID 公证的本地测试包，不是 App Store 包。

## 默认行为

- 支持 Apple Silicon Mac；Godot 客户端是 Universal 2，内置 Python 后端为 arm64。
- 默认关闭真实 LLM 与向量模型下载，使用规则文案和关键词 RAG，断网也可游玩。
- 默认 NPC 策略为 `local`（夜间信念置信度门禁 + 本地模型评分，已通过 30 局金丝雀）；
  可通过 `.env` 的 `AGENT_TOWN_NPC_POLICY_MODE` 改回 `rule`。
- 存档、居民记忆和后端日志写入
  `~/Library/Application Support/Agent Town Demo/`，不写入应用包。

## 可选 DeepSeek

复制 `配置示例.env` 为同目录的 `.env`，填写 `LLM_BASE_URL`、`LLM_API_KEY` 和
`LLM_MODEL`，并把 `ENABLE_LLM` 改为 `true`。API Key 只保存在本机 `.env`，不要分享
或放进 zip。修改配置后退出并重新启动游戏。

## 手动排错

- 后端日志：`~/Library/Application Support/Agent Town Demo/backend.log`
- 健康检查：`http://127.0.0.1:8000/api/health`
- 游戏固定连接本机 `127.0.0.1:8000`；如果该端口被其他程序占用，请先退出占用进程。
