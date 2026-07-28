import pytest

from analyzer.services.bi_fields import (
    get_engine_family_meta,
    get_tool_engine,
    summarize_tool_engines,
    get_tool_family,
    summarize_tool_families,
    infer_consensus,
    infer_confidence,
    estimate_issue_rank_score,
    clean_page_name,
    derive_page_group,
    humanize_slug,
    severity_sort_value,
    wcag_level_sort_value,
    issue_scope_sort_value,
    infer_owner_team,
    infer_issue_scope,
    _normalize_page_token,
    canonical_page_key,
    humanize_page_key,
)


# -------------------------
# 🛠️ TOOL & ENGINE CLASSIFICATION
# -------------------------

def test_get_engine_family_meta():
    """Test engine metadata lookups, including defaults[cite: 2]."""
    meta = get_engine_family_meta("axe-core")
    assert meta["label"] == "Axe"
    assert meta["class"] == "engine-axe"

    unknown = get_engine_family_meta("made-up-tool")
    assert unknown["label"] == "Other"
    assert unknown["class"] == "engine-other"

    assert get_engine_family_meta(None)["label"] == "Other"


def test_get_tool_engine_and_family():
    """Test the mapping from specific tools to their broader engines and families[cite: 2]."""
    # Engine mapping
    assert get_tool_engine("lighthouse") == "axe"
    assert get_tool_engine("pa11y-htmlcs") == "htmlcs"
    assert get_tool_engine(None) == "unknown"

    # Family mapping
    assert get_tool_family("axe-scan") == "axe-like"
    assert get_tool_family("ibm-equal-access") == "ibm-like"
    assert get_tool_family("random-linter") == "unknown"


def test_summarize_tools():
    """Test deduplication and sorting of tools into engines and families[cite: 2]."""
    sources = ["axe-core", "lighthouse", "html-sniffer", None]
    
    engines = summarize_tool_engines(sources)
    assert engines == ["axe", "htmlcs"]  # lighthouse & axe-core condense into "axe"

    families = summarize_tool_families(sources)
    assert families == ["axe-like", "htmlcs-like"]


# -------------------------
# 🧠 SCORING & CONSENSUS LOGIC
# -------------------------

def test_infer_consensus():
    """Test the consensus tiers based on tool agreement[cite: 2]."""
    assert infer_consensus(tool_engine_count=3) == "verified"
    assert infer_consensus(tool_engine_count=2) == "likely"
    assert infer_consensus(tool_family_count=2, tool_count=2, tool_engine_count=1) == "likely"
    assert infer_consensus(tool_family_count=1, tool_count=1, tool_engine_count=1) == "single"


def test_infer_confidence():
    """Test the qualitative confidence score generation (High/Medium/Low)[cite: 2]."""
    # High confidence: Cross-engine, multiple pages, critical severity
    high_score = infer_confidence(
        tool_engine_count=3,  # +2.5
        tool_count=4,         # +1.0
        pages=5,              # +1.5
        severity="critical"   # +0.5
    )
    assert high_score == "high"  # 5.5 total >= 5.0

    # Medium confidence
    med_score = infer_confidence(
        tool_engine_count=2,  # +1.5
        instance_count=3,     # +1.0
        rule_id="color-contrast" # +0.5
    )
    assert med_score == "medium" # 3.0 total >= 3.0

    # Low confidence (Single tool, single instance)
    low_score = infer_confidence(
        tool_engine_count=1,  # +0.75
        instance_count=1,     # 0
        pages=1               # 0
    )
    assert low_score == "low" # 0.75 total < 3.0


def test_estimate_issue_rank_score():
    """Test the priority ranking score calculation for BI sorting[cite: 2]."""
    score = estimate_issue_rank_score(
        severity="critical", # 8 * 5 = 40
        pages=5,             # 5 * 3 = 15
        instance_count=10,   # min(10, 20) = 10
        tool_engine_count=3, # +10
        tool_family_count=1, # +0
        tool_count=3,        # (3-1)*2 = +4
        systemic=True        # +8
    )
    assert score == 87 


# -------------------------
# 🏷️ FORMATTING & LOOKUPS
# -------------------------

def test_clean_page_name():
    """Test full URL to readable path extraction[cite: 2]."""
    assert clean_page_name("https://example.com/products/shoes/") == "products/shoes"
    assert clean_page_name("https://example.com/") == "home"
    assert clean_page_name("just_a_string") == "just_a_string"
    assert clean_page_name(None) == "unknown"


def test_derive_page_group():
    """Test top-level directory grouping[cite: 2]."""
    assert derive_page_group("https://example.com/products/shoes/") == "products"
    assert derive_page_group("https://example.com/") == "root"
    assert derive_page_group("dashboard/settings") == "dashboard"


def test_humanize_slug():
    """Test string cleanup into Title Case[cite: 2]."""
    assert humanize_slug("primary_button-component") == "Primary Button Component"
    assert humanize_slug(None) == "Other"


@pytest.mark.parametrize("value, expected", [
    ("critical", 1), ("warning", 5), ("Unknown", 6), (None, 6)
])
def test_severity_sort_value(value, expected):
    """Test severity integer mappings[cite: 2]."""
    assert severity_sort_value(value) == expected


@pytest.mark.parametrize("value, expected", [
    ("AAA", 3), ("A", 1), ("Unknown", 9), (None, 9)
])
def test_wcag_level_sort_value(value, expected):
    """Test WCAG level integer mappings[cite: 2]."""
    assert wcag_level_sort_value(value) == expected


def test_infer_owner_team():
    """Test team assignment based on UI components, handling lists safely[cite: 2]."""
    assert infer_owner_team("form", "button") == "Design System"
    assert infer_owner_team("layout", "header") == "Frontend Platform"
    assert infer_owner_team("document_metadata", "title") == "Content / SEO"
    assert infer_owner_team(None, "unmapped_thing") == "Frontend Platform"
    
    # Test robust unboxing of unexpected list structures
    assert infer_owner_team(["layout"], ["header"]) == "Frontend Platform"


def test_infer_issue_scope():
    """Test determining if an issue is page-specific vs a pattern/system defect[cite: 2]."""
    assert infer_issue_scope(root_cause="Design System - Button") == "Shared component"
    assert infer_issue_scope(systemic=True) == "Shared template/pattern"
    assert infer_issue_scope(pages=4, component="layout") == "Shared template/pattern"
    assert infer_issue_scope(component="image") == "Page-specific"
    assert infer_issue_scope() == "Unknown"


# -------------------------
# 🌐 URL NORMALIZATION
# -------------------------

def test_normalize_page_token():
    """Test sanitization of raw URLs and filenames[cite: 2]."""
    assert _normalize_page_token("some-page.json") == "some_page"
    assert _normalize_page_token("upload_form") == "upload" # via PAGE_ALIAS_MAP
    assert _normalize_page_token("special@chars!") == "special_chars"
    assert _normalize_page_token("///lots//of/slashes/") == "lots/of/slashes"


def test_canonical_page_key():
    """Test URL hierarchy deduplication logic[cite: 2]."""
    # Prefer non-axe artifact URLs
    assert canonical_page_key(
        "rules/axe/button-name.json", 
        "http://example.com/checkout"
    ) == "checkout"

    # Skips data URIs entirely
    assert canonical_page_key("data:image/png;base64,...", "/valid-path") == "valid_path"

    # Defaults to 'unknown'
    assert canonical_page_key(None, "") == "unknown"


def test_humanize_page_key():
    """Test breadcrumb formatting[cite: 2]."""
    assert humanize_page_key("http://example.com/") == "Home"
    assert humanize_page_key("account_settings_billing") == "Account / Settings / Billing"