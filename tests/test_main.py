import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# IMPORTANT: Change "main" to the actual name of your Python file if it isn't main.py
from analyzer.app.main import app

client = TestClient(app)

# -------------------------
# 🛠️ FIXTURES
# -------------------------

@pytest.fixture
def mock_metrics():
    """Returns a dummy metrics dictionary to prevent KeyError in _build_api_payload"""
    return {
        "pages": ["/home", "/about"],
        "pages_count": 2,
        "shared_pattern_impact": 15,
        "design_system_impact": 5,
        "accessibility_debt_index": 85,
        "component_heatmap": {},
        "design_heatmap": {},
        "source_counts": {},
        "wcag_levels": {},
        "accessibility_opportunity_score": 90,
        "confidence_counts": {},
        "issuesperpage": {},
        "consensus_counts": {},
        "component_risk": {},
        "top_fixes": []
    }

@pytest.fixture
def mock_rows():
    """Returns dummy row data to bypass the 400 'No violations found' error"""
    return [
        {
            "page": "/home",
            "ruleId": "color-contrast",
            "component": "button",
            "severity": "high"
        }
    ]


# -------------------------
# 🧠 CORE ANALYSIS TESTS
# -------------------------

@patch("main.inspect_report_inventory")
@patch("main.load_reports")
@patch("main.process_rows")
@patch("main.build_clusters")
@patch("main.calculate_metrics")
@patch("main.get_suggested_components")
@patch("main.get_emerging_patterns")
def test_analyze_success(
    mock_patterns, mock_components, mock_calc_metrics, 
    mock_build_clusters, mock_process_rows, mock_load_reports, 
    mock_inspect, mock_metrics, mock_rows
):
    """Test standard ETL pipeline returning successful JSON payload"""
    mock_process_rows.return_value = mock_rows
    mock_calc_metrics.return_value = mock_metrics
    mock_build_clusters.return_value = {"cluster_1": []}
    mock_inspect.return_value = {"scanned": 1}

    response = client.post("/analyze", json={"folder": "/fake/reports/dir"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["violations"] == 1
    assert len(data["rows"]) == 1
    assert data["rows"][0]["page"] == "/home"

@patch("main.process_rows")
@patch("main.load_reports")
@patch("main.inspect_report_inventory")
def test_analyze_no_violations(mock_inspect, mock_load, mock_process_rows):
    """Test ETL pipeline throwing a 400 when no violations are found"""
    mock_process_rows.return_value = []  # Empty rows

    response = client.post("/analyze", json={"folder": "/fake/reports/dir"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "No violations found"

@patch("main._build_api_payload")
@patch("main.export_xlsx")
def test_export_xlsx_report(mock_export, mock_build_payload, tmp_path):
    """Test Excel export endpoint"""
    # Mock the tuple returned by _build_api_payload
    mock_build_payload.return_value = ({}, [{"fake": "row"}], {}, {})
    
    # Fake the output file creation so FileResponse doesn't crash
    fake_file = tmp_path / "accessibility_analysis.xlsx"
    fake_file.touch()
    
    with patch("main.Path", return_value=fake_file):
        response = client.post("/export-xlsx", json={"folder": "/fake/dir"})
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        mock_export.assert_called_once()

@patch("main.build_analysis_outputs")
def test_build_analysis_success(mock_build):
    mock_build.return_value = {"status": "success", "files_generated": 5}
    
    response = client.post("/build-analysis", json={
        "reports_dir": "/in", 
        "output_dir": "/out"
    })
    
    assert response.status_code == 200
    assert response.json() == {"status": "success", "files_generated": 5}

@patch("main.build_analysis_outputs")
def test_build_analysis_value_error(mock_build):
    """Test that a ValueError from the runner translates to a 400 Bad Request"""
    mock_build.side_effect = ValueError("Invalid report format")
    
    response = client.post("/build-analysis", json={"reports_dir": "/in", "output_dir": "/out"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid report format"


# -------------------------
# 📊 JOB DASHBOARD TESTS
# -------------------------

@patch("main.Path.exists")
@patch("main.build_analysis_outputs")
def test_run_analysis_for_job_success(mock_build, mock_exists):
    """Test job runner with valid paths"""
    mock_exists.return_value = True
    mock_build.return_value = {"status": "success"}

    response = client.post("/jobs/job-123/run-analysis", json={
        "jobs_base_dir": "/fake/jobs",
    })

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-123"
    assert "reports_dir" in response.json()

@patch("main.Path.exists")
def test_run_analysis_for_job_missing_reports(mock_exists):
    """Test job runner failing if reports dir does not exist"""
    mock_exists.return_value = False  # Simulates missing reports directory

    response = client.post("/jobs/job-123/run-analysis", json={})
    
    assert response.status_code == 404
    assert "Reports directory not found" in response.json()["detail"]


@patch("main.Path.exists", return_value=True)
@patch("main.Path.is_file", return_value=True)
@patch("main.Path.read_text")
def test_analysis_status_success(mock_read_text, mock_is_file, mock_exists):
    """Test fetching JSON analysis status"""
    mock_read_text.return_value = json.dumps({"status": "completed"})

    response = client.get("/jobs/job-123/analysis-status")
    
    assert response.status_code == 200
    assert response.json() == {"status": "completed"}


@patch("main.Path.exists", return_value=False)
def test_file_response_not_found(mock_exists):
    """Test 404 handling in the _file_response and _json_file helpers"""
    response_json = client.get("/jobs/job-123/analysis-status")
    assert response_json.status_code == 404

    response_file = client.get("/jobs/job-123/dashboard")
    assert response_file.status_code == 404


# -------------------------
# 🖼️ STATIC/HTML ENDPOINTS
# -------------------------

def test_dashboard_template():
    """Test the dashboard template renders. Requires a dummy template to avoid Jinja errors."""
    with patch("main.templates.TemplateResponse") as mock_template:
        mock_template.return_value = "Mocked HTML Response"
        
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        mock_template.assert_called_once()
        assert mock_template.call_args[1]["name"] == "dashboard.html"


def test_documentation_endpoints(tmp_path):
    """Test simple static HTML file serves by pointing TEMPLATES_DIR to a tmp path"""
    # Create dummy files
    for filename in ["workbook_guide.html", "readme_overview.html", "dashboard_guide.html"]:
        (tmp_path / filename).write_text(f"<h1>{filename}</h1>")

    with patch("main.TEMPLATES_DIR", tmp_path):
        res1 = client.get("/workbook_guide.html")
        assert res1.status_code == 200
        assert "workbook_guide" in res1.text

        res2 = client.get("/readme_overview.html")
        assert res2.status_code == 200

        res3 = client.get("/dashboard_guide.html")
        assert res3.status_code == 200


# -------------------------
# 🤖 COMPONENT LEARNING TESTS
# -------------------------

@patch("main.save_learning")
@patch("main.load_learning")
def test_learn_component(mock_load, mock_save):
    """Test that learning a component updates the in-memory dictionary and saves it"""
    # Provide a base state
    mock_load.return_value = {"existing-pattern": {"count": 1, "component": "tab"}}
    
    response = client.post("/learn-component", json={
        "pattern": "div > span.button-text", 
        "component": "button"
    })
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Assert side effects took place
    mock_save.assert_called_once()
    assert "div > span.button-text" in main.LEARNING

def test_get_learned_components():
    """Test the unique aggregation of components from the LEARNING dict"""
    main.LEARNING.clear()
    main.LEARNING.update({
        "pattern_1": {"component": "nav"},
        "pattern_2": {"component": "nav"},
        "pattern_3": {"component": "other"},     # Should be ignored
        "pattern_4": {"component": "modal"},
        "pattern_5": {}                          # Missing component should be ignored
    })

    response = client.get("/learned-components")
    
    assert response.status_code == 200
    # Should be sorted and deduplicated, excluding "other"
    assert response.json() == ["modal", "nav"]

@patch("main.get_suggested_components")
def test_get_suggested_components(mock_suggested):
    """Test proxying of suggested components"""
    mock_suggested.return_value = ["accordion", "alert"]
    
    response = client.get("/suggested-components")
    
    assert response.status_code == 200
    assert response.json() == ["accordion", "alert"]