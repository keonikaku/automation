"""Product search: matching and non-matching terms."""

from __future__ import annotations

from playwright.sync_api import expect

from shopsmart.pages import ProductsPage

#: A string with no chance of matching a catalogue item.
NO_MATCH_TERM = "zzzznotaproduct"


def test_02_search(page, settings):
    """Search for a product — verify the results page displays matches."""
    products = ProductsPage(page, settings.base_url).open()
    products.search("dress")

    expect(products.results_heading).to_be_visible()
    assert products.result_count() > 0, "expected at least one result for 'dress'"


def test_10_search_no_results(page, settings):
    """Search a non-matching term — verify the results grid comes back empty.

    The 'Searched Products' heading renders whether or not anything matched, so
    asserting on the heading alone would pass even if the site returned the
    whole catalogue. The load-bearing assertion is the product-card count.
    """
    products = ProductsPage(page, settings.base_url).open()
    products.search(NO_MATCH_TERM)

    expect(products.results_heading).to_be_visible()
    assert products.result_count() == 0, (
        f"expected no results for {NO_MATCH_TERM!r}, "
        f"got {products.result_count()} product cards"
    )
