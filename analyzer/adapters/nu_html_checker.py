from adapters.registry import register_adapter


NU_MESSAGE_MAP = {
    "duplicate id": {
        "wcag": "4.1.1",
        "wcag_level": "A",
        "rule_name": "Duplicate ID",
    },
    "bad value": {
        "wcag": None,
        "wcag_level": None,
        "rule_name": "Invalid value",
    },
    "attribute": {
        "wcag": None,
        "wcag_level": None,
        "rule_name": "HTML attribute issue",
    },
    "aria": {
        "wcag": "4.1.2",
        "wcag_level": "A",
        "rule_name": "ARIA validity",
    },
}


def detect_nu_html_checker(data):
    return (
        isinstance(data, dict)
        and data.get("tool") == "nu-html-checker"
        and isinstance(data.get("result"), dict)
        and isinstance(data["result"].get("messages"), list)
    )


def _severity(msg_type, subtype):
    msg_type = str(msg_type or "").lower()
    subtype = str(subtype or "").lower()

    if msg_type == "error":
        return "serious"
    if subtype == "warning" or msg_type == "info":
        return "warning"
    return "minor"


def _result_type(msg_type):
    return "violation" if str(msg_type or "").lower() == "error" else "warning"


def _rule_from_message(message, msg_type, subtype):
    text = str(message or "").lower()

    for needle, meta in NU_MESSAGE_MAP.items():
        if needle in text:
            return (
                f"nu-html-checker-{needle.replace(' ', '-')}",
                meta.get("rule_name"),
                meta.get("wcag"),
                meta.get("wcag_level"),
            )

    fallback = subtype or msg_type or "message"
    return (
        f"nu-html-checker-{str(fallback).lower()}",
        str(fallback).title(),
        None,
        None,
    )


def adapt_nu_html_checker(file, data):
    out = []
    page_url = data.get("url")
    result = data.get("result") or {}
    messages = result.get("messages") or []
    version = result.get("version")

    for msg in messages:
        msg_type = str(msg.get("type") or "").lower()
        subtype = str(msg.get("subType") or "").lower()
        message = msg.get("message") or "Nu HTML Checker message"

        rule_id, rule_name, wcag, wcag_level = _rule_from_message(
            message,
            msg_type,
            subtype,
        )

        line = msg.get("lastLine")
        column = msg.get("lastColumn")
        extract = msg.get("extract") or ""

        out.append({
            "file": file,
            "page_url": page_url,
            "url": page_url,
            "ruleId": rule_id,
            "rule_name": rule_name,
            "message": message,
            "dom": extract or message,
            "selector": "",
            "html": extract,
            "severity": _severity(msg_type, subtype),
            "source": "nu-html-checker",
            "result_type": _result_type(msg_type),
            "needs_review": msg_type != "error",
            "line": line,
            "column": column,
            "target": f"line {line}, column {column}" if line or column else "",
            "wcag": wcag,
            "wcag_level": wcag_level,
            "engine_version": version,
        })

    return out


register_adapter(detect_nu_html_checker, adapt_nu_html_checker)
