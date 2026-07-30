import re

from analyzer.component_config import COMPONENT_GROUPS, COMPONENT_PATTERNS
from analyzer.define_taxonomy import PROBLEM_TYPE_MAP
from services.wcag_refs import WCAG_SUCCESS_CRITERIA
from services.bi_fields import get_tool_family, get_tool_engine
from analyzer.component_learning import UNKNOWN_PATTERNS, LEARNING


def is_dynamic_id(p):
    return bool(re.match(r"#?[a-f0-9\-]{8,}", p))


def _is_strict_agreement_candidate(r):
    result_type = str(r.get("result_type") or "").strip().lower()
    source = str(r.get("source") or "").strip().lower()

    rule_id = str(
        r.get("canonical_rule_id")
        or r.get("rule_id")
        or r.get("ruleId")
        or ""
    ).strip().lower()

    if rule_id == "frame-tested":
        return False

    if result_type in {"manual", "recommendation", "potentialrecommendation"}:
        return False

    if result_type in {"warning", "incomplete"}:
        return False

    if result_type == "potentialviolation":
        return source == "ibm"

    if r.get("needs_review") and source != "ibm":
        return False

    return True


def _is_balanced_agreement_candidate(r):
    result_type = str(r.get("result_type") or "").strip().lower()
    source = str(r.get("source") or "").strip().lower()
    needs_review = bool(r.get("needs_review"))

    rule_id = str(
        r.get("canonical_rule_id")
        or r.get("rule_id")
        or r.get("ruleId")
        or ""
    ).strip().lower()

    if rule_id == "frame-tested":
        return False
    
    if r.get("is_audit_note"):
        return False

    if result_type in {"manual", "recommendation", "potentialrecommendation"}:
        return False

    if result_type == "violation":
        return True

    if result_type == "potentialviolation":
        return source in {"ibm", "axe-scan"}

    if result_type == "incomplete":
        return source == "axe-core"

    if result_type == "warning":
        return source in {"html-sniffer", "pa11y-htmlcs", "speca11y"}

    if needs_review:
        return source in {"ibm", "axe-scan", "axe-core", "html-sniffer", "pa11y-htmlcs", "speca11y"}

    return False


def collapse_agreement_rows_for_chart(rows):
    collapsed = {}

    for r in rows:
        page = str(r.get("page") or "unknown").strip().lower()
        source = str(r.get("source") or "unknown").strip().lower()
        rule_id = str(
            r.get("canonical_rule_id")
            or r.get("rule_id")
            or r.get("ruleId")
            or r.get("wcag")
            or "unknown-rule"
        ).strip().lower()

        target = str(
            r.get("normalized_target_key")
            or r.get("fingerprint")
            or r.get("selector")
            or r.get("dom_path")
            or ""
        ).strip().lower()

        # Chart-only dampening for very noisy source output.
        if source == "pa11y-axe":
            key = (page, source, rule_id)
        else:
            key = (page, source, rule_id, target)

        if key not in collapsed:
            collapsed[key] = r

    return list(collapsed.values())

# def _agreement_cluster_key(r):
#     page = str(r.get("page") or "unknown").strip().lower()

#     rule_id = str(
#         r.get("canonical_rule_id")
#         or r.get("rule_id")
#         or r.get("ruleId")
#         or r.get("wcag")
#         or "unknown-rule"
#     ).strip().lower()

#     component = str(r.get("component") or "other").strip().lower()
#     wcag = str(r.get("wcag") or "").strip()

#     # Looser than strict dedupe on purpose:
#     # enough to merge equivalent findings across tools on the same page,
#     # but still separated by rule/component/WCAG.
#     # return f"{page}|{rule_id}|{component}|{wcag}"
#     return f"{page}|{rule_id}"

def _agreement_cluster_key(r):
    page = str(r.get("page") or "unknown").strip().lower()

    rule_id = str(
        r.get("canonical_rule_id")
        or r.get("rule_id")
        or r.get("ruleId")
        or r.get("wcag")
        or "unknown-rule"
    ).strip().lower()

    return f"{page}|{rule_id}"


def collapse_to_agreement_clusters(rows):
    grouped = {}

    for r in rows:
        key = _agreement_cluster_key(r)

        if key not in grouped:
            base = dict(r)
            base["sources"] = set(r.get("sources") or ([r.get("source")] if r.get("source") else []))
            grouped[key] = base
        else:
            base = grouped[key]
            incoming_sources = r.get("sources") or ([r.get("source")] if r.get("source") else [])
            base["sources"].update(incoming_sources)

        # Keep a few helpful rollups fresh
        grouped[key]["tool_families"] = {
            get_tool_family(source)
            for source in grouped[key]["sources"]
            if source
        }
        grouped[key]["tool_engines"] = {
            get_tool_engine(source)
            for source in grouped[key]["sources"]
            if source
        }
        grouped[key]["tool_family_count"] = len(grouped[key]["tool_families"])
        grouped[key]["tool_engine_count"] = len(grouped[key]["tool_engines"])

    out = []
    for row in grouped.values():
        row["sources"] = sorted(row["sources"])
        row["tool_families"] = sorted(row["tool_families"])
        row["tool_engines"] = sorted(row["tool_engines"])
        out.append(row)

    return out


def suggest_component(pattern):
    if not pattern:
        return None

    learned = LEARNING.get(pattern)
    if learned and learned.get("component"):
        return learned["component"]

    p = str(pattern).lower().strip()

    for component, keywords in COMPONENT_PATTERNS.items():
        for k in keywords:
            if k in p:
                return component

    if p in {
        "#email",
        "#firstname",
        "#first",
        "#lasttname",
        "#phno",
        "#postalcode",
        "#state",
        "#date",
        "#noedit",
        "#isdisabled",
        "#dontwrite",
        "#addl1",
        "#addl2",
        "#second",
    }:
        return "form_field"

    if p in {
        "#fruits",
        "#lang",
        "#superheros",
    }:
        return "form_field"

    if p in {
        "#generate",
        "#clearme",
        "#getme",
        "#join",
    }:
        return "button"

    if p == "#shopping":
        return "product_card"

    if p == "#sample-box1":
        return "card"

    if p in {
        ".content",
    }:
        return "text"

    if p in {
        ".block",
        ".is-expanded",
        ".is-6-desktop",
        ".p-4",
    }:
        return "layout"

    if p in {
        ".current",
    }:
        return "navigation"

    if p in {
        ".filed",
    }:
        return "form_field"

    if "html-has-lang" in p or "html_lang_exists" in p or "language-of-page" in p:
        return "document_metadata"

    if "region" in p or "landmark" in p:
        return "layout"

    if "listitem" in p or p.endswith("> li") or " li" in p:
        return "list"

    if "oobee-accessible-label" in p:
        return "link"

    if "toggle-theme" in p or "theme-icon" in p or "data-theme-status" in p:
        return "theme_toggle"

    if "navbar-dropdown" in p or "has-dropdown" in p or "dropdown-item" in p:
        return "dropdown_menu"

    if "navbar" in p or "navbar-item" in p or "navbar-link" in p or "navbar-menu" in p or "navbar-burger" in p:
        return "navbar"

    if "iframe" in p or "firstfr" in p or "frameui" in p:
        return "iframe_embed"

    if "selectable" in p:
        return "selectable_list"

    if "card" in p and ("product" in p or "price" in p or "rating" in p or "store" in p):
        return "product_card"

    if "field" in p or "control" in p:
        return "form_field"

    if "table" in p or "thead" in p or "tbody" in p or "tr" in p or "td" in p or "th" in p:
        return "data_table"

    if (
        p.startswith("#___ytsubscribe_")
        or p.startswith("#i0_")
        or p.startswith("#aswift_")
        or p in {
            ".google-anno",
            ".google-auto-placed",
            "#google-anno-sa",
            "div",
            "unknown",
            "#testing",
        }
    ):
        return None

    if is_dynamic_id(p):
        return None

    if 'role="button"' in p or "[role=button]" in p:
        return "button"

    if 'role="dialog"' in p or "[role=dialog]" in p or "modal" in p or "dialog" in p:
        return "modal"

    if 'role="tab"' in p or 'role="tablist"' in p or "tablist" in p or "tabpanel" in p or "tabs" in p:
        return "tabs"

    if 'role="navigation"' in p or "[role=navigation]" in p or "<nav" in p or " nav" in p:
        return "navigation"

    if 'role="search"' in p or "[role=search]" in p or "search" in p:
        return "search"

    if 'role="alert"' in p or "[role=alert]" in p or "alert" in p or "toast" in p or "banner" in p:
        return "alert"

    if 'role="tooltip"' in p or "[role=tooltip]" in p or "tooltip" in p:
        return "tooltip"

    if 'role="checkbox"' in p or 'type="checkbox"' in p or "[type=checkbox]" in p or "checkbox" in p:
        return "form"

    if 'role="radio"' in p or 'type="radio"' in p or "[type=radio]" in p or "radio" in p:
        return "form"

    if 'role="combobox"' in p or "[role=combobox]" in p or "combobox" in p or "autocomplete" in p:
        return "form"

    if 'role="table"' in p or "[role=table]" in p or "gridcell" in p or "treegrid" in p:
        return "data_table"

    if 'role="list"' in p or "[role=list]" in p or "<ul" in p or "<ol" in p or "list" in p:
        return "list"

    if p.startswith("button") or " button" in p or ".btn" in p or "btn-" in p:
        return "button"

    if p.startswith("a") or " a" in p or "link" in p:
        return "link"

    if "input" in p or "textarea" in p or "select" in p or "option" in p or "fieldset" in p or "label" in p:
        return "form"

    if "file-upload" in p or "upload" in p:
        return "file_upload"

    if p == "i" or "icon" in p or "svg" in p:
        return "icon"

    if "img" in p or "image" in p or "figure" in p:
        return "image"

    if "frame" in p or "frameset" in p:
        return "frame"

    if "ul" in p or "ol" in p or "li" in p or "list" in p:
        return "list"

    if "header" in p or "footer" in p or "main" in p or "aside" in p:
        return "layout"

    if "container" in p or "#content" in p or "wrapper" in p or "layout" in p:
        return "layout"

    if "grid" in p or "col-" in p or "row" in p:
        return "grid"

    if p.startswith(("h1", "h2", "h3", "h4", "h5", "h6")):
        return "heading"

    if p.startswith("p") or " p" in p or "text" in p or "copy" in p:
        return "text"

    if "meta" in p or "head" in p or "title" in p:
        return "document_metadata"

    if "accordion" in p:
        return "accordion"

    if "card" in p:
        return "card"

    if "breadcrumb" in p:
        return "breadcrumb"

    if "pagination" in p or "pager" in p:
        return "pagination"

    if "carousel" in p or "slider" in p:
        return "carousel"

    if "calendar" in p or "datepicker" in p or "date-picker" in p:
        return "form"

    return None


def suggest_component_from_context(rule_id=None, message=None, dom_path=None, pattern=None):
    rule = str(rule_id or "").lower()
    msg = str(message or "").lower()
    dom = str(dom_path or "").lower()
    pat = str(pattern or "").lower()

    combined = " ".join([rule, msg, dom, pat])

    if any(x in rule for x in [
        "html-has-lang",
        "html_lang_exists",
        "language-of-page",
        "document-title",
        "page-title",
    ]):
        return "document_metadata"

    if (
        "<html" in dom
        or "html element must have a lang attribute" in msg
        or "lang attribute" in msg
        or "language of page" in msg
    ):
        return "document_metadata"

    if any(x in rule for x in [
        "region",
        "landmark",
    ]):
        return "layout"

    if (
        "content is not contained by landmarks" in msg
        or "not contained by landmarks" in msg
        or "landmark" in msg
    ):
        return "layout"

    if any(x in rule for x in [
        "oobee-accessible-label",
        "link-name",
        "link-purpose",
        "link-purpose-in-context",
    ]):
        return "link"

    if any(x in rule for x in [
        "button-name",
        "aria-command-name",
        "name-role-value",
    ]):
        if "button" in combined or "discernible text" in msg or "toggle" in combined:
            return "button"

    if any(x in rule for x in [
        "frame-title",
        "frame-title-unique",
        "iframe-title",
    ]):
        return "frame"

    if any(x in rule for x in [
        "image-alt",
        "image-alt-text-missing",
        "figure-missing-alt",
    ]):
        return "image"

    if any(x in rule for x in [
        "select-name",
        "label",
        "label_ref_valid",
        "form-field-name-missing",
        "form-field-has-no-description",
        "input_checkboxes_grouped",
    ]):
        return "form"

    if any(x in rule for x in [
        "heading-order",
        "page-has-heading-one",
        "headings-not-nested-properly",
    ]):
        return "heading"

    if any(x in rule for x in [
        "listitem",
        "list",
        "definition-list",
    ]):
        return "list"

    if any(x in rule for x in [
        "table-header",
        "table_headers_exists",
        "table-has-no-headers",
        "table-header-cell-has-no-scope",
    ]):
        return "table"

    if any(x in rule for x in [
        "text-spacing",
        "avoid-inline-spacing",
        "use-of-color",
        "color-contrast",
        "contrast-minimum",
        "contrast-enhanced",
    ]):
        if any(x in dom for x in ["<a", " a ", "href", "a[", "a:"]):
            return "link"
        if any(x in dom for x in ["button", "btn", 'role="button"', "[role=button]", "toggle"]):
            return "button"
        if any(x in dom for x in ["font", "span", "p", "label", "strong", "em", "small", "b", "h1", "h2", "h3", "h4", "h5", "h6"]):
            return "text"
        if "letter-spacing" in msg or "word-spacing" in msg:
            return "text"

    if "links must have discernible text" in msg or "link purpose" in msg:
        return "link"

    if "clickable element does not have an accessible label" in msg:
        return "link"

    if "buttons must have discernible text" in msg or "button must have discernible text" in msg:
        return "button"

    if "frames must have an accessible name" in msg or "frame elements must have an accessible name" in msg or "iframe" in msg:
        return "frame"

    if "inline text spacing must be adjustable" in msg or "letter-spacing" in msg or "word-spacing" in msg:
        return "text"

    if "image" in msg and "alt" in msg:
        return "image"

    if "list item does not have a <ul>, <ol> parent element" in msg:
        return "list"

    if "checkbox" in msg or "radio" in msg or "combobox" in msg:
        return "form"

    if any(x in dom for x in ["iframe", "frame", "frameset"]):
        return "frame"

    if any(x in dom for x in ["button", "btn", 'role="button"', "[role=button]", "toggle"]):
        return "button"

    if any(x in dom for x in ["input", "textarea", "select", "option", "fieldset", "form", "checkbox", "radio"]):
        return "form"

    if any(x in dom for x in ["img", "image", "figure", "svg", "icon"]):
        return "image"

    if any(x in dom for x in ["<a", " a ", "href", "a[", "a:"]):
        return "link"

    if any(x in dom for x in ["ul", "ol", "li", "list"]):
        return "list"

    if any(x in dom for x in ["dialog", "modal"]):
        return "modal"

    if any(x in dom for x in ["tablist", "tabpanel", 'role="tab"', "[role=tab]"]):
        return "tabs"

    if any(x in dom for x in ["nav", "navigation", "breadcrumb", "pagination", "pager"]):
        return "navigation"

    if any(x in dom for x in ["center", "table", "thead", "tbody", "tr", "td", "th"]):
        if "landmark" in combined or "region" in combined:
            return "layout"
        if "listitem" in combined:
            return "list"
        if "accessible label" in combined or "link-name" in combined:
            return "link"
        return "table"

    if any(x in dom for x in ["span", "p", "text", "copy", "headline", "title", "font", "b", "strong"]):
        if "spacing" in combined or "contrast" in combined or "color" in combined:
            return "text"

    if "frames should be tested with axe-core" in msg or "frame-tested" in rule:
        return "frame"

    if pat in {"/", "div", "span"}:
        if "link" in combined:
            return "link"
        if "button" in combined:
            return "button"
        if "frame" in combined:
            return "frame"
        if "spacing" in combined or "contrast" in combined or "color" in combined:
            return "text"

    if "toggle" in pat or "toggle" in dom or "toggle" in msg:
        return "button"

    return None


def get_suggested_components():
    sorted_unknowns = sorted(
        UNKNOWN_PATTERNS.items(),
        key=lambda x: x[1],
        reverse=True
    )

    results = []

    for pattern, count in sorted_unknowns:
        learned = LEARNING.get(pattern)
        if learned and learned.get("component"):
            continue

        suggestion = suggest_component(pattern) or "other"
        group = COMPONENT_GROUPS.get(suggestion, suggestion)

        results.append({
            "pattern": pattern,
            "count": count,
            "suggestion": suggestion,
            "group": group
        })

        if len(results) >= 15:
            break

    return results

def _build_next_best_fixes(clusters, rows=None):
    pattern_rollup = {}

    # Build a quick lookup from pattern/rule to its page files using raw rows
    pattern_to_pages = {}
    if rows:
        for r in rows:
            pats = [r.get("pattern"), r.get("ruleId"), r.get("rule_id")]
            file_list = r.get("files") or ([r.get("page")] if r.get("page") else [])
            for p in pats:
                if p:
                    pattern_to_pages.setdefault(p, set()).update(file_list)

    for c in clusters:
        pattern = c.get("pattern")
        rule_id = c.get("canonical_rule_id") or c.get("ruleId")
        component = c.get("component")

        weak_values = {"", "unknown", "unknown-pattern", "other", None}

        if pattern in weak_values:
            if rule_id and str(rule_id).strip().lower() not in weak_values:
                pattern = rule_id
            elif component and str(component).strip().lower() not in weak_values:
                pattern = component
            else:
                continue

        stats = pattern_rollup.setdefault(pattern, {
            "pattern": pattern,
            "display_pattern": c.get("display_pattern") or pattern,
            "component": c.get("component") or "other",
            "component_display": c.get("component_display") or (c.get("component") or "other").replace("_", " ").title(),
            "severity": c.get("severity") or "unknown",
            "severity_display": str(c.get("severity") or "unknown").title(),
            "severity_sort": c.get("severity_sort") or 99,
            "findings_count": 0,
            "pages": set(),
            "is_systemic": False,
            "issue_scope": c.get("issue_scope") or "Unknown",
            "issue_scope_sort": c.get("issue_scope_sort") or 99,
            "owner_team": c.get("owner_team") or "Frontend Platform",
            "priority_score": 0,
            "root_cause": c.get("root_cause") or "",
        })

        stats["findings_count"] += c.get("count", 0)
        
        # Safely pull pages from cluster files, instances, or fallback to raw rows lookup
        cluster_files = c.get("files") or []
        if isinstance(cluster_files, list):
            stats["pages"].update(cluster_files)
            
        if c.get("instances"):
            for inst in c.get("instances"):
                if isinstance(inst, dict):
                    f = inst.get("files") or inst.get("page") or inst.get("file")
                    if isinstance(f, list):
                        stats["pages"].update(f)
                    elif f:
                        stats["pages"].add(f)

        if not stats["pages"] and rows:
            if pattern in pattern_to_pages:
                stats["pages"].update(pattern_to_pages[pattern])
            if rule_id and rule_id in pattern_to_pages:
                stats["pages"].update(pattern_to_pages[rule_id])

        stats["is_systemic"] = stats["is_systemic"] or bool(c.get("systemic"))
        stats["priority_score"] = max(stats["priority_score"], c.get("issue_rank_score", 0))
        if (c.get("issue_scope_sort") or 99) < (stats.get("issue_scope_sort") or 99):
            stats["issue_scope"] = c.get("issue_scope") or stats.get("issue_scope")
            stats["issue_scope_sort"] = c.get("issue_scope_sort") or stats.get("issue_scope_sort")

        current_sort = c.get("severity_sort") or 99
        if current_sort < stats["severity_sort"]:
            stats["severity_sort"] = current_sort
            stats["severity"] = c.get("severity") or "unknown"
            stats["severity_display"] = str(c.get("severity") or "unknown").title()

        if c.get("root_cause") and not stats["root_cause"]:
            stats["root_cause"] = c.get("root_cause")

    ranked = []
    for stats in pattern_rollup.values():
        stats["affected_pages_count"] = len(stats["pages"])
        stats["top_fix_candidate"] = (
            stats["affected_pages_count"] >= 2
            or stats["is_systemic"]
            or stats["findings_count"] >= 3
        )
        ranked.append(stats)

    ranked.sort(
        key=lambda item: (
            item["priority_score"],
            item["affected_pages_count"],
            item["findings_count"],
            -item["severity_sort"],
        ),
        reverse=True,
    )

    for idx, item in enumerate(ranked, start=1):
        item["top_fix_rank"] = idx
        item["systemic_label"] = "Yes" if item["is_systemic"] else "No"
        item["pages"] = sorted(item["pages"])

    top_fixes = ranked[:10]
    top5_pages = sorted({page for item in top_fixes[:5] for page in item["pages"]})

    owner_counts = {}
    for item in top_fixes:
        owner = item.get("owner_team") or "Frontend Platform"
        owner_counts[owner] = owner_counts.get(owner, 0) + item.get("findings_count", 0)

    top_owner_team = None
    if owner_counts:
        top_owner_team = max(owner_counts.items(), key=lambda pair: pair[1])[0]

    summary = {
        "systemic_fixes": sum(1 for item in top_fixes if item.get("is_systemic")),
        "pages_impacted_top5": len(top5_pages),
        "top_owner_team": top_owner_team or "-",
        "top5_pages": top5_pages,
    }

    return top_fixes, summary
    pattern_rollup = {}

    for c in clusters:
        pattern = c.get("pattern")
        rule_id = c.get("canonical_rule_id") or c.get("ruleId")
        component = c.get("component")

        weak_values = {"", "unknown", "unknown-pattern", "other", None}

        if pattern in weak_values:
            if rule_id and str(rule_id).strip().lower() not in weak_values:
                pattern = rule_id
            elif component and str(component).strip().lower() not in weak_values:
                pattern = component
            else:
                continue

        stats = pattern_rollup.setdefault(pattern, {
            "pattern": pattern,
            "display_pattern": c.get("display_pattern") or pattern,
            "component": c.get("component") or "other",
            "component_display": c.get("component_display") or (c.get("component") or "other").replace("_", " ").title(),
            "severity": c.get("severity") or "unknown",
            "severity_display": str(c.get("severity") or "unknown").title(),
            "severity_sort": c.get("severity_sort") or 99,
            "findings_count": 0,
            "pages": set(),
            "is_systemic": False,
            "issue_scope": c.get("issue_scope") or "Unknown",
            "issue_scope_sort": c.get("issue_scope_sort") or 99,
            "owner_team": c.get("owner_team") or "Frontend Platform",
            "priority_score": 0,
            "root_cause": c.get("root_cause") or "",
        })

        stats["findings_count"] += c.get("count", 0)
        stats["pages"].update(c.get("files") or [])
        stats["is_systemic"] = stats["is_systemic"] or bool(c.get("systemic"))
        stats["priority_score"] = max(stats["priority_score"], c.get("issue_rank_score", 0))
        if (c.get("issue_scope_sort") or 99) < (stats.get("issue_scope_sort") or 99):
            stats["issue_scope"] = c.get("issue_scope") or stats.get("issue_scope")
            stats["issue_scope_sort"] = c.get("issue_scope_sort") or stats.get("issue_scope_sort")

        current_sort = c.get("severity_sort") or 99
        if current_sort < stats["severity_sort"]:
            stats["severity_sort"] = current_sort
            stats["severity"] = c.get("severity") or "unknown"
            stats["severity_display"] = str(c.get("severity") or "unknown").title()

        if c.get("root_cause") and not stats["root_cause"]:
            stats["root_cause"] = c.get("root_cause")

    ranked = []
    for stats in pattern_rollup.values():
        stats["affected_pages_count"] = len(stats["pages"])
        stats["top_fix_candidate"] = (
            stats["affected_pages_count"] >= 2
            or stats["is_systemic"]
            or stats["findings_count"] >= 3
        )
        ranked.append(stats)

    ranked.sort(
        key=lambda item: (
            item["priority_score"],
            item["affected_pages_count"],
            item["findings_count"],
            -item["severity_sort"],
        ),
        reverse=True,
    )

    for idx, item in enumerate(ranked, start=1):
        item["top_fix_rank"] = idx
        item["systemic_label"] = "Yes" if item["is_systemic"] else "No"
        item["pages"] = sorted(item["pages"])

    top_fixes = ranked[:10]
    top5_pages = sorted({page for item in top_fixes[:5] for page in item["pages"]})

    owner_counts = {}
    for item in top_fixes:
        owner = item.get("owner_team") or "Frontend Platform"
        owner_counts[owner] = owner_counts.get(owner, 0) + item.get("findings_count", 0)

    top_owner_team = None
    if owner_counts:
        top_owner_team = max(owner_counts.items(), key=lambda pair: pair[1])[0]

    summary = {
        "systemic_fixes": sum(1 for item in top_fixes if item.get("is_systemic")),
        "pages_impacted_top5": len(top5_pages),
        "top_owner_team": top_owner_team or "-",
        "top5_pages": top5_pages,
    }

    return top_fixes, summary


def calculate_metrics(rows, clusters):
    """
    Calculates dashboard metrics and prioritizes accessibility issues.

    Takes the raw violation rows and the deduplicated clusters to generate
    scoring, heatmaps, and tool-consensus profiles. Highlights systemic 
    patterns across pages to prioritize "Fix Once, Benefit Many" remediations.
    """
    print("\n" + "="*50)
    print("💥 HELLO FROM THE NEW METRICS ENGINE! 💥")
    print("="*50 + "\n")
    
    violations = len(rows)
    unique_pages = set()
    for r in rows:
        page_list = r.get("files")
        if page_list and isinstance(page_list, list):
            unique_pages.update(page_list)
        elif r.get("page"):
            unique_pages.add(r.get("page"))

    # Count how many findings share the same rule/pattern across multiple pages or instances
    pattern_counts = {}
    for r in rows:
        key = r.get("pattern") or r.get("ruleId") or r.get("rule_id") or "unknown"
        pattern_counts[key] = pattern_counts.get(key, 0) + 1

    # Any finding belonging to a pattern that appears more than once is "shared"
    shared_findings = sum(
        count for key, count in pattern_counts.items() if count > 1
    )
    
    shared_pattern_impact = round((shared_findings / violations) * 100) if violations else 0

    source_counts = {}

    for r in rows:
        sources = r.get("sources")

        if sources:
            for s in sources:
                source_counts[s] = source_counts.get(s, 0) + 1
        else:
            source = r.get("source") or "unknown"
            source_counts[source] = source_counts.get(source, 0) + 1

    component_heatmap = {}
    for r in rows:
        component = r.get("component") or "other"
        component_heatmap[component] = component_heatmap.get(component, 0) + 1

    component_heatmap = dict(
        sorted(component_heatmap.items(), key=lambda x: x[1], reverse=True)
    )

    component_risk = {}
    for c in clusters:
        component = c.get("component") or "other"
        count = c.get("count", 0)
        pages = c.get("pages", 1)
        systemic = c.get("systemic")

        risk = count * pages
        if systemic:
            risk *= 2

        component_risk[component] = component_risk.get(component, 0) + risk

    component_risk = dict(
        sorted(component_risk.items(), key=lambda x: x[1], reverse=True)
    )

    design_heatmap = {}
    systemic_violations = 0

    for c in clusters:
        cause = c.get("root_cause")
        component = c.get("component") or "other"
        rule = c.get("wcag")

        if cause or c.get("systemic"):
            key = f"{component} | {rule}"
            design_heatmap[key] = (
                design_heatmap.get(key, 0)
                + c.get("count", 0)
            )

        if c.get("systemic"):
            systemic_violations += c.get("count", 0)

    design_system_impact = 0
    if rows:
        design_system_impact = round(
            (systemic_violations / len(rows)) * 100
        )

    adi = 0
    for c in clusters:
        level = c.get("wcag_level")

        wcag_weight = 1
        if level == "AA":
            wcag_weight = 2
        elif level == "AAA":
            wcag_weight = 3

        systemic_weight = 3 if c.get("systemic") else 1

        pages = c.get("pages", 1)
        if pages >= 6:
            page_weight = 3
        elif pages >= 2:
            page_weight = 2
        else:
            page_weight = 1

        adi += wcag_weight * systemic_weight * page_weight * c.get("count", 0)

    top_fixes = {}
    for c in clusters:
        cause = c.get("root_cause")
        if not cause:
            continue

        if cause not in top_fixes:
            top_fixes[cause] = {
                "violations": 0,
                "page_keys": set(),
            }

        top_fixes[cause]["violations"] += c.get("count", 0)

        for page in (c.get("files") or []):
            if page:
                top_fixes[cause]["page_keys"].add(page)

    top_fixes = {
        cause: {
            "violations": data["violations"],
            "pages": len(data["page_keys"]),
        }
        for cause, data in sorted(
            top_fixes.items(),
            key=lambda x: x[1]["violations"],
            reverse=True
        )
    }

    # Pass 'rows' into the builder so it can accurately map pages
    next_best_fixes, next_best_fixes_summary = _build_next_best_fixes(clusters, rows)

    wcag_levels = {}
    for r in rows:
        level = r.get("wcag_level")

        if not level:
            wcag = r.get("wcag")
            if wcag:
                ref = WCAG_SUCCESS_CRITERIA.get(wcag)
                if ref:
                    level = ref.get("level")

        if not level:
            continue

        wcag_levels[level] = wcag_levels.get(level, 0) + 1

    distinct_wcag_criteria = len({
        (r.get("wcag") or "").strip()
        for r in rows
        if (r.get("wcag") or "").strip()
    })

    total_violations = violations
    top_fix_violations = 0
    top_n = 5

    sorted_fixes = sorted(
        top_fixes.items(),
        key=lambda x: x[1]["violations"],
        reverse=True
    )

    for _, data in sorted_fixes[:top_n]:
        top_fix_violations += data["violations"]

    opportunity_score = 0
    if total_violations:
        opportunity_score = round(
            (top_fix_violations / total_violations) * 100
        )

    problem_types = {}
    for r in rows:
        component = (r.get("component") or "other").lower()
        problem = PROBLEM_TYPE_MAP.get(component, "Other")
        problem_types[problem] = problem_types.get(problem, 0) + 1

    problem_types = dict(
        sorted(problem_types.items(), key=lambda x: x[1], reverse=True)
    )

    full_issues_per_page = {}
    for r in rows:
        # Pull the list of files from the row
        pages = r.get("files")
        
        # If 'files' is a list and not empty, iterate through it
        if pages and isinstance(pages, list):
            for page in pages:
                full_issues_per_page[page] = full_issues_per_page.get(page, 0) + 1
        else:
            # Fallback if no files are associated with the row
            full_issues_per_page["unknown"] = full_issues_per_page.get("unknown", 0) + 1

    sorted_page_counts = sorted(
        full_issues_per_page.items(),
        key=lambda x: x[1],
        reverse=True
    )

    issues_per_page = dict(sorted_page_counts[:15])

    agreement_rows = [r for r in rows if _is_strict_agreement_candidate(r)]
    balanced_agreement_rows = [r for r in rows if _is_balanced_agreement_candidate(r)]

    agreement_cluster_rows = collapse_to_agreement_clusters(agreement_rows)
    balanced_agreement_cluster_rows = collapse_to_agreement_clusters(balanced_agreement_rows)

    chart_agreement_rows = collapse_agreement_rows_for_chart(agreement_cluster_rows)
    chart_balanced_agreement_rows = collapse_agreement_rows_for_chart(balanced_agreement_cluster_rows)

    print("ROWS TOTAL:", len(rows))
    print("AGREEMENT ROWS:", len(agreement_rows))
    print("AGREEMENT CLUSTER ROWS:", len(agreement_cluster_rows))
    print("CHART AGREEMENT ROWS:", len(chart_agreement_rows))

    rows_with_sources = sum(1 for r in chart_agreement_rows if r.get("sources"))
    rows_multi_source = sum(
        1 for r in chart_agreement_rows
        if isinstance(r.get("sources"), list) and len(r.get("sources")) > 1
    )

    print("CHART ROWS WITH sources:", rows_with_sources)
    print("CHART ROWS WITH multi-source sources:", rows_multi_source)

    classification_debug = {
        "unique_like": 0,
        "same_family_like": 0,
        "cross_family_like": 0,
    }

    for r in chart_agreement_rows:
        family_count = int(r.get("tool_family_count") or 1)
        sources = r.get("sources") or ([r.get("source")] if r.get("source") else [])

        if len(sources) <= 1:
            classification_debug["unique_like"] += 1
        elif family_count <= 1:
            classification_debug["same_family_like"] += 1
        else:
            classification_debug["cross_family_like"] += 1

    print("CHART CLASSIFICATION DEBUG:", classification_debug)

    axe_pair_context = {
        "pair_only_same_family": 0,
        "pair_with_cross_family": 0,
    }

    for r in chart_agreement_rows:
        sources = set(r.get("sources") or [])
        if {"pa11y-axe", "axe-core"}.issubset(sources):
            if int(r.get("tool_family_count") or 1) > 1:
                axe_pair_context["pair_with_cross_family"] += 1
            else:
                axe_pair_context["pair_only_same_family"] += 1

    print("PA11Y-AXE + AXE-CORE CONTEXT:", axe_pair_context)

    print("SAMPLE MERGED SOURCES:")
    for r in chart_agreement_rows[:10]:
        print({
            "ruleId": r.get("ruleId") or r.get("canonical_rule_id"),
            "source": r.get("source"),
            "sources": r.get("sources"),
            "tool_family_count": r.get("tool_family_count"),
            "tool_engine_count": r.get("tool_engine_count"),
            "result_type": r.get("result_type"),
            "needs_review": r.get("needs_review"),
            "component": r.get("component"),
            "wcag": r.get("wcag"),
        })

    for r in rows[:10]:
        print({
            "ruleId": r.get("ruleId") or r.get("canonical_rule_id"),
            "source": r.get("source"),
            "sources": r.get("sources"),
            "tool_family_count": r.get("tool_family_count"),
            "tool_engine_count": r.get("tool_engine_count"),
        })

    axe_scan_rows = [r for r in rows if (r.get("source") or "").strip().lower() == "axe-scan"]
    print("AXE-SCAN TOTAL ROWS:", len(axe_scan_rows))
    print("AXE-SCAN RESULT TYPES:", sorted({str(r.get("result_type") or "").strip().lower() for r in axe_scan_rows}))
    print("AXE-SCAN NEEDS REVIEW COUNT:", sum(1 for r in axe_scan_rows if r.get("needs_review")))
    print("HTML-SNIFFER RAW ROWS:", sum(1 for r in rows if (r.get("source") or "").strip().lower() == "html-sniffer"))
    print("HTML-SNIFFER STRICT ROWS:", sum(1 for r in agreement_rows if (r.get("source") or "").strip().lower() == "html-sniffer"))

    tool_family_counts = {
        "1_family": 0,
        "2_families": 0,
        "3plus_families": 0,
    }

    tool_engine_counts = {
        "1_engine": 0,
        "2_engines": 0,
        "3plus_engines": 0,
    }

    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    consensus_counts = {"verified": 0, "likely": 0, "single": 0}

    for r in chart_agreement_rows:
        family_count = int(r.get("tool_family_count") or 1)
        engine_count = int(r.get("tool_engine_count") or 1)
        
        # 🔥 NEW: Count the actual number of individual tools!
        sources = r.get("sources") or []
        source_count = len(sources) if len(sources) > 0 else 1
        
        # Tool Family buckets
        if family_count >= 3:
            tool_family_counts["3plus_families"] += 1
        elif family_count == 2:
            tool_family_counts["2_families"] += 1
        else:
            tool_family_counts["1_family"] += 1

        # Tool Engine buckets 
        if engine_count >= 3:
            tool_engine_counts["3plus_engines"] += 1
        elif engine_count == 2:
            tool_engine_counts["2_engines"] += 1
        else:
            tool_engine_counts["1_engine"] += 1
            
        # 🔥 FIX 1: Consensus (Cross-Tool Overlap) - Use source_count instead of engine_count
        if source_count >= 3:
            consensus_counts["verified"] += 1
        elif source_count == 2:
            consensus_counts["likely"] += 1
        else:
            consensus_counts["single"] += 1
            
        # 🔥 FIX 2: Evidence Confidence - Use source_count for the 'Established' tier
        if family_count >= 2:
            # Caught by completely different tool families (e.g. axe + htmlcs)
            confidence_counts["high"] += 1
        elif source_count >= 2:
            # Caught by multiple tools sharing an engine (e.g. axe-core + axe-scan)
            confidence_counts["medium"] += 1
        else:
            # Only caught by one tool
            confidence_counts["low"] += 1

    tool_agreement_profile = {
        source: {
            "multi_family": 0,
            "same_family_only": 0,
            "unique": 0,
            "total": 0,
            "multi_family_pct": 0,
            "same_family_only_pct": 0,
            "unique_pct": 0,
        }
        for source in sorted(source_counts.keys())
    }

    tool_engine_agreement_profile = {
        source: {
            "multi_engine": 0,
            "same_engine_only": 0,
            "unique": 0,
            "total": 0,
            "multi_engine_pct": 0,
            "same_engine_only_pct": 0,
            "unique_pct": 0,
        }
        for source in sorted(source_counts.keys())
    }

    for r in chart_agreement_rows:
        sources = list(r.get("sources") or [])
        if not sources:
            source = r.get("source")
            if source:
                sources = [source]

        if not sources:
            continue

        source_families = {source: get_tool_family(source) for source in sources}
        source_engines = {source: get_tool_engine(source) for source in sources}

        for source in sources:
            family_bucket = tool_agreement_profile.setdefault(source, {
                "multi_family": 0,
                "same_family_only": 0,
                "unique": 0,
                "total": 0,
                "multi_family_pct": 0,
                "same_family_only_pct": 0,
                "unique_pct": 0,
            })

            engine_bucket = tool_engine_agreement_profile.setdefault(source, {
                "multi_engine": 0,
                "same_engine_only": 0,
                "unique": 0,
                "total": 0,
                "multi_engine_pct": 0,
                "same_engine_only_pct": 0,
                "unique_pct": 0,
            })

            family_bucket["total"] += 1
            engine_bucket["total"] += 1

            if len(sources) == 1:
                family_bucket["unique"] += 1
                engine_bucket["unique"] += 1
                continue

            this_family = source_families[source]
            other_families = {
                family
                for other_source, family in source_families.items()
                if other_source != source
            }

            if any(family != this_family for family in other_families):
                family_bucket["multi_family"] += 1
            else:
                family_bucket["same_family_only"] += 1

            this_engine = source_engines[source]
            other_engines = {
                engine
                for other_source, engine in source_engines.items()
                if other_source != source
            }

            if any(engine != this_engine for engine in other_engines):
                engine_bucket["multi_engine"] += 1
            else:
                engine_bucket["same_engine_only"] += 1

    for source, stats in tool_agreement_profile.items():
        total = stats["total"] or 1
        stats["multi_family_pct"] = round((stats["multi_family"] / total) * 100)
        stats["same_family_only_pct"] = round((stats["same_family_only"] / total) * 100)
        stats["unique_pct"] = round((stats["unique"] / total) * 100)

    for source, stats in tool_engine_agreement_profile.items():
        total = stats["total"] or 1
        stats["multi_engine_pct"] = round((stats["multi_engine"] / total) * 100)
        stats["same_engine_only_pct"] = round((stats["same_engine_only"] / total) * 100)
        stats["unique_pct"] = round((stats["unique"] / total) * 100)

    shared_source_findings = sum(
        c.get("count", 0)
        for c in clusters
        if c.get("design_system_issue") or c.get("systemic") or c.get("root_cause")
    )

    shared_source_rate = 0
    if violations:
        shared_source_rate = round((shared_source_findings / violations) * 100)

    top5_pages_list = [page for page, _ in sorted_page_counts[:5]]
    top5_page_issue_total = sum(count for _, count in sorted_page_counts[:5])

    # 1. Calculate the total from the same source as sorted_page_counts
    total_issues_in_page_list = sum(count for _, count in sorted_page_counts)
    
    # 2. Use that total as the denominator
    top5_page_concentration = 0
    if total_issues_in_page_list > 0:
        top5_page_concentration = round((top5_page_issue_total / total_issues_in_page_list) * 100)

    frame_rows = [
        r for r in rows
        if (r.get("component") or "").lower() == "frame"
    ]

    frame_pages_set = set(
        (r.get("page") or "unknown")
        for r in frame_rows
    )

    frame_issues = len(frame_rows)
    frame_pages = len(frame_pages_set)
    frame_pages_list = list(frame_pages_set)

    # print("DEBUG METRICS:", {
    #     "violations": violations,
    #     "shared_source_rate": shared_source_rate,
    #     "top5_page_concentration": top5_page_concentration,
    # })
    print(f"DEBUG: Calculated shared_pattern_impact: {shared_pattern_impact}")
    return {
        "issuesperpage": issues_per_page,
        "violations": violations,
        "pages_list": list(unique_pages),
        "pages_count": len(unique_pages), 
        "pages": list(unique_pages),
        "source_counts": source_counts,
        "component_heatmap": component_heatmap,
        "design_heatmap": design_heatmap,
        "component_risk": component_risk,
        "design_system_impact": design_system_impact,
        "shared_source_rate": shared_source_rate,
        "top5_page_concentration": top5_page_concentration,
        "top5_pages_list": top5_pages_list,
        "accessibility_debt_index": adi,
        "top_fixes": top_fixes,
        "next_best_fixes": next_best_fixes,
        "next_best_fixes_summary": next_best_fixes_summary,
        "wcag_levels": wcag_levels,
        "distinct_wcag_criteria": distinct_wcag_criteria,
        "accessibility_opportunity_score": opportunity_score,
        "confidence_counts": confidence_counts,
        "consensus_counts": consensus_counts,
        "tool_family_counts": tool_family_counts,
        "tool_engine_counts": tool_engine_counts,
        "tool_agreement_profile": tool_agreement_profile,
        "tool_family_agreement_profile": tool_agreement_profile,
        "tool_engine_agreement_profile": tool_engine_agreement_profile,
        "clusters": clusters,
        "suggested_components": get_suggested_components(),
        "frame_issues": frame_issues,
        "frame_pages": frame_pages,
        "frame_pages_list": frame_pages_list,
        "problem_types": problem_types,
        "shared_pattern_impact": shared_pattern_impact,
    }