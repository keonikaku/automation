# ShopSmart QA Automation Suite

[![CI](https://github.com/keonikaku/automation/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/keonikaku/automation/actions/workflows/ci.yml)
[![E2E (on demand)](https://github.com/keonikaku/automation/actions/workflows/e2e-scheduled.yml/badge.svg)](https://github.com/keonikaku/automation/actions/workflows/e2e-scheduled.yml)

Playwright + pytest automation covering desktop web, mobile web, and native iOS
against a public practice e-commerce site.

**Two badges, deliberately.** `CI` is the deterministic gate: lint, unit tests,
and collection integrity, on every commit, dependent on nothing but this
repository. `E2E (on demand)` drives the live third-party practice site when
it is asked to; it can go amber for reasons no commit here controls, so it
reports rather than gates. Only the first is published on the portfolio site. The reasoning is in
[`docs/quality-gates.md`](docs/quality-gates.md).

## Quick start

```bash
git clone https://github.com/keonikaku/automation.git
cd automation
pip install -r requirements.txt
playwright install chromium
pytest
```

That is the whole setup. No account to create, no credentials to supply, no
`.env` to fill in: the suite registers the accounts it needs and deletes them
again. `pytest` runs the unit suite and the 10 web tests; the native iOS test is
deselected by default because it needs macOS and a running Appium server.

**Watch it run:**

```bash
pytest --headed          # or: HEADED=1 pytest
pytest --headed -m ui    # just the browser tests
SLOW_MO=250 pytest --headed -m ui
```

Headless is the default so the suite runs unattended.

## What runs where

| | Command | Needs |
|---|---|---|
| Deterministic checks | `pytest -m unit` | nothing but Python |
| Web suite (desktop + mobile) | `pytest -m ui` | Chromium, network |
| Native iOS | `pytest -m native` | macOS, Xcode, a booted Simulator, `appium` running |
| Everything except native | `pytest` | Chromium, network |

## Test coverage

Web suite, `tests/ui/`:

| Test | Type | Description |
|------|------|-------------|
| test_01_login | Happy path | Valid credentials: successful login |
| test_02_search | Happy path | Search returns matching products |
| test_03_filter_by_category | Happy path | Women › Dress category page |
| test_04_add_to_cart | Happy path | Add product to cart: cart page loads |
| test_05_checkout_requires_login | Negative | Guest checkout is blocked |
| test_06_contact_form | Happy path | Contact form success message |
| test_07_mobile_login | Mobile web | iPhone 13 emulation: login flow |
| test_08_invalid_login | Negative | Unregistered account is rejected |
| test_09_empty_login_fields | Negative | Empty form does not submit |
| test_10_search_no_results | Negative | Non-matching term returns nothing |

Native, `tests/native/`:

| Test | Type | Description |
|------|------|-------------|
| test_11_ios_native | Native iOS | Appium XCUITest: footer navigation, Sauce Labs demo app |

Framework, `tests/unit/`: settings resolution, simulator-selection rules, and
static contracts on the repository itself. These are the tests that gate every
commit. See [`docs/quality-gates.md`](docs/quality-gates.md) for what each one
covers and why.

## How it is put together

```
automation/
├── .github/workflows/
│   ├── ci.yml                  # deterministic gate: every push and PR
│   └── e2e-scheduled.yml       # live web suite, on demand, reported not gated
├── shopsmart/
│   ├── config.py               # settings resolution (headless default, base URL)
│   ├── ios.py                  # Simulator discovery: no hardcoded UDIDs
│   └── pages/                  # page objects; the only place selectors live
├── tests/
│   ├── conftest.py             # browser, context, page and account fixtures
│   ├── unit/                   # deterministic: no network, no browser
│   ├── ui/                     # Playwright web tests
│   └── native/                 # Appium iOS
├── conftest.py                 # CLI options and location-based markers
├── pytest.ini                  # markers, default deselection, strict config
├── requirements.txt            # runtime deps, pinned
├── requirements-dev.txt        # + lint and retry plugin, pinned
├── build_test_cases_page.py    # regenerates test-cases.html + the combined CSV
├── test-cases/                 # the published manual test cases
│   ├── *_FINAL.csv                 # the four originals, unmodified
│   └── all_test_cases_combined.csv # generated: all 54 with a Suite column
├── test-cases.html             # generated: all 54 cases, rendered
├── demo/                       # recording runners: NOT tests, never collected
│   ├── record_web_walkthrough.py   # the whole web flow in one browser session
│   └── record_ios_walkthrough.py   # simctl capture while Appium drives the app
├── docs/quality-gates.md       # what must be green before a change lands, and why
├── index.html                  # walkthrough page: the published recordings
└── recordings/                 # raw run output (gitignored)
    └── published/              # curated recordings backing the page (tracked)
```

**Page objects.** Tests describe intent; page objects own selectors. There is a
unit test that fails the build if a raw selector appears in a test file.

**Fixtures, not monkeypatching.** An earlier version of this suite patched
`Browser.new_page`, `Browser.new_context` and `Browser.close` at runtime to bolt
video recording onto tests that managed their own browsers. Nothing is patched
now. `tests/conftest.py` owns the browser lifecycle, and because a fixture
closes each context before the test finishes, Playwright flushes video to disk
on its own, which is the only thing the patch was buying.

**Self-registering accounts.** The `registered_account` fixture creates a
throwaway account on the practice site, hands the credentials to the test, and
deletes the account at teardown. Registration happens in a separate browser
context, so the test still has to log in for real. There are no credentials in
this repository and none to configure.

The one deliberate exception is `test_08_invalid_login`, which hardcodes a fake
unregistered address. Authenticating badly is the entire point of that test, so
it must not depend on an account existing, or on the environment deciding which
scenario it runs.

**The manual test cases are published too.** `test-cases/` holds 54 functional
test cases written before and alongside the automation, in their original CSV
form and unmodified. 19 of them carry `PENDING PM CLARIFICATION` instead of an
expected result. Where the spec was silent, the case says so and proposes an
expectation rather than inventing one. One defect, SMART-201, is traced through
three catalog cases and is the whole smoke suite.

`Automated` is a **derived** column: it exists only in the generated outputs and
maps each case to the test in `tests/ui/` that covers it: 5 fully, 4 partially,
45 not automated. Unit tests fail the build if a named test stops existing, if a
mapped case title is not in the CSVs, if the generated page and the data
disagree, if an original CSV changes, or if the numbers in this paragraph drift
from the derived counts. Regenerate with `python build_test_cases_page.py`.

**Recording is a separate program from testing.** Each test in `tests/ui/` gets
a fresh browser context, because isolation is what makes a test mean anything.
That produces ten short clips of a browser starting up, which shows nothing. So
`demo/` holds runners that drive the *same page objects* through one continuous
session for the camera. The suite was not loosened to get a better video; a
second caller of the same framework was added. Run them with
`python demo/record_web_walkthrough.py`.

**Simulator discovery.** The native iOS test used to carry a hardcoded UDID,
which meant it ran on exactly one Mac. `shopsmart/ios.py` now discovers a
simulator at runtime: preferring one that is already booted, then the model
named by `IOS_DEVICE_NAME`, then any available iPhone, and the selection rules
are unit-tested on Linux because parsing is split from the `xcrun` call.

## Configuration

Everything is optional; every default works on a clean clone.

| Variable | Default | Effect |
|---|---|---|
| `HEADED` | unset | `1` shows the browser window (same as `--headed`) |
| `SLOW_MO` | `0` | milliseconds of delay between actions, for watching a run |
| `RECORD_VIDEO` | `1` | `0` disables video recording |
| `SHOPSMART_BASE_URL` | the practice site | point the suite at another host |
| `MOBILE_DEVICE` | `iPhone 13` | Playwright device descriptor for mobile tests |
| `IOS_DEVICE_NAME` | `iPhone 17` | preferred Simulator model |
| `IOS_UDID` | unset | pin a specific Simulator, skipping discovery |
| `APPIUM_SERVER` | `http://127.0.0.1:4723` | Appium endpoint |

## Screen recording

Every web test records itself. The context fixture configures Playwright's
built-in video recording and closes the context at teardown, which is what
flushes the file; recordings land in `recordings/` as
`<test_name>_<timestamp>.webm`. **Failing tests are recorded the same way
passing ones are**, which is usually when you most want the video.

Recording works headless, which is what makes the CI run able to upload video
artifacts.

### What gets committed

Raw run output is **not** committed: `recordings/*.webm` and `recordings/*.mp4`
are gitignored, and those patterns are deliberately non-recursive so a stray run
can't sweep itself into the repo. Recordings chosen for publication are moved by
hand into **`recordings/published/`**, which *is* tracked, so publishing a
recording is always a deliberate act rather than a side effect of running the
suite.

The two files there back the
[walkthrough page](https://keonikaku.github.io/automation/): one continuous
recording of the web suite's flows in a single browser session, and one screen
capture of an iPhone Simulator while Appium drives the native app. Both are
unedited, both were recorded on 2026-07-28, and both were produced by the
runners in `demo/`.

## Test report

```bash
pytest -m ui --html=report.html --self-contained-html
```

`report.html` is generated output and is not committed. The on demand CI run
produces one on every execution and uploads it as a build artifact.

## Tools

Python 3.12-3.14 · Playwright · pytest · pytest-html · Appium (native iOS) ·
ruff · GitHub Actions

Versions are pinned in `requirements.txt` and `requirements-dev.txt`; CI proves
the pin set installs on Python 3.12 and 3.13 on a machine that is not the
author's.

## Author

Keoni Kakugawa, QA & Release Management Leader
20+ years in software, 15 in QA, ~6 in release management
[github.com/keonikaku/automation](https://github.com/keonikaku/automation) ·
[LinkedIn](https://www.linkedin.com/in/keonikaku)
