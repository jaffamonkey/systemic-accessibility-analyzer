from __future__ import annotations

from pathlib import Path

from service.tool_runner_common import run_node_tool


def run_speca11y(job_dir: Path, *, require_storage_state: bool = True) -> None:
    run_node_tool(
        job_dir,
        "speca11y",
        "run_speca11y.mjs",
        log_name="speca11y.log",
        require_storage_state=require_storage_state,
    )
