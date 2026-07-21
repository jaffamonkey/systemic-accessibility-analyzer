"""
Processing Engine

This module serves as the primary ETL (Extract, Transform, Load) pipeline for 
raw accessibility violations. It normalizes data from disparate testing tools, 
cleans noisy DOM selectors, maps rules to a canonical taxonomy, and enriches 
the data with Business Intelligence (BI) fields for dashboard reporting.
"""

import re
from pathlib import Path

from analyzer.component_config import COMPONENT_GROUPS
from services.rule_aliases import (
    RULE_ALIAS_MAP,
    PROBLEM_TYPE_MAP,
    CANONICAL_RULES,
)
from analyzer.component_detector import detect_design_system
from analyzer.component_learning import update_learning
from analyzer.utils import simplify_pattern
from analyzer.fingerprint import build_fingerprint
from services.metrics_engine import suggest_component, suggest_component_from_context
from services.severity import normalize_severity
from services.deduplicate_engine import deduplicate_rows
from services.bi_fields import (
    clean_page_name,
    derive_page_group,
    canonical_page_key,
    humanize_page_key,
    humanize_slug,
    infer_owner_team,
    infer_issue_scope,
    issue_scope_sort_value,
    severity_sort_value,
    wcag_level_sort_value,
    estimate_issue_rank_score,
    get_tool_family,
    get_tool_engine,
)


def _slugify_rule_text(value: str) -> str | None:
    """
    Converts arbitrary text into a safe, kebab-case slug for use as a canonical ID.
    """
    if not value:
        return None
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or None


def _canonicalize_htmlsniffer_rule(raw: str) -> str:
    """
    Extracts the core WCAG criteria and technique from noisy HTMLCS strings.
    Example: 'WCAG2AA.Principle1.Guideline1_4.1_4_3.G18' -> 'htmlcs-1_4_3-g18'
    """
    text = str(raw or "").strip()
    if not text:
        return ""

    upper = text.upper()
    wcag_match = re.search(r"(\d)_(\d)_(\d)", upper)
    technique_match = re.search(r"\b([A-Z]+\d+)\b", upper)

    wcag_part = ""
    if wcag_match:
        wcag_part = f"{wcag_match.group(1)}_{wcag_match.group(2)}_{wcag_match.group(3)}"

    technique_part = technique_match.group(1).lower() if technique_match else ""

    if wcag_part and technique_part:
        return f"htmlcs-{wcag_part}-{technique_part}"
    if technique_part:
        return f"htmlcs-{technique_part}"
    if wcag_part:
        return f"htmlcs-{wcag_part}"

    return upper.lower()


def _canonicalize_rule_id(source: str, raw_rule_id: str = None, rule_label: str = None, message: str = None) -> str:
    """
    Maps tool-specific rule IDs to our universal taxonomy. If a direct alias
    doesn't exist, it falls back to a slugified version of the rule label or message.
    """
    source = str(source or "").strip().lower()
    raw = str(raw_rule_id or "").strip()

    # Handle HTMLCS idiosyncrasies first
    if source in {"html-sniffer", "htmlcs", "html_codesniffer", "pa11y-htmlcs"} and raw:
        canonical = _canonicalize_htmlsniffer_rule(raw)
        return RULE_ALIAS_MAP.get(canonical, canonical)

    if raw:
        raw_lower = raw.lower()
        if raw_lower in RULE_ALIAS_MAP:
            return RULE_ALIAS_MAP[raw_lower]
        return raw_lower

    # Fallback 1: Use the rule's human-readable label
    label_slug = _slugify_rule_text(rule_label)
    if label_slug:
        if label_slug in RULE_ALIAS_MAP:
            return RULE_ALIAS_MAP[label_slug]
        return label_slug

    # Fallback 2: Use the error message itself
    message_slug = _slugify_rule_text(message)
    if message_slug:
        if message_slug in RULE_ALIAS_MAP:
            return RULE_ALIAS_MAP[message_slug]
        return message_slug

    return "unknown-rule"


def _canonicalize_problem_type(canonical_rule_id: str) -> str:
    """
    Maps a canonical rule ID to a broader problem category (e.g., 'contrast', 'keyboard').
    """
    canonical = CANONICAL_RULES.get(canonical_rule_id)
    if canonical:
        return canonical.get("problem_type", "other")

    return PROBLEM_TYPE_MAP.get(canonical_rule_id, "other")


def _coerce_selector_value(value) -> str:
    """
    Safely extracts a string representation of a DOM selector, regardless of 
    whether the tool provided it as a string, list, tuple, or dict.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value

    if isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                extracted = ""
                for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
                    if item.get(key):
                        extracted = str(item[key])
                        break
                if not extracted:
                    extracted = str(item)
                parts.append(extracted)
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p).strip()

    if isinstance(value, dict):
        for key in ("xpath", "selector", "target", "css", "path", "html", "dom"):
            if value.get(key):
                return str(value[key]).strip()
        return str(value).strip()

    return str(value).strip()


def _extract_href_token(text: str) -> str | None:
    if not text:
        return None
    match = re.search(r'href\s*=\s*["\']([^"\']+)["\']', str(text), re.IGNORECASE)
    if match:
        return f"href={match.group(1).strip().lower()}"
    return None


def _extract_id_token(text: str) -> str | None:
    if not text:
        return None
    text = str(text).strip()

    # Match CSS id (#my-id)
    match = re.search(r'#([a-zA-Z][\w\-:.]*)', text)
    if match:
        return f"id={match.group(1).lower()}"

    # Match HTML id attribute (id="my-id")
    match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
    if match:
        return f"id={match.group(1).strip().lower()}"

    return None


def _strip_positional_noise(text: str) -> str:
    """
    Removes fragile pseudo-selectors (like nth-child) to prevent dynamic 
    content shifts from breaking our systemic issue clustering.
    """
    if not text:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r":nth-child\(\d+\)", "", text)
    text = re.sub(r":nth-of-type\(\d+\)", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s*>\s*", " > ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_tag_token(text: str) -> str | None:
    if not text:
        return None
    text = str(text).strip().lower()
    for tag in ("button", "a", "input", "select", "textarea", "img", "li", "td", "th"):
        if text == tag or text.startswith(tag) or f"<{tag}" in text or f" {tag}" in text:
            return f"tag={tag}"
    return None


HTMLCS_SOURCES = {"html-sniffer", "pa11y-htmlcs", "htmlcs", "html_codesniffer"}


def _normalize_htmlcs_context(value: str | None) -> str:
    """
    HTMLCS often returns massive blocks of raw HTML/CSS as the context.
    This strips out inline styles, data attributes, and massive class lists to
    prevent clustering failures caused by irrelevant DOM differences.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r'\sstyle="[^"]*"', "", text, flags=re.I)
    text = re.sub(r"\sstyle='[^']*'", "", text, flags=re.I)
    text = re.sub(r"\sdata-[a-z0-9_-]+=\"[^\"]*\"", "", text, flags=re.I)
    text = re.sub(r"\sdata-[a-z0-9_-]+='[^']*'", "", text, flags=re.I)
    text = re.sub(r"\s(class|id)=\"[^\"]{40,}\"", "", text, flags=re.I)
    text = re.sub(r"\s(class|id)='[^']{40,}'", "", text, flags=re.I)
    return text[:300].strip()


def _normalize_htmlcs_selector(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r":nth-child\(\d+\)", "", text)
    text = re.sub(r":nth-of-type\(\d+\)", "", text)
    parts = [p.strip() for p in re.split(r"\s*>\s*|\s+", text) if p.strip()]
    if not parts:
        return ""
    last = parts[-1]
    return last or text[:120]


def _build_normalized_target_key(row: dict, raw_selector: str, pattern: str) -> str:
    """
    Constructs a highly stable fingerprint for a DOM element.
    Evaluates candidates in order of reliability: ID > Cleaned Selector > Href > Tag.
    """
    source = str(row.get("source") or "").strip().lower()
    context = row.get("html") or row.get("context") or row.get("dom")

    # Handle HTMLCS specifically due to its noisy output
    if source in HTMLCS_SOURCES:
        norm_context = _normalize_htmlcs_context(context)
        norm_selector = _normalize_htmlcs_selector(
            raw_selector
            or row.get("selector")
            or row.get("dom_path")
            or row.get("target")
        )

        if norm_context and norm_selector:
            return f"{norm_selector}|{norm_context}"
        if norm_context:
            return norm_context
        if norm_selector:
            if pattern and pattern not in {"unknown-target", norm_selector}:
                return f"{norm_selector}|pattern={pattern}"
            return norm_selector

    # Gather all possible location hints
    candidates = [
        raw_selector,
        row.get("selector"),
        row.get("target"),
        row.get("xpath"),
        row.get("dom_path"),
        row.get("dom"),
        pattern,
    ]

    # 1. Strongest match: explicit ID
    for value in candidates:
        token = _extract_id_token(value)
        if token:
            return token

    # 2. Prefer a meaningful, noise-stripped selector/path
    cleaned_candidates = []
    for value in candidates:
        cleaned = _strip_positional_noise(value)
        if cleaned and cleaned not in {"html", "body", "document"}:
            cleaned_candidates.append(cleaned)

    for cleaned in cleaned_candidates:
        if any(marker in cleaned for marker in ["#", ".", "[", ">", "/", "href=", "id="]):
            return cleaned

    # 3. Href can help, but shouldn't stand alone if we can avoid it
    for value in candidates:
        href_token = _extract_href_token(value)
        if href_token:
            tag_token = _extract_tag_token(value) or _extract_tag_token(pattern)
            if pattern and pattern not in {"a", "link", "button", "input", "unknown-target"}:
                return f"{tag_token or 'tag=unknown'}|{href_token}|pattern={pattern}"
            return f"{tag_token or 'tag=unknown'}|{href_token}"

    # 4. Final fallback: HTML Tag
    tag_token = _extract_tag_token(raw_selector) or _extract_tag_token(pattern)
    if tag_token:
        if pattern and pattern not in {"a", "link", "button", "input", "unknown-target"}:
            return f"{tag_token}|pattern={pattern}"
        return tag_token

    return pattern or "unknown-target"


def process_rows(rows: list) -> list:
    """
    Main processing loop. Iterates through raw violation rows to clean, 
    normalize, and enrich the dataset before generating BI dashboards.
    """
    cleaned_rows = []
    
    for r in rows:
        # --- 1. PAGE IDENTIFICATION ---
        # Capture page identifier from known file paths if explicit page name is missing
        if not r.get("page") or r.get("page") == "Unknown":
            source_path = r.get("source_file") or r.get("path")
            if source_path:
                r["page"] = Path(source_path).stem

        # --- 2. SEVERITY & TOOL IDENTIFICATION ---
        severity = normalize_severity(r.get("severity"))
        if severity is None:
            continue
        r["severity"] = severity

        source = r.get("source")
        r["tool_family"] = r.get("tool_family") or get_tool_family(source)
        r["tool_engine"] = r.get("tool_engine") or get_tool_engine(source)

        if not r.get("sources"):
            r["sources"] = [source] if source else []

        # Deduplicate tool families and engines
        existing_families = r.get("tool_families")
        if existing_families:
            r["tool_families"] = sorted({str(v) for v in existing_families if v})
        else:
            r["tool_families"] = [r["tool_family"]] if r["tool_family"] else []

        existing_engines = r.get("tool_engines")
        if existing_engines:
            r["tool_engines"] = sorted({str(v) for v in existing_engines if v})
        else:
            r["tool_engines"] = [r["tool_engine"]] if r["tool_engine"] else []

        r["tool_family_count"] = max(1, len(r["tool_families"])) if r["tool_families"] else 1
        r["tool_engine_count"] = max(1, len(r["tool_engines"])) if r["tool_engines"] else 1
        r["tool_count"] = max(1, int(r.get("tool_count") or len(r["sources"]) or 1))

        # --- 3. DOM SELECTOR EXTRACTION ---
        raw_selector = (
            r.get("selector")
            or r.get("dom")
            or r.get("context")
            or r.get("target")
            or r.get("xpath")
            or r.get("path")
            or ""
        )

        raw_selector = _coerce_selector_value(raw_selector)
        r["selector"] = raw_selector
        r["dom_path"] = raw_selector or _coerce_selector_value(r.get("dom"))

        try:
            pattern = simplify_pattern(raw_selector)
        except Exception:
            pattern = ""

        # Edge Case: SpecA11y often has stable rule IDs for page-level findings with no DOM selector.
        source_key = str(r.get("source") or "").strip().lower()
        if source_key == "speca11y":
            speca11y_rule_key = (
                r.get("rule_id")
                or r.get("ruleId")
                or r.get("canonical_rule_id")
                or r.get("rule_name")
            )
            speca11y_pattern = _slugify_rule_text(speca11y_rule_key)
            if speca11y_pattern:
                pattern = speca11y_pattern

        if not pattern or pattern in ["html", "body", "document"]:
            continue

        parts = pattern.split("_") if pattern else []
        r["pattern"] = pattern
        r["pattern_parts"] = parts

        # --- 4. CANONICAL RULE NORMALIZATION ---
        raw_rule_id = r.get("ruleId") or r.get("rule_id")
        if str(r.get("source") or "").strip().lower() == "speca11y":
            raw_rule_id = r.get("rule_id") or r.get("ruleId")

        canonical_rule_id = _canonicalize_rule_id(
            source=r.get("source"),
            raw_rule_id=raw_rule_id,
            rule_label=r.get("rule_name") or r.get("rule") or r.get("title"),
            message=r.get("message"),
        )

        r["canonical_rule_id"] = canonical_rule_id
        r["canonical_problem_type"] = _canonicalize_problem_type(canonical_rule_id)
        r["normalized_target_key"] = _build_normalized_target_key(r, raw_selector, pattern)

        # --- 5. COMPONENT & DESIGN SYSTEM DETECTION ---
        component = suggest_component(pattern)
        if not component:
            component = suggest_component_from_context(
                rule_id=r.get("ruleId"),
                message=r.get("message"),
                dom_path=r.get("dom_path") or r.get("selector") or r.get("dom"),
                pattern=pattern,
            )

        design_system = detect_design_system(pattern)

        # Log unrecognized patterns to the learning engine
        if not component:
            update_learning(pattern)
            component = "other"

        group = COMPONENT_GROUPS.get(component, component)

        # --- 6. BI FIELD ENRICHMENT ---
        page_key = canonical_page_key(
            r.get("page"),
            r.get("url"),
            r.get("file"),
            r.get("document"),
            r.get("page_url"),
        )

        r["component"] = component
        r["component_group"] = group
        r["design_system"] = design_system or "custom"
        r["pattern"] = pattern
        r["page"] = page_key
        r["page_id"] = page_key
        r["page_display"] = humanize_page_key(page_key)
        r["page_group"] = derive_page_group(page_key)
        r["severity_sort"] = severity_sort_value(severity)
        r["severity_label"] = humanize_slug(severity)
        r["wcag_level_sort"] = wcag_level_sort_value(r.get("wcag_level"))
        r["component_display"] = humanize_slug(component)
        r["component_group_display"] = humanize_slug(group)
        r["display_pattern"] = (
            r.get("rule_name")
            if str(r.get("source") or "").strip().lower() == "speca11y" and r.get("rule_name")
            else humanize_slug(pattern)
        )
        r["rule_display"] = (
            r.get("rule_name")
            or r.get("rule")
            or r.get("title")
            or r.get("message")
            or canonical_rule_id
        )
        r["fingerprint"] = build_fingerprint(
            r.get("dom"),
            r["normalized_target_key"] or raw_selector or pattern
        )
        r["owner_team"] = infer_owner_team(group, component)
        r["design_system_issue"] = (design_system or "custom") != "custom"
        r["issue_scope"] = infer_issue_scope(
            design_system=design_system,
            component=component,
            pages=1,
            systemic=False,
        )
        r["issue_scope_sort"] = issue_scope_sort_value(r["issue_scope"])
        r["is_systemic"] = False
        r["affected_pages_count"] = 1
        r["issue_rank_score"] = estimate_issue_rank_score(
            severity=severity,
            pages=1,
            instance_count=int(r.get("instance_count") or 1),
            systemic=False,
            tool_count=int(r.get("tool_count") or 1),
            tool_family_count=int(r.get("tool_family_count") or 1),
            tool_engine_count=int(r.get("tool_engine_count") or 1),
        )

        cleaned_rows.append(r)

    # --- 7. FINAL DEDUPLICATION ---
    return deduplicate_rows(cleaned_rows)