from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_tab_map(job_dir: Path, require_storage_state: bool = False) -> None:
    job_dir = job_dir.resolve()

    runner_dir = Path(__file__).resolve().parents[1] / "tool_runners" / "tab-map-runner"
    script_path = runner_dir / "run_tab_map.js"

    if not runner_dir.exists():
        raise FileNotFoundError(f"tab-map runner folder not found: {runner_dir}")
    if not script_path.exists():
        raise FileNotFoundError(f"run_tab_map.js not found: {script_path}")

    logs_dir = job_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "tab-map.log"

    (job_dir / "reports" / "tab-map").mkdir(parents=True, exist_ok=True)
    (job_dir / "reports" / "visual-preview").mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    storage_state = job_dir / "auth" / "storage_state.json"

    if storage_state.exists():
        env["STORAGE_STATE_PATH"] = str(storage_state)
    elif require_storage_state:
        raise FileNotFoundError(f"storage_state.json not found: {storage_state}")
    else:
        env.pop("STORAGE_STATE_PATH", None)

    with log_path.open("a", encoding="utf-8") as fh:
        subprocess.run(
            ["node", str(script_path), str(job_dir)],
            cwd=str(runner_dir),
            check=True,
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
        )
