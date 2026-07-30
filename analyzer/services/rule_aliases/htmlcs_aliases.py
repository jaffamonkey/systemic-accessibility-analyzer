"""
HTMLCS Aliases
Maps raw HTML_CodeSniffer rule strings to the Canonical Rules.
"""

HTMLCS_ALIASES = {
    # Normalised mappings
    "htmlcs-1_1_1-h37": "missing-alt",
    "htmlcs-h37": "missing-alt",
    "htmlcs-1_3_1-h42": "heading-hierarchy",
    "htmlcs-h42": "heading-hierarchy",
    "htmlcs-1_3_1-h43": "table-header",
    "htmlcs-h43": "table-header",
    "htmlcs-1_3_1-h63": "table-header",
    "htmlcs-h63": "table-header",
    "htmlcs-1_4_3-g18": "color-contrast",
    "htmlcs-g18": "color-contrast",
    "htmlcs-1_4_6-g17": "color-contrast-enhanced",
    "htmlcs-g17": "color-contrast-enhanced",
    "htmlcs-2_4_1-h64": "frame-title",
    "htmlcs-h64": "frame-title",
    "htmlcs-2_4_2-h25": "page-title",
    "htmlcs-h25": "page-title",
    "htmlcs-3_3_2-h44": "form-label",
    "htmlcs-h44": "form-label",
    "htmlcs-4_1_2-h91": "widget-name",
    "htmlcs-h91": "widget-name",

    # Raw HTMLCS output intercepts
    "wcag2aa.principle1.guideline1_4.1_4_3.g18.fail": "color-contrast",
    "wcag2aaa.principle1.guideline1_4.1_4_6.g17.fail": "color-contrast-enhanced",
    "wcag2aa.principle1.guideline1_4.1_4_3.g18.bgimage": "color-contrast-review",
    "wcag2aaa.principle1.guideline1_4.1_4_6.g17.bgimage": "color-contrast-review",
    "wcag2aa.principle1.guideline1_4.1_4_3.g145.bgimage": "color-contrast-review",
    "wcag2aaa.principle1.guideline1_4.1_4_6.g145.bgimage": "color-contrast-review",
    "wcag2aa.principle1.guideline1_4.1_4_3_f24.f24.fgcolour": "color-contrast-review",
    "wcag2aaa.principle1.guideline1_4.1_4_3_f24.f24.fgcolour": "color-contrast-review",
    "wcag2aaa.principle1.guideline1_4.1_4_6.g17.abs": "color-contrast-enhanced",
    "wcag2aa.principle1.guideline1_4.1_4_3.g18.abs": "color-contrast",
    "wcag2aa.principle1.guideline1_4.1_4_3.g18.alpha": "color-contrast-review",
    "wcag2aaa.principle1.guideline1_4.1_4_3_f24.f24.bgcolour": "color-contrast-review",
    "wcag2aa.principle1.guideline1_4.1_4_3_f24.f24.bgcolour": "color-contrast-review",
    
    # Uppercase fallbacks for Pa11y
    "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail": "color-contrast",
    "WCAG2AA.Principle1.Guideline1_4.1_4_3.G145.Fail": "color-contrast",
    "WCAG2AAA.Principle1.Guideline1_4.1_4_6.G17.Fail": "color-contrast-enhanced",

    # Reflow / fixed positioning warnings
    "wcag2aa.principle1.guideline1_4.1_4_10.c32,c31,c33,c38,scr34,g206": "reflow",
    "wcag2aaa.principle1.guideline1_4.1_4_10.c32,c31,c33,c38,scr34,g206": "reflow",

    # Name / purpose / labels
    "wcag2aa.principle4.guideline4_1.4_1_2.h91.a.nocontent": "link-name",
    "wcag2aaa.principle4.guideline4_1.4_1_2.h91.a.nocontent": "link-name",
    "wcag2aa.principle4.guideline4_1.4_1_2.h91.a.placeholder": "link-name",
    "wcag2aaa.principle4.guideline4_1.4_1_2.h91.a.placeholder": "link-name",
    "wcag2aa.principle4.guideline4_1.4_1_2.h91.inputtext.name": "form-label",
    "wcag2aaa.principle4.guideline4_1.4_1_2.h91.inputtext.name": "form-label",
    "wcag2aa.principle1.guideline1_1.1_1_1.h37": "missing-alt",
    "wcag2aaa.principle4.guideline4_1.4_1_2.h91.select.value": "form-label",

    "wcag2aaa.principle1.guideline1_1.1_1_1.h67.2": "decorative-image",
    "wcag2aaa.principle1.guideline1_3.1_3_1.h85.2": "form-structure",
    "wcag2aaa.principle1.guideline1_3.1_3_1.h48": "list-structure",
    "wcag2aaa.principle1.guideline1_3.1_3_1.h71.samename": "fieldset-legend",
    "wcag2aaa.principle2.guideline2_4.2_4_1.g1,g123,g124.nosuchid": "bypass-blocks",

    "invalidrole": "aria-validity",
    "deprecatedrole": "aria-validity",
    "unsupportedrole": "aria-validity",
    "abstractrole": "aria-validity",
}