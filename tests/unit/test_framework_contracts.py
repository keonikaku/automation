"""Structural guards on the repository itself.

Each test here encodes a defect this suite has actually shipped, so that the
defect cannot come back quietly. They are pure static analysis — no network,
no browser — which is what lets them gate every pull request.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from shopsmart.config import BASE_URL
from shopsmart.pages import (
    BasePage,
    CartPage,
    CategoryPage,
    ContactPage,
    LoginPage,
    ProductsPage,
    SignupPage,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_TESTS_DIR = REPO_ROOT / "tests" / "ui"

PAGE_CLASSES = [
    CartPage,
    CategoryPage,
    ContactPage,
    LoginPage,
    ProductsPage,
    SignupPage,
]


#: Directories that hold this project's own code. Deliberately an allow-list
#: rather than an rglob of the repository root: a developer who creates a
#: virtualenv inside the clone would otherwise have these guards scanning
#: site-packages, and third-party code would fail rules it never agreed to.
PROJECT_DIRECTORIES = ("shopsmart", "tests")


def python_sources() -> list[Path]:
    """Every Python file that is part of this project."""
    found = list(REPO_ROOT.glob("*.py"))
    for directory in PROJECT_DIRECTORIES:
        found.extend((REPO_ROOT / directory).rglob("*.py"))
    return sorted(path for path in found if "__pycache__" not in path.parts)


def test_the_source_scan_finds_this_project_and_nothing_else():
    """Guard the guards: an empty or over-broad glob makes every scan below lie."""
    relative = {str(path.relative_to(REPO_ROOT)) for path in python_sources()}

    # It must reach the three layers the rules below are about.
    for expected in ("conftest.py", "shopsmart/config.py", "tests/ui/test_auth.py"):
        assert expected in relative, f"source scan missed {expected}"

    # And it must not reach anything vendored or installed.
    strays = [
        path
        for path in relative
        if any(part in path for part in ("site-packages", ".venv", "venv/", "node_modules"))
    ]
    assert not strays, f"source scan escaped the project: {strays[:5]}"


# ── defect 1: every browser launched with a visible window ────────────
#: Assembled from fragments so that this file does not itself contain the
#: literal it forbids — a guard that trips on its own source is useless.
HEADED_LAUNCH = re.compile(r"headless\s*=\s*" + "False")


def test_no_source_file_launches_a_headed_browser():
    """Pinning a browser launch to a visible window makes the suite un-CI-able.

    Every one of the 15 launch sites in the old suite hardcoded a visible
    window. Headedness is now a runtime decision (``--headed`` / ``HEADED=1``)
    resolved in one place; it is never a literal in a test.
    """
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in python_sources()
        if HEADED_LAUNCH.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        f"a hardcoded headed browser launch must not appear in source: {offenders}"
    )


# ── defect 2: a test function called at module scope ──────────────────
@pytest.mark.parametrize(
    "source", python_sources(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_module_calls_a_test_function_at_import_time(source: Path):
    """A root-level script used to call ``test_add_to_cart()`` at module scope.

    That launched a real browser during *collection* — before pytest had run a
    single test — so ``pytest --collect-only`` opened a window and could hang.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        assert not name.startswith("test_"), (
            f"{source.relative_to(REPO_ROOT)} calls {name}() at module scope; "
            "collection would execute it"
        )


# ── defect 3: credentials in source ───────────────────────────────────
CREDENTIAL_NAME = re.compile(r"(PASSWORD|SECRET|TOKEN|API_?KEY)", re.IGNORECASE)

#: The one deliberate exception. ``test_08`` asserts that an unknown user with
#: a wrong password is rejected; that scenario is only reproducible with a
#: literal, and the literal is meaningless outside the test.
ALLOWED_CREDENTIAL_LITERALS = {("tests/ui/test_auth.py", "WRONG_PASSWORD")}

#: Page objects name their locators after the field they drive, so
#: ``PASSWORD = "[data-qa='password']"`` is a selector, not a secret.
SELECTOR_SHAPE = re.compile(r"^[.#\[]|data-qa|^input|^button")


def looks_like_a_selector(value: str) -> bool:
    return bool(SELECTOR_SHAPE.search(value))


@pytest.mark.parametrize(
    "source", python_sources(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_credential_literals_in_source(source: Path):
    """Nothing that looks like a credential is assigned a literal value."""
    relative = str(source.relative_to(REPO_ROOT))
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, str):
            continue
        if not node.value.value or looks_like_a_selector(node.value.value):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or not CREDENTIAL_NAME.search(target.id):
                continue
            assert (relative, target.id) in ALLOWED_CREDENTIAL_LITERALS, (
                f"{relative}: {target.id} is assigned a literal. Credentials are "
                "generated per run, never committed."
            )


# ── page-object boundary ──────────────────────────────────────────────
#: Anything on this list is Playwright's API leaking into a test.
RAW_SELECTOR_MARKERS = [
    "data-qa",
    ".locator(",
    "get_by_text(",
    "get_by_role(",
    "get_by_label(",
    ".fill(",
    ".click(",
    "css=",
    "xpath=",
]


@pytest.mark.parametrize(
    "source", sorted(UI_TESTS_DIR.glob("test_*.py")), ids=lambda p: p.name
)
def test_ui_tests_contain_no_raw_selectors(source: Path):
    """Tests describe intent; page objects own selectors."""
    text = source.read_text(encoding="utf-8")
    found = [marker for marker in RAW_SELECTOR_MARKERS if marker in text]
    assert not found, (
        f"{source.name} reaches past its page object: {found}. "
        "Move the selector into shopsmart/pages/."
    )


@pytest.mark.parametrize("page_class", PAGE_CLASSES, ids=lambda c: c.__name__)
def test_every_page_object_is_a_base_page_with_a_url(page_class):
    assert issubclass(page_class, BasePage)
    instance = page_class(page=None)
    assert instance.url.startswith(BASE_URL)


def test_page_objects_honour_a_base_url_override():
    """Pointing the suite at another host must not require touching a page."""
    assert LoginPage(page=None, base_url="https://staging.test").url == (
        "https://staging.test/login"
    )
    assert CategoryPage(page=None, base_url="https://staging.test").url == (
        "https://staging.test/category_products/1"
    )


# ── dependency hygiene ────────────────────────────────────────────────
def requirement_lines(filename: str) -> list[str]:
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("-r ")
    ]


@pytest.mark.parametrize("filename", ["requirements.txt", "requirements-dev.txt"])
def test_every_dependency_is_pinned(filename):
    """A clean clone must resolve to the versions this suite was proven against."""
    unpinned = [line for line in requirement_lines(filename) if "==" not in line]
    assert not unpinned, f"{filename} has unpinned dependencies: {unpinned}"


def test_markers_are_declared_and_native_is_deselected_by_default():
    """A clean clone runs ``pytest`` with no Appium server and no simulator."""
    config = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    for marker in ("unit:", "ui:", "native:"):
        assert marker in config, f"pytest.ini does not declare the {marker} marker"
    assert "--strict-markers" in config
    assert "not native" in config
