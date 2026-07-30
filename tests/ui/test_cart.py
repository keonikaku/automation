"""Cart and guest checkout."""

from __future__ import annotations

from playwright.sync_api import expect

from shopsmart.pages import ProductsPage


def test_04_add_to_cart(page, settings):
    """Add a product to the cart: verify the cart page loads."""
    products = ProductsPage(page, settings.base_url).open()
    cart = products.add_first_product_to_cart()

    expect(page).to_have_url(cart.url)


def test_05_checkout_requires_login(page, settings):
    """Guest checkout: verify the register/login prompt appears."""
    products = ProductsPage(page, settings.base_url).open()
    cart = products.add_first_product_to_cart()
    cart.proceed_to_checkout()

    expect(cart.login_required_prompt).to_be_visible()
