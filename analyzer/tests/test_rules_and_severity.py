import pytest

# Adjust imports to match your project structure
from rule_formatter import _looks_like_wcag_code, _humanize_rule_id, format_rule_label as format_label_dashboard
from rule_normalizer import normalize_rule as normalize_rule_id
from severity_normalizer import normalize_severity
from wcag_mapper import extract_wcag_from_text, guess_wcag_from_message, ensure_wcag
from wcag_refs import (
    extract_wcag_technique,
    enrich_wcag_rule,
    resolve_rule_wcag,
    resolve_wcag_level,
    slugify_title
)
from rule_aliases import format_rule_label as format_alias_label


# -------------------------
# 🏷️ RULE FORMATTER TESTS
# -------------------------

def test_looks_like_wcag_code():
    """Tests the regex that identifies raw WCAG codes and proprietary HTMLCS strings[cite: 16]."""
    assert _looks_like_wcag_code("1.4.3") is True
    assert _looks_like_wcag_code("1.4.3 [G18]") is True
    assert _looks_like_wcag_code("WCAG2AA.Principle1.Guideline1_4") is True
    assert _looks_like_wcag_code("color-contrast") is False
    assert _looks_like_wcag_code(None) is False


def test_humanize_rule_id():
    """Tests the conversion of technical slugs into Title Case[cite: 16]."""
    assert _humanize_rule_id("color-contrast") == "Color Contrast"
    assert _humanize_rule_id("aria_hidden_nontabbable") == "Aria Hidden Nontabbable"
    assert _humanize_rule_id(None) == ""


def test_format_rule_label_dashboard():
    """Tests the precedence for selecting the best human-readable label[cite: 16]."""
    # 1. Prefers explicit, plain-English rule name[cite: 16]
    cluster1 = {"rule_name": "Check Color Contrast", "ruleId": "color-contrast"}
    assert format_label_dashboard(cluster1) == "Check Color Contrast"
    
    # 2. Falls back to humanized rule ID if rule name is a WCAG code[cite: 16]
    cluster2 = {"rule_name": "1.4.3", "ruleId": "color-contrast"}
    assert format_label_dashboard(cluster2) == "Color Contrast"
    
    # 3. Falls back to WCAG Title[cite: 16]
    cluster3 = {"wcag_title": "Contrast (Minimum)", "wcag": "1.4.3"}
    assert format_label_dashboard(cluster3) == "Contrast (Minimum)"
    
    # 4. Falls back to raw WCAG code[cite: 16]
    cluster4 = {"wcag": "1.4.3"}
    assert format_label_dashboard(cluster4) == "1.4.3"
    
    # 5. Last resort fallback[cite: 16]
    assert format_label_dashboard({}) == "Unknown"


# -------------------------
# 🧹 RULE NORMALIZER TESTS
# -------------------------

def test_normalize_rule_id():
    """Tests extraction of WCAG strings and hardcoded fallbacks from messy IDs[cite: 17]."""
    # Extracts dot-notation[cite: 17]
    assert normalize_rule_id("wcag1.4.3") == "1.4.3"
    
    # Extracts underscore-notation[cite: 17]
    assert normalize_rule_id("rule_1_3_1_error") == "1.3.1"
    
    # Hardcoded Axe-core fallbacks[cite: 17]
    assert normalize_rule_id("check-color-contrast") == "1.4.3"
    assert normalize_rule_id("aria-hidden-element") == "4.1.2"
    
    assert normalize_rule_id("unrecognized-rule") == "unrecognized-rule"
    assert normalize_rule_id(None) is None


# -------------------------
# 🚦 SEVERITY NORMALIZER TESTS
# -------------------------

@pytest.mark.parametrize("raw, expected", [
    ("critical", "critical"),  # Axe baseline[cite: 18]
    ("violation", "serious"),  # IBM Equal Access[cite: 18]
    ("error", "serious"),      # HTMLCS / Lighthouse[cite: 18]
    ("warning", "warning"),    # Shared warning mapping[cite: 18]
    ("notice", None),          # Ignored HTMLCS noise[cite: 18]
    ("unknown-level", "minor"), # Default fallback[cite: 18]
    (None, "minor"),           # Null fallback[cite: 18]
])
def test_normalize_severity(raw, expected):
    """Tests standardization of incoming severity ratings to a canonical scale[cite: 18]."""
    assert normalize_severity(raw) == expected


# -------------------------
# 🧠 WCAG MAPPER & FALLBACK TESTS
# -------------------------

def test_extract_wcag_from_text():
    """Tests regex scraping of standard WCAG IDs from text blocks[cite: 19]."""
    assert extract_wcag_from_text("This fails WCAG 2.4.4 Link Purpose") == "2.4.4"
    assert extract_wcag_from_text("No wcag code here") is None


def test_guess_wcag_from_message():
    """Tests heuristic keyword matching against tool error messages[cite: 19]."""
    assert guess_wcag_from_message("text spacing must be adjustable") == "1.4.12"
    assert guess_wcag_from_message("image is missing alt text") == "1.1.1"
    assert guess_wcag_from_message("document language is not set") == "3.1.1"
    assert guess_wcag_from_message("completely unknown message") is None


def test_ensure_wcag():
    """Tests the main resolution pipeline for determining a WCAG criteria[cite: 19]."""
    # 1. Exact mapping (hypothetical alias mapped to 1.3.1)[cite: 19]
    assert ensure_wcag({"ruleId": "input_checkboxes_grouped"}) == "1.3.1"
    
    # 3. Regex extraction from the rule string[cite: 19]
    assert ensure_wcag({"ruleId": "error_2.4.1_bypass"}) == "2.4.1"
    
    # 4. Heuristic fallback based on concatenated fields[cite: 19]
    row_heuristic = {
        "ruleId": "unknown", 
        "message": "color is not used as the only visual means"
    }
    assert ensure_wcag(row_heuristic) == "1.4.1"
    
    # 5. Final pass using standard string extractors[cite: 19]
    row_fallback = {"description": "Make sure reading order is correct."}
    assert ensure_wcag(row_fallback) == "1.3.2"


# -------------------------
# 📚 WCAG REFS TAXONOMY TESTS
# -------------------------

def test_extract_wcag_technique():
    """Tests extraction of technique tags from HTMLCS strings[cite: 20]."""
    assert extract_wcag_technique("1.4.3 [G18]") == "G18"
    assert extract_wcag_technique("Just a rule") is None


def test_enrich_wcag_rule():
    """Tests combining base WCAG rules with official titles and techniques[cite: 20]."""
    # Enriches with title and technique description[cite: 20, 22]
    enriched = enrich_wcag_rule("1.4.3 [G18]")
    assert "1.4.3" in enriched
    assert "Contrast (Minimum)" in enriched
    assert "Contrast ratio at least 4.5:1" in enriched
    
    # Enriches with just title if no technique is provided[cite: 20]
    assert enrich_wcag_rule("2.4.1") == "2.4.1" # Only runs if it matches the bracket regex


def test_resolve_wcag_level():
    """Tests level lookup in the master taxonomy[cite: 20]."""
    assert resolve_wcag_level("1.1.1") == "A"
    assert resolve_wcag_level("1.4.3") == "AA"
    assert resolve_wcag_level("invalid") is None


def test_slugify_title():
    """Tests string cleaning for IDs/CSS class names[cite: 20]."""
    assert slugify_title("Contrast (Minimum)") == "contrast-minimum"
    assert slugify_title("Audio-only (Live)") == "audio-only-live"


# -------------------------
# 🔗 RULE ALIASES TESTS
# -------------------------

def test_format_alias_label():
    """Tests mapping from tool-specific rule slugs to standard WCAG reference codes[cite: 21]."""
    assert format_alias_label("image-alt-text-missing") == "1.1.1"
    assert format_alias_label("color_contrast") == "1.4.3"
    assert format_alias_label("scrollable-region-focusable") == "2.1.1" # First match in dict[cite: 21]
    
    # Returns original string if not in the map[cite: 21]
    assert format_alias_label("unknown_custom_rule") == "unknown_custom_rule"