from collections import defaultdict
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LEARNING_FILE = BASE_DIR / "data" / "component_learning.json"
UNKNOWN_PATTERNS = defaultdict(int)


def load_learning():
    if LEARNING_FILE.exists():
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_learning(data):
    LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

import re

def is_noisy_pattern(pattern):
    if not pattern:
        return True
        
    p = pattern.lower()
    
    # 1. Catch 32-character hex hashes (MD5s)
    if re.match(r'^[a-f0-9]{32}$', p):
        return True
        
    # 2. Catch raw HTML fragments (look for brackets or attribute equals)
    if "<" in p or ">" in p or "=\"" in p:
        return True
        
    # 3. Catch the JS-identified noise
    noise_keywords = ["beacon", "batbeacon", "tracking", "analytics", "nth-child", "alfa-opaque-node"]
    if any(k in p for k in noise_keywords):
        return True
        
    # 4. Long number sequences
    if re.search(r'\d{6,}', p):
        return True
        
    return False

LEARNING = load_learning()


def update_learning(pattern):
    if not pattern or pattern == "frame":
        return
    
    if is_noisy_pattern(pattern):
        return

    UNKNOWN_PATTERNS[pattern] += 1

    if pattern not in LEARNING:
        LEARNING[pattern] = {
            "count": 0,
            "component": None,
            "confidence": 0.0,
        }

    LEARNING[pattern]["count"] += 1

    if LEARNING[pattern]["count"] >= 20 and not LEARNING[pattern]["component"]:
        LEARNING[pattern]["component"] = auto_guess(pattern)
        LEARNING[pattern]["confidence"] = 0.7


def auto_guess(pattern):
    p = pattern.lower()

    if any(x in p for x in ["col", "grid", "row", "large-", "small-", "medium-"]):
        return "grid"
    if any(x in p for x in ["nav", "menu", "footer", "header"]):
        return "navigation"
    if any(x in p for x in ["btn", "button", "cta"]):
        return "button"
    if any(x in p for x in ["form", "input", "field"]):
        return "form"
    if any(x in p for x in ["text", "title", "label"]):
        return "text"

    return "other"
