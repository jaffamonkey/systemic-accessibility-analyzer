from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from adapters import load_adapters
from analyzer.component_detector import get_emerging_patterns
from analyzer.component_learning import LEARNING, load_learning, save_learning
from exports.xlsx_exporter import export_xlsx
from services.analysis_runner import build_analysis_outputs
from services.bi_fields import humanize_page_key
from services.cluster_engine import build_clusters
from services.metrics_engine import calculate_metrics, get_suggested_components
from services.processing_engine import process_rows
from services.report_loader import load_reports, inspect_report_inventory

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

DEFAULT_LOCAL_JOBS_DIR = Path(
    "/Users/user/code/systemic-accessibility-analyzer/tools/auth_service/jobs"
)
JOBS_BASE_DIR = Path(
    os.getenv("ANALYSIS_JOBS_BASE_DIR", str(DEFAULT_LOCAL_JOBS_DIR))
).resolve()

load_adapters()

from adapters.registry import ADAPTERS
print("REGISTERED ADAPTER COUNT:", len(ADAPTERS))
print("REGISTERED ADAPTERS:", [a.__name__ for _, a in ADAPTERS])
print("REGISTERED DETECTORS:", [d.__name__ for d, _ in ADAPTERS])

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class LearnComponentRequest(BaseModel):
    pattern: str
    component: str


class AnalyzeRequest(BaseModel):
    folder: str


class BuildAnalysisRequest(BaseModel):
    reports_dir: str
    output_dir: str


class JobRunAnalysisRequest(BaseModel):
    jobs_base_dir: str | None = None
    reports_dir: str | None = None
    output_dir: str | None = None


def _resolve_base_dir(jobs_base_dir: str | None = None) -> Path:
    return Path(jobs_base_dir).resolve() if jobs_base_dir else JOBS_BASE_DIR


def _resolve_job_dirs(
    job_id: str,
    jobs_base_dir: str | None = None,
    reports_dir: str | None = None,
    output_dir: str | None = None,
) -> tuple[Path, Path, Path]:
    base = _resolve_base_dir(jobs_base_dir)
    job_dir = base / job_id
    resolved_reports = Path(reports_dir).resolve() if reports_dir else job_dir / "reports"
    resolved_output = Path(output_dir).resolve() if output_dir else job_dir / "analysis"
    return job_dir, resolved_reports, resolved_output


def _resolve_analysis_dir(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
) -> Path:
    base = _resolve_base_dir(jobs_base_dir)
    return Path(analysis_dir).resolve() if analysis_dir else (base / job_id / "analysis")


def _json_file(path: Path, not_found_message: str):
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=not_found_message)
    return json.loads(path.read_text(encoding="utf-8"))


def _file_response(path: Path, not_found_message: str, filename: str | None = None):
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=not_found_message)
    return FileResponse(path, filename=filename)

def _build_api_payload(folder: str) -> tuple[dict, list, list, dict]:
    inventory_check = inspect_report_inventory(folder)
    rows = process_rows(load_reports(folder))

    if not rows:
        raise HTTPException(status_code=400, detail="No violations found")

    clusters = build_clusters(rows)
    metrics = calculate_metrics(rows, clusters)

    payload = {
        "violations": len(rows),
        "pages_list": metrics["pages"],       # Passes the list
        "pages": metrics["pages_count"],      # Passes the count to the "Pages Affected" card
        "shared_pattern_impact": metrics["shared_pattern_impact"],
        "design_system_impact": metrics["design_system_impact"],
        "accessibility_debt_index": metrics["accessibility_debt_index"],
        "component_heatmap": metrics["component_heatmap"],
        "design_heatmap": metrics["design_heatmap"],
        "source_counts": metrics["source_counts"],
        "wcag_levels": metrics["wcag_levels"],
        "distinct_wcag_criteria": metrics.get("distinct_wcag_criteria", 0),
        "accessibility_opportunity_score": metrics["accessibility_opportunity_score"],
        "confidence_counts": metrics["confidence_counts"],
        "issuesperpage": metrics["issuesperpage"],
        "consensus_counts": metrics["consensus_counts"],
        "component_risk": metrics["component_risk"],
        "top_fixes": metrics["top_fixes"],
        "next_best_fixes": metrics.get("next_best_fixes", []),
        "next_best_fixes_summary": metrics.get("next_best_fixes_summary", {}),
        "clusters": clusters,
        "suggested_components": get_suggested_components(),
        "emerging_patterns": get_emerging_patterns(),
        "frame_issues": metrics.get("frame_issues", 0),
        "frame_pages": metrics.get("frame_pages", 0),
        "frame_pages_list": metrics.get("frame_pages_list", []),
        "problem_types": metrics.get("problem_types", {}),
        "page_inventory_check": inventory_check,
        "shared_source_rate": metrics.get("shared_source_rate", 0),
        "top5_page_concentration": metrics.get("top5_page_concentration", 0),
        "top5_pages_list": metrics.get("top5_pages_list", []),
        "tool_family_counts": metrics.get("tool_family_counts", {}),
        "tool_engine_counts": metrics.get("tool_engine_counts", {}),
        "tool_agreement_profile": metrics.get("tool_agreement_profile", {}),
        "tool_family_agreement_profile": metrics.get("tool_family_agreement_profile", {}),
        "tool_engine_agreement_profile": metrics.get("tool_engine_agreement_profile", {}),
        "rows": [
            {
                "files": r.get("files", []),
                "page": r.get("page"),
                "page_display": r.get("page_display") or humanize_page_key(r.get("page")),
                "page_group": r.get("page_group"),
                "wcag": r.get("wcag"),
                "wcag_title": r.get("wcag_title"),
                "ruleId": r.get("ruleId"),
                "rule_id": r.get("rule_id"),
                "rule_label": r.get("rule_label"),
                "wcag_level": r.get("wcag_level"),
                "wcag_level_sort": r.get("wcag_level_sort"),
                "component": r.get("component"),
                "component_group": r.get("component_group"),
                "component_display": r.get("component_display"),
                "design_system": r.get("design_system"),
                "design_system_issue": r.get("design_system_issue"),
                "issue_scope": r.get("issue_scope"),
                "issue_scope_sort": r.get("issue_scope_sort"),
                "severity": r.get("severity"),
                "severity_sort": r.get("severity_sort"),
                "message": r.get("message"),
                "source": r.get("source"),
                "pattern": r.get("pattern"),
                "display_pattern": r.get("display_pattern"),
                "pattern_parts": r.get("pattern_parts", []),
                "owner_team": r.get("owner_team"),
                "issue_rank_score": r.get("issue_rank_score"),
                "tool_count": r.get("tool_count"),
                "tool_family_count": r.get("tool_family_count"),
                "tool_families": r.get("tool_families", []),
                "tool_engine": r.get("tool_engine"),
                "tool_engine_count": r.get("tool_engine_count"),
                "tool_engines": r.get("tool_engines", []),
                "consensus": r.get("consensus"),
                "confidence": r.get("confidence"),
                "dom_path": r.get("dom_path"),
                "fingerprint": r.get("fingerprint"),
                "selector": r.get("selector"),
                "dom": r.get("dom"),
            }
            for r in rows
        ],
    }
    return payload, rows, clusters, metrics


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    payload, _, _, _ = _build_api_payload(request.folder)
    return payload


@app.post("/export-xlsx")
def export_xlsx_report(request: AnalyzeRequest):
    _, rows, clusters, metrics = _build_api_payload(request.folder)
    output = Path("accessibility_analysis.xlsx")
    export_xlsx(rows, clusters, metrics, output)
    return FileResponse(output, filename="accessibility_analysis.xlsx")


@app.post("/build-analysis")
def build_analysis(request: BuildAnalysisRequest):
    try:
        return build_analysis_outputs(Path(request.reports_dir), Path(request.output_dir))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/jobs/{job_id}/run-analysis")
def run_analysis_for_job(job_id: str, request: JobRunAnalysisRequest):
    try:
        job_dir, reports_dir, output_dir = _resolve_job_dirs(
            job_id=job_id,
            jobs_base_dir=request.jobs_base_dir,
            reports_dir=request.reports_dir,
            output_dir=request.output_dir,
        )

        if not reports_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Reports directory not found for job {job_id}: {reports_dir}",
            )

        result = build_analysis_outputs(reports_dir, output_dir)

        result["job_id"] = job_id
        result["job_dir"] = str(job_dir)
        result["reports_dir"] = str(reports_dir)
        result["output_dir"] = str(output_dir)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/jobs/{job_id}/analysis-status")
def analysis_status(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    status_path = resolved_analysis_dir / "analysis_status.json"
    return _json_file(status_path, f"No analysis_status.json found for job {job_id}")


@app.get("/jobs/{job_id}/dashboard")
def dashboard_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    dashboard_path = resolved_analysis_dir / "dashboard.html"
    return _file_response(dashboard_path, f"No dashboard found for job {job_id}")


@app.get("/jobs/{job_id}/workbook")
def workbook_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    workbook_path = resolved_analysis_dir / "accessibility_analysis.xlsx"
    return _file_response(
        workbook_path,
        f"No workbook found for job {job_id}",
        filename=f"{job_id}-accessibility_analysis.xlsx",
    )


@app.get("/jobs/{job_id}/analysis-data")
def analysis_data_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    data_path = resolved_analysis_dir / "data" / "analysis.json"
    return _json_file(data_path, f"No analysis data found for job {job_id}")


@app.get("/jobs/{job_id}/site_preview.html")
def site_preview_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    preview_path = resolved_analysis_dir / "site_preview.html"
    return _file_response(preview_path, f"No site preview found for job {job_id}")


@app.get("/jobs/{job_id}/static/{asset_path:path}")
def job_dashboard_static(
    job_id: str,
    asset_path: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    asset_file = resolved_analysis_dir / "static" / asset_path
    return _file_response(asset_file, f"Static asset not found for job {job_id}: {asset_path}")


@app.get("/jobs/{job_id}/data/{data_path:path}")
def job_dashboard_data(
    job_id: str,
    data_path: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    data_file = resolved_analysis_dir / "data" / data_path
    return _file_response(data_file, f"Data file not found for job {job_id}: {data_path}")


# @app.get("/jobs/{job_id}/reports/visual-preview/{asset_path:path}")
# def job_screenshots(
#     job_id: str,
#     asset_path: str,
#     jobs_base_dir: str | None = None,
#     analysis_dir: str | None = None,
# ):
#     resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
#     asset_file = resolved_analysis_dir / "screenshots" / asset_path
#     return _file_response(asset_file, f"Screenshot asset not found for job {job_id}: {asset_path}")

@app.get("/jobs/{job_id}/reports/visual-preview/{asset_path:path}")
def job_visual_preview_assets(
    job_id: str,
    asset_path: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    base = _resolve_base_dir(jobs_base_dir)
    asset_file = base / job_id / "reports" / "visual-preview" / asset_path
    return _file_response(asset_file, f"Visual preview asset not found for job {job_id}: {asset_path}")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashbaord.html",
        context={"request": request},
    )


@app.post("/learn-component")
def learn_component(request: LearnComponentRequest):
    pattern = request.pattern
    component = request.component

    if pattern not in LEARNING:
        LEARNING[pattern] = {"count": 0, "component": component}
    else:
        LEARNING[pattern]["component"] = component

    save_learning(LEARNING)
    LEARNING.clear()
    LEARNING.update(load_learning())
    return {"status": "ok"}


@app.get("/suggested-components")
def suggested_components():
    return get_suggested_components()


@app.get("/learned-components")
def get_learned_components():
    components = {
        data.get("component")
        for data in LEARNING.values()
        if data.get("component") and data.get("component") != "other"
    }
    return sorted(components)


@app.get("/workbook_guide.html")
def workbook_guide():
    return FileResponse(TEMPLATES_DIR / "workbook_guide.html")


@app.get("/readme_overview.html")
def readme_overview():
    return FileResponse(TEMPLATES_DIR / "readme_overview.html")


@app.get("/dashboard_guide.html")
def dashboard_charts_and_metrics_guide():
    return FileResponse(TEMPLATES_DIR / "dashboard_guide.html")

@app.get("/jobs/{job_id}/virtual_screenreader.html")
def virtual_screenreader_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    preview_path = resolved_analysis_dir / "virtual_screenreader.html"
    return _file_response(preview_path, f"No virtual screenreader page found for job {job_id}")

@app.get("/jobs/{job_id}/virtual-screenreader/{asset_path:path}")
def job_virtual_screenreader_assets(
    job_id: str,
    asset_path: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    asset_file = resolved_analysis_dir / "virtual-screenreader" / asset_path
    return _file_response(asset_file, f"Virtual screenreader asset not found for job {job_id}: {asset_path}")

@app.get("/jobs/{job_id}/tab_map.html")
def tab_map_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    preview_path = resolved_analysis_dir / "tab_map.html"
    return _file_response(preview_path, f"No tab map page found for job {job_id}")

@app.get("/jobs/{job_id}/tab-map/{asset_path:path}")
def job_tab_map_assets(
    job_id: str,
    asset_path: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    asset_file = resolved_analysis_dir / "tab-map" / asset_path
    return _file_response(asset_file, f"Tab map asset not found for job {job_id}: {asset_path}")


@app.get("/jobs/{job_id}/contrast_report.html")
def contrast_report_for_job(
    job_id: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    preview_path = resolved_analysis_dir / "contrast_report.html"
    return _file_response(preview_path, f"No virtual screenreader page found for job {job_id}")

@app.get("/jobs/{job_id}/contrast/{asset_path:path}")
def job_tab_map_assets(
    job_id: str,
    asset_path: str,
    jobs_base_dir: str | None = None,
    analysis_dir: str | None = None,
):
    resolved_analysis_dir = _resolve_analysis_dir(job_id, jobs_base_dir, analysis_dir)
    asset_file = resolved_analysis_dir / "contrast" / asset_path
    return _file_response(asset_file, f"Conrast asset not found for job {job_id}: {asset_path}")
