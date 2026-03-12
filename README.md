# ArXiv Physics Digest

用于自动追踪 arXiv `cond-mat` 分类、按关键词筛选并发送每日简报。

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
    "sender_name": "arXiv Digest",
    "password_env": "ARXIV_DIGEST_SMTP_PASSWORD",
    "use_ssl": true,
    "starttls": false
  }
}
```

说明：

- `references/config.json` 已加入 `.gitignore`，不会提交到仓库。
- 建议优先使用 `smtp.password_env` 或 `smtp.password_keychain_server`，不要把授权码直接写进 Git 版本库。

## 使用

- 正常运行：
```bash
python3 scripts/digest.py
```

- 只生成文本流程（不发邮件、不生成 PDF）：
```bash
python3 scripts/digest.py --skip-email --skip-pdf
```

- 使用本地 RSS 离线测试：
```bash
python3 scripts/digest.py --rss-file assets/sample_rss.xml --skip-email --skip-pdf
```

- 执行项目自检：
```bash
python3 scripts/test_pdf.py
```

## 定时任务（macOS，示例为每天 08:30）

```bash
30 8 * * * PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin /absolute/path/to/python3 /absolute/path/to/arxiv-physics-digest/scripts/digest.py >> /absolute/path/to/arxiv-physics-digest/log.txt 2>&1
```
