import pytest
from playwright.sync_api import Page
from authentication.shared_login import (
    _has_captcha,
    _is_transient_auth_page,
    _has_login_error,
    _is_application_page
)
from tools.authentication.models import JobConfig

# --- Mock Configurations ---

@pytest.fixture
def mock_config():
    # A simplified mock of your JobConfig model
    class MockConfig(JobConfig):
        login_entry_url = "https://app.example.com/login"
        target_urls = ["https://app.example.com/dashboard"]
    return MockConfig()

# --- Security & Captcha Detection Tests ---

def test_has_captcha_via_text(page: Page):
    """Ensure text-based human verification screens are flagged."""
    page.set_content('''
        <body>
            <h1>Security Check</h1>
            <p>Please verify you are human before continuing.</p>
        </body>
    ''')
    assert _has_captcha(page) is True

def test_has_captcha_via_selector(page: Page, mocker):
    """Ensure standard CAPTCHA iframes (like reCAPTCHA) are flagged."""
    # Mocker allows us to inject our own list of selectors for testing
    mocker.patch('authentication.shared_login.CAPTCHA_SELECTORS', ['iframe[src*="recaptcha"]'])
    
    page.set_content('''
        <body>
            <form>
                <iframe src="https://www.google.com/recaptcha/api2/anchor"></iframe>
            </form>
        </body>
    ''')
    assert _has_captcha(page) is True

def test_no_captcha_on_clean_page(page: Page):
    """Ensure a standard login form does not trigger a false positive CAPTCHA flag."""
    page.set_content('''
        <body>
            <h1>Welcome Back</h1>
            <form>
                <input type="text" name="username">
                <input type="password" name="password">
            </form>
        </body>
    ''')
    assert _has_captcha(page) is False

# --- Transient & Error State Tests ---

def test_is_transient_auth_page_via_url(page: Page):
    """Ensure OAuth/SSO callback URLs are detected as transient states."""
    # We use route interception to mock the URL without actual navigation
    page.route("**/api/auth/callback/**", lambda route: route.fulfill(body="<html></html>"))
    page.goto("https://app.example.com/api/auth/callback/google")
    
    assert _is_transient_auth_page(page) is True

def test_is_transient_auth_page_via_text(page: Page):
    """Ensure IdP processing screens are detected as transient states."""
    page.set_content('''
        <body>
            <p>Redirecting to your identity provider, please wait...</p>
        </body>
    ''')
    assert _is_transient_auth_page(page) is True

def test_has_login_error_visible(page: Page, mocker):
    """Ensure visible login error messages are detected."""
    mocker.patch('authentication.shared_login.LOGIN_ERROR_SELECTORS', ['.error-msg'])
    
    page.set_content('''
        <body>
            <div class="error-msg" style="display: block;">Incorrect username or password. Try again.</div>
        </body>
    ''')
    assert _has_login_error(page) is True

# --- Verification Tests ---

def test_is_application_page_matches_host(page: Page, mock_config):
    """Ensure we can verify when the browser lands back on the expected application host."""
    page.route("**/dashboard", lambda route: route.fulfill(body="<html></html>"))
    page.goto("https://app.example.com/dashboard")
    
    # The current host matches the configured expected host (app.example.com)
    assert _is_application_page(page, mock_config) is True