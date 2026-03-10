---
name: arxiv-physics-digest
description: 自动抓取 arXiv 凝聚态物理分类的最新论文，并根据“超导体”、“拓扑”等关键词筛选、总结，最后通过 macOS Mail 应用发送每日简报给指定邮箱。
---

# arXiv Physics Digest 技能

这个技能模仿了 `labAgent` 的工作流，专为物理研究人员提供每日论文情报。

## 核心功能
1. **自动抓取**: 访问 arXiv API 获取凝聚态物理 (cond-mat) 的最新论文。
2. **关键词匹配**: 基于 `references/config.json` 中的关键词进行全文筛选。
3. **邮件分发**: 自动调用 macOS 的 Mail 应用发送汇总报告。

## 如何使用

### 1. 手动生成简报
如果您想现在就获取一份简报，可以运行：
```bash
python3 scripts/digest.py
```

### 2. 修改搜索关键词或收件人
编辑 `references/config.json` 文件：
- `keywords`: 添加或删除您关注的研究方向（如 "Majorana", "Superconductivity"）。
- `recipients`: 在数组中添加多个邮箱地址。

### 3. 设置定时发送 (每天早上 9 点)
在终端输入 `crontab -e`，并添加以下行：
```bash
0 9 * * * /usr/bin/python3 /Users/qiuzhuolun/arxiv-physics-digest/scripts/digest.py >> /Users/qiuzhuolun/arxiv-physics-digest/log.txt 2>&1
```

## 依赖
- 需要 macOS 系统。
- 需要在“邮件”应用中配置好发件账户。
- 无需第三方 Python 库，使用标准库运行。
