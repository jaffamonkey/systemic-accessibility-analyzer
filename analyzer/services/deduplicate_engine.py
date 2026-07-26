"""
Deduplicate Engine

This module is responsible for taking a flat list of normalized accessibility 
violations and grouping them into "Systemic Clusters". 

Because different accessibility tools report the exact same issue using slightly 
different DOM selectors (e.g., Tool A reports `nav > ul > li > a` while Tool B 
reports `.menu-item`), this engine uses a two-tier approach:
1. Strict Bucketing: Group issues by their canonical Rule ID and UI Component.
2. Proximity Matching: Fuzzy-match the DOM snippets and selectors within that 
   bucket to determine if they point to the exact same physical node.
"""

import re
from analyzer.fingerprint import build_fingerprint
from analyzer.component_detector import detect_component
from services.wcag_refs import WCAG_SUCCESS_CRITERIA
from services.design_system import detect_design_system_issue
from services.rule_formatter import format_rule_label
from services.component_mapper import normalize_component
from services.bi_fields import (
    humanize_slug,
    humanize_page_key,
    infer_owner_team,
    infer_issue_scope,
    issue_scope_sort_value,
    severity_sort_value,
    wcag_level_sort_value,
    estimate_issue_rank_score,
    get_tool_family,
)

# -------------------------
# 🧩 TIER 2: PROXIMITY LOGIC
# -------------------------
def is_proximity_match(row: dict, cluster: dict) -> bool:
    """
    Fuzzy matching to detect if two issues point to the exact same DOM node, 
    even if different tools generated slightly different selectors.
    """
    
    # 1. The Easy Win: Exact Fingerprint Match
    if row.get("fingerprint") and cluster.get("fingerprint"):
        if row["fingerprint"] == cluster["fingerprint"]:
            return True

    # Helper: Safely extract CSS IDs (e.g., #my-element) for strict anchoring
    def extract_id(text):
        if not text: return None
        match = re.search(r'#([a-zA-Z0-9_-]+)', str(text))
        return match.group(1) if match else None

    r_sel = str(row.get("selector") or row.get("pattern") or "").lower()
    c_sel = str(cluster.get("pattern") or "").lower()

    # 2. Shared Exact ID (The Anchor)
    # If both tools flagged elements with the exact same CSS ID, they are the same issue.
    r_id = extract_id(r_sel) or extract_id(str(row.get("dom") or "").lower())
    c_id = extract_id(c_sel) or extract_id(str(cluster.get("dom") or "").lower())
    if r_id and c_id and r_id == c_id:
        return True

    # 3. Robust Substring Match (Selectors)
    # We require length > 8 to prevent a generic "a" from falsely matching "nav > a"
    if r_sel and c_sel and len(r_sel) > 8 and len(c_sel) > 8:
        if r_sel in c_sel or c_sel in r_sel:
            return True

    # 4. Robust Substring Match (Raw DOM Snippets)
    # If the raw HTML string provided by the tools overlaps significantly, merge them.
    r_dom = str(row.get("dom") or "").lower()
    c_dom = str(cluster.get("dom") or "").lower()
    if r_dom and c_dom and len(r_dom) > 15 and len(c_dom) > 15:
        if r_dom in c_dom or c_dom in r_dom:
            return True

    return False


# -------------------------
# 🛠️ HELPER FUNCTIONS
# -------------------------

def normalize_page(r: dict) -> str:
    """Strips file extensions and tool-specific suffixes from page URLs/names."""
    raw = (
        r.get("page")
        or r.get("url")
        or r.get("file")
        or r.get("document")
        or "unknown"
    )
    p = str(raw).lower().strip()
    p = re.sub(r"\.json$", "", p)
    p = re.sub(r"_(axe|lighthouse|htmlcs|ibm|wave|pa11y)$", "", p)
    return p

def _coerce_selector_value(value) -> str:
    """Safely extracts a flat string representation of a DOM selector from mixed types."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                extracted = ""
                for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
                    candidate = item.get(key)
                    if candidate:
                        extracted = str(candidate)
                        break
                if not extracted:
                    extracted = str(item)
                parts.append(extracted)
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p).strip()

    if isinstance(value, dict):
        for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
            candidate = value.get(key)
            if candidate:
                return str(candidate).strip()
        return str(value).strip()

    return str(value).strip()


def normalize_selector(selector: str) -> str:
    """Strips highly fragile positional pseudo-classes from selectors."""
    selector = _coerce_selector_value(selector)
    if not selector:
        return ""
    s = selector.lower()
    s = re.sub(r":nth-child\(\d+\)", "", s)
    s = re.sub(r":nth-of-type\(\d+\)", "", s)
    s = re.sub(r"\[\d+\]", "", s)
    s = " ".join(s.split())
    return s

# -------------------------
# 🚀 CORE CLUSTERING ENGINE
# -------------------------
def deduplicate_rows(rows: list) -> list:
    """
    The main deduplication entrypoint. Converts a flat list of normalized rows 
    into consolidated issue clusters, then enriches them with BI scoring fields.
    """
    buckets = {}

    for r in rows:
        dom = r.get("dom", "")
        selector = r.get("selector") or r.get("pattern") or ""
        component = normalize_component(r.get("component") or detect_component(dom, selector))
        
        fingerprint = (
            r.get("fingerprint")
            or build_fingerprint(
                dom, 
                r.get("normalized_target_key") or selector,
                r.get("ruleId") or r.get("rule_id")
            )
        )

        rule_key = r.get("canonical_rule_id") or r.get("ruleId") or r.get("wcag") or "unknown-rule"

        r["component"] = component
        r["fingerprint"] = fingerprint

        # 🪣 TIER 1 BUCKET: Isolate by Rule and Component type to limit the search space
        bucket_key = f"{rule_key}|{component}"

        if bucket_key not in buckets:
            buckets[bucket_key] = []

        # 🧲 TIER 2: Scan the bucket for a proximity match
        merged = False
        for cluster in buckets[bucket_key]:
            if is_proximity_match(r, cluster):
                cluster["count"] += 1
                cluster["sources"].add(r.get("source") or "unknown")
                
                # Capture multiple error messages from different tools
                if r.get("message") and r["message"] not in cluster.get("message", ""):
                    cluster["message"] = f"{cluster.get('message', '')} | {r['message']}".strip(" | ")

                page = r.get("page") or r.get("url") or r.get("document") or r.get("file")
                if page:
                    cluster["files"].add(page)
                    page_display = r.get("page_display") or humanize_page_key(page)
                    if page_display:
                        cluster["page_displays"].add(page_display)

                # Keep the longest (most descriptive) pattern/dom available
                if len(selector) > len(cluster.get("pattern") or ""):
                    cluster["pattern"] = selector
                if len(dom) > len(cluster.get("dom") or ""):
                    cluster["dom"] = dom

                merged = True
                break

        # If no proximity match was found, establish a new cluster
        if not merged:
            new_cluster = {
                "ruleId": r.get("ruleId"),
                "rule_name": r.get("rule_name") or r.get("rule") or r.get("rule_display"),
                "rule_key": rule_key,
                "source": r.get("source"),
                "wcag": r.get("wcag"),
                "wcag_level": r.get("wcag_level"),
                "wcag_title": r.get("wcag_title"),
                "wcag_url": r.get("wcag_url"),
                "message": r.get("message"),
                "dom": dom,
                "dom_path": selector or dom,
                "fingerprint": fingerprint,
                "normalized_target_key": r.get("normalized_target_key"),
                "severity": r.get("severity"),
                "component": component,
                "root_cause": None,
                "count": 1,
                "files": set(),
                "page_displays": set(),
                "pattern": selector,
                "component_group": r.get("component_group") or component,
                "tool_count": 0,
                "tool_family_count": 0,
                "tool_families": [],
                "sources": {r.get("source") or "unknown"},
                "canonical_rule_id": r.get("canonical_rule_id"),
                "canonical_problem_type": r.get("canonical_problem_type"),
            }

            page = r.get("page") or r.get("url") or r.get("document") or r.get("file")
            if page:
                new_cluster["files"].add(page)
                page_display = r.get("page_display") or humanize_page_key(page)
                if page_display:
                    new_cluster["page_displays"].add(page_display)

            buckets[bucket_key].append(new_cluster)

    # -------------------------
    # 📊 FLATTEN AND ENRICH
    # -------------------------
    final_clusters = []
    for cluster_list in buckets.values():
        final_clusters.extend(cluster_list)

    # Attach finalized BI and scoring fields to the generated clusters
    for c in final_clusters:
        c["files"] = sorted(c["files"])
        c["page_displays"] = sorted(c.get("page_displays", []))
        c["page_names"] = ", ".join(c["page_displays"])
        c["sources"] = sorted(c["sources"])
        c["tool_count"] = len(c["sources"])
        c["tool_families"] = sorted({get_tool_family(source) for source in c["sources"] if source})
        c["tool_family_count"] = len(c["tool_families"])
        c["pages"] = len(c["files"])
        c["root_cause"] = detect_design_system_issue(c)
        c["systemic"] = c["pages"] >= 3 and c["count"] >= 2

        c["rule_label"] = format_rule_label(c)

        c["severity_sort"] = severity_sort_value(c.get("severity"))
        c["wcag_level_sort"] = wcag_level_sort_value(c.get("wcag_level"))
        c["component_display"] = humanize_slug(c.get("component"))
        c["component_group_display"] = humanize_slug(c.get("component_group"))
        c["display_pattern"] = humanize_slug(c.get("pattern") or c.get("component"))
        c["owner_team"] = infer_owner_team(c.get("component_group"), c.get("component"))
        c["design_system_issue"] = bool(c.get("root_cause") or c.get("systemic"))
        c["issue_scope"] = infer_issue_scope(
            design_system=c.get("root_cause"),
            component=c.get("component"),
            root_cause=c.get("root_cause"),
            pages=c.get("pages", 1),
            systemic=c.get("systemic", False),
        )
        c["issue_scope_sort"] = issue_scope_sort_value(c["issue_scope"])
        c["affected_pages_count"] = c.get("pages", 0)
        c["issue_rank_score"] = estimate_issue_rank_score(
            severity=c.get("severity"),
            pages=c.get("pages", 1),
            instance_count=c.get("count", 1),
            systemic=c.get("systemic", False),
            tool_count=c.get("tool_count", 1),
        )

    # Return clusters sorted by priority: Highest Rank Score -> Most Instances -> Most Pages Affected
    return sorted(final_clusters, key=lambda c: (c.get("issue_rank_score", 0), c["count"], c["pages"]), reverse=True)