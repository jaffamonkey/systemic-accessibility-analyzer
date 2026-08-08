from __future__ import annotations

from pathlib import Path

from service.tool_runner_common import run_node_tool


def run_a11yhawk(job_dir: Path, *, require_storage_state: bool = True) -> None:
    run_node_tool(
        job_dir,
        "a11yhawk",
        "run_a11yhawk.mjs",
        log_name="a11yhawk.log",
        require_storage_state=require_storage_state,
    )