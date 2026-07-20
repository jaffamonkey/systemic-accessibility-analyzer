import re


def _looks_like_wcag_code(value):
    if not value:
        return False

    text = str(value).strip()

    # Plain WCAG code, optionally with technique tag like [G17]
    if re.fullmatch(r"\d+\.\d+\.\d+(?:\s*\[[A-Z0-9]+\])?", text):
        return True

    # HTML_CodeSniffer style rule ids
    if text.startswith("WCAG2"):
        return True

    return False


def _humanize_rule_id(rule_id):
    if not rule_id:
        return ""
    text = str(rule_id).strip().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.title()


def format_rule_label(cluster):
    rule_name = cluster.get("rule_name")
    wcag = cluster.get("wcag")
    title = cluster.get("wcag_title")
    rule = cluster.get("ruleId")

    if rule_name and not _looks_like_wcag_code(rule_name):
        return str(rule_name)

    if rule and not _looks_like_wcag_code(rule):
        return _humanize_rule_id(rule)

    if title:
        return str(title)

    if wcag:
        return str(wcag)

    return rule or "Unknown"
