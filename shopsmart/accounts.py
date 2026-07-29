"""Throwaway account creation on the practice site.

The valid-login tests used to depend on one hand-made account. When that
account was deleted the tests died, and nobody else could run them. Everything
that needs an account now creates its own and deletes it afterwards.

This lives in the framework rather than in ``tests/conftest.py`` because two
callers need it: the ``registered_account`` fixture, and the walkthrough
recorder in ``demo/``. One implementation means the video cannot drift from
what the suite actually does.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from playwright.sync_api import BrowserContext, Page

from shopsmart.config import BASE_URL
from shopsmart.pages import AccountDetails, BasePage, LoginPage

#: Every account this suite creates is named this, so a human looking at the
#: practice site's data can tell where it came from.
ACCOUNT_NAME = "ShopSmart Test Account"


@dataclass(frozen=True)
class Account:
    """Credentials for a throwaway account this run created."""

    name: str
    email: str
    password: str


def new_credentials(prefix: str = "shopsmart-suite") -> Account:
    """Generate unique, obviously-synthetic credentials.

    ``example.com`` is IANA-reserved and cannot receive mail, so a generated
    address can never collide with a real person's.
    """
    token = uuid.uuid4().hex[:12]
    return Account(
        name=ACCOUNT_NAME,
        email=f"{prefix}-{token}@example.com",
        password=f"Sh0pSmart-{token}",
    )


def register(context: BrowserContext, base_url: str = BASE_URL) -> tuple[Account, Page]:
    """Create an account in ``context`` and return it with its logged-in page.

    The returned page is left authenticated so the caller can hand it back to
    :func:`delete` at teardown. Callers that want the account tested from a
    logged-out browser should pass a context of their own — contexts do not
    share cookies, which is what makes that isolation free.
    """
    account = new_credentials()
    page = context.new_page()

    login_page = LoginPage(page, base_url).open()
    signup_page = login_page.start_signup(account.name, account.email)
    signup_page.create_account(AccountDetails(password=account.password))
    signup_page.continue_to_site()

    return account, page


def delete(page: Page, base_url: str = BASE_URL) -> None:
    """Delete the account the given page is logged in as."""
    BasePage(page, base_url).delete_account()
