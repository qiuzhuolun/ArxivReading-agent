import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_self_check(live_mode=False, keep_pdf=False):
    repo_root = Path(__file__).resolve().parent.parent
    digest_script = repo_root / "scripts" / "digest.py"
    sample_rss = repo_root / "assets" / "sample_rss.xml"

    with tempfile.TemporaryDirectory(prefix="arxiv_digest_test_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        config_path = temp_dir_path / "config.json"
        output_dir = temp_dir_path / "out"

        config = {
            "keywords": ["superconductor", "topological superconductors", "machine learning"],
            "recipients": ["example@example.com"],
            "category": "cond-mat",
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

        cmd = [
            sys.executable,
            str(digest_script),
            "--config",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--skip-email",
            "--max-papers",
            "2",
        ]

        if not live_mode:
            cmd.extend(["--rss-file", str(sample_rss), "--skip-pdf"])
        elif not keep_pdf:
            cmd.append("--skip-pdf")

        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)

        print("----- stdout -----")
        print(result.stdout)
        print("----- stderr -----")
        print(result.stderr)
        print("------------------")

        if result.returncode != 0:
            print("Self-check failed: digest.py returned non-zero exit code.")
            return 1

        if "筛选后得到" not in result.stdout and "没有发现" not in result.stdout:
            print("Self-check failed: expected digest summary line not found.")
            return 1

        if not live_mode and "处理论文" not in result.stdout:
            print("Self-check failed: offline sample RSS did not produce matched papers.")
            return 1

        print("Self-check passed.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Safe self-check for arxiv-physics-digest")
    parser.add_argument("--live", action="store_true", help="Fetch live RSS instead of local sample")
    parser.add_argument("--keep-pdf", action="store_true", help="In live mode, keep PDF rendering enabled")
    args = parser.parse_args()

    return run_self_check(live_mode=args.live, keep_pdf=args.keep_pdf)


if __name__ == "__main__":
    raise SystemExit(main())
