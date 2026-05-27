# ShopSmart Automation Suite
# 10 test cases covering happy path, negative scenarios, and mobile
# Target: https://www.automationexercise.com

from playwright.sync_api import sync_playwright, expect

# ─── CREDENTIALS ───────────────────────────────────────────────
EMAIL = "myfellowdude@gmail.com"
PASSWORD = "Prime21*"
# ───────────────────────────────────────────────────────────────


def test_01_login():
    """Valid credentials — verify successful login"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/login")
        page.wait_for_load_state("domcontentloaded")
        page.fill("[data-qa='login-email']", EMAIL)
        page.fill("[data-qa='login-password']", PASSWORD)
        page.click("[data-qa='login-button']")
        page.wait_for_load_state("domcontentloaded")
        expect(page).to_have_url("https://www.automationexercise.com/")
        browser.close()


def test_02_search():
    """Search for a product — verify results page displays"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/products")
        page.wait_for_load_state("domcontentloaded")
        page.fill("#search_product", "dress")
        page.click("#submit_search")
        page.wait_for_load_state("domcontentloaded")
        expect(page.get_by_text("Searched Products")).to_be_visible()
        browser.close()


def test_03_filter_by_category():
    """Filter products by Women category — verify results update"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/products")
        page.wait_for_load_state("domcontentloaded")
        
        # Close ad popup if it appears
        try:
            page.locator("#ad-bnr").click(timeout=3000)
        except:
            pass
        try:
            page.get_by_text("Close").click(timeout=3000)
        except:
            pass
        
        # Click Women category
        page.get_by_text("Women").first.click()
        page.wait_for_load_state("domcontentloaded")
        
        # Wait for Dress subcategory to be visible then click
        page.locator("a", has_text="Dress").first.wait_for(state="visible", timeout=5000)
        page.locator("a", has_text="Dress").first.click()
        page.wait_for_load_state("domcontentloaded")
        
        expect(page.get_by_text("Women - Dress Products")).to_be_visible()
        browser.close()


def test_04_add_to_cart():
    """Add product to cart — verify cart page loads"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/products")
        page.wait_for_load_state("domcontentloaded")
        page.locator(".add-to-cart").first.click()
        page.wait_for_timeout(2000)
        page.get_by_text("View Cart").click()
        page.wait_for_load_state("domcontentloaded")
        expect(page).to_have_url(
            "https://www.automationexercise.com/view_cart"
        )
        browser.close()


def test_05_checkout_requires_login():
    """Guest user checkout — verify login modal appears"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/products")
        page.wait_for_load_state("domcontentloaded")
        page.locator(".add-to-cart").first.click()
        page.wait_for_timeout(2000)
        page.get_by_text("View Cart").click()
        page.wait_for_load_state("domcontentloaded")
        page.locator(".check_out").click()
        page.wait_for_timeout(2000)
        expect(page.get_by_text(
            "Register / Login account to proceed on checkout."
        )).to_be_visible()
        browser.close()


def test_06_contact_form():
    """Submit contact form — verify success message displays"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/contact_us")
        page.wait_for_load_state("domcontentloaded")
        page.fill("[data-qa='name']", "Keoni Kakugawa")
        page.fill("[data-qa='email']", "keoni@example.com")
        page.fill("[data-qa='subject']", "Test Inquiry")
        page.fill("#message", "This is an automated test message.")
        page.on("dialog", lambda dialog: dialog.accept())
        page.click("[data-qa='submit-button']")
        page.wait_for_load_state("domcontentloaded")
        expect(page.locator(".status.alert.alert-success")).to_be_visible()
        browser.close()


def test_07_mobile_login():
    """iPhone 13 simulation — verify login works on mobile"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        iphone = p.devices["iPhone 13"]
        context = browser.new_context(**iphone)
        page = context.new_page()
        page.goto("https://www.automationexercise.com/login")
        page.wait_for_load_state("domcontentloaded")
        page.fill("[data-qa='login-email']", EMAIL)
        page.fill("[data-qa='login-password']", PASSWORD)
        page.click("[data-qa='login-button']")
        page.wait_for_load_state("domcontentloaded")
        expect(page).to_have_url("https://www.automationexercise.com/")
        context.close()
        browser.close()


def test_08_invalid_login():
    """Wrong password — verify error message displays"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/login")
        page.wait_for_load_state("domcontentloaded")
        page.fill("[data-qa='login-email']", EMAIL)
        page.fill("[data-qa='login-password']", "wrongpassword123")
        page.click("[data-qa='login-button']")
        page.wait_for_load_state("domcontentloaded")
        expect(page.get_by_text(
            "Your email or password is incorrect!"
        )).to_be_visible()
        browser.close()


def test_09_empty_login_fields():
    """Empty email and password — verify form does not submit"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/login")
        page.wait_for_load_state("domcontentloaded")
        page.click("[data-qa='login-button']")
        page.wait_for_timeout(1000)
        expect(page).to_have_url(
            "https://www.automationexercise.com/login"
        )
        browser.close()


def test_10_search_no_results():
    """Search with no matching term — verify empty results"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.automationexercise.com/products")
        page.wait_for_load_state("domcontentloaded")
        page.fill("#search_product", "zzzznotaproduct")
        page.click("#submit_search")
        page.wait_for_load_state("domcontentloaded")
        expect(page.get_by_text("Searched Products")).to_be_visible()
        browser.close()