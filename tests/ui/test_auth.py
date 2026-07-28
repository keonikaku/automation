"""Authentication: valid login (desktop and mobile web) and negative paths.

Target: https://www.automationexercise.com
"""

from __future__ import annotations

from playwright.sync_api import expect

from shopsmart.pages import LoginPage

# Negative-path credentials are deliberately hardcoded and deliberately fake.
# Authenticating badly is the entire point of test_08, so it must not read a
# credential from anywhere: unset, the field's own required/type=email
# validation would block submit and the test would silently duplicate
# test_09; pointed at a real account, it would test a wrong password instead
# of an unknown user. Only a hardcoded unregistered address tests what the
# docstring says it tests. example.com is IANA-reserved and unregisterable.
UNREGISTERED_EMAIL = "nonexistent-user@example.com"
WRONG_PASSWORD = "wrongpassword123"


def test_01_login(page, registered_account, settings):
    """Valid credentials — verify successful login.

    The account is registered by the fixture at setup and deleted at teardown,
    so this test depends on nothing that exists before the run starts.
    """
    login_page = LoginPage(page, settings.base_url).open()
    login_page.login(registered_account.email, registered_account.password)

    expect(page).to_have_url(f"{settings.base_url}/")
    expect(login_page.logged_in_banner).to_contain_text(registered_account.name)


def test_07_mobile_login(mobile_page, registered_account, settings):
    """iPhone 13 emulation — verify login works on mobile web."""
    login_page = LoginPage(mobile_page, settings.base_url).open()
    login_page.login(registered_account.email, registered_account.password)

    expect(mobile_page).to_have_url(f"{settings.base_url}/")
    expect(login_page.logged_in_banner).to_contain_text(registered_account.name)


def test_08_invalid_login(page, settings):
    """Unregistered account — verify the incorrect-credentials error displays.

    Self-contained: uses a hardcoded fake address, no account required.
    """
    login_page = LoginPage(page, settings.base_url).open()
    login_page.login(UNREGISTERED_EMAIL, WRONG_PASSWORD)

    expect(login_page.error_message).to_be_visible()


def test_09_empty_login_fields(page, settings):
    """Empty email and password — verify the form does not submit."""
    login_page = LoginPage(page, settings.base_url).open()
    login_page.submit()

    page.wait_for_timeout(1000)
    expect(page).to_have_url(f"{settings.base_url}/login")
