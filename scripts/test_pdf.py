import urllib.request
import xml.etree.ElementTree as ET
import json
import subprocess
import os
import fitz  # PyMuPDF
from datetime import datetime
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

def get_first_image(pdf_path, output_image_path):
    print(f"Opening PDF: {pdf_path}")
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
                
                # Filter out tiny logos and small icons
                if width > 150 and height > 150:
                    img_path = f"{output_image_path}.{ext}"
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"Extracted image on page {i+1} ({width}x{height})")
                    doc.close()
                    return img_path
    doc.close()
    return None

def main():
    config_path = os.path.join(os.path.dirname(__file__), '../references/config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    import requests
    url = f"https://rss.arxiv.org/rss/{config['category']}"
    print(f"Fetching RSS: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers)
    xml_data = response.content

    root = ET.fromstring(xml_data)
    items = root.findall('.//item')
    
    matched_paper = None
    for item in items:
        raw_title = item.find('title').text if item.find('title') is not None else ""
        title = raw_title.replace('Title: ', '').strip()
        summary = item.find('description').text if item.find('description') is not None else ""
        link = item.find('link').text if item.find('link') is not None else ""
        
        matched = [k for k in config['keywords'] if k.lower() in (title + summary).lower()]
        if matched:
            matched_paper = {"title": title, "summary": summary, "link": link, "keywords": matched}
            break

    if not matched_paper:
        print("今日没有发现与关键词相关的论文，无法进行测试。")
        return

    print(f"Selected Paper: {matched_paper['title']}")
    
    # Download PDF
    pdf_url = matched_paper['link'].replace('/abs/', '/pdf/')
    pdf_path = "/tmp/test_paper.pdf"
    print(f"Downloading PDF from: {pdf_url}")
    pdf_response = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'})
    with open(pdf_path, 'wb') as f:
        f.write(pdf_response.content)
    
    # Extract Image
    img_path = get_first_image(pdf_path, "/tmp/test_paper_img")
    
    # Generate Typst content
    typst_content = f'''
#set page(margin: 1.5in)

#align(center)[
  #text(size: 20pt, weight: "bold")[arXiv Paper Digest Test]
]

#v(2em)

== {matched_paper['title']}

*Keywords:* {', '.join(matched_paper['keywords'])}

*Link:* #link("{matched_paper['link']}")

'''
    if img_path:
        img_filename = os.path.basename(img_path)
        typst_content += f'''
#align(center)[
  #image("{img_filename}", width: 80%)
]
'''
    else:
        typst_content += f"\n*(No suitable image found in the first few pages)*\n"

    # Try to clean up HTML tags in summary
    import re
    clean_summary = re.sub('<[^<]+>', '', matched_paper['summary'])
    # Escape typst special chars in summary
    clean_summary = clean_summary.replace('#', r'\#').replace('$', r'\$').replace('*', r'\*').replace('_', r'\_')

    typst_content += f'''
*Abstract:*
{clean_summary}
'''

    typst_file = "/tmp/test_report.typ"
    with open(typst_file, "w") as f:
        f.write(typst_content)
    
    # Compile Typst
    pdf_output = "/tmp/test_report.pdf"
    print("Compiling PDF...")
    subprocess.run(["typst", "compile", typst_file, pdf_output])
    
    if os.path.exists(pdf_output):
        print(f"PDF generated at {pdf_output}")
        # Send Email via AppleScript
        subject = f"【测试】arXiv 杂志版附图测试"
        content_escaped = "这是一封带有排版精美的 PDF 附件（包含论文首图）的测试邮件，请查看附件！"
        
        applescript = f'''
        tell application "Mail"
            set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{content_escaped}", visible:true}}
            tell newMessage
                make new to recipient at end of to recipients with properties {{address:"zhuolunqiu@gmail.com"}}
                make new attachment with properties {{file name:POSIX file "{pdf_output}"}} at after the last paragraph
                send
            end tell
        end tell
        '''
        script_path = '/tmp/test_send_mail.scpt'
        with open(script_path, 'w') as f:
            f.write(applescript)
        
        result = subprocess.run(['osascript', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 测试邮件 (带 PDF 附件) 已发送。")
        else:
            print(f"❌ 发送失败: {result.stderr}")

if __name__ == "__main__":
    main()
