from adapters.registry import register_adapter


def detect_axe_scan(data):
    return (
        isinstance(data, list)
        and len(data) > 0
        and isinstance(data[0], dict)
        and "Rule Type" in data[0]
        and "HTML Element" in data[0]
        and "DOM Element" in data[0]
        and "axe-scan Version" in data[0]
    )


def _normalize_result_type(result_type: str | None) -> str:
    value = str(result_type or "").strip().lower()
    if value == "violations":
        return "violation"
    if value == "incomplete":
        return "potentialviolation"
    return value or "violation"


def _needs_review(result_type: str | None) -> bool:
    return _normalize_result_type(result_type) != "violation"


def adapt_axe_scan(file, data):
    out = []

    for item in data:
        url = item.get("URL")
        rule_id = item.get("Rule Type")
        result_type = item.get("Result Type")
        wcag = item.get("WCAG Criteria") or None

        out.append({
            "file": file,
            "page_url": url,
            "url": url,
            "ruleId": rule_id,
            "rule_name": rule_id,
            "message": item.get("Message") or item.get("Help") or rule_id,
            
            # 🔥 FIX: Isolate DOM to purely HTML snippets and route selector to pattern
            "dom": item.get("HTML Element") or "",
            "selector": item.get("DOM Element") or "",
            "pattern": item.get("DOM Element") or "",
            "display_pattern": rule_id,
            
            "html": item.get("HTML Element"),
            "severity": item.get("Impact"),
            "source": "axe-scan",
            "result_type": _normalize_result_type(result_type),
            "needs_review": _needs_review(result_type),
            "wcag": wcag,
            "wcag_criteria": [wcag] if wcag else [],
            "wcag_level": None,
            "help": item.get("Help"),
            "helpUrl": item.get("Help URL"),
            "rule_set": item.get("Rule Set"),
            "result_condition": item.get("Result Condition"),
            "result_condition_index": item.get("Result Condition Index"),
            "axe_scan_version": item.get("axe-scan Version"),
        })

    return out


register_adapter(detect_axe_scan, adapt_axe_scan)