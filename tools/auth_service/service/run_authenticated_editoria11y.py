from __future__ import annotations

from pathlib import Path
import sys

from service.tool_run_editoria11y import run_editoria11y


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_authenticated_editoria11y <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_editoria11y(job_dir)
    print("editoria11y reports written under:", job_dir / "reports" / "editoria11y")


if __name__ == "__main__":
    main()
