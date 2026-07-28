"""Contact Us form (``/contact_us``)."""

from __future__ import annotations

from playwright.sync_api import Locator

from shopsmart.pages.base_page import BasePage


class ContactPage(BasePage):
    PATH = "/contact_us"

    NAME = "[data-qa='name']"
    EMAIL = "[data-qa='email']"
    SUBJECT = "[data-qa='subject']"
    MESSAGE = "#message"
    SUBMIT = "[data-qa='submit-button']"
    SUCCESS = ".status.alert.alert-success"

    def submit_enquiry(self, name: str, email: str, subject: str, message: str):
        """Fill and submit the form, accepting the native confirm dialog.

        The dialog handler is registered before the click: Playwright blocks on
        an unhandled dialog, so registering it afterwards deadlocks the page.
        """
        self.page.fill(self.NAME, name)
        self.page.fill(self.EMAIL, email)
        self.page.fill(self.SUBJECT, subject)
        self.page.fill(self.MESSAGE, message)
        self.page.on("dialog", lambda dialog: dialog.accept())
        self.page.click(self.SUBMIT)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @property
    def success_message(self) -> Locator:
        return self.page.locator(self.SUCCESS)
