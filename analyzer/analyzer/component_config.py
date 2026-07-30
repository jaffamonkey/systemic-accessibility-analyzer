"""
Component Configuration

Contains static lookup dictionaries used to categorize raw DOM elements 
into standardized design system components and broader UI groups.
"""

COMPONENT_PATTERNS = {
    "navigation": ["nav", "menu", "navbar", "breadcrumb", "footer", "elementor-nav", "menu-item"],
    "form": ["form", "input", "textarea", "select", "label", "login", "fieldset", "legend"],
    "button": ["button", "btn", "submit", "cta", "elementor-button"],
    "link": ["href", "link", ".action"],
    "image": ["img", "svg", "icon", "picture", "figure"],
    "table": ["table", "thead", "tbody", "tr", "td", "th", "caption"],
    "heading": ["h1", "h2", "h3", "h4", "h5", "h6", "elementor-heading"],
    "list": ["ul", "ol", "li", "dl", "dt", "dd"],
    "modal": ["modal", "dialog", "popup", "overlay"],
    "card": ["card", "tile", "panel"],
    "search": ["search", "keyword"],
    "frame": ["frame", "frameset", "iframe"],
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
    "heading": "content",
    "list": "content",
    "table": "content",
    "icon": "media",
    "image": "media",
    "media": "media",
    "frame": "structure",
    "third_party": "noise"
}