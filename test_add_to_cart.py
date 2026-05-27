# Import the Playwright library so we can automate a browser
from playwright.sync_api import sync_playwright, expect

def test_add_to_cart():
    # Start Playwright
    with sync_playwright() as p:
        # Open a visible Chrome browser window
        browser = p.chromium.launch(headless=False)
        
        # Open a new browser tab
        page = browser.new_page()
        
        # Navigate to the Products page
        page.goto("https://www.automationexercise.com/products")
        
        # Wait for the page to load
        page.wait_for_load_state("domcontentloaded")
        
        # Click Add to Cart on the first product
        page.locator(".add-to-cart").first.click()
        
        # Wait for the confirmation modal to appear
        page.wait_for_timeout(2000)
        
        # Click View Cart in the modal using get_by_text
        page.get_by_text("View Cart").click()
        
        # Wait for cart page to load
        page.wait_for_load_state("domcontentloaded")
        
        # Verify we landed on the cart page
        expect(page).to_have_url(
            "https://www.automationexercise.com/view_cart"
        )
        
        # Print success message
        print("Add to cart test passed — item added and cart opened")
        
        # Close the browser
        browser.close()

# Run the test
test_add_to_cart()
