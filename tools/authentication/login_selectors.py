"""
Login Selectors

A consolidated repository of CSS selectors utilized during the authentication flow.
These are primarily used as highly targeted fallbacks when heuristic scoring 
requires additional context (e.g., verifying if a user successfully logged in, 
detecting CAPTCHA traps, or locating multi-stage auth inputs).
"""

# Identifies bot-protection iframes and tags that break automated logins
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha' i]",
    "iframe[src*='hcaptcha' i]",
    "iframe[src*='turnstile' i]", # Cloudflare
    ".g-recaptcha",
    ".h-captcha",
    "[data-sitekey]",
    "[class*='captcha' i]",
    "[id*='captcha' i]",
]

# Identifies failed authentication attempts
LOGIN_ERROR_SELECTORS = [
    "[role='alert']",
    ".error",
    ".error-message",
    ".validation-error",
    "[class*='error' i]",
    "[id*='error' i]",
]

# Selectors that confirm a user is actively authenticated
LOGGED_IN_SELECTORS = [
    "a[href*='logout' i]",
    "button:has-text('Logout')",
    "button:has-text('Log out')",
    "a:has-text('Logout')",
    "a:has-text('Log out')",
    "[aria-label*='account' i]",
    "[data-testid*='account' i]",
]

# Selectors used to check if the header has transitioned to a logged-in account menu
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

# Menu items only visible inside an account dropdown when authenticated
LOGGED_IN_ACCOUNT_MENU_SELECTORS = [
    "a:has-text('Sign out')",
    "button:has-text('Sign out')",
    "a:has-text('Log out')",
    "button:has-text('Log out')",
    "a:has-text('Go to your account')",
    "button:has-text('Go to your account')",
]

# Stage 1 of a multi-stage login flow (e.g., "Enter email", then click Next)
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

# Stage 2 of a multi-stage login flow
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

# The final submission trigger
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