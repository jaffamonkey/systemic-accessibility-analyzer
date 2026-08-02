set -euo pipefail

mkdir -p reports

python3 - <<'PY'
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

INPUT_FILE = "axe-results.csv"
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

def make_slug(raw_url):
    if not raw_url:
        return "__missing_url__"

    raw_url = raw_url.strip()

    # Ensure protocol is present so urlparse extracts netloc/path correctly
    target_url = raw_url if re.match(r"^https?://", raw_url, re.I) else f"https://{raw_url}"
    parsed = urlparse(target_url)

    netloc = parsed.netloc
    path = re.sub(r"/index\.(html?|php|asp|aspx)$", "", parsed.path, flags=re.I)
    query = parsed.query
    frag = parsed.fragment

    # Optional custom fragment tidy-up
    if frag:
        frag = re.sub(r"^intid=", "", frag, flags=re.I)
        frag = re.sub(r"^gnav_LEVEL1_COMPONENT_", "", frag, flags=re.I)

    # Combine all parts (netloc, path, query, fragment)
    full_str = f"{netloc}{path}{query}{frag}"

    # Standardize: replace special characters with dashes, collapse consecutive dashes, and trim ends
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", full_str)
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