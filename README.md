# ArxivReading Agent

Track new arXiv papers from a chosen RSS category, filter them by keywords, and send yourself a daily digest by email.

The default use case is `cond-mat`, but the script works with any arXiv RSS category such as `hep-th`, `cs.LG`, or `math.PR`.

## Features

- Fetch the latest feed from `https://rss.arxiv.org/rss/<category>`.
- Match papers by keywords in title and abstract.
- Send a plain-text digest by SMTP.
- Fall back to macOS Mail + AppleScript if SMTP is not configured.
- Optionally download matched PDFs and render a formatted digest with Typst.
- Optionally extract the first useful paper figure with `PyMuPDF`.
- Include an offline sample RSS file and a safe self-check script.

## Quick Start

1. Clone the repository and enter it.

```bash
git clone https://github.com/qiuzhuolun/ArxivReading-agent.git
cd ArxivReading-agent
```

2. Create a Python environment and install the optional Python dependency.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

3. Copy the config template.

```bash
cp references/config.example.json references/config.json
```

4. Run the offline self-check. This does not fetch live data and does not send email.

```bash
python3 scripts/test_pdf.py
```

5. Run a live text-only test.

```bash
python3 scripts/digest.py --skip-email --skip-pdf --max-papers 3
```

6. When the output looks right, enable email sending.

```bash
python3 scripts/digest.py
```

## Platform Support

- Cross-platform: RSS fetching, keyword filtering, SMTP email sending, text-only mode.
- Cross-platform with extra tools: Typst PDF rendering and `PyMuPDF` image extraction.
- macOS-only: Mail.app fallback via `osascript`, password lookup via Keychain `security`.

If you want the most portable setup, use SMTP and keep Mail.app fallback disabled.

## Installation Notes

Required:

- `python3` 3.9+

Optional:

- `PyMuPDF` for extracting the first figure from matched paper PDFs
- `typst` for generating a formatted PDF digest

Install Typst separately if you want PDF output:

```bash
brew install typst
```

## Configuration

`references/config.json` is ignored by Git and safe to keep local.

Start from the template:

```bash
cp references/config.example.json references/config.json
```

Example full config:

```json
{
  "keywords": ["quantum materials", "spin liquid", "machine learning"],
  "recipients": ["your-email@example.com"],
  "category": "cond-mat",
  "smtp": {
    "host": "smtp.example.com",
    "port": 465,
    "username": "your-account@example.com",
    "sender": "your-account@example.com",
    "sender_name": "ArxivReading Agent",
    "password_env": "ARXIV_DIGEST_SMTP_PASSWORD",
    "use_ssl": true,
    "starttls": false
  }
}
```

Example minimal config for `--smtp-only`:

```json
{
  "recipients": ["your-email@example.com"],
  "smtp": {
    "host": "smtp.example.com",
    "port": 465,
    "username": "your-account@example.com",
    "sender": "your-account@example.com",
    "password_env": "ARXIV_DIGEST_SMTP_PASSWORD",
    "use_ssl": true
  }
}
```

Important fields:

- `keywords`: keyword list matched against title and abstract
- `recipients`: recipient email addresses
- `category`: arXiv RSS category, for example `cond-mat` or `cs.LG`
- `smtp.password_env`: read the SMTP password from an environment variable
- `smtp.password_keychain_server`: read the password from macOS Keychain

Security notes:

- Prefer `smtp.password_env` or `smtp.password_keychain_server`.
- Do not commit SMTP passwords into Git.
- `references/config.json` is already in `.gitignore`.

## Common Commands

Offline self-check:

```bash
python3 scripts/test_pdf.py
```

Offline digest test with bundled sample RSS:

```bash
python3 scripts/digest.py --rss-file assets/sample_rss.xml --skip-email --skip-pdf
```

Live fetch, no email, no PDF:

```bash
python3 scripts/digest.py --skip-email --skip-pdf --max-papers 3
```

SMTP connectivity test only:

```bash
python3 scripts/digest.py --smtp-only
```

Verbose SMTP diagnostics:

```bash
python3 scripts/digest.py --smtp-debug --debug-log /tmp/arxiv_smtp_debug.log
```

## Scheduling

Example `cron` entry for daily execution at `08:30`:

```bash
30 8 * * * PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin /absolute/path/to/python3 /absolute/path/to/ArxivReading-agent/scripts/digest.py >> /absolute/path/to/ArxivReading-agent/log.txt 2>&1
```

Operational notes:

- The machine must be awake and online at the scheduled time.
- Do not enable both `cron` and `launchd` unless you want duplicate sends.
- If delivery fails, inspect `log.txt` and any `--smtp-debug` output.

## Repository Layout

- `scripts/digest.py`: main entry point
- `scripts/test_pdf.py`: safe self-check
- `references/config.example.json`: starter config
- `assets/sample_rss.xml`: offline sample feed
- `SKILL.md`: Codex skill metadata, not required for normal use

## License

This project is released under the MIT License. See `LICENSE`.
