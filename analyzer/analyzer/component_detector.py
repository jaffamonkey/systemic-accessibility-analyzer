"""
Component Detector

The heuristic engine responsible for translating raw, messy DOM strings 
and CSS selectors into standardized Design System components. It uses a 
waterfall approach: checking explicit HTML tags, contextual hierarchy, 
historical learned patterns, and finally keyword matching.
"""

import re
from collections import defaultdict

from analyzer.utils import clean_dynamic_selectors, simplify_pattern
from analyzer.component_config import COMPONENT_PATTERNS
from analyzer.component_learning import auto_guess, load_learning, LEARNING

DESIGN_SYSTEM_PATTERNS = {
    "landmarks": ["header", "nav", "main", "footer", "aside", "section", "article"],
    "interactive": ["btn", "button", "cta", "trigger", "toggle", "menu", "dropdown", "modal", "dialog"],
    "navigation": ["breadcrumb", "pagination", "tabs", "navbar", "sidebar"],
    "feedback": ["alert", "error", "success", "warning", "hint", "tooltip", "status"],
    "forms": ["input", "select", "textarea", "checkbox", "radio", "fieldset", "legend"]
}


def get_emerging_patterns() -> list:
    """
    Scans the local learning file for high-frequency, unclassified DOM patterns 
    so they can be surfaced on the dashboard for manual mapping.
    """
    learning = load_learning()
    results = []

    for pattern, data in learning.items():
        # Only surface patterns that appear frequently across the estate
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
            # Prefix match (e.g., 'mt-' matches 'mt-5')
            if k.endswith('-') or k.endswith('_'):
                regex = rf'\b{re.escape(k)}'
            # Exact word boundary match (e.g., 'grid' matches 'main-grid' but not 'gridlock')
            else:
                regex = rf'\b{re.escape(k)}\b'
            
            if re.search(regex, p):
                return group

    return None


def parse_pattern(pattern: str) -> list:
    """Breaks a CSS pattern into hierarchy parts (e.g. 'nav-ul-li-a' → ['nav','ul','li','a'])."""
    if not pattern:
        return []
    return pattern.split("-")


def detect_component(dom: str, selector: str = None) -> str:
    """
    The primary waterfall pipeline for identifying a UI component.
    Evaluates in order: Exclusions -> Explicit Target -> Hierarchy -> Machine Learning -> Keywords.
    """
    # 1. SCRUB THE RAW INPUTS
    dom = clean_dynamic_selectors(dom)
    selector = clean_dynamic_selectors(selector)

    # 2. COMBINE THEM
    text = f"{dom or ''} {selector or ''}".lower().strip()

    # 3. THE BOUNCER: Catch opaque hashes and tracking scripts early
    if "alfa-opaque-node-hash" in text:
        return "third_party"

    pattern = simplify_pattern(text)
    parts = parse_pattern(pattern)

    if not parts:
        return "other"

    # 4. PRIORITY: LAST ELEMENT (The actual target node)
    last = parts[-1]

    if last == "a": return "link"
    if last in ["button"]: return "button"
    if last in ["input", "textarea", "select"]: return "form"
    if last in ["img", "svg"]: return "image"
    if last in ["li"]: return "list"
    if "frame" in pattern: return "frame"

    # 5. CONTEXT-AWARE BOOST (Looking up the DOM tree)
    if "nav" in parts: return "navigation"
    if "ul" in parts or "ol" in parts: return "list"
    if "table" in parts: return "table"
    if "form" in parts: return "form"

    # 6. MACHINE LEARNING OVERRIDE
    if pattern in LEARNING and LEARNING[pattern].get("component"):
        return LEARNING[pattern]["component"]

    # 7. KEYWORD MATCH (Catches customized class names like '.primary-cta')
    for comp, keywords in COMPONENT_PATTERNS.items():
        if any(k in pattern for k in keywords):
            return comp

    # 8. FALLBACK
    if len(parts) == 1 and parts[0] in ["div", "section", "container"]:
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