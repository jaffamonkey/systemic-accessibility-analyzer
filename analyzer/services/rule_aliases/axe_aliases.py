"""
Axe Aliases
Maps raw axe-core rule IDs to the Systemic Analyzer's Canonical Rules.
"""

AXE_ALIASES = {
    # --- INTERACTIVE & WIDGETS ---
    "button-name": "widget-name",
    "aria-command-name": "widget-name",
    "aria-tooltip-name": "widget-name",
    "focusable-no-name": "widget-name",
    "has-visible-text": "widget-name",
    "label-content-name-mismatch": "widget-name",
    "button-has-visible-text": "widget-name",
    "link-name": "link-name",

    # --- FORMS ---
    "aria-input-field-name": "form-label",
    "select-name": "form-label",
    "label": "form-label",
    "aria-toggle-field-name": "form-label",
    "aria-meter-name": "form-label",
    "aria-progressbar-name": "form-label",
    "input-button-name": "form-label",

    # --- MEDIA ---
    "image-alt": "missing-alt",
    "input-image-alt": "missing-alt",
    "svg-img-alt": "missing-alt",
    "image-redundant-alt": "redundant-alt",

    # --- KEYBOARD & FOCUS ---
    "scrollable-region-focusable": "focus-management",
    "aria-hidden-focus": "focus-management",

    # --- STRUCTURE & SEMANTICS ---
    "region": "landmarks",
    "landmark-one-main": "landmarks",
    "header-present": "landmarks",
    "heading-order": "heading-hierarchy",
    "page-has-heading-one": "heading-hierarchy",
    "empty-heading": "heading-hierarchy",
    "list": "list-structure",
    "listitem": "list-structure",
    "definition-list": "list-structure",
    "dlitem": "list-structure",
    "only-listitems": "list-structure",
    "html-has-lang": "language",
    "html-lang-valid": "language",
    "valid-lang": "language",
    "document-title": "page-title",
    "frame-title": "frame-title",

    # --- VISUAL ---
    "color-contrast": "color-contrast",
    "color-contrast-enhanced": "color-contrast",

    # --- TECHNICAL / ARIA ---
    "duplicate-id": "duplicate-id",
    "duplicate-id-active": "duplicate-id",
    "aria-prohibited-attr": "aria-validity",
    "aria-allowed-role": "aria-validity",
    "aria-allowed-attr": "aria-validity",
    "aria-required-attr": "aria-validity",
    "aria-required-children": "aria-validity",
    "aria-valid-attr-value": "aria-validity",
    "aria-valid-attr": "aria-validity",
}