"""
UUV Aliases
Maps UUV summary codes to the Systemic Analyzer's Canonical Rules.
"""

UUV_ALIASES = {
    # --- Elements ---
    "blank-buttons": "widget-name",
    "blank-links": "link-name",
    
    # 🔥 FIX: Matched exactly to the summary code generated in uuv.py
    "missing-label-inputs": "form-label",
    
    "images-missing-alt": "missing-alt",
    
    # --- Diagnostics & Noise ---
    "axe-violations": "summary",
    "failed-requests": "technical-noise",
    "console-noise": "technical-noise",
}