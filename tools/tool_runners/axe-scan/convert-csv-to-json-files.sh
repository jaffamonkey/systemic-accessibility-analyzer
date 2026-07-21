set -euo pipefail

mkdir -p reports

python3 - <<'PY'
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

INPUT_FILE = "axe-results.csv"
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

def make_slug(raw_url):
    if not raw_url:
        raw_url = "__missing_url__"

    slug = raw_url.strip()

    slug = re.sub(r"^https?://", "", slug, flags=re.I)
    slug = re.sub(r"\?.*$", "", slug)

    # Split fragment off so we can simplify it
    base, frag = (slug.split("#", 1) + [""])[:2]

    base = re.sub(r"/index\.(html?|php|asp|aspx)$", "", base, flags=re.I)
    base = re.sub(r"/$", "", base)

    if frag:
        frag = re.sub(r"^intid=", "", frag, flags=re.I)

        # Optional tidy-up for M&S nav fragments
        frag = re.sub(r"^gnav_LEVEL1_COMPONENT_", "", frag, flags=re.I)

        slug = f"{base}-{frag}"
    else:
        slug = base

    slug = slug.replace("/", "-")
    slug = re.sub(r"[^a-zA-Z0-9._-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")

    return slug or "__empty_slug__"

grouped = defaultdict(list)

with open(INPUT_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        raw_url = row.get("URL") or "__missing_url__"
        row["URL"] = raw_url

        slug = make_slug(raw_url)
        grouped[slug].append(row)


for slug, rows in grouped.items():
    output_file = REPORT_DIR / f"{slug}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"Wrote {output_file} ({len(rows)} rows)")
PY