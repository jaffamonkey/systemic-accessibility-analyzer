"""
Problem Type Taxonomy

This module maps highly specific, canonical rule IDs into broad, human-readable 
"Problem Types" (e.g., 'accessible-name', 'keyboard', 'contrast'). 

This is primarily used to power the high-level analytical charts on the 
dashboard, allowing stakeholders to see macro-trends like "40% of our 
accessibility debt is related to Keyboard navigation."
"""

PROBLEM_TYPE_MAP = {
    # --- Accessible Names & Labels ---
    "widget-name": "accessible-name",
    "link-name": "accessible-name",
    "form-label": "accessible-name",
    "aria-validity": "accessible-name",

    # --- Images & Media ---
    "missing-alt": "image",
    "redundant-alt": "image",

    # --- Contrast & Visual Presentation ---
    "color-contrast": "contrast",
    "color-contrast-enhanced": "contrast",
    "color-contrast-review": "contrast",
    "use-of-color": "use-of-color",
    "reflow": "reflow",
    "text-spacing": "text-spacing",

    # --- Page Structure & Navigation ---
    "landmarks": "landmark",
    "heading-hierarchy": "heading",
    "list-structure": "structure",
    "table-header": "table-header",
    "page-title": "page-title",
    "frame-title": "frame-title",
    "language": "language",
    "reading-order": "reading-order",
    "consistent-navigation": "navigation",
    "bypass-blocks": "bypass-blocks",

    # --- Keyboard & Focus ---
    "focus-management": "keyboard",
    "keyboard": "keyboard",
    "focus-order": "focus-order",
    "focus-visible": "focus-visible",
    "content-on-hover": "content-on-hover",

    # --- ARIA & Parsing ---
    "duplicate-id": "duplicate-id",
    "aria-role": "aria-role",

    # --- Visibility & Interaction ---
    "hidden-content": "hidden-content",

    # --- Miscellaneous ---
    "orientation": "orientation",
    "sensory-instructions": "sensory-instructions",

    # --- Technical / Scraper Artifacts ---
    "summary": "summary",
    "technical-noise": "technical",
}