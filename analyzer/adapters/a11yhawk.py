from adapters.registry import register_adapter

SEVERITY_MAP = {
    "critical": "critical",
    "serious": "serious",
    "high": "serious",
    "moderate": "moderate",
    "medium": "moderate",
    "minor": "minor",
    "low": "minor",
}


def _normalize_severity(value, default="serious"):
    if value is None:
        return default
    return SEVERITY_MAP.get(str(value).strip().lower(), default)


def _extract_wcag_criteria(tags_or_criteria):
    if not tags_or_criteria:
        return []

    if isinstance(tags_or_criteria, str):
        tags_or_criteria = [tags_or_criteria]

    out = []
    for tag in tags_or_criteria:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        if t == "unknown":
            continue
        if t.startswith("wcag"):
            suffix = t.replace("wcag", "").strip()
            if "." in suffix:
                out.append(suffix)
        elif "." in t and t.replace(".", "").isdigit():
            out.append(t)

    seen = set()
    deduped = []
    for item in out:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def detect_a11yhawk(data):
    return isinstance(data, dict) and data.get("tool") == "a11yhawk"


def adapt_a11yhawk(file, data):
    out = []
    page_url = data.get("url", "unknown_url")
    result = data.get("result") or {}

    issues = result.get("issues", [])

    for issue in issues:
        # 1. Use patternDetected (e.g., 'color-contrast') for rule grouping
        pattern_detected = issue.get("patternDetected") or ""
        rule_id = pattern_detected or issue.get("id") or "a11yhawk-issue"

        # 2. Extract location and code context
        location = issue.get("location") or ""
        code_context = issue.get("codeContext") or ""

        # Build fallback selector string so pattern is never empty / "Unknown"
        raw_selector = (
            issue.get("selector")
            or issue.get("target")
            or (location if location and location != "[unknown element]" else "")
            or pattern_detected
            or rule_id
        )

        html = code_context or issue.get("html") or issue.get("snippet") or ""

        # 3. Handle WCAG criteria and Level
        wcag_raw = issue.get("wcagCriteria") or issue.get("tags") or []
        wcag_criteria = _extract_wcag_criteria(wcag_raw)
        wcag_level = issue.get("wcagLevel")
        if wcag_level == "unknown":
            wcag_level = None

        rule_name = issue.get("title") or rule_id
        message = issue.get("impact") or issue.get("userImpact") or rule_name

        out.append(
            {
                "file": file,
                "page_url": page_url,
                "url": page_url,
                "ruleId": rule_id,
                "rule_name": rule_name,
                "message": message,
                "dom": html,
                "selector": raw_selector,
                "pattern": pattern_detected or raw_selector,
                "display_pattern": rule_name,
                "html": html,
                "severity": _normalize_severity(
                    issue.get("severity") or issue.get("impact")
                ),
                "source": "a11yhawk",
                "result_type": "violation",
                "needs_review": False,
                "wcag_criteria": wcag_criteria,
                "wcag_level": wcag_level,
                "helpUrl": issue.get("recommendation") or "",
            }
        )

    return out


register_adapter(detect_a11yhawk, adapt_a11yhawk)