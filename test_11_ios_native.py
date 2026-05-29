from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
import time

def test_ios_navigation():
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.device_name = "iPhone 17"
    options.udid = "D51307BC-09B7-4558-99FE-593747EB8D5C"
    options.bundle_id = "com.saucelabs.mydemo.app.ios"
    options.automation_name = "XCUITest"
    options.no_reset = True

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    try:
        driver.implicitly_wait(10)

        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Catalog-tab-item").click()
        time.sleep(2)
        print("Step 1 passed — Catalog tab tapped")

        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Cart-tab-item").click()
        time.sleep(2)
        print("Step 2 passed — Cart tab tapped")

        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "More-tab-item").click()
        time.sleep(2)
        print("Step 3 passed — More tab tapped")

        print("iOS native navigation test passed — all footer tabs verified")

    finally:
        driver.quit()
