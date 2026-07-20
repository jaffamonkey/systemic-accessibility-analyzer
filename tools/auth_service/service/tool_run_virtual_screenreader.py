from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_virtual_screenreader(job_dir: Path, *, require_storage_state: bool = False) -> None:
    job_dir = job_dir.resolve()

    logs_dir = job_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "virtual-screenreader.log"

    storage_state = job_dir / "auth" / "storage_state.json"

    env = os.environ.copy()
    if storage_state.exists():
        env["STORAGE_STATE_PATH"] = str(storage_state)
    else:
        env.pop("STORAGE_STATE_PATH", None)

    auth_service_dir = Path(__file__).resolve().parents[1]
    runner_dir = auth_service_dir / "tool_runners" / "virtual_screenreader_runner"
    script_path = runner_dir / "run_virtual_screenreader.js"

    if not runner_dir.exists():
        raise FileNotFoundError(f"Runner directory not found: {runner_dir}")
    if not script_path.exists():
        raise FileNotFoundError(f"Runner script not found: {script_path}")

    if require_storage_state and not storage_state.exists():
        raise FileNotFoundError(f"Missing authenticated storage state: {storage_state}")

    with log_path.open("a", encoding="utf-8") as fh:
        result = subprocess.run(
            ["node", "run_virtual_screenreader.js", str(job_dir)],
            cwd=runner_dir,
            check=False,
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
        )

    if result.returncode != 0:
        raise RuntimeError(f"virtual-screenreader runner failed with exit code {result.returncode}")