import re
from analyzer.utils import clean_dynamic_selectors

def normalize(value):
    return str(value or "").strip().lower()


def _coerce_selector_value(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            if item is None:
                continue

            if isinstance(item, dict):
                extracted = ""
                for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
                    candidate = item.get(key)
                    if candidate:
                        extracted = str(candidate)
                        break
                if not extracted:
                    extracted = str(item)
                parts.append(extracted)
            else:
                parts.append(str(item))

        return " ".join(p for p in parts if p).strip()

    if isinstance(value, dict):
        for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
            candidate = value.get(key)
            if candidate:
                return str(candidate).strip()
        return str(value).strip()

    return str(value).strip()


def build_selector_signature(selector):
    selector = _coerce_selector_value(selector)

    if not selector:
        return ""

    # 🔥 Intercept and scrub before signature hashes are computed
    s = clean_dynamic_selectors(selector)

    s = selector.lower()
    s = re.sub(r":nth-child\(\d+\)", "", s)
    s = re.sub(r":nth-of-type\(\d+\)", "", s)
    s = re.sub(r"\[\d+\]", "", s)

    tag = ""
    classes = re.findall(r"\.([a-zA-Z0-9_-]+)", s)
    ids = re.findall(r"#([a-zA-Z0-9_-]+)", s)

    tag_match = re.match(r"^[a-z]+", s)
    if tag_match:
        tag = tag_match.group(0)

    classes = sorted(classes)[:2]
    ids = sorted(ids)[:1]
    return " ".join([tag] + classes + ids).strip()


# def build_violation_key(r):
#     page = (
#         r.get("page")
#         or r.get("url")
#         or r.get("file")
#         or r.get("document")
#         or "unknown"
#     )

#     wcag = normalize(r.get("wcag"))
#     rule_id = normalize(r.get("ruleId") or r.get("rule_id") or r.get("rule"))
#     selector = build_selector_signature(
#         r.get("selector")
#         or r.get("dom")
#         or r.get("target")
#         or r.get("xpath")
#         or r.get("path")
#         or ""
#     )

#     canonical_rule = wcag or rule_id

#     parts = [str(page), canonical_rule, selector]

#     if not canonical_rule:
#         parts.append(normalize(r.get("message") or r.get("description")))

#     return "|".join(parts)

# MORE EXTREME

def build_violation_key(r):
    page = (
        r.get("page")
        or r.get("url")
        or r.get("file")
        or r.get("document")
        or "unknown"
    )

    wcag = normalize(r.get("wcag"))
    rule_id = normalize(r.get("ruleId") or r.get("rule_id") or r.get("rule"))
    selector = build_selector_signature(
        r.get("selector")
        or r.get("dom")
        or r.get("target")
        or r.get("xpath")
        or r.get("path")
        or ""
    )

    canonical_rule = wcag or rule_id

    parts = [str(page), canonical_rule]

    weak_selectors = {"", "*", "/", "div", "span", "body", "html", "unknown"}

    if selector not in weak_selectors:
        parts.append(selector)

    if not canonical_rule:
        parts.append(normalize(r.get("message") or r.get("description")))

    return "|".join(parts)


# THE MOST EXTREME (SELECTOR FULLY OPtIONAL)

# def build_violation_key(r):
#     page = (
#         r.get("page")
#         or r.get("url")
#         or r.get("file")
#         or r.get("document")
#         or "unknown"
#     )

#     wcag = normalize(r.get("wcag"))
#     rule_id = normalize(r.get("ruleId") or r.get("rule_id") or r.get("rule"))

#     canonical_rule = wcag or rule_id

#     parts = [str(page), canonical_rule]

#     if not canonical_rule:
#         parts.append(normalize(r.get("message") or r.get("description")))

#     return "|".join(parts)

# def build_violation_key(r):
#     page = (
#         r.get("page")
#         or r.get("url")
#         or r.get("file")
#         or r.get("document")
#         or "unknown"
#     )

#     wcag = normalize(r.get("wcag"))
#     rule_id = normalize(r.get("ruleId") or r.get("rule_id") or r.get("rule"))

#     selector = build_selector_signature(
#         r.get("selector")
#         or r.get("dom")
#         or r.get("target")
#         or r.get("xpath")
#         or r.get("path")
#         or ""
#     )

#     canonical_rule = wcag or rule_id

#     parts = [str(page), canonical_rule]

#     weak_selectors = {
#         "",
#         "*",
#         "/",
#         "div",
#         "span",
#         "body",
#         "html",
#         "unknown",
#     }

#     if selector and selector not in weak_selectors:
#         parts.append(selector)
#     else:
#         message = normalize(r.get("message") or r.get("description") or "")
#         if message:
#             message_words = message.split()[:8]
#             parts.append("msg:" + "_".join(message_words))

#     return "|".join(parts)
