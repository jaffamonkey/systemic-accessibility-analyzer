def detect_design_system_issue(cluster):
    rule = (cluster.get("ruleId") or "").lower()
    wcag = cluster.get("wcag")
    component = (cluster.get("component") or "").lower()

    if wcag == "1.4.3" or "color-contrast" in rule or "contrast" in rule:
        return "Design system color palette or theme tokens"

    if component in {"button", "buttons"} or "button" in rule:
        return "Design system button component"

    if component in {"form", "forms"} or "label" in rule:
        return "Design system form field component"

    if component == "navigation":
        return "Design system navigation component"

    if component in {"table", "tables"}:
        return "Design system table component"

    return None
