import urllib.request
import xml.etree.ElementTree as ET
import json
import subprocess
import os
import sys
from datetime import datetime

def main():
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '../references/config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 1. Fetch from arXiv RSS (New for 2026 data)
    print(f"正在从 RSS 抓取 {config['category']} 的最新论文...")
    url = f"https://rss.arxiv.org/rss/{config['category']}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"抓取失败: {e}")
        return

    # 2. Parse and Filter (RSS 2.0 format)
    root = ET.fromstring(xml_data)
    matched_papers = []
    
    # RSS 2.0 使用 item 标签
    items = root.findall('.//item')
    print(f"本次共获取到 {len(items)} 条最新论文。")
    
    for item in items:
        # RSS 的 title 通常包含 "Title: " 前缀，我们将其移除
        raw_title = item.find('title').text if item.find('title') is not None else ""
        title = raw_title.replace('Title: ', '').strip()
        
        # RSS 的 description 通常包含摘要
        summary = item.find('description').text if item.find('description') is not None else ""
        link = item.find('link').text if item.find('link') is not None else ""
        
        # 关键词匹配
        matched = [k for k in config['keywords'] if k.lower() in (title + summary).lower()]
        if matched:
            matched_papers.append({"title": title, "summary": summary, "link": link, "keywords": matched})

    if not matched_papers:
        print("今日没有发现与关键词相关的论文。")
        return

    # 3. Generate Report Text
    today_str = datetime.now().strftime('%Y-%m-%d')
    report = f"arXiv 每日物理论文简报 ({today_str})\n"
    report += "=" * 40 + "\n"
    report += f"在今日发布的 {len(items)} 篇论文中为您筛选出以下内容：\n\n"
    
    for idx, p in enumerate(matched_papers):
        report += f"[{idx+1}] {p['title']}\n"
        report += f"   链接: {p['link']}\n"
        report += f"   匹配关键词: {', '.join(p['keywords'])}\n"
        # 摘要在 RSS 中可能包含 HTML 标签或冗余信息，这里保持原样或进行简单清理
        report += f"   摘要: {p['summary']}\n"
        report += "-" * 40 + "\n\n"

    # 4. Send via AppleScript
    print(f"正在发送至 {', '.join(config['recipients'])}...")
    subject = f"【arXiv Daily】今日凝聚态物理精华 ({len(matched_papers)} 篇)"
    
    # 转义 AppleScript 特殊字符
    content_escaped = report.replace('\\', '\\\\').replace('"', '\\"')
    subject_escaped = subject.replace('\\', '\\\\').replace('"', '\\"')
    
    recipients_commands = ""
    for r in config['recipients']:
        recipients_commands += f'make new to recipient at end of to recipients with properties {{address:"{r}"}}\n'
        
    applescript = f'''
    tell application "Mail"
        set newMessage to make new outgoing message with properties {{subject:"{subject_escaped}", content:"{content_escaped}", visible:true}}
        tell newMessage
            {recipients_commands}
            send
        end tell
    end tell
    '''
    
    with open('/tmp/send_mail.scpt', 'w') as f:
        f.write(applescript)
    
    result = subprocess.run(['osascript', '/tmp/send_mail.scpt'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 邮件已排队发送。")
    else:
        print(f"❌ 发送失败: {result.stderr}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
