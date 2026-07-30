from adapters.registry import register_adapter
import re


def detect_oobee(data):
    if not isinstance(data, dict):
        return False
    return (
        "url" in data
        and any(k in data for k in ("mustFix", "goodToFix", "needsReview", "passed"))
        and isinstance(data.get("pageTitle"), str)
    )


CATEGORY_DEFAULT_SEVERITY = {
    "mustFix": "serious",
    "goodToFix": "moderate",
    "needsReview": "moderate",
}

CATEGORY_RESULT_TYPE = {
    "mustFix": "violation",
    "goodToFix": "warning",
    "needsReview": "potentialviolation",
}

CONFORMANCE_LEVEL_RE = re.compile(r"wcag(?:2|21|22)?(aaa|aa|a)\b", re.I)


def _extract_wcag_from_conformance(conformance):
    if not conformance:
        return None
    for ref in conformance:
        text = str(ref or "").lower()
        match = re.search(r"wcag(\d)(\d)(\d)", text)
        if match:
            return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    return None


def _extract_wcag_level_from_conformance(conformance):
    if not conformance:
        return None
    for ref in conformance:
        text = str(ref or "").strip()
        match = CONFORMANCE_LEVEL_RE.search(text)
        if not match:
            continue
        level = match.group(1).upper()
        if level in {"A", "AA", "AAA"}:
            return level
    return None


def _severity_for_bucket(bucket_name, rule_obj):
    axe_impact = str((rule_obj or {}).get("axeImpact") or "").strip().lower()
    if axe_impact:
        return axe_impact
    return CATEGORY_DEFAULT_SEVERITY.get(bucket_name, "moderate")


def _result_type_for_bucket(bucket_name):
    return CATEGORY_RESULT_TYPE.get(bucket_name, "warning")


def _needs_review_for_bucket(bucket_name):
    return bucket_name in {"goodToFix", "needsReview"}


def adapt_oobee(file, data):
    out = []
    page_url = data.get("url")
    page_title = data.get("pageTitle")

    for bucket_name in ("mustFix", "goodToFix", "needsReview"):
        bucket = data.get(bucket_name) or {}
        rules = bucket.get("rules") or {}
        for rule_id, rule_obj in rules.items():
            description = rule_obj.get("description")
            help_url = rule_obj.get("helpUrl")
            conformance = rule_obj.get("conformance") or []
            wcag = _extract_wcag_from_conformance(conformance)
            wcag_level = _extract_wcag_level_from_conformance(conformance)
            severity = _severity_for_bucket(bucket_name, rule_obj)
            result_type = _result_type_for_bucket(bucket_name)
            needs_review = _needs_review_for_bucket(bucket_name)

            for item in rule_obj.get("items") or []:
                message = item.get("message") or description or rule_id
                selector = item.get("xpath") or item.get("selector") or ""
                html = item.get("html") or ""
                item_url = item.get("url") or page_url

                out.append({
                    "file": file,
                    "page_url": item_url,
                    "url": item_url,
                    "ruleId": rule_id,
                    "rule_name": description or rule_id,
                    "message": message,
                    
                    # 🔥 FIX: Isolate DOM to purely HTML snippets and route selector to pattern
                    "dom": html,
                    "selector": selector,
                    "pattern": selector,
                    "display_pattern": description or rule_id,
                    
                    "html": html,
                    "severity": severity,
                    "wcag": wcag,
                    "wcag_criteria": [wcag] if wcag else [],
                    "wcag_level": wcag_level,
                    "helpUrl": help_url,
                    "source": "oobee",
                    "result_type": result_type,
                    "needs_review": needs_review,
                    "status_bucket": bucket_name,
                    "tool_category": bucket_name,
                    "page_title": page_title,
                    "axeImpact": rule_obj.get("axeImpact"),
                    "conformance": conformance,
                })

    return out


register_adapter(detect_oobee, adapt_oobee)