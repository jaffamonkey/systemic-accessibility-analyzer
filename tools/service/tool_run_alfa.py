from __future__ import annotations

import os
from pathlib import Path

from service.tool_runner_common import run_node_tool


def run_alfa(job_dir: Path, *, require_storage_state: bool = True) -> None:
    # Give Node.js up to 8GB of heap memory to handle large DOMs
    os.environ["NODE_OPTIONS"] = "--max-old-space-size=8192"

    run_node_tool(
        job_dir,
        "alfa",
        "run_alfa.js",  # or run_alfa.mjs depending on your filename
        log_name="alfa.log",
        require_storage_state=require_storage_state,
    )