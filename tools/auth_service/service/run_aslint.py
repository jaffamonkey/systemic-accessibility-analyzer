from __future__ import annotations

from pathlib import Path
import sys

from service.tool_run_aslint import run_aslint


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_aslint <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_aslint(job_dir, require_storage_state=False)
    print("aslint reports written under:", job_dir / "reports" / "aslint")


if __name__ == "__main__":
    main()
