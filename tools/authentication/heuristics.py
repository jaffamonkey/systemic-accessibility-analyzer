"""
Authentication Heuristics

This module contains the probabilistic scoring engine used to identify 
login forms on unknown websites. Instead of relying on fragile, hardcoded 
CSS selectors, it evaluates DOM elements based on their type, autocomplete 
attributes, surrounding labels, and text content to "score" how likely they 
are to be username, password, or submit fields.
"""

from __future__ import annotations

import re
from typing import Iterable
from playwright.sync_api import Page, Locator

# --- Regex Patterns for Scoring ---
LOGIN_WORDS = re.compile(r"\b(log\s*in|login|sign\s*in|signin|my account|account)\b", re.I)
USERNAME_WORDS = re.compile(r"\b(email|e-mail|username|user name|login|account|member id|customer id)\b", re.I)
PASSWORD_WORDS = re.compile(r"\b(password|passcode|pwd)\b", re.I)
SUBMIT_WORDS = re.compile(r"\b(log\s*in|login|sign\s*in|signin|continue|next|submit)\b", re.I)

# Anti-patterns to prevent the engine from accidentally filling out newsletter or search bars
BAD_USERNAME_WORDS = re.compile(r"\b(search|newsletter|subscribe|postcode|zip|coupon|promo|voucher)\b", re.I)
BAD_SUBMIT_WORDS = re.compile(r"\b(search|subscribe|newsletter|cancel|close|back|register|sign up|create account)\b", re.I)

LOGIN_TRIGGER_SELECTORS = [
    "a:has-text('Login')",
    "a:has-text('Log in')",
    "a:has-text('Sign in')",
    "button:has-text('Login')",
    "button:has-text('Log in')",
    "button:has-text('Sign in')",
    "a[href*='login' i]",
    "a[href*='signin' i]",
    "a[href*='sign-in' i]",
    "a[href*='account' i]",
    "a[href*='auth' i]",
    "button[aria-label*='log in' i]",
    "a[aria-label*='log in' i]",
    "button[data-testid*='login' i]",
    ".login-button",
    "#login-button",
]


# -------------------------
# SAFE DOM EXTRACTORS
# -------------------------

def _safe_attr(locator: Locator, name: str) -> str:
    try:
        return locator.get_attribute(name) or ""
    except Exception:
        return ""


def _safe_text(locator: Locator) -> str:
    try:
        return locator.text_content(timeout=500) or ""
    except Exception:
        return ""


def _visible_enabled(locator: Locator) -> bool:
    try:
        return locator.is_visible(timeout=500) and locator.is_enabled(timeout=500)
    except Exception:
        return False


def _field_text(page: Page, field: Locator) -> str:
    """
    Builds a massive text blob containing all semantic clues about a field.
    Includes attributes, explicit <label> tags, wrapping labels, and immediate parents.
    """
    bits: list[str] = []

    for attr in [
        "id", "name", "type", "autocomplete", "placeholder",
        "aria-label", "data-testid", "data-test", "data-cy", "class",
    ]:
        bits.append(_safe_attr(field, attr))

    field_id = _safe_attr(field, "id")
    if field_id:
        try:
            label = page.locator(f"label[for='{field_id}']").first
            bits.append(_safe_text(label))
        except Exception:
            pass

    try:
        wrapping_label = field.locator("xpath=ancestor::label[1]").first
        bits.append(_safe_text(wrapping_label))
    except Exception:
        pass

    try:
        parent = field.locator("xpath=ancestor::*[self::div or self::p or self::li][1]").first
        bits.append(_safe_text(parent))
    except Exception:
        pass

    return " ".join(x.strip() for x in bits if x and x.strip())


# -------------------------
# PROBABILISTIC SCORING
# -------------------------

def _score_username(page: Page, field: Locator) -> int:
    """Scores how likely an input field is to be a Username/Email field."""
    if not _visible_enabled(field):
        return -999

    text = _field_text(page, field)
    field_type = _safe_attr(field, "type").lower()
    autocomplete = _safe_attr(field, "autocomplete").lower()

    score = 0

    if field_type == "email": score += 80
    elif field_type in {"text", ""}: score += 25
    else: score -= 20

    if autocomplete in {"username", "email"}: score += 100
    if USERNAME_WORDS.search(text): score += 70
    
    # Heavily penalize fields that look like newsletter signups
    if BAD_USERNAME_WORDS.search(text): score -= 120

    if "email" in text.lower(): score += 25
    if "username" in text.lower(): score += 25

    return score


def _score_password(page: Page, field: Locator) -> int:
    """Scores how likely an input field is to be a Password field."""
    if not _visible_enabled(field):
        return -999

    text = _field_text(page, field)
    field_type = _safe_attr(field, "type").lower()
    autocomplete = _safe_attr(field, "autocomplete").lower()

    score = 0

    if field_type == "password": score += 150
    if autocomplete in {"current-password", "password"}: score += 80
    if PASSWORD_WORDS.search(text): score += 50
    
    # Avoid accidentally entering the password into a "Change Password" reset field
    if autocomplete == "new-password": score -= 80

    return score


def _button_text(button: Locator) -> str:
    bits: list[str] = []
    bits.append(_safe_text(button))

    for attr in [
        "value", "aria-label", "title", "id", "name",
        "data-testid", "data-test", "data-cy", "class", "type",
    ]:
        bits.append(_safe_attr(button, attr))

    return " ".join(x.strip() for x in bits if x and x.strip())


def _score_submit(button: Locator) -> int:
    """Scores how likely a button is the actual Login submission trigger."""
    if not _visible_enabled(button):
        return -999

    text = _button_text(button)
    button_type = _safe_attr(button, "type").lower()
    tag = ""

    try:
        tag = button.evaluate("el => el.tagName.toLowerCase()")
    except Exception:
        pass

    score = 0

    if button_type == "submit": score += 70
    if tag == "button": score += 20
    if SUBMIT_WORDS.search(text): score += 80
    if BAD_SUBMIT_WORDS.search(text): score -= 120

    return score


# -------------------------
# REGION ISOLATION
# -------------------------

def _candidate_inputs(scope: Locator) -> list[Locator]:
    selector = (
        "input:not([type='hidden']):not([type='checkbox']):not([type='radio']):not([type='submit']), "
        "textarea, "
        "[contenteditable='true']"
    )
    try:
        loc = scope.locator(selector)
        return [loc.nth(i) for i in range(min(loc.count(), 30))]
    except Exception:
        return []


def _candidate_buttons(scope: Locator) -> list[Locator]:
    selector = (
        "button, "
        "input[type='submit'], "
        "input[type='button'], "
        "[role='button'], "
        "a:has-text('Log in'), "
        "a:has-text('Login'), "
        "a:has-text('Sign in'), "
        "a:has-text('Continue'), "
        "a:has-text('Next')"
    )
    try:
        loc = scope.locator(selector)
        return [loc.nth(i) for i in range(min(loc.count(), 30))]
    except Exception:
        return []


def _nearest_form_or_region(page: Page, field: Locator) -> Locator:
    """
    Prefers the actual <form> tag. If no form exists (common in React apps), 
    climbs the DOM tree to find a nearby dialog, modal, or container.
    """
    try:
        form = field.locator("xpath=ancestor::form[1]").first
        if form.count() > 0:
            return form
    except Exception:
        pass

    for xpath in [
        "xpath=ancestor::*[@role='dialog'][1]",
        "xpath=ancestor::*[contains(@class, 'modal')][1]",
        "xpath=ancestor::*[contains(@class, 'login') or contains(@class, 'signin') or contains(@class, 'auth')][1]",
        "xpath=ancestor::*[self::section or self::main or self::div][1]",
    ]:
        try:
            region = field.locator(xpath).first
            if region.count() > 0:
                return region
        except Exception:
            continue

    return page.locator("body")


def _best_submit(scope: Locator) -> Locator | None:
    scored: list[tuple[int, Locator]] = []
    for button in _candidate_buttons(scope):
        score = _score_submit(button)
        if score > 0:
            scored.append((score, button))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else None


# -------------------------
# FORM DETECTION ENGINES
# -------------------------

def detect_login_form(page: Page):
    """
    More robust than global first-match detection.
    Anchors to the highest-scoring password field, isolates that DOM region,
    and then hunts for the best username and submit button within that same region.
    Returns: username_locator, password_locator, submit_locator
    """
    password_candidates: list[tuple[int, Locator]] = []

    try:
        inputs = page.locator("input:not([type='hidden'])")
        for i in range(min(inputs.count(), 50)):
            field = inputs.nth(i)
            score = _score_password(page, field)
            if score > 0:
                password_candidates.append((score, field))
    except Exception:
        pass

    password_candidates.sort(key=lambda item: item[0], reverse=True)
    form_candidates: list[tuple[int, Locator, Locator, Locator]] = []

    for password_score, password in password_candidates:
        scope = _nearest_form_or_region(page, password)
        username_scored: list[tuple[int, Locator]] = []
        
        for field in _candidate_inputs(scope):
            try:
                # Skip checking the password field against itself
                if field.evaluate("(a, b) => a === b", password):
                    continue
            except Exception:
                pass

            score = _score_username(page, field)
            if score > 0:
                username_scored.append((score, field))

        username_scored.sort(key=lambda item: item[0], reverse=True)
        submit = _best_submit(scope)

        if username_scored and submit:
            username_score, username = username_scored[0]
            submit_score = _score_submit(submit)

            total = password_score + username_score + submit_score
            form_candidates.append((total, username, password, submit))

    form_candidates.sort(key=lambda item: item[0], reverse=True)

    if form_candidates:
        _, username, password, submit = form_candidates[0]
        return username, password, submit

    return None, None, None


def detect_login_trigger(page: Page):
    """Hunts for a 'Sign In' or 'Log In' link/button on the page before a form is visible."""
    scored: list[tuple[int, Locator]] = []

    selectors = [
        "a", "button", "[role='button']",
        "[aria-label*='login' i]", "[aria-label*='sign in' i]",
        "[data-testid*='login' i]", "[data-test*='login' i]",
    ]

    seen: set[str] = set()

    for selector in selectors:
        try:
            locators = page.locator(selector)
            for i in range(min(locators.count(), 40)):
                item = locators.nth(i)

                if not _visible_enabled(item):
                    continue

                text = _button_text(item)
                href = _safe_attr(item, "href")
                combined = f"{text} {href}".strip()

                if not combined:
                    continue

                key = combined.lower()
                if key in seen:
                    continue
                seen.add(key)

                score = 0

                if LOGIN_WORDS.search(combined): score += 100
                if re.search(r"/(login|signin|sign-in|account|auth)\b", href, re.I): score += 70
                if re.search(r"\b(register|sign up|basket|cart|search|menu)\b", combined, re.I): score -= 60

                if score > 0:
                    scored.append((score, item))
        except Exception:
            continue

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else None