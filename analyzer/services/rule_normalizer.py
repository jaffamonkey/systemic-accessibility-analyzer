import re

def normalize_rule(rule):

    if not rule:
        return None

    rule = rule.lower()

    # extract wcag numbers
    match = re.search(r"(\d)\.(\d)\.(\d)", rule)

    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    match = re.search(r"(\d)_(\d)_(\d)", rule)

    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    # axe common names
    if "color-contrast" in rule:
        return "1.4.3"

    if "aria-hidden" in rule:
        return "4.1.2"

    return rule