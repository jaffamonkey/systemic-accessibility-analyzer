"""
Rule Formatter

Provides a clean mapping from highly technical, tool-specific rule slugs 
(e.g., 'aria_hidden_nontabbable' or 'svg_graphics_labelled') to standard 
WCAG reference codes. This ensures the deduplicate engine correctly merges 
findings from different tools into the same cluster.
"""

WCAG_RULE_MAP = {
    # -------------------
    # WCAG 1.1.1 Non-text Content
    # -------------------
    "svg_graphics_labelled": "1.1.1",
    "image-alt": "1.1.1",
    "image_alt": "1.1.1",
    "svg-img-alt": "1.1.1",
    "svg_img_alt": "1.1.1",
    "area-alt": "1.1.1",
    "area_alt": "1.1.1",
    "area_alt_exists": "1.1.1",
    "object-alt": "1.1.1",
    "object_alt": "1.1.1",
    "input-image-alt": "1.1.1",
    "input_image_alt": "1.1.1",
    "img_alt_valid": "1.1.1",
    "imagemap_alt_exists": "1.1.1",
    "image-alt-text-missing": "1.1.1",
    "image_alt_text_missing": "1.1.1",
    "figure-missing-alt": "1.1.1",
    "figure_missing_alt": "1.1.1",

    # -------------------
    # WCAG 1.3.1 Info and Relationships
    # -------------------
    "aria_navigation_label_unique": "1.3.1",
    "input_label_exists": "1.3.1",
    "input_label_before": "1.3.1",
    "form_label_unique": "1.3.1",
    "aria-required-children": "1.3.1",
    "aria_required_children": "1.3.1",
    "landmark-one-main": "1.3.1",
    "landmark_one_main": "1.3.1",
    "landmark-unique": "1.3.1",
    "landmark_unique": "1.3.1",
    "landmark-no-duplicate-banner": "1.3.1",
    "landmark_no_duplicate_banner": "1.3.1",
    "aria_banner_label_unique": "1.3.1",
    "region": "1.3.1",
    "label": "1.3.1",
    "aria-required-attr": "1.3.1",
    "aria_required_attr": "1.3.1",
    "aria-required-parent": "1.3.1",
    "aria_required_parent": "1.3.1",
    "table-header": "1.3.1",
    "table_header": "1.3.1",
    "scope-attr-valid": "1.3.1",
    "scope_attr_valid": "1.3.1",
    "definition-list": "1.3.1",
    "definition_list": "1.3.1",
    "list": "1.3.1",
    "listitem": "1.3.1",
    "fieldset": "1.3.1",
    "page-has-heading-one": "1.3.1",
    "page_has_heading_one": "1.3.1",
    "input_checkboxes_grouped": "1.3.1",
    "document-not-tagged": "1.3.1",
    "document_not_tagged": "1.3.1",
    "table-has-no-headers": "1.3.1",
    "table_has_no_headers": "1.3.1",
    "table-header-cell-has-no-scope": "1.3.1",
    "table_header_cell_has_no_scope": "1.3.1",
    "table_headers_exists": "1.3.1",
    "text_quoted_correctly": "1.3.1",
    "pdf-layout-with-spaces": "1.3.1",
    "pdf_layout_with_spaces": "1.3.1",

    # -------------------
    # WCAG 1.3.2 Meaningful Sequence
    # -------------------
    "focus-order-semantics": "1.3.2",
    "focus_order_semantics": "1.3.2",
    "#sibling*": "1.3.2",
    "document-reading-order-is-incorrect": "1.3.2",
    "document_reading_order_is_incorrect": "1.3.2",

    # -------------------
    # WCAG 1.3.5 Identify Input Purpose
    # -------------------
    "autocomplete-valid": "1.3.5",
    "autocomplete_valid": "1.3.5",

    # -------------------
    # WCAG 1.4.1 Use of Color
    # -------------------
    "color-only": "1.4.1",
    "color_only": "1.4.1",
    "style_color_misuse": "1.4.1",

    # -------------------
    # WCAG 1.4.3 Contrast (Minimum)
    # -------------------
    "text_contrast_sufficient": "1.4.3",
    "color-contrast": "1.4.3",
    "color_contrast": "1.4.3",
    "contrast": "1.4.3",
    "text-contrast": "1.4.3",
    "text_contrast": "1.4.3",

    # -------------------
    # WCAG 1.4.4 Resize Text
    # -------------------
    "text-resize": "1.4.4",
    "text_resize": "1.4.4",

    # -------------------
    # WCAG 1.4.10 Reflow
    # -------------------
    "meta-viewport": "1.4.10",
    "meta_viewport": "1.4.10",

    # -------------------
    # WCAG 1.4.11 Non-text Contrast
    # -------------------
    "non-text-contrast": "1.4.11",
    "non_text_contrast": "1.4.11",

    # -------------------
    # WCAG 1.4.12 Text Spacing
    # -------------------
    "text_spacing_valid": "1.4.12",
    "avoid-inline-spacing": "1.4.12",
    "avoid_inline_spacing": "1.4.12",

    # -------------------
    # WCAG 2.1.1 Keyboard
    # -------------------
    "keyboard": "2.1.1",
    "keyboard-access": "2.1.1",
    "keyboard_access": "2.1.1",
    "focusable-no-keyboard": "2.1.1",
    "focusable_no_keyboard": "2.1.1",
    "scrollable-region-focusable": "2.1.1",

    # -------------------
    # WCAG 2.1.2 No Keyboard Trap
    # -------------------
    "keyboard-trap": "2.1.2",
    "keyboard_trap": "2.1.2",

    # -------------------
    # WCAG 2.1.3 Keyboard (No Exception)
    # -------------------
    "scrollable-region-focusable": "2.1.3",

    # -------------------
    # WCAG 2.2.1 Timing Adjustable
    # -------------------
    "time-limit": "2.2.1",
    "time_limit": "2.2.1",

    # -------------------
    # WCAG 2.3.1 Three Flashes
    # -------------------
    "flash": "2.3.1",

    # -------------------
    # WCAG 2.4.1 Bypass Blocks
    # -------------------
    "skip_main_exists": "2.4.1",
    "bypass": "2.4.1",
    "skip-link": "2.4.1",
    "skip_link": "2.4.1",
    "frame-title-unique": "2.4.1",
    "frame_title_unique": "2.4.1",
    "html_skipnav_exists": "2.4.1",

    # -------------------
    # WCAG 2.4.2 Page Titled
    # -------------------
    "document-title": "2.4.2",
    "document_title": "2.4.2",
    "page-title": "2.4.2",
    "page_title": "2.4.2",
    "page_title_exists": "2.4.2",
    "document-metadata-is-missing-title-property": "2.4.2",
    "document_metadata_is_missing_title_property": "2.4.2",
    "document-has-no-title": "2.4.2",
    "document_has_no_title": "2.4.2",
    "document-title-is-missing": "2.4.2",
    "document_title_is_missing": "2.4.2",
    "document-title-not-showing-in-window-title-bar": "2.4.2",
    "document_title_not_showing_in_window_title_bar": "2.4.2",

    # -------------------
    # WCAG 2.4.3 Focus Order
    # -------------------
    "focus-order": "2.4.3",
    "focus_order": "2.4.3",
    "document-tab-order-does-not-match-structure": "2.4.3",
    "document_tab_order_does_not_match_structure": "2.4.3",

    # -------------------
    # WCAG 2.4.4 Link Purpose
    # -------------------
    "link-name": "2.4.4",
    "link_name": "2.4.4",
    "link-purpose": "2.4.4",
    "link_purpose": "2.4.4",
    "link-in-text-block": "2.4.4",
    "link_in_text_block": "2.4.4",
    "a_text_purpose": "2.4.4",
    "link-annotation-missing-alt-text": "2.4.4",
    "link_annotation_missing_alt_text": "2.4.4",
    "oobee-accessible-label": "2.4.4",
    "oobee_accessible_label": "2.4.4",

    # -------------------
    # WCAG 2.4.5 Multiple Ways
    # -------------------
    "bookmarks-missing": "2.4.5",
    "bookmarks_missing": "2.4.5",

    # -------------------
    # WCAG 2.4.6 Headings and Labels
    # -------------------
    "heading-order": "2.4.6",
    "heading_order": "2.4.6",
    "heading-levels": "2.4.6",
    "heading_levels": "2.4.6",
    "headings-not-nested-properly": "2.4.6",
    "headings_not_nested_properly": "2.4.6",
    "document-has-no-headings": "2.4.6",
    "document_has_no_headings": "2.4.6",

    # -------------------
    # WCAG 2.4.7 Focus Visible
    # -------------------
    "focus-visible": "2.4.7",
    "focus_visible": "2.4.7",
    "element_tabbable_visible": "2.4.7",

    # -------------------
    # WCAG 2.5.3 Label in Name
    # -------------------
    "label-in-name": "2.5.3",
    "label_in_name": "2.5.3",

    # -------------------
    # WCAG 2.5.8 Target Size (Minimum)
    # -------------------
    "target-size": "2.5.8",
    "target_size": "2.5.8",
    "target_spacing_sufficient": "2.5.8",

    # -------------------
    # WCAG 3.1.1 Language of Page
    # -------------------
    "html-has-lang": "3.1.1",
    "html_has_lang": "3.1.1",
    "html-lang": "3.1.1",
    "html_lang": "3.1.1",
    "html_lang_exists": "3.1.1",
    "document-language-is-not-set": "3.1.1",
    "document_language_is_not_set": "3.1.1",

    # -------------------
    # WCAG 3.2.2 On Input
    # -------------------
    "change-on-input": "3.2.2",
    "change_on_input": "3.2.2",

    # -------------------
    # WCAG 3.3.1 Error Identification
    # -------------------
    "error-message": "3.3.1",
    "error_message": "3.3.1",
    "page-errors": "3.3.1",
    "page_errors": "3.3.1",

    # -------------------
    # WCAG 3.3.2 Labels or Instructions
    # -------------------
    "form-label": "3.3.2",
    "form_label": "3.3.2",
    "form_label_unique": "3.3.2",
    "input-label": "3.3.2",
    "input_label": "3.3.2",
    "label_ref_valid": "3.3.2",
    "form-field-has-no-description": "3.3.2",
    "form_field_has_no_description": "3.3.2",

    # -------------------
    # WCAG 3.3.3 Error Suggestion
    # -------------------
    "error-suggestion": "3.3.3",
    "error_suggestion": "3.3.3",

    # -------------------
    # WCAG 4.1.1 Parsing
    # -------------------
    "duplicate-id": "4.1.1",
    "duplicate_id": "4.1.1",
    "duplicate-id-active": "4.1.1",
    "duplicate_id_active": "4.1.1",
    "aria-id-unique": "4.1.1",
    "aria_id_unique": "4.1.1",
    "file-upload": "4.1.1",
    "file_upload": "4.1.1",

    # -------------------
    # WCAG 4.1.2 Name Role Value
    # -------------------
    "aria_hidden_nontabbable": "4.1.2",
    "aria-valid-attr": "4.1.2",
    "aria_valid_attr": "4.1.2",
    "aria-valid-attr-value": "4.1.2",
    "aria_valid_attr_value": "4.1.2",
    "aria-hidden-nontabbable": "4.1.2",
    "aria-allowed-role": "4.1.2",
    "aria_allowed_role": "4.1.2",
    "aria-role": "4.1.2",
    "aria_role": "4.1.2",
    "aria_eventhandler_role_valid": "4.1.2",
    "frame_title_exists": "4.1.2",
    "select-name": "4.1.2",
    "select_name": "4.1.2",
    "frame-title": "4.1.2",
    "frame_title": "4.1.2",
    "frame-tested": "4.1.2",
    "frame_tested": "4.1.2",
    "button-name": "4.1.2",
    "button_name": "4.1.2",
    "aria-command-name": "4.1.2",
    "aria_command_name": "4.1.2",
    "nested-interactive": "4.1.2",
    "nested_interactive": "4.1.2",
    "form-field-name-missing": "4.1.2",
    "form_field_name_missing": "4.1.2",

    # -------------------
    # WCAG 1.2.x Media (Audio/Video)
    # -------------------
    "video-caption": "1.2.2",
    "video_caption": "1.2.2",
    "caption_track_exists": "1.2.2",
}

def format_rule_label(rule_id: str) -> str:
    """Takes a raw rule ID and returns its mapped WCAG string, if available."""
    return WCAG_RULE_MAP.get(rule_id, rule_id)