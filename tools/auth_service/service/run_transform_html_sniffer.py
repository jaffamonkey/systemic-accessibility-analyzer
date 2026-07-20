from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m service.run_transform_html_sniffer <job_dir>")

    job_ref = sys.argv[1]
    job_dir = Path(job_ref).resolve()
    if not job_dir.exists():
        candidate = Path(__file__).resolve().parent.parent / job_ref
        job_dir = candidate.resolve()

    reports_dir = job_dir / "reports" / "html-sniffer"
    if not reports_dir.exists():
        print(f"html-sniffer reports folder not found: {reports_dir}")
        return

    script_path = (
        Path(__file__).resolve().parent.parent
        / "tool_runners"
        / "html_sniffer_runner"
        / "transform-html-sniffer-to-pa11y-shape.js"
    )

    if not script_path.exists():
        raise FileNotFoundError(f"Transform script not found: {script_path}")

    result = subprocess.run(
        ["node", str(script_path), str(reports_dir)],
        check=False,
        cwd=str(script_path.parent),
    )

    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()