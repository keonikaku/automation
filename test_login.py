# Import the Playwright library so we can automate a browser
from playwright.sync_api import sync_playwright, expect

def test_login():
    # Start Playwright
    with sync_playwright() as p:
        # Open a visible Chrome browser window
        browser = p.chromium.launch(headless=False)
        
        # Open a new browser tab
        page = browser.new_page()
        
        # Navigate to the automationexercise.com login page
        page.goto("https://www.automationexercise.com/login")
        
        # Find the email field and type your email address
        page.fill("[data-qa='login-email']", "myfellowdude@gmail.com")
        
        # Find the password field and type your password
        page.fill("[data-qa='login-password']", "Prime21*")
        
        # Click the Login button
        page.click("[data-qa='login-button']")
        
        # Wait for the page to load after login
        page.wait_for_load_state("networkidle")
        
        # Verify the user is logged in by checking the URL
        # After login the site redirects to the homepage
        expect(page).to_have_url("https://www.automationexercise.com/")
        
        # Print a success message in the terminal
        print("Login test passed — user is logged in")
        
        # Close the browser
        browser.close()

