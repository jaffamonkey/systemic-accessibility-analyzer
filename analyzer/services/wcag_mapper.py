import re

from services.wcag_refs import RULE_WCAG_MAP, resolve_rule_wcag

def extract_wcag_from_text(text):
    if not text:
        return None

    match = re.search(r"\b\d\.\d\.\d\b", str(text))
    if match:
        return match.group(0)

    return None

def guess_wcag_from_message(message):
    if not message:
        return None

    msg = str(message).lower()

    if "contrast" in msg:
        return "1.4.3"

    if "text spacing" in msg or "spacing must be adjustable" in msg or "inline spacing" in msg:
        return "1.4.12"

    if "target size" in msg or "touch target" in msg or "target spacing" in msg:
        return "2.5.8"

    if "label" in msg:
        return "3.3.2"

    if "heading" in msg:
        return "2.4.6"

    if "frame" in msg or "iframe" in msg:
        return "2.4.1"

    if "nested interactive" in msg or "interactive controls must not be nested" in msg:
        return "4.1.2"

    if "checkbox" in msg and "group" in msg:
        return "1.3.1"

    if "command name" in msg or "accessible name" in msg:
        return "4.1.2"

    if "link" in msg and "purpose" in msg:
        return "2.4.4"

    if "error" in msg:
        return "3.3.1"

    if "document is not tagged" in msg or "tagged pdf" in msg:
        return "1.3.1"

    if "document language" in msg or "language is not set" in msg:
        return "3.1.1"

    if "title property" in msg or "document title" in msg:
        return "2.4.2"

    if "reading order" in msg:
        return "1.3.2"

    if "tab order" in msg:
        return "2.4.3"

    if "alt text" in msg and ("image" in msg or "figure" in msg):
        return "1.1.1"

    if "bookmark" in msg:
        return "2.4.5"

    if "table header" in msg or "table headers" in msg:
        return "1.3.1"

    if "form field" in msg and "description" in msg:
        return "3.3.2"

    return None

def ensure_wcag(row):
    rule = str(
        row.get("ruleId")
        or row.get("rule_id")
        or row.get("rule")
        or ""
    ).strip().lower()

    mapped = resolve_rule_wcag(rule)
    if mapped:
        return mapped

    if rule in RULE_WCAG_MAP:
        return RULE_WCAG_MAP[rule]

    normalized_rule = rule.replace("-", "_")
    mapped = resolve_rule_wcag(normalized_rule)
    if mapped:
        return mapped

    match = re.search(r"\d+\.\d+\.\d+", rule)
    if match:
        return match.group(0)

    message = str(row.get("message", "") or "")
    help_url = str(row.get("help", "") or row.get("helpUrl", "") or "")
    description = str(row.get("description", "") or "")
    combined = f"{rule} {normalized_rule} {message} {description} {help_url}".lower()

    if "landmark" in combined or "banner" in combined:
        return "1.3.1"

    if "target-size" in combined or "target size" in combined or "target spacing" in combined:
        return "2.5.8"

    if "text_spacing_valid" in combined or "text spacing" in combined or "avoid-inline-spacing" in combined:
        return "1.4.12"

    if "nested-interactive" in combined or "nested interactive" in combined:
        return "4.1.2"

    if "checkbox" in combined and "group" in combined:
        return "1.3.1"

    if "frame-title-unique" in combined:
        return "2.4.1"

    if "frame-title" in combined:
        return "4.1.2"

    if "aria-command-name" in combined:
        return "4.1.2"

    if "button-name" in combined:
        return "4.1.2"

    if "color-contrast" in combined:
        return "1.4.3"

    if "duplicate-id-active" in combined:
        return "4.1.1"

    if "image-alt" in combined:
        return "1.1.1"

    if "area_alt_exists" in combined or "area-alt" in combined or "area alt" in combined:
        return "1.1.1"

    if "imagemap_alt_exists" in combined or "imagemap alt" in combined:
        return "1.1.1"

    if "label_ref_valid" in combined:
        return "3.3.2"

    if "html_lang_exists" in combined or "html-has-lang" in combined or "html has lang" in combined:
        return "3.1.1"

    if "listitem" in combined:
        return "1.3.1"

    if "table_headers_exists" in combined:
        return "1.3.1"

    if "aria_eventhandler_role_valid" in combined:
        return "4.1.2"

    if "caption_track_exists" in combined or "caption track" in combined:
        return "1.2.2"

    if "text_quoted_correctly" in combined or "text quoted correctly" in combined:
        return "1.3.1"

    if "video-caption" in combined or "video caption" in combined:
        return "1.2.2"

    if "link-in-text-block" in combined or "link-name" in combined:
        return "2.4.4"

    if "select-name" in combined:
        return "4.1.2"

    if "page-errors" in combined:
        return "3.3.1"

    if "document-is-not-tagged" in combined or "document not tagged" in combined or "tagged pdf" in combined:
        return "1.3.1"

    if "document-metadata-is-missing-language-property" in combined or "document-language-is-not-set" in combined or "document language" in combined or "language is not set" in combined:
        return "3.1.1"

    if "document-metadata-is-missing-title-property" in combined or "document-has-no-title" in combined or "document-title-is-missing" in combined or "document title" in combined or "title property" in combined:
        return "2.4.2"

    if "document-reading-order-is-incorrect" in combined or "reading order" in combined:
        return "1.3.2"

    if "document-tab-order-does-not-match-structure" in combined or "tab order" in combined:
        return "2.4.3"

    if "image-alt-text-missing" in combined or "figure-missing-alt" in combined or ("alt text" in combined and ("image" in combined or "figure" in combined)):
        return "1.1.1"

    if "link-annotation-missing-alt-text" in combined:
        return "2.4.4"

    if "form-field-has-no-description" in combined or ("form field" in combined and "description" in combined):
        return "3.3.2"

    if "form-field-name-missing" in combined:
        return "4.1.2"

    if "table-has-no-headers" in combined or "table-header-cell-has-no-scope" in combined or "table header" in combined:
        return "1.3.1"

    if "headings-not-nested-properly" in combined:
        return "2.4.6"

    if "bookmarks-missing" in combined or "bookmark" in combined:
        return "2.4.5"
    
    if "document has no headings" in combined:
        return "2.4.6"

    if "layout with spaces" in combined or "consecutive spaces" in combined:
        return "1.3.1"
    
    if "html_skipnav_exists" in combined or "bypass repeated blocks" in combined:
        return "2.4.1"

    if "element_tabbable_visible" in combined or "visible when it has keyboard focus" in combined:
        return "2.4.7"

    if "style_color_misuse" in combined or "color is not used as the only visual means" in combined:
        return "1.4.1"

    wcag = extract_wcag_from_text(message) or extract_wcag_from_text(help_url) or extract_wcag_from_text(description)
    if wcag:
        return wcag

    wcag = guess_wcag_from_message(message) or guess_wcag_from_message(description)
    if wcag:
        return wcag

    return None
