def normalize_severity(raw_severity):
    if not raw_severity:
        return "Minor"

    s = raw_severity.lower()

    # Axe / AxeScan (already aligned)
    if s in ["critical", "serious", "moderate", "minor"]:
        return s

    # IBM Equal Access
    if s == "violation":
        return "serious"
    if s == "warning":
        return "warning"

    # HTMLSniffer
    if s == "error":
        return "serious"
    if s == "notice":
        return None  # 🚫 ignore completely

    # Lighthouse / Pa11y
    if s == "error":
        return "Serious"
    if s == "warning":
        return "Warning"

    return "minor"  # fallback