"""The published test cases: reading them, and mapping them to automation.

``test-cases/*.csv`` are Keoni's originals, committed unmodified. This module
adds the two things the published page needs and the CSVs do not contain:
how to read them consistently, and which cases the automated suite covers.

The CSVs have no "Automated" column. It is *derived* here by mapping each case
to the test in ``tests/ui/`` that exercises it, so the claim is checkable
rather than asserted: unit tests verify that every ``case`` below exists in
the CSVs and every ``test`` below exists in the suite.

Three coverage states, because two would force a lie somewhere:

``YES``
    The automated test asserts the case's primary expected outcome.
``PARTIAL``
    An automated test exercises the scenario but asserts a materially weaker
    property than the case specifies. "Yes" would overclaim; "No" would hide
    real coverage.
``NO``
    Everything else, and the default: a case is not automated unless listed.

Coverage is deliberately narrow. Test design and automation are different
activities, and which cases get automated is a risk decision, not a backlog.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

TEST_CASES_DIR = Path(__file__).resolve().parent.parent / "test-cases"

CSV_FILES = [
    "01_registration_login_FINAL.csv",
    "02_catalog_search_FINAL.csv",
    "03_shopping_cart_FINAL.csv",
    "04_smoke_test_suite_FINAL.csv",
]

SECTION_TITLES = {
    "01_registration_login_FINAL.csv": "Registration & login",
    "02_catalog_search_FINAL.csv": "Catalog & search",
    "03_shopping_cart_FINAL.csv": "Shopping cart",
    "04_smoke_test_suite_FINAL.csv": "Smoke suite",
}

#: Prefixes for the IDs the published page assigns. The source CSVs have no ID
#: column; these exist so rows can be referred to, and are never written back.
SECTION_PREFIX = {
    "01_registration_login_FINAL.csv": "REG",
    "02_catalog_search_FINAL.csv": "CAT",
    "03_shopping_cart_FINAL.csv": "CART",
    "04_smoke_test_suite_FINAL.csv": "SMOKE",
}

EXPECTED_COLUMNS = [
    "Title",
    "Preconditions",
    "Steps",
    "Expected Result",
    "Priority",
    "Type",
]

#: The exact string that marks a case where the specification is silent.
PENDING_MARKER = "PENDING PM CLARIFICATION"

#: The defect traced through the catalog cases and into the smoke suite.
TRACE_ID = "SMART-201"


def read_cases(filename: str) -> list[dict[str, str]]:
    """Parse one CSV. ``utf-8-sig`` because the originals carry a BOM."""
    with open(TEST_CASES_DIR / filename, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def all_cases() -> list[tuple[str, int, dict[str, str]]]:
    """Every case as ``(filename, 1-based row number, row)``."""
    return [
        (filename, index, row)
        for filename in CSV_FILES
        for index, row in enumerate(read_cases(filename), start=1)
    ]


def is_spec_gap(row: dict[str, str]) -> bool:
    return PENDING_MARKER in " ".join(v or "" for v in row.values())


def is_traced(row: dict[str, str]) -> bool:
    return TRACE_ID in " ".join(v or "" for v in row.values())


YES = "Yes"
PARTIAL = "Partial"
NO = "No"


@dataclass(frozen=True)
class Coverage:
    """One case-to-test mapping, with the reason it is what it is."""

    csv: str
    case: str
    test: str
    state: str
    note: str


COVERAGE: list[Coverage] = [
    Coverage(
        csv="01_registration_login_FINAL.csv",
        case="Successful login with valid credentials",
        test="test_01_login",
        state=YES,
        note="Asserts both clauses: redirect to the homepage and the username "
        "in the navigation header.",
    ),
    Coverage(
        csv="01_registration_login_FINAL.csv",
        case="Login with unregistered email address",
        test="test_08_invalid_login",
        state=YES,
        note="Asserts the incorrect-credentials error. Does not separately "
        "assert that the browser stayed on the login page.",
    ),
    Coverage(
        csv="01_registration_login_FINAL.csv",
        case="Login with valid credentials — verify redirect to homepage",
        test="test_01_login",
        state=YES,
        note="Same scenario as the first login case; one test covers both.",
    ),
    Coverage(
        csv="02_catalog_search_FINAL.csv",
        case="Filter products by Women category",
        test="test_03_filter_by_category",
        state=PARTIAL,
        note="Asserts the correct category page is served. Does not assert "
        "that non-Women products are absent, which is what the case specifies.",
    ),
    Coverage(
        csv="02_catalog_search_FINAL.csv",
        case=(
            "Search for a product that exists — verify results match search "
            "term across full catalog"
        ),
        test="test_02_search",
        state=PARTIAL,
        note="Asserts that results came back at all. Does not assert that each "
        "result matches the search term.",
    ),
    Coverage(
        csv="02_catalog_search_FINAL.csv",
        case="Search for a product that does not exist",
        test="test_10_search_no_results",
        state=YES,
        note="Asserts the results grid is empty. The spec gap this case flags "
        "is about the empty-state message, which is not asserted because it is "
        "not yet defined.",
    ),
    Coverage(
        csv="03_shopping_cart_FINAL.csv",
        case="Add product to cart from product listing page",
        test="test_04_add_to_cart",
        state=PARTIAL,
        note="Exercises the confirmation modal but asserts the cart page it "
        "leads to, not that the modal offered both options.",
    ),
    Coverage(
        csv="03_shopping_cart_FINAL.csv",
        case="View Cart from confirmation modal navigates to cart page",
        test="test_04_add_to_cart",
        state=PARTIAL,
        note="Asserts the browser lands on the cart page. Does not assert that "
        "the added product is visible there, which is the case's second clause "
        "and the half that would catch a cart which navigates but drops the "
        "item.",
    ),
    Coverage(
        csv="03_shopping_cart_FINAL.csv",
        case=(
            "Integration — Guest user attempting to add to cart is not blocked "
            "but checkout requires login"
        ),
        test="test_05_checkout_requires_login",
        state=YES,
        note="Adds as a guest and asserts the register/login gate on checkout. "
        "The site presents a modal rather than the redirect the case describes; "
        "the test asserts the behaviour the site actually has.",
    ),
]

#: Automated tests with no matching published case. Named rather than omitted:
#: an unexplained gap in either direction is what makes a coverage claim
#: untrustworthy.
AUTOMATED_WITHOUT_A_CASE = {
    "test_06_contact_form": "No Contact Us case exists in these four files.",
    "test_07_mobile_login": "No mobile-web case exists; these files cover "
    "desktop behaviour only.",
    "test_09_empty_login_fields": "The published cases cover an empty email and "
    "an empty password separately; this test submits both empty at once.",
    "test_11_ios_native": "Different application — the Sauce Labs demo app, not "
    "the site these cases describe.",
}


def by_case() -> dict[tuple[str, str], Coverage]:
    return {(item.csv, item.case): item for item in COVERAGE}


# ── the published page ────────────────────────────────────────────────
#: The case shown in full on the preview: the defect trace, end to end.
FEATURED_CASE = (
    "04_smoke_test_suite_FINAL.csv",
    "Smoke — Search respects active category filter (SMART-201)",
)

#: Four rows chosen to show the shape of the set rather than its size: one of
#: each coverage state, and one spec gap.
PREVIEW_CASES = [
    ("01_registration_login_FINAL.csv", "Successful login with valid credentials"),
    (
        "01_registration_login_FINAL.csv",
        "Registration with already registered email address",
    ),
    ("03_shopping_cart_FINAL.csv", "Update product quantity directly on cart page"),
    ("02_catalog_search_FINAL.csv", "Filter products by Women category"),
]

#: Columns of the combined export. Suite, ID and the two automation columns are
#: derived and exist only here: the four original files keep their own six
#: columns and are published unmodified.
COMBINED_COLUMNS = [
    "Suite",
    "ID",
    "Title",
    "Preconditions",
    "Steps",
    "Expected Result",
    "Priority",
    "Type",
    "Automated",
    "Automated Test",
]

COMBINED_FILENAME = "all_test_cases_combined.csv"


def case_id(filename: str, index: int) -> str:
    return f"{SECTION_PREFIX[filename]}-{index:02d}"


def find_case(filename: str, title: str) -> tuple[str, dict[str, str]]:
    """Look a case up by title, returning its assigned ID and the row."""
    for index, row in enumerate(read_cases(filename), start=1):
        if row["Title"] == title:
            return case_id(filename, index), row
    raise KeyError(f"{filename} has no case titled {title!r}")


def coverage_for(filename: str, title: str) -> Coverage | None:
    return by_case().get((filename, title))


def combined_rows() -> list[dict[str, str]]:
    """Every case, flattened, with its suite and derived automation columns."""
    rows = []
    for filename, index, row in all_cases():
        item = coverage_for(filename, row["Title"])
        rows.append(
            {
                "Suite": SECTION_TITLES[filename],
                "ID": case_id(filename, index),
                "Title": row["Title"],
                "Preconditions": row["Preconditions"],
                "Steps": row["Steps"],
                "Expected Result": row["Expected Result"],
                "Priority": row["Priority"],
                "Type": row["Type"],
                "Automated": item.state if item else NO,
                "Automated Test": item.test if item else "",
            }
        )
    return rows


def write_combined_csv() -> Path:
    """Write the single-file export beside the originals."""
    destination = TEST_CASES_DIR / COMBINED_FILENAME
    with open(destination, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMBINED_COLUMNS)
        writer.writeheader()
        writer.writerows(combined_rows())
    return destination


def counts() -> dict[str, int]:
    """The headline numbers, derived from the CSVs so they cannot be invented."""
    cases = all_cases()
    coverage = by_case()
    states = [
        coverage[(f, r["Title"])].state for f, _, r in cases if (f, r["Title"]) in coverage
    ]
    return {
        "cases": len(cases),
        "gaps": sum(is_spec_gap(r) for _, _, r in cases),
        "traced": sum(is_traced(r) for _, _, r in cases),
        "yes": states.count(YES),
        "partial": states.count(PARTIAL),
        "automated": len(states),
    }
