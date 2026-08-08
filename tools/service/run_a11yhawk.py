from __future__ import annotations

from pathlib import Path
import sys

from service.tool_run_a11yhawk import run_a11yhawk


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m service.run_a11yhawk <job_dir>")
        raise SystemExit(1)

    job_dir = Path(sys.argv[1])
    run_a11yhawk(job_dir, require_storage_state=False)
    print("a11yhawk reports written under:", job_dir / "reports" / "a11yhawk")


if __name__ == "__main__":
    main()