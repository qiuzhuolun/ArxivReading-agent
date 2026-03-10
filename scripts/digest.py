import urllib.request
import xml.etree.ElementTree as ET
import json
import subprocess
import os
import sys

def main():
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '../references/config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 1. Fetch from arXiv
    print(f"正在抓取 {config['category']} 的最新论文...")
    url = f"http://export.arxiv.org/api/query?search_query=cat:{config['category']}&sortBy=submittedDate&sortOrder=descending&max_results=100"
    with urllib.request.urlopen(url) as response:
        xml_data = response.read()

    # 2. Parse and Filter
    root = ET.fromstring(xml_data)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    matched_papers = []
    
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
        summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
        link = entry.find('atom:id', ns).text.strip()
        
        matched = [k for k in config['keywords'] if k.lower() in (title + summary).lower()]
        if matched:
            matched_papers.append({"title": title, "summary": summary, "link": link, "keywords": matched})

    if not matched_papers:
        print("今天没有发现与关键词相关的论文。")
        return

    # 3. Generate Report Text (包含摘要版)
    report = "arXiv 每日物理论文简报 (由 AI 生成)\n"
    report += "=" * 40 + "\n\n"
    
    for idx, p in enumerate(matched_papers):
        report += f"[{idx+1}] {p['title']}\n"
        report += f"   链接: {p['link']}\n"
        report += f"   匹配关键词: {', '.join(p['keywords'])}\n"
        report += f"   摘要: {p['summary']}\n"
        report += "-" * 40 + "\n\n"

    # 4. Send via AppleScript
    print(f"正在发送至 {', '.join(config['recipients'])}...")
    subject = "【arXiv Daily】今日凝聚态物理精华"
    content = report.replace('"', '\\"') # Escape quotes for AppleScript
    
    recipients_commands = ""
    for r in config['recipients']:
        recipients_commands += f'make new to recipient at end of to recipients with properties {{address:"{r}"}}\n'
        
    applescript = f'''
    tell application "Mail"
        set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{content}", visible:true}}
        tell newMessage
            {recipients_commands}
            send
        end tell
    end tell
    '''
    
    # Write to a temp script to execute safely
    with open('/tmp/send_mail.scpt', 'w') as f:
        f.write(applescript)
    
    subprocess.run(['osascript', '/tmp/send_mail.scpt'])
    print("✅ 发送指令已执行。")

if __name__ == "__main__":
    main()
