"""Record one continuous walkthrough of the web suite, for publication.

**This is not a test and pytest never collects it.** The suite in ``tests/ui/``
gives every test a fresh browser context, because isolation is the point — a
test that inherits another test's session is not testing what it says it is.
That is what CI runs and what a reviewer should read.

A recording has the opposite requirement. Ten isolated tests produce ten short
clips of a browser starting up, which shows almost nothing. So this runner
drives **the same page objects** in **one browser session**, in an order that
reads as a story rather than as a test-file listing:

    blocked login -> successful login -> search -> filter -> add to cart
    -> checkout gate -> contact form -> no results

Same code against the same site, sequenced differently. The suite is not
compromised for the video; the video is produced by a second caller of the
same framework.

Run it::

    python demo/record_web_walkthrough.py

Output lands in ``recordings/`` as ``web_walkthrough_<timestamp>.webm``.

``SLOW_MO`` defaults to 400ms here so the result is watchable. That is a
recording choice, not a measurement — nothing produced by this script is a
timing, and no duration from it is ever published.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shopsmart import accounts  # noqa: E402
from shopsmart.config import load_settings  # noqa: E402
from shopsmart.pages import (  # noqa: E402
    BasePage,
    CategoryPage,
    ContactPage,
    LoginPage,
    ProductsPage,
)

RECORDINGS_DIR = REPO_ROOT / "recordings"

#: Wide enough that the page doesn't collapse to a mobile layout on video.
VIEWPORT = {"width": 1280, "height": 800}

#: Milliseconds between actions. Playwright at full speed is unreadable.
DEFAULT_SLOW_MO = 400

#: Beat between steps, so a viewer can register what just happened.
STEP_PAUSE_MS = 1200

# The same hardcoded fake credentials test_08 uses. A negative login test must
# not depend on an account existing.
UNREGISTERED_EMAIL = "nonexistent-user@example.com"
WRONG_PASSWORD = "wrongpassword123"


def announce(step: int, title: str) -> None:
    print(f"  [{step}/8] {title}", flush=True)


def main() -> int:
    settings = load_settings()
    slow_mo = settings.slow_mo or DEFAULT_SLOW_MO

    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    staging = RECORDINGS_DIR / ".walkthrough-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    print(f"Recording walkthrough against {settings.base_url} (slow_mo={slow_mo}ms)")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.headless, slow_mo=slow_mo)

        # A second, unrecorded context creates the account. It exists only so
        # the recorded session is genuinely logged out and has to log in for
        # real — exactly what the registered_account fixture does.
        setup_context = browser.new_context()
        account, setup_page = accounts.register(setup_context, settings.base_url)

        # One context, one page, held open for the whole walkthrough. Closing
        # the context at the end is what flushes the single video file.
        context = browser.new_context(record_video_dir=str(staging), viewport=VIEWPORT)
        page = context.new_page()

        def beat() -> None:
            page.wait_for_timeout(STEP_PAUSE_MS)

        try:
            # 1 — a login that should fail (test_08_invalid_login)
            announce(1, "Login rejected — unregistered account")
            login_page = LoginPage(page, settings.base_url).open()
            login_page.login(UNREGISTERED_EMAIL, WRONG_PASSWORD)
            expect(login_page.error_message).to_be_visible()
            beat()

            # 2 — the same form, with credentials that work (test_01_login)
            announce(2, "Login succeeds — account registered by this run")
            login_page = LoginPage(page, settings.base_url).open()
            login_page.login(account.email, account.password)
            expect(page).to_have_url(f"{settings.base_url}/")
            expect(login_page.logged_in_banner).to_contain_text(account.name)
            beat()

            # 3 — search returns matches (test_02_search)
            announce(3, "Search returns matching products")
            products = ProductsPage(page, settings.base_url).open()
            products.search("dress")
            expect(products.results_heading).to_be_visible()
            assert products.result_count() > 0
            beat()

            # 4 — category filter (test_03_filter_by_category)
            announce(4, "Category filter — Women > Dress")
            category = CategoryPage(page, settings.base_url).open()
            expect(category.heading).to_be_visible()
            beat()

            # 5 — add to cart (test_04_add_to_cart)
            announce(5, "Add to cart")
            products = ProductsPage(page, settings.base_url).open()
            cart = products.add_first_product_to_cart()
            expect(page).to_have_url(cart.url)
            beat()

            # 6 — checkout gate (test_05_checkout_requires_login)
            #
            # This one asserts that a *guest* cannot check out, so the session
            # has to be signed out first — the walkthrough logged in at step 2
            # and a logged-in user is, correctly, not blocked. Logging out on
            # camera is the honest way to show it: the alternative is claiming
            # a gate that the recorded session never actually hit.
            announce(6, "Checkout requires an account — verified as a guest")
            BasePage(page, settings.base_url).logout()
            products = ProductsPage(page, settings.base_url).open()
            cart = products.add_first_product_to_cart()
            cart.proceed_to_checkout()
            expect(cart.login_required_prompt).to_be_visible()
            beat()

            # 7 — contact form (test_06_contact_form)
            announce(7, "Contact form submits")
            contact = ContactPage(page, settings.base_url).open()
            contact.submit_enquiry(
                name=account.name,
                email="shopsmart-suite@example.com",
                subject="Test Inquiry",
                message="This is an automated test message.",
            )
            expect(contact.success_message).to_be_visible()
            beat()

            # 8 — a search that matches nothing (test_10_search_no_results)
            announce(8, "Search with no matches returns nothing")
            products = ProductsPage(page, settings.base_url).open()
            products.search("zzzznotaproduct")
            expect(products.results_heading).to_be_visible()
            assert products.result_count() == 0
            beat()

        finally:
            # Closing the context flushes the video; closing the setup context
            # after deleting the account leaves the practice site as we found it.
            context.close()
            try:
                accounts.delete(setup_page, settings.base_url)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: could not delete {account.email}: {exc}")
            setup_context.close()
            browser.close()

    videos = sorted(staging.glob("*.webm"))
    if not videos:
        print("ERROR: no video was written", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = RECORDINGS_DIR / f"web_walkthrough_{timestamp}.webm"
    shutil.move(str(videos[0]), destination)
    shutil.rmtree(staging, ignore_errors=True)

    size_kb = destination.stat().st_size // 1024
    print(f"\nWalkthrough saved — {destination} ({size_kb} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
