"""
Authentication Site Hints

A configuration file for known edge-cases. While the heuristic engine 
is designed to work dynamically across the internet, some sites use entirely 
custom authentication triggers (e.g., specific custom endpoints) that require 
manual mapping overrides to ensure the automation succeeds.
"""

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SiteHint:
    domain: str
    login_trigger: str | None = None
    username: str | None = None
    password: str | None = None
    submit: str | None = None
    success: str | None = None

KNOWN_SITE_HINTS: list[SiteHint] = [
    # Marks & Spencer uses a highly customized sliding DOM menu for login
    SiteHint(
        domain="marksandspencer.com",
        login_trigger="a[href*='header_sign-in_sign-in']",
    ),
]