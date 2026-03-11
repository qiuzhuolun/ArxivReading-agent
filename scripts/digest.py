import xml.etree.ElementTree as ET
import json
import subprocess
import os
import fitz  # PyMuPDF
from datetime import datetime
import re
import requests

def get_first_image(pdf_path, output_image_path):
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            image_list = page.get_images(full=True)
            if image_list:
                for img in image_list:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    width = base_image["width"]
                    height = base_image["height"]
                    ext = base_image["ext"]
                    
                    if width > 150 and height > 150:
                        img_path = f"{output_image_path}.{ext}"
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)
                        doc.close()
                        return img_path
        doc.close()
    except Exception as e:
        print(f"Error extracting image from {pdf_path}: {e}")
    return None

def escape_typst(text):
    if not text:
        return ""
    text = re.sub('<[^<]+>', '', text)
    # Remove standard arXiv announcement prefix from the abstract if present
    text = re.sub(r'arXiv:\d+\.\d+v\d+\s+Announce Type:.*?Abstract:\s*', '', text)
    # Escape Typst special characters
    return text.replace('\\', r'\\').replace('#', r'\#').replace('$', r'\$').replace('*', r'\*').replace('_', r'\_').replace('&', r'\&')

def main():
    config_path = os.path.join(os.path.dirname(__file__), '../references/config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    url = f"https://rss.arxiv.org/rss/{config['category']}"
    print(f"正在从 RSS 抓取 {config['category']} 的最新论文...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        xml_data = response.content
    except Exception as e:
        print(f"抓取失败: {e}")
        return

    root = ET.fromstring(xml_data)
    items = root.findall('.//item')
    print(f"本次共获取到 {len(items)} 条最新论文。")
    
    matched_papers = []
    
    for item in items:
        raw_title = item.find('title').text if item.find('title') is not None else ""
        title = raw_title.replace('Title: ', '').strip()
        summary = item.find('description').text if item.find('description') is not None else ""
        link = item.find('link').text if item.find('link') is not None else ""
        
        matched = [k for k in config['keywords'] if k.lower() in (title + summary).lower()]
        if matched:
            matched_papers.append({
                "title": title, 
                "summary": summary, 
                "link": link, 
                "keywords": matched
            })

    if not matched_papers:
        print("今日没有发现与关键词相关的论文。")
        return

    # PDF & Image Processing Directory
    work_dir = "/tmp/arxiv_digest"
    os.makedirs(work_dir, exist_ok=True)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Generate Typst content
    typst_content = f'''
#set page(
  margin: (x: 1.5in, y: 1.2in),
  numbering: "1",
)
#set text(size: 11pt)
#set par(justify: true, leading: 0.65em)

#align(center)[
  #text(size: 24pt, weight: "bold")[arXiv 论文速递 (物理)]
  
  #v(1em)
  #text(size: 14pt)[{today_str}]
]

#v(3em)
'''

    report_text = f"arXiv 每日物理论文简报 ({today_str})\n"
    report_text += "=" * 40 + "\n"
    report_text += f"在今日发布的 {len(items)} 篇论文中为您筛选出 {len(matched_papers)} 篇内容：\n\n"

    for idx, p in enumerate(matched_papers):
        print(f"处理论文 {idx+1}/{len(matched_papers)}: {p['title']}")
        
        report_text += f"[{idx+1}] {p['title']}\n"
        report_text += f"   链接: {p['link']}\n"
        report_text += f"   匹配关键词: {', '.join(p['keywords'])}\n"
        report_text += "-" * 40 + "\n\n"
        
        pdf_url = p['link'].replace('/abs/', '/pdf/')
        pdf_path = os.path.join(work_dir, f"paper_{idx}.pdf")
        img_base_path = os.path.join(work_dir, f"img_{idx}")
        
        img_path = None
        try:
            print(f"下载 PDF: {pdf_url}")
            pdf_response = requests.get(pdf_url, headers=headers, timeout=60)
            if pdf_response.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_response.content)
                img_path = get_first_image(pdf_path, img_base_path)
        except Exception as e:
            print(f"下载或处理 PDF 失败: {e}")

        typst_content += f'''
== {escape_typst(p['title'])}

*Keywords:* {escape_typst(', '.join(p['keywords']))} \\
*Link:* #link("{p['link']}")

'''
        if img_path:
            img_filename = os.path.basename(img_path)
            typst_content += f'''
#align(center)[
  #box(height: 35%, image("{img_filename}", fit: "contain"))
]
'''
        else:
            typst_content += f"\n#align(center)[*(No suitable image found)*]\n"

        typst_content += f'''
*Abstract:*
#v(0.5em)
{escape_typst(p['summary'])}

#pagebreak()
'''

    typst_file = os.path.join(work_dir, "report.typ")
    with open(typst_file, "w", encoding='utf-8') as f:
        f.write(typst_content)
    
    pdf_output = os.path.join(work_dir, f"arXiv_Digest_{today_str}.pdf")
    print("正在编译最终 PDF 排版...")
    subprocess.run(["typst", "compile", typst_file, pdf_output], cwd=work_dir)
    
    if not os.path.exists(pdf_output):
        print("❌ PDF 编译失败。")
        return

    # Send Email via AppleScript
    print(f"正在发送至 {', '.join(config['recipients'])}...")
    subject = f"【arXiv 杂志版】今日凝聚态物理精华 ({len(matched_papers)} 篇)"
    
    content_escaped = report_text.replace('\\', '\\\\').replace('"', '\\"')
    subject_escaped = subject.replace('\\', '\\\\').replace('"', '\\"')
    
    recipients_commands = ""
    for r in config['recipients']:
        recipients_commands += f'make new to recipient at end of to recipients with properties {{address:"{r}"}}\n'
        
    applescript = f'''
    tell application "Mail"
        set newMessage to make new outgoing message with properties {{subject:"{subject_escaped}", content:"{content_escaped}\\n\\n请查看随附的 PDF 杂志版简报获取图片预览。\\n", visible:true}}
        tell newMessage
            {recipients_commands}
            make new attachment with properties {{file name:POSIX file "{pdf_output}"}} at after the last paragraph
            send
        end tell
    end tell
    '''
    
    scpt_path = os.path.join(work_dir, 'send_mail.scpt')
    with open(scpt_path, 'w', encoding='utf-8') as f:
        f.write(applescript)
    
    result = subprocess.run(['osascript', scpt_path], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 杂志版简报已成功发送！")
    else:
        print(f"❌ 发送失败: {result.stderr}")

if __name__ == "__main__":
    main()
