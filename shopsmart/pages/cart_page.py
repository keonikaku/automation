"""Shopping cart page (``/view_cart``)."""

from __future__ import annotations

from playwright.sync_api import Locator

from shopsmart.pages.base_page import BasePage


class CartPage(BasePage):
    PATH = "/view_cart"

    CHECKOUT = ".check_out"
    LOGIN_PROMPT = "Register / Login account to proceed on checkout."

    def proceed_to_checkout(self):
        self.page.locator(self.CHECKOUT).click()
        # The prompt is a Bootstrap modal with a fade transition and no
        # network round-trip to wait on.
        self.page.wait_for_timeout(2000)
        return self

    @property
    def login_required_prompt(self) -> Locator:
        """Modal shown when a guest tries to check out."""
        return self.page.get_by_text(self.LOGIN_PROMPT)
