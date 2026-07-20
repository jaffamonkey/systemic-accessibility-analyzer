from adapters.registry import register_adapter


ALFA_RULE_MAP = {
    "sia-r2": {
        "wcag": "1.1.1",
        "wcag_level": "A",
        "rule_name": "Image has accessible name",
        "component_hint": "image",
    },
    "sia-r66": {
        "wcag": "1.4.3",
        "wcag_level": "AA",
        "rule_name": "Text contrast",
        "component_hint": "text",
    },
    "sia-r90": {
        "wcag": None,
        "wcag_level": None,
        "rule_name": "Tabbable descendants",
        "component_hint": "keyboard",
    },
}


def detect_alfa(data):
    return (
        isinstance(data, dict)
        and data.get("tool") == "alfa"
        and isinstance(data.get("result"), dict)
        and isinstance(data["result"].get("outcomes"), list)
    )


def _rule_id_from_uri(uri):
    return str(uri or "alfa-rule").rstrip("/").split("/")[-1]


def _message_and_threshold(expectations):
    for expectation in expectations or []:
        if not isinstance(expectation, list) or len(expectation) < 2:
            continue

        payload = expectation[1] or {}
        err = payload.get("error") or {}
        val = payload.get("value") or {}

        message = err.get("message") or val.get("message")
        threshold = err.get("threshold") or val.get("threshold")

        if message or threshold:
            return message, threshold

    return None, None


def _wcag_for(rule_id, threshold=None):
    meta = ALFA_RULE_MAP.get(rule_id, {})
    wcag = meta.get("wcag")
    wcag_level = meta.get("wcag_level")

    if rule_id == "sia-r66" and threshold is not None:
        try:
            threshold_value = float(threshold)
            if threshold_value >= 7:
                return "1.4.6", "AAA"
            if threshold_value >= 4.5:
                return "1.4.3", "AA"
        except Exception:
            pass

    return wcag, wcag_level

def _normalise_alfa_target(target):
    if isinstance(target, dict):
        return target

    if isinstance(target, list):
        for t in target:
            if isinstance(t, dict):
                return t

    return {}

def adapt_alfa(file, data):
    out = []
    page_url = data.get("url")
    result = data.get("result") or {}
    outcomes = result.get("outcomes") or []
    alfa_version = result.get("alfaVersion")

    for item in outcomes:
        outcome = str(item.get("outcome") or "").lower()

        if outcome in {"passed", "inapplicable"}:
            continue
            
        rule = item.get("rule") or {}
        rule_uri = rule.get("uri")
        rule_id = _rule_id_from_uri(rule_uri)

        message, threshold = _message_and_threshold(item.get("expectations"))
        wcag, wcag_level = _wcag_for(rule_id, threshold)
        meta = ALFA_RULE_MAP.get(rule_id, {})

        # NEW - normalise the target here
        target = _normalise_alfa_target(item.get("target"))

        if not target and item.get("target") is not None:
            print(f"⚠️ Unexpected Alfa target format: {type(item.get('target'))}")
        target_id = target.get("serializationId") or target.get("internalId") or ""
        target_type = target.get("type")

        rule_name = meta.get("rule_name") or rule_id

        diagnostic = item.get("diagnostic") or {}
        diagnostic_message = diagnostic.get("message")

        row_message = message or diagnostic_message or rule_uri or rule_id

        if diagnostic_message and diagnostic_message not in str(row_message):
            row_message = f"{row_message} ({diagnostic_message})"

        if outcome == "failed":
            severity = "serious"
            result_type = "violation"
            needs_review = False
            review_status = "confirmed"
        elif outcome == "canttell":
            severity = "warning"
            result_type = "needs_review"
            needs_review = True
            review_status = "needs-review"
        else:
            severity = "minor"
            result_type = "advisory"
            needs_review = True
            review_status = outcome or "unknown"

        out.append({
            "file": file,
            "page_url": page_url,
            "url": page_url,
            "ruleId": rule_id,
            "rule_name": rule_name,
            "message": row_message,
            "dom": target_id or row_message or rule_id,
            "selector": target_id,
            "html": "",
            "severity": severity,
            "source": "alfa",
            "result_type": result_type,
            "needs_review": needs_review,
            "review_status": review_status,
            "helpUrl": rule_uri,
            "wcag": wcag,
            "wcag_level": wcag_level,
            "alfa_outcome": outcome,
            "alfa_threshold": threshold,
            "target_type": target_type,
            "component_hint": meta.get("component_hint"),
            "engine_version": alfa_version,
        })

    return out


register_adapter(detect_alfa, adapt_alfa)
