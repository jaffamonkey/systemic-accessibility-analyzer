import pytest
from unittest.mock import patch

# IMPORTANT: Change "metrics_engine" to the actual module name where your code lives.
from analyzer.services.metrics_engine import (
    is_dynamic_id,
    _is_strict_agreement_candidate,
    _is_balanced_agreement_candidate,
    collapse_agreement_rows_for_chart,
    _agreement_cluster_key,
    collapse_to_agreement_clusters,
    suggest_component,
    suggest_component_from_context,
    get_suggested_components,
    _build_next_best_fixes,
    calculate_metrics
)


# -------------------------
# 🛠️ HELPER & REGEX TESTS
# -------------------------

def test_is_dynamic_id():
    """Test dynamic ID regex matcher[cite: 1]."""
    assert is_dynamic_id("#a1b2c3d4") is True
    assert is_dynamic_id("12345678-abcd") is True
    assert is_dynamic_id("#header") is False
    assert is_dynamic_id(".is-expanded") is False


# -------------------------
# 🤝 AGREEMENT CANDIDATE TESTS
# -------------------------

def test_is_strict_agreement_candidate():
    """Test strict candidate filtering[cite: 1]."""
    # Excluded rule
    assert _is_strict_agreement_candidate({"rule_id": "frame-tested"}) is False
    
    # Excluded result types
    assert _is_strict_agreement_candidate({"result_type": "manual"}) is False
    assert _is_strict_agreement_candidate({"result_type": "warning"}) is False
    
    # Potential violation exceptions
    assert _is_strict_agreement_candidate({"result_type": "potentialviolation", "source": "axe"}) is False
    assert _is_strict_agreement_candidate({"result_type": "potentialviolation", "source": "ibm"}) is True
    
    # Needs review exceptions
    assert _is_strict_agreement_candidate({"needs_review": True, "source": "axe-core"}) is False
    assert _is_strict_agreement_candidate({"needs_review": True, "source": "ibm"}) is True
    
    # Valid candidate
    assert _is_strict_agreement_candidate({"result_type": "violation", "source": "axe-core"}) is True


def test_is_balanced_agreement_candidate():
    """Test balanced candidate filtering[cite: 1]."""
    # Excluded rule
    assert _is_balanced_agreement_candidate({"ruleId": "frame-tested"}) is False
    assert _is_balanced_agreement_candidate({"is_audit_note": True}) is False
    
    # Direct violation
    assert _is_balanced_agreement_candidate({"result_type": "violation"}) is True
    
    # Conditional inclusions
    assert _is_balanced_agreement_candidate({"result_type": "potentialviolation", "source": "axe-scan"}) is True
    assert _is_balanced_agreement_candidate({"result_type": "incomplete", "source": "axe-core"}) is True
    assert _is_balanced_agreement_candidate({"result_type": "warning", "source": "html-sniffer"}) is True
    
    # Conditional exclusions
    assert _is_balanced_agreement_candidate({"result_type": "warning", "source": "axe-core"}) is False


# -------------------------
# 📊 CLUSTERING & CHART TESTS
# -------------------------

def test_collapse_agreement_rows_for_chart():
    """Test deduplication logic for charts[cite: 1]."""
    rows = [
        {"page": "/home", "source": "axe-core", "rule_id": "color-contrast", "target": "div"},
        {"page": "/home", "source": "axe-core", "rule_id": "color-contrast", "target": "div"},  # Duplicate
        {"page": "/home", "source": "pa11y-axe", "rule_id": "alt-text", "target": "img1"},
        {"page": "/home", "source": "pa11y-axe", "rule_id": "alt-text", "target": "img2"},       # pa11y-axe ignores target
    ]
    
    collapsed = collapse_agreement_rows_for_chart(rows)
    
    assert len(collapsed) == 2
    assert collapsed[0]["source"] == "axe-core"
    assert collapsed[1]["source"] == "pa11y-axe"


def test_agreement_cluster_key():
    """Test cluster key generation[cite: 1]."""
    row1 = {"page": "/about", "canonical_rule_id": "color-contrast"}
    assert _agreement_cluster_key(row1) == "/about|color-contrast"
    
    row2 = {"page": None, "wcag": "1.1.1"}
    assert _agreement_cluster_key(row2) == "unknown|1.1.1"


@patch("metrics_engine.get_tool_family")
@patch("metrics_engine.get_tool_engine")
def test_collapse_to_agreement_clusters(mock_get_engine, mock_get_family):
    """Test deep clustering and source aggregations[cite: 1]."""
    mock_get_family.side_effect = lambda x: f"{x}-family"
    mock_get_engine.side_effect = lambda x: f"{x}-engine"

    rows = [
        {"page": "/home", "rule_id": "r1", "source": "axe-core"},
        {"page": "/home", "rule_id": "r1", "source": "html-sniffer"},
    ]
    
    result = collapse_to_agreement_clusters(rows)
    
    assert len(result) == 1
    cluster = result[0]
    assert set(cluster["sources"]) == {"axe-core", "html-sniffer"}
    assert cluster["tool_family_count"] == 2
    assert cluster["tool_engine_count"] == 2


# -------------------------
# 🧠 COMPONENT SUGGESTION TESTS
# -------------------------

def test_suggest_component():
    """Test component suggestions based on DOM strings[cite: 1]."""
    assert suggest_component("#email") == "form_field"
    assert suggest_component(".current") == "navigation"
    assert suggest_component("role=\"dialog\"") == "modal"
    assert suggest_component("button.primary") == "button"
    assert suggest_component("#12345678-abc") is None  # Dynamic ID
    
    # Test learning dictionary override
    with patch.dict(metrics_engine.LEARNING, {"custom-pattern": {"component": "custom_widget"}}):
        assert suggest_component("custom-pattern") == "custom_widget"


def test_suggest_component_from_context():
    """Test rich context-based component suggestions[cite: 1]."""
    assert suggest_component_from_context(rule_id="html-has-lang") == "document_metadata"
    assert suggest_component_from_context(message="content is not contained by landmarks") == "layout"
    assert suggest_component_from_context(rule_id="color-contrast", dom_path="<a href='x'>") == "link"
    assert suggest_component_from_context(message="buttons must have discernible text") == "button"
    assert suggest_component_from_context(dom_path="center table thead") == "table"


@patch("metrics_engine.COMPONENT_GROUPS", {"button": "Form Controls"})
def test_get_suggested_components():
    """Test aggregation of unknown patterns[cite: 1]."""
    mock_unknown = {
        ".btn-custom": 10,
        "#dynamic123456789": 5
    }
    
    with patch.dict(metrics_engine.UNKNOWN_PATTERNS, mock_unknown, clear=True):
        results = get_suggested_components()
        
        assert len(results) == 2
        
        # Checking the highest frequency item first
        assert results[0]["pattern"] == ".btn-custom"
        assert results[0]["suggestion"] == "button"
        assert results[0]["group"] == "Form Controls"
        
        # Fallback to 'other' if no suggestion is found
        assert results[1]["pattern"] == "#dynamic123456789"
        assert results[1]["suggestion"] == "other"


# -------------------------
# 📈 METRICS & FIXES TESTS
# -------------------------

def test_build_next_best_fixes():
    """Test logic to identify systemic 'fix once' patterns[cite: 1]."""
    clusters = [
        {
            "pattern": "btn-primary",
            "component": "button",
            "count": 5,
            "files": ["/a", "/b"],
            "systemic": True,
            "issue_rank_score": 100
        },
        {
            "pattern": "btn-primary",
            "count": 2,
            "files": ["/c"],
            "systemic": True,
            "issue_rank_score": 80
        }
    ]
    
    fixes, summary = _build_next_best_fixes(clusters)
    
    assert len(fixes) == 1
    assert fixes[0]["findings_count"] == 7
    assert fixes[0]["affected_pages_count"] == 3
    assert fixes[0]["is_systemic"] is True
    assert fixes[0]["top_fix_rank"] == 1
    
    assert summary["systemic_fixes"] == 1
    assert summary["pages_impacted_top5"] == 3


@patch("metrics_engine.PROBLEM_TYPE_MAP", {"button": "Actionable"})
@patch("metrics_engine.WCAG_SUCCESS_CRITERIA", {"1.1.1": {"level": "A"}})
def test_calculate_metrics():
    """Test full integration of the dashboard metrics engine[cite: 1]."""
    rows = [
        {"page": "/home", "files": ["/home"], "component": "button", "source": "axe-core", "wcag": "1.1.1"},
        {"page": "/about", "files": ["/about"], "component": "frame", "source": "ibm"}
    ]
    
    clusters = [
        {"pattern": "btn", "count": 5, "files": ["/home", "/about"], "systemic": True, "component": "button", "wcag_level": "AA"},
        {"pattern": "iframe", "count": 1, "files": ["/about"], "systemic": False, "component": "frame"}
    ]
    
    metrics = calculate_metrics(rows, clusters)
    
    assert metrics["violations"] == 2
    assert metrics["pages_count"] == 2
    assert "axe-core" in metrics["source_counts"]
    assert metrics["component_heatmap"]["button"] == 1
    assert metrics["frame_issues"] == 1
    assert metrics["frame_pages"] == 1
    
    # Since cluster 1 has count=5 (systemic=True), and cluster 2 has count=1.
    # systemic_findings = 5. total_findings = 6. 
    # shared_pattern_impact = round(5 / 6 * 100) = 83
    assert metrics["shared_pattern_impact"] == 83
    
    # Assert problem types mapped correctly
    assert metrics["problem_types"]["Actionable"] == 1