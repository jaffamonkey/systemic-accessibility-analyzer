from __future__ import annotations

from pathlib import Path
import sys

from service.tool_run_tab_map import run_tab_map


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_tab_map <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_tab_map(job_dir, require_storage_state=False)
    print("tab-map reports written under:", job_dir / "reports" / "tab-map")
    print("visual previews written under:", job_dir / "reports" / "visual-preview")


if __name__ == "__main__":
    main()
