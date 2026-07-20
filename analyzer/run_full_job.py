from __future__ import annotations
from pathlib import Path
import argparse
from services.analysis_runner import build_analysis_outputs

def _infer_job_id(reports_dir: Path) -> str:
    """Extracts job_id from the reports directory path."""
    parts = reports_dir.resolve().parts
    try:
        # Assuming path structure ends in /jobs/<job_id>/reports
        jobs_index = parts.index("jobs")
        return parts[jobs_index + 1]
    except (ValueError, IndexError):
        return "default-job"

def main() -> None:
    parser = argparse.ArgumentParser(description="Build job-aware analysis outputs.")
    parser.add_argument("--reports-dir", required=True)
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir).resolve()
    job_id = _infer_job_id(reports_dir)
    
    # Dynamically set output_dir to the path the server expects: /jobs/<job_id>/dashboard
    # We navigate up from the reports dir (assumed to be in .../jobs/<job_id>/reports)
    base_dir = reports_dir.parent.parent # Points to .../jobs/<job_id>/
    output_dir = base_dir / "dashboard"

    print(f"Building analysis for {job_id} into: {output_dir}")

    # Call the runner with the correctly inferred paths
    build_analysis_outputs(reports_dir, output_dir)
    
    print(f"Analysis successfully built for {job_id}")

if __name__ == "__main__":
    main()