"""
WCAG Reference Taxonomy

The master lookup table for official WCAG 2.2 Success Criteria. 
It contains the exact titles, levels (A/AA/AAA), and W3C documentation URLs.
It also provides helper functions to hydrate proprietary rule strings with 
official WCAG metadata.
"""

import re
from services.wcag_techniques import WCAG_TECHNIQUES

# The master taxonomy of WCAG Success Criteria
WCAG_SUCCESS_CRITERIA = {
  "1.1.1": {"title": "Non-text Content", "level": "A", "url": "https://www.w3.org"},
  "1.2.1": {"title": "Audio-only and Video-only (Prerecorded)", "level": "A", "url": "https://www.w3.org"},
  "1.2.2": {"title": "Captions (Prerecorded)", "level": "A", "url": "https://www.w3.org"},
  "1.2.3": {"title": "Audio Description or Media Alternative (Prerecorded)", "level": "A", "url": "https://www.w3.org"},
  "1.2.4": {"title": "Captions (Live)", "level": "AA", "url": "https://www.w3.org"},
  "1.2.5": {"title": "Audio Description (Prerecorded)", "level": "AA", "url": "https://www.w3.org"},
  "1.2.6": {"title": "Sign Language (Prerecorded)", "level": "AAA", "url": "https://www.w3.org"},
  "1.2.7": {"title": "Extended Audio Description (Prerecorded)", "level": "AAA", "url": "https://www.w3.org"},
  "1.2.8": {"title": "Media Alternative (Prerecorded)", "level": "AAA", "url": "https://www.w3.org"},
  "1.2.9": {"title": "Audio-only (Live)", "level": "AAA", "url": "https://www.w3.org"},
  "1.3.1": {"title": "Info and Relationships", "level": "A", "url": "https://www.w3.org"},
  "1.3.2": {"title": "Meaningful Sequence", "level": "A", "url": "https://www.w3.org"},
  "1.3.3": {"title": "Sensory Characteristics", "level": "A", "url": "https://www.w3.org"},
  "1.3.4": {"title": "Orientation", "level": "AA", "url": "https://www.w3.org"},
  "1.3.5": {"title": "Identify Input Purpose", "level": "AA", "url": "https://www.w3.org"},
  "1.3.6": {"title": "Identify Purpose", "level": "AAA", "url": "https://www.w3.org"},
  "1.4.1": {"title": "Use of Color", "level": "A", "url": "https://www.w3.org"},
  "1.4.2": {"title": "Audio Control", "level": "A", "url": "https://www.w3.org"},
  "1.4.3": {"title": "Contrast (Minimum)", "level": "AA", "url": "https://www.w3.org"},
  "1.4.4": {"title": "Resize text", "level": "AA", "url": "https://www.w3.org"},
  "1.4.5": {"title": "Images of Text", "level": "AA", "url": "https://www.w3.org"},
  "1.4.6": {"title": "Contrast (Enhanced)", "level": "AAA", "url": "https://www.w3.org"},
  "1.4.7": {"title": "Low or No Background Audio", "level": "AAA", "url": "https://www.w3.org"},
  "1.4.8": {"title": "Visual Presentation", "level": "AAA", "url": "https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html"},
  "1.4.9": {"title": "Images of Text (No Exception)", "level": "AAA", "url": "https://www.w3.org"},
  "1.4.10": {"title": "Reflow", "level": "AA", "url": "https://www.w3.org"},
  "1.4.11": {"title": "Non-text Contrast", "level": "AA", "url": "https://www.w3.org"},
  "1.4.12": {"title": "Text Spacing", "level": "AA", "url": "https://www.w3.org"},
  "1.4.13": {"title": "Content on Hover or Focus", "level": "AA", "url": "https://www.w3.org"},
  "2.1.1": {"title": "Keyboard", "level": "A", "url": "https://www.w3.org"},
  "2.1.2": {"title": "No Keyboard Trap", "level": "A", "url": "https://www.w3.org"},
  "2.1.3": {"title": "Keyboard (No Exception)", "level": "AAA", "url": "https://www.w3.org"},
  "2.1.4": {"title": "Character Key Shortcuts", "level": "A", "url": "https://www.w3.org"},
  "2.2.1": {"title": "Timing Adjustable", "level": "A", "url": "https://www.w3.org"},
  "2.2.2": {"title": "Pause, Stop, Hide", "level": "A", "url": "https://www.w3.org"},
  "2.2.3": {"title": "No Timing", "level": "AAA", "url": "https://www.w3.org"},
  "2.2.4": {"title": "Interruptions", "level": "AAA", "url": "https://www.w3.org"},
  "2.2.5": {"title": "Re-authenticating", "level": "AAA", "url": "https://www.w3.org"},
  "2.2.6": {"title": "Timeouts", "level": "AAA", "url": "https://www.w3.org"},
  "2.3.1": {"title": "Three Flashes or Below Threshold", "level": "A", "url": "https://www.w3.org"},
  "2.3.2": {"title": "Three Flashes", "level": "AAA", "url": "https://www.w3.org"},
  "2.3.3": {"title": "Animation from Interactions", "level": "AAA", "url": "https://www.w3.org"},
  "2.4.1": {"title": "Bypass Blocks", "level": "A", "url": "https://www.w3.org"},
  "2.4.2": {"title": "Page Titled", "level": "A", "url": "https://www.w3.org"},
  "2.4.3": {"title": "Focus Order", "level": "A", "url": "https://www.w3.org"},
  "2.4.4": {"title": "Link Purpose (In Context)", "level": "A", "url": "https://www.w3.org"},
  "2.4.5": {"title": "Multiple Ways", "level": "AA", "url": "https://www.w3.org"},
  "2.4.6": {"title": "Headings and Labels", "level": "AA", "url": "https://www.w3.org"},
  "2.4.7": {"title": "Focus Visible", "level": "AA", "url": "https://www.w3.org"},
  "2.4.8": {"title": "Location", "level": "AAA", "url": "https://www.w3.org"},
  "2.4.9": {"title": "Link Purpose (Link Only)", "level": "AAA", "url": "https://www.w3.org"},
  "2.4.10": {"title": "Section Headings", "level": "AAA", "url": "https://www.w3.org"},
  "2.4.11": {"title": "Focus Not Obscured (Minimum)", "level": "AA", "url": "https://www.w3.org"},
  "2.4.12": {"title": "Focus Not Obscured (Enhanced)", "level": "AAA", "url": "https://www.w3.org"},
  "2.4.13": {"title": "Focus Appearance", "level": "AAA", "url": "https://www.w3.org"},
  "2.5.1": {"title": "Pointer Gestures", "level": "A", "url": "https://www.w3.org"},
  "2.5.2": {"title": "Pointer Cancellation", "level": "A", "url": "https://www.w3.org"},
  "2.5.3": {"title": "Label in Name", "level": "A", "url": "https://www.w3.org"},
  "2.5.4": {"title": "Motion Actuation", "level": "A", "url": "https://www.w3.org"},
  "2.5.5": {"title": "Target Size (Enhanced)", "level": "AAA", "url": "https://www.w3.org"},
  "2.5.6": {"title": "Concurrent Input Mechanisms", "level": "AAA", "url": "https://www.w3.org"},
  "2.5.7": {"title": "Dragging Movements", "level": "AA", "url": "https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html"},
  "2.5.8": {"title": "Target Size (Minimum)", "level": "AA", "url": "https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html"},
  "3.1.1": {"title": "Language of Page", "level": "A", "url": "https://www.w3.org"},
  "3.1.2": {"title": "Language of Parts", "level": "AA", "url": "https://www.w3.org"},
  "3.1.3": {"title": "Unusual Words", "level": "AAA", "url": "https://www.w3.org"},
  "3.1.4": {"title": "Abbreviations", "level": "AAA", "url": "https://www.w3.org"},
  "3.1.5": {"title": "Reading Level", "level": "AAA", "url": "https://www.w3.org"},
  "3.1.6": {"title": "Pronunciation", "level": "AAA", "url": "https://www.w3.org"},
  "3.2.1": {"title": "On Focus", "level": "A", "url": "https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html"},
  "3.2.2": {"title": "On Input", "level": "A", "url": "https://www.w3.org"},
  "3.2.3": {"title": "Consistent Navigation", "level": "AA", "url": "https://www.w3.org"},
  "3.2.4": {"title": "Consistent Identification", "level": "AA", "url": "https://www.w3.org"},
  "3.2.5": {"title": "Change on Request", "level": "AAA", "url": "https://www.w3.org"},
  "3.2.6": {"title": "Consistent Help", "level": "A", "url": "https://www.w3.org"},
  "3.3.1": {"title": "Error Identification", "level": "A", "url": "https://www.w3.org"},
  "3.3.2": {"title": "Labels or Instructions", "level": "A", "url": "https://www.w3.org"},
  "3.3.3": {"title": "Error Suggestion", "level": "AA", "url": "https://www.w3.org"},
  "3.3.4": {"title": "Error Prevention (Legal, Financial, Data)", "level": "AA", "url": "https://www.w3.org"},
  "3.3.5": {"title": "Help", "level": "AAA", "url": "https://www.w3.org"},
  "3.3.6": {"title": "Error Prevention (All)", "level": "AAA", "url": "https://www.w3.org"},
  "3.3.7": {"title": "Redundant Entry", "level": "A", "url": "https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry.html"},
  "3.3.8": {"title": "Accessible Authentication (Minimum)", "level": "AA", "url": "https://www.w3.org"},
  "3.3.9": {"title": "Accessible Authentication (Enhanced)", "level": "AAA", "url": "https://www.w3.org"},
  "4.1.1": {"title": "Parsing", "level": "A", "url": "https://www.w3.org"},
  "4.1.2": {"title": "Name, Role, Value", "level": "A", "url": "https://www.w3.org"},
  "4.1.3": {"title": "Status Messages", "level": "AA", "url": "https://www.w3.org"},
}

# Strict dictionary mapping common proprietary tool rules directly to a WCAG ID
RULE_WCAG_MAP = {
    "aria-command-name": "4.1.2",
    "aria_command_name": "4.1.2",
    "frame-title-unique": "2.4.1",
    "frame_title_unique": "2.4.1",
    "input_checkboxes_grouped": "1.3.1",
    "landmark-no-duplicate-banner": "1.3.1",
    "landmark_no_duplicate_banner": "1.3.1",
    "aria_banner_label_unique": "1.3.1",
    "nested-interactive": "4.1.2",
    "nested_interactive": "4.1.2",
    "page-errors": "3.3.1",
    "page_errors": "3.3.1",
    "target_spacing_sufficient": "2.5.8",
    "target-size": "2.5.8",
    "target_size": "2.5.8",
    "text_spacing_valid": "1.4.12",
    "avoid-inline-spacing": "1.4.12",
    "avoid_inline_spacing": "1.4.12",
    "button-name": "4.1.2",
    "button_name": "4.1.2",
    "color-contrast": "1.4.3",
    "color_contrast": "1.4.3",
    "duplicate-id-active": "4.1.1",
    "duplicate_id_active": "4.1.1",
    "frame-title": "4.1.2",
    "frame_title": "4.1.2",
    "image-alt": "1.1.1",
    "image_alt": "1.1.1",
    "label": "1.3.1",
    "label_ref_valid": "3.3.2",
    "link-in-text-block": "2.4.4",
    "link_in_text_block": "2.4.4",
    "link-name": "2.4.4",
    "link_name": "2.4.4",
    "list": "1.3.1",
    "listitem": "1.3.1",
    "select-name": "4.1.2",
    "select_name": "4.1.2",
    "document-not-tagged": "1.3.1",
    "document_not_tagged": "1.3.1",
    "document-language-is-not-set": "3.1.1",
    "document_language_is_not_set": "3.1.1",
    "document-metadata-is-missing-title-property": "2.4.2",
    "document_metadata_is_missing_title_property": "2.4.2",
    "document-has-no-title": "2.4.2",
    "document_has_no_title": "2.4.2",
    "document-title-is-missing": "2.4.2",
    "document_title_is_missing": "2.4.2",
    "document-title-not-showing-in-window-title-bar": "2.4.2",
    "document_title_not_showing_in_window_title_bar": "2.4.2",
    "document-reading-order-is-incorrect": "1.3.2",
    "document_reading_order_is_incorrect": "1.3.2",
    "document-tab-order-does-not-match-structure": "2.4.3",
    "document_tab_order_does_not_match_structure": "2.4.3",
    "image-alt-text-missing": "1.1.1",
    "image_alt_text_missing": "1.1.1",
    "figure-missing-alt": "1.1.1",
    "figure_missing_alt": "1.1.1",
    "link-annotation-missing-alt-text": "2.4.4",
    "link_annotation_missing_alt_text": "2.4.4",
    "form-field-has-no-description": "3.3.2",
    "form_field_has_no_description": "3.3.2",
    "form-field-name-missing": "4.1.2",
    "form_field_name_missing": "4.1.2",
    "table-has-no-headers": "1.3.1",
    "table_has_no_headers": "1.3.1",
    "table-header-cell-has-no-scope": "1.3.1",
    "table_header_cell_has_no_scope": "1.3.1",
    "table_headers_exists": "1.3.1",
    "headings-not-nested-properly": "2.4.6",
    "headings_not_nested_properly": "2.4.6",
    "bookmarks-missing": "2.4.5",
    "bookmarks_missing": "2.4.5",
    "video-caption": "1.2.2",
    "video_caption": "1.2.2",
    "caption_track_exists": "1.2.2",
    "text_quoted_correctly": "1.3.1",
    "document-has-no-headings": "2.4.6",
    "document_has_no_headings": "2.4.6",
    "pdf-layout-with-spaces": "1.3.1",
    "pdf_layout_with_spaces": "1.3.1",
    "html_skipnav_exists": "2.4.1",
    "element_tabbable_visible": "2.4.7",
    "style_color_misuse": "1.4.1"
}


def extract_wcag_technique(rule_text: str | None) -> str | None:
    """Extracts technique tags (e.g., [G18]) from embedded HTMLCS rule strings."""
    if not rule_text:
        return None

    match = re.search(r"\[(.*?)\]", str(rule_text))
    return match.group(1) if match else None


def enrich_wcag_rule(rule: str | None) -> str | None:
    """Combines a base WCAG rule with its official W3C title and technique description."""
    if not rule:
        return rule

    match = re.match(r"([\d\.]+)\s*\[([A-Z0-9]+)\]", str(rule))
    if not match:
        return rule

    wcag_id, technique = match.groups()
    ref = WCAG_SUCCESS_CRITERIA.get(wcag_id, {})
    title = ref.get("title", "")
    tech = WCAG_TECHNIQUES.get(technique, {})
    tech_desc = tech.get("description", "")

    if tech_desc:
        return f"{wcag_id} – {title} ({technique}: {tech_desc})"
    if title:
        return f"{wcag_id} – {title}"
    return rule


def resolve_rule_wcag(rule_id: str) -> str | None:
    if not rule_id:
        return None
    return RULE_WCAG_MAP.get(str(rule_id).strip().lower())


def resolve_wcag_level(wcag_id: str) -> str | None:
    if not wcag_id:
        return None
    ref = WCAG_SUCCESS_CRITERIA.get(str(wcag_id).strip())
    return ref.get("level") if ref else None


def slugify_title(title: str) -> str:
    """Cleans a string for use as an ID or CSS class name."""
    if not title:
        return ""

    return (
        title.lower()
        .replace("_", "-")
        .replace("(", "")
        .replace(")", "")
        .replace(":", "")
        .replace(",", "")
        .replace(".", "")
        .replace("/", "-")
        .strip()
        .replace(" ", "-")
    )