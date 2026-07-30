"""
Component Learning Engine

This module acts as a lightweight tracking database. It monitors incoming 
DOM patterns that the analyzer fails to recognize. If an unknown pattern 
appears frequently enough across the estate, the engine attempts to auto-guess 
its component type and saves it to a persistent JSON file for future runs.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LEARNING_FILE = BASE_DIR / "data" / "component_learning.json"
UNKNOWN_PATTERNS = defaultdict(int)

def load_learning() -> dict:
    if LEARNING_FILE.exists():
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_learning(data: dict) -> None:
    LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

def is_noisy_pattern(pattern: str) -> bool:
    """
    A filter to prevent the learning engine from filling up with useless junk.
    Blocks 32-character hashes, raw HTML snippets, and known tracking scripts.
    """
    if not pattern or not pattern.strip():
        return True
        
    p = pattern.lower()
    
    if re.match(r'^[a-f0-9]{32}$', p):
        return True
        
    if "<" in p or ">" in p or "=\"" in p:
        return True
        
    noise_keywords = ["beacon", "batbeacon", "tracking", "analytics", "nth-child", "alfa-opaque-node"]
    if any(k in p for k in noise_keywords):
        return True
        
    if re.search(r'\d{6,}', p):
        return True
        
    return False


LEARNING = load_learning()


def update_learning(pattern: str) -> None:
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


def auto_guess(pattern: str) -> str:
    """
    Heuristic fallback used to classify high-frequency unknown patterns 
    based on common CSS naming conventions.
    """
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