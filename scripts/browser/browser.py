
"""
Reusable Playwright browser manager.

This module handles starting and closing Chromium.
Site-specific automation should live in separate modules.
"""

from playwright.sync_api import sync_playwright


def launch_browser(headless=False):
    """
    Launch Chromium and return the Playwright objects
    needed by the automation system.

    Returns:
        tuple: (playwright, browser, context)
    """

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=headless
    )

    context = browser.new_context()

    print("Chromium launched successfully.")

    return playwright, browser, context


def close_browser(playwright, browser):
    """
    Close the browser and stop Playwright.
    """

    if browser:
        browser.close()

    if playwright:
        playwright.stop()

    print("Browser closed.")


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    playwright = None
    browser = None
    context = None

    try:

        playwright, browser, context = launch_browser(
            headless=False
        )

        page = context.new_page()

        print("Browser page created.")
        print("Opening MyJobMag...")

        response = page.goto(
            "https://www.myjobmag.co.ke/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("Website loaded.")

        if response:
            print(
                f"Status: {response.status}"
            )

        print(
            f"Title: {page.title()}"
        )

        # Keep browser open briefly so we can
        # visually confirm that Chromium works.
        page.wait_for_timeout(3000)

    except Exception as error:

        print(
            f"Browser error: {error}"
        )

    finally:

        if browser and playwright:

            close_browser(
                playwright,
                browser
            )

