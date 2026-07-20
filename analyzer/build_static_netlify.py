
from pathlib import Path
import argparse

from services.analysis_runner import build_analysis_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static dashboard bundle from a reports folder.")
    parser.add_argument("--reports-dir", default=str(Path(__file__).resolve().parent / "reports"))
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parent / "dist"))
    args = parser.parse_args()

    result = build_analysis_outputs(Path(args.reports_dir), Path(args.output_dir))
    print(f"Built static analysis at: {result['output_dir']}")


if __name__ == "__main__":
    main()
