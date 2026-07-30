"""
Analyzer Utilities

Helper functions for parsing, cleaning, and simplifying CSS selectors 
and DOM fragments before they enter the main analysis pipeline.
"""

import re

GENERIC_TAGS = {"a", "li", "div", "span", "em", "i", "p"}

def clean_dynamic_selectors(selector: str | None) -> str:
    """
    Strips out highly dynamic, auto-generated noise from selectors 
    to prevent clustering failures. Targets common CMS and frontend frameworks.
    """
    if not selector:
        return ""
        
    selector = str(selector).lower().strip()
    
    # Generic dynamically generated trailing numbers (e.g., #button-12345 -> #button-)
    selector = re.sub(r'#([a-zA-Z_-]+)\d{4,}', r'#\1', selector)
    
    # Catch 32-character hex hashes (e.g., Siteimprove Alfa artifacts)
    if re.match(r'^[a-f0-9]{32}$', selector):
        return "alfa-opaque-node-hash"
        
    # Elementor dynamic element hashes
    selector = re.sub(r'elementor-element-[a-f0-9]+', 'elementor-element', selector)
    
    # WordPress dynamic menu item IDs
    selector = re.sub(r'menu-item-\d+', 'menu-item', selector)
    
    # SmartMenu dynamic IDs
    selector = re.sub(r'#sm-\d+-\d+', '', selector)
        
    return selector


def simplify_pattern(selector) -> str:
    """
    Reduces a complex, tool-specific DOM selector payload down to a single, 
    flat string, stripping out fragile positional pseudo-classes.
    """
    if selector is None:
        return "unknown"

    if isinstance(selector, (list, tuple, set)):
        parts = []
        for item in selector:
            if item is None:
                continue
            if isinstance(item, dict):
                for key in ("xpath", "selector", "target", "html", "path"):
                    value = item.get(key)
                    if value:
                        parts.append(str(value))
                        break
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        selector = " ".join(parts)

    elif isinstance(selector, dict):
        for key in ("xpath", "selector", "target", "html", "path"):
            value = selector.get(key)
            if value:
                selector = str(value)
                break
        else:
            selector = str(selector)
    else:
        selector = str(selector)

    s = selector.lower().strip()

    if not s:
        return "unknown"

    s = re.sub(r":nth-child\(\d+\)", "", s)
    s = re.sub(r":nth-of-type\(\d+\)", "", s)
    s = re.sub(r"\s+", " ", s)

    return s