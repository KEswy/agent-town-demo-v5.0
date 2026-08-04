# Agent Town Demo V5 Windows x64 试玩包

## 启动

解压完整 ZIP 后，双击 `Start Agent Town Demo.bat`。不要只移动游戏 EXE：同目录的
`backend/`、PowerShell 启动器和配置文件都是运行所需内容。

启动器会运行包内便携 Python 后端，等待 `http://127.0.0.1:8000/api/health` 通过后
打开游戏；退出游戏后，由启动器创建的后端进程会一起退出。玩家不需要安装 Python、
Godot 或 pip。

## 默认行为

- 支持 64 位 Windows 10/11。
- 默认关闭真实 LLM 与向量模型下载，使用规则文案和关键词 RAG，断网可玩。
- 默认 NPC 策略为 `local`（夜间信念置信度门禁 + 本地模型评分，已通过 30 局金丝雀）；
  可通过 `.env` 的 `AGENT_TOWN_NPC_POLICY_MODE` 改回 `rule`。
- 存档、居民记忆和后端日志写入
  `%LOCALAPPDATA%\Agent Town Demo\`，不写入游戏目录。

## 可选 DeepSeek

复制 `配置示例.env` 为同目录的 `.env`，填写自己的 `LLM_BASE_URL`、`LLM_API_KEY`
和 `LLM_MODEL`，再把 `ENABLE_LLM` 改为 `true`。不要分享填写过 API Key 的 `.env`。

## 安全提示

当前是未购买代码签名证书的开发测试包，Windows SmartScreen 可能提示“未知发布者”。
请只从可信发送者处接收，并先核对同目录 SHA-256。公开分发前应使用受信代码签名证书
签署 EXE，并在真实 Windows 10/11 上完成图形交互验收。

## 源码构建

macOS/Linux 安装 Godot 4.7 Windows x86_64 Export Templates 后，在项目根目录运行：

```bash
scripts/package_windows.sh
```

若模板不在 Godot 默认目录，可通过 `AGENT_TOWN_GODOT_TEMPLATE_DIR` 指向
`4.7.stable` 模板目录。
