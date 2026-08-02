"""
Full Job Runner

The master orchestration script for the tooling pipeline. It evaluates the job 
configuration to determine if authentication is required, selects the appropriate 
tool modules (authenticated vs. public), and spawns subprocesses to execute 
each requested accessibility scanner.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import concurrent.futures

from service.prepare_public_job import prepare_public_job

DEFAULT_TOOLS = [
    "axe-core",
    "axe-scan",
    "html-sniffer",
    "oobee",
    "lighthouse",
    "ibm",
    "uuv",
    "alfa",
    "aslint",
    "editoria11y",
    "nu-html-checker",
    "speca11y",
    "pa11y-axe",
    "pa11y-htmlcs",
    "virtual-screenreader",
    "tab-map",
    "contrast-checker",
]

AUTH_TOOL_MODULES = {
    "axe-core": "service.run_authenticated_axe_core",
    "html-sniffer": "service.run_authenticated_html_sniffer",
    "oobee": "service.run_authenticated_oobee",
    "lighthouse": "service.run_authenticated_lighthouse",
    "ibm": "service.run_authenticated_ibm",
    "uuv": "service.run_authenticated_uuv",
    "alfa": "service.run_authenticated_alfa",
    "aslint": "service.run_authenticated_aslint",
    "editoria11y": "service.run_authenticated_editoria11y",
    "nu-html-checker": "service.run_authenticated_nu_html_checker",
    "speca11y": "service.run_authenticated_speca11y",
    "qualweb": "service.run_authenticated_qualweb",
    "pa11y-htmlcs": "service.run_authenticated_pa11y_htmlcs",
    "pa11y-axe": "service.run_authenticated_pa11y_axe",
    "axe-scan": "service.run_axe_scan",
    "virtual-screenreader": "service.run_virtual_screenreader",
    "tab-map": "service.run_tab_map",
    "contrast-checker": "service.run_contrast_checker",
}

PUBLIC_TOOL_MODULES = {
    "axe-core": "service.run_axe_core",
    "html-sniffer": "service.run_html_sniffer",
    "oobee": "service.run_oobee",
    "lighthouse": "service.run_lighthouse",
    "ibm": "service.run_ibm",
    "uuv": "service.run_uuv",
    "alfa": "service.run_alfa",
    "aslint": "service.run_aslint",
    "editoria11y": "service.run_editoria11y",
    "nu-html-checker": "service.run_nu_html_checker",
    "qualweb": "service.run_qualweb",
    "pa11y-axe": "service.run_pa11y_axe",
    "pa11y-htmlcs": "service.run_pa11y_htmlcs",
    "axe-scan": "service.run_axe_scan",
    "virtual-screenreader": "service.run_virtual_screenreader",
    "tab-map": "service.run_tab_map",
    "contrast-checker": "service.run_contrast_checker",
    "speca11y": "service.run_speca11y",
}

def _run_command(cmd: list[str], *, cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess:
    """Helper to safely execute external shell commands with an optional timeout."""
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False, timeout=timeout)

def _load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def _execute_single_tool(tool: str, module: str, job_id: str, auth_service_dir: Path, reports_dir: Path) -> dict:
    """
    Worker function to execute a single accessibility tool in an isolated subprocess.
    Designed to be run concurrently with a strict timeout.
    """
    tool_reports_dir = reports_dir / tool
    skip_marker = tool_reports_dir / "SKIPPED"
    
    print(f"🔄 Launching {tool}...")
    
    try:
        # 🔥 The 3600 second (30 minute) timeout prevents infinite hangs on longer runs
        result = _run_command(
            [sys.executable, "-m", module, f"jobs/{job_id}"],
            cwd=auth_service_dir,
            timeout=3600
        )
    except subprocess.TimeoutExpired:
        print(f"⏱️ ❌ {tool} timed out after 10 minutes and was forcefully terminated!")
        return {
            "status": "error",
            "returncode": -1,
            "report_count": 0,
            "reports_dir": str(tool_reports_dir),
            "message": "Tool execution timed out and was killed by the orchestrator."
        }

    if skip_marker.exists():
        print(f"⏭️  {tool} skipped (via SKIPPED marker)")
        return {
            "status": "skipped",
            "message": skip_marker.read_text(encoding="utf-8").strip(),
            "reports_dir": str(tool_reports_dir),
        }

    report_count = len(list(tool_reports_dir.glob("*.json"))) if tool_reports_dir.exists() else 0

    if result.returncode == 0:
        print(f"✅ {tool} completed successfully ({report_count} reports)")
        return {
            "status": "ok",
            "report_count": report_count,
            "reports_dir": str(tool_reports_dir),
        }
    elif report_count > 0:
        print(f"⚠️  {tool} finished with warnings ({report_count} reports generated)")
        return {
            "status": "partial",
            "returncode": result.returncode,
            "report_count": report_count,
            "reports_dir": str(tool_reports_dir),
            "message": "Tool returned non-zero but produced report files",
        }
    else:
        print(f"❌ {tool} failed (Code: {result.returncode})")
        return {
            "status": "error",
            "returncode": result.returncode,
            "report_count": 0,
            "reports_dir": str(tool_reports_dir),
        }
def run_full_job(
    *,
    job_id: str,
    job_config: Path,
    auth_service_dir: Path,
    analysis_repo_dir: Path,
    tools: list[str] | None = None,
    skip_analysis: bool = False,
) -> dict:
    """
    Executes the complete analysis lifecycle:
    1. Triggers authentication (if required).
    2. Runs all requested scraping/scanning tools in parallel.
    3. Triggers the final analysis/dashboard generation.
    """
    tools = list(tools or DEFAULT_TOOLS)

    # Automatically expand grouped tools into their specific runner variants
    TOOL_EXPANSIONS = {
        "pa11y": ["pa11y-axe", "pa11y-htmlcs"],
    }

    expanded_tools = []
    for tool in tools:
        expanded_tools.extend(TOOL_EXPANSIONS.get(tool, [tool]))

    # Deduplicate while preserving order
    tools = list(dict.fromkeys(expanded_tools))

    # Always ensure core visual/UX diagnostic tools are included
    if "virtual-screenreader" not in tools: tools.append("virtual-screenreader")
    if "tab-map" not in tools: tools.append("tab-map")
    if "contrast-checker" not in tools: tools.append("contrast-checker")

    auth_service_dir = auth_service_dir.resolve()
    analysis_repo_dir = analysis_repo_dir.resolve()
    job_config = job_config.resolve()

    job_dir = auth_service_dir / "jobs" / job_id
    reports_dir = job_dir / "reports"
    analysis_dir = job_dir / "analysis"

    config_data = json.loads(job_config.read_text(encoding="utf-8"))
    credentials = config_data.get("credentials") or {}
    login_entry_url = str(config_data.get("login_entry_url") or "").strip()
    username = str(credentials.get("username") or "").strip()
    password = str(credentials.get("password") or "").strip()

    requires_auth = bool(login_entry_url or username or password)
    tool_modules = AUTH_TOOL_MODULES if requires_auth else PUBLIC_TOOL_MODULES

    summary = {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "job_config": str(job_config),
        "reports_dir": str(reports_dir),
        "analysis_dir": str(analysis_dir),
        "auth": {"status": "pending"},
        "tools": {},
        "analysis": {"status": "skipped" if skip_analysis else "pending"},
    }

    status_path = job_dir / "status.json"

    # --- 1. AUTHENTICATION PHASE ---
    if requires_auth:
        print(f"\n🔐 Executing Authentication for Job {job_id}...")
        prepare_cmd = [
            sys.executable,
            "run_job.py",
            f"jobs/{job_id}",
            str(job_config),
        ]
        prepare_result = _run_command(prepare_cmd, cwd=auth_service_dir)

        job_status = _load_status(status_path)

        if prepare_result.returncode != 0:
            print("❌ Authentication script failed.")
            summary["auth"] = {
                "status": "error",
                "returncode": prepare_result.returncode,
                "message": "run_job.py failed",
            }
            _write_summary(job_dir, summary)
            return summary

        if not job_status.get("auth_success"):
            print("❌ Authentication failed (Invalid Credentials/Timeout).")
            summary["auth"] = {
                "status": "error",
                "message": job_status.get("message", "Authentication failed"),
            }
            _write_summary(job_dir, summary)
            return summary

        print("✅ Authentication successful.")
        summary["auth"] = {
            "status": "ok",
            "message": job_status.get("message", "Authentication succeeded"),
            "final_url": job_status.get("final_url"),
        }
    else:
        print(f"\n🌐 Executing Public Job {job_id} (No Auth required)")
        job_status = prepare_public_job(job_dir, job_config)
        summary["auth"] = {
            "status": "skipped",
            "message": job_status.get("message", "Authentication not required"),
        }

    # --- 2. TOOL EXECUTION PHASE (PARALLEL) ---
    print(f"\n⚡ Spawning {len(tools)} analysis tools concurrently...")
    
    # Setup the execution pool. max_workers defines how many tools run at exactly the same time.
    # We default to half of the CPU cores to prevent local machines from freezing, but ensure 
    # at least 4 concurrent workers if the machine has fewer cores.
    import multiprocessing
    max_workers = max(4, multiprocessing.cpu_count() // 2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a dictionary of futures to keep track of which tool is running
        future_to_tool = {}
        for tool in tools:
            module = tool_modules.get(tool)
            if not module:
                summary["tools"][tool] = {
                    "status": "error",
                    "message": f"Unknown tool: {tool}",
                }
                continue
            
            # Submit the isolated task to the worker pool
            future = executor.submit(
                _execute_single_tool, 
                tool, 
                module, 
                job_id, 
                auth_service_dir, 
                reports_dir
            )
            future_to_tool[future] = tool

        # Wait for all tools to finish and collect their results
        for future in concurrent.futures.as_completed(future_to_tool):
            tool = future_to_tool[future]
            try:
                tool_summary = future.result()
                summary["tools"][tool] = tool_summary
            except Exception as exc:
                print(f"❌ {tool} generated an unhandled exception: {exc}")
                summary["tools"][tool] = {
                    "status": "error",
                    "message": str(exc)
                }

    # --- 3. ANALYSIS PHASE ---
    if not skip_analysis:
        print("\n📈 Building Systemic Dashboard and Analytics...")
        analysis_cmd = [
            sys.executable,
            "run_job_analysis.py",
            "--reports-dir",
            str(reports_dir),
            "--output-dir",
            str(analysis_dir),
        ]
        analysis_result = _run_command(analysis_cmd, cwd=analysis_repo_dir)

        if analysis_result.returncode == 0:
            print("✅ Dashboard built successfully!")
            summary["analysis"] = {
                "status": "ok",
                "output_dir": str(analysis_dir),
                "dashboard": str(analysis_dir / "dashboard.html"),
                "workbook": str(analysis_dir / "accessibility_analysis.xlsx"),
            }
        else:
            print("❌ Dashboard generation failed.")
            summary["analysis"] = {
                "status": "error",
                "returncode": analysis_result.returncode,
                "output_dir": str(analysis_dir),
            }

    _write_summary(job_dir, summary)
    return summary


def _write_summary(job_dir: Path, summary: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    summary_path = job_dir / "full_job_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")