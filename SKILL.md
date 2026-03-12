---
name: arxiv-physics-digest
description: 抓取 arXiv 的 cond-mat RSS，按关键词筛选论文并生成每日简报；可选生成 Typst PDF 和首图预览，并通过 macOS Mail 自动发送。用户提到“arXiv 每日追踪/论文简报/关键词筛选/自动邮件推送”时使用。
---

# arXiv Physics Digest

按下面流程执行：

1. 复制 `references/config.example.json` 为 `references/config.json`，再设置 `keywords`、`recipients`、`category`。
2. 运行 `python3 scripts/digest.py` 生成并发送简报。
3. 若仅做测试，运行无副作用模式：`python3 scripts/digest.py --skip-email --skip-pdf`。

## 关键命令

- 正常运行：
```bash
python3 scripts/digest.py
```

- 离线自检（无需网络、不会发邮件）：
```bash
python3 scripts/test_pdf.py
```

- 使用本地 RSS 文件调试：
```bash
python3 scripts/digest.py --rss-file assets/sample_rss.xml --skip-email --skip-pdf
```

## 定时任务示例（每天 08:30）

```bash
30 8 * * * PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin /absolute/path/to/python3 /absolute/path/to/arxiv-physics-digest/scripts/digest.py >> /absolute/path/to/arxiv-physics-digest/log.txt 2>&1
```

## 依赖与降级行为

- 必需：`python3`。
- 可选：`typst`（生成 PDF）。未安装时自动跳过 PDF。
- 可选：`PyMuPDF` (`fitz`)（从 PDF 提取首图）。未安装时 PDF 仍可生成，但不含提取图。
- 发送邮件优先使用 SMTP；未配置 SMTP 时可回退到 macOS Mail + `osascript`。
