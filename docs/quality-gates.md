# Quality gates

What has to be green before a change lands, what does not, and why. Every
rule below is implemented in a file in this repository; the file is named next
to the rule so the two can be checked against each other.

**On enforcement, plainly:** `main` has no branch protection and no rulesets.
Nothing on the platform *prevents* a merge over a red CI run. The rule below
is a standard this repository is held to, enforced by convention — by the
person merging — not by GitHub. That is stated here rather than implied,
because a document that claims an enforcement mechanism it does not have is
worse than one that admits the mechanism is a human.

---

## The problem this design solves

The web suite drives **automationexercise.com**, a third-party practice site.
It serves interstitial ads (which already forced this suite to navigate
directly to a category URL instead of clicking the sidebar link), and it goes
down from time to time. Nothing in this repository can prevent either.

If a public badge were wired to that suite, the badge would go red for
reasons that have nothing to do with the code. A badge that goes red for
reasons the author cannot control teaches everyone who looks at it to ignore
it — at which point it is worse than no badge, because it also costs
credibility when someone does look.

So the gates are split by **what the result actually means**:

| | Deterministic gate | Live E2E |
|---|---|---|
| Workflow | `.github/workflows/ci.yml` | `.github/workflows/e2e-scheduled.yml` |
| Trigger | every push and pull request | nightly schedule + manual dispatch |
| Depends on a third party? | no | yes |
| Red means | this repository is broken | this repository **or** the practice site |
| Required green before merging | yes, by convention | no |
| Badge on the portfolio site | yes | no |

---

## Gate 1 — deterministic checks (required green)

`ci.yml`. Runs on Python 3.12 and 3.13, on every push and pull request. It is
the standard for merging: a change does not land on `main` with this red. That
is a convention held by whoever merges, not a branch-protection rule — see the
note at the top. This is the badge published on the portfolio site.

Nothing in it touches the practice site, and it never installs browser
binaries. Every step is a pure function of the commit.

| Check | Command | Why it is required |
|---|---|---|
| Dependencies resolve | `pip install -r requirements-dev.txt` | The README promises a clean clone installs. This proves it on a machine that is not the author's, twice. |
| Lint | `ruff check .` | Unused imports, shadowed names, mutable default arguments, bare `except`. |
| Format | `ruff format --check .` | Diffs stay about behaviour, not whitespace. |
| Unit tests | `pytest -m unit` | See below — these are the tests of the framework itself. |
| Collection integrity | `pytest --collect-only` | See below. |

### Why there are no browser binaries in this job

This suite once had a root-level script that called its own test function at
module scope. `pytest --collect-only` — a command that is supposed to list
tests without running anything — launched a real browser window.

The deterministic job installs the `playwright` **package** but never runs
`playwright install`, and asserts up front that no browser binaries are
present. If any module ever launches a browser at import time again, the
collection step fails immediately instead of hanging. The guarantee is
structural: it cannot be commented out without the assertion noticing.

### What the unit suite actually covers

`tests/unit/` is not a token suite. It tests the parts of the framework that
have to be right for the E2E tests to mean anything, and each file encodes a
defect this repository has actually shipped:

- **`test_config.py`** — headless is the default and an explicit `--headed`
  beats a stale environment variable; malformed settings fall back rather
  than exploding; no credential is read from the environment at all.
- **`test_ios_device.py`** — simulator selection rules. Previously a
  hardcoded UDID, so the native test ran on exactly one Mac. Discovery is
  split from the `xcrun` call precisely so the rules can be tested on Linux.
- **`test_framework_contracts.py`** — static guards on the repository:
  - no source file hardcodes a headed browser launch;
  - no module calls a `test_*` function at import time;
  - nothing that looks like a credential is assigned a literal (one
    documented exception: the negative-login test's fake password);
  - no test under `tests/ui/` contains a raw selector — selectors live in
    page objects;
  - every dependency in both requirements files is pinned with `==`;
  - `pytest.ini` declares its markers and deselects `native` by default.

### Collection-integrity thresholds

Enforced in the `Collection integrity` step of `ci.yml`:

| Assertion | Threshold | Rationale |
|---|---|---|
| UI tests collected | exactly `10` | The web suite is a known size. Moving it is a deliberate act that edits this number in the same commit. |
| Native tests collected | exactly `1` | |
| Native tests collected by default | `0` | A clean clone must run `pytest` with no Appium server. |
| `default == unit + ui` | exact | Every test carries exactly one location marker, so nothing can arrive unmarked and be swept into the wrong job. |
| Unit tests collected | `>= 20` | Catches a silent collapse of the unit suite. |

---

## Gate 2 — live E2E (reported, never required)

`e2e-scheduled.yml`. Nightly at 11:17 UTC, plus manual dispatch. Runs
`pytest -m ui` against the live site, headless, with video recording on, and
uploads the HTML report and the `.webm` recordings as artifacts.

**Retries.** The run uses `--reruns 2 --reruns-delay 5`. That is a judgement
call and here is the reasoning: an ad overlay or a 502 from a free practice
site is not information about this code, and a suite that reports it as a
defect trains its owner to ignore failures. A real defect is not absorbed by
a retry — it fails all three attempts and the job goes red.

**What is explicitly not allowed:**

- No `continue-on-error`. This job is capable of going red and does.
- No `|| true` on a test command.
- No skipping a test to get to green. A test that cannot pass is either fixed
  or deleted with a reason.
- No retry count above 2. If something needs four attempts it is broken, and
  the honest fix is to make the test deterministic or drop it.

**Escalation.** Two consecutive scheduled failures on the same test means the
test is presumed broken rather than flaky, and it is fixed before the next
release of this repository is linked anywhere.

---

## Native iOS: excluded by architecture

`tests/native/test_ios_native.py` needs macOS, Xcode, a booted iPhone
Simulator, the Sauce Labs demo app installed on it, and a running Appium
server. GitHub-hosted macOS minutes bill at roughly ten times Linux, and the
app build is not published — the job could not be made to work at any price
worth paying.

So it is excluded deliberately and visibly, in three places that agree with
each other:

1. `pytest.ini` deselects `-m "not native"` by default;
2. no workflow in this repository ever *runs* it. `ci.yml` does pass
   `-m native`, but only to `pytest --collect-only`, to count that the test
   still exists. No workflow ever executes a native test;
3. `ci.yml` asserts that exactly one native test exists and that zero are
   collected by default — so the test cannot quietly disappear and leave the
   exclusion looking like coverage.

It is run locally and its screen recording is published. Nothing anywhere
claims it runs in CI.

---

## The rules, in one place

1. A badge is a promise. Only publish one whose red state is actionable by
   the person whose name is on it.
2. Third-party dependence is reported, never gated.
3. Retries absorb infrastructure, never defects.
4. Exclusions are asserted, not assumed.
5. Every threshold in this document is enforced by a command in a workflow
   file, so the document cannot quietly drift away from the pipeline.
6. Where a rule is held by a human rather than by the platform, this document
   says so. Rule 5 covers thresholds, which are machine-checked; the decision
   not to merge over a red run is not, and pretending otherwise would make
   every other claim here worth less.

---

## Related

Test-strategy thinking at the programme level — validation categories,
risk-based prioritisation, entry/exit and cutover go/no-go criteria — is
written up in the data-migration project rather than restated here:
[Migration Test Strategy](https://github.com/keonikaku/sql-data-validation/blob/main/strategy/migration_test_strategy.md).
This document is the narrower question of what gates a commit in *this*
repository.
