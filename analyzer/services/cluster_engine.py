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


def build_clusters(rows):
    clusters = {}

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
        fp = f"{rule_key}|{component}|{fingerprint}"

        if fp not in clusters:
            clusters[fp] = {
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
                "count": 0,
                "files": set(),
                "page_displays": set(),
                "pattern": r.get("pattern"),
                "component_group": r.get("component_group") or component,
                "tool_count": 0,
                "tool_family_count": 0,
                "tool_families": [],
                "sources": set(),
                "canonical_rule_id": r.get("canonical_rule_id"),
                "canonical_problem_type": r.get("canonical_problem_type"),
            }

        clusters[fp]["count"] += 1
        clusters[fp]["sources"].add(r.get("source") or "unknown")
        # Prefer the normalized page identifier so the same page found by
        # different tools does not get counted twice (for example `login.json`
        # and `https://.../login`).
        page = r.get("page") or r.get("url") or r.get("document") or r.get("file")
        if page:
            clusters[fp]["files"].add(page)
            page_display = r.get("page_display") or humanize_page_key(page)
            if page_display:
                clusters[fp]["page_displays"].add(page_display)

    for c in clusters.values():
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

    return sorted(clusters.values(), key=lambda c: (c.get("issue_rank_score", 0), c["count"], c["pages"]), reverse=True)
