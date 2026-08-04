# 发布与上架指南（macOS 公证 / Windows 签名 / itch.io）

## 1. macOS 公证（需要付费 Apple Developer 账号）

1. 在 [developer.apple.com](https://developer.apple.com) 创建 **Developer ID Application** 证书并导出到钥匙串。
2. 配置 notarytool 凭据（只做一次）：
   ```bash
   xcrun notarytool store-credentials agent-town \
     --apple-id "你的AppleID" --team-id "TEAMID" --password "app专用密码"
   ```
3. 带身份与公证配置打包：
   ```bash
   AGENT_TOWN_CODESIGN_IDENTITY="Developer ID Application: 你的名字 (TEAMID)" \
   AGENT_TOWN_NOTARY_PROFILE=agent-town \
   scripts/package_macos.sh
   ```
4. 验证：`codesign --verify --deep --strict` 与 `spctl -a -vv` 均应通过。

## 2. Windows Authenticode 签名（需要代码签名证书）

在 Windows 构建机（或 macOS 装 osslsigncode）上：

```bash
AGENT_TOWN_WINDOWS_CERT=/path/to/cert.pfx \
AGENT_TOWN_WINDOWS_CERT_PASSWORD=证书密码 \
scripts/package_windows.sh
```

脚本会自动使用 `signtool`（Windows）或 `osslsigncode`（macOS）签名 EXE；
两都没有时会跳过并打印警告。

## 3. itch.io 页面文案（可直接使用）

**标题**：Agent Town Demo —— 会"骗人"的 AI 狼人杀

**一句话**：在 2D 小镇里与 11 名有性格的 AI 角色来一局完整的十二人狼人杀；他们会被骗、会撒谎、会记仇，也会记住你。

**简介**：
Agent Town Demo 是一个 Godot 4 + Python FastAPI 的 AI NPC 原型。你在扩建后的小镇里自由移动，和两名常驻居民聊天，也可以开一局 1 名玩家 + 11 名 NPC 的十二人狼人杀。每个 NPC 都维护自己的合法视野与信念：好人会推理也会被骗，狼人会悍跳、倒钩、卖队友，还会记住你私聊说过的话。

- 🧠 本地策略模型驱动 NPC 决策（放逐、警长、归票、夜技），断网可玩
- 💬 可选 DeepSeek 让发言更鲜活，离线也有逐角色开场白与口头禅
- 📖 内置规则百科、角色档案、战绩与成就
- 🎬 赛后复盘：本局高光、决策解释与逐步重播
- 💾 三槽位存档，随时保存/继续

**标签建议**：werewolf、mafia、ai、npc、godot、chinese、strategy、social-deduction

**上传内容**：
- macOS：`dist/AgentTownDemo-V5-macOS-arm64.zip`（需先完成公证）
- Windows：`dist/AgentTownDemo-V5-Windows-x64.zip`（需先完成签名）
- 封面：建议 630×500 的城镇全景截图；缩略图 315×250

## 4. 注意事项

- 公证/签名只影响 Gatekeeper/SmartScreen 拦截；未签名版本本地试玩不受影响。
- 发布前建议在未注册的 Windows 10/11 真机完整跑通启动与一局流程。
