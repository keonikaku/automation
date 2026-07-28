"""Category browsing."""

from __future__ import annotations

from playwright.sync_api import expect

from shopsmart.pages import CategoryPage


def test_03_filter_by_category(page, settings):
    """Filter products by Women > Dress — verify the category page renders."""
    category = CategoryPage(page, settings.base_url).open()

    expect(category.heading).to_be_visible()
    assert category.current_url == category.url
