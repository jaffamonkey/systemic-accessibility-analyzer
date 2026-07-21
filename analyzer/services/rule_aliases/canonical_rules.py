"""
Canonical Rules Dictionary

This module acts as the "Encyclopedia" of normalized accessibility rules.
Instead of surfacing 50 different tool-specific descriptions for the same issue, 
this dictionary provides a single, rich, canonical object containing a clear 
name, description, category, and related WCAG 2.x criteria.
"""

CANONICAL_RULES = {
    # --- INTERACTIVE & WIDGETS ---
    "widget-name": {
        "name": "Widget Name",
        "description": "Interactive controls (buttons, toggles, accordions) must have an accessible name.",
        "component_category": "Interactive",
        "related_wcag2": ["4.1.2"]
    },
    "link-name": {
        "name": "Link Name",
        "description": "Links must have discernible, meaningful text.",
        "component_category": "Interactive",
        "related_wcag2": ["2.4.4", "4.1.2"]
    },
    
    # --- FORMS ---
    "form-label": {
        "name": "Form Label",
        "description": "Form inputs must have a programmatically associated label.",
        "component_category": "Forms",
        "related_wcag2": ["1.3.1", "3.3.2", "4.1.2"]
    },

    # --- MEDIA ---
    "missing-alt": {
        "name": "Missing Alternative Text",
        "description": "Meaningful images must have alternative text; decorative images must be hidden.",
        "component_category": "Media",
        "related_wcag2": ["1.1.1"]
    },
    "redundant-alt": {
        "name": "Redundant Alternative Text",
        "description": "Alternative text should not repeat nearby text or use phrases like 'image of'.",
        "component_category": "Media",
        "related_wcag2": ["1.1.1"]
    },

    # --- KEYBOARD & FOCUS ---
    "focus-management": {
        "name": "Focus Management",
        "description": "Hidden elements must not receive focus, and scrollable regions must be accessible via keyboard.",
        "component_category": "Keyboard",
        "related_wcag2": ["2.1.1", "2.4.3"]
    },

    # --- STRUCTURE & SEMANTICS ---
    "heading-hierarchy": {
        "name": "Heading Hierarchy",
        "description": "Headings must be present, not empty, and logically ordered.",
        "component_category": "Structure",
        "related_wcag2": ["1.3.1", "2.4.6"]
    },
    "landmarks": {
        "name": "Landmarks",
        "description": "Pages must use ARIA landmarks or HTML5 sectioning elements correctly.",
        "component_category": "Structure",
        "related_wcag2": ["1.3.1", "2.4.1"]
    },
    "list-structure": {
        "name": "List Structure",
        "description": "Lists and list items must be constructed correctly.",
        "component_category": "Structure",
        "related_wcag2": ["1.3.1"]
    },
    "language": {
        "name": "Page Language",
        "description": "The document must have a valid language attribute.",
        "component_category": "Structure",
        "related_wcag2": ["3.1.1"]
    },
    "page-title": {
        "name": "Page Title",
        "description": "The document must have a meaningful title.",
        "component_category": "Structure",
        "related_wcag2": ["2.4.2"]
    },
    "frame-title": {
        "name": "Frame Title",
        "description": "Iframes must have an accessible name/title.",
        "component_category": "Structure",
        "related_wcag2": ["4.1.2"]
    },

    # --- VISUAL ---
    "color-contrast": {
        "name": "Color Contrast",
        "description": "Text must meet minimum contrast ratios against its background.",
        "component_category": "Visual",
        "related_wcag2": ["1.4.3", "1.4.6"]
    },

    # --- TECHNICAL / ARIA ---
    "aria-validity": {
        "name": "ARIA Validity",
        "description": "ARIA attributes must be valid, allowed on the element, and have valid values.",
        "component_category": "Technical",
        "related_wcag2": ["4.1.2"]
    },
    "duplicate-id": {
        "name": "Duplicate ID",
        "description": "ID attributes must be unique across the DOM.",
        "component_category": "Technical",
        "related_wcag2": ["4.1.1"]
    }
}

def is_canonical_rule(rule_id: str) -> bool:
    """Checks if a given string matches a recognized, high-level canonical rule."""
    return rule_id in CANONICAL_RULES