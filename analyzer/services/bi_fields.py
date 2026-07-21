"""
BI Fields & Enrichment

This module provides the logic for mapping raw accessibility data into structured, 
sortable, and human-readable formats suitable for Business Intelligence (BI) dashboards.
It handles severity sorting, team assignment, tool consensus scoring, and URL normalization.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, unquote

# -------------------------
# 📊 SORTING & TAXONOMY MAPS
# -------------------------

SEVERITY_SORT = {
    "critical": 1,
    "serious": 2,
    "moderate": 3,
    "minor": 4,
    "warning": 5,
    "unknown": 6,
}

WCAG_LEVEL_SORT = {
    "A": 1,
    "AA": 2,
    "AAA": 3,
}

ISSUE_SCOPE_SORT = {
    "Shared component": 1,
    "Shared template/pattern": 2,
    "Page-specific": 3,
    "Unknown": 4,
}

# Maps generalized UI components to the team likely responsible for fixing them
OWNER_TEAM_RULES = {
    "button": "Design System",
    "form": "Design System",
    "navigation": "Design System",
    "tabs": "Design System",
    "table": "Design System",
    "modal": "Design System",
    "card": "Design System",
    "accordion": "Design System",
    "layout": "Frontend Platform",
    "header": "Frontend Platform",
    "frame": "Frontend Platform",
    "document_metadata": "Content / SEO",
    "text": "Content",
    "image": "Content",
    "link": "Content",
    "search": "Frontend Platform",
    "other": "Frontend Platform",
    "navbar": "Design System",
    "dropdown_menu": "Design System",
    "theme_toggle": "Design System",
    "form_field": "Design System",
    "data_table": "Design System",
    "product_card": "Design System",
    "iframe_embed": "Frontend Platform",
    "selectable_list": "Design System"
}

# -------------------------
# 🛠️ TOOL & ENGINE CLASSIFICATION
# -------------------------

TOOL_FAMILY_MAP = {
    "axe-core": "axe-like",
    "axe": "axe-like",
    "axe-scan": "axe-like",
    "lighthouse": "axe-like",
    "pa11y-axe": "axe-like",
    "pa11y-htmlcs": "htmlcs-like",
    "htmlcs": "htmlcs-like",
    "html-sniffer": "htmlcs-like",
    "ibm-equal-access": "ibm-like",
    "ibm": "ibm-like",
    "oobee": "custom-like",
    "uuv": "custom-like",
    "alfa": "htmlcs-like",
    "aslint": "custom-like",
    "editoria11y": "custom-like",
    "nu-html-checker": "htmlcs-like",
    "qualweb": "custom-like",
    "speca11y": "speca11y-like"
}

TOOL_ENGINE_MAP = {
    "axe-core": "axe",
    "axe": "axe",
    "axe-scan": "axe",
    "lighthouse": "axe",
    "htmlcs": "htmlcs",
    "html-sniffer": "htmlcs",
    "pa11y-axe": "axe",
    "pa11y-htmlcs": "htmlcs",
    "ibm-equal-access": "ibm",
    "ibm": "ibm",
    "oobee": "custom",
    "uuv": "custom",
    "alfa": "alfa",
    "aslint": "aslint",
    "speca11y": "speca11y",
    "nu-html-checker": "nuval",
    "qualweb": "qualweb",
}

ENGINE_FAMILY_MAP = {
    "axe-core": {"label": "Axe", "badge": "🪓", "class": "engine-axe"},
    "axe-scan": {"label": "Axe", "badge": "🪓", "class": "engine-axe"},
    "pa11y-axe": {"label": "Axe", "badge": "🪓", "class": "engine-axe"},
    "html-sniffer": {"label": "HTMLCS", "badge": "🔍", "class": "engine-htmlcs"},
    "pa11y-htmlcs": {"label": "HTMLCS", "badge": "🔍", "class": "engine-htmlcs"},
    "ibm": {"label": "IBM", "badge": "🏢", "class": "engine-ibm"},
    "ibm-equal-access": {"label": "IBM", "badge": "🏢", "class": "engine-ibm"},
    "lighthouse": {"label": "Browser", "badge": "💡", "class": "engine-browser"},
    "uuv": {"label": "UUV", "badge": "🧪", "class": "engine-uuv"},
    "oobee": {"label": "Oobee", "badge": "🧩", "class": "engine-oobee"},
    "alfa": {"label": "Alfa", "badge": "🧩", "class": "engine-alfa"},
    "nu-html-checker": {"label": "Validator", "badge": "⚖️", "class": "engine-validator"},
    "speca11y": { "label": "SpecA11y", "badge": "🧪", "class": "engine-speca11y" },
    "contrast-checker": {"label": "Visual", "badge": "👁️", "class": "engine-visual"},
    "tab-map": {"label": "Keyboard", "badge": "⌨️", "class": "engine-keyboard"},
    "virtual-screenreader": {"label": "AT", "badge": "🗣️", "class": "engine-at"},
}


def get_engine_family_meta(source: str | None) -> dict:
    """Returns display metadata (labels, badges, CSS classes) for a given tool engine."""
    key = str(source or "").strip().lower()
    return ENGINE_FAMILY_MAP.get(
        key,
        {"label": "Other", "badge": "•", "class": "engine-other"},
    )


def get_tool_engine(source: str | None) -> str:
    if not source:
        return "unknown"
    key = str(source).strip().lower()
    return TOOL_ENGINE_MAP.get(key, "unknown")


def summarize_tool_engines(sources) -> list[str]:
    return sorted({get_tool_engine(source) for source in (sources or []) if source})


def get_tool_family(source: str | None) -> str:
    if not source:
        return "unknown"
    key = str(source).strip().lower()
    return TOOL_FAMILY_MAP.get(key, "unknown")


def summarize_tool_families(sources) -> list[str]:
    return sorted({get_tool_family(source) for source in (sources or []) if source})


# -------------------------
# 🧠 SCORING & CONSENSUS LOGIC
# -------------------------

def infer_consensus(
    *,
    tool_family_count: int = 1,
    tool_engine_count: int = 1,
    tool_count: int = 1,
) -> str:
    """
    Determines the reliability of a finding based on how many distinct tools flagged it.
    Requires multiple independent testing engines to achieve 'verified' status.
    """
    if tool_engine_count >= 3:
        return "verified"
    if tool_engine_count >= 2:
        return "likely"
    if tool_family_count >= 2 and tool_count >= 2:
        return "likely"
    return "single"


def infer_confidence(
    *,
    tool_family_count: int = 1,
    tool_engine_count: int = 1,
    tool_count: int = 1,
    instance_count: int = 1,
    selector_count: int = 0,
    pages: int = 1,
    systemic: bool = False,
    wcag: str | None = None,
    rule_id: str | None = None,
    message: str | None = None,
    severity: str | None = None,
) -> str:
    """
    Calculates a qualitative confidence score (High/Medium/Low) for a finding.
    It builds a cumulative numeric score based on cross-tool validation, 
    issue prevalence across the estate, and data completeness.
    """
    score = 0.0

    # Strongest signal: Cross-engine validation
    if tool_engine_count >= 3:
        score += 2.5
    elif tool_engine_count == 2:
        score += 1.5
    else:
        score += 0.75

    if tool_family_count >= 2:
        score += 0.5

    if tool_count >= 4:
        score += 1.0
    elif tool_count >= 2:
        score += 0.5

    # Signal: High frequency indicates it is not a fluke
    if instance_count >= 8:
        score += 1.5
    elif instance_count >= 3:
        score += 1.0

    if pages >= 5:
        score += 1.5
    elif pages >= 2:
        score += 1.0

    if systemic:
        score += 1.0

    if selector_count >= 3:
        score += 0.75
    elif selector_count >= 1:
        score += 0.25

    # Signal: Robust reporting metadata
    if wcag:
        score += 0.5
    if rule_id:
        score += 0.5
    if message:
        score += 0.5

    sev = str(severity or "").lower()
    if sev in {"critical", "serious", "high"}:
        score += 0.5

    # Map the cumulative score to a confidence tier
    if score >= 5.0:
        return "high"
    if score >= 3.0:
        return "medium"
    return "low"


def estimate_issue_rank_score(
    *,
    severity: str | None,
    pages: int = 1,
    instance_count: int = 1,
    systemic: bool = False,
    tool_count: int = 1,
    tool_family_count: int = 1,
    tool_engine_count: int = 1,
) -> int:
    """
    Generates a priority ranking score for the "Next Best Fixes" dashboard panel.
    Heavily weights severity, spread (pages affected), and tool consensus to surface 
    high-impact, easy-to-verify systemic issues.
    """
    sev_weight = {
        "critical": 8,
        "serious": 5,
        "moderate": 3,
        "minor": 2,
        "warning": 1,
        "unknown": 1,
    }.get(str(severity or "unknown").lower(), 1)

    score = sev_weight * 5
    score += min(max(pages, 1), 25) * 3
    score += min(max(instance_count, 1), 20)

    # Reward cross-tool consensus
    if tool_engine_count >= 3:
        score += 10
    elif tool_engine_count == 2:
        score += 6
    else:
        score += 2

    if tool_family_count >= 3:
        score += 4
    elif tool_family_count == 2:
        score += 2

    score += max(min(tool_count, 8) - 1, 0) * 2

    if systemic:
        score += 8

    return int(score)


# -------------------------
# 🏷️ FORMATTING & LOOKUPS
# -------------------------

def clean_page_name(page: str | None) -> str:
    """Extracts a clean, readable path from a full URL."""
    if not page:
        return "unknown"

    page = str(page).strip()
    if page.startswith("http"):
        parsed = urlparse(page)
        path = parsed.path.strip("/")
        return path.replace("_", "-") or "home"
    return page


def derive_page_group(page: str | None) -> str:
    """Extracts the top-level directory from a page URL to group related views."""
    page = clean_page_name(page)
    bits = [b for b in re.split(r"[\\/]", page) if b]
    if not bits:
        return "root"
    return bits[0]


def humanize_slug(value: str | None) -> str:
    """Converts a programmatic slug (e.g., 'primary-button') into Title Case."""
    if not value:
        return "Other"
    value = str(value).replace("_", " ").replace("-", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value.title()


def severity_sort_value(severity: str | None) -> int:
    return SEVERITY_SORT.get(str(severity or "unknown").lower(), 6)


def wcag_level_sort_value(level: str | None) -> int:
    return WCAG_LEVEL_SORT.get(str(level or "").upper(), 9)


def issue_scope_sort_value(scope: str | None) -> int:
    return ISSUE_SCOPE_SORT.get(str(scope or "Unknown"), 9)


def infer_owner_team(component_group, component) -> str:
    """
    Assigns an issue to a specific organizational team based on the UI component type.
    """
    # Fix: Force it to a single string if a list sneaks through from the parser
    if isinstance(component_group, list):
        component_group = component_group[0] if component_group else "other"
    if isinstance(component, list):
        component = component[0] if component else "other"
        
    key = (component_group or component or "other").lower()

    return OWNER_TEAM_RULES.get(key, OWNER_TEAM_RULES.get((component or "other").lower(), "Frontend Platform"))


def infer_issue_scope(*, design_system: str | None = None, component: str | None = None, root_cause: str | None = None, pages: int = 1, systemic: bool = False) -> str:
    """
    Determines whether an issue is isolated to a single page, or indicative 
    of a broader design system or template pattern defect.
    """
    root = str(root_cause or "").lower()
    ds = str(design_system or "").lower()
    comp = str(component or "").lower()

    if root.startswith("design system") or (ds and ds != "custom"):
        return "Shared component"

    if systemic or pages >= 3 or comp in {"layout", "header", "navigation"} and pages >= 2:
        return "Shared template/pattern"

    if comp:
        return "Page-specific"

    return "Unknown"


# -------------------------
# 🌐 URL NORMALIZATION
# -------------------------

PAGE_ALIAS_MAP = {
    "upload_form": "upload",
    "menu_element": "shifting_content_menu",
    "shifting_content_menu": "shifting_content_menu",
    "shifting_content-menu": "shifting_content_menu",
    "shifting_content/menu": "shifting_content_menu",
    "jqueryui/menu": "jqueryui_menu",
    "shadow_dom": "shadowdom",
    "shadow-dom": "shadowdom",
    "challenging-dom": "challenging_dom",
    "drag-and-drop": "drag_and_drop",
    "entry-ad": "entry_ad",
    "horizontal-slider": "horizontal_slider",
    "jqueryui-menu": "jqueryui_menu",
    "key-presses": "key_presses",
    "nested-frames": "nested_frames",
    "pet_sitioner": "sitioner",
}


def _normalize_page_token(value: str | None) -> str:
    """Sanitizes raw URLs/filenames into stable tokens for deduplication."""
    if not value:
        return ""
    token = str(value).strip().lower()
    token = token.replace('\\', '/')
    if token.endswith('.json'):
        token = token[:-5]
    token = token.strip('/')
    token = unquote(token)
    token = token.replace('-', '_')
    token = re.sub(r'[^a-z0-9/_]+', '_', token)
    token = re.sub(r'_+', '_', token)
    token = re.sub(r'/+', '/', token)
    token = token.strip('_/')
    return PAGE_ALIAS_MAP.get(token, token)


def canonical_page_key(*candidates: str | None) -> str:
    """
    Takes multiple possible page references (URLs, file paths, IDs) and returns 
    the most stable, normalized key to ensure cross-tool alignment.
    """
    for candidate in candidates:
        if not candidate:
            continue

        raw = str(candidate).strip()
        if not raw or raw.startswith('data:'):
            continue

        if raw.startswith('http://') or raw.startswith('https://'):
            parsed = urlparse(raw)
            path = _normalize_page_token(parsed.path)
            # Avoid using axe report artifact paths as the page key
            if path and not path.startswith('rules/axe/'):
                return path or 'home'
            continue

        token = _normalize_page_token(raw)
        if token:
            return token

    return 'unknown'


def humanize_page_key(page: str | None) -> str:
    """Formats a technical page key into a clean breadcrumb for the dashboard."""
    key = canonical_page_key(page)
    if key == 'home':
        return 'Home'
    return key.replace('_', ' / ').title()