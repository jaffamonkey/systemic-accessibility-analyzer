import re
from analyzer.fingerprint import build_fingerprint
from analyzer.component_detector import detect_component
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
# 🔥 TIER 2: PROXIMITY LOGIC
# -------------------------
def is_proximity_match(row, cluster):
    """Fuzzy matching to detect if two issues point to the exact same DOM node."""
    
    # 1. The Easy Win: Exact Fingerprint Match
    if row.get("fingerprint") and cluster.get("fingerprint"):
        if row["fingerprint"] == cluster["fingerprint"]:
            return True

    # Helper: Safely extract CSS IDs (#my-element)
    def extract_id(text):
        if not text: return None
        match = re.search(r'#([a-zA-Z0-9_-]+)', str(text))
        return match.group(1) if match else None

    r_sel = str(row.get("selector") or row.get("pattern") or "").lower()
    c_sel = str(cluster.get("pattern") or "").lower()

    # 2. Shared Exact ID (The Anchor)
    r_id = extract_id(r_sel) or extract_id(str(row.get("dom") or "").lower())
    c_id = extract_id(c_sel) or extract_id(str(cluster.get("dom") or "").lower())
    if r_id and c_id and r_id == c_id:
        return True

    # 3. Robust Substring Match (Selectors)
    # We require length > 8 to prevent a generic "a" from matching "nav > a"
    if r_sel and c_sel and len(r_sel) > 8 and len(c_sel) > 8:
        if r_sel in c_sel or c_sel in r_sel:
            return True

    # 4. Robust Substring Match (Raw DOM Snippets)
    r_dom = str(row.get("dom") or "").lower()
    c_dom = str(cluster.get("dom") or "").lower()
    if r_dom and c_dom and len(r_dom) > 15 and len(c_dom) > 15:
        if r_dom in c_dom or c_dom in r_dom:
            return True

    return False

def normalize_page(r):
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


def _infer_wcag_level(wcag: str | None) -> str | None:
    if not wcag:
        return None

    ref = WCAG_SUCCESS_CRITERIA.get(str(wcag).split()[0])
    if ref:
        return ref.get("level")
    return None


def _coerce_selector_value(value):
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


def normalize_selector(selector):
    selector = _coerce_selector_value(selector)

    if not selector:
        return ""

    s = selector.lower()
    s = re.sub(r":nth-child\(\d+\)", "", s)
    s = re.sub(r":nth-of-type\(\d+\)", "", s)
    s = re.sub(r"\[\d+\]", "", s)
    s = " ".join(s.split())
    return s


def _primary_selector_value(r):
    return _coerce_selector_value(
        r.get("selector")
        or r.get("dom")
        or r.get("target")
        or r.get("xpath")
        or r.get("path")
    )


def _row_wcags(r) -> list[str]:
    vals = r.get("wcag_criteria") or r.get("wcag") or []
    if isinstance(vals, str):
        return [vals.strip()]
    return [str(x).strip() for x in vals if str(x).strip()]


def _dedupe_key(r):
    page = normalize_page(r)
    canonical_rule_id = (
        r.get("canonical_rule_id")
        or r.get("rule_id")
        or r.get("ruleId")
        or r.get("wcag")
        or "unknown-rule"
    )

    source = str(r.get("source") or "").strip().lower()
    is_page_level = source == "speca11y" and r.get("issue_scope") == "page"

    if is_page_level:
        return f"{page}|{canonical_rule_id}|page-level"

    target_key = (
        r.get("normalized_target_key")
        or normalize_selector(
            r.get("selector")
            or r.get("dom_path")
            or r.get("dom")
            or r.get("target")
            or r.get("xpath")
            or r.get("path")
            or r.get("pattern")
            or ""
        )
        or r.get("fingerprint")
        or "unknown-target"
    )

    return f"{page}|{canonical_rule_id}|{target_key}"


def deduplicate_rows(rows):
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
                r.get("ruleId") or r.get("rule_id")  # 🔥 Added the rule ID here!
            )
        )

        rule_key = r.get("canonical_rule_id") or r.get("ruleId") or r.get("wcag") or "unknown-rule"

        r["component"] = component
        r["fingerprint"] = fingerprint

        # 🔥 TIER 1 BUCKET: Isolate by Rule and Component type
        bucket_key = f"{rule_key}|{component}"

        if bucket_key not in buckets:
            buckets[bucket_key] = []

        # 🔥 TIER 2: Scan the bucket for a proximity match
        merged = False
        for cluster in buckets[bucket_key]:
            if is_proximity_match(r, cluster):
                cluster["count"] += 1
                cluster["sources"].add(r.get("source") or "unknown")
                
                # Optional: Capture multiple error messages!
                if r.get("message") and r["message"] not in cluster.get("message", ""):
                    cluster["message"] = f"{cluster.get('message', '')} | {r['message']}".strip(" | ")

                page = r.get("page") or r.get("url") or r.get("document") or r.get("file")
                if page:
                    cluster["files"].add(page)
                    page_display = r.get("page_display") or humanize_page_key(page)
                    if page_display:
                        cluster["page_displays"].add(page_display)

                if len(selector) > len(cluster.get("pattern") or ""):
                    cluster["pattern"] = selector
                if len(dom) > len(cluster.get("dom") or ""):
                    cluster["dom"] = dom

                merged = True
                break

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
    # FLATTEN AND ENRICH
    # -------------------------
    final_clusters = []
    for cluster_list in buckets.values():
        final_clusters.extend(cluster_list)

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

    return sorted(final_clusters, key=lambda c: (c.get("issue_rank_score", 0), c["count"], c["pages"]), reverse=True)
