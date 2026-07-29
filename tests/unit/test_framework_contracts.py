"""Structural guards on the repository itself.

Each test here encodes a defect this suite has actually shipped, so that the
defect cannot come back quietly. They are pure static analysis — no network,
no browser — which is what lets them gate every pull request.
"""

from __future__ import annotations

import ast
import html
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
WALKTHROUGH_PAGE = REPO_ROOT / "index.html"

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
PROJECT_DIRECTORIES = ("shopsmart", "tests", "demo")


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
    for expected in (
        "conftest.py",
        "shopsmart/config.py",
        "tests/ui/test_auth.py",
        "demo/record_web_walkthrough.py",
    ):
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

#: The deliberate exceptions, both the same one. ``test_08`` asserts that an
#: unknown user with a wrong password is rejected, and the walkthrough recorder
#: replays that step for the camera. The scenario is only reproducible with a
#: literal, and the literal is meaningless outside it.
ALLOWED_CREDENTIAL_LITERALS = {
    ("tests/ui/test_auth.py", "WRONG_PASSWORD"),
    ("demo/record_web_walkthrough.py", "WRONG_PASSWORD"),
}

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


# ── the walkthrough page quotes this repository's code ────────────────
# index.html is a public page that displays, under each video, the assertion
# the test makes. Quoted code drifts silently: the restructure moved every
# test onto page objects and the page went on showing the raw-selector style
# the restructure had just deleted — on the very page built to show it off.
# Nothing false was stated, but it advertised the wrong thing to exactly the
# reader it was written for. These two tests make that drift a build failure.

ASSERT_BLOCK = re.compile(r'<div class="assert">(.*?)</div>', re.DOTALL)
CARD_NAME = re.compile(r'<span class="vname">(test_\w+)</span>')
GAP_NAME = re.compile(r"<h3>(test_\w+)</h3>")


def walkthrough_html() -> str:
    return WALKTHROUGH_PAGE.read_text(encoding="utf-8")


def ui_test_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(UI_TESTS_DIR.glob("test_*.py"))
    )


def quoted_assertion_lines() -> list[str]:
    """Every non-blank line of every assertion block on the walkthrough page."""
    lines = []
    for block in ASSERT_BLOCK.findall(walkthrough_html()):
        for line in html.unescape(block).splitlines():
            if line.strip():
                lines.append(line.strip())
    return lines


def test_the_walkthrough_page_quotes_assertions_it_can_be_checked_against():
    """Guard the guard: no blocks found would make the check below vacuous."""
    assert len(quoted_assertion_lines()) >= 10


@pytest.mark.parametrize("quoted", quoted_assertion_lines(), ids=lambda line: line[:48])
def test_every_assertion_shown_on_the_walkthrough_page_exists_in_the_suite(quoted):
    """Each quoted line must appear verbatim in tests/ui/."""
    assert quoted in ui_test_source(), (
        f"index.html shows an assertion that is not in tests/ui/:\n    {quoted}\n"
        "The page has drifted from the code it claims to show."
    )


def suite_test_names() -> set[str]:
    """Every test function in the suite, web and native."""
    sources = sorted(UI_TESTS_DIR.glob("test_*.py")) + sorted(
        (REPO_ROOT / "tests" / "native").glob("test_*.py")
    )
    names: set[str] = set()
    for path in sources:
        names.update(
            re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.MULTILINE)
        )
    return names


def test_the_walkthrough_page_accounts_for_every_test_in_the_suite():
    """Every test is either shown in a video or explained as not shown.

    The page presents two videos rather than one clip per test, so a test can
    legitimately be absent from the footage. What it cannot be is *silently*
    absent — that is how a suite quietly loses a test and a page goes on
    implying full coverage. Each test must appear either as a step beside a
    video or in the "Not in this set" list, and never in both.
    """
    page = walkthrough_html()
    shown = set(CARD_NAME.findall(page))
    explained = set(GAP_NAME.findall(page))
    suite = suite_test_names()

    assert not (shown & explained), (
        f"tests both shown and excused on the page: {sorted(shown & explained)}"
    )
    assert shown | explained == suite, (
        f"walkthrough page and suite disagree — "
        f"unaccounted for on the page: {sorted(suite - (shown | explained))}, "
        f"on the page but not in the suite: {sorted((shown | explained) - suite)}"
    )
