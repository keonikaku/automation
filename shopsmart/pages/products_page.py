"""Product listing, search results, and category pages."""

from __future__ import annotations

from playwright.sync_api import Locator

from shopsmart.config import BASE_URL
from shopsmart.pages.base_page import BasePage


class ProductsPage(BasePage):
    PATH = "/products"

    SEARCH_INPUT = "#search_product"
    SEARCH_SUBMIT = "#submit_search"
    RESULTS_HEADING = "Searched Products"

    #: One card per matching product inside the results grid. Counting these is
    #: how the suite tells "results returned" from "no results": the heading
    #: renders either way, so asserting on the heading alone proves nothing.
    RESULT_CARDS = ".features_items .product-image-wrapper"

    ADD_TO_CART = ".add-to-cart"
    VIEW_CART = "View Cart"

    def search(self, term: str):
        self.page.fill(self.SEARCH_INPUT, term)
        self.page.click(self.SEARCH_SUBMIT)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @property
    def results_heading(self) -> Locator:
        return self.page.get_by_text(self.RESULTS_HEADING)

    @property
    def result_cards(self) -> Locator:
        return self.page.locator(self.RESULT_CARDS)

    def result_count(self) -> int:
        """How many product cards the results grid is showing."""
        return self.result_cards.count()

    def add_first_product_to_cart(self):
        """Add the first listed product, then follow the modal into the cart."""
        self.page.locator(self.ADD_TO_CART).first.click()
        # The confirmation modal animates in; it has no stable ready-state hook.
        self.page.wait_for_timeout(2000)
        self.page.get_by_text(self.VIEW_CART).click()
        self.page.wait_for_load_state("domcontentloaded")
        from shopsmart.pages.cart_page import CartPage

        return CartPage(self.page, self.base_url)


class CategoryPage(BasePage):
    """A category listing, e.g. Women > Dress.

    Navigated to directly rather than through the sidebar: the practice site
    serves interstitial ads over the category links, and clicking through them
    was testing the ad network rather than the site.
    """

    #: Women > Dress on the practice site.
    WOMEN_DRESS_ID = 1
    WOMEN_DRESS_HEADING = "Women - Dress Products"

    def __init__(self, page, base_url: str = BASE_URL, category_id: int = WOMEN_DRESS_ID):
        super().__init__(page, base_url)
        self.category_id = category_id

    @property
    def url(self) -> str:
        return f"{self.base_url}/category_products/{self.category_id}"

    @property
    def heading(self) -> Locator:
        return self.page.get_by_text(self.WOMEN_DRESS_HEADING)
