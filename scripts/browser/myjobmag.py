"""
MyJobMag browser automation.

Uses Playwright to open MyJobMag and inspect job listings.
This module is separate from the existing HTTP collector.
"""

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


MYJOBMAG_URL = (
    "https://www.myjobmag.co.ke/"
    "jobs-by-title/developer-python"
)


def open_myjobmag():
    """
    Open the MyJobMag Python developer jobs page
    using Chromium.
    """

    playwright = None
    browser = None

    try:

        playwright, browser, context = launch_browser(
            headless=False
        )

        page = context.new_page()

        print("Opening MyJobMag Python jobs...")

        response = page.goto(
            MYJOBMAG_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("MyJobMag page loaded.")

        if response:

            print(
                f"Status: {response.status}"
            )

        print(
            f"Title: {page.title()}"
        )

        # Keep the browser open briefly so we can
        # visually confirm the correct page opened.
        page.wait_for_timeout(5000)

    except Exception as error:

        print(
            f"MyJobMag browser error: {error}"
        )

    finally:

        if browser and playwright:

            close_browser(
                playwright,
                browser
            )


if __name__ == "__main__":

    open_myjobmag()
