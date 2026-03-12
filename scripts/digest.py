import argparse
import html
import json
import mimetypes
import os
import platform
import re
import smtplib
import socket
import ssl
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from shutil import which
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = "arxiv-physics-digest/1.1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "config.json"


class RunLogger:
    def __init__(self, path=None):
        self.path = path
        self.handle = open(path, "a", encoding="utf-8") if path else None

    def log(self, message):
        print(message)
        if self.handle:
            self.handle.write(f"{message}\n")
            self.handle.flush()

    def close(self):
        if self.handle:
            self.handle.close()
            self.handle = None


def strip_html_tags(text):
    return re.sub(r"<[^<]+?>", "", text or "")


def clean_summary(text):
    cleaned = html.unescape(strip_html_tags(text))
    cleaned = re.sub(r"arXiv:\d+\.\d+v\d+\s+Announce Type:.*?Abstract:\s*", "", cleaned)
    return cleaned.strip()


def escape_typst(text):
    if not text:
        return ""
    escaped = text
    replacements = {
        "\\": r"\\",
        "#": r"\#",
        "$": r"\$",
        "*": r"\*",
        "_": r"\_",
        "&": r"\&",
    }
    for src, dst in replacements.items():
        escaped = escaped.replace(src, dst)
    return escaped


def mask_secret(secret, visible=4):
    if not secret:
        return "(empty)"
    if len(secret) <= visible * 2:
        return "*" * len(secret)
    return f"{secret[:visible]}...{secret[-visible:]}"


def format_exception(exc):
    return "".join(traceback.format_exception_only(type(exc), exc)).strip()


def log_dns_resolution(host, logger):
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = sorted({info[4][0] for info in infos})
        logger.log(f"[SMTP] DNS 解析 {host}: {', '.join(addresses)}")
        return addresses
    except socket.gaierror as exc:
        logger.log(f"[SMTP] DNS 解析失败: {format_exception(exc)}")
        return []


def probe_tcp_endpoint(host, port, timeout, logger):
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            elapsed = time.monotonic() - started
            logger.log(
                f"[SMTP] TCP 连接成功: local={sock.getsockname()} peer={sock.getpeername()} elapsed={elapsed:.2f}s"
            )
            return True
    except OSError as exc:
        logger.log(f"[SMTP] TCP 连接失败: {format_exception(exc)}")
        return False


def probe_ssl_endpoint(host, port, timeout, logger):
    started = time.monotonic()
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw_sock:
            with context.wrap_socket(raw_sock, server_hostname=host) as tls_sock:
                elapsed = time.monotonic() - started
                logger.log(
                    "[SMTP] SSL 握手成功: "
                    f"version={tls_sock.version()} cipher={tls_sock.cipher()} elapsed={elapsed:.2f}s"
                )
                return True
    except OSError as exc:
        logger.log(f"[SMTP] SSL 握手失败: {format_exception(exc)}")
        return False


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required = ["keywords", "recipients", "category"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"配置文件缺少字段: {', '.join(missing)}")

    if not isinstance(config["keywords"], list) or not all(isinstance(k, str) for k in config["keywords"]):
        raise ValueError("`keywords` 必须是字符串数组")

    if not isinstance(config["recipients"], list) or not all(isinstance(r, str) for r in config["recipients"]):
        raise ValueError("`recipients` 必须是字符串数组")

    if not isinstance(config["category"], str) or not config["category"].strip():
        raise ValueError("`category` 必须是非空字符串")

    smtp = config.get("smtp")
    if smtp is not None:
        if not isinstance(smtp, dict):
            raise ValueError("`smtp` 必须是对象")
        required_smtp = ["host", "port", "username"]
        missing_smtp = [k for k in required_smtp if k not in smtp]
        if missing_smtp:
            raise ValueError(f"`smtp` 缺少字段: {', '.join(missing_smtp)}")
        if not isinstance(smtp["host"], str) or not smtp["host"].strip():
            raise ValueError("`smtp.host` 必须是非空字符串")
        if not isinstance(smtp["port"], int) or smtp["port"] <= 0:
            raise ValueError("`smtp.port` 必须是正整数")
        if not isinstance(smtp["username"], str) or not smtp["username"].strip():
            raise ValueError("`smtp.username` 必须是非空字符串")

    return config


def fetch_bytes(url, timeout=30):
    req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_first_image(pdf_path, output_image_base, fitz_module):
    try:
        doc = fitz_module.open(pdf_path)
        for page in doc:
            image_list = page.get_images(full=True)
            if not image_list:
                continue

            for image in image_list:
                xref = image[0]
                extracted = doc.extract_image(xref)
                width = extracted.get("width", 0)
                height = extracted.get("height", 0)
                ext = extracted.get("ext", "png")

                # Filter tiny icons/logos.
                if width <= 150 or height <= 150:
                    continue

                out_path = f"{output_image_base}.{ext}"
                with open(out_path, "wb") as f:
                    f.write(extracted["image"])
                doc.close()
                return out_path

        doc.close()
    except Exception as exc:
        print(f"提取图片失败: {exc}")

    return None


def build_typst_header(today_str):
    return f'''
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


def escape_applescript_text(text):
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return escaped.replace("\n", "\\n")


def send_mail(recipients, subject, body_text, attachment_path=None):
    if which("osascript") is None:
        print("未找到 osascript，跳过邮件发送。")
        return False

    command = ["osascript"]
    if which("launchctl") is not None:
        command = ["launchctl", "asuser", str(os.getuid()), "osascript"]

    recipients_commands = []
    for r in recipients:
        safe_addr = r.replace("\\", "\\\\").replace('"', '\\"')
        recipients_commands.append(
            f'make new to recipient at end of to recipients with properties {{address:"{safe_addr}"}}'
        )
    recipients_block = "\n            ".join(recipients_commands)

    attachment_command = ""
    if attachment_path:
        safe_file = attachment_path.replace("\\", "\\\\").replace('"', '\\"')
        attachment_command = (
            f'make new attachment with properties {{file name:POSIX file "{safe_file}"}} '
            "at after the last paragraph"
        )

    subject_escaped = escape_applescript_text(subject)
    body_escaped = escape_applescript_text(body_text)

    applescript = f'''
    tell application "Mail"
        set newMessage to make new outgoing message with properties {{subject:"{subject_escaped}", content:"{body_escaped}", visible:false}}
        tell newMessage
            {recipients_block}
            {attachment_command}
            send
        end tell
    end tell
    '''

    result = subprocess.run(command + ["-e", applescript], capture_output=True, text=True)
    if result.returncode == 0:
        return True

    print(f"邮件发送失败: {result.stderr.strip()}")
    return False


def read_keychain_internet_password(server, account):
    if which("security") is None:
        return None

    result = subprocess.run(
        ["security", "find-internet-password", "-s", server, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def resolve_smtp_password_with_source(smtp_config):
    password = smtp_config.get("password")
    if isinstance(password, str) and password:
        return password, "config.smtp.password"

    env_name = smtp_config.get("password_env")
    if isinstance(env_name, str) and env_name:
        env_value = os.getenv(env_name)
        if env_value:
            return env_value, f"env:{env_name}"

    keychain_server = smtp_config.get("password_keychain_server")
    if isinstance(keychain_server, str) and keychain_server:
        password = read_keychain_internet_password(keychain_server, smtp_config["username"])
        if password:
            return password, f"keychain:{keychain_server}"

    return None, None


def send_mail_smtp(recipients, subject, body_text, attachment_path, smtp_config, logger=None):
    logger = logger or RunLogger()
    password, password_source = resolve_smtp_password_with_source(smtp_config)
    if not password:
        logger.log("SMTP 密码未配置。请设置 `smtp.password`、`smtp.password_env` 或 `smtp.password_keychain_server`。")
        return False

    sender = smtp_config.get("sender", smtp_config["username"])
    sender_name = smtp_config.get("sender_name", "")
    use_ssl = smtp_config.get("use_ssl", smtp_config["port"] == 465)
    starttls = smtp_config.get("starttls", smtp_config["port"] == 587 and not use_ssl)
    timeout = smtp_config.get("timeout", 60)

    logger.log("[SMTP] 开始发送诊断")
    logger.log(f"[SMTP] host={smtp_config['host']} port={smtp_config['port']} use_ssl={use_ssl} starttls={starttls}")
    logger.log(f"[SMTP] username={smtp_config['username']} sender={sender} sender_name={sender_name or '(empty)'}")
    logger.log(f"[SMTP] recipients={', '.join(recipients)}")
    logger.log(f"[SMTP] password_source={password_source} password_masked={mask_secret(password)}")
    logger.log(f"[SMTP] python={platform.python_version()} platform={platform.platform()}")
    logger.log(f"[SMTP] cwd={Path.cwd()} uid={os.getuid()} pid={os.getpid()}")
    if attachment_path:
        attachment_file = Path(attachment_path)
        logger.log(
            f"[SMTP] attachment={attachment_file} exists={attachment_file.exists()} size={attachment_file.stat().st_size if attachment_file.exists() else 0}"
        )
    else:
        logger.log("[SMTP] attachment=(none)")

    log_dns_resolution(smtp_config["host"], logger)
    probe_tcp_endpoint(smtp_config["host"], smtp_config["port"], timeout, logger)
    if use_ssl:
        probe_ssl_endpoint(smtp_config["host"], smtp_config["port"], timeout, logger)

    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = ", ".join(recipients)
    message["From"] = f"{sender_name} <{sender}>" if sender_name else sender
    message.set_content(body_text)

    if attachment_path:
        attachment_file = Path(attachment_path)
        mime_type, _ = mimetypes.guess_type(str(attachment_file))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with open(attachment_file, "rb") as f:
            message.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment_file.name,
            )

    ssl_context = ssl.create_default_context()

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(
                smtp_config["host"],
                smtp_config["port"],
                timeout=timeout,
                context=ssl_context,
            ) as server:
                logger.log(f"[SMTP] CONNECT_SSL peer={server.sock.getpeername()!r}")
                code, resp = server.ehlo()
                logger.log(f"[SMTP] EHLO code={code} resp={resp!r}")
                code, resp = server.login(smtp_config["username"], password)
                logger.log(f"[SMTP] LOGIN code={code} resp={resp!r}")
                failures = server.send_message(message)
                logger.log(f"[SMTP] SEND failures={failures}")
                code, resp = server.noop()
                logger.log(f"[SMTP] NOOP code={code} resp={resp!r}")
        else:
            with smtplib.SMTP(timeout=timeout) as server:
                code, resp = server.connect(smtp_config["host"], smtp_config["port"])
                logger.log(f"[SMTP] CONNECT code={code} resp={resp!r}")
                code, resp = server.ehlo()
                logger.log(f"[SMTP] EHLO code={code} resp={resp!r}")
                if starttls:
                    code, resp = server.starttls(context=ssl_context)
                    logger.log(f"[SMTP] STARTTLS code={code} resp={resp!r}")
                    code, resp = server.ehlo()
                    logger.log(f"[SMTP] EHLO_AFTER_STARTTLS code={code} resp={resp!r}")
                code, resp = server.login(smtp_config["username"], password)
                logger.log(f"[SMTP] LOGIN code={code} resp={resp!r}")
                failures = server.send_message(message)
                logger.log(f"[SMTP] SEND failures={failures}")
                code, resp = server.noop()
                logger.log(f"[SMTP] NOOP code={code} resp={resp!r}")
        logger.log("[SMTP] SMTP 发送完成")
        return True
    except Exception as exc:
        logger.log(f"[SMTP] SMTP 发送失败: {format_exception(exc)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate and send arXiv physics digest.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to config.json",
    )
    parser.add_argument("--rss-file", help="Use local RSS file for offline testing")
    parser.add_argument("--output-dir", default="/tmp/arxiv_digest", help="Working directory")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF/image extraction and Typst rendering")
    parser.add_argument("--skip-email", action="store_true", help="Skip Mail sending")
    parser.add_argument("--smtp-only", action="store_true", help="Skip arXiv fetch/PDF and send an SMTP test email only")
    parser.add_argument("--smtp-debug", action="store_true", help="Write verbose SMTP diagnostics to a log file")
    parser.add_argument("--debug-log", help="Path to diagnostic log file")
    parser.add_argument("--max-papers", type=int, default=0, help="Limit number of matched papers (0 means no limit)")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(
            "读取配置失败: 未找到配置文件。请先复制 "
            "`references/config.example.json` 为 `references/config.json` 后再运行。"
        )
        return 1
    except Exception as exc:
        print(f"读取配置失败: {exc}")
        return 1

    work_dir = Path(args.output_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    debug_log = None
    if args.debug_log:
        debug_log = Path(args.debug_log).expanduser().resolve()
        debug_log.parent.mkdir(parents=True, exist_ok=True)
    elif args.smtp_debug or args.smtp_only:
        debug_log = work_dir / f"smtp_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    run_logger = RunLogger(str(debug_log) if debug_log else None)
    if debug_log:
        run_logger.log(f"[DEBUG] 日志文件: {debug_log}")
        run_logger.log(f"[DEBUG] 命令参数: {' '.join(os.sys.argv)}")

    if args.smtp_only:
        smtp_config = config.get("smtp")
        if not smtp_config:
            run_logger.log("未配置 `smtp`，无法执行 SMTP-only 测试。")
            run_logger.close()
            return 1

        subject = f"【SMTP 测试】ArxivReading Agent {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        body_lines = [
            "这是一封 SMTP 诊断测试邮件。",
            "",
            f"时间: {datetime.now().isoformat(timespec='seconds')}",
            f"主机: {platform.node()}",
            f"Python: {platform.python_version()}",
            f"平台: {platform.platform()}",
            "",
            "如果你收到这封邮件，说明 SMTP 基本可用。",
        ]
        run_logger.log("进入 SMTP-only 测试模式，不抓取 arXiv，不生成 PDF。")
        run_logger.log(f"正在发送邮件至: {', '.join(config['recipients'])}")
        success = send_mail_smtp(config["recipients"], subject, "\n".join(body_lines), None, smtp_config, logger=run_logger)
        if success:
            run_logger.log("SMTP-only 测试成功。")
            run_logger.close()
            return 0

        run_logger.log("SMTP-only 测试失败。")
        run_logger.close()
        return 1

    if args.rss_file:
        print(f"正在读取本地 RSS 文件: {args.rss_file}")
        try:
            with open(args.rss_file, "rb") as f:
                xml_data = f.read()
        except OSError as exc:
            print(f"读取 RSS 文件失败: {exc}")
            return 1
    else:
        rss_url = f"https://rss.arxiv.org/rss/{config['category']}"
        print(f"正在从 RSS 抓取 {config['category']} 的最新论文...")
        try:
            xml_data = fetch_bytes(rss_url, timeout=30)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"抓取失败: {exc}")
            return 1

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        print(f"RSS 解析失败: {exc}")
        return 1

    items = root.findall(".//item")
    print(f"本次共获取到 {len(items)} 条论文。")

    matched_papers = []
    for item in items:
        raw_title = item.findtext("title", default="")
        title = raw_title.replace("Title: ", "").strip()
        summary = clean_summary(item.findtext("description", default=""))
        link = item.findtext("link", default="").strip()

        combined_text = f"{title} {summary}".lower()
        matched = [k for k in config["keywords"] if k.lower() in combined_text]
        if matched:
            matched_papers.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "keywords": matched,
                }
            )

    if args.max_papers > 0:
        matched_papers = matched_papers[: args.max_papers]

    print(f"关键词筛选后得到 {len(matched_papers)} 篇论文。")

    if not matched_papers:
        print("今日没有发现与关键词相关的论文。")
        return 0

    today_str = datetime.now().strftime("%Y-%m-%d")

    report_text = [
        f"arXiv 每日物理论文简报 ({today_str})",
        "=" * 40,
        f"在今日发布的 {len(items)} 篇论文中筛选出 {len(matched_papers)} 篇：",
        "",
    ]

    should_render_pdf = not args.skip_pdf
    fitz_module = None
    if should_render_pdf and which("typst") is None:
        print("未检测到 typst，自动跳过 PDF 生成。")
        should_render_pdf = False

    if should_render_pdf:
        try:
            import fitz  # type: ignore

            fitz_module = fitz
        except ModuleNotFoundError:
            print("未安装 PyMuPDF(fitz)，将继续生成 PDF 但不提取论文图片。")

    typst_content = build_typst_header(today_str) if should_render_pdf else ""

    for idx, paper in enumerate(matched_papers, start=1):
        print(f"处理论文 {idx}/{len(matched_papers)}: {paper['title']}")

        report_text.append(f"[{idx}] {paper['title']}")
        report_text.append(f"链接: {paper['link']}")
        report_text.append(f"匹配关键词: {', '.join(paper['keywords'])}")
        report_text.append("")

        img_path = None
        if should_render_pdf and paper["link"]:
            pdf_url = paper["link"].replace("/abs/", "/pdf/")
            pdf_path = work_dir / f"paper_{idx}.pdf"
            img_base = work_dir / f"img_{idx}"
            try:
                pdf_bytes = fetch_bytes(pdf_url, timeout=60)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                if fitz_module is not None:
                    img_path = get_first_image(str(pdf_path), str(img_base), fitz_module)
            except Exception as exc:
                print(f"下载或处理 PDF 失败 ({paper['title']}): {exc}")

        if should_render_pdf:
            typst_content += f'''
== {escape_typst(paper['title'])}

*Keywords:* {escape_typst(', '.join(paper['keywords']))} \\
*Link:* #link("{paper['link']}")

'''
            if img_path:
                img_file = Path(img_path).name
                typst_content += f'''
#align(center)[
  #box(height: 35%, image("{img_file}", fit: "contain"))
]
'''
            else:
                typst_content += "\n#align(center)[*(No suitable image found)*]\n"

            typst_content += f'''
*Abstract:*
#v(0.5em)
{escape_typst(paper['summary'])}

#pagebreak()
'''

    report_body = "\n".join(report_text)
    pdf_output = None

    if should_render_pdf:
        typst_file = work_dir / "report.typ"
        with open(typst_file, "w", encoding="utf-8") as f:
            f.write(typst_content)

        pdf_path = work_dir / f"arXiv_Digest_{today_str}.pdf"
        print("正在编译 PDF 排版...")
        compile_result = subprocess.run(
            ["typst", "compile", str(typst_file), str(pdf_path)],
            capture_output=True,
            text=True,
            cwd=str(work_dir),
        )
        if compile_result.returncode == 0 and pdf_path.exists():
            pdf_output = str(pdf_path)
            print(f"PDF 已生成: {pdf_output}")
        else:
            print("PDF 编译失败，继续发送文本简报。")
            if compile_result.stderr.strip():
                print(compile_result.stderr.strip())

    if args.skip_email:
        print("已按参数跳过邮件发送。")
        return 0

    if not config["recipients"]:
        print("收件人列表为空，跳过邮件发送。")
        return 0

    subject = f"【arXiv 杂志版】今日凝聚态物理精华 ({len(matched_papers)} 篇)"
    mail_body = report_body
    if pdf_output:
        mail_body += "\n\n请查看附件 PDF 获取排版与图片预览。"

    print(f"正在发送邮件至: {', '.join(config['recipients'])}")
    smtp_config = config.get("smtp")
    if smtp_config:
        print(f"使用 SMTP 服务器: {smtp_config['host']}:{smtp_config['port']}")
        sent = send_mail_smtp(config["recipients"], subject, mail_body, pdf_output, smtp_config, logger=run_logger)
    else:
        sent = send_mail(config["recipients"], subject, mail_body, attachment_path=pdf_output)
    if sent:
        print("简报发送成功。")
        run_logger.close()
        return 0

    print("简报发送失败。")
    run_logger.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
