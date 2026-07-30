"""Page objects for automationexercise.com.

One class per page, each owning its own selectors. Tests never contain a raw
selector, when the site moves an element, exactly one file changes.
"""

from shopsmart.pages.base_page import BasePage
from shopsmart.pages.cart_page import CartPage
from shopsmart.pages.contact_page import ContactPage
from shopsmart.pages.login_page import LoginPage
from shopsmart.pages.products_page import CategoryPage, ProductsPage
from shopsmart.pages.signup_page import AccountDetails, SignupPage

__all__ = [
    "AccountDetails",
    "BasePage",
    "CartPage",
    "CategoryPage",
    "ContactPage",
    "LoginPage",
    "ProductsPage",
    "SignupPage",
]
