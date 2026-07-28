# ShopSmart QA Automation Suite

Playwright Python automation suite covering web and mobile testing 
for a full e-commerce platform.

## Known state

The three login tests (`test_01_login`, `test_07_mobile_login`,
`test_08_invalid_login`, plus the standalone `test_login.py` /
`test_mobile_login.py` scripts) **currently fail.** The practice-site
account they were written against has been deleted, so there are no
valid credentials to supply.

This is a known, tracked gap — not a broken commit. The fix is a setup
step that registers its own throwaway account per run rather than
depending on a long-lived one; that work is scheduled alongside the
framework restructure. Everything else in the suite passes.

Credentials are read from environment variables (`SHOPSMART_EMAIL`,
`SHOPSMART_PASSWORD`). See `.env.example`. Nothing secret is committed.

## About This Project

ShopSmart is a simulated e-commerce platform used to demonstrate 
end-to-end QA automation skills. All scripts automate against 
[AutomationExercise.com](https://www.automationexercise.com) — 
a full-featured practice e-commerce site.

## Tools and Technologies

- Python 3.14
- Playwright
- pytest
- pytest-html (visual test reporting)
- Appium (native iOS testing)


## Test Coverage

| Test | Type | Description |
|------|------|-------------|
| test_01_login | Happy Path | Valid credentials — successful login |
| test_02_search | Happy Path | Search for a product — results display |
| test_03_filter_by_category | Happy Path | Filter by Women category |
| test_04_add_to_cart | Happy Path | Add product to cart — cart page loads |
| test_05_checkout_requires_login | Negative | Guest checkout redirects to login modal |
| test_06_contact_form | Happy Path | Submit contact form — success message |
| test_07_mobile_login | Mobile Web | iPhone 13 simulation — login flow |
| test_08_invalid_login | Negative | Wrong password — error message displays |
| test_09_empty_login_fields | Negative | Empty fields — form does not submit |
| test_10_search_no_results | Negative | No matching search term — empty results |
| test_11_ios_native | Native iOS | Appium XCUITest — footer navigation on iPhone 17 Simulator |

## How To Run

**Install dependencies:**
```
pip3 install playwright pytest pytest-html
playwright install
```

**Set credentials:**
```
cp .env.example .env      # then edit .env with your own test account
export SHOPSMART_EMAIL="your-test-account@example.com"
export SHOPSMART_PASSWORD="..."
```
Register your own account on the practice site. `.env` is gitignored.
See "Known state" above for why the login tests fail today.

**Run the full suite:**
```
pytest test_shopsmart_suite.py -v
```

**Run with visual HTML report:**
```
pytest test_shopsmart_suite.py -v --html=report.html --self-contained-html
```

**Run individual scripts:**
```
pytest test_login.py -v
pytest test_mobile_login.py -v

**Run native iOS test (requires Appium running):**
pytest test_11_ios_native.py -v
```

## Test Report

Run the suite with the --html flag above to generate report.html. 
Open it in any browser to see full test results with pass/fail 
status and timing.

## Screen Recording

Every test run records video automatically — no changes to individual
test files required.

- **Playwright tests** (web + mobile web): `conftest.py` wraps every
  browser context with Playwright's built-in video recording. Each
  recording is saved to `recordings/` as `<test_name>_<timestamp>.webm`.
- **Native iOS test** (`test_11_ios_native.py`): uses Appium's
  `start_recording_screen()` / `stop_recording_screen()` around the
  test body. The result is decoded from base64 and saved to
  `recordings/ios_native_<timestamp>.mp4`.

Videos are captured for **failed** tests as well as passing ones, which
is usually when you most want them — the recording shows exactly what the
browser was doing when the assertion or timeout hit.

**Disable video for a run:**
```
RECORD_VIDEO=0 pytest test_shopsmart_suite.py -v
```
(This only affects the Playwright tests — the iOS native test always
records, since Appium's screen recording has no per-run toggle here.)

Recording files themselves aren't committed (`recordings/*.webm` and
`recordings/*.mp4` are gitignored) — the `recordings/` folder is kept
in the repo via `.gitkeep` so it always exists locally.

## Project Structure

```
automation/
├── .env.example               # Credential template — copy to .env (gitignored)
├── conftest.py                # Pytest fixture — enables video recording for Playwright tests
├── test_shopsmart_suite.py    # Full 10-test suite
├── test_login.py              # Login automation
├── test_search.py             # Search automation
├── test_add_to_cart.py        # Cart automation
├── test_contact_form.py       # Contact form automation
├── test_mobile_login.py       # Mobile web — iPhone 13 simulation
├── test_11_ios_native.py      # Native iOS — Appium XCUITest on iPhone 17 Simulator
└── recordings/                # Test run video recordings (gitignored contents)
```

`report.html` and `test_results.png` are generated output and are no
longer committed — run the suite with `--html` to produce your own.

## Author

Keoni Kakugawa — QA & Release Management Leader  
20+ years in software, 15 in QA, ~6 in release management  
github.com/keonikaku/automation
[LinkedIn](https://www.linkedin.com/in/keonikaku)
