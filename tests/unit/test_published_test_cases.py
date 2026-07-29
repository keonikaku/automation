"""Guards on the published test cases.

The page states numbers — 54 designed, 9 automated, 19 spec gaps — and marks
cases as covered by named tests. Every one of those claims is derived from the
CSVs or from ``tests/ui/``, and every one is checked here, because a published
number nobody can source is the failure mode this whole repository is trying
to avoid.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import build_test_cases_page as builder
from shopsmart.testcases import (
    AUTOMATED_WITHOUT_A_CASE,
    COMBINED_COLUMNS,
    COMBINED_FILENAME,
    COVERAGE,
    CSV_FILES,
    EXPECTED_COLUMNS,
    FEATURED_CASE,
    PREVIEW_CASES,
    TEST_CASES_DIR,
    all_cases,
    combined_rows,
    counts,
    is_spec_gap,
    is_traced,
    read_cases,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_TESTS_DIR = REPO_ROOT / "tests" / "ui"
NATIVE_TESTS_DIR = REPO_ROOT / "tests" / "native"


def suite_source() -> str:
    paths = sorted(UI_TESTS_DIR.glob("test_*.py")) + sorted(
        NATIVE_TESTS_DIR.glob("test_*.py")
    )
    return "\n".join(p.read_text(encoding="utf-8") for p in paths)


# ── the source files ──────────────────────────────────────────────────
@pytest.mark.parametrize("filename", CSV_FILES)
def test_every_published_csv_parses_with_the_original_columns(filename):
    """The originals are published unmodified — including their columns."""
    rows = read_cases(filename)
    assert rows, f"{filename} has no rows"
    assert list(rows[0].keys()) == EXPECTED_COLUMNS, (
        f"{filename} columns changed: {list(rows[0].keys())}"
    )


def test_the_case_count_is_what_the_pages_claim():
    assert counts()["cases"] == 54


def test_no_case_is_missing_a_title_steps_or_expected_result():
    for filename, index, row in all_cases():
        for column in ("Title", "Steps", "Expected Result", "Priority", "Type"):
            assert row[column].strip(), f"{filename} row {index} has an empty {column}"


# ── the derived coverage column ───────────────────────────────────────
@pytest.mark.parametrize("item", COVERAGE, ids=lambda c: c.test)
def test_every_mapped_case_exists_in_the_csvs(item):
    """A coverage row that names a case which no longer exists is a lie."""
    titles = {row["Title"] for row in read_cases(item.csv)}
    assert item.case in titles, f"{item.csv} has no case titled {item.case!r}"


@pytest.mark.parametrize("item", COVERAGE, ids=lambda c: c.test)
def test_every_mapped_test_exists_in_the_suite(item):
    """Marking a case automated requires the named test to be real."""
    assert f"def {item.test}(" in suite_source(), (
        f"{item.case!r} is marked automated by {item.test}, which does not exist"
    )


@pytest.mark.parametrize("name", sorted(AUTOMATED_WITHOUT_A_CASE))
def test_tests_listed_as_having_no_case_still_exist(name):
    assert f"def {name}(" in suite_source()


def test_every_automated_test_is_either_mapped_or_explained():
    """No test may quietly fall out of the coverage story in either direction."""
    in_suite = {
        line.split("def ")[1].split("(")[0]
        for line in suite_source().splitlines()
        if line.startswith("def test_")
    }
    accounted = {item.test for item in COVERAGE} | set(AUTOMATED_WITHOUT_A_CASE)
    assert in_suite <= accounted, (
        f"tests missing from the coverage story: {sorted(in_suite - accounted)}"
    )


def test_the_featured_and_preview_cases_exist():
    builder.find_case(*FEATURED_CASE)
    for filename, title in PREVIEW_CASES:
        builder.find_case(filename, title)


def test_smart_201_is_published_as_not_automated():
    """He chose to publish it honestly rather than automate it under review."""
    mapped = {(item.csv, item.case) for item in COVERAGE}
    for filename, _, row in all_cases():
        if is_traced(row):
            assert (filename, row["Title"]) not in mapped, (
                f"{row['Title']!r} is marked automated; nothing in the suite "
                "combines a category filter with a search"
            )


# ── the combined export ───────────────────────────────────────────────
def test_the_combined_csv_matches_the_originals():
    committed = list(
        csv.DictReader(
            open(TEST_CASES_DIR / COMBINED_FILENAME, newline="", encoding="utf-8")
        )
    )
    assert list(committed[0].keys()) == COMBINED_COLUMNS
    assert committed == combined_rows(), (
        f"{COMBINED_FILENAME} is stale — run `python build_test_cases_page.py`"
    )
    assert len(committed) == counts()["cases"]


# ── the generated pages ───────────────────────────────────────────────
def test_the_full_test_case_page_is_not_stale():
    committed = (REPO_ROOT / "test-cases.html").read_text(encoding="utf-8")
    assert committed == builder.build(), (
        "test-cases.html is stale — run `python build_test_cases_page.py`"
    )


def test_the_preview_section_in_index_is_not_stale():
    page = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    start = page.index(builder.PREVIEW_START)
    end = page.index(builder.PREVIEW_END) + len(builder.PREVIEW_END)
    assert page[start:end] == builder.build_preview(), (
        "the preview in index.html is stale — run `python build_test_cases_page.py`"
    )


def test_the_headline_numbers_are_all_derived():
    """Sanity-check the numbers both pages print against the raw files."""
    total = counts()
    cases = all_cases()
    assert total["gaps"] == sum(is_spec_gap(row) for _, _, row in cases)
    assert total["traced"] == sum(is_traced(row) for _, _, row in cases)
    assert total["automated"] == total["yes"] + total["partial"] == len(COVERAGE)
    assert total["gaps"] > 0 and total["traced"] > 0
