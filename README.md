# ArxivReading Agent

`ArxivReading Agent` 是这个仓库的项目名，技能标识保持为 `arxiv-physics-digest`。

用于自动追踪 arXiv `cond-mat` 分类，按关键词筛选论文，并通过文本邮件或带附件 PDF 的形式发送每日简报。

## 功能

- 从 `https://rss.arxiv.org/rss/<category>` 抓取最新 RSS。
- 根据标题和摘要中的关键词筛选论文。
- 可选下载论文 PDF，并用 `PyMuPDF` 提取首张合适图片。
- 可选用 `Typst` 生成排版后的 PDF 简报。
- 优先使用 SMTP 发送邮件；未配置 SMTP 时可回退到 macOS Mail + AppleScript。
- 提供离线样例 RSS 和自检脚本，便于无副作用调试。

## 项目结构

- `scripts/digest.py`: 主流程（抓取 RSS、筛选、可选生成 PDF、可选发邮件）
- `scripts/test_pdf.py`: 安全自检脚本（默认离线、不会发邮件）
- `references/config.example.json`: 配置模板
- `assets/sample_rss.xml`: 离线测试用 RSS 样例
- `SKILL.md`: skill 使用说明

## 依赖

- 必需：`python3`
- 可选：`typst`（用于生成 PDF）
- 可选：`PyMuPDF`（Python 包名 `PyMuPDF`，模块名 `fitz`，用于提取论文首图）
- 可选：macOS Mail（未配置 SMTP 时可回退到 AppleScript 发送）

安装可选依赖示例：

```bash
python3 -m pip install PyMuPDF
brew install typst
```

## 配置

先复制模板：

```bash
cp references/config.example.json references/config.json
```

然后编辑 `references/config.json`：

```json
{
  "keywords": ["topological superconductors", "machine learning"],
  "recipients": ["your-email@example.com"],
  "category": "cond-mat",
  "smtp": {
    "host": "smtp.qq.com",
    "port": 465,
    "username": "your-account@qq.com",
    "sender": "your-account@qq.com",
    "sender_name": "ArxivReading Agent",
    "password_env": "ARXIV_DIGEST_SMTP_PASSWORD",
    "use_ssl": true,
    "starttls": false
  }
}
```

说明：

- `references/config.json` 已加入 `.gitignore`，不会提交到仓库。
- 建议优先使用 `smtp.password_env` 或 `smtp.password_keychain_server`，不要把授权码直接写进 Git 版本库。
- 如果没有 `smtp` 配置，脚本会尝试通过 macOS `Mail` 应用发送。

常用配置项：

- `keywords`: 用于匹配标题和摘要的关键词列表。
- `recipients`: 收件人邮箱列表。
- `category`: RSS 分类，当前默认使用 `cond-mat`。
- `smtp.password_env`: 从环境变量读取 SMTP 授权码。
- `smtp.password_keychain_server`: 从 macOS Keychain 读取互联网密码。

## 使用

- 正常运行：
```bash
python3 scripts/digest.py
```

- 只生成文本流程（不发邮件、不生成 PDF）：
```bash
python3 scripts/digest.py --skip-email --skip-pdf
```

- 正常抓取，但只测试 SMTP 发信：
```bash
python3 scripts/digest.py --smtp-only
```

- 开启 SMTP 调试日志：
```bash
python3 scripts/digest.py --smtp-debug --debug-log /tmp/arxiv_smtp_debug.log
```

- 使用本地 RSS 离线测试：
```bash
python3 scripts/digest.py --rss-file assets/sample_rss.xml --skip-email --skip-pdf
```

- 限制本次最多处理 3 篇论文：
```bash
python3 scripts/digest.py --max-papers 3
```

- 执行项目自检：
```bash
python3 scripts/test_pdf.py
```

脚本参数摘要：

- `--config`: 指定配置文件路径。
- `--rss-file`: 使用本地 RSS 文件调试。
- `--output-dir`: 指定工作目录，默认 `/tmp/arxiv_digest`。
- `--skip-pdf`: 跳过 PDF 下载、图片提取和 Typst 渲染。
- `--skip-email`: 跳过邮件发送。
- `--smtp-only`: 仅发送 SMTP 测试邮件。
- `--smtp-debug`: 生成 SMTP 诊断日志。
- `--debug-log`: 显式指定诊断日志路径。
- `--max-papers`: 限制处理的匹配论文数量。

## 定时任务

`cron` 示例，表示每天 `08:30` 运行：

```bash
30 8 * * * PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin /absolute/path/to/python3 /absolute/path/to/ArxivReading-agent/scripts/digest.py >> /absolute/path/to/ArxivReading-agent/log.txt 2>&1
```

注意：

- 到点时机器需要处于唤醒状态并联网。
- 如果同时启用 `cron` 和 `launchd`，可能会重复发信。
- 若某天没有收到邮件，先查看 `log.txt` 和 `--smtp-debug` 生成的诊断日志。
