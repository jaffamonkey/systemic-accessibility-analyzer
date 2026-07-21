from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, Locator

from authentication.heuristics import detect_login_form, detect_login_trigger
from authentication.models import AuthResult, JobConfig
from authentication.site_hints import KNOWN_SITE_HINTS


CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha' i]",
    "iframe[src*='hcaptcha' i]",
    "iframe[src*='turnstile' i]",
    ".g-recaptcha",
    ".h-captcha",
    "[data-sitekey]",
    "[class*='captcha' i]",
    "[id*='captcha' i]",
]

LOGIN_ERROR_SELECTORS = [
    "[role='alert']",
    ".error",
    ".error-message",
    ".validation-error",
    "[class*='error' i]",
    "[id*='error' i]",
]

LOGGED_IN_SELECTORS = [
    "a[href*='logout' i]",
    "button:has-text('Logout')",
    "button:has-text('Log out')",
    "a:has-text('Logout')",
    "a:has-text('Log out')",
    "[aria-label*='account' i]",
    "[data-testid*='account' i]",
]

ACCOUNT_MENU_BUTTON_SELECTORS = [
    "button[aria-label*='account' i]",
    "[role='button'][aria-label*='account' i]",
    "button[data-testid*='account' i]",
    "[role='button'][data-testid*='account' i]",
    "button[data-test*='account' i]",
    "[role='button'][data-test*='account' i]",
    "[class*='account' i] button",
    "button[class*='account' i]",
]

LOGGED_IN_ACCOUNT_MENU_SELECTORS = [
    "a:has-text('Sign out')",
    "button:has-text('Sign out')",
    "a:has-text('Log out')",
    "button:has-text('Log out')",
    "a:has-text('Go to your account')",
    "button:has-text('Go to your account')",
]

USERNAME_STAGE_SELECTORS = [
    "input[autocomplete='username']",
    "input[autocomplete='email']",
    "input[type='email']",
    "input[name*='email' i]",
    "input[id*='email' i]",
    "input[name*='username' i]",
    "input[id*='username' i]",
    "input[name*='user' i]",
    "input[id*='user' i]",
    "input[name*='login' i]",
    "input[id*='login' i]",
    "input[placeholder*='email' i]",
    "input[placeholder*='user' i]",
]

PASSWORD_STAGE_SELECTORS = [
    "input[autocomplete='current-password']",
    "input[type='password']",
    "input[name*='password' i]",
    "input[id*='password' i]",
    "input[name*='pass' i]",
    "input[id*='pass' i]",
    "input[placeholder*='password' i]",
    "input[placeholder*='pass' i]",
]

SUBMIT_STAGE_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Login')",
    "button:has-text('Log in')",
    "button:has-text('Sign in')",
    "button:has-text('Continue')",
    "button:has-text('Next')",
    "[role='button']:has-text('Login')",
    "[role='button']:has-text('Log in')",
    "[role='button']:has-text('Sign in')",
    "[role='button']:has-text('Continue')",
    "[role='button']:has-text('Next')",
    "form button:not([type='button'])",
]


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


def _first_visible(
    page: Page,
    selectors: list[str],
    *,
    timeout: int = 500,
) -> Locator | None:
    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if _is_visible(locator, timeout=timeout):
                return locator
        except Exception:
            continue

    return None


def _nearest_scope(page: Page, field: Locator) -> Locator:
    """
    Prefer the nearest actual form.

    Some React/Vue login components do not use a <form>, so fall back
    to a nearby dialog, modal-style container or the page body.
    """
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
    """
    Detect a username/email-only first stage.

    This covers modern login flows that initially show an email address
    field and a Next or Continue button, then reveal the password field.
    """
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
    """
    Detect common CAPTCHA implementations and obvious human-verification text.

    The script deliberately does not attempt to bypass CAPTCHA. A manual or
    guided login can be used to create storage_state.json instead.
    """
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
    """
    Verify login through the account-menu state.

    Some sites do not display a simple logged-in message after authentication.
    Instead, the header account button becomes active and exposes account-only
    actions such as "Sign out" or "Go to your account".

    The function checks visible state only. This matters because some sites,
    including M&S, may keep signed-in and signed-out menu content in the DOM
    while showing only the relevant version.
    """
    for selector in ACCOUNT_MENU_BUTTON_SELECTORS:
        try:
            account_button = page.locator(selector).first

            if not _is_visible(account_button, timeout=750):
                continue

            if not account_button.is_enabled(timeout=500):
                continue

            aria_expanded = (
                account_button.get_attribute("aria-expanded") or ""
            ).strip().lower()

            aria_pressed = (
                account_button.get_attribute("aria-pressed") or ""
            ).strip().lower()

            data_state = (
                account_button.get_attribute("data-state") or ""
            ).strip().lower()

            class_name = (
                account_button.get_attribute("class") or ""
            ).strip().lower()

            visibly_active = (
                aria_expanded == "true"
                or aria_pressed == "true"
                or data_state in {"active", "open", "opened", "expanded"}
                or re.search(r"\b(active|open|opened|expanded)\b", class_name)
            )

            if visibly_active:
                return True

            # The menu may be available but collapsed after navigation.
            # Open it and look for a visible logged-in-only menu action.
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
    """
    M&S signed-out state includes a specific account dropdown login link.

    After a successful login, that link is removed from the DOM rather than
    merely hidden. We therefore check whether the link still exists, not
    whether it is currently visible.
    """
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
    """
    Return True while authentication is still in progress.

    A missing password field is not sufficient proof of success. Redirect
    screens, identity-provider pages and anti-bot interstitials commonly
    remove the form before the user reaches the signed-in application.
    """
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
    """
    Confirm that the browser has returned to the configured application host.

    Use an exact host match so that an authentication subdomain cannot be
    mistaken for the completed application page.
    """
    current_host = (urlparse(page.url).hostname or "").lower()
    expected_host = (
        urlparse(config.login_entry_url).hostname or ""
    ).lower()

    return bool(
        current_host
        and expected_host
        and current_host == expected_host
    )

def _verify_authenticated_target(
    page: Page,
    config: JobConfig,
    *,
    log_lines: list[str],
) -> bool:
    """
    Verify that the saved browser context can reach an application page after
    authentication.

    This catches cases where credentials were accepted but the browser remains
    stuck on an identity-provider or anti-bot processing screen.
    """
    verification_url = (
        config.target_urls[0]
        if config.target_urls
        else config.login_entry_url
    )

    log_lines.append(
        f"Verifying authenticated application page: {verification_url}"
    )

    try:
        page.goto(
            verification_url,
            wait_until="domcontentloaded",
            timeout=15000,
        )
    except Exception as exc:
        log_lines.append(
            f"Verification navigation did not complete cleanly: {exc}"
        )

    page.wait_for_timeout(1500)

    if _is_transient_auth_page(page):
        log_lines.append(
            f"Verification still reached an authentication or "
            f"processing page: {page.url}"
        )
        return False

    if not _is_application_page(page, config):
        log_lines.append(
            f"Verification did not return to the application host: {page.url}"
        )
        return False

    if _has_login_error(page):
        log_lines.append(
            f"Verification page contains a login error: {page.url}"
        )
        return False

    log_lines.append(
        f"Authenticated application page verified at: {page.url}"
    )

    return True

def _is_successful(
    page: Page,
    config: JobConfig,
    *,
    log_lines: list[str] | None = None,
) -> bool:
    if _has_captcha(page):
        return False

    if _is_transient_auth_page(page):
        return False

    if not _is_application_page(page, config):
        return False

    if _has_login_error(page):
        return False

    if config.selectors.success:
        try:
            return _is_visible(
                page.locator(config.selectors.success).first,
                timeout=1500,
            )
        except Exception:
            return False

    if config.selectors.logged_in_text:
        try:
            return _is_visible(
                page.get_by_text(config.selectors.logged_in_text).first,
                timeout=1500,
            )
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

    return (
        password_gone
        and sign_in_link_gone
        and not login_error
    )

# def _is_successful(page: Page, config: JobConfig) -> bool:
#     if _has_captcha(page):
#         return False

#     if _has_login_error(page):
#         return False

#     if config.selectors.success:
#         try:
#             return _is_visible(
#                 page.locator(config.selectors.success).first,
#                 timeout=1500,
#             )
#         except Exception:
#             return False

#     if config.selectors.logged_in_text:
#         try:
#             return _is_visible(
#                 page.get_by_text(config.selectors.logged_in_text).first,
#                 timeout=1500,
#             )
#         except Exception:
#             return False

#     for selector in LOGGED_IN_SELECTORS:
#         try:
#             if _is_visible(page.locator(selector).first, timeout=750):
#                 return True
#         except Exception:
#             continue

#     try:
#         password_field = page.locator("input[type='password']").first
#         password_gone = not _is_visible(password_field, timeout=750)
#     except Exception:
#         password_gone = False

#     return password_gone and not _has_login_error(page)

def _wait_for_login_completion(
    page: Page,
    config: JobConfig,
    *,
    log_lines: list[str],
    timeout_ms: int = 45000,
    progress_screenshot_path: Path | None = None,
) -> bool:
    """
    Wait for login redirects to complete without hanging indefinitely.

    Progress is printed immediately as well as added to the saved log.
    If an anti-bot processing page does not clear within the timeout,
    return False so the caller can fail cleanly.
    """
    import time

    started_at = time.monotonic()
    deadline = started_at + (timeout_ms / 1000)
    next_heartbeat = started_at
    stable_success_checks = 0
    last_url = ""

    def report(message: str) -> None:
        log_lines.append(message)
        print(message, flush=True)

    report(
        f"Waiting up to {timeout_ms // 1000}s for login completion"
    )

    while time.monotonic() < deadline:
        current_url = page.url

        if current_url != last_url:
            report(
                "Authentication navigation: "
                f"{current_url[:240]}"
                f"{'...' if len(current_url) > 240 else ''}"
            )
            last_url = current_url

        if time.monotonic() >= next_heartbeat:
            elapsed = int(time.monotonic() - started_at)
            remaining = max(
                0,
                int(deadline - time.monotonic()),
            )

            report(
                f"Still waiting for login completion: "
                f"{elapsed}s elapsed, {remaining}s remaining"
            )

            if progress_screenshot_path is not None:
                try:
                    page.screenshot(
                        path=str(progress_screenshot_path),
                        full_page=True,
                    )
                except Exception:
                    pass

            next_heartbeat = time.monotonic() + 5

        if _has_captcha(page):
            report(
                "CAPTCHA or human-verification page detected"
            )

            return False

        if _is_transient_auth_page(page):
            stable_success_checks = 0
            page.wait_for_timeout(500)
            continue

        if _has_login_error(page):
            report(
                f"Login error detected at: {page.url}"
            )

            return False

        if _is_successful(page, config, log_lines=log_lines):
            stable_success_checks += 1

            report(
                f"Potential logged-in state detected "
                f"({stable_success_checks}/3): {page.url}"
            )

            if stable_success_checks >= 3:
                report(
                    f"Stable logged-in state confirmed at: {page.url}"
                )

                return True

        else:
            stable_success_checks = 0

        page.wait_for_timeout(500)

    final_url = page.url

    report(
        "Timed out waiting for login completion. Final URL: "
        f"{final_url[:240]}"
        f"{'...' if len(final_url) > 240 else ''}"
    )

    return False

def _find_login_triggers(page: Page) -> list[Locator]:
    selectors = [
        "a[href*='login' i]",
        "a[href*='signin' i]",
        "a[href*='sign-in' i]",
        "button",
        "a",
        "[role='button']",
        "[aria-label*='login' i]",
        "[aria-label*='sign in' i]",
        "[data-testid*='login' i]",
        "[data-test*='login' i]",
    ]

    matches: list[tuple[int, Locator]] = []
    seen: set[str] = set()

    for selector in selectors:
        try:
            locators = page.locator(selector)
            count = min(locators.count(), 25)

            for i in range(count):
                item = locators.nth(i)

                if not _is_visible(item, timeout=300):
                    continue

                text = (item.text_content() or "").strip().lower()
                aria = (item.get_attribute("aria-label") or "").strip().lower()
                href = (item.get_attribute("href") or "").strip().lower()

                combined = " ".join(x for x in [text, aria, href] if x)

                if not combined:
                    continue

                score = 0

                if text in {"login", "log in", "sign in", "signin", "sign-in"}:
                    score += 100

                if "login" in href or "signin" in href or "sign-in" in href:
                    score += 80

                if "login" in aria or "sign in" in aria or "signin" in aria:
                    score += 70

                if "login" in text or "sign in" in text or "signin" in text:
                    score += 60

                if "account" in text or "account" in aria:
                    score += 10

                if any(
                    blocked in combined
                    for blocked in [
                        "sign up",
                        "signup",
                        "register",
                        "registration",
                        "create account",
                        "create-an-account",
                    ]
                ):
                    score = -1000

                if score <= 0:
                    continue

                key = f"{selector}|{text}|{aria}|{href}"

                if key in seen:
                    continue

                seen.add(key)
                matches.append((score, item))

        except Exception:
            continue

    matches.sort(key=lambda x: x[0], reverse=True)

    return [item for _, item in matches[:5]]

def _login_ui_or_username_stage_is_visible(page: Page) -> bool:
    if _login_ui_is_visible(page):
        return True

    username_stage, username_submit = _find_username_stage(page)

    return bool(username_stage and username_submit)

def _login_ui_is_visible(page: Page) -> bool:
    """
    Return True only for a clear login form.

    A generic visible email field is not enough evidence: homepages commonly
    contain newsletter sign-up forms. Username-only multi-step login screens
    are handled separately after a login trigger has been followed.
    """
    username, password, submit = detect_login_form(page)

    return bool(username and password and submit)

def _cookie_contexts(page: Page):
    """
    Return the main page plus any frames.

    Some consent managers render their buttons inside iframes, so checking
    page.locator(...) alone is not enough.
    """
    contexts = [page]

    try:
        contexts.extend(page.frames)
    except Exception:
        pass

    return contexts


def _dismiss_cookie_banner(
    page: Page,
    *,
    log_lines: list[str],
) -> None:
    """
    Dismiss common cookie-consent overlays when present.

    These overlays can block otherwise valid login-link and submit-button
    clicks. Failure to dismiss is logged but does not stop the login flow.
    """
    selectors = [
        "#onetrust-reject-all-handler",
        "#onetrust-accept-btn-handler",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        "#didomi-notice-agree-button",
        "#truste-consent-button",

        "button:has-text('Reject all cookies')",
        "button:has-text('Accept all cookies')",
        "button:has-text('Accept all')",
        "button:has-text('Accept All')",
        "button:has-text('Confirm choices')",
        "button:has-text('I agree')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
        "button:has-text('Continue')",        
        "[aria-label*='Accept All' i]",

        "[role='button']:has-text('Accept all')",
        "[role='button']:has-text('Confirm choices')",
        "[role='button']:has-text('I agree')",
        "[role='button']:has-text('Agree')",
        "[role='button']:has-text('OK')",

        "input[type='submit'][value='Sounds good!']",
        "input[type='submit'][value*='Accept' i]",
        "input[type='submit'][value*='Agree' i]",
        "input[type='submit'][value*='OK' i]",
        "input[type='submit'][value*='Got it' i]",
        "input[type='submit'][value*='Sounds good' i]",
    ]

    # Try a couple of short passes because CMP dialogs often appear shortly
    # after the login form has already rendered.
    for attempt in range(3):
        for context in _cookie_contexts(page):
            context_url = getattr(context, "url", "")

            for selector in selectors:
                try:
                    button = context.locator(selector).first

                    if not _is_visible(button, timeout=500):
                        continue

                    button.click(timeout=3000)
                    page.wait_for_timeout(700)

                    log_lines.append(
                        "Dismissed cookie banner using selector: "
                        f"{selector}"
                        f"{f' in frame: {context_url}' if context is not page else ''}"
                    )

                    return

                except Exception:
                    continue

            role_patterns = [
                r"accept\s+all",
                r"accept",
                r"confirm\s+choices",
                r"agree",
                r"ok",
                r"got\s+it",
                r"continue",
                r"sounds\s+good",
            ]

            for pattern in role_patterns:
                try:
                    button = context.get_by_role(
                        "button",
                        name=re.compile(pattern, re.IGNORECASE),
                    ).first

                    if not _is_visible(button, timeout=500):
                        continue

                    button.click(timeout=3000)
                    page.wait_for_timeout(700)

                    log_lines.append(
                        "Dismissed cookie banner using button text pattern: "
                        f"{pattern}"
                        f"{f' in frame: {context_url}' if context is not page else ''}"
                    )

                    return

                except Exception:
                    continue

        if attempt < 2:
            page.wait_for_timeout(700)

    # Final fallback: remove obvious fixed/sticky consent overlays.
    # This is only used if no visible accept/confirm control can be clicked.
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
            log_lines.append(
                f"Removed {removed} cookie/consent overlay element(s)"
            )
            return

    except Exception as exc:
        log_lines.append(f"Cookie-overlay removal fallback failed: {exc}")

    log_lines.append("No dismissible cookie banner detected")

def _wait_for_login_ui(
    page: Page,
    *,
    timeout_ms: int = 8000,
    log_lines: list[str] | None = None,
) -> bool:
    """
    Wait for a genuine login form or a username-first login stage.

    Authentication redirects can take a moment to render after navigation.
    Without this wait, the script may continue looking for another login
    trigger and accidentally click a registration link.
    """
    elapsed = 0
    poll_ms = 250

    while elapsed < timeout_ms:
        if _login_ui_is_visible(page):
            if log_lines is not None:
                log_lines.append(
                    f"Detected complete login form at: {page.url}"
                )

            return True

        username_stage, username_submit = _find_username_stage(page)

        if username_stage and username_submit:
            if log_lines is not None:
                log_lines.append(
                    f"Detected username-first login stage at: {page.url}"
                )

            return True

        page.wait_for_timeout(poll_ms)
        elapsed += poll_ms

    if log_lines is not None:
        log_lines.append(
            f"Timed out waiting for login form at: {page.url}"
        )

    return False

def _open_login_ui(
    page: Page,
    *,
    trigger_selector: str | None,
    log_lines: list[str],
) -> str:
    if _login_ui_is_visible(page):
        log_lines.append("Login form already visible on landing page")
        return "direct_form"

    if trigger_selector:
        try:
            trigger = page.locator(trigger_selector).first

            if _is_visible(trigger, timeout=1500):
                before_url = page.url

                log_lines.append(
                    f"Clicking configured login trigger: {trigger_selector}"
                )

                trigger.click()

                try:
                    page.wait_for_url(
                        lambda url: str(url) != before_url,
                        timeout=8000,
                    )
                except Exception:
                    pass

                page.wait_for_timeout(500)

                if page.url != before_url:
                    log_lines.append(
                        "Configured login trigger changed URL: "
                        f"{before_url} -> {page.url}"
                    )
                else:
                    log_lines.append(
                        "Configured login trigger did not change URL; "
                        "checking for modal or inline form"
                    )

                if _wait_for_login_ui(
                    page,
                    timeout_ms=8000,
                    log_lines=log_lines,
                ):
                    return "login_trigger_override"

        except Exception as exc:
            log_lines.append(
                f"Configured login trigger failed: {exc}"
            )

    try:
        trigger = detect_login_trigger(page)

        if trigger:
            before_url = page.url

            log_lines.append(
                "Trying heuristic login trigger"
            )

            trigger.click()

            try:
                page.wait_for_url(
                    lambda url: str(url) != before_url,
                    timeout=8000,
                )
            except Exception:
                pass

            page.wait_for_timeout(500)

            if page.url != before_url:
                log_lines.append(
                    f"Heuristic trigger changed URL: "
                    f"{before_url} -> {page.url}"
                )
            else:
                log_lines.append(
                    "Heuristic trigger did not change URL; "
                    "checking for modal or inline form"
                )

            if _wait_for_login_ui(
                page,
                timeout_ms=8000,
                log_lines=log_lines,
            ):
                return "login_link_or_modal"

    except Exception as exc:
        log_lines.append(
            f"Heuristic trigger click failed: {exc}"
        )

    for idx, trigger in enumerate(
        _find_login_triggers(page),
        start=1,
    ):
        try:
            before_url = page.url
            text = (trigger.text_content() or "").strip()
            href = trigger.get_attribute("href") or ""

            combined = f"{text} {href}".lower()

            if any(
                blocked in combined
                for blocked in [
                    "sign up",
                    "signup",
                    "register",
                    "registration",
                    "create account",
                    "create-an-account",
                ]
            ):
                log_lines.append(
                    f"Skipping registration candidate {idx}: "
                    f"text={text!r} href={href!r}"
                )

                continue

            log_lines.append(
                f"Trying login candidate {idx}: "
                f"text={text!r} href={href!r}"
            )

            trigger.click()

            try:
                page.wait_for_url(
                    lambda url: str(url) != before_url,
                    timeout=8000,
                )
            except Exception:
                pass

            page.wait_for_timeout(500)

            if page.url != before_url:
                log_lines.append(
                    f"Candidate {idx} changed URL: "
                    f"{before_url} -> {page.url}"
                )
            else:
                log_lines.append(
                    f"Candidate {idx} did not change URL; "
                    "checking for modal or inline form"
                )

            if _wait_for_login_ui(
                page,
                timeout_ms=8000,
                log_lines=log_lines,
            ):
                return "login_link_or_modal"

        except Exception as exc:
            log_lines.append(
                f"Candidate {idx} failed: {exc}"
            )

            continue

    raise RuntimeError(
        "Could not detect login trigger or login form"
    )

def _click_or_press_enter(
    field: Locator,
    submit_button: Locator | None,
    *,
    log_lines: list[str],
    stage_name: str,
) -> None:
    if submit_button and _is_visible(submit_button, timeout=500):
        try:
            submit_button.click()
            log_lines.append(f"Clicked {stage_name} submit/continue button")
            return
        except Exception as exc:
            log_lines.append(
                f"Could not click {stage_name} submit button: {exc}; "
                "pressing Enter instead"
            )

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
    """
    Fill and submit either:

    1. A normal username + password form.
    2. A multi-step username -> Next -> password form.
    """
    username_input.fill(username)
    log_lines.append("Filled username/email field")

    if password_input and _is_visible(password_input, timeout=500):
        password_input.fill(password)
        log_lines.append("Filled password field on single-stage login form")

        _dismiss_cookie_banner(
            page,
            log_lines=log_lines,
        )

        _click_or_press_enter(
            password_input,
            submit_button,
            log_lines=log_lines,
            stage_name="login",
        )

        return

    log_lines.append(
        "Password field is not visible yet; treating login as a multi-step flow"
    )

    _dismiss_cookie_banner(
        page,
        log_lines=log_lines,
    )

    _click_or_press_enter(
        username_input,
        submit_button,
        log_lines=log_lines,
        stage_name="username",
    )

    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass

    page.wait_for_timeout(750)

    if _has_captcha(page):
        raise RuntimeError(
            "CAPTCHA detected after username submission. "
            "Automated login cannot continue. "
            "Use manual or guided login and save storage_state.json."
        )

    _, detected_password, detected_submit = detect_login_form(page)

    if not detected_password:
        detected_password, detected_submit = _find_password_stage(page)

    if not detected_password:
        raise RuntimeError(
            "Username was submitted, but a password field did not appear"
        )

    detected_password.fill(password)
    log_lines.append("Filled password field on second stage of login flow")

    _dismiss_cookie_banner(
        page,
        log_lines=log_lines,
    )

    _click_or_press_enter(
        detected_password,
        detected_submit,
        log_lines=log_lines,
        stage_name="password",
    )


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
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(config.timeout_ms)

        try:
            log_lines.append(
                f"Opening login entry URL: {config.login_entry_url}"
            )

            page.goto(
                config.login_entry_url,
                wait_until="domcontentloaded",
            )

            page.wait_for_timeout(500)

            _dismiss_cookie_banner(
                page,
                log_lines=log_lines,
            )

            if _has_captcha(page):
                raise RuntimeError(
                    "CAPTCHA detected before login. "
                    "Automated login cannot continue. "
                    "Use manual or guided login and save storage_state.json."
                )

            username_selector = (
                config.selectors.username
                or getattr(hint, "username", None)
            )

            password_selector = (
                config.selectors.password
                or getattr(hint, "password", None)
            )

            submit_selector = (
                config.selectors.submit
                or getattr(hint, "submit", None)
            )

            trigger_selector = (
                config.selectors.login_trigger
                or getattr(hint, "login_trigger", None)
            )

            method = _open_login_ui(
                page,
                trigger_selector=trigger_selector,
                log_lines=log_lines,
            )

            _dismiss_cookie_banner(
                page,
                log_lines=log_lines,
            )

            if _has_captcha(page):
                raise RuntimeError(
                    "CAPTCHA detected on login form. "
                    "Automated login cannot continue. "
                    "Use manual or guided login and save storage_state.json."
                )

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

            if username_input:
                log_lines.append(
                    "Using configured/hinted username selector"
                )

                if password_input:
                    log_lines.append(
                        "Using configured/hinted password selector"
                    )

                if submit_button:
                    log_lines.append(
                        "Using configured/hinted submit selector"
                    )

            if not username_input:
                detected_username, detected_password, detected_submit = (
                    detect_login_form(page)
                )

                if detected_username:
                    username_input = detected_username
                    password_input = password_input or detected_password
                    submit_button = submit_button or detected_submit

                    log_lines.append(
                        "Using heuristic single-stage login form detection"
                    )

            if not username_input:
                username_input, username_stage_submit = (
                    _find_username_stage(page)
                )

                submit_button = submit_button or username_stage_submit

                if username_input:
                    log_lines.append(
                        "Using heuristic username-first login detection"
                    )

            if not username_input:
                raise RuntimeError(
                    "Could not detect username or email field"
                )

            if not submit_button:
                submit_button = _find_submit_for_field(
                    page,
                    username_input,
                )

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
                page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=10000,
                )
            except Exception:
                pass

            page.wait_for_timeout(1500)

            if _has_captcha(page):
                raise RuntimeError(
                    "CAPTCHA detected after login submission. "
                    "Automated login cannot continue. "
                    "Use manual or guided login and save storage_state.json."
                )

            if not _wait_for_login_completion(
                page,
                config,
                log_lines=log_lines,
                timeout_ms=config.auth_completion_timeout_ms,
                progress_screenshot_path=screenshot_path,
            ):
                raise RuntimeError(
                    "Login submitted but a stable logged-in state "
                    "could not be verified"
                )

            if not _verify_authenticated_target(
                page,
                config,
                log_lines=log_lines,
            ):
                raise RuntimeError(
                    "Credentials were submitted, but the authenticated application "
                    "page could not be verified"
                )
            context.storage_state(path=str(storage_state_path))
            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )

            log_lines.append(
                f"Saved storage state: {storage_state_path}"
            )

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
                page.screenshot(
                    path=str(screenshot_path),
                    full_page=True,
                )
            except Exception:
                pass

            _write_log(
                log_path,
                log_lines + [f"ERROR: {exc}"],
            )

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