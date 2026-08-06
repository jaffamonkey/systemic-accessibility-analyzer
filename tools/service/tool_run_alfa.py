from __future__ import annotations

import os
from pathlib import Path

from service.tool_runner_common import run_node_tool


def run_alfa(job_dir: Path, *, require_storage_state: bool = True) -> None:
    # 1. Create a fresh copy of the system environment variables
    custom_env = os.environ.copy()
    
    # 2. Inject the massive 8GB memory limit for the V8 engine
    custom_env["NODE_OPTIONS"] = "--max-old-space-size=8192"

    # 3. Pass the custom environment down to the runner
    run_node_tool(
        job_dir,
        "alfa",
        "run_alfa.js",
        log_name="alfa.log",
        require_storage_state=require_storage_state,
        env=custom_env, 
    )