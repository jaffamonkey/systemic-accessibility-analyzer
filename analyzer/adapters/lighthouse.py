from adapters.registry import register_adapter


def detect_lighthouse(data):
    return isinstance(data, dict) and "lighthouseVersion" in data


SEVERITY_MAP = {
    "critical": "critical",
    "serious": "serious",
    "moderate": "moderate",
    "minor": "minor",
}


def _normalize_severity(value, default="serious"):
    if value is None:
        return default
    return SEVERITY_MAP.get(str(value).strip().lower(), default)


def _extract_wcag_criteria(tags):
    out = []
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        if not t.startswith("wcag"):
            continue
        suffix = t[4:]
        if suffix.isdigit() and len(suffix) >= 3:
            out.append(".".join(suffix))
    seen = set()
    deduped = []
    for item in out:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _wcag_level_from_tags(tags):
    level = None
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        if t.endswith("aaa"):
            return "AAA"
        if t.endswith("aa"):
            level = "AA"
        elif t.endswith("a") and level is None:
            level = "A"
    return level


def _push(out, file, page_url, audit_id, audit, item, result_type):
    debug = ((audit.get("details") or {}).get("debugData")) or {}
    tags = debug.get("tags") or []
    wcag_criteria = _extract_wcag_criteria(tags)
    wcag_level = _wcag_level_from_tags(tags)

    node = (item or {}).get("node") or {}
    selector = node.get("selector") or ""
    html = node.get("snippet") or ""
    explanation = node.get("explanation")

    out.append({
        "file": file,
        "page_url": page_url,
        "url": page_url,
        "ruleId": audit_id,
        "rule_name": audit.get("title") or audit_id,
        "message": explanation or audit.get("title") or audit_id,
        
        # 🔥 FIX: Isolate DOM to purely HTML snippets and route selector to pattern
        "dom": html,
        "selector": selector,
        "pattern": selector,
        "display_pattern": audit.get("title") or audit_id,
        
        "html": html,
        "severity": _normalize_severity(debug.get("impact")),
        "source": "lighthouse",
        "result_type": result_type,
        "needs_review": result_type != "violation",
        "wcag_criteria": wcag_criteria,
        "wcag_level": wcag_level,
        "helpUrl": audit.get("description"),
        "score": audit.get("score"),
        "scoreDisplayMode": audit.get("scoreDisplayMode"),
    })


def adapt_lighthouse(file, data):
    out = []
    page_url = data.get("finalUrl") or data.get("finalDisplayedUrl") or data.get("mainDocumentUrl") or data.get("requestedUrl")

    audits = data.get("audits", {})

    for audit_id, audit in audits.items():
        score = audit.get("score")
        score_display_mode = audit.get("scoreDisplayMode")
        details = audit.get("details", {}) or {}
        items = details.get("items", []) or []
        debug = details.get("debugData") or {}
        tags = debug.get("tags") or []

        if not tags:
            continue

        if score != 0:
            continue

        result_type = "violation"
        if score_display_mode in {"informative", "manual"}:
            result_type = "warning"

        if not items:
            _push(out, file, page_url, audit_id, audit, {}, result_type)
            continue

        for item in items:
            _push(out, file, page_url, audit_id, audit, item, result_type)

    return out


register_adapter(detect_lighthouse, adapt_lighthouse)