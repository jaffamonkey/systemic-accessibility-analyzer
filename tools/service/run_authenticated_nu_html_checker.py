from __future__ import annotations

from pathlib import Path
import sys

from service.tool_run_nu_html_checker import run_nu_html_checker


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_authenticated_nu_html_checker <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_nu_html_checker(job_dir)
    print("nu-html-checker reports written under:", job_dir / "reports" / "nu-html-checker")


if __name__ == "__main__":
    main()
