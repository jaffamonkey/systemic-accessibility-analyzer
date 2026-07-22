"""
Fingerprint Generator

Creates a highly stable, unique identifier for a specific DOM node. 
This is used by the clustering engine to realize that an issue found by Axe 
and an issue found by HTMLCS are actually pointing to the exact same element.
"""

import re
from analyzer.component_detector import detect_component
from analyzer.utils import clean_dynamic_selectors

def _coerce_value(value) -> str:
    """Safely extracts a string from mixed-type selector payloads."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                extracted = ""
                for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
                    candidate = item.get(key)
                    if candidate:
                        extracted = str(candidate)
                        break
                if not extracted:
                    extracted = str(item)
                parts.append(extracted)
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p).strip()

    if isinstance(value, dict):
        for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
            candidate = value.get(key)
            if candidate:
                return str(candidate).strip()
        return str(value).strip()

    return str(value).strip()


def build_fingerprint(dom: str, selector: str, rule_id: str = None) -> str:
    """
    Generates a normalized fingerprint by stripping dynamic attributes, 
    positional pseudo-selectors, and keeping only the most meaningful 
    structural parts of the DOM path.
    """
    dom = _coerce_value(dom)
    selector = _coerce_value(selector)

    # Prevent blank DOMs from collapsing into a single generic fingerprint
    if not dom:
        safe_rule = str(rule_id or "page-level-issue").strip().lower()
        return f"document_metadata::{safe_rule}"

    dom = clean_dynamic_selectors(dom).lower()

    # --- 1. DOM NORMALIZATION ---
    # Strip fragile positional identifiers that change when content is added/removed
    dom = re.sub(r"nth-child\(\d+\)", "nth-child(*)", dom)
    dom = re.sub(r"-\d+", "", dom)
    dom = re.sub(r"\[.*?\]", "", dom)

    parts = re.split(r"[>/ ]", dom)
    parts = [p.strip() for p in parts if p.strip()]

    # Filter out layout wrappers to isolate the actual semantic target
    ignore = {"div", "span", "section", "container", "wrapper"}
    meaningful = [p for p in parts if p not in ignore]
    
    # Keep only the last 3 meaningful nodes to ensure stability across minor structural changes
    meaningful = meaningful[-3:]
    dom_part = "/".join(meaningful)

    # --- 2. SELECTOR CLEANUP ---
    selector_part = ""
    if selector:
        selector = clean_dynamic_selectors(selector)
        selector = re.sub(r"nth-child\(\d+\)", "nth-child(*)", selector)
        selector_part = selector.split(" ")[0]

    # --- 3. COMPONENT SIGNAL ---
    component = detect_component(dom, selector)

    # --- 4. FINAL FINGERPRINT ---
    base = f"{dom_part}|{selector_part}" if selector_part else dom_part
    return f"{component}::{base}"