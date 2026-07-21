from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from service.tool_run_html_sniffer import run_html_sniffer


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m service.run_authenticated_html_sniffer <job_dir>")

    job_dir = Path(sys.argv[1])

    run_html_sniffer(job_dir)

    result = subprocess.run(
        [sys.executable, "-m", "service.run_transform_html_sniffer", str(job_dir)],
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    print("html-sniffer reports written under:", job_dir / "reports" / "html-sniffer")


if __name__ == "__main__":
    main()