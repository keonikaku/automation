# Import the Playwright library so we can automate a browser
from playwright.sync_api import sync_playwright, expect

def test_mobile_login():
    # Start Playwright
    with sync_playwright() as p:
        # Open a visible Chrome browser window
        browser = p.chromium.launch(headless=False)
        
        # Load iPhone 13 device settings
        iphone = p.devices["iPhone 13"]
        
        # Create a browser context with iPhone 13 settings applied
        # This sets the screen size, user agent, and touch support
        context = browser.new_context(**iphone)
        
        # Open a new page inside the iPhone context
        page = context.new_page()
        
        # Navigate to the login page
        page.goto("https://www.automationexercise.com/login")
        
        # Wait for the page to load
        page.wait_for_load_state("domcontentloaded")
        
        # Fill in the email field
        page.fill("[data-qa='login-email']", "myfellowdude@gmail.com")
        
        # Fill in the password field
        page.fill("[data-qa='login-password']", "Prime21*")
        
        # Click the Login button
        page.click("[data-qa='login-button']")
        
        # Wait for the page to load after login
        page.wait_for_load_state("domcontentloaded")
        
        # Verify the user is logged in by checking the URL
        expect(page).to_have_url("https://www.automationexercise.com/")
        
        # Print success message
        print("Mobile login test passed — iPhone 13 simulation")
        
        # Close the context and browser
        context.close()
        browser.close()

