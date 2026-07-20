import re
from adapters.registry import register_adapter


def detect_pa11y(data):
    return isinstance(data, dict) and "issues" in data


AXE_RULE_WCAG_MAP = {
    "area-alt": (["1.1.1"], "A"),
    "button-name": (["4.1.2"], "A"),
    "bypass": (["2.4.1"], "A"),
    "html-has-lang": (["3.1.1"], "A"),
    "image-alt": (["1.1.1"], "A"),
    "input-image-alt": (["1.1.1"], "A"),
    "label": (["3.3.2", "4.1.2"], "A"),
    "landmark-one-main": (["1.3.1"], "A"),
    "link-name": (["2.4.4", "4.1.2"], "A"),
    "listitem": (["1.3.1"], "A"),
    "meta-viewport": (["1.4.4"], "AA"),
    "target-size": (["2.5.8"], "AA"),
    "color-contrast": (["1.4.3"], "AA"),
    "identical-links-same-purpose": (["2.4.9"], "AAA"),
    "meta-refresh-no-exceptions": (["2.2.1"], "AAA"),
    "p-as-heading": (["1.3.1", "2.4.6"], "AAA"),
}

SEVERITY_MAP = {
    "error": "serious",
    "warning": "moderate",
    "notice": "minor",
    "critical": "critical",
    "serious": "serious",
    "moderate": "moderate",
    "minor": "minor",
}


def _normalize_severity(value, default="moderate"):
    if value is None:
        return default
    return SEVERITY_MAP.get(str(value).strip().lower(), default)


def extract_wcag_from_htmlcs(code):
    if not code:
        return None
    match = re.search(r"(\d)_(\d)_(\d)", str(code))
    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    return None


def detect_issue_runner(issue, file=None, data=None):
    issue_runner = str(issue.get("runner") or "").lower().strip()
    if issue_runner in {"axe", "htmlcs"}:
        return issue_runner

    code = str(issue.get("code") or "")
    runner_extras = issue.get("runnerExtras") or {}

    if extract_wcag_from_htmlcs(code):
        return "htmlcs"

    if runner_extras.get("impact") or runner_extras.get("help") or runner_extras.get("helpUrl"):
        return "axe"

    path = str(file or "").lower()
    if "htmlcs" in path or "html_codesniffer" in path or "codesniffer" in path:
        return "htmlcs"
    if "pa11y-axe" in path or "pa11y_axe" in path:
        return "axe"

    runner = data.get("runner") or data.get("engine") or data.get("testRunner") if isinstance(data, dict) else None
    runner_str = str(runner or "").lower()
    if "htmlcs" in runner_str or "html_codesniffer" in runner_str or "codesniffer" in runner_str:
        return "htmlcs"
    if "axe" in runner_str:
        return "axe"

    return "unknown"


def _htmlcs_level_from_code(code):
    s = str(code or "").upper()
    if "WCAG2AAA" in s or "WCAG22AAA" in s or "WCAG21AAA" in s:
        return "AAA"
    if "WCAG2AA" in s or "WCAG22AA" in s or "WCAG21AA" in s:
        return "AA"
    if "WCAG2A" in s or "WCAG22A" in s or "WCAG21A" in s:
        return "A"
    return None


def _source_from_runner(runner):
    if runner == "axe":
        return "pa11y-axe"
    if runner == "htmlcs":
        return "pa11y-htmlcs"
    return "pa11y"


def _soften_frame_tested(issue, runner, result_type, severity):
    code = str(issue.get("code") or "").strip().lower()
    if runner == "axe" and code == "frame-tested":
        return {
            "result_type": "warning",
            "severity": "minor",
            "needs_review": True,
            "message": (
                "Frame content may require separate accessibility review. "
                "This is an audit coverage note rather than a confirmed defect."
            ),
            "is_audit_note": True,
        }

    return {
        "result_type": result_type,
        "severity": severity,
        "needs_review": result_type != "violation",
        "message": issue.get("message"),
        "is_audit_note": False,
    }


def _push(out, file, page_url, issue, runner, wcag_criteria, wcag_level, result_type, severity):
    runner_extras = issue.get("runnerExtras") or {}
    selector = issue.get("selector") or ""
    html = issue.get("context") or ""
    rule_name = (
        runner_extras.get("help")
        or runner_extras.get("description")
        or issue.get("message")
        or issue.get("code")
    )

    softened = _soften_frame_tested(issue, runner, result_type, severity)

    out.append({
        "file": file,
        "page_url": page_url,
        "url": page_url,
        "ruleId": issue.get("code"),
        "rule_name": rule_name,
        "message": softened["message"],
        "dom": selector or html or softened["message"] or issue.get("message"),
        "selector": selector,
        "html": html,
        "severity": _normalize_severity(softened["severity"]),
        "source": _source_from_runner(runner),
        "runner": runner,
        "result_type": softened["result_type"],
        "needs_review": softened["needs_review"],
        "is_audit_note": softened["is_audit_note"],
        "wcag": wcag_criteria[0] if wcag_criteria else None,
        "wcag_criteria": wcag_criteria,
        "wcag_level": wcag_level,
        "helpUrl": runner_extras.get("helpUrl"),
        "runner_impact": runner_extras.get("impact"),
        "typeCode": issue.get("typeCode"),
        "original_rule": runner_extras.get("originalRule"),
        "original_runner": runner_extras.get("originalRunner"),
    })


def adapt_pa11y(file, data):
    out = []
    page_url = data.get("pageUrl")

    for issue in data.get("issues", []) or []:
        code = issue.get("code")
        issue_type = str(issue.get("type") or "").lower()
        runner = detect_issue_runner(issue, file=file, data=data)

        if issue_type == "error":
            result_type = "violation"
        elif issue_type in {"warning", "notice"}:
            result_type = "warning"
        else:
            result_type = "warning"

        if runner == "axe":
            wcag_criteria, wcag_level = AXE_RULE_WCAG_MAP.get(str(code or ""), ([], None))
            severity = (issue.get("runnerExtras") or {}).get("impact") or issue.get("type")
        else:
            wcag = extract_wcag_from_htmlcs(code)
            wcag_criteria = [wcag] if wcag else []
            wcag_level = _htmlcs_level_from_code(code)
            severity = issue.get("type")

        _push(
            out,
            file,
            page_url,
            issue,
            runner,
            wcag_criteria,
            wcag_level,
            result_type,
            severity,
        )

    return out


register_adapter(detect_pa11y, adapt_pa11y)