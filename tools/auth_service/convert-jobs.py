#!/usr/bin/env python3

# Run it like this:
# python make_static_analysis_all.py /path/to/auth_service/jobs --zip
# That will turn:
# jobs/job-a/analysis
# jobs/job-b/analysis
# into:
# jobs/job-a/analysis-static
# jobs/job-b/analysis-static
# and also create:
# jobs/job-a/analysis-static.zip
# jobs/job-b/analysis-static.zip
# if you use --zip.

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path


TEXT_EXTENSIONS = {".html", ".htm", ".js", ".css", ".json", ".md", ".txt"}

LOCAL_URL_REPLACEMENTS = [
    (re.compile(r"https?://127\.0\.0\.1:\d+/readme_overview\.html", re.I), "readme_overview.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/workbook_guide\.html", re.I), "workbook_guide.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/dashboard_guide\.html", re.I), "dashboard_guide.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/site_preview\.html", re.I), "site_preview.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/virtual_screenreader\.html", re.I), "virtual_screenreader.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/tabbing_order\.html", re.I), "tabbing_order.html"),
]

JOB_DASHBOARD_RE = re.compile(
    r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/(?:dashboard|index\.html)?",
    re.I,
)

JOB_PAGE_REPLACEMENTS = [
    (re.compile(r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/site_preview\.html", re.I), "site_preview.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/virtual_screenreader\.html", re.I), "virtual_screenreader.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/tabbing_order\.html", re.I), "tabbing_order.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/readme_overview\.html", re.I), "readme_overview.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/workbook_guide\.html", re.I), "workbook_guide.html"),
    (re.compile(r"https?://127\.0\.0\.1:\d+/jobs/[^\"'\s<>]+/dashboard_guide\.html", re.I), "dashboard_guide.html"),
]


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def zip_folder(folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(folder))


def find_dashboard_filename(root: Path) -> str:
    if (root / "index.html").exists():
        return "index.html"
    return "index.html"


def make_relative_href(target_name: str, current_file: Path, root: Path) -> str:
    target = root / target_name
    rel = target.relative_to(current_file.parent)
    return str(rel).replace("\\", "/")


def rewrite_common_urls(text: str, dashboard_name: str) -> str:
    for pattern, replacement in LOCAL_URL_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    for pattern, replacement in JOB_PAGE_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    text = JOB_DASHBOARD_RE.sub(dashboard_name, text)

    text = re.sub(r'href="/static/', 'href="static/', text)
    text = re.sub(r"href='/static/", "href='static/", text)
    text = re.sub(r'src="/static/', 'src="static/', text)
    text = re.sub(r"src='/static/", "src='static/", text)
    text = re.sub(r'fetch\("/static/', 'fetch("static/', text)
    text = re.sub(r"fetch\('/static/", "fetch('static/", text)

    return text


def rewrite_page_links(text: str, current_file: Path, root: Path, dashboard_name: str) -> str:
    targets = {
        "readme_overview.html": make_relative_href("readme_overview.html", current_file, root) if (root / "readme_overview.html").exists() else "readme_overview.html",
        "workbook_guide.html": make_relative_href("workbook_guide.html", current_file, root) if (root / "workbook_guide.html").exists() else "workbook_guide.html",
        "dashboard_guide.html": make_relative_href("dashboard_guide.html", current_file, root) if (root / "dashboard_guide.html").exists() else "dashboard_guide.html",
        "site_preview.html": make_relative_href("site_preview.html", current_file, root) if (root / "site_preview.html").exists() else "site_preview.html",
        "virtual_screenreader.html": make_relative_href("virtual_screenreader.html", current_file, root) if (root / "virtual_screenreader.html").exists() else "virtual_screenreader.html",
        "tabbing_order.html": make_relative_href("tabbing_order.html", current_file, root) if (root / "tabbing_order.html").exists() else "tabbing_order.html",
        dashboard_name: make_relative_href(dashboard_name, current_file, root),
    }

    for page_name, rel_path in targets.items():
        text = re.sub(rf'href="{re.escape(page_name)}"', f'href="{rel_path}"', text)
        text = re.sub(rf"href='{re.escape(page_name)}'", f"href='{rel_path}'", text)

    text = re.sub(r'href="dashboard"', f'href="{targets[dashboard_name]}"', text)
    text = re.sub(r"href='dashboard'", f"href='{targets[dashboard_name]}'", text)
    text = re.sub(r'href="index\.html"', f'href="{targets[dashboard_name]}"', text)
    text = re.sub(r"href='index\.html'", f"href='{targets[dashboard_name]}'", text)

    js_targets = {
        "site_preview.html": targets.get("site_preview.html", "site_preview.html"),
        "virtual_screenreader.html": targets.get("virtual_screenreader.html", "virtual_screenreader.html"),
        "tabbing_order.html": targets.get("tabbing_order.html", "tabbing_order.html"),
        dashboard_name: targets[dashboard_name],
    }

    for page_name, rel_path in js_targets.items():
        text = re.sub(rf'(["\']){re.escape(page_name)}\1', f'"{rel_path}"', text)

    text = re.sub(r'(["\'])(?:dashboard|index\.html)\1', f'"{targets[dashboard_name]}"', text)

    return text


def patch_text_file(path: Path, root: Path, dashboard_name: str) -> None:
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return

    updated = original
    updated = rewrite_common_urls(updated, dashboard_name)
    updated = rewrite_page_links(updated, path, root, dashboard_name)

    updated = updated.replace(
        '// function updateSitePreviewLink(jobId) {\n    const link = document.getElementById("sitePreviewLink");\n    if (!link) return;\n    link.href = "site_preview.html";\n}',
        'function updateSitePreviewLink(jobId) {\n    const link = document.getElementById("sitePreviewLink");\n    if (!link) return;\n    link.href = "site_preview.html";\n}',
    )

    if updated != original:
        path.write_text(updated, encoding="utf-8")


def ensure_index_redirect(root: Path, dashboard_name: str) -> None:
    if dashboard_name == "index.html":
        return

    index_path = root / "index.html"
    if index_path.exists():
        return

    index_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={dashboard_name}">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Accessibility Analysis</title>
</head>
<body>
  <p>Redirecting to <a href="{dashboard_name}">{dashboard_name}</a>…</p>
</body>
</html>
""",
        encoding="utf-8",
    )


def process_analysis_folder(src: Path, dest: Path, make_zip: bool) -> tuple[Path, Path | None]:
    copy_tree(src, dest)

    dashboard_name = find_dashboard_filename(dest)

    for path in dest.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            patch_text_file(path, dest, dashboard_name)

    ensure_index_redirect(dest, dashboard_name)

    zip_path = None
    if make_zip:
        zip_path = dest.with_suffix(".zip")
        zip_folder(dest, zip_path)

    return dest, zip_path


def find_analysis_folders(jobs_root: Path) -> list[Path]:
    found = []
    for child in sorted(jobs_root.iterdir()):
        if not child.is_dir():
            continue
        analysis = child / "analysis"
        if analysis.exists() and analysis.is_dir():
            found.append(analysis)
    return found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert every job analysis folder in a jobs directory into a static-site-friendly copy."
    )
    parser.add_argument(
        "jobs_root",
        type=Path,
        help="Path to the jobs directory",
    )
    parser.add_argument(
        "--suffix",
        default="analysis-static",
        help="Name of the generated folder inside each job directory (default: analysis-static)",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also create a zip next to each generated folder",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jobs_root = args.jobs_root.resolve()

    if not jobs_root.exists() or not jobs_root.is_dir():
        raise SystemExit(f"Jobs root not found or is not a directory: {jobs_root}")

    analysis_folders = find_analysis_folders(jobs_root)
    if not analysis_folders:
        raise SystemExit(f"No analysis folders found under: {jobs_root}")

    print(f"Found {len(analysis_folders)} analysis folder(s).")

    for src in analysis_folders:
        job_dir = src.parent
        dest = job_dir / args.suffix
        out_dir, zip_path = process_analysis_folder(src, dest, args.zip)
        print(f"Created static folder: {out_dir}")
        if zip_path:
            print(f"Created zip: {zip_path}")


if __name__ == "__main__":
    main()