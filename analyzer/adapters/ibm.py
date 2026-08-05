from adapters.registry import register_adapter


def detect_ibm(data):
    return isinstance(data, dict) and ("results" in data or "report" in data)


SEVERITY_MAP = {
    "violation": "serious",
    "potentialviolation": "moderate",
    "recommendation": "minor",
}


IBM_RULE_WCAG_MAP = {
    "html_lang_exists": (["3.1.1"], "A"),
    "html_skipnav_exists": (["2.4.1"], "A"),
    "table_headers_exists": (["1.3.1"], "A"),
    "img_alt_valid": (["1.1.1"], "A"),
    "input_label_exists": (["3.3.2", "4.1.2"], "A"),
    "area_alt_exists": (["1.1.1"], "A"),
    "a_text_purpose": (["2.4.4"], "A"),
    "imagemap_alt_exists": (["1.1.1"], "A"),
    "style_color_misuse": (["1.3.3"], "A"),
    "text_contrast_sufficient": (["1.4.3"], "AA"),
    "element_tabbable_visible": (["2.4.7"], "AA"),
    "aria_descendant_valid": (["1.3.1"], "A"),
    "style_focus_visible": (["2.4.7"], "AA"),
    "text_sensory_misuse": (["1.3.3"], "A"),
    "element_tabbable_unobscured": (["2.4.11"], "AA"),
    "element_tabbable_role_valid": (["4.1.2"], "A"),
    "element_id_unique": (["4.1.1"], "A"),
    "aria_form_label_unique": (["1.3.1"], "A"),
    "aria_role_valid": (["4.1.2"], "A"),
    "aria_parent_required": (["1.3.1"], "A"),
    "input_label_exists": (["3.3.2", "4.1.2"], "A"),
    "widget_tabbable_exists": (["2.1.1"], "A"),
    "blockquote_cite_exists": (["Best Practice"], None)
}


def _normalize_severity(level):
    if level is None:
        return "moderate"
    return SEVERITY_MAP.get(str(level).strip().lower(), "moderate")


def _wcag_for_rule(rule_id):
    return IBM_RULE_WCAG_MAP.get(rule_id, ([], None))


def _extract_path_fields(result):
    path = result.get("path") or {}
    selector = ""
    dom = ""

    if isinstance(path, dict):
        selector = (
            path.get("css")
            or path.get("selector")
            or path.get("xpath")
            or path.get("dom")
            or ""
        )
        dom = path.get("dom") or ""
    elif isinstance(path, str):
        selector = path

    return selector, dom, path


def _friendly_rule_name(result, rule_id):
    return (
        result.get("reasonId")
        or result.get("message")
        or result.get("help")
        or rule_id
    )


def _push(out, file, page_url, result, result_type):
    rule_id = result.get("ruleId")
    wcag_criteria, wcag_level = _wcag_for_rule(rule_id)

    selector, dom, raw_path = _extract_path_fields(result)
    html = result.get("snippet") or ""

    is_review = result_type != "violation"
    is_audit_note = result_type == "recommendation"

    out.append({
        "file": file,
        "page_url": page_url,
        "url": page_url,
        "ruleId": rule_id,
        "rule_name": _friendly_rule_name(result, rule_id),
        "message": result.get("message") or rule_id,
        "dom": dom or html or selector or (result.get("message") or rule_id),
        "selector": selector,
        "html": html,
        "severity": _normalize_severity(result.get("level")),
        "source": "ibm",
        "result_type": result_type,
        "needs_review": is_review,
        "is_audit_note": is_audit_note,
        "wcag_criteria": wcag_criteria,
        "wcag_level": wcag_level,
        "helpUrl": result.get("help"),
        "reasonId": result.get("reasonId"),
        "ibm_value": result.get("value"),
        "ibm_level": result.get("level"),
        "ignored": result.get("ignored"),
        "ibm_path": raw_path,
        "bounds": result.get("bounds"),
        "category": result.get("category"),
        "ruleGroup": result.get("ruleGroup"),
    })


def adapt_ibm(file, data):
    out = []

    report = data.get("report") or {}
    results = data.get("results") or report.get("results", [])
    page_url = data.get("url") or report.get("url")

    for r in results:
        level = str(r.get("level") or "").strip().lower()

        if level == "violation":
            _push(out, file, page_url, r, "violation")
        elif level == "potentialviolation":
            _push(out, file, page_url, r, "potentialviolation")
        elif level == "recommendation":
            _push(out, file, page_url, r, "recommendation")

    return out


register_adapter(detect_ibm, adapt_ibm)