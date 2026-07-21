"""
Problem Type Taxonomy

This module maps highly specific, technical rule IDs into broad, human-readable 
"Problem Types" (e.g., 'accessible-name', 'keyboard', 'contrast'). 

This is primarily used to power the high-level analytical charts on the 
dashboard, allowing stakeholders to see macro-trends like "40% of our 
accessibility debt is related to Keyboard navigation."
"""

PROBLEM_TYPE_MAP = {
    # --- Accessible Names & Labels ---
    "button-name": "accessible-name",
    "link-name": "accessible-name",
    "label": "accessible-name",
    "interactive-name": "accessible-name",
    "input-name": "accessible-name",
    "widget-name": "accessible-name",
    "aria-input-field-name": "accessible-name",
    "label-content-name-mismatch": "accessible-name",

    # --- Images & Media ---
    "image-alt": "missing-alt",
    "decorative-image": "image",
    "redundant-alt": "image",
    "frame-title": "frame-title",

    # --- Contrast & Visual Presentation ---
    "color-contrast": "contrast",
    "color-contrast-enhanced": "contrast",
    "color-contrast-review": "contrast",
    "use-of-color": "use-of-color",
    "reflow": "reflow",
    "text-spacing": "text-spacing",
    "target-spacing": "target-size",
    "focus-appearance": "focus-visible",

    # --- Page Structure & Navigation ---
    "region": "landmark",
    "landmark": "landmark",
    "landmark-one-main": "landmark",
    "landmark-banner-top-level": "landmark",
    "landmark-complementary-top-level": "landmark",
    "landmark-unique": "landmark",

    "skip-link": "bypass-blocks",
    "bypass-blocks": "bypass-blocks",

    "heading": "heading",
    "heading-order": "heading",

    "table-header": "table-header",
    "page-title": "page-title",
    "language": "language",
    "meaningful-sequence": "reading-order",
    "consistent-navigation": "navigation",

    # --- Keyboard & Focus ---
    "keyboard": "keyboard",
    "scrollable-region-focusable": "keyboard",
    "element-tabbable-unobscured": "keyboard",
    "widget-tabbable-single": "keyboard",
    "no-keyboard-trap": "keyboard",

    "focus-order": "focus-order",
    "focus-order-semantics": "focus-order",
    "focus-visible": "focus-visible",
    "style-focus-visible": "focus-visible",

    # --- Forms ---
    "form-submit": "form",
    "form-structure": "form",
    "fieldset-legend": "form",
    "error-suggestion": "form",

    # --- ARIA & Parsing ---
    "aria-role": "aria-role",
    "aria-allowed-role": "aria-role",
    "aria-allowed-attr": "aria-role",
    "aria-descendant-valid": "aria-role",
    "aria-hidden-focusable": "keyboard",
    "aria-prohibited-attr": "aria-role",
    "aria-required-attr": "aria-role",
    "aria-required-children": "aria-role",
    "aria-valid": "aria-role",
    "aria-valid-attr": "aria-role",
    "aria-validity": "aria-role",

    "duplicate-id": "duplicate-id",

    # --- Document Structure ---
    "list-structure": "structure",
    "nested-interactive": "structure",

    # --- Visibility & Interaction ---
    "hidden-content": "hidden-content",
    "css-content-visibility": "hidden-content",
    "hidden-attribute-override": "hidden-content",
    "content-on-hover-focus": "content-on-hover",

    # --- Miscellaneous ---
    "orientation": "orientation",
    "css-orientation-lock": "orientation",
    "sensory-instructions": "sensory-instructions",
    "text-sensory-misuse": "sensory-instructions",

    # --- Technical / Scraper Artifacts ---
    "axe-violations-summary": "summary",
    "network-failure": "technical",
    "console-noise": "technical",
    "technical-noise": "technical",
}