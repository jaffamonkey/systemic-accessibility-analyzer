"""
Rule Normalizer

A lightweight pre-processor that attempts to extract standardized WCAG 
criteria strings (e.g., '1.4.3') from messy, tool-specific rule IDs 
before they hit the main resolution pipeline.
"""

import re

def normalize_rule(rule: str | None) -> str | None:
    """
    Cleans up common proprietary rule IDs by extracting embedded WCAG numbers 
    or mapping specific high-frequency Axe-core rules.
    """
    if not rule:
        return None

    rule = rule.lower()

    # Extract standard dot-notation WCAG numbers (e.g., "wcag1.4.3" -> "1.4.3")
    match = re.search(r"(\d)\.(\d)\.(\d)", rule)
    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    # Extract underscore-notation WCAG numbers used by some tools (e.g., "1_4_3")
    match = re.search(r"(\d)_(\d)_(\d)", rule)
    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    # Hardcoded fallbacks for Axe-core's most common proprietary names
    if "color-contrast" in rule:
        return "1.4.3"

    if "aria-hidden" in rule:
        return "4.1.2"

    return rule