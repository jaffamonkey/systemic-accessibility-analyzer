"""
Component Configuration

Contains static lookup dictionaries used to categorize raw DOM elements 
into standardized design system components and broader UI groups.
"""

# Maps a standardized component slug to a list of keyword hints found in the DOM
COMPONENT_PATTERNS = {
    "navigation": ["nav", "menu", "navbar", "breadcrumb", "footer"],
    "form": ["form", "input", "textarea", "select", "label", "login"],
    "button": ["button", "btn", "submit", "cta"],
    "link": ["href", "link", ".action"],
    "image": ["img", "svg", "icon"],
    "table": ["table", "thead", "tbody", "tr", "td"],
    "heading": ["h1", "h2", "h3", "h4", "h5", "h6"],
    "list": ["ul", "ol", "li"],
    "modal": ["modal", "dialog"],
    "card": ["card", "tile", "panel"],
    "search": ["search", "keyword"],
    "frame": ["frame", "frameset"],
    "third_party": [
        "batbeacon", 
        "google-analytics", 
        "googletagmanager", 
        "hotjar", 
        "_ga", 
        "_gid", 
        "facebook-jssdk", 
        "recaptcha"
    ]
}

# Rolls up specific components into broader macro-categories for high-level dashboard charts
COMPONENT_GROUPS = {
    "button": "interaction",
    "link": "navigation",
    "form": "input",
    "input": "input",
    "search": "input",
    "navigation": "navigation",
    "card": "content",
    "modal": "overlay",
    "layout": "structure",
    "grid": "structure",
    "spacing": "structure",
    "text": "content",
    "icon": "media",
    "media": "media",
    "frame": "structure",
    "third_party": "noise"
}