"""Contact Us form submission."""

from __future__ import annotations

from playwright.sync_api import expect

from shopsmart.pages import ContactPage


def test_06_contact_form(page, settings):
    """Submit the contact form: verify the success message displays."""
    contact = ContactPage(page, settings.base_url).open()
    contact.submit_enquiry(
        name="ShopSmart Test Account",
        email="shopsmart-suite@example.com",
        subject="Test Inquiry",
        message="This is an automated test message.",
    )

    expect(contact.success_message).to_be_visible()
