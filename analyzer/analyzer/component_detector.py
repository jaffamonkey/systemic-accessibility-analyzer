from collections import defaultdict
import re
from analyzer.utils import clean_dynamic_selectors

from analyzer.component_config import COMPONENT_PATTERNS
from analyzer.component_learning import auto_guess, load_learning, LEARNING
from analyzer.utils import simplify_pattern

def get_emerging_patterns():

    learning = load_learning()

    results = []

    for pattern, data in learning.items():

        # only show frequently seen patterns
        if data.get("count", 0) < 5:
            continue

        results.append({
            "pattern": pattern,
            "count": data.get("count", 0),
            "component": data.get("component"),
            "confidence": data.get("confidence", 0)
        })

    return sorted(results, key=lambda x: x["count"], reverse=True)[:20]

DESIGN_SYSTEM_PATTERNS = {
    "landmarks": ["header", "nav", "main", "footer", "aside", "section", "article"],
    "interactive": ["btn", "button", "cta", "trigger", "toggle", "menu", "dropdown", "modal", "dialog"],
    "navigation": ["breadcrumb", "pagination", "tabs", "navbar", "sidebar"],
    "feedback": ["alert", "error", "success", "warning", "hint", "tooltip", "status"],
    "forms": ["input", "select", "textarea", "checkbox", "radio", "fieldset", "legend"]
}

def detect_design_system(pattern):
    if not pattern:
        return None

    p = pattern.lower()

    for group, keywords in DESIGN_SYSTEM_PATTERNS.items():
        for k in keywords:
            # Use regex for exact matches or prefix matches (like 'col-')
            # \b handles word boundaries so 'text' doesn't match 'texture'
            if k.endswith('-') or k.endswith('_'):
                # Prefix match: e.g., 'mt-' matches 'mt-5'
                regex = rf'\b{re.escape(k)}'
            else:
                # Exact word match: e.g., 'grid' matches 'main-grid' but not 'gridlock'
                regex = rf'\b{re.escape(k)}\b'
            
            if re.search(regex, p):
                return group

    return None


def parse_pattern(pattern):
    """
    Break pattern into hierarchy parts
    e.g. 'nav-ul-li-a' → ['nav','ul','li','a']
    """
    if not pattern:
        return []

    return pattern.split("-")

def detect_component(dom, selector=None):
    # 🔥 1. SCRUB THE RAW INPUTS FIRST
    dom = clean_dynamic_selectors(dom)
    selector = clean_dynamic_selectors(selector)

    # 2. COMBINE THEM
    text = f"{dom or ''} {selector or ''}".lower().strip()

    # 🔥 3. THE BOUNCER: CATCH OPAQUE HASHES EARLY
    if "alfa-opaque-node-hash" in text:
        return "third_party"

    pattern = simplify_pattern(text)
    parts = parse_pattern(pattern)

    if not parts:
        return "other"

    # -------------------------
    # 🔥 PRIORITY: LAST ELEMENT (actual element)
    # -------------------------
    last = parts[-1]

    if last == "a":
        return "link"

    if last in ["button"]:
        return "button"

    if last in ["input", "textarea", "select"]:
        return "form"

    if last in ["img", "svg"]:
        return "image"

    if last in ["li"]:
        return "list"
    
    if "frame" in pattern:
        return "frame"

    # -------------------------
    # 🔥 CONTEXT-AWARE BOOST
    # -------------------------
    if "nav" in parts:
        return "navigation"

    if "ul" in parts or "ol" in parts:
        return "list"

    if "table" in parts:
        return "table"

    if "form" in parts:
        return "form"

    # 🔥 learned component override
    if pattern in LEARNING and LEARNING[pattern].get("component"):
        return LEARNING[pattern]["component"]

    # -------------------------
    # 🔥 KEYWORD MATCH
    # -------------------------
    # Because we added "third_party" to COMPONENT_PATTERNS, 
    # things like "batbeacon" and "_ga" will be caught perfectly here!
    for comp, keywords in COMPONENT_PATTERNS.items():
        if any(k in pattern for k in keywords):
            return comp

    # -------------------------
    # FALLBACK
    # -------------------------
    if len(parts) == 1 and parts[0] in ["div", "section", "container"]:
        return "layout"

    return "other"

def detect_root_cause(rule, component, message):

    text = f"{rule} {component} {message}".lower()

    # Contrast issues
    if "contrast" in text:
        return "Design system color palette or theme tokens"

    # Buttons
    if component == "Buttons":
        return "Shared button component implementation"

    # Forms
    if component == "Forms":
        return "Form field component missing accessible label pattern"

    # Images
    if component == "Images":
        return "Image component missing alt attribute or CMS content issue"

    # Tables
    if component == "Tables":
        return "Table component missing headers or scope attributes"

    # ARIA issues
    if "aria" in text:
        return "ARIA attributes incorrectly implemented in component"

    # Labels
    if "label" in text:
        return "Form labels not programmatically associated"

    return "Likely reusable component or template issue"

def detect_design_system_issue(cluster):

    rule = (cluster.get("ruleId") or "").lower()
    wcag = cluster.get("wcag")
    component = (cluster.get("component") or "").lower()

    # Color / theme tokens
    if (
        wcag == "1.4.3"
        or "color-contrast" in rule
        or "contrast" in rule
    ):
        return "Design system color palette or theme tokens"

    # Buttons / controls
    if component == "buttons" or "button" in rule:
        return "Design system button component"

    # Forms
    if component == "forms" or "label" in rule:
        return "Design system form field component"

    # Navigation / menus
    if component == "navigation":
        return "Design system navigation component"

    # Tables
    if component == "tables":
        return "Design system table component"

    return None

