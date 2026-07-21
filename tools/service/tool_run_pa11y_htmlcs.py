from __future__ import annotations

from pathlib import Path
from service.tool_runner_common import run_node_tool


def run_pa11y_htmlcs(job_dir: Path, *, require_storage_state: bool = True) -> None:
    run_node_tool(
        job_dir,
        "pa11y_runner_htmlcs",
        "run_pa11y_htmlcs.js",
        log_name="pa11y_htmlcs.log",
        require_storage_state=require_storage_state,
        check=False,
    )