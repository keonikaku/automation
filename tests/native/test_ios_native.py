"""Native iOS — Appium / XCUITest against the Sauce Labs demo app.

**This test never runs in CI, by design.** It needs macOS, Xcode, a booted
iPhone Simulator and a running Appium server; GitHub-hosted macOS runners cost
roughly ten times a Linux minute and still could not host the app build. It is
excluded by the ``native`` marker, which ``pytest.ini`` deselects by default.
No workflow ever runs a native test; ``ci.yml`` passes ``-m native`` only to
``pytest --collect-only``, to assert this test still exists. See
``docs/quality-gates.md``.

Run it locally with::

    appium                                   # in another terminal
    xcrun simctl boot "iPhone 17"
    pytest -m native

The simulator UDID is discovered at runtime. It used to be a literal in this
file, which meant the test only ran on the one Mac that UDID belonged to.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pytest

from shopsmart.ios import SimulatorNotFound, resolve_device, screen_recording

appium_webdriver = pytest.importorskip(
    "appium.webdriver",
    reason="Appium-Python-Client is not installed",
)
XCUITestOptions = pytest.importorskip("appium.options.ios").XCUITestOptions
AppiumBy = pytest.importorskip("appium.webdriver.common.appiumby").AppiumBy

RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "recordings"

FOOTER_TABS = ["Catalog-tab-item", "Cart-tab-item", "More-tab-item"]


@pytest.fixture
def ios_driver(settings):
    """An Appium session against a simulator discovered on this machine."""
    try:
        device = resolve_device(
            preferred_name=settings.ios_device_name,
            explicit_udid=settings.ios_udid,
        )
    except SimulatorNotFound as exc:
        pytest.skip(str(exc))

    print(f"Using simulator {device.get('name')} ({device['udid']})")

    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.device_name = device.get("name") or settings.ios_device_name
    options.udid = device["udid"]
    options.bundle_id = settings.ios_bundle_id
    options.automation_name = "XCUITest"
    options.no_reset = True

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = RECORDINGS_DIR / f"ios_native_{timestamp}.mp4"

    # Capture is best-effort: this test is about navigation, and a recording
    # problem must not be reported as a navigation defect.
    with screen_recording(device["udid"], destination) as recorded:
        driver = appium_webdriver.Remote(settings.appium_server, options=options)
        driver.implicitly_wait(10)
        try:
            yield driver
        finally:
            driver.quit()

    if recorded and destination.exists():
        print(f"Screen recording saved — {destination}")


def test_11_ios_native(ios_driver):
    """Footer navigation — verify each tab bar item is reachable and taps."""
    for accessibility_id in FOOTER_TABS:
        ios_driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id).click()
        # The tab bar has no completion event to await; the app animates in.
        time.sleep(2)
        # Re-find rather than reuse the reference: switching tabs rebuilds the
        # bar, and XCUITest treats the old handle as stale.
        tab = ios_driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id)
        assert tab.is_displayed(), f"{accessibility_id} disappeared after tapping it"
