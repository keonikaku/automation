# Pytest configuration for the ShopSmart automation suite.
#
# Wraps every Playwright browser context created inside a test with
# built-in video recording, so individual test files don't need any
# changes to get a recording. Videos land in recordings/, named
# <test_name>_<timestamp>.webm.
#
# Disable recording for a run with:
#   RECORD_VIDEO=0 pytest -v

import glob
import os
import shutil
from datetime import datetime

import pytest
from playwright.sync_api import Browser

RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")

_orig_new_page = Browser.new_page
_orig_new_context = Browser.new_context
_orig_close = Browser.close


@pytest.fixture(autouse=True)
def _record_video(request, tmp_path):
    if os.environ.get("RECORD_VIDEO", "1") == "0":
        yield
        return

    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    video_dir = tmp_path / "video"
    video_dir.mkdir()

    def new_page(self, **kwargs):
        kwargs.setdefault("record_video_dir", str(video_dir))
        return _orig_new_page(self, **kwargs)

    def new_context(self, **kwargs):
        kwargs.setdefault("record_video_dir", str(video_dir))
        return _orig_new_context(self, **kwargs)

    # Playwright only flushes a video to disk when its context closes, and the
    # existing tests call browser.close() directly — so close contexts first.
    def close(self, **kwargs):
        for context in list(self.contexts):
            try:
                context.close()
            except Exception:
                pass
        return _orig_close(self, **kwargs)

    Browser.new_page = new_page
    Browser.new_context = new_context
    Browser.close = close

    try:
        yield
    finally:
        Browser.new_page = _orig_new_page
        Browser.new_context = _orig_new_context
        Browser.close = _orig_close

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        videos = sorted(glob.glob(str(video_dir / "*.webm")))
        for i, video_file in enumerate(videos):
            suffix = f"_{i}" if i else ""
            dest = os.path.join(
                RECORDINGS_DIR, f"{request.node.name}_{timestamp}{suffix}.webm"
            )
            shutil.move(video_file, dest)
