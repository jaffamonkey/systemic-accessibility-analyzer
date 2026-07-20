from adapters.registry import register_adapter


def detect_generic_axe(data):
    if not isinstance(data, dict):
        return False

    if "violations" not in data:
        return False

    violations = data.get("violations", [])
    if not violations:
        return False

    return isinstance(violations[0], dict) and "nodes" in violations[0]


SEVERITY_MAP = {
    "minor": "minor",
    "low": "minor",
    "moderate": "moderate",
    "medium": "moderate",
    "serious": "serious",
    "high": "serious",
    "critical": "critical",
    "severe": "critical",
}


def _normalize_severity(value, default="moderate"):
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


def _build_message(rule, node):
    parts = []

    for bucket in ("any", "all", "none"):
        for check in node.get(bucket, []) or []:
            msg = check.get("message")
            if msg:
                parts.append(msg)

    failure_summary = node.get("failureSummary")
    if failure_summary:
        parts.append(failure_summary)

    return " | ".join(parts) or rule.get("help") or rule.get("description") or rule.get("id") or "axe-rule"


def adapt_generic_axe(file, data):
    out = []

    source = data.get("tool") or "axe"
    page_url = data.get("url") or data.get("page_url") or data.get("page") or data.get("document")
    source_version = ((data.get("testEngine") or {}).get("version")) or data.get("version")

    common = {
        "source_version": source_version,
    }

    for v in data.get("violations", []) or []:
        rule_id = v.get("id") or "axe-rule"
        rule_name = v.get("help") or v.get("description") or rule_id
        wcag_criteria = _extract_wcag_criteria(v.get("tags"))
        wcag_level = _wcag_level_from_tags(v.get("tags"))

        for node in v.get("nodes", []) or [{}]:
            target = node.get("target") or [""]
            selector = target[0] if isinstance(target, list) and target else ""
            html = node.get("html") or ""

            out.append({
                "file": file,
                "page_url": page_url,
                "url": page_url,
                "ruleId": rule_id,
                "rule_name": rule_name,
                "message": _build_message(v, node),
                "dom": selector or html or rule_name,
                "selector": selector,
                "html": html,
                "severity": _normalize_severity(v.get("impact")),
                "source": source,
                "result_type": "violation",
                "needs_review": False,
                "wcag_criteria": wcag_criteria,
                "wcag_level": wcag_level,
                "helpUrl": v.get("helpUrl"),
                **common,
            })

    for v in data.get("incomplete", []) or []:
        rule_id = v.get("id") or "axe-incomplete"
        rule_name = v.get("help") or v.get("description") or rule_id
        wcag_criteria = _extract_wcag_criteria(v.get("tags"))
        wcag_level = _wcag_level_from_tags(v.get("tags"))

        for node in v.get("nodes", []) or [{}]:
            target = node.get("target") or [""]
            selector = target[0] if isinstance(target, list) and target else ""
            html = node.get("html") or ""

            out.append({
                "file": file,
                "page_url": page_url,
                "url": page_url,
                "ruleId": rule_id,
                "rule_name": rule_name,
                "message": _build_message(v, node),
                "dom": selector or html or rule_name,
                "selector": selector,
                "html": html,
                "severity": _normalize_severity(v.get("impact")),
                "source": source,
                "result_type": "incomplete",
                "needs_review": True,
                "wcag_criteria": wcag_criteria,
                "wcag_level": wcag_level,
                "helpUrl": v.get("helpUrl"),
                **common,
            })

    return out


register_adapter(detect_generic_axe, adapt_generic_axe)