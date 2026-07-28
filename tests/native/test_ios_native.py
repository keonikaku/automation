"""Native iOS — Appium / XCUITest against the Sauce Labs demo app.

**This test never runs in CI, by design.** It needs macOS, Xcode, a booted
iPhone Simulator and a running Appium server; GitHub-hosted macOS runners cost
roughly ten times a Linux minute and still could not host the app build. It is
excluded by the ``native`` marker, which ``pytest.ini`` deselects by default
and which no CI workflow ever selects. See ``docs/quality-gates.md``.

Run it locally with::

    appium                                   # in another terminal
    xcrun simctl boot "iPhone 17"
    pytest -m native

The simulator UDID is discovered at runtime. It used to be a literal in this
file, which meant the test only ran on the one Mac that UDID belonged to.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime
from pathlib import Path

import pytest

from shopsmart.ios import SimulatorNotFound, resolve_device

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

    driver = appium_webdriver.Remote(settings.appium_server, options=options)
    driver.implicitly_wait(10)
    driver.start_recording_screen()
    try:
        yield driver
    finally:
        try:
            _save_recording(driver)
        finally:
            driver.quit()


def _save_recording(driver) -> None:
    """Decode Appium's base64 screen recording into ``recordings/``."""
    video_base64 = driver.stop_recording_screen()
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = RECORDINGS_DIR / f"ios_native_{timestamp}.mp4"
    destination.write_bytes(base64.b64decode(video_base64))
    print(f"Screen recording saved — {destination}")


def test_11_ios_native(ios_driver):
    """Footer navigation — verify each tab bar item is reachable and taps."""
    for accessibility_id in FOOTER_TABS:
        tab = ios_driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id)
        tab.click()
        # The tab bar has no completion event to await; the app animates in.
        time.sleep(2)
        assert tab.is_displayed(), f"{accessibility_id} disappeared after tapping it"
