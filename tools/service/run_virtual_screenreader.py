from __future__ import annotations

import sys
from pathlib import Path

from service.tool_run_virtual_screenreader import run_virtual_screenreader


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_virtual_screenreader <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_virtual_screenreader(job_dir)
    print("virtual screenreader reports written under:", job_dir / "reports" / "virtual-screenreader")


if __name__ == "__main__":
    main()