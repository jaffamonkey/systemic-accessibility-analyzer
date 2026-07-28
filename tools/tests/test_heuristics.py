import pytest
from playwright.sync_api import Page
from tools.authentication.heuristics import (
    USERNAME_WORDS,
    BAD_USERNAME_WORDS,
    _score_username,
    _score_password,
    _score_submit
)

# --- Regex Unit Tests ---

def test_username_regex_patterns():
    """Ensure the regex correctly identifies valid terms and ignores others."""
    assert USERNAME_WORDS.search("Email address") is not None
    assert USERNAME_WORDS.search("Member ID") is not None
    assert BAD_USERNAME_WORDS.search("Subscribe to our newsletter") is not None
    assert BAD_USERNAME_WORDS.search("Search for products") is not None

# --- DOM Scoring Unit Tests ---

def test_score_username_high_probability(page: Page):
    """Test that a clear email/username field scores highly."""
    page.set_content('''
        <label for="user_email">Email Address</label>
        <input type="email" id="user_email" name="email" autocomplete="username">
    ''')
    field = page.locator("#user_email")
    score = _score_username(page, field)
    
    # Should get points for type="email", autocomplete="username", and "email" in text
    assert score > 150

def test_score_username_penalizes_search_bars(page: Page):
    """Test that search and newsletter fields are heavily penalized."""
    page.set_content('''
        <label for="search">Search</label>
        <input type="text" id="search" placeholder="Search our site...">
    ''')
    field = page.locator("#search")
    score = _score_username(page, field)
    
    # The BAD_USERNAME_WORDS regex should heavily penalize this field
    assert score < 0

def test_score_password_standard_field(page: Page):
    """Test that a standard password field gets a high score."""
    page.set_content('''
        <label for="pwd">Password</label>
        <input type="password" id="pwd" autocomplete="current-password">
    ''')
    field = page.locator("#pwd")
    score = _score_password(page, field)
    
    # Should get points for type="password" and autocomplete="current-password"
    assert score > 200

def test_score_password_penalizes_new_password(page: Page):
    """Test that 'new-password' fields (like in resets) are penalized to prevent accidental updates."""
    page.set_content('''
        <label for="new_pwd">Create New Password</label>
        <input type="password" id="new_pwd" autocomplete="new-password">
    ''')
    field = page.locator("#new_pwd")
    score = _score_password(page, field)
    
    # The autocomplete="new-password" penalty should reduce the overall score
    standard_score = 150 + 50 # type="password" + PASSWORD_WORDS match
    assert score == standard_score - 80 

def test_score_submit_button(page: Page):
    """Test that login submit buttons are accurately scored."""
    page.set_content('''
        <button type="submit" class="login-btn">Log in</button>
    ''')
    button = page.locator("button")
    score = _score_submit(button)
    
    # Should get points for type="submit", tag="button", and SUBMIT_WORDS match
    assert score >= 170