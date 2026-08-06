from adapters.registry import register_adapter


ALFA_RULE_MAP = {
    "sia-r2": {
        "wcag": "1.1.1",
        "wcag_level": "A",
        "rule_name": "Image has accessible name",
        "component_hint": "image",
    },
    "sia-r41": {
        "wcag": "2.4.4",
        "wcag_level": "A",
        "rule_name": "Links with identical accessible names have equivalent purpose",
        "component_hint": "link",
    },
    "sia-r65": {
        "wcag": "2.4.7",
        "wcag_level": "AA",
        "rule_name": "Element in sequential focus order has visible focus",
        "component_hint": "keyboard",
    },
    "sia-r66": {
        "wcag": "1.4.3",
        "wcag_level": "AA",
        "rule_name": "Text contrast",
        "component_hint": "text",
    },
    "sia-r69": {
        "wcag": "1.4.3",
        "wcag_level": "AA",
        "rule_name": "Text has minimum contrast",
        "component_hint": "text",
    },
    "sia-r71": {
        "wcag": "1.4.8",
        "wcag_level": "AAA",
        "rule_name": "Paragraphs of text are not justified",
        "component_hint": "typography",
    },
    "sia-r73": {
        "wcag": "1.4.8",
        "wcag_level": "AAA",
        "rule_name": "Paragraphs of text have sufficient line height",
        "component_hint": "typography",
    },
    "sia-r74": {
        "wcag": "1.4.8",
        "wcag_level": "AAA",
        "rule_name": "Paragraphs of text do not have font sizes defined in absolute units",
        "component_hint": "typography",
    },
    "sia-r80": {
        "wcag": "1.4.8",
        "wcag_level": "AAA",
        "rule_name": "Paragraphs of text do not have line heights defined in absolute units",
        "component_hint": "typography",
    },
    "sia-r81": {
        "wcag": "2.4.4",
        "wcag_level": "A",
        "rule_name": "Links with identical accessible names and context serve equivalent purpose",
        "component_hint": "link",
    },
    "sia-r87": {
        "wcag": "2.4.1",
        "wcag_level": "A",
        "rule_name": "First focusable element is link to main content",
        "component_hint": "navigation",
    },
    "sia-r90": {
        "wcag": None,
        "wcag_level": None,
        "rule_name": "Tabbable descendants",
        "component_hint": "keyboard",
    },
    "sia-r111": {
        "wcag": "2.5.8",
        "wcag_level": "AAA",
        "rule_name": "Target Size (enhanced)",
        "component_hint": "interactive",
    },
    "sia-r113": {
        "wcag": "2.5.8",
        "wcag_level": "AA",
        "rule_name": "Target Size (Minimum)",
        "component_hint": "interactive",
    },
    "sia-r17": {
        "wcag": "4.1.2",
        "wcag_level": "A",
        "rule_name": "Elements with aria-hidden must not be focusable",
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
            
            # 🔥 FIX: Alfa uses 'serializationId' which looks like '#my-id' instead of HTML
            # We map this to pattern/selector, and leave DOM empty rather than injecting it
            "dom": "",
            "selector": target_id,
            "pattern": target_id,
            "display_pattern": rule_name,
            
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

