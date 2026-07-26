"""
Axe-Scan Runner

Executes the Axe-Scan CLI tool. Evaluates target URLs, executes the scan 
using the local node_modules installation, and converts the resulting 
CSV output into standard JSON reports for the analysis engine.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
import re


def _safe_slug(url: str) -> str:
    return (
        str(url or "")
        .replace("http://", "")
        .replace("https://", "")
        .strip()
    ).rstrip("/")


def _report_slug(url: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", _safe_slug(url))
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _load_clean_urls(src: Path) -> list[str]:
    return [
        line.strip()
        for line in src.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _check_slug_collisions(urls: list[str]) -> dict[str, list[str]]:
    collisions: dict[str, list[str]] = {}
    seen: dict[str, list[str]] = {}

    for url in urls:
        slug = _report_slug(url)
        seen.setdefault(slug, []).append(url)

    for slug, slug_urls in seen.items():
        if len(slug_urls) > 1:
            collisions[slug] = slug_urls

    return collisions


def _load_job_config(job_dir: Path) -> dict:
    candidates = [
        job_dir / "incoming_job_config.json",
        job_dir / "input" / "job_config.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _job_requires_auth(cfg: dict) -> bool:
    login_entry_url = str(cfg.get("login_entry_url") or "").strip()

    credentials = cfg.get("credentials") or {}
    username = str(credentials.get("username") or "").strip()
    password = str(credentials.get("password") or "").strip()

    return bool(login_entry_url or username or password)


def _resolve_runner_dir() -> Path:
    env_dir = os.environ.get("AXE_SCAN_REPO_DIR")
    if env_dir:
        path = Path(env_dir).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"AXE_SCAN_REPO_DIR does not exist: {path}")
        return path

    default = Path(__file__).resolve().parents[1] / "tool_runners" / "axe-scan"
    if not default.exists():
        raise FileNotFoundError(
            f"Could not find axe-scan repo at: {default}. "
            "Set AXE_SCAN_REPO_DIR to the correct folder."
        )
    return default.resolve()


def _find_axe_scan_command(runner_dir: Path) -> list[str]:
    """
    Locates the axe-scan executable. 
    Prefers the local node_modules installation in the runner directory 
    to ensure version stability, falling back to a global install if necessary.
    """
    local_bin = runner_dir / "node_modules" / ".bin" / "axe-scan"
    if local_bin.exists():
        return [str(local_bin), "run"]

    # Fallback to global installations
    exe = shutil.which("axe-scan")
    if exe:
        return [exe, "run"]

    npx = shutil.which("npx")
    if npx:
        return [npx, "axe-scan", "run"]

    raise FileNotFoundError(
        "Could not find local 'axe-scan' in node_modules, nor globally via 'npx'. "
        "Ensure you have run 'npm install' inside the tool_runners/axe-scan directory."
    )


def _normalize_urls_file(src: Path, dst: Path) -> list[str]:
    clean_urls = _load_clean_urls(src)
    dst.write_text("\n".join(clean_urls), encoding="utf-8")
    return clean_urls


def run_axe_scan(job_dir: Path) -> None:
    job_dir = job_dir.resolve()

    reports_dir = job_dir / "reports" / "axe-scan"
    logs_dir = job_dir / "logs"
    work_dir = job_dir / "tool_work" / "axe-scan"

    reports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / "axe-scan.log"
    skipped_marker = reports_dir / "SKIPPED"

    job_cfg = _load_job_config(job_dir)
    
    # Axe-scan does not support complex playwright authentication
    if _job_requires_auth(job_cfg):
        skipped_marker.write_text(
            "axe-scan skipped because this job requires authentication.\n",
            encoding="utf-8",
        )
        return

    runner_dir = _resolve_runner_dir()
    urls_src = job_dir / "input" / "urls.txt"
    urls_dst = work_dir / "urls.txt"

    if not urls_src.exists():
        raise FileNotFoundError(f"urls.txt not found: {urls_src}")

    clean_urls = _normalize_urls_file(urls_src, urls_dst)
    url_count = len(clean_urls)

    if url_count == 0:
        raise RuntimeError(f"axe-scan received no valid URLs from: {urls_src}")

    collisions = _check_slug_collisions(clean_urls)
    if collisions:
        collision_lines = []
        for slug, urls in collisions.items():
            collision_lines.append(f"{slug}: {urls}")
        raise RuntimeError(
            "axe-scan URL slug collisions detected. These URLs would overwrite each other:\n"
            + "\n".join(collision_lines)
        )

    config_src = runner_dir / "axe-scan.config.json"
    converter_src = runner_dir / "convert-csv-to-json-files.sh"

    if not config_src.exists():
        raise FileNotFoundError(f"Missing axe-scan.config.json in {runner_dir}")
    if not converter_src.exists():
        raise FileNotFoundError(f"Missing convert-csv-to-json-files.sh in {runner_dir}")

    shutil.copy2(config_src, work_dir / "axe-scan.config.json")
    shutil.copy2(converter_src, work_dir / "convert-csv-to-json-files.sh")

    os.chmod(work_dir / "convert-csv-to-json-files.sh", 0o755)

    # Clear previous generated artifacts in the work dir
    for old_json in work_dir.rglob("*.json"):
        if old_json.name != "axe-scan.config.json":
            old_json.unlink(missing_ok=True)
            
    csv_path = work_dir / "axe-results.csv"
    csv_path.unlink(missing_ok=True)

    axe_scan_cmd = _find_axe_scan_command(runner_dir)

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"Running axe-scan in {work_dir}\n")
        fh.write(f"Using runner dir: {runner_dir}\n")
        fh.write(f"Normalized URL count: {url_count}\n")
        fh.write(f"Command: {' '.join(axe_scan_cmd)}\n")

        with csv_path.open("w", encoding="utf-8") as csv_fh:
            result = subprocess.run(
                axe_scan_cmd,
                cwd=str(work_dir),
                check=False,
                stdout=csv_fh,
                stderr=fh,
                text=True,
            )

        fh.write(f"axe-scan exit code: {result.returncode}\n")

        if result.returncode != 0:
            raise RuntimeError(f"axe-scan run failed with exit code {result.returncode}")

        convert_result = subprocess.run(
            ["bash", "convert-csv-to-json-files.sh"],
            cwd=str(work_dir),
            check=False,
            stdout=fh,
            stderr=fh,
            text=True,
        )

        fh.write(f"converter exit code: {convert_result.returncode}\n")

        if convert_result.returncode != 0:
            raise RuntimeError(
                f"convert-csv-to-json-files.sh failed with exit code {convert_result.returncode}"
            )

        report_jsons = [
            p for p in sorted((work_dir / "reports").glob("*.json"))
            if p.name != "axe-scan.config.json"
        ]

        fh.write("JSON candidates after conversion:\n")
        for candidate in report_jsons:
            fh.write(f"  {candidate}\n")

        fh.write(f"Converted JSON report count: {len(report_jsons)}\n")
        fh.write(f"Expected URL count: {url_count}\n")

        if len(report_jsons) == 0:
            raise RuntimeError(
                f"axe-scan completed but produced no JSON reports under {work_dir}. "
                f"Check {log_path} and inspect the converter output."
            )

        if len(report_jsons) < url_count:
            raise RuntimeError(
                f"axe-scan produced only {len(report_jsons)} JSON report(s) for {url_count} URL(s). "
                f"Check {log_path} and the raw CSV output for skipped or stalled pages."
            )

    copied = 0
    for json_file in report_jsons:
        shutil.copy2(json_file, reports_dir / json_file.name)
        copied += 1

    if csv_path.exists():
        shutil.copy2(csv_path, reports_dir / csv_path.name)