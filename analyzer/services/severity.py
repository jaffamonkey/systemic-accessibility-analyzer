"""
Severity Normalizer

Different accessibility tools use entirely different scales for severity. 
For example, Axe uses (critical, serious, moderate, minor), while HTMLCodeSniffer 
uses (error, warning, notice). 

This module standardizes all incoming severity ratings to a canonical scale 
so that issues can be uniformly prioritized across the dashboard.
"""

def normalize_severity(raw_severity: str | None) -> str | None:
    """
    Maps a tool-specific severity string to the canonical scale:
    'critical', 'serious', 'moderate', 'minor', or 'warning'. 
    
    Returns None if the issue is deemed too noisy to include (e.g., HTMLCS notices).
    """
    if not raw_severity:
        return "minor"

    s = str(raw_severity).strip().lower()

    # Axe / Axe-scan (Our baseline standard)
    if s in ["critical", "serious", "moderate", "minor"]:
        return s

    # IBM Equal Access Accessibility Checker
    if s == "violation":
        return "serious"
    if s == "warning":
        return "warning"

    # HTML CodeSniffer (HTMLCS)
    if s == "error":
        return "serious"
    if s == "notice":
        return None  # 🚫 Ignore manual checks/notices completely to reduce noise

    # Lighthouse / Pa11y / Generic Fallbacks
    if s == "error":
        return "serious"
    if s == "warning":
        return "warning"

    # Default fallback for unrecognized severities
    return "minor"