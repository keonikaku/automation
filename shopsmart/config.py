"""Runtime configuration for the ShopSmart suite.

Every setting has a default that works on a clean clone with no setup, so
``pip install -r requirements.txt && pytest`` is the whole install story.

Two rules this module exists to enforce:

1. **Headless is the default.** A test run must not depend on a display
   server. Headed is an opt-in for a human who wants to watch.
2. **Nothing here reads a credential.** The suite registers the accounts it
   needs (see the ``registered_account`` fixture) and deletes them again, so
   there is no secret to supply and none to leak.

Resolution is a pure function of a mapping, which is what makes it testable
without touching ``os.environ``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

BASE_URL = "https://www.automationexercise.com"

#: Playwright device descriptor used by the mobile-web tests.
MOBILE_DEVICE = "iPhone 13"

#: Default simulator model for the native iOS test. Overridable, never a UDID —
#: UDIDs are machine-specific and are discovered at runtime instead.
DEFAULT_IOS_DEVICE_NAME = "iPhone 17"

TRUTHY = frozenset({"1", "true", "yes", "on"})
FALSEY = frozenset({"0", "false", "no", "off"})


def as_bool(value: str | None, default: bool) -> bool:
    """Interpret an environment-variable string as a boolean.

    Unset or unrecognised values fall back to ``default`` rather than raising,
    because a typo in a local shell should not fail a CI run in a way that
    looks like a product defect.
    """
    if value is None:
        return default
    normalised = value.strip().lower()
    if normalised in TRUTHY:
        return True
    if normalised in FALSEY:
        return False
    return default


@dataclass(frozen=True)
class Settings:
    """Resolved settings for one pytest session."""

    base_url: str = BASE_URL
    headless: bool = True
    slow_mo: int = 0
    record_video: bool = True
    mobile_device: str = MOBILE_DEVICE
    ios_device_name: str = DEFAULT_IOS_DEVICE_NAME
    ios_udid: str | None = None
    ios_bundle_id: str = "com.saucelabs.mydemo.app.ios"
    appium_server: str = "http://127.0.0.1:4723"

    def url(self, path: str = "") -> str:
        """Absolute URL for a site-relative path."""
        return f"{self.base_url}{path}"


def load_settings(
    env: Mapping[str, str] | None = None,
    *,
    headed: bool = False,
) -> Settings:
    """Build :class:`Settings` from an environment mapping and CLI flags.

    ``headed`` comes from ``pytest --headed`` and wins over the environment,
    because an explicit flag on the command line is a stronger signal of
    intent than an exported variable someone forgot about.
    """
    env = os.environ if env is None else env

    headed_requested = headed or as_bool(env.get("HEADED"), False)

    slow_mo_raw = env.get("SLOW_MO", "")
    try:
        slow_mo = max(0, int(slow_mo_raw))
    except ValueError:
        slow_mo = 0

    return Settings(
        base_url=env.get("SHOPSMART_BASE_URL") or BASE_URL,
        headless=not headed_requested,
        slow_mo=slow_mo,
        record_video=as_bool(env.get("RECORD_VIDEO"), True),
        mobile_device=env.get("MOBILE_DEVICE") or MOBILE_DEVICE,
        ios_device_name=env.get("IOS_DEVICE_NAME") or DEFAULT_IOS_DEVICE_NAME,
        ios_udid=env.get("IOS_UDID") or None,
        ios_bundle_id=env.get("IOS_BUNDLE_ID") or Settings.ios_bundle_id,
        appium_server=env.get("APPIUM_SERVER") or Settings.appium_server,
    )
