from pathlib import Path
import json
import re

from adapters import load_adapters
from adapters.registry import get_adapter
from services.wcag_mapper import ensure_wcag
from services.wcag_refs import WCAG_SUCCESS_CRITERIA, slugify_title
from analyzer.component_detector import detect_component
from services.bi_fields import (
    canonical_page_key,
    get_tool_family,
    get_tool_engine,
    get_engine_family_meta,
)


IGNORED_REPORT_FOLDERS = {"virtual-screenreader", "screenshots", "tab-map", "contrast-checker"}
IGNORED_REPORT_FILES = {"summary.json", "manifest.json", "index.json"}

# -------------------------
# RULE NORMALIZATION
# -------------------------
def normalize_rule(rule):
    if not rule:
        return ""

    rule = str(rule)

    match = re.search(r"(\d)_(\d)_(\d)", rule)
    if match:
        wcag = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
        tech_match = re.search(r"\.(G\d+|H\d+|ARIA\d+)", rule)
        return f"{wcag} [{tech_match.group(1)}]" if tech_match else wcag

    if "ColorContrast" in rule:
        return "1.4.3"

    return rule.lower()


# -------------------------
# KNOWN RULE -> WCAG ENRICHMENT
# -------------------------
KNOWN_RULE_WCAG_MAP = {
    "aria-allowed-role": ("4.1.2", "A"),
    "aria_descendant_valid": ("1.3.1", "A"),
    "aria-descendant-valid": ("1.3.1", "A"),
    "css-orientation-lock": ("1.3.4", "AA"),
    "focus-order-semantics": ("4.1.2", "A"),
    "style_focus_visible": ("2.4.7", "AA"),
    "style-focus-visible": ("2.4.7", "AA"),
    "text_sensory_misuse": ("1.3.3", "A"),
    "text-sensory-misuse": ("1.3.3", "A"),
    "widget_tabbable_single": ("2.1.1", "A"),
    "widget-tabbable-single": ("2.1.1", "A"),
}

SKIP_STRICT_WCAG_ENRICHMENT = {
    "element_tabbable_unobscured",
    "element-tabbable-unobscured",
    "hidden-content",
}


def _enrich_known_wcag_rules(row: dict) -> dict:
    rule_id = str(row.get("ruleId") or row.get("rule_id") or "").strip().lower()

    if not rule_id or rule_id in SKIP_STRICT_WCAG_ENRICHMENT:
        return row

    if not row.get("wcag") and rule_id in KNOWN_RULE_WCAG_MAP:
        wcag_code, wcag_level = KNOWN_RULE_WCAG_MAP[rule_id]
        row["wcag"] = wcag_code
        row["wcag_level"] = row.get("wcag_level") or wcag_level

    return row


def _hydrate_wcag_fields(row: dict) -> dict:
    row = _enrich_known_wcag_rules(row)

    if not row.get("wcag"):
        row["wcag"] = ensure_wcag(row)

    if row.get("wcag"):
        rule_code = str(row.get("wcag") or "").split()[0]
        wcag_ref = WCAG_SUCCESS_CRITERIA.get(rule_code)
        if wcag_ref:
            row["wcag_title"] = row.get("wcag_title") or wcag_ref["title"]
            row["wcag_level"] = row.get("wcag_level") or wcag_ref["level"]
            row["wcag_url"] = row.get("wcag_url") or wcag_ref["url"]

    return row


def _resolve_reports_root(folder):
    """Find the actual reports root containing tool subfolders."""
    base_path = Path(folder)
    if not base_path.exists():
        raise FileNotFoundError(f"Report folder not found: {folder}")

    def valid_tool_dirs(path):
        subdirs = [d for d in path.iterdir() if d.is_dir() and not d.name.startswith("__")]
        json_tool_dirs = [d for d in subdirs if any(d.glob("*.json"))]
        return subdirs, json_tool_dirs

    subdirs, json_tool_dirs = valid_tool_dirs(base_path)
    if json_tool_dirs:
        return base_path, json_tool_dirs

    # Common case: user points at project root and reports/ is one level below
    for child in subdirs:
        child_subdirs, child_json_tool_dirs = valid_tool_dirs(child)
        if child_json_tool_dirs:
            return child, child_json_tool_dirs

    return base_path, json_tool_dirs


# -------------------------
# MAIN LOADER
# -------------------------
def load_reports(folder):
    load_adapters()

    rows = []
    base_path, subfolders = _resolve_reports_root(folder)

    json_files = []
    if subfolders:
        for tool_folder in subfolders:
            if tool_folder.name in IGNORED_REPORT_FOLDERS:
                continue

            for file in sorted(tool_folder.glob("*.json")):
                if file.name.lower() in IGNORED_REPORT_FILES:
                    continue
                json_files.append((tool_folder.name, file))
    else:
        for file in sorted(base_path.glob("*.json")):
            if file.name.lower() in IGNORED_REPORT_FILES:
                continue
            json_files.append(("unknown", file))

    print("DISCOVERED REPORT FILES:")
    for dbg_tool_name, dbg_file in json_files:
        print(f"  {dbg_tool_name}: {dbg_file}")

    for tool_name, file in json_files:
        print(f"REPORT FILE: {file}")
        print(f"TOOL FOLDER: {tool_name}")

        with open(file, encoding="utf-8") as f:
            data = json.load(f)

        print("DATA TYPE:", type(data).__name__)
        if isinstance(data, list):
            print("LIST LEN:", len(data))
            if data:
                if isinstance(data[0], dict):
                    print("FIRST ITEM KEYS:", list(data[0].keys())[:20])
                else:
                    print("FIRST ITEM TYPE:", type(data[0]).__name__)
        elif isinstance(data, dict):
            print("DICT KEYS:", list(data.keys())[:20])

        adapter = get_adapter(data)
        print("ADAPTER:", adapter.__name__ if adapter else None)

        if not adapter:
            print("NO ADAPTER MATCHED")
            print()
            continue

        file_page = canonical_page_key(file.stem)
        results = adapter(str(file), data)
        print("ROW COUNT:", len(results))
        print()

        for result in results:
            if tool_name == "html-sniffer":
                result["source_detail"] = result.get("source")
                result["source"] = "html-sniffer"
            else:
                result["source"] = result.get("source") or tool_name
            result["tool_family"] = result.get("tool_family") or get_tool_family(result["source"])
            result["tool_engine"] = result.get("tool_engine") or get_tool_engine(result["source"])
            engine_meta = get_engine_family_meta(result["source"])
            result["engine_family"] = engine_meta["label"]
            result["engine_badge"] = engine_meta["badge"]
            result["engine_class"] = engine_meta["class"]
            page_key = canonical_page_key(
                file.stem,
                result.get("page"),
                result.get("url"),
                result.get("page_url"),
            )
            result["page"] = page_key or file_page
            result["page_id"] = result["page"]
            result["ruleId"] = normalize_rule(result.get("ruleId"))
            if not result.get("rule_name"):
                result["rule_name"] = result.get("rule") or result.get("title") or result.get("ruleId")
            result["component"] = detect_component(
                dom=result.get("dom"),
                selector=result.get("selector") or result.get("target"),
            )
            rows.append(_hydrate_wcag_fields(result))

    return rows


def _extract_page_candidate_from_data(data):
    """Best-effort extraction of a page/url-like identifier from raw report JSON."""
    seen = set()

    def walk(obj, depth=0):
        if depth > 4:
            return None
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_l = str(key).lower()
                if key_l in {"url", "page", "page_url", "document", "documenturl", "path", "filename", "file"}:
                    cand = canonical_page_key(value)
                    if cand:
                        return cand
                nested = walk(value, depth + 1)
                if nested:
                    return nested
        elif isinstance(obj, list):
            for item in obj[:10]:
                nested = walk(item, depth + 1)
                if nested:
                    return nested
        elif isinstance(obj, str):
            if obj in seen:
                return None
            seen.add(obj)
            cand = canonical_page_key(obj)
            if cand:
                return cand
        return None

    return walk(data)


def inspect_report_inventory(folder):
    """Build a page-inventory diagnostic from raw report files per tool folder."""
    load_adapters()

    base_path, subfolders = _resolve_reports_root(folder)
    if subfolders:
        subfolders = [
            tool_folder
            for tool_folder in subfolders
            if tool_folder.name not in IGNORED_REPORT_FOLDERS
        ]

    if not subfolders:
        return {
            "tools": [],
            "tools_count": 0,
            "total_distinct_pages": 0,
            "pages_present_in_all_tools": 0,
            "mismatched_pages": 0,
            "missing_reports_count": 0,
            "complete": True,
            "coverage_pct": 100,
            "page_rows": [],
            "tool_rows": [],
            "inventory_available": False,
            "status": "unavailable",
            "status_label": "Inventory data unavailable",
            "status_message": "No tool subfolders were found, so the inventory check could not run.",
        }

    tool_pages = {}
    for tool_folder in sorted(subfolders, key=lambda p: p.name.lower()):
        pages = set()

        for file in sorted(tool_folder.glob("*.json")):
            if file.name.lower() in IGNORED_REPORT_FILES:
                continue

            page_key = canonical_page_key(file.stem)
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)

                adapter = get_adapter(data)
                if adapter:
                    try:
                        results = adapter(str(file), data) or []
                    except Exception:
                        results = []

                    for result in results[:3]:
                        candidate = canonical_page_key(
                            file.stem,
                            result.get("page"),
                            result.get("url"),
                            result.get("page_url"),
                        )
                        if candidate:
                            page_key = candidate
                            break

                if not page_key:
                    page_key = _extract_page_candidate_from_data(data) or canonical_page_key(file.stem)

            except Exception:
                page_key = canonical_page_key(file.stem)

            if page_key:
                pages.add(page_key)

        tool_pages[tool_folder.name] = pages

    all_tools = sorted(tool_pages.keys())
    all_pages = sorted(set().union(*tool_pages.values()) if tool_pages else set())

    page_rows = []
    for page in all_pages:
        present_in = sorted([tool for tool, pages in tool_pages.items() if page in pages])
        missing_from = sorted([tool for tool in all_tools if tool not in present_in])
        page_rows.append({
            "page": page,
            "present_in": present_in,
            "missing_from": missing_from,
            "present_count": len(present_in),
            "missing_count": len(missing_from),
            "status": "complete" if not missing_from else ("partial" if present_in else "missing"),
        })

    tool_rows = []
    for tool in all_tools:
        pages = sorted(tool_pages.get(tool, set()))
        tool_rows.append({
            "tool": tool,
            "pages_count": len(pages),
            "pages": pages,
            "missing_pages_count": len([p for p in all_pages if p not in set(pages)]),
        })

    pages_present_in_all_tools = sum(1 for row in page_rows if not row["missing_from"])
    mismatched_pages = sum(1 for row in page_rows if row["missing_from"])
    missing_reports_count = sum(len(row["missing_from"]) for row in page_rows)
    possible_coverage = max(1, len(all_pages) * max(1, len(all_tools)))
    actual_coverage = sum(len(row["present_in"]) for row in page_rows)
    coverage_pct = round((actual_coverage / possible_coverage) * 100)

    inventory_available = bool(all_tools and all_pages)
    complete = inventory_available and mismatched_pages == 0
    status = "ok" if complete else ("warning" if inventory_available else "unavailable")
    status_label = "No mismatches detected" if complete else ("Needs review" if inventory_available else "Inventory data unavailable")

    if complete:
        status_message = f"All {len(all_pages)} pages are present across {len(all_tools)} tool folders."
    elif inventory_available:
        status_message = f"{mismatched_pages} page keys are missing from at least one tool folder. Coverage is {coverage_pct}%."
    else:
        status_message = "Inventory data unavailable."

    return {
        "tools": all_tools,
        "tools_count": len(all_tools),
        "total_distinct_pages": len(all_pages),
        "pages_present_in_all_tools": pages_present_in_all_tools,
        "mismatched_pages": mismatched_pages,
        "missing_reports_count": missing_reports_count,
        "complete": complete,
        "coverage_pct": coverage_pct,
        "page_rows": page_rows,
        "tool_rows": tool_rows,
        "inventory_available": inventory_available,
        "status": status,
        "status_label": status_label,
        "status_message": status_message,
    }