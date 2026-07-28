"""Shared page-object behaviour.

Every page object owns its own selectors. Tests call methods and read
properties; no test file contains a raw selector string. That boundary is the
whole point — when the practice site moves an element, exactly one file
changes.

The site header (login state, logout, delete account) is present on every
page, so it lives here rather than in a component nobody would remember to
instantiate.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from shopsmart.config import BASE_URL


class BasePage:
    """A page on the practice site."""

    #: Site-relative path this page is reachable at. ``""`` means the home page.
    PATH: str = ""

    def __init__(self, page: Page, base_url: str = BASE_URL) -> None:
        self.page = page
        self.base_url = base_url

    # ── navigation ────────────────────────────────────────────────────
    @property
    def url(self) -> str:
        """The absolute URL this page object navigates to."""
        return f"{self.base_url}{self.PATH}"

    def open(self):
        """Navigate to this page and wait for the DOM to be ready."""
        self.page.goto(self.url)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @property
    def current_url(self) -> str:
        return self.page.url

    # ── header, present on every page ─────────────────────────────────
    @property
    def logged_in_banner(self) -> Locator:
        """The header's 'Logged in as <name>' link."""
        return self.page.locator("a:has-text('Logged in as')")

    def is_logged_in(self) -> bool:
        return self.logged_in_banner.count() > 0

    def logout(self):
        self.page.click("a[href='/logout']")
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def delete_account(self):
        """Delete the currently logged-in account and confirm the site said so."""
        self.page.click("a[href='/delete_account']")
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @property
    def account_deleted_confirmation(self) -> Locator:
        return self.page.locator("[data-qa='account-deleted']")
