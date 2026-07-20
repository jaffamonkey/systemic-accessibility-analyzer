DESIGN_SYSTEM_MAP = {

    # Navigation
    "nav": "navigation",
    "menu": "navigation",
    "breadcrumb": "navigation",
    "tabs": "navigation",
    "pagination": "navigation",

    # Frames
    "frame": "frame",

    # Buttons / actions
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

    # UI patterns
    "modal": "modal",
    "dialog": "modal",
    "card": "card",
    "accordion": "accordion",
    "tab": "tabs",
}

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

def normalize_component(component):

    if not component:
        return "other"

    component = component.lower()

    for key, mapped in DESIGN_SYSTEM_MAP.items():
        if key in component:
            return mapped

    return component