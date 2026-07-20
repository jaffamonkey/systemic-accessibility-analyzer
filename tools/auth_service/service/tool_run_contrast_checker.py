from __future__ import annotations

import subprocess
from pathlib import Path


def run_contrast_checker(job_dir: Path) -> None:
    # Ensure job_dir is an absolute, resolved path
    absolute_job_dir = job_dir.resolve()
    
    runner_dir = Path(__file__).resolve().parents[1] / "tool_runners" / "contrast_checker"
    script_path = runner_dir / "run_contrast.js"

    # Pass the absolute path as a string to the Node script
    subprocess.run(
        ["node", str(script_path), str(absolute_job_dir)], 
        cwd=str(runner_dir),
        check=True,
    )