"""
Rule Formatter

Prepares human-readable labels for accessibility rules to be displayed 
on the dashboard. It prioritizes descriptive names over raw WCAG codes 
or technical slugs to ensure the BI reports are readable by non-technical 
stakeholders.
"""

import re

def _looks_like_wcag_code(value: str | None) -> bool:
    """
    Checks if a string is a raw technical WCAG code (e.g., '1.4.3' or 'WCAG2AA...').
    Used to deprioritize these in favor of plain-English rule names.
    """
    if not value:
        return False

    text = str(value).strip()

    # Matches plain WCAG codes, optionally with technique tags like [G17]
    if re.fullmatch(r"\d+\.\d+\.\d+(?:\s*\[[A-Z0-9]+\])?", text):
        return True

    # Matches HTML_CodeSniffer style proprietary rule IDs
    if text.startswith("WCAG2"):
        return True

    return False


def _humanize_rule_id(rule_id: str | None) -> str:
    """Converts a technical slug (e.g., 'color-contrast') into Title Case."""
    if not rule_id:
        return ""
    text = str(rule_id).strip().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.title()


def format_rule_label(cluster: dict) -> str:
    """
    Determines the best human-readable label for a cluster of issues.
    Evaluates candidates in order of readability: 
    Rule Name > Humanized Rule ID > WCAG Title > Raw WCAG Code.
    """
    rule_name = cluster.get("rule_name")
    wcag = cluster.get("wcag")
    title = cluster.get("wcag_title")
    rule = cluster.get("ruleId")

    # 1. Prefer an explicit, plain-English rule name provided by the tool
    if rule_name and not _looks_like_wcag_code(rule_name):
        return str(rule_name)

    # 2. Fall back to a humanized version of the tool's proprietary rule ID
    if rule and not _looks_like_wcag_code(rule):
        return _humanize_rule_id(rule)

    # 3. Fall back to the official W3C WCAG Title (e.g., 'Contrast (Minimum)')
    if title:
        return str(title)

    # 4. Fall back to the raw WCAG code (e.g., '1.4.3')
    if wcag:
        return str(wcag)

    # 5. Last resort
    return rule or "Unknown"