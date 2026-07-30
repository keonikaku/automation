"""Account-creation page (``/signup``).

Used only by the ``registered_account`` fixture. The suite creates the account
it needs at setup and deletes it at teardown, so no test depends on a
hand-made account surviving on a public practice site.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Locator

from shopsmart.pages.base_page import BasePage


@dataclass(frozen=True)
class AccountDetails:
    """The fields the practice site requires to create an account.

    All values are synthetic. Nothing here is, or resembles, real personal
    data: this is a throwaway account on a public practice site.
    """

    password: str
    first_name: str = "Test"
    last_name: str = "Account"
    address: str = "1 Example Street"
    country: str = "United States"
    state: str = "Test State"
    city: str = "Test City"
    zipcode: str = "00000"
    mobile: str = "5555550100"
    birth: tuple[str, str, str] = field(default=("1", "1", "2000"))


class SignupPage(BasePage):
    PATH = "/signup"

    TITLE = "Enter Account Information"
    GENDER = "#id_gender1"
    PASSWORD = "[data-qa='password']"
    DAYS = "[data-qa='days']"
    MONTHS = "[data-qa='months']"
    YEARS = "[data-qa='years']"
    FIRST_NAME = "[data-qa='first_name']"
    LAST_NAME = "[data-qa='last_name']"
    ADDRESS = "[data-qa='address']"
    COUNTRY = "[data-qa='country']"
    STATE = "[data-qa='state']"
    CITY = "[data-qa='city']"
    ZIPCODE = "[data-qa='zipcode']"
    MOBILE = "[data-qa='mobile_number']"
    CREATE = "[data-qa='create-account']"
    CREATED = "[data-qa='account-created']"
    CONTINUE = "[data-qa='continue-button']"

    @property
    def heading(self) -> Locator:
        return self.page.get_by_text(self.TITLE)

    @property
    def account_created_confirmation(self) -> Locator:
        return self.page.locator(self.CREATED)

    def create_account(self, details: AccountDetails):
        """Fill in every required field and submit."""
        day, month, year = details.birth
        self.page.check(self.GENDER)
        self.page.fill(self.PASSWORD, details.password)
        self.page.select_option(self.DAYS, day)
        self.page.select_option(self.MONTHS, month)
        self.page.select_option(self.YEARS, year)
        self.page.fill(self.FIRST_NAME, details.first_name)
        self.page.fill(self.LAST_NAME, details.last_name)
        self.page.fill(self.ADDRESS, details.address)
        self.page.select_option(self.COUNTRY, details.country)
        self.page.fill(self.STATE, details.state)
        self.page.fill(self.CITY, details.city)
        self.page.fill(self.ZIPCODE, details.zipcode)
        self.page.fill(self.MOBILE, details.mobile)
        self.page.click(self.CREATE)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def continue_to_site(self):
        """Dismiss the 'Account Created!' interstitial; leaves you logged in."""
        self.page.click(self.CONTINUE)
        self.page.wait_for_load_state("domcontentloaded")
        return BasePage(self.page, self.base_url)
