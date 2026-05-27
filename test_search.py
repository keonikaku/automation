# Import the Playwright library so we can automate a browser
from playwright.sync_api import sync_playwright, expect

def test_search():
    # Start Playwright
    with sync_playwright() as p:
        # Open a visible Chrome browser window
        browser = p.chromium.launch(headless=False)
        
        # Open a new browser tab
        page = browser.new_page()
        
        # Navigate to the Products page where the search bar lives
        page.goto("https://www.automationexercise.com/products")
        
        # Find the search input field and type a search term
        page.fill("#search_product", "dress")
        
        # Click the Search button
        page.click("#submit_search")
        
        # Wait for the page to load after search
        page.wait_for_load_state("domcontentloaded")
        
        # Verify the search results page is displayed
        expect(page).to_have_url(
            "https://www.automationexercise.com/products?search=dress"
        )
        
        # Print a success message in the terminal
        print("Search test passed — results page displayed")
        
        # Close the browser
        browser.close()

