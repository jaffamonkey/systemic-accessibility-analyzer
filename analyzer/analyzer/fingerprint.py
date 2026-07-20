import re
from analyzer.component_detector import detect_component
from analyzer.utils import clean_dynamic_selectors

def _coerce_value(value):
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


def build_fingerprint(dom, selector, rule_id=None) -> str:
    dom = _coerce_value(dom)
    selector = _coerce_value(selector)

    # 🔥 THE FIX: Prevent blank DOMs from collapsing into a single empty fingerprint!
    if not dom:
        safe_rule = str(rule_id or "page-level-issue").strip().lower()
        return f"document_metadata::{safe_rule}"

    # 🔥 Call the cleaner right away
    dom = clean_dynamic_selectors(dom)

    dom = dom.lower()

    # -------------------------
    # NORMALIZATION
    # -------------------------

    dom = re.sub(r"nth-child\(\d+\)", "nth-child(*)", dom)
    dom = re.sub(r"-\d+", "", dom)
    dom = re.sub(r"\[.*?\]", "", dom)

    parts = re.split(r"[>/ ]", dom)
    parts = [p.strip() for p in parts if p.strip()]

    ignore = {"div", "span", "section", "container", "wrapper"}

    meaningful = [p for p in parts if p not in ignore]
    meaningful = meaningful[-3:]

    dom_part = "/".join(meaningful)

    # -------------------------
    # SELECTOR CLEANUP
    # -------------------------

    selector_part = ""
    if selector:
        # 🔥 Clean the target selector as well
        selector = clean_dynamic_selectors(selector)
        selector = re.sub(r"nth-child\(\d+\)", "nth-child(*)", selector)
        selector_part = selector.split(" ")[0]

    # -------------------------
    # 🔥 NEW: COMPONENT SIGNAL
    # -------------------------

    component = detect_component(dom, selector)

    # -------------------------
    # FINAL FINGERPRINT
    # -------------------------

    base = f"{dom_part}|{selector_part}" if selector_part else dom_part

    return f"{component}::{base}"