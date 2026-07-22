"""
Job Layout Setup

A utility script to initialize the standard directory structure required 
for an analysis job. Ensures isolated folders exist for inputs, authentication 
state, raw reports, final analysis, and logs.
"""

from __future__ import annotations
from pathlib import Path

JOB_SUBDIRS = ["input", "auth", "reports", "analysis", "logs"]

def create_job_dirs(job_root: Path) -> None:
    """Creates the necessary subdirectories for a new job instance."""
    job_root.mkdir(parents=True, exist_ok=True)
    for name in JOB_SUBDIRS:
        (job_root / name).mkdir(parents=True, exist_ok=True)