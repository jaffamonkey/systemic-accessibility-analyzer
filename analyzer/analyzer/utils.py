import re

GENERIC_TAGS = {"a", "li", "div", "span", "em", "i", "p"}

def clean_dynamic_selectors(selector) -> str:
    # 🔥 THE GUARD CLAUSE: If it's None or empty, just return an empty string safely
    if not selector:
        return ""
        
    selector = str(selector).lower().strip()
    
    # Now it is perfectly safe to run the regex!
    selector = re.sub(r'#([a-zA-Z_-]+)\d{4,}', r'#\1', selector)
    
    if re.match(r'^[a-f0-9]{32}$', selector):
        return "alfa-opaque-node-hash"
        
    return selector

def simplify_pattern(selector) -> str:
    if selector is None:
        return "unknown"

    # Normalize lists/tuples/sets into a single string
    if isinstance(selector, (list, tuple, set)):
        parts = []
        for item in selector:
            if item is None:
                continue
            if isinstance(item, dict):
                # Prefer common location keys if present
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

    # remove nth-child noise
    s = re.sub(r":nth-child\(\d+\)", "", s)
    s = re.sub(r":nth-of-type\(\d+\)", "", s)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s)

    return s