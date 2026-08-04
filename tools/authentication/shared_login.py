"""
Authentication Runner

The orchestration engine for automated logins via Playwright. 
This script handles the entire lifecycle: dismissing cookie banners, 
locating the login trigger, navigating 1-step vs. 2-step login flows, 
bypassing transient Identity Provider (IdP) screens, and securely 
saving the final session state to a storage file.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, Locator

from authentication.heuristics import detect_login_form, detect_login_trigger
from authentication.models import AuthResult, JobConfig
from authentication.site_hints import KNOWN_SITE_HINTS
from authentication.login_selectors import (
    CAPTCHA_SELECTORS, 
    LOGIN_ERROR_SELECTORS, 
    LOGGED_IN_SELECTORS, 
    ACCOUNT_MENU_BUTTON_SELECTORS, 
    LOGGED_IN_ACCOUNT_MENU_SELECTORS, 
    USERNAME_STAGE_SELECTORS, 
    PASSWORD_STAGE_SELECTORS, 
    SUBMIT_STAGE_SELECTORS
)


def _login_ui_or_username_stage_is_visible(page: Page) -> bool:
    if _login_ui_is_visible(page):
        return True
    username_stage, username_submit = _find_username_stage(page)
    return bool(username_stage and username_submit)


def _login_ui_is_visible(page: Page) -> bool:
    """Return True only for a clear, complete login form."""
    username, password, submit = detect_login_form(page)
    return bool(username and password and submit)

def _write_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _hint_for_domain(url: str):
    host = urlparse(url).hostname or ""
    for hint in KNOWN_SITE_HINTS:
        if host.endswith(hint.domain):
            return hint
    return None


def _is_visible(locator: Locator | None, timeout: int = 1500) -> bool:
    if locator is None:
        return False
    try:
        locator.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


def _first_visible(page: Page, selectors: list[str], *, timeout: int = 500) -> Locator | None:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if _is_visible(locator, timeout=timeout):
                return locator
        except Exception:
            continue
    return None


def _nearest_scope(page: Page, field: Locator) -> Locator:
    scope_selectors = [
        "xpath=ancestor::form[1]",
        "xpath=ancestor::*[@role='dialog'][1]",
        "xpath=ancestor::*[contains(@class, 'modal')][1]",
        (
            "xpath=ancestor::*["
            "contains(@class, 'login') or "
            "contains(@class, 'signin') or "
            "contains(@class, 'auth')"
            "][1]"
        ),
    ]

    for selector in scope_selectors:
        try:
            scope = field.locator(selector).first
            if scope.count() > 0:
                return scope
        except Exception:
            continue

    return page.locator("body")


def _find_submit_for_scope(scope: Locator) -> Locator | None:
    for selector in SUBMIT_STAGE_SELECTORS:
        try:
            locator = scope.locator(selector).first
            if _is_visible(locator, timeout=500):
                return locator
        except Exception:
            continue
    return None


def _find_submit_for_field(page: Page, field: Locator) -> Locator | None:
    scope = _nearest_scope(page, field)
    submit = _find_submit_for_scope(scope)
    if submit:
        return submit
    return _first_visible(page, SUBMIT_STAGE_SELECTORS, timeout=500)


def _find_username_stage(page: Page) -> tuple[Locator | None, Locator | None]:
    username_input = _first_visible(page, USERNAME_STAGE_SELECTORS, timeout=500)
    if not username_input:
        return None, None

    submit_button = _find_submit_for_field(page, username_input)
    return username_input, submit_button


def _find_password_stage(page: Page) -> tuple[Locator | None, Locator | None]:
    password_input = _first_visible(page, PASSWORD_STAGE_SELECTORS, timeout=750)
    if not password_input:
        return None, None

    submit_button = _find_submit_for_field(page, password_input)
    return password_input, submit_button


def _has_captcha(page: Page) -> bool:
    for selector in CAPTCHA_SELECTORS:
        try:
            if _is_visible(page.locator(selector).first, timeout=500):
                return True
        except Exception:
            continue

    try:
        body_text = page.locator("body").inner_text(timeout=1000)
        return bool(
            re.search(
                r"captcha|recaptcha|hcaptcha|verify you are human|"
                r"prove you are human|are you human|human verification",
                body_text,
                re.IGNORECASE,
            )
        )
    except Exception:
        return False


def _has_login_error(page: Page) -> bool:
    for selector in LOGIN_ERROR_SELECTORS:
        try:
            locator = page.locator(selector).first
            if not _is_visible(locator, timeout=500):
                continue

            text = (locator.text_content() or "").strip()
            if re.search(
                r"invalid|incorrect|required|failed|try again|"
                r"not recognised|not recognized|unable to log|"
                r"wrong password|authentication failed",
                text,
                re.IGNORECASE,
            ):
                return True
        except Exception:
            continue
    return False


def _has_active_account_menu(page: Page) -> bool:
    for selector in ACCOUNT_MENU_BUTTON_SELECTORS:
        try:
            account_button = page.locator(selector).first
            if not _is_visible(account_button, timeout=750):
                continue
            if not account_button.is_enabled(timeout=500):
                continue

            aria_expanded = (account_button.get_attribute("aria-expanded") or "").strip().lower()
            aria_pressed = (account_button.get_attribute("aria-pressed") or "").strip().lower()
            data_state = (account_button.get_attribute("data-state") or "").strip().lower()
            class_name = (account_button.get_attribute("class") or "").strip().lower()

            visibly_active = (
                aria_expanded == "true"
                or aria_pressed == "true"
                or data_state in {"active", "open", "opened", "expanded"}
                or re.search(r"\b(active|open|opened|expanded)\b", class_name)
            )

            if visibly_active:
                return True

            try:
                account_button.click()
                page.wait_for_timeout(300)
            except Exception:
                continue

            for menu_selector in LOGGED_IN_ACCOUNT_MENU_SELECTORS:
                try:
                    menu_item = page.locator(menu_selector).first
                    if _is_visible(menu_item, timeout=500):
                        return True
                except Exception:
                    continue
        except Exception:
            continue
    return False


def _sign_in_link_has_disappeared(page: Page) -> bool:
    selectors = [
        "a[href*='MSResLogin']",
        "a[href*='header_sign-in_sign-in']",
        "a[href*='myAcctMain=1']",
    ]

    for selector in selectors:
        try:
            if page.locator(selector).count() > 0:
                return False
        except Exception:
            continue
    return True


def _is_transient_auth_page(page: Page) -> bool:
    current_url = page.url.lower()

    transient_url_fragments = [
        "akamai-challenge-resubmit=true",
        "/api/auth/callback/",
        "bridge.ciam.",
        "auth.ciam.",
        "/login?",
        "/authorize?",
        "/oauth",
        "/sso/",
    ]

    if any(fragment in current_url for fragment in transient_url_fragments):
        return True

    try:
        body_text = page.locator("body").inner_text(timeout=1000)
    except Exception:
        body_text = ""

    transient_text_patterns = [
        r"processing your request",
        r"doesn['’]t refresh automatically",
        r"resubmit your request",
        r"powered and protected by\s+akamai",
        r"please wait",
        r"redirecting",
    ]

    return any(
        re.search(pattern, body_text, re.IGNORECASE)
        for pattern in transient_text_patterns
    )


def _is_application_page(page: Page, config: JobConfig) -> bool:
    current_host = (urlparse(page.url).hostname or "").lower()
    expected_host = (urlparse(config.login_entry_url).hostname or "").lower()

    return bool(
        current_host
        and expected_host
        and current_host == expected_host
    )


def _verify_authenticated_target(page: Page, config: JobConfig, *, log_lines: list[str]) -> bool:
    verification_url = (
        config.target_urls[0]
        if config.target_urls
        else config.login_entry_url
    )

    log_lines.append(f"Verifying authenticated application page: {verification_url}")

    try:
        page.goto(verification_url, wait_until="domcontentloaded", timeout=15000)
    except Exception as exc:
        log_lines.append(f"Verification navigation did not complete cleanly: {exc}")

    page.wait_for_timeout(1500)

    if _is_transient_auth_page(page):
        log_lines.append(f"Verification still reached an authentication or processing page: {page.url}")
        return False

    if not _is_application_page(page, config):
        log_lines.append(f"Verification did not return to the application host: {page.url}")
        return False

    if _has_login_error(page):
        log_lines.append(f"Verification page contains a login error: {page.url}")
        return False

    log_lines.append(f"Authenticated application page verified at: {page.url}")
    return True


def _is_successful(page: Page, config: JobConfig, *, log_lines: list[str] | None = None) -> bool:
    if _has_captcha(page) or _is_transient_auth_page(page) or not _is_application_page(page, config) or _has_login_error(page):
        return False

    if config.selectors.success:
        try:
            return _is_visible(page.locator(config.selectors.success).first, timeout=1500)
        except Exception:
            return False

    if config.selectors.logged_in_text:
        try:
            return _is_visible(page.get_by_text(config.selectors.logged_in_text).first, timeout=1500)
        except Exception:
            return False

    if _has_active_account_menu(page):
        return True

    for selector in LOGGED_IN_SELECTORS:
        try:
            if _is_visible(page.locator(selector).first, timeout=750):
                return True
        except Exception:
            continue

    try:
        password_field = page.locator("input[type='password']").first
        password_gone = not _is_visible(password_field, timeout=750)
    except Exception:
        password_gone = False

    sign_in_link_gone = _sign_in_link_has_disappeared(page)
    login_error = _has_login_error(page)

    if log_lines is not None:
        log_lines.append(
            "Fallback success check: "
            f"password_gone={password_gone}, "
            f"sign_in_link_gone={sign_in_link_gone}, "
            f"login_error={login_error}"
        )

    return password_gone and sign_in_link_gone and not login_error


def _wait_for_login_completion(
    page: Page,
    config: JobConfig,
    *,
    log_lines: list[str],
    timeout_ms: int = 45000,
    progress_screenshot_path: Path | None = None,
) -> bool:
    started_at = time.monotonic()
    deadline = started_at + (timeout_ms / 1000)
    next_heartbeat = started_at
    stable_success_checks = 0
    last_url = ""

    def report(message: str) -> None:
        log_lines.append(message)
        print(message, flush=True)

    report(f"Waiting up to {timeout_ms // 1000}s for login completion")

    while time.monotonic() < deadline:
        current_url = page.url

        if current_url != last_url:
            report(f"Authentication navigation: {current_url[:240]}{'...' if len(current_url) > 240 else ''}")
            last_url = current_url

        if time.monotonic() >= next_heartbeat:
            elapsed = int(time.monotonic() - started_at)
            remaining = max(0, int(deadline - time.monotonic()))
            report(f"Still waiting for login completion: {elapsed}s elapsed, {remaining}s remaining")

            if progress_screenshot_path is not None:
                try:
                    page.screenshot(path=str(progress_screenshot_path), full_page=True)
                except Exception:
                    pass

            next_heartbeat = time.monotonic() + 5

        if _has_captcha(page):
            report("CAPTCHA or human-verification page detected")
            return False

        if _is_transient_auth_page(page):
            stable_success_checks = 0
            page.wait_for_timeout(500)
            continue

        if _has_login_error(page):
            report(f"Login error detected at: {page.url}")
            return False

        if _is_successful(page, config, log_lines=log_lines):
            stable_success_checks += 1
            report(f"Potential logged-in state detected ({stable_success_checks}/3): {page.url}")

            if stable_success_checks >= 3:
                report(f"Stable logged-in state confirmed at: {page.url}")
                return True
        else:
            stable_success_checks = 0

        page.wait_for_timeout(500)

    final_url = page.url
    report(f"Timed out waiting for login completion. Final URL: {final_url[:240]}{'...' if len(final_url) > 240 else ''}")
    return False


def _find_login_triggers(page: Page) -> list[Locator]:
    # FIX: Adding >> visible=true to let the browser engine do the filtering natively
    selectors = [
        "a[href*='login' i] >> visible=true", "a[href*='signin' i] >> visible=true", "a[href*='sign-in' i] >> visible=true",
        "button >> visible=true", "a >> visible=true", "[role='button'] >> visible=true",
        "[aria-label*='login' i] >> visible=true", "[aria-label*='sign in' i] >> visible=true",
        "[data-testid*='login' i] >> visible=true", "[data-test*='login' i] >> visible=true",
    ]

    matches: list[tuple[int, Locator]] = []
    seen: set[str] = set()

    for selector in selectors:
        try:
            locators = page.locator(selector)
            count = min(locators.count(), 25)

            for i in range(count):
                item = locators.nth(i)
                
                # FIX: Instantaneous check without a timeout argument
                try:
                    if not item.is_visible(): 
                        continue
                except Exception:
                    continue

                text = (item.text_content() or "").strip().lower()
                aria = (item.get_attribute("aria-label") or "").strip().lower()
                href = (item.get_attribute("href") or "").strip().lower()

                combined = " ".join(x for x in [text, aria, href] if x)
                if not combined: continue

                score = 0

                if text in {"login", "log in", "sign in", "signin", "sign-in"}: score += 100
                if "login" in href or "signin" in href or "sign-in" in href: score += 80
                if "login" in aria or "sign in" in aria or "signin" in aria: score += 70
                if "login" in text or "sign in" in text or "signin" in text: score += 60
                if "account" in text or "account" in aria: score += 10

                if any(blocked in combined for blocked in ["sign up", "signup", "register", "registration", "create account", "create-an-account"]):
                    score = -1000

                if score <= 0: continue

                key = f"{selector}|{text}|{aria}|{href}"
                if key in seen: continue

                seen.add(key)
                matches.append((score, item))

        except Exception:
            continue

    matches.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in matches[:5]]


def _cookie_contexts(page: Page):
    contexts = [page]
    try:
        contexts.extend(page.frames)
    except Exception:
        pass
    return contexts


def _dismiss_cookie_banner(page: Page, *, log_lines: list[str]) -> None:
    # FIX: Consolidate CSS selectors and text selectors for a single bulk query
    css_selectors = [
        "#onetrust-reject-all-handler", "#onetrust-accept-btn-handler",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        "#didomi-notice-agree-button", "#truste-consent-button",
        "button:has-text('Reject all cookies')", "button:has-text('Accept all cookies')",
        "button:has-text('Accept all')", "button:has-text('Accept All')",
        "button:has-text('Confirm choices')", "button:has-text('I agree')",
        "button:has-text('Agree')", "button:has-text('OK')",
        "button:has-text('Got it')", "button:has-text('Continue')",        
        "[aria-label*='Accept All' i]",
        "[role='button']:has-text('Accept all')", "[role='button']:has-text('Confirm choices')",
        "[role='button']:has-text('I agree')", "[role='button']:has-text('Agree')",
        "[role='button']:has-text('OK')",
        "input[type='submit'][value='Sounds good!']", "input[type='submit'][value*='Accept' i]",
        "input[type='submit'][value*='Agree' i]", "input[type='submit'][value*='OK' i]",
        "input[type='submit'][value*='Got it' i]", "input[type='submit'][value*='Sounds good' i]",
    ]
    
    combined_selector = ", ".join(css_selectors)

    for attempt in range(3):
        for context in _cookie_contexts(page):
            context_url = getattr(context, "url", "")
            
            # Fire one massive query for all explicit CSS checks
            try:
                button = context.locator(combined_selector).first
                if button.is_visible(timeout=500):
                    button.click(timeout=3000)
                    page.wait_for_timeout(700)
                    log_lines.append(f"Dismissed cookie banner using combined CSS selectors{f' in frame: {context_url}' if context is not page else ''}")
                    return
            except Exception:
                pass

            # Fallback regex patterns
            role_patterns = [
                r"accept\s+all", r"accept", r"confirm\s+choices", r"agree",
                r"ok", r"got\s+it", r"continue", r"sounds\s+good",
            ]

            for pattern in role_patterns:
                try:
                    button = context.get_by_role("button", name=re.compile(pattern, re.IGNORECASE)).first
                    if button.is_visible(timeout=500): 
                        button.click(timeout=3000)
                        page.wait_for_timeout(700)
                        log_lines.append(f"Dismissed cookie banner using button text pattern: {pattern}{f' in frame: {context_url}' if context is not page else ''}")
                        return
                except Exception:
                    continue

        if attempt < 2:
            page.wait_for_timeout(700)

    try:
        removed = page.evaluate(
            """
            () => {
                const keywordRe = /(cookie|consent|gdpr|privacy|cmp|onetrust|trustarc|didomi|cookiebot|qc-cmp|sp_message_container)/i;
                let removedCount = 0;

                for (const el of Array.from(document.querySelectorAll('body *'))) {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    const text = (el.textContent || '').slice(0, 500);
                    const idClass = `${el.id || ''} ${(el.className || '').toString()}`;
                    const attrs = `${el.getAttribute('aria-label') || ''} ${el.getAttribute('role') || ''}`;

                    const keywordMatch = keywordRe.test(idClass) || keywordRe.test(text) || keywordRe.test(attrs);
                    const overlayish = style.position === 'fixed' || style.position === 'sticky';
                    const highZ = style.zIndex === '2147483647' || (!Number.isNaN(Number(style.zIndex)) && Number(style.zIndex) >= 999);
                    const largeEnough = rect.width >= window.innerWidth * 0.3 || rect.height >= window.innerHeight * 0.15;

                    if (keywordMatch && (overlayish || highZ) && largeEnough) {
                        el.remove();
                        removedCount += 1;
                    }
                }

                document.documentElement.style.overflow = '';
                document.body.style.overflow = '';
                return removedCount;
            }
            """
        )
        if removed:
            page.wait_for_timeout(500)
            log_lines.append(f"Removed {removed} cookie/consent overlay element(s)")
            return
    except Exception as exc:
        log_lines.append(f"Cookie-overlay removal fallback failed: {exc}")

    log_lines.append("No dismissible cookie banner detected")


def _wait_for_login_ui(page: Page, *, timeout_ms: int = 8000, log_lines: list[str] | None = None) -> bool:
    # FIX: Replaced the artificial loop counter with a real-time system clock monitor
    start_time = time.monotonic()
    deadline = start_time + (timeout_ms / 1000.0)
    poll_ms = 250

    while time.monotonic() < deadline:
        if _login_ui_is_visible(page):
            if log_lines is not None: log_lines.append(f"Detected complete login form at: {page.url}")
            return True

        username_stage, username_submit = _find_username_stage(page)
        if username_stage and username_submit:
            if log_lines is not None: log_lines.append(f"Detected username-first login stage at: {page.url}")
            return True

        page.wait_for_timeout(poll_ms)

    if log_lines is not None:
        log_lines.append(f"Timed out waiting for login form at: {page.url}")

    return False


def _open_login_ui(page: Page, *, trigger_selector: str | None, log_lines: list[str]) -> str:
    if _login_ui_is_visible(page):
        log_lines.append("Login form already visible on landing page")
        return "direct_form"

    if trigger_selector:
        try:
            trigger = page.locator(trigger_selector).first
            if _is_visible(trigger, timeout=1500):
                before_url = page.url
                log_lines.append(f"Clicking configured login trigger: {trigger_selector}")
                trigger.click()

                try:
                    page.wait_for_url(lambda url: str(url) != before_url, timeout=8000)
                except Exception:
                    pass

                page.wait_for_timeout(500)
                if page.url != before_url:
                    log_lines.append(f"Configured login trigger changed URL: {before_url} -> {page.url}")
                else:
                    log_lines.append("Configured login trigger did not change URL; checking for modal or inline form")

                if _wait_for_login_ui(page, timeout_ms=8000, log_lines=log_lines):
                    return "login_trigger_override"
        except Exception as exc:
            log_lines.append(f"Configured login trigger failed: {exc}")

    try:
        trigger = detect_login_trigger(page)
        if trigger:
            before_url = page.url
            log_lines.append("Trying heuristic login trigger")
            trigger.click()

            try:
                page.wait_for_url(lambda url: str(url) != before_url, timeout=8000)
            except Exception:
                pass

            page.wait_for_timeout(500)
            if page.url != before_url:
                log_lines.append(f"Heuristic trigger changed URL: {before_url} -> {page.url}")
            else:
                log_lines.append("Heuristic trigger did not change URL; checking for modal or inline form")

            if _wait_for_login_ui(page, timeout_ms=8000, log_lines=log_lines):
                return "login_link_or_modal"
    except Exception as exc:
        log_lines.append(f"Heuristic trigger click failed: {exc}")

    for idx, trigger in enumerate(_find_login_triggers(page), start=1):
        try:
            before_url = page.url
            text = (trigger.text_content() or "").strip()
            href = trigger.get_attribute("href") or ""
            combined = f"{text} {href}".lower()

            if any(blocked in combined for blocked in ["sign up", "signup", "register", "registration", "create account"]):
                log_lines.append(f"Skipping registration candidate {idx}: text={text!r} href={href!r}")
                continue

            log_lines.append(f"Trying login candidate {idx}: text={text!r} href={href!r}")
            trigger.click()

            try:
                page.wait_for_url(lambda url: str(url) != before_url, timeout=8000)
            except Exception:
                pass

            page.wait_for_timeout(500)
            if page.url != before_url:
                log_lines.append(f"Candidate {idx} changed URL: {before_url} -> {page.url}")
            else:
                log_lines.append(f"Candidate {idx} did not change URL; checking for modal or inline form")

            if _wait_for_login_ui(page, timeout_ms=8000, log_lines=log_lines):
                return "login_link_or_modal"
        except Exception as exc:
            log_lines.append(f"Candidate {idx} failed: {exc}")
            continue

    raise RuntimeError("Could not detect login trigger or login form")


def _click_or_press_enter(field: Locator, submit_button: Locator | None, *, log_lines: list[str], stage_name: str) -> None:
    if submit_button and _is_visible(submit_button, timeout=500):
        try:
            submit_button.click()
            log_lines.append(f"Clicked {stage_name} submit/continue button")
            return
        except Exception as exc:
            log_lines.append(f"Could not click {stage_name} submit button: {exc}; pressing Enter instead")

    field.press("Enter")
    log_lines.append(f"Pressed Enter on {stage_name} field")


def _fill_and_submit_login(
    page: Page,
    *,
    username_input: Locator,
    password_input: Locator | None,
    submit_button: Locator | None,
    username: str,
    password: str,
    log_lines: list[str],
) -> None:
    username_input.fill(username)
    log_lines.append("Filled username/email field")

    if password_input and _is_visible(password_input, timeout=500):
        password_input.fill(password)
        log_lines.append("Filled password field on single-stage login form")
        _dismiss_cookie_banner(page, log_lines=log_lines)
        _click_or_press_enter(password_input, submit_button, log_lines=log_lines, stage_name="login")
        return

    log_lines.append("Password field is not visible yet; treating login as a multi-step flow")
    _dismiss_cookie_banner(page, log_lines=log_lines)
    _click_or_press_enter(username_input, submit_button, log_lines=log_lines, stage_name="username")

    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass

    page.wait_for_timeout(750)

    if _has_captcha(page):
        raise RuntimeError("CAPTCHA detected after username submission. Automated login cannot continue.")

    _, detected_password, detected_submit = detect_login_form(page)
    if not detected_password:
        detected_password, detected_submit = _find_password_stage(page)

    if not detected_password:
        raise RuntimeError("Username was submitted, but a password field did not appear")

    detected_password.fill(password)
    log_lines.append("Filled password field on second stage of login flow")
    _dismiss_cookie_banner(page, log_lines=log_lines)
    _click_or_press_enter(detected_password, detected_submit, log_lines=log_lines, stage_name="password")


# -------------------------
# MAIN EXECUTION ENTRYPOINT
# -------------------------

def run_shared_login(config: JobConfig, job_dir: Path) -> AuthResult:
    auth_dir = job_dir / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)

    storage_state_path = auth_dir / "storage_state.json"
    screenshot_path = auth_dir / "login-result.png"
    log_path = auth_dir / "login.log"
    log_lines: list[str] = []

    hint = _hint_for_domain(config.login_entry_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.headless)
        context = browser.new_context(
            timezone_id="Europe/London",
            locale="en-GB",
            viewport={"width": 1280, "height": 720} 
        )
        page = context.new_page()
        page.set_default_timeout(config.timeout_ms)

        try:
            log_lines.append(f"Opening login entry URL: {config.login_entry_url}")
            page.goto(config.login_entry_url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            
            _dismiss_cookie_banner(page, log_lines=log_lines)

            if _has_captcha(page):
                raise RuntimeError("CAPTCHA detected before login. Automated login cannot continue.")

            username_selector = config.selectors.username or getattr(hint, "username", None)
            password_selector = config.selectors.password or getattr(hint, "password", None)
            submit_selector = config.selectors.submit or getattr(hint, "submit", None)
            trigger_selector = config.selectors.login_trigger or getattr(hint, "login_trigger", None)

            method = _open_login_ui(page, trigger_selector=trigger_selector, log_lines=log_lines)
            _dismiss_cookie_banner(page, log_lines=log_lines)

            if _has_captcha(page):
                raise RuntimeError("CAPTCHA detected on login form. Automated login cannot continue.")

            username_input: Locator | None = None
            password_input: Locator | None = None
            submit_button: Locator | None = None

            if username_selector:
                configured_username = page.locator(username_selector).first
                if _is_visible(configured_username, timeout=1000):
                    username_input = configured_username

            if password_selector:
                configured_password = page.locator(password_selector).first
                if _is_visible(configured_password, timeout=1000):
                    password_input = configured_password

            if submit_selector:
                configured_submit = page.locator(submit_selector).first
                if _is_visible(configured_submit, timeout=1000):
                    submit_button = configured_submit

            if not username_input:
                detected_username, detected_password, detected_submit = detect_login_form(page)
                if detected_username:
                    username_input = detected_username
                    password_input = password_input or detected_password
                    submit_button = submit_button or detected_submit
                    log_lines.append("Using heuristic single-stage login form detection")

            if not username_input:
                username_input, username_stage_submit = _find_username_stage(page)
                submit_button = submit_button or username_stage_submit
                if username_input:
                    log_lines.append("Using heuristic username-first login detection")

            if not username_input:
                raise RuntimeError("Could not detect username or email field")

            if not submit_button:
                submit_button = _find_submit_for_field(page, username_input)

            _fill_and_submit_login(
                page,
                username_input=username_input,
                password_input=password_input,
                submit_button=submit_button,
                username=config.credentials.username,
                password=config.credentials.password,
                log_lines=log_lines,
            )

            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

            page.wait_for_timeout(1500)

            if _has_captcha(page):
                raise RuntimeError("CAPTCHA detected after login submission. Automated login cannot continue.")

            if not _wait_for_login_completion(
                page,
                config,
                log_lines=log_lines,
                timeout_ms=config.auth_completion_timeout_ms,
                progress_screenshot_path=screenshot_path,
            ):
                raise RuntimeError("Login submitted but a stable logged-in state could not be verified")

            if not _verify_authenticated_target(page, config, log_lines=log_lines):
                raise RuntimeError("Credentials were submitted, but the authenticated application page could not be verified")
                
            context.storage_state(path=str(storage_state_path))
            page.screenshot(path=str(screenshot_path), full_page=True)

            log_lines.append(f"Saved storage state: {storage_state_path}")
            _write_log(log_path, log_lines)

            return AuthResult(
                True,
                method,
                page.url,
                storage_state_path,
                screenshot_path,
                log_path,
                "Login successful",
            )

        except Exception as exc:
            print(f"ERROR: {exc}", flush=True)
            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pass

            _write_log(log_path, log_lines + [f"ERROR: {exc}"])

            return AuthResult(
                False,
                "failed",
                page.url,
                None,
                screenshot_path if screenshot_path.exists() else None,
                log_path,
                str(exc),
            )

        finally:
            context.close()
            browser.close()