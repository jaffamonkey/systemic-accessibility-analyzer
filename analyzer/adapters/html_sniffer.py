from adapters.registry import register_adapter
import html
import re


WCAG_RE = re.compile(r"\d+\.\d+\.\d+")
STYLE_ATTR_RE = re.compile(r'\sstyle="[^"]*"', re.I)
DATA_ATTR_RE = re.compile(r"\sdata-[\w-]+=\"[^\"]*\"", re.I)
NOISY_ATTR_RE = re.compile(
    r'\s(?:tabindex|aria-describedby|data-google-[\w-]+|data-google[\w-]*)="[^"]*"',
    re.I,
)

SEVERITY_MAP = {
    "error": "serious",
    "warning": "moderate",
    "notice": "minor",
}


def _clean(value):
    return str(value or "").strip()


def _compact(value: str, max_len: int = 220) -> str:
    text = " ".join(_clean(value).split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _normalize_severity(value, default="moderate"):
    if value is None:
        return default
    return SEVERITY_MAP.get(str(value).strip().lower(), default)


def _wcag_level_from_rule(rule: str | None):
    s = str(rule or "").upper()
    if "WCAG2AAA" in s or "WCAG21AAA" in s or "WCAG22AAA" in s:
        return "AAA"
    if "WCAG2AA" in s or "WCAG21AA" in s or "WCAG22AA" in s:
        return "AA"
    if "WCAG2A" in s or "WCAG21A" in s or "WCAG22A" in s:
        return "A"
    return None


def _clean_html_snippet(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""

    text = text.replace('\\"', '"')
    text = html.unescape(text)

    text = STYLE_ATTR_RE.sub(' style="[omitted]"', text)
    text = DATA_ATTR_RE.sub("", text)
    text = NOISY_ATTR_RE.sub("", text)

    text = " ".join(text.split())
    return text


def _derive_selector_from_html(html_snippet: str, fallback: str = "") -> str:
    html_snippet = _clean(html_snippet)
    if not html_snippet:
        return _clean(fallback)

    match = re.match(r"<([a-zA-Z0-9:_-]+)([^>]*)>", html_snippet)
    if not match:
        return _clean(fallback)

    tag = match.group(1).lower()
    attrs = match.group(2) or ""

    id_match = re.search(r'\sid="([^"]+)"', attrs, re.I)
    class_match = re.search(r'\sclass="([^"]+)"', attrs, re.I)

    selector = tag
    if id_match:
        selector += f"#{id_match.group(1).strip()}"

    if class_match:
        classes = [c for c in class_match.group(1).split() if c]
        if classes:
            selector += "".join(f".{c}" for c in classes[:4])

    return selector or _clean(fallback)


def _extract_target_fields(parts):
    candidates = [_clean(p) for p in parts[2:] if _clean(p)]

    html_snippet = next((p for p in reversed(candidates) if "<" in p and ">" in p), "")
    html_snippet = _clean_html_snippet(html_snippet)

    selector_candidate = next(
        (
            p for p in candidates
            if p and p != html_snippet and any(
                token in p.lower()
                for token in (
                    "#", ".", ">", "[", "/",
                    "xpath", "html", "body",
                    "form", "button", "input", "select",
                    "textarea", "img", "iframe", "label", "a"
                )
            )
        ),
        ""
    )

    selector = (
        _derive_selector_from_html(html_snippet, selector_candidate)
        or _clean(selector_candidate)
        or (candidates[0] if candidates else "")
    )

    dom_path = html_snippet or _clean(selector_candidate) or selector
    return selector, dom_path, html_snippet


def adapt_htmlcs(file, data):
    out = []

    for entry in data:
        log = _clean(entry.get("log"))
        if not log:
            continue

        parts = [p.strip() for p in log.split("|", 5)]

        if len(parts) < 5:
            continue

        severity = parts[0].replace("[HTMLCS]", "").strip().lower()
        if severity == "notice":
            continue

        rule = _clean(parts[1])
        target = _clean(parts[2]) if len(parts) > 2 else ""
        context = _clean(parts[3]) if len(parts) > 3 else ""
        message = _clean(parts[4]) if len(parts) > 4 else ""
        html_snippet = _clean(parts[5]) if len(parts) > 5 else ""

        cleaned_html = _clean_html_snippet(html_snippet)
        selector, dom_path, extracted_html = _extract_target_fields(
            [parts[0], parts[1], target, context, message, cleaned_html]
        )

        wcag_match = WCAG_RE.search(rule)
        wcag = wcag_match.group(0) if wcag_match else None
        wcag_level = _wcag_level_from_rule(rule)

        page_url = (
            entry.get("url")
            or entry.get("page_url")
            or entry.get("page")
            or entry.get("document")
        )

        clean_message = _compact(message or context or target or rule, 260)
        display_dom = _compact(dom_path or selector or target, 220)

        out.append({
            "file": file,
            "page_url": page_url,
            "url": page_url,
            "ruleId": rule,
            "rule_name": rule,
            "message": clean_message,
            "dom": dom_path or target or rule,
            "selector": selector or target,
            "dom_path": dom_path or selector or target,
            "html": extracted_html or cleaned_html,
            "severity": _normalize_severity(severity),
            "source": "html-sniffer",
            "wcag": wcag,
            "wcag_criteria": [wcag] if wcag else [],
            "wcag_level": wcag_level,
            "result_type": "warning" if severity == "warning" else "violation",
            "needs_review": severity == "warning",
            "is_audit_note": False,
            "raw_log": log,

            "display_message": clean_message,
            "display_dom_path": display_dom,
            "raw_html": html_snippet,
            "target": target,
            "context": context,
        })

    return out


def detect_htmlcs(data):
    return (
        isinstance(data, list)
        and len(data) > 0
        and isinstance(data[0], dict)
        and "log" in data[0]
    )


register_adapter(detect_htmlcs, adapt_htmlcs)