import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Adjust imports to match your project structure
from analyzer.services.component_mapper import normalize_component
from analyzer.services.design_system import detect_design_system_issue as ds_detect
from analyzer.services.cluster_engine import build_clusters
from analyzer.services.deduplicate_engine import (
    is_proximity_match,
    normalize_page,
    _coerce_selector_value as dedup_coerce_selector,
    normalize_selector,
    deduplicate_rows,
)
from analyzer.services.processing_engine import (
    _slugify_rule_text,
    _canonicalize_htmlsniffer_rule,
    _canonicalize_rule_id,
    _extract_href_token,
    _extract_id_token,
    _strip_positional_noise,
    _extract_tag_token,
    _normalize_htmlcs_context,
    _build_normalized_target_key,
    process_rows,
)
from analyzer.services.report_loader import (
    normalize_rule,
    _enrich_known_wcag_rules,
    _extract_page_candidate_from_data,
    inspect_report_inventory,
)


# -------------------------
# 🧱 COMPONENT MAPPER TESTS
# -------------------------

def test_normalize_component():
    """Tests mapping of loose DOM strings to canonical taxonomy[cite: 11]."""
    # Matches known taxonomy keywords[cite: 11]
    assert normalize_component("btn-primary") == "button"
    assert normalize_component("main-nav") == "navigation"
    assert normalize_component("data-grid") == "table"
    
    # Falls back to the original string or 'other' if no match[cite: 11]
    assert normalize_component("random-widget") == "random-widget"
    assert normalize_component(None) == "other"
    assert normalize_component("") == "other"


# -------------------------
# 🎨 DESIGN SYSTEM ANALYZER TESTS
# -------------------------

def test_detect_design_system_issue():
    """Tests the translation of clusters into root causes[cite: 13]."""
    # Color / Theming root causes[cite: 13]
    assert ds_detect({"wcag": "1.4.3"}) == "Design system color palette or theme tokens"
    assert ds_detect({"ruleId": "color-contrast"}) == "Design system color palette or theme tokens"
    
    # Specific UI Component root causes[cite: 13]
    assert ds_detect({"component": "buttons"}) == "Design system button component"
    assert ds_detect({"component": "forms"}) == "Design system form field component"
    assert ds_detect({"ruleId": "label-missing"}) == "Design system form field component"
    assert ds_detect({"component": "navigation"}) == "Design system navigation component"
    assert ds_detect({"component": "table"}) == "Design system table component"
    
    # Page-specific fallback[cite: 13]
    assert ds_detect({"component": "image", "ruleId": "alt-text"}) is None


# -------------------------
# 🗃️ CLUSTER ENGINE TESTS
# -------------------------

@patch("cluster_engine.estimate_issue_rank_score", return_value=99)
@patch("cluster_engine.detect_component", return_value="button")
@patch("cluster_engine.build_fingerprint", return_value="btn-fingerprint")
def test_build_clusters(mock_fingerprint, mock_detect, mock_score):
    """Tests aggregation of individual accessibility violations into systemic clusters[cite: 10]."""
    rows = [
        {"ruleId": "color-contrast", "page": "/home", "source": "axe", "component": "button"},
        {"ruleId": "color-contrast", "page": "/about", "source": "htmlcs", "component": "button"},
        {"ruleId": "color-contrast", "page": "/contact", "source": "axe", "component": "button"}
    ]
    
    clusters = build_clusters(rows)
    
    # Should group into exactly 1 cluster based on rule and fingerprint[cite: 10]
    assert len(clusters) == 1
    cluster = clusters[0]
    
    # Calculates systemic impact and enriches with BI fields[cite: 10]
    assert cluster["count"] == 3
    assert cluster["pages"] == 3
    assert cluster["systemic"] is True  # pages >= 3 and count >= 2[cite: 10]
    assert cluster["tool_count"] == 2   # axe and htmlcs[cite: 10]
    assert cluster["issue_rank_score"] == 99


# -------------------------
# 🧩 DEDUPLICATE ENGINE TESTS
# -------------------------

def test_is_proximity_match():
    """Tests fuzzy matching logic for DOM nodes[cite: 12]."""
    # 1. Exact Fingerprint Match[cite: 12]
    assert is_proximity_match({"fingerprint": "fp1"}, {"fingerprint": "fp1"}) is True
    
    # 2. Shared Exact ID[cite: 12]
    row_id = {"selector": "#submit-btn"}
    cluster_id = {"pattern": "button#submit-btn"}
    assert is_proximity_match(row_id, cluster_id) is True
    
    # 3. Robust Substring Match (Selectors length > 8)[cite: 12]
    row_sub = {"selector": "nav > ul > li > a.menu-item"}
    cluster_sub = {"pattern": "a.menu-item"}
    assert is_proximity_match(row_sub, cluster_sub) is True
    
    # 4. Robust Substring Match (DOM snippets length > 15)[cite: 12]
    row_dom = {"dom": "<div class='container'><p>Hello World</p></div>"}
    cluster_dom = {"dom": "<p>Hello World</p>"}
    assert is_proximity_match(row_dom, cluster_dom) is True


def test_normalize_page():
    """Tests stripping file extensions and tool suffixes from URLs[cite: 12]."""
    assert normalize_page({"page": "index.json"}) == "index"
    assert normalize_page({"file": "checkout_axe"}) == "checkout"
    assert normalize_page({}) == "unknown"


# -------------------------
# ⚙️ PROCESSING ENGINE TESTS
# -------------------------

def test_slugify_rule_text():
    """Tests conversion of text into safe kebab-case slugs[cite: 14]."""
    assert _slugify_rule_text("Color Contrast Warning!") == "color-contrast-warning"
    assert _slugify_rule_text(None) is None


def test_canonicalize_htmlsniffer_rule():
    """Tests extraction of WCAG criteria and technique from HTMLCS strings[cite: 14]."""
    assert _canonicalize_htmlsniffer_rule("WCAG2AA.Principle1.Guideline1_4.1_4_3.G18") == "htmlcs-1_4_3-g18"
    assert _canonicalize_htmlsniffer_rule("WCAG2AA.Principle4.4_1_2") == "htmlcs-4_1_2"


def test_token_extractors():
    """Tests DOM parsing extractors for normalized target keys[cite: 14]."""
    # Href extraction[cite: 14]
    assert _extract_href_token("<a href='/home'>") == "href=/home"
    
    # ID extraction (handles both CSS selectors and HTML attributes)[cite: 14]
    assert _extract_id_token("#main-content") == "id=main-content"
    assert _extract_id_token("<div id='nav'>") == "id=nav"
    
    # Tag extraction[cite: 14]
    assert _extract_tag_token("<button class='btn'>") == "tag=button"


def test_normalize_htmlcs_context():
    """Tests stripping of noisy HTMLCS output[cite: 14]."""
    noisy_html = "<div style='color: red;' data-tracking='123' class='a'*45>content</div>"
    clean_html = _normalize_htmlcs_context(noisy_html)
    assert "style=" not in clean_html
    assert "data-tracking=" not in clean_html


# -------------------------
# 📦 REPORT LOADER TESTS
# -------------------------

def test_normalize_rule():
    """Tests cleanup of proprietary rule IDs into standard WCAG references[cite: 15]."""
    # Extracts WCAG and technique[cite: 15]
    assert normalize_rule("1_4_3.G18") == "1.4.3 [G18]"
    # Hardcoded ColorContrast mapping[cite: 15]
    assert normalize_rule("ColorContrast") == "1.4.3"
    assert normalize_rule("image-alt") == "image-alt"


def test_enrich_known_wcag_rules():
    """Tests fallback WCAG mappings for specific proprietary rule IDs[cite: 15]."""
    row = {"ruleId": "css-orientation-lock"}
    enriched = _enrich_known_wcag_rules(row)
    assert enriched["wcag"] == "1.3.4"
    assert enriched["wcag_level"] == "AA"


def test_extract_page_candidate_from_data():
    """Tests recursive extraction of URLs from unknown JSON shapes[cite: 15]."""
    data = {
        "metadata": {
            "page_url": "https://example.com/login"
        }
    }
    # Matches 'page_url' key and extracts 'login'[cite: 15]
    assert _extract_page_candidate_from_data(data) == "login"


@patch("report_loader._resolve_reports_root")
def test_inspect_report_inventory_missing_pages(mock_resolve):
    """Tests diagnostic tool flagging silent failures between tools[cite: 15]."""
    # Mocking two tools where 'axe' found 2 pages, but 'htmlcs' only found 1
    mock_base = Path("/fake/dir")
    mock_axe = MagicMock(name="axe")
    mock_axe.name = "axe"
    mock_axe.glob.return_value = [Path("page1.json"), Path("page2.json")]
    
    mock_htmlcs = MagicMock(name="htmlcs")
    mock_htmlcs.name = "htmlcs"
    mock_htmlcs.glob.return_value = [Path("page1.json")]
    
    mock_resolve.return_value = (mock_base, [mock_axe, mock_htmlcs])
    
    # Mock json reading inside the glob loop
    with patch("builtins.open", MagicMock()), patch("json.load", return_value={}):
        inventory = inspect_report_inventory("/fake/dir")
        
        assert inventory["tools_count"] == 2
        assert inventory["total_distinct_pages"] == 2
        # Detects that page2 is missing from htmlcs[cite: 15]
        assert inventory["mismatched_pages"] == 1
        assert inventory["complete"] is False
        assert inventory["status"] == "warning"