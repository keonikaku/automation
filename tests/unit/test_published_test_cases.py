"""Guards on the published test cases.

The page states numbers — 54 designed, 9 automated, 19 spec gaps — and marks
cases as covered by named tests. Every one of those claims is derived from the
CSVs or from ``tests/ui/``, and every one is checked here, because a published
number nobody can source is the failure mode this whole repository is trying
to avoid.
"""

from __future__ import annotations

import csv
import hashlib
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


# ── the originals are the one claim with no derivation behind it ──────
#
# Everything else on the published page is *derived* from these four files, so
# a stale number fails a test. The claim "committed unmodified" is different in
# kind: it is a claim about the files themselves, and nothing downstream
# notices if one of them changes — the page and the combined CSV would simply
# regenerate around the edit and every other guard would still pass.
#
# So it gets a checksum. These digests are the files as Keoni authored them.
# A failure here means either an original was edited (fix the file, not the
# digest) or the originals were deliberately republished (say so in the commit,
# then update the digest).
ORIGINAL_DIGESTS = {
    "01_registration_login_FINAL.csv": (
        "cf11ee432a4a77b3af4c9a6b06022a50ba8dfeab9939e948418ea145a810ea17"
    ),
    "02_catalog_search_FINAL.csv": (
        "8528e2549ca6532ea17fd0141c65dfa2c32f1f320d6228a0122c97b5515a066b"
    ),
    "03_shopping_cart_FINAL.csv": (
        "411db5ca296dcbf533eafdecfec7798276ef8ef871f47615001342157b2e53ea"
    ),
    "04_smoke_test_suite_FINAL.csv": (
        "b31c8369a25b675c426e978d0690f06d9da5f56db2f3005d4d85464bd3a1ad61"
    ),
}


def test_the_digest_list_covers_every_published_original():
    """A new original must not slip in unguarded."""
    assert sorted(ORIGINAL_DIGESTS) == sorted(
        f for f in CSV_FILES if f != COMBINED_FILENAME
    )


@pytest.mark.parametrize("filename", sorted(ORIGINAL_DIGESTS))
def test_every_original_csv_is_byte_for_byte_unmodified(filename):
    digest = hashlib.sha256((TEST_CASES_DIR / filename).read_bytes()).hexdigest()
    assert digest == ORIGINAL_DIGESTS[filename], (
        f"{filename} has changed. The README and the published page both say "
        "these files are committed unmodified, so either restore the file or "
        "change the claim — do not just update the digest."
    )


# ── the README states the same numbers in prose ───────────────────────
#
# The generated surfaces cannot go stale; the README can, and hand-written
# prose next to generated output is exactly where a number drifts first.
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def readme_prose() -> str:
    """The README with line wrapping normalised away."""
    return " ".join((REPO_ROOT / "README.md").read_text(encoding="utf-8").split())


def test_the_readme_numbers_match_the_derived_counts():
    total = counts()
    prose = readme_prose()
    not_automated = total["cases"] - total["automated"]
    catalog_traced = sum(
        1
        for filename, _, row in all_cases()
        if is_traced(row) and filename.startswith("02_")
    )
    expected = [
        f"holds {total['cases']} functional test cases",
        f"{total['gaps']} of them carry `PENDING PM CLARIFICATION`",
        f"traced through {NUMBER_WORDS[catalog_traced]} catalog cases",
        f"{total['yes']} fully, {total['partial']} partially, "
        f"{not_automated} not automated",
    ]
    for sentence in expected:
        assert sentence in prose, (
            f"README.md no longer says {sentence!r}. The derived counts are "
            f"{total} — update the README, not this test."
        )
