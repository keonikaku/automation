"""Record the native iOS test running on an iPhone Simulator, for publication.

**This is not a test and pytest never collects it.** It drives the same flow
``tests/native/test_ios_native.py`` asserts: footer navigation through the
Sauce Labs demo app: at a pace a human can follow, and captures the simulator
screen while it happens.

Deliberately the same flow and nothing more. A demo that explored screens the
suite does not assert would show capability the repository cannot back up.

Screen capture is ``xcrun simctl io … recordVideo`` rather than Appium's own
``start_recording_screen``, which shells out to ffmpeg and fails outright when
ffmpeg is absent. simctl ships with Xcode (already required here) and records
the whole device rather than just the app's render surface. The capture is then
re-encoded down to a web-servable size with avconvert; see compress_for_web.

Prerequisites::

    appium                              # in another terminal
    xcrun simctl boot "iPhone 17"       # or leave it to be picked up if booted

Then::

    python demo/record_ios_walkthrough.py

Output lands in ``recordings/`` as ``ios_walkthrough_<timestamp>.mp4``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shopsmart.config import load_settings  # noqa: E402
from shopsmart.ios import (  # noqa: E402
    SimulatorNotFound,
    resolve_device,
    screen_recording,
)

RECORDINGS_DIR = REPO_ROOT / "recordings"

#: The same accessibility identifiers tests/native/test_ios_native.py drives,
#: plus a return to Catalog so the recording ends where it began.
FOOTER_TABS = ["Catalog-tab-item", "Cart-tab-item", "More-tab-item", "Catalog-tab-item"]

#: Long enough for a viewer to see the tab change land.
TAB_PAUSE_SECONDS = 2.5


def main() -> int:
    from appium import webdriver
    from appium.options.ios import XCUITestOptions
    from appium.webdriver.common.appiumby import AppiumBy

    settings = load_settings()

    try:
        device = resolve_device(
            preferred_name=settings.ios_device_name,
            explicit_udid=settings.ios_udid,
        )
    except SimulatorNotFound as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    udid = device["udid"]
    print(f"Simulator: {device.get('name') or settings.ios_device_name} ({udid})")

    # Relaunch the app so the recording starts from a known screen rather than
    # wherever a previous session happened to leave it.
    subprocess.run(
        ["xcrun", "simctl", "terminate", udid, settings.ios_bundle_id], capture_output=True
    )
    time.sleep(1)

    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = RECORDINGS_DIR / f"ios_walkthrough_{timestamp}.mp4"

    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.device_name = device.get("name") or settings.ios_device_name
    options.udid = udid
    options.bundle_id = settings.ios_bundle_id
    options.automation_name = "XCUITest"
    options.no_reset = True

    print(f"Connecting to Appium at {settings.appium_server}…")
    driver = webdriver.Remote(settings.appium_server, options=options)
    driver.implicitly_wait(15)

    try:
        # Let the app settle in the foreground *before* recording starts.
        # Capturing the session handshake instead would open the video on the
        # iOS home screen and the WebDriverAgent icon: test scaffolding, not
        # the thing being demonstrated.
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, FOOTER_TABS[0])
        time.sleep(1.5)

        print("Starting screen recording…")
        # required=True: unlike the test, producing the video is this script's
        # entire purpose, so a capture failure must stop it rather than be a
        # warning nobody reads.
        with screen_recording(udid, destination, required=True):
            time.sleep(1)

            for index, accessibility_id in enumerate(FOOTER_TABS, start=1):
                label = accessibility_id.replace("-tab-item", "")
                print(f"  [{index}/{len(FOOTER_TABS)}] {label} tab", flush=True)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id).click()
                time.sleep(TAB_PAUSE_SECONDS)
                # Re-find: switching tabs rebuilds the bar and XCUITest treats
                # the previous handle as stale.
                tab = driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id)
                assert tab.is_displayed(), f"{accessibility_id} vanished after tapping"

            print("Stopping screen recording…")

    finally:
        driver.quit()

    if not destination.exists() or destination.stat().st_size == 0:
        print("ERROR: no video was written", file=sys.stderr)
        return 1

    compress_for_web(destination)
    print(f"\nWalkthrough saved: {destination} ({destination.stat().st_size // 1024} KB)")
    return 0


def compress_for_web(video: Path) -> None:
    """Re-encode a simulator capture down to something a web page can serve.

    simctl records at the simulator's native resolution: around 1200x2600 for
    a current iPhone, which lands at roughly 3.5 Mbps and 10 MB for twenty
    seconds. That is far too heavy for a portfolio page, especially on mobile
    data.

    ``avconvert`` ships with macOS, so this needs no extra install; the machine
    running this script already requires Xcode. ``Preset1280x720`` fits the
    portrait frame to 720 on the long edge, which is still sharp at the size a
    phone-shaped video is displayed on a page.
    """
    if not shutil.which("avconvert"):
        print("WARNING: avconvert not found; publishing the full-resolution capture")
        return

    before = video.stat().st_size
    compressed = video.with_suffix(".compressed.mp4")
    result = subprocess.run(
        [
            "avconvert",
            "--source",
            str(video),
            "--output",
            str(compressed),
            "--preset",
            "Preset1280x720",
            "--disableMetadataFilter",
        ],
        capture_output=True,
    )

    if result.returncode != 0 or not compressed.exists():
        compressed.unlink(missing_ok=True)
        print("WARNING: avconvert failed; keeping the full-resolution capture")
        return

    after = compressed.stat().st_size
    if after >= before:
        compressed.unlink(missing_ok=True)
        print("Re-encode was not smaller; keeping the original")
        return

    compressed.replace(video)
    print(f"Compressed for web: {before // 1024} KB -> {after // 1024} KB")


if __name__ == "__main__":
    raise SystemExit(main())
