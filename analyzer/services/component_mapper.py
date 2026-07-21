"""
Component Mapper

Normalizes raw UI identifiers (like HTML tags, CSS classes, or custom IDs) 
into a strict, canonical taxonomy. This prevents reporting fragmentation, 
ensuring that variations like "btn", "cta", and "button" are all aggregated 
under a single "button" component in the BI dashboards.
"""

# -------------------------
# 🗂️ TAXONOMY MAPS
# -------------------------

# Maps loose, raw DOM strings to our standardized component names
DESIGN_SYSTEM_MAP = {
    # Navigation
    "nav": "navigation",
    "menu": "navigation",
    "breadcrumb": "navigation",
    "tabs": "navigation",
    "pagination": "navigation",

    # Frames
    "frame": "frame",

    # Buttons / Actions
    "button": "button",
    "btn": "button",
    "cta": "button",

    # Forms
    "input": "form",
    "select": "form",
    "textarea": "form",
    "checkbox": "form",
    "radio": "form",
    "form": "form",

    # Tables
    "table": "table",
    "datatable": "table",
    "grid": "table",

    # Layout
    "header": "header",
    "footer": "footer",
    "sidebar": "layout",
    "container": "layout",

    # UI Patterns
    "modal": "modal",
    "dialog": "modal",
    "card": "card",
    "accordion": "accordion",
    "tab": "tabs",
}

# The definitive list of top-level component categories allowed in the system
COMPONENT_SLUGS = {
    "button",
    "link",
    "form",
    "image",
    "list",
    "table",
    "navigation",
    "frame",
    "layout",
    "aria",
    "other",
    "third_party",
}

def normalize_component(component: str | None) -> str:
    """
    Takes an arbitrary component string and maps it to the official taxonomy.
    If no match is found, it falls back to the original string or 'other'.
    """
    if not component:
        return "other"

    component = component.lower()

    # Search for known taxonomy keywords inside the raw string
    for key, mapped in DESIGN_SYSTEM_MAP.items():
        if key in component:
            return mapped

    return component