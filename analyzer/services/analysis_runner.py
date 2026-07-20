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
try:
    from exports.xlsx_exporter import export_xlsx
except ImportError:
    export_xlsx = None

# def _copy_tree(src: Path, dst: Path) -> None:
#     """Recursively copy a directory tree."""
#     if not src.exists():
#         return
#     if dst.exists():
#         shutil.rmtree(dst)
#     shutil.copytree(src, dst)

def _copy_tree(src: Path, dst: Path) -> None:
    """Copies items, but does NOT rmtree the destination first."""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_dir():
            shutil.copytree(item, dst / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst / item.name)

def _copy_optional_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree only if it exists."""
    if src.exists():
        _copy_tree(src, dst)

ROOT = Path(__file__).resolve().parent.parent

# --- (Keep your existing helper functions: _infer_job_id_from_reports_dir, _copy_tree, _copy_optional_tree, _looks_like_hash, friendly_pattern, _build_debug_matches here) ---

def _build_debug_matches(rows):
    watch = {
        "button-name",
        "color-contrast",
        "color-contrast-enhanced",
        "interactive-name",
        "text_contrast_sufficient",
        "label",
    }

    debug_rows = []
    for r in rows:
        if not r.get("page"):
        # Assuming your row has a 'source_file' or 'path' key
            path = r.get("path") or r.get("source_file") or "Unknown"
            r["page"] = Path(path).stem # Extracts 'my_page' from '/path/to/my_page.json'
        canonical_rule_id = r.get("canonical_rule_id") or r.get("ruleId")
        if canonical_rule_id not in watch:
            continue

        debug_rows.append({
            "page": r.get("page"),
            "page_display": r.get("page_display") or humanize_page_key(r.get("page")),
            "source": r.get("source"),
            "sources": r.get("sources", []),
            "ruleId": r.get("ruleId"),
            "canonical_rule_id": r.get("canonical_rule_id"),
            "canonical_problem_type": r.get("canonical_problem_type"),
            "normalized_target_key": r.get("normalized_target_key"),
            "component": r.get("component"),
            "component_group": r.get("component_group"),
            "fingerprint": r.get("fingerprint"),
            "selector": r.get("selector"),
            "dom_path": r.get("dom_path"),
            "message": r.get("message"),
            "tool_count": r.get("tool_count"),
            "tool_family_count": r.get("tool_family_count"),
            "tool_families": r.get("tool_families", []),
            "consensus": r.get("consensus"),
            "confidence": r.get("confidence"),
        })

    return debug_rows[:300]
    
def _infer_job_id_from_reports_dir(reports_dir: Path) -> str | None:
    parts = reports_dir.resolve().parts
    try:
        jobs_index = parts.index("jobs")
        return parts[jobs_index + 1]
    except (ValueError, IndexError):
        return None

def friendly_pattern(pattern: str) -> str:
    # Truncate long patterns and replace underscores for readability
    return pattern.replace("_", " ")[:50]

def build_analysis_outputs(reports_dir: Path, output_dir: Path) -> dict:
    reports_dir = Path(reports_dir).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(parents=True, exist_ok=True)

    # --- 1. Pipeline Engine: Load & Process Data ---
    load_adapters()
    rows = process_rows(load_reports(str(reports_dir)))
          
    # Enrich rows: Ensure rows are linked to pages as lists
    for r in rows:
        if not r.get("files"):
            page = r.get("page") or r.get("page_key")
            if page:
                r["files"] = [page]
    
    # --- 2. Build Clusters & Calculate Metrics ---
    clusters = build_clusters(rows)
    
    # Calculate cluster page counts and unique files
    for cluster in clusters:
        pattern = cluster.get("pattern")
        matching_rows = [r for r in rows if r.get("pattern") == pattern]
        
        unique_files = set()
        for r in matching_rows:
            if "files" in r and isinstance(r["files"], list):
                unique_files.update(r["files"])
            elif r.get("page"):
                unique_files.add(r.get("page"))
        
        cluster["affected_pages_count"] = len(unique_files)
        cluster["files"] = list(unique_files)
    
    metrics = calculate_metrics(rows, clusters)

    # --- 3. Construct Final Payload ---
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
                "dom_path": r.get("dom_path") or r.get("dom"),
                "fingerprint": r.get("fingerprint"),
                "files": r.get("files") if isinstance(r.get("files"), list) else [r.get("page") or "Unknown"],
                "wcag": r.get("wcag") or r.get("ruleId"), 
                "dom": r.get("dom") 
            } for r in rows 
        ],
    }
    
    # Merge remaining custom metrics into the payload
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
    if 'export_xlsx' in globals(): # Safety check in case it isn't imported
        export_xlsx(rows, clusters, metrics, workbook_path)

    # --- 6. Deploy Dashboard & Assets ---
    dashboard_template_dir = ROOT / "templates"
    static_templates_dir = ROOT / "static"
    
    _copy_tree(dashboard_template_dir, output_dir)
    _copy_tree(static_templates_dir, output_dir / "static")

    # Sweep for any remaining .html guide files in the templates root
    for html_file in dashboard_template_dir.glob("*.html"):
        shutil.copy2(html_file, output_dir / html_file.name)
    
    _copy_optional_tree(reports_dir / "virtual-screenreader", output_dir / "virtual-screenreader")
    _copy_optional_tree(reports_dir / "tab-map", output_dir / "tab-map")
    _copy_optional_tree(reports_dir / "contrast-checker", output_dir / "contrast")
    _copy_optional_tree(reports_dir / "visual-preview", output_dir / "visual_review")

    # --- 7. Save Component Learning (The Batch Save!) ---
    # This ensures all the new components detected during processing are written to disk at once
    save_learning(LEARNING)

    # --- 8. Final Status Return ---
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