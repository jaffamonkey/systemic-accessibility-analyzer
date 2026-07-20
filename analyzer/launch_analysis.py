# /Users/user/code/github/wcag-tools-reporting-analysis/launch_analysis.py
import sys
from pathlib import Path
# Add the repo root so imports work
sys.path.append(str(Path(__file__).parent)) 
from services.analysis_runner import build_analysis_outputs

# Simple, hard-coded runner
reports = Path(sys.argv[1])
output = Path(sys.argv[2])
build_analysis_outputs(reports, output)