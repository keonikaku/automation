# Import the Playwright library so we can automate a browser
from playwright.sync_api import sync_playwright, expect

def test_contact_form():
    # Start Playwright
    with sync_playwright() as p:
        # Open a visible Chrome browser window
        browser = p.chromium.launch(headless=False)
        
        # Open a new browser tab
        page = browser.new_page()
        
        # Navigate to the Contact Us page
        page.goto("https://www.automationexercise.com/contact_us")
        
        # Wait for the page to load
        page.wait_for_load_state("domcontentloaded")
        
        # Fill in the Name field
        page.fill("[data-qa='name']", "Keoni Kakugawa")
        
        # Fill in the Email field
        page.fill("[data-qa='email']", "keoni@example.com")
        
        # Fill in the Subject field
        page.fill("[data-qa='subject']", "Test Inquiry")
        
        # Fill in the Message field
        page.fill("#message", "This is an automated test message.")
        
        # Handle the browser alert BEFORE clicking submit
        page.on("dialog", lambda dialog: dialog.accept())
        
        # Click the Submit button
        page.click("[data-qa='submit-button']")
        
        # Wait for the page to load after submission
        page.wait_for_load_state("domcontentloaded")
        
        # Verify success message is visible
        expect(page.locator(".status.alert.alert-success")).to_be_visible()
        
        # Print success message
        print("Contact form test passed — form submitted successfully")
        
        # Close the browser
        browser.close()

