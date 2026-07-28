"""Root pytest configuration: CLI options, settings, and automatic markers.

Browser fixtures live in ``tests/conftest.py``. This file deliberately imports
nothing from Playwright, so ``pytest --collect-only`` stays cheap and cannot
start a browser.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shopsmart.config import Settings, load_settings

#: Directory name under ``tests/`` -> marker automatically applied to
#: everything inside it. Marking by location rather than by hand means a new
#: native test cannot accidentally arrive unmarked and get picked up by CI.
MARKER_BY_DIRECTORY = {
    "unit": "unit",
    "ui": "ui",
    "native": "native",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run the browser with a visible window. Default is headless.",
    )


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    """Resolved settings for this session."""
    return load_settings(headed=bool(pytestconfig.getoption("--headed")))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply ``unit`` / ``ui`` / ``native`` markers based on directory."""
    tests_root = Path(config.rootpath) / "tests"
    for item in items:
        try:
            relative = Path(str(item.path)).relative_to(tests_root)
        except ValueError:
            continue
        if not relative.parts:
            continue
        marker = MARKER_BY_DIRECTORY.get(relative.parts[0])
        if marker:
            item.add_marker(getattr(pytest.mark, marker))
