# ArXiv Physics Digest (Agentic Skill)

这是一个专为物理研究人员设计的 **arXiv 论文自动追踪与简报系统**。它最初是作为 `Gemini CLI` 的一个自定义技能（Skill）开发的，旨在通过代理（Agent）自动化日常科研情报的搜集工作。

## 🌟 核心功能
- **自动抓取**：每日自动从 arXiv 获取最新的凝聚态物理 (cond-mat) 论文。
- **智能筛选**：基于自定义关键词（如：非常规超导体、重费米子、拓扑、机器学习等）进行全文扫描。
- **邮件推送**：利用 AppleScript 驱动 macOS Mail 应用自动发送格式整齐的每日汇总。
- **轻量化**：完全基于 Python 标准库，无需安装复杂的第三方依赖。

## 📂 项目结构
- `scripts/digest.py`: 核心逻辑脚本（抓取、筛选、发送）。
- `references/config.json`: 配置文件（关键词、收件人列表）。
- `SKILL.md`: Gemini CLI 技能定义文件。

## 🚀 快速开始

### 1. 配置
编辑 `references/config.json`，设置您的研究兴趣和接收邮箱：
```json
{
  "keywords": ["topology", "superconductors"],
  "recipients": ["your-email@example.com"]
}
```

### 2. 手动运行
```bash
python3 scripts/digest.py
```

### 3. 设置定时任务 (macOS)
在终端输入 `crontab -e` 并添加以下内容以实现每天早上 9 点自动运行：
```bash
0 9 * * * /usr/bin/python3 /绝对路径/to/arxiv-physics-digest/scripts/digest.py
```

## 🤖 作为 Gemini CLI 技能使用
如果您安装了 [Gemini CLI](https://github.com/google/gemini-cli)，您可以直接将其作为技能加载，从而通过自然语言与之交互。

```bash
gemini skills install arxiv-physics-digest.skill --scope user
```

## 📄 开源协议
MIT
