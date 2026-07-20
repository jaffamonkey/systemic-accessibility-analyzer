from adapters.registry import register_adapter
import re


def detect_avalpdf(data):
    return isinstance(data, dict) and data.get("report_type") == "multi_file_analysis"


PDF_ISSUE_RULE_MAP = {
    "document is not tagged": "document-not-tagged",
    "document metadata is missing title property": "document-metadata-is-missing-title-property",
    "document metadata is missing language property": "document-language-is-not-set",
    "document has no headings - every document should have at least an h1 heading": "document-has-no-headings",
}

PDF_RULE_WCAG_MAP = {
    "document-not-tagged": (["1.3.1"], "A"),
    "document-metadata-is-missing-title-property": (["2.4.2"], "A"),
    "document-language-is-not-set": (["3.1.1"], "A"),
    "document-has-no-headings": (["1.3.1", "2.4.6"], "AA"),
    "pdf-layout-with-spaces": (["1.3.2"], "A"),
    "pdf-smart-apostrophe-encoding": ([], None),
}

SEVERITY_MAP = {
    "error": "serious",
    "warning": "moderate",
}


def _normalize_severity(value, default="moderate"):
    if value is None:
        return default
    return SEVERITY_MAP.get(str(value).strip().lower(), default)


def _wcag_for_rule(rule_id):
    return PDF_RULE_WCAG_MAP.get(rule_id, ([], None))


def normalize_pdf_issue(issue_text):
    text = str(issue_text or "").strip().lower()

    if not text:
        return "pdf-unknown-issue"

    if text in PDF_ISSUE_RULE_MAP:
        return PDF_ISSUE_RULE_MAP[text]

    if "consecutive spaces" in text and "attempting layout with spaces" in text:
        return "pdf-layout-with-spaces"

    if "incorrect accent usage" in text and "right single quotation mark" in text:
        return "pdf-smart-apostrophe-encoding"

    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "pdf-unknown-issue"


def _push(out, filename, message, level):
    rule = normalize_pdf_issue(message)
    wcag_criteria, wcag_level = _wcag_for_rule(rule)
    result_type = "warning" if str(level).strip().lower() == "warning" else "violation"

    out.append({
        "file": filename,
        "page_url": None,
        "url": None,
        "ruleId": rule,
        "rule_name": rule.replace("-", " ").title(),
        "message": message,
        "dom": "pdf-document",
        "selector": "pdf-document",
        "html": "",
        "severity": _normalize_severity(level),
        "source": "avalpdf",
        "result_type": result_type,
        "needs_review": result_type != "violation",
        "is_audit_note": False,
        "wcag": wcag_criteria[0] if wcag_criteria else None,
        "wcag_criteria": wcag_criteria,
        "wcag_level": wcag_level,
        "document_type": "pdf",
        "tool_family": "pdf",
    })


def adapt_avalpdf(file, data):
    out = []

    for file_result in data.get("files", []):
        filename = file_result.get("file_name") or file

        for issue in file_result.get("issues", []):
            _push(out, filename, issue, "error")

        for warning in file_result.get("warnings", []):
            _push(out, filename, warning, "warning")

    return out


register_adapter(detect_avalpdf, adapt_avalpdf)