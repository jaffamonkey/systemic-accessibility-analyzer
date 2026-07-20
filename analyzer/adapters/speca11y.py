from adapters.registry import register_adapter

WCAG_LEVEL_MAP = {
    "1.1.1": "A",
    "1.3.1": "A",
    "1.3.2": "A",
    "1.4.3": "AA",
    "1.4.4": "AA",
    "1.4.11": "AA",
    "1.4.12": "AA",
    "1.4.13": "AA",
    "2.1.1": "A",
    "2.4.1": "A",
    "2.4.3": "A",
    "2.4.4": "A",
    "2.4.7": "AA",
    "2.5.3": "A",
    "3.2.3": "AA",
    "3.3.3": "AA",
    "4.1.2": "A",
}

SEVERITY_MAP = {
    "critical": "critical",
    "serious": "serious",
    "moderate": "moderate",
    "minor": "minor",
    "warning": "moderate",
    "info": "minor",
}

RESULT_TYPE_MAP = {
    "violation": "violation",
    "warning": "warning",
    "incomplete": "needs_review",
    "canttell": "needs_review",
    "review": "needs_review",
}

def detect_speca11y(data):
    return (
        isinstance(data, dict)
        and isinstance(data.get("summary"), dict)
        and isinstance(data.get("entries"), list)
        and any(
            isinstance(entry, dict)
            and isinstance(entry.get("rule"), dict)
            and isinstance(entry.get("results"), list)
            for entry in data.get("entries", [])
        )
    )

def _first(value):
    if isinstance(value, list) and value:
        return value[0]
    return None

def _wcag_level(criteria):
    levels = [
        WCAG_LEVEL_MAP.get(str(code).strip())
        for code in criteria or []
        if WCAG_LEVEL_MAP.get(str(code).strip())
    ]

    if "A" in levels:
        return "A"
    if "AA" in levels:
        return "AA"
    if "AAA" in levels:
        return "AAA"

    return None

def _normalise_severity(value):
    return SEVERITY_MAP.get(str(value or "").strip().lower(), "moderate")

def _normalise_result_type(value):
    return RESULT_TYPE_MAP.get(str(value or "").strip().lower(), "warning")

def _normalise_element(element):
    if not isinstance(element, dict):
        return {
            "selector": "",
            "dom": "",
            "html": "",
            "accessible_name": None,
            "role": None,
            "bounding_box": None,
        }

    selector = (
        element.get("cssSelector")
        or element.get("selector")
        or element.get("xpath")
        or ""
    )

    html = element.get("html") or ""
    accessible_name = element.get("accessibleName")
    role = element.get("role")

    dom = html or selector or ""

    return {
        "selector": selector,
        "dom": dom,
        "html": html,
        "accessible_name": accessible_name,
        "role": role,
        "bounding_box": element.get("boundingBox"),
    }

def _is_page_level(element):
    return not (element.get("selector") or element.get("html") or element.get("dom"))

def adapt_speca11y(file, data):
    out = []

    summary = data.get("summary") or {}
    page_url = summary.get("url") or data.get("url")
    scanned_at = summary.get("timestamp")
    tool_version = summary.get("version") or data.get("version")

    for entry in data.get("entries") or []:

        rule = entry.get("rule") or {}

        entry_rule_id = (
            rule.get("id")
            or rule.get("ruleId")
            or "speca11y-rule"
        )

        rule_name = (
            rule.get("name")
            or rule.get("title")
            or entry_rule_id
        )

        wcag_criteria = rule.get("wcagCriteria") or []
        wcag = _first(wcag_criteria)
        wcag_level = _wcag_level(wcag_criteria)

        wcag3 = (
            rule.get("wcag3")
            or rule.get("wcag3Criteria")
            or rule.get("wcag3Outcomes")
            or rule.get("silver")
        )

        for result in entry.get("results") or []:

            result_rule_id = result.get("ruleId") or entry_rule_id

            message = (
                result.get("message")
                or rule.get("description")
                or rule_name
                or result_rule_id
            )

            result_type = _normalise_result_type(result.get("type"))

            # Ignore execution failures.
            if (
                result_type == "needs_review"
                and "timed out" in message.lower()
            ):
                continue

            needs_review = result_type != "violation"

            element = _normalise_element(result.get("element") or {})

            # 🔥 NEW FIX: Scrub the rule ID from the DOM to prevent it mimicking an element
            if element["selector"] == result_rule_id or element["dom"] == result_rule_id:
                element["selector"] = ""
                element["dom"] = ""
                element["html"] = ""

            is_page_level = _is_page_level(element)

            issue_scope = (
                "page"
                if is_page_level
                else "dom"
            )

            out.append({

                # File / page
                "file": file,
                "page_url": page_url,
                "url": page_url,

                # Rule
                "ruleId": result_rule_id,
                "rule_id": result_rule_id,
                "rule_name": rule_name,
                "rule_label": rule_name,

                # Display / clustering
                "display_pattern": rule_name,
                "pattern": result_rule_id,

                # Scope
                "issue_scope": issue_scope,

                # Message
                "message": message,
                "description": rule.get("description"),

                # DOM
                "dom": "" if is_page_level else element["dom"],
                "selector": "" if is_page_level else element["selector"],
                "html": "" if is_page_level else element["html"],

                # Component
                "component": (
                    "document_metadata"
                    if is_page_level
                    else None
                ),

                # Severity
                "severity": _normalise_severity(
                    rule.get("severity")
                ),

                "source": "speca11y",

                "result_type": result_type,
                "needs_review": needs_review,

                # WCAG
                "wcag": wcag,
                "wcag_criteria": wcag_criteria,
                "wcag_level": wcag_level,

                # Help
                "helpUrl": (
                    rule.get("helpUrl")
                    or rule.get("url")
                ),

                # Confidence
                "confidence": rule.get("confidence"),

                # SpecA11y metadata
                "speca11y_rule_id": result_rule_id,
                "speca11y_rule_type": rule.get("type"),
                "speca11y_result_type": result.get("type"),
                "speca11y_tags": rule.get("tags", []),
                "speca11y_wcag3": wcag3,

                # Element metadata
                "accessible_name": element["accessible_name"],
                "role": element["role"],
                "bounds": element["bounding_box"],

                # Scan metadata
                "scanned_at": scanned_at,
                "engine_version": tool_version,
            })

    return out

register_adapter(detect_speca11y, adapt_speca11y)