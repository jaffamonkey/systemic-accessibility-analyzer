"""
Analysis Runner & Orchestrator

This module serves as the primary controller for the Analysis Service. 
It takes a directory of raw JSON reports, passes them through the ETL 
pipeline (Extraction, Transformation, Deduplication, and Metrics generation), 
and exports the final artifacts (Analysis JSON, Excel Workbook, and the 
static HTML Dashboard) into an output directory.
"""

from __future__ import annotations
from pathlib import Path
import json
import shutil

from adapters import load_adapters
from services.report_loader import load_reports, inspect_report_inventory
from services.processing_engine import process_rows
from services.cluster_engine import build_clusters
from services.metrics_engine import calculate_metrics, get_suggested_components
from analyzer.component_detector import get_emerging_patterns
from services.bi_fields import humanize_page_key
from analyzer.component_learning import LEARNING, save_learning

# Gracefully handle the Excel exporter in case openpyxl isn't installed
try:
    from exports.xlsx_exporter import export_xlsx
except ImportError:
    export_xlsx = None

ROOT = Path(__file__).resolve().parent.parent

# -------------------------
# 🗂️ FILE SYSTEM HELPERS
# -------------------------

def _copy_tree(src: Path, dst: Path) -> None:
    """
    Copies a directory tree safely. Unlike shutil.copytree default behavior, 
    this does NOT delete the destination directory first, allowing us to safely 
    overlay dashboard assets into existing job folders.
    """
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_dir():
            shutil.copytree(item, dst / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst / item.name)


def _copy_optional_tree(src: Path, dst: Path) -> None:
    """Copies a directory tree only if the source actually exists."""
    if src.exists():
        _copy_tree(src, dst)


def _infer_job_id_from_reports_dir(reports_dir: Path) -> str | None:
    """
    Extracts the unique job ID from the folder path hierarchy.
    Assumes a structure like: `/.../jobs/<job-id>/reports`
    """
    parts = reports_dir.resolve().parts
    try:
        jobs_index = parts.index("jobs")
        return parts[jobs_index + 1]
    except (ValueError, IndexError):
        return None


def friendly_pattern(pattern: str) -> str:
    """Truncates long DOM patterns and replaces underscores for UI readability."""
    return pattern.replace("_", " ")[:50]


# -------------------------
# 🚀 MAIN PIPELINE ORCHESTRATOR
# -------------------------

def build_analysis_outputs(reports_dir: Path, output_dir: Path) -> dict:
    """
    The main execution flow for analyzing a job. 
    1. Loads raw reports
    2. Cleans & normalizes data
    3. Builds systemic clusters
    4. Calculates BI metrics
    5. Exports JSON, Excel, and copies static Dashboard HTML assets
    """
    reports_dir = Path(reports_dir).resolve()
    output_dir = Path(output_dir).resolve()
    
    # Ensure destination directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(parents=True, exist_ok=True)

    # --- 1. Pipeline Engine: Load & Process Data ---
    load_adapters()
    rows = process_rows(load_reports(str(reports_dir)))
          
    # Enrich rows: Ensure every row is explicitly linked to an array of file/page keys
    for r in rows:
        if not r.get("files"):
            page = r.get("page") or r.get("page_key")
            if page:
                r["files"] = [page]
    
    # --- 2. Build Clusters & Calculate Metrics ---
    # The cluster engine handles all fuzzy-matching and assigns unique page counts internally
    clusters = build_clusters(rows)
    metrics = calculate_metrics(rows, clusters)

    # --- 3. Construct Final Data Payload ---
    # This dictionary becomes the 'analysis.json' file consumed by the frontend dashboard
    payload = {
        "violations": len(rows),
        "pages": metrics.get("pages_count", 0),
        "pages_list": metrics.get("pages", []),
        "clusters": clusters,
        "suggested_components": get_suggested_components(),
        "emerging_patterns": get_emerging_patterns(),
        "page_inventory_check": inspect_report_inventory(str(reports_dir)),
        "rows": [ 
            { 
                "page": r.get("page") or r.get("page_key") or "Unknown",
                "component": r.get("component") or "Other",
                "issue_scope": r.get("issue_scope") or "Unknown",
                "source": r.get("source") or "-",
                "ruleId": r.get("ruleId") or r.get("wcag"),
                "message": r.get("message"),
                
                # Expose the cleaned architectural fields directly to the UI
                "pattern": r.get("pattern"),
                "selector": r.get("selector"),
                "dom": r.get("dom"), 
                
                "fingerprint": r.get("fingerprint"),
                "files": r.get("files") if isinstance(r.get("files"), list) else [r.get("page") or "Unknown"],
                "wcag": r.get("wcag") or r.get("ruleId"), 
            } for r in rows 
        ],
    }
    
    # Merge any remaining custom metrics from the metrics engine into the root payload
    for key, value in metrics.items():
        if key not in payload:
            payload[key] = value

    job_id = _infer_job_id_from_reports_dir(reports_dir)
    payload["job_id"] = job_id

    # --- 4. Export JSON Data ---
    analysis_json = output_dir / "data" / "analysis.json"
    try:
        with analysis_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to write analysis JSON: {e}")

    # --- 5. Export Excel Workbook ---
    workbook_path = output_dir / "accessibility_analysis.xlsx"
    if 'export_xlsx' in globals() and export_xlsx: 
        export_xlsx(rows, clusters, metrics, workbook_path)

    # --- 6. Deploy Static Dashboard & Assets ---
    dashboard_template_dir = ROOT / "templates"
    static_templates_dir = ROOT / "static"
    
    _copy_tree(dashboard_template_dir, output_dir)
    _copy_tree(static_templates_dir, output_dir / "static")

    # Sweep for any remaining .html guide/documentation files in the templates root
    for html_file in dashboard_template_dir.glob("*.html"):
        shutil.copy2(html_file, output_dir / html_file.name)
    
    # Copy tool-specific visual artifacts if the scanners generated them
    _copy_optional_tree(reports_dir / "virtual-screenreader", output_dir / "virtual-screenreader")
    _copy_optional_tree(reports_dir / "tab-map", output_dir / "tab-map")
    _copy_optional_tree(reports_dir / "contrast-checker", output_dir / "contrast")
    _copy_optional_tree(reports_dir / "visual-preview", output_dir / "visual_review")

    # --- 7. Save Component Learning ---
    # Batches all new, unrecognized DOM patterns detected during the run to disk
    save_learning(LEARNING)

    # --- 8. Final Status Return ---
    # Writes a status manifest so the auth_service knows the analysis finished successfully
    status = {
        "job_id": job_id,
        "reports_dir": str(reports_dir),
        "output_dir": str(output_dir),
        "analysis_json": str(analysis_json),
        "workbook": str(workbook_path),
        "violations": payload["violations"],
        "pages": payload["pages"],
        "screenshots": {"job_id": job_id, "message": "Artifacts processed"}, 
    }
    
    status_path = output_dir / "analysis_status.json"
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    
    return status