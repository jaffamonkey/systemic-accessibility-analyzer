import pytest
from unittest.mock import patch, mock_open

# Adjust these imports to match your project's directory structure
from analyzer.analyzer.utils import clean_dynamic_selectors, simplify_pattern
from analyzer.analyzer.component_learning import is_noisy_pattern, auto_guess, update_learning, UNKNOWN_PATTERNS
from analyzer.analyzer.component_detector import (
    get_emerging_patterns,
    detect_design_system,
    parse_pattern,
    detect_component,
    detect_root_cause,
    detect_design_system_issue,
)
from fingerprint_generator import _coerce_value, build_fingerprint
from violation_key_generator import (
    normalize,
    _coerce_selector_value,
    build_selector_signature,
    build_violation_key,
)


# -------------------------
# 🛠️ ANALYZER UTILITIES TESTS
# -------------------------

def test_clean_dynamic_selectors():
    """Test that dynamic noise is stripped from selectors[cite: 8]."""
    # Strips trailing numbers from dynamically generated IDs[cite: 8]
    assert clean_dynamic_selectors("#button-12345") == "#button-"
    
    # Catches 32-character hex hashes (Alfa artifacts)[cite: 8]
    alfa_hash = "a" * 32
    assert clean_dynamic_selectors(alfa_hash) == "alfa-opaque-node-hash"
    
    assert clean_dynamic_selectors(None) == ""


def test_simplify_pattern():
    """Test reduction of complex DOM selector payloads[cite: 8]."""
    # Normalizes lists into a flat string[cite: 8]
    assert simplify_pattern(["div", "span"]) == "div span"
    
    # Normalizes dictionaries by checking specific keys like 'selector' or 'target'[cite: 8]
    assert simplify_pattern({"selector": ".btn"}) == ".btn"
    assert simplify_pattern([{"xpath": "//div"}, {"target": "#main"}]) == "//div #main"
    
    # Removes fragile nth-child and nth-of-type noise[cite: 8]
    assert simplify_pattern("ul li:nth-child(3) a:nth-of-type(1)") == "ul li a"
    
    # Collapses whitespace[cite: 8]
    assert simplify_pattern("div    span") == "div span"
    assert simplify_pattern(None) == "unknown"


# -------------------------
# 🧠 COMPONENT LEARNING TESTS
# -------------------------

def test_is_noisy_pattern():
    """Test filtering of junk patterns before they enter the learning engine[cite: 5]."""
    # Blocks 32-character hex hashes[cite: 5]
    assert is_noisy_pattern("a1b2c3d4e5f67890123456789abcdef0") is True
    
    # Blocks raw HTML snippets[cite: 5]
    assert is_noisy_pattern("<div class=\"test\">") is True
    
    # Blocks tracking scripts and alfa opaque nodes[cite: 5]
    assert is_noisy_pattern("google-analytics-script") is True
    assert is_noisy_pattern("alfa-opaque-node-hash") is True
    
    # Blocks long dynamic number sequences[cite: 5]
    assert is_noisy_pattern("item-12345678") is True
    
    # Allows valid patterns[cite: 5]
    assert is_noisy_pattern("nav-ul-li-a") is False


def test_auto_guess():
    """Test heuristic fallback for classifying high-frequency unknown patterns[cite: 5]."""
    assert auto_guess("col-md-6") == "grid"
    assert auto_guess("main-nav-item") == "navigation"
    assert auto_guess("primary-btn") == "button"
    assert auto_guess("login-form") == "form"
    assert auto_guess("page-title") == "text"
    assert auto_guess("random-div") == "other"


@patch("analyzer.component_learning.LEARNING", {})
def test_update_learning():
    """Test tracking frequency and auto-guessing when threshold is met[cite: 5]."""
    UNKNOWN_PATTERNS.clear()
    
    # Bypasses 'frame' and empty patterns[cite: 5]
    update_learning("frame")
    assert "frame" not in UNKNOWN_PATTERNS
    
    # Updates count for valid unknown patterns[cite: 5]
    for _ in range(19):
        update_learning("custom-submit-btn")
        
    from analyzer.analyzer.component_learning import LEARNING
    assert LEARNING["custom-submit-btn"]["count"] == 19
    assert LEARNING["custom-submit-btn"]["component"] is None
    
    # Hits the threshold of 20 and triggers auto_guess[cite: 5]
    update_learning("custom-submit-btn")
    assert LEARNING["custom-submit-btn"]["count"] == 20
    assert LEARNING["custom-submit-btn"]["component"] == "button"
    assert LEARNING["custom-submit-btn"]["confidence"] == 0.7


# -------------------------
# 🕵️ COMPONENT DETECTOR TESTS
# -------------------------

@patch("analyzer.component_detector.load_learning")
def test_get_emerging_patterns(mock_load):
    """Test scanning local learning files for high-frequency unclassified patterns[cite: 4]."""
    mock_load.return_value = {
        "pattern1": {"count": 10, "component": None},
        "pattern2": {"count": 2, "component": None},  # Below threshold of 5[cite: 4]
        "pattern3": {"count": 25, "component": None},
    }
    
    results = get_emerging_patterns()
    assert len(results) == 2
    # Sorted by count descending[cite: 4]
    assert results[0]["pattern"] == "pattern3"
    assert results[1]["pattern"] == "pattern1"


def test_detect_design_system():
    """Test checking if a pattern belongs to core design system categories[cite: 4]."""
    # Tests exact word boundary matches[cite: 4]
    assert detect_design_system("alert") == "feedback"
    assert detect_design_system("alerting") is None
    
    # Tests prefix matches[cite: 4]
    assert detect_design_system("btn-primary") == "interactive"
    assert detect_design_system("navbar-top") == "navigation"


def test_parse_pattern():
    """Test breaking CSS patterns into hierarchy parts[cite: 4]."""
    assert parse_pattern("nav-ul-li-a") == ["nav", "ul", "li", "a"]
    assert parse_pattern("") == []


@patch("analyzer.component_detector.LEARNING", {"known-modal": {"component": "modal"}})
def test_detect_component():
    """Test the primary waterfall pipeline for identifying UI components[cite: 4]."""
    # 3. The Bouncer: Catches tracking scripts[cite: 4]
    assert detect_component("alfa-opaque-node-hash") == "third_party"
    
    # 4. Priority: Last Element[cite: 4]
    assert detect_component("div-span-a") == "link"
    assert detect_component("form-input") == "form"
    
    # 5. Context-Aware Boost[cite: 4]
    assert detect_component("nav-div-span") == "navigation"
    
    # 6. Machine Learning Override[cite: 4]
    assert detect_component("known-modal") == "modal"
    
    # 8. Fallback[cite: 4]
    assert detect_component("div") == "layout"
    assert detect_component("unknown-tag") == "other"


def test_detect_root_cause():
    """Test human-readable explanations for systemic issues[cite: 4]."""
    assert detect_root_cause("color-contrast", "text", "low contrast") == "Design system color palette or theme tokens"
    assert detect_root_cause("button-name", "Buttons", "missing text") == "Shared button component implementation"
    assert detect_root_cause("aria-hidden", "other", "bad aria") == "ARIA attributes incorrectly implemented in component"


def test_detect_design_system_issue():
    """Test evaluating clusters for systemic fixes at the Design System level[cite: 4]."""
    assert detect_design_system_issue({"wcag": "1.4.3"}) == "Design system color palette or theme tokens"
    assert detect_design_system_issue({"ruleId": "button-name"}) == "Design system button component"
    assert detect_design_system_issue({"component": "tables"}) == "Design system table component"
    assert detect_design_system_issue({"component": "image"}) is None


# -------------------------
# 🧬 FINGERPRINT GENERATOR TESTS
# -------------------------

def test_coerce_value():
    """Test safe extraction of strings from mixed-type payloads[cite: 7]."""
    assert _coerce_value(None) == ""
    assert _coerce_value(" .btn ") == ".btn"
    assert _coerce_value([{"xpath": "//a"}, {"target": "#link"}]) == "//a #link"
    assert _coerce_value({"css": ".header"}) == ".header"


@patch("fingerprint_generator.detect_component", return_value="button")
def test_build_fingerprint(mock_detect):
    """Test normalization and stripping of dynamic elements for fingerprints[cite: 7]."""
    # Blank DOMs generate a generic document metadata fingerprint[cite: 7]
    assert build_fingerprint("", "", rule_id="html-lang") == "document_metadata::html-lang"
    
    # Strips nth-child and layout wrappers (div, span, section)[cite: 7]
    dom = "body > div > section > ul:nth-child(2) > li > button"
    selector = "button:nth-child(1)"
    
    fingerprint = build_fingerprint(dom, selector)
    
    # Keeps only the last 3 meaningful nodes (body, ul, li, button -> ul/li/button)[cite: 7]
    # Replaces nth-child digits with a wildcard (*)[cite: 7]
    assert fingerprint == "button::ul/li/button|button:nth-child(*)"


# -------------------------
# 🔑 VIOLATION KEY GENERATOR TESTS
# -------------------------

def test_violation_normalize():
    """Test string lowering and stripping for key generation[cite: 9]."""
    assert normalize("  Color-Contrast  ") == "color-contrast"
    assert normalize(None) == ""


def test_coerce_selector_value():
    """Test flat string extraction for selector payloads[cite: 9]."""
    assert _coerce_selector_value([{"selector": ".card"}, ".title"]) == ".card .title"
    assert _coerce_selector_value({"dom": "#main"}) == "#main"


def test_build_selector_signature():
    """Test distilling CSS down to core tags, classes, and IDs[cite: 9]."""
    # Removes pseudo-classes and limits to 2 classes and 1 ID[cite: 9]
    complex_css = "button.btn.btn-primary.large-btn#submit-btn#extra-id:nth-child(3)"
    signature = build_selector_signature(complex_css)
    
    # Sorts classes alphabetically, taking the first two, and the first ID[cite: 9]
    assert signature == "button btn btn-primary submit-btn"


def test_build_violation_key():
    """Test construction of the master grouping key for identical issues[cite: 9]."""
    row = {
        "page": "/home",
        "ruleId": "color-contrast",
        "selector": "a.link",
    }
    
    key = build_violation_key(row)
    # Merges page context, canonical rule, and CSS signature[cite: 9]
    assert key == "/home|color-contrast|a link"
    
    # Skips weak selectors (like 'div' or '*')[cite: 9]
    row_weak = {
        "url": "/about",
        "wcag": "1.1.1",
        "target": "div"
    }
    assert build_violation_key(row_weak) == "/about|1.1.1"

    # Falls back to error message if no rule is provided[cite: 9]
    row_no_rule = {
        "file": "/contact",
        "message": "Missing alt text",
        "dom": "img"
    }
    assert build_violation_key(row_no_rule) == "/contact||img|missing alt text"