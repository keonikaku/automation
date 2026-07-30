"""Login / signup entry page (``/login``)."""

from __future__ import annotations

from playwright.sync_api import Locator

from shopsmart.pages.base_page import BasePage


class LoginPage(BasePage):
    """Carries both forms the site puts on ``/login``: sign in, and start signup."""

    PATH = "/login"

    EMAIL = "[data-qa='login-email']"
    PASSWORD = "[data-qa='login-password']"
    SUBMIT = "[data-qa='login-button']"

    SIGNUP_NAME = "[data-qa='signup-name']"
    SIGNUP_EMAIL = "[data-qa='signup-email']"
    SIGNUP_SUBMIT = "[data-qa='signup-button']"

    ERROR = "Your email or password is incorrect!"

    # ── sign in ───────────────────────────────────────────────────────
    def login(self, email: str, password: str):
        """Fill the sign-in form and submit it."""
        self.page.fill(self.EMAIL, email)
        self.page.fill(self.PASSWORD, password)
        return self.submit()

    def submit(self):
        """Submit the sign-in form as-is: used by the empty-fields test."""
        self.page.click(self.SUBMIT)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @property
    def error_message(self) -> Locator:
        return self.page.get_by_text(self.ERROR)

    # ── start signup ──────────────────────────────────────────────────
    def start_signup(self, name: str, email: str):
        """Submit the 'New User Signup!' form, landing on ``/signup``."""
        self.page.fill(self.SIGNUP_NAME, name)
        self.page.fill(self.SIGNUP_EMAIL, email)
        self.page.click(self.SIGNUP_SUBMIT)
        self.page.wait_for_load_state("domcontentloaded")
        from shopsmart.pages.signup_page import SignupPage

        return SignupPage(self.page, self.base_url)
