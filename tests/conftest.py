"""Browser fixtures and test-data fixtures for the web suite.

Replaces the previous approach, which monkeypatched ``Browser.new_page``,
``Browser.new_context`` and ``Browser.close`` at runtime to bolt video
recording onto tests that managed their own browsers. Nothing is patched now:
the fixtures own the browser lifecycle, and because a fixture closes each
context before the test finishes, Playwright flushes video to disk on its own.
That was the only thing the patch was buying.

Fixtures are lazy, so unit tests — which request none of these — never launch
a browser or touch the network.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Error, Page, sync_playwright

from shopsmart import accounts
from shopsmart.config import Settings

RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "recordings"


# ── browser lifecycle ─────────────────────────────────────────────────
@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as instance:
        yield instance


@pytest.fixture(scope="session")
def browser(playwright, settings: Settings):
    """One browser per session. Headless unless --headed / HEADED=1."""
    try:
        instance = playwright.chromium.launch(
            headless=settings.headless,
            slow_mo=settings.slow_mo,
        )
    except Error as exc:
        # Loud and actionable, never a skip. Silently skipping ten browser
        # tests because a binary is missing is how a suite reports green
        # while covering nothing.
        raise RuntimeError(
            "Could not launch Chromium. Install the browser binaries first:\n"
            "    playwright install chromium\n"
            f"Playwright said: {exc}"
        ) from exc

    yield instance
    instance.close()


@pytest.fixture
def context_factory(playwright, browser: Browser, settings: Settings, request, tmp_path):
    """Create browser contexts that clean up — and flush their video — for you.

    Every context this hands out is closed during teardown. Playwright only
    writes a video file when the *context* closes, so closing here is what
    makes recording work headless, in CI, and on failure.
    """
    created: list[BrowserContext] = []
    video_dir = tmp_path / "video"

    def _new_context(device: str | None = None, record: bool = True, **kwargs):
        if device:
            kwargs.update(playwright.devices[device])
        if record and settings.record_video:
            video_dir.mkdir(parents=True, exist_ok=True)
            kwargs.setdefault("record_video_dir", str(video_dir))
        context = browser.new_context(**kwargs)
        created.append(context)
        return context

    yield _new_context

    for context in created:
        try:
            context.close()
        except Exception:  # noqa: BLE001 - teardown must not mask a test failure
            pass

    _collect_recordings(video_dir, request.node.name)


def _collect_recordings(video_dir: Path, test_name: str) -> None:
    """Move flushed videos into ``recordings/`` as ``<test>_<timestamp>.webm``."""
    if not video_dir.exists():
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for index, video in enumerate(sorted(video_dir.glob("*.webm"))):
        suffix = f"_{index}" if index else ""
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(video), RECORDINGS_DIR / f"{test_name}_{timestamp}{suffix}.webm")


@pytest.fixture
def page(context_factory) -> Page:
    """A desktop browser page."""
    return context_factory().new_page()


@pytest.fixture
def mobile_page(context_factory, settings: Settings) -> Page:
    """A page in an emulated mobile context (viewport, user agent, touch)."""
    return context_factory(device=settings.mobile_device).new_page()


# ── test data ─────────────────────────────────────────────────────────
@pytest.fixture
def registered_account(context_factory, settings: Settings):
    """Register a throwaway account, hand it to the test, delete it afterwards.

    Registration happens in its own browser context, so the session it leaves
    behind is invisible to the test's context — the test gets a genuinely
    logged-out browser and has to log in for real. That same context is still
    authenticated at teardown, which is what lets it delete the account.

    The account itself is built by ``shopsmart.accounts``, which the
    walkthrough recorder in ``demo/`` also uses, so the published video cannot
    drift from what the suite does.
    """
    context = context_factory(record=False)
    account, setup_page = accounts.register(context, settings.base_url)

    try:
        yield account
    finally:
        # Best effort: a failure to clean up must not turn a passing test red,
        # but it must be visible in the run output.
        try:
            accounts.delete(setup_page, settings.base_url)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: could not delete throwaway account {account.email}: {exc}")
