"""
WCAG Mapper & Fallback Engine

Not all accessibility testing tools explicitly link their findings to an official
WCAG Success Criterion. This module acts as a robust fallback, using regex and 
heuristic keyword matching against error messages and rule descriptions to 
infer the correct WCAG ID when it is missing from the raw report.
"""

import re
from services.wcag_refs import RULE_WCAG_MAP, resolve_rule_wcag

def extract_wcag_from_text(text: str | None) -> str | None:
    """Uses regex to scrape standard WCAG IDs (e.g., '1.4.3') directly from text."""
    if not text:
        return None

    match = re.search(r"\b\d\.\d\.\d\b", str(text))
    if match:
        return match.group(0)

    return None

def guess_wcag_from_message(message: str | None) -> str | None:
    """
    A brute-force heuristic fallback. Searches for known terminology inside
    a tool's error message to guess the most likely WCAG criterion.
    """
    if not message:
        return None

    msg = str(message).lower()

    # Contrast & Visuals
    if "contrast" in msg: return "1.4.3"
    if "text spacing" in msg or "spacing must be adjustable" in msg or "inline spacing" in msg: return "1.4.12"
    if "target size" in msg or "touch target" in msg or "target spacing" in msg: return "2.5.8"
    
    # Structure & Semantics
    if "heading" in msg: return "2.4.6"
    if "table header" in msg or "table headers" in msg: return "1.3.1"
    if "reading order" in msg: return "1.3.2"
    
    # Forms & Interactive Elements
    if "label" in msg and "form" not in msg: return "3.3.2" # Note: Adjusted to prevent clashing below
    if "form field" in msg and "description" in msg: return "3.3.2"
    if "checkbox" in msg and "group" in msg: return "1.3.1"
    if "command name" in msg or "accessible name" in msg: return "4.1.2"
    if "nested interactive" in msg or "interactive controls must not be nested" in msg: return "4.1.2"
    if "error" in msg: return "3.3.1"
    
    # Navigation & Links
    if "tab order" in msg: return "2.4.3"
    if "bookmark" in msg: return "2.4.5"
    if "link" in msg and "purpose" in msg: return "2.4.4"
    if "frame" in msg or "iframe" in msg: return "2.4.1"
    
    # Media & Documents
    if "alt text" in msg and ("image" in msg or "figure" in msg): return "1.1.1"
    if "document is not tagged" in msg or "tagged pdf" in msg: return "1.3.1"
    if "document language" in msg or "language is not set" in msg: return "3.1.1"
    if "title property" in msg or "document title" in msg: return "2.4.2"

    return None

def ensure_wcag(row: dict) -> str | None:
    """
    The main resolution pipeline for determining a WCAG criteria.
    Attempts strict mapping first, then falls back to heuristic string matching
    on the combined description and help URLs.
    """
    rule = str(
        row.get("ruleId")
        or row.get("rule_id")
        or row.get("rule")
        or ""
    ).strip().lower()

    # 1. Attempt exact rule mapping
    mapped = resolve_rule_wcag(rule)
    if mapped: return mapped
    if rule in RULE_WCAG_MAP: return RULE_WCAG_MAP[rule]

    # 2. Attempt exact rule mapping with underscores
    normalized_rule = rule.replace("-", "_")
    mapped = resolve_rule_wcag(normalized_rule)
    if mapped: return mapped

    # 3. Attempt to extract a raw WCAG ID from the rule string itself
    match = re.search(r"\d+\.\d+\.\d+", rule)
    if match: return match.group(0)

    # 4. Fallback: Concatenate all available text and perform heuristic keyword mapping
    message = str(row.get("message", "") or "")
    help_url = str(row.get("help", "") or row.get("helpUrl", "") or "")
    description = str(row.get("description", "") or "")
    combined = f"{rule} {normalized_rule} {message} {description} {help_url}".lower()

    # Core Structural Issues
    if "landmark" in combined or "banner" in combined: return "1.3.1"
    if "listitem" in combined: return "1.3.1"
    if "table_headers_exists" in combined or "table-has-no-headers" in combined or "table-header-cell-has-no-scope" in combined or "table header" in combined: return "1.3.1"
    if "layout with spaces" in combined or "consecutive spaces" in combined: return "1.3.1"
    if "checkbox" in combined and "group" in combined: return "1.3.1"
    if "headings-not-nested-properly" in combined or "document has no headings" in combined: return "2.4.6"
    
    # Interaction & Focus
    if "target-size" in combined or "target size" in combined or "target spacing" in combined: return "2.5.8"
    if "nested-interactive" in combined or "nested interactive" in combined: return "4.1.2"
    if "aria-command-name" in combined or "button-name" in combined or "select-name" in combined or "form-field-name-missing" in combined: return "4.1.2"
    if "aria_eventhandler_role_valid" in combined: return "4.1.2"
    if "element_tabbable_visible" in combined or "visible when it has keyboard focus" in combined: return "2.4.7"
    if "duplicate-id-active" in combined: return "4.1.1"
    
    # Visuals & Contrast
    if "color-contrast" in combined: return "1.4.3"
    if "style_color_misuse" in combined or "color is not used as the only visual means" in combined: return "1.4.1"
    if "text_spacing_valid" in combined or "text spacing" in combined or "avoid-inline-spacing" in combined: return "1.4.12"
    
    # Media & Links
    if "image-alt" in combined or "image-alt-text-missing" in combined or "figure-missing-alt" in combined or ("alt text" in combined and ("image" in combined or "figure" in combined)): return "1.1.1"
    if "area_alt_exists" in combined or "area-alt" in combined or "area alt" in combined: return "1.1.1"
    if "imagemap_alt_exists" in combined or "imagemap alt" in combined: return "1.1.1"
    if "caption_track_exists" in combined or "caption track" in combined or "video-caption" in combined or "video caption" in combined: return "1.2.2"
    if "link-in-text-block" in combined or "link-name" in combined or "link-annotation-missing-alt-text" in combined: return "2.4.4"

    # Frames & Documents
    if "frame-title-unique" in combined: return "2.4.1"
    if "frame-title" in combined: return "4.1.2"
    if "html_skipnav_exists" in combined or "bypass repeated blocks" in combined: return "2.4.1"
    if "document-is-not-tagged" in combined or "document not tagged" in combined or "tagged pdf" in combined or "text_quoted_correctly" in combined or "text quoted correctly" in combined: return "1.3.1"
    if "document-metadata-is-missing-language-property" in combined or "document-language-is-not-set" in combined or "document language" in combined or "language is not set" in combined or "html_lang_exists" in combined or "html-has-lang" in combined or "html has lang" in combined: return "3.1.1"
    if "document-metadata-is-missing-title-property" in combined or "document-has-no-title" in combined or "document-title-is-missing" in combined or "document title" in combined or "title property" in combined: return "2.4.2"
    if "document-reading-order-is-incorrect" in combined or "reading order" in combined: return "1.3.2"
    if "document-tab-order-does-not-match-structure" in combined or "tab order" in combined: return "2.4.3"
    
    # Forms & Errors
    if "label_ref_valid" in combined: return "3.3.2"
    if "form-field-has-no-description" in combined or ("form field" in combined and "description" in combined): return "3.3.2"
    if "page-errors" in combined: return "3.3.1"
    if "bookmarks-missing" in combined or "bookmark" in combined: return "2.4.5"

    # 5. Final pass using standard string extractors
    wcag = extract_wcag_from_text(message) or extract_wcag_from_text(help_url) or extract_wcag_from_text(description)
    if wcag: return wcag

    wcag = guess_wcag_from_message(message) or guess_wcag_from_message(description)
    if wcag: return wcag

    return None