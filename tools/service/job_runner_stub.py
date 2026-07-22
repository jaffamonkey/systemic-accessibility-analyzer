"""
Job Authenticator & Preparer

Loads the user's job configuration and triggers the automated login flow. 
If successful, it saves the session state (cookies/tokens) to the disk 
so subsequent scraper tools can inherit the authenticated session.
"""

from __future__ import annotations
from pathlib import Path
import json

from authentication.models import JobConfig, Credentials, SelectorHints
from authentication.shared_login import run_shared_login
from service.job_layout import create_job_dirs

def load_job_config(path: Path) -> JobConfig:
    """Parses a raw JSON config file into a strongly-typed JobConfig object."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return JobConfig(
        login_entry_url=raw["login_entry_url"],
        target_urls=raw["target_urls"],
        credentials=Credentials(**raw["credentials"]),
        auth_mode=raw.get("auth_mode", "auto"),
        selectors=SelectorHints(**raw.get("selectors", {})),
        headless=raw.get("headless", True),
        timeout_ms=raw.get("timeout_ms", 20000),
    )

def prepare_job(job_dir: Path, config_path: Path) -> None:
    """
    Initializes the job directory, loads the configuration, and executes 
    the Playwright login flow, saving the result to a status manifest.
    """
    create_job_dirs(job_dir)
    config = load_job_config(config_path)
    
    # Write the target URLs to a standard text file for legacy tools to consume
    (job_dir / "input" / "urls.txt").write_text("\n".join(config.target_urls) + "\n", encoding="utf-8")
    
    # Store a localized copy of the config inside the job directory for auditing
    (job_dir / "input" / "job_config.json").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    
    auth_result = run_shared_login(config, job_dir)
    
    status = {
        "auth_success": auth_result.success,
        "auth_method": auth_result.method,
        "final_url": auth_result.final_url,
        "storage_state_path": str(auth_result.storage_state_path) if auth_result.storage_state_path else None,
        "message": auth_result.message,
    }
    
    (job_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")