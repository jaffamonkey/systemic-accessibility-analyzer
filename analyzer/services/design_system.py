"""
Design System Analyzer

Translates grouped accessibility clusters into actionable root causes.
Rather than telling a team they have 50 page-level errors, this logic 
attributes those errors to the specific underlying Design System asset 
(e.g., global color tokens, the shared button component) that requires fixing.
"""

def detect_design_system_issue(cluster: dict) -> str | None:
    """
    Infers the systemic root cause of an issue cluster based on its 
    WCAG criteria, rule signature, and UI component type.
    
    Returns a human-readable string identifying the offending design 
    system asset, or None if the issue appears to be page-specific content.
    """
    rule = (cluster.get("ruleId") or "").lower()
    wcag = cluster.get("wcag")
    component = (cluster.get("component") or "").lower()

    # 🎨 Color / Theming root causes
    if wcag == "1.4.3" or "color-contrast" in rule or "contrast" in rule:
        return "Design system color palette or theme tokens"

    # 🧱 Specific UI Component root causes
    if component in {"button", "buttons"} or "button" in rule:
        return "Design system button component"

    if component in {"form", "forms"} or "label" in rule:
        return "Design system form field component"

    if component == "navigation":
        return "Design system navigation component"

    if component in {"table", "tables"}:
        return "Design system table component"

    return None