"""
Component Detector

The heuristic engine responsible for translating raw, messy DOM strings 
and CSS selectors into standardized Design System components. It uses a 
waterfall approach: checking explicit HTML tags, contextual hierarchy, 
historical learned patterns, and finally keyword matching.
"""

import re
from analyzer.utils import clean_dynamic_selectors, simplify_pattern
from analyzer.component_config import COMPONENT_PATTERNS
from analyzer.component_learning import load_learning, LEARNING

DESIGN_SYSTEM_PATTERNS = {
    "landmarks": ["header", "nav", "main", "footer", "aside", "section", "article"],
    "interactive": ["btn", "button", "cta", "trigger", "toggle", "menu", "dropdown", "modal", "dialog"],
    "navigation": ["breadcrumb", "pagination", "tabs", "navbar", "sidebar"],
    "feedback": ["alert", "error", "success", "warning", "hint", "tooltip", "status"],
    "forms": ["input", "select", "textarea", "checkbox", "radio", "fieldset", "legend"]
}


def get_emerging_patterns() -> list:
    """Surfaces high-frequency, unclassified DOM patterns for the dashboard."""
    learning = load_learning()
    results = []

    for pattern, data in learning.items():
        if data.get("count", 0) < 5:
            continue

        results.append({
            "pattern": pattern,
            "count": data.get("count", 0),
            "component": data.get("component"),
            "confidence": data.get("confidence", 0)
        })

    return sorted(results, key=lambda x: x["count"], reverse=True)[:20]


def detect_design_system(pattern: str) -> str | None:
    """Uses regex boundaries to determine if a pattern belongs to a core design system category."""
    if not pattern:
        return None

    p = pattern.lower()

    for group, keywords in DESIGN_SYSTEM_PATTERNS.items():
        for k in keywords:
            if k.endswith('-') or k.endswith('_'):
                regex = rf'\b{re.escape(k)}'
            else:
                regex = rf'\b{re.escape(k)}\b'
            
            if re.search(regex, p):
                return group

    return None


def parse_pattern(pattern: str) -> list:
    """
    Breaks a standard CSS selector into hierarchy parts.
    Example: 'nav > ul > li.menu-item > a' -> ['nav', 'ul', 'li.menu-item', 'a']
    """
    if not pattern:
        return []
    # Split by CSS combinators (space, >, +, ~)
    parts = re.split(r'\s*(?:>|\+|~|\s)\s*', pattern.strip())
    return [p for p in parts if p and p not in {'>', '+', '~'}]


def _get_base_tag(element_selector: str) -> str:
    """Extracts the base HTML tag from a complex element selector (e.g., 'a.btn#id' -> 'a')."""
    match = re.match(r'^([a-zA-Z0-9]+)', element_selector)
    return match.group(1) if match else ""


def detect_component(dom: str, selector: str = None) -> str:
    """
    The primary waterfall pipeline for identifying a UI component.
    Evaluates in order: Exclusions -> Explicit Target -> Hierarchy -> Machine Learning -> Keywords.
    """
    dom = clean_dynamic_selectors(dom)
    selector = clean_dynamic_selectors(selector)

    text = f"{dom or ''} {selector or ''}".lower().strip()

    if "alfa-opaque-node-hash" in text:
        return "third_party"

    pattern = simplify_pattern(text)
    parts = parse_pattern(pattern)

    if not parts:
        return "other"

    # Isolate the exact element targeted by the rule
    last_element = parts[-1]
    base_tag = _get_base_tag(last_element)

    # 1. PRIORITY: HTML Base Tag
    if base_tag == "a": return "link"
    if base_tag == "button": return "button"
    if base_tag in ["input", "textarea", "select", "fieldset", "legend"]: return "form"
    if base_tag in ["img", "svg"]: return "image"
    if base_tag in ["li"]: return "list"
    if base_tag in ["iframe"]: return "frame"

    # 2. CONTEXT-AWARE BOOST (Looking up the parsed DOM tree)
    if "nav" in parts: return "navigation"
    if "ul" in parts or "ol" in parts: return "list"
    if "table" in parts: return "table"
    if "form" in parts: return "form"

    # 3. MACHINE LEARNING OVERRIDE
    if pattern in LEARNING and LEARNING[pattern].get("component"):
        return LEARNING[pattern]["component"]

    # 4. KEYWORD MATCH (Catches customized class names like '.primary-cta')
    for comp, keywords in COMPONENT_PATTERNS.items():
        if any(k in pattern for k in keywords):
            return comp

    # 5. FALLBACK
    if len(parts) == 1 and base_tag in ["div", "section", "container", "header", "main", "footer"]:
        return "layout"

    return "other"


def detect_root_cause(rule: str, component: str, message: str) -> str:
    """Provides a human-readable explanation of why a systemic issue is occurring."""
    text = f"{rule} {component} {message}".lower()

    if "contrast" in text: return "Design system color palette or theme tokens"
    if component == "Buttons": return "Shared button component implementation"
    if component == "Forms": return "Form field component missing accessible label pattern"
    if component == "Images": return "Image component missing alt attribute or CMS content issue"
    if component == "Tables": return "Table component missing headers or scope attributes"
    if "aria" in text: return "ARIA attributes incorrectly implemented in component"
    if "label" in text: return "Form labels not programmatically associated"

    return "Likely reusable component or template issue"


def detect_design_system_issue(cluster: dict) -> str | None:
    """
    Evaluates a specific cluster's properties to determine if it is a 
    systemic issue requiring a fix at the Design System level.
    """
    rule = (cluster.get("ruleId") or "").lower()
    wcag = cluster.get("wcag")
    component = (cluster.get("component") or "").lower()

    if wcag == "1.4.3" or "color-contrast" in rule or "contrast" in rule:
        return "Design system color palette or theme tokens"
    if component == "buttons" or "button" in rule:
        return "Design system button component"
    if component == "forms" or "label" in rule:
        return "Design system form field component"
    if component == "navigation":
        return "Design system navigation component"
    if component == "tables":
        return "Design system table component"

    return None