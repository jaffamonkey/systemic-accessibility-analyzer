"""
IBM Aliases
Maps raw IBM Accessibility Checker rule IDs to the Systemic Analyzer's Canonical Rules.
"""

IBM_ALIASES = {
    # --- Contrast & Color ---
    "text_contrast_sufficient": "color-contrast",
    "style_color_misuse": "use-of-color",

    # --- Forms, Names & Labels ---
    "input_label_exists": "input-name",
    "input_label_visible": "input-name",
    "aria_form_label_unique": "input-name",
    "input_checkboxes_grouped": "input-name",
    "a_text_purpose": "link-name",
    "form_submit_button_exists": "form-submit",

    # --- Images & Media ---
    "img_alt_valid": "image-alt",
    "area_alt_exists": "image-alt",
    "imagemap_alt_exists": "image-alt",
    "img_alt_redundant": "redundant-alt",
    "svg_graphics_labelled": "image-alt",
    "frame_title_exists": "frame-title",

    # --- Tables, Headings & Page Structure ---
    "table_headers_exists": "table-header",
    "text_block_heading": "heading",
    "html_lang_exists": "language",
    "html_lang_valid": "language",
    "page_title_exists": "page-title",

    # --- Landmarks & Bypass Blocks ---
    "skip_main_exists": "skip-link",
    "html_skipnav_exists": "skip-link",
    "aria_content_in_landmark": "region",
    "aria_complementary_labelled": "landmark",
    "aria_landmark_name_unique": "landmark",

    # --- ARIA & Technical ---
    "aria_descendant_valid": "aria-role",
    "element_tabbable_role_valid": "aria-role",
    "aria_role_valid": "aria-role",
    "aria_required_parent": "aria-role",
    "aria_required_children": "aria-role",
    "aria_attribute_valid": "aria-validity",

    # --- Keyboard & Focus ---
    "aria_hidden_nontabbable": "aria-hidden-focusable",
    "aria-hidden-focusable": "keyboard",
    "element_tabbable_visible": "focus-visible",
    "element_tabbable_unobscured": "element-tabbable-unobscured",
    "widget_tabbable_single": "widget-tabbable-single",
    "style_focus_visible": "style-focus-visible",

    # --- Validation, IDs & Spacing ---
    "element_id_unique": "duplicate-id",
    "aria_id_unique": "duplicate-id",
    "target_spacing_sufficient": "target-spacing",
    "text_sensory_misuse": "text-sensory-misuse",

    # --- Advisory / Review ---
    "hidden-content": "hidden-content",
}