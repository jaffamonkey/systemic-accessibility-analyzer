from __future__ import annotations

from pathlib import Path
import sys

from service.tool_run_contrast_checker import run_contrast_checker


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_contrast_checker <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_contrast_checker(job_dir)
    print("contrast-checker reports written under:", job_dir / "reports" / "contrast-checker")


if __name__ == "__main__":
    main()