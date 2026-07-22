"""
Problem Type Taxonomy (Updated)

Maps specific accessibility rule IDs or components into high-level, 
human-readable UI categories for macro-level dashboard reporting.
"""

PROBLEM_TYPE_MAP = {
    # --- FORMS ---
    "form": "Forms",
    "form_field": "Forms",
    "search": "Forms",
    "file_upload": "Forms",

    # --- INTERACTIVE ---
    "button": "Interactive",
    "pseudo_button": "Interactive",
    "theme_toggle": "Interactive",
    "modal": "Interactive",
    "dialog": "Interactive",
    "accordion": "Interactive",
    "carousel": "Interactive",
    "tooltip": "Interactive",

    # --- NAVIGATION ---
    "link": "Navigation",
    "navigation": "Navigation",
    "navbar": "Navigation",
    "dropdown_menu": "Navigation",
    "breadcrumb": "Navigation",
    "tabs": "Navigation",
    "pagination": "Navigation",
    "skip-link": "bypass-blocks",

    # --- CONTENT ---
    "heading": "Content",
    "text": "Content",
    "list": "Content",
    "card": "Content",
    "product_card": "Content",
    "alert": "Content",
    "selectable_list": "Content",
    "region": "landmark",

    # --- MEDIA ---
    "image": "Media",
    "icon": "Media",
    "image-alt": "missing-alt",

    # --- STRUCTURE ---
    "layout": "Structure",
    "grid": "Structure",
    "frame": "Structure",
    "iframe_embed": "Structure",
    "table": "Structure",
    "data_table": "Structure",
    "document_metadata": "Structure",
    "frame-title": "frame-title",
    "reflow": "reflow",

    # --- KEYBOARD & FOCUS ---
    "scrollable-region-focusable": "keyboard",
    "keyboard": "keyboard",

    # --- VISUALS & CONTRAST ---
    "color-contrast-review": "contrast",
    "use-of-color": "use-of-color",

    # --- SPECIAL & FALLBACKS ---
    "aria": "ARIA",
    "aria-prohibited-attr": "aria-role",
    "third_party": "Third-Party Noise",
    "other": "Other",
}