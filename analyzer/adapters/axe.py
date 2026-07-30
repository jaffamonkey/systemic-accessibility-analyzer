from adapters.registry import register_adapter


def detect_axe(data):
    return isinstance(data, dict) and "violations" in data


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


def _normalize_source(value):
    source = str(value or "").strip().lower()
    if source in {"axe-core", "axe", "axe core"}:
        return "axe-core"
    return source or "axe-core"


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


def _soften_audit_note(rule, result_type):
    rule_id = str(rule.get("id") or "").strip().lower()

    if rule_id == "frame-tested":
        return {
            "result_type": "warning",
            "needs_review": True,
            "is_audit_note": True,
            "severity": "minor",
            "message_override": (
                "Frame content may require separate accessibility review. "
                "This is an audit coverage note rather than a confirmed defect."
            ),
        }

    return {
        "result_type": result_type,
        "needs_review": result_type == "incomplete",
        "is_audit_note": False,
        "severity": rule.get("impact"),
        "message_override": None,
    }


def _push(out, file, page_url, source, result_type, rule, node=None, **extra):
    node = node or {}
    target = node.get("target") or [""]
    selector = target[0] if isinstance(target, list) and target else ""
    html = node.get("html") or ""

    softened = _soften_audit_note(rule, result_type)

    row = {
        "file": file,
        "page_url": page_url,
        "url": page_url,
        "ruleId": rule.get("id") or "axe-rule",
        "rule_name": rule.get("help") or rule.get("description") or rule.get("id") or "axe-rule",
        "message": softened["message_override"] or _build_message(rule, node),
        
        # 🔥 FIX: Explicitly assign HTML to DOM and map selector directly to pattern
        "dom": html,
        "selector": selector,
        "pattern": selector,
        "display_pattern": rule.get("help") or rule.get("description") or rule.get("id") or "axe-rule",
        
        "html": html,
        "severity": _normalize_severity(softened["severity"]),
        "source": _normalize_source(source),
        "result_type": softened["result_type"],
        "needs_review": softened["needs_review"],
        "is_audit_note": softened["is_audit_note"],
        "node_impact": node.get("impact"),
    }
    row.update({k: v for k, v in extra.items() if v is not None})
    out.append(row)


def adapt_axe(file, data):
    out = []

    meta = data.get("meta") or {}
    page_url = data.get("url") or meta.get("url")
    source = ((data.get("testEngine") or {}).get("name")) or data.get("tool") or "axe-core"
    source_version = (data.get("testEngine") or {}).get("version")
    run_tags = (((data.get("toolOptions") or {}).get("runOnly") or {}).get("values")) or meta.get("tags") or []
    conformance_level = _wcag_level_from_tags(run_tags)

    common = {
        "source_version": source_version,
        "conformance_level": conformance_level,
    }

    for rule in data.get("violations", []) or []:
        wcag_criteria = _extract_wcag_criteria(rule.get("tags"))
        wcag_level = _wcag_level_from_tags(rule.get("tags")) or conformance_level
        nodes = rule.get("nodes", []) or [{}]
        for node in nodes:
            _push(
                out,
                file,
                page_url,
                source,
                "violation",
                rule,
                node=node,
                helpUrl=rule.get("helpUrl"),
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                **common,
            )

    for rule in data.get("incomplete", []) or []:
        wcag_criteria = _extract_wcag_criteria(rule.get("tags"))
        wcag_level = _wcag_level_from_tags(rule.get("tags")) or conformance_level
        nodes = rule.get("nodes", []) or [{}]
        for node in nodes:
            _push(
                out,
                file,
                page_url,
                source,
                "incomplete",
                rule,
                node=node,
                helpUrl=rule.get("helpUrl"),
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                **common,
            )

    return out


register_adapter(detect_axe, adapt_axe)