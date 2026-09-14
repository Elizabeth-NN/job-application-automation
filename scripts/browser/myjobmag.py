"""
MyJobMag browser automation.

Uses Playwright to inspect MyJobMag job listings and
determine how applications are handled.
"""

import re

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


# ============================================================
# URLS
# ============================================================

MYJOBMAG_URL = (
    "https://www.myjobmag.co.ke/"
    "jobs-by-title/developer-python"
)

TEST_JOB_URL = (
    "https://www.myjobmag.co.ke/"
    "job/fullstack-developer-itravel-holidays"
)


# ============================================================
# COLLECT JOB LINKS
# ============================================================

def collect_job_links(page):
    """
    Find job listing links on the current MyJobMag page.
    """

    job_links = []

    links = page.locator("a").all()

    for link in links:

        try:

            href = link.get_attribute("href")
            title = link.inner_text().strip()

            if not href or not title:
                continue

            if "/job/" not in href:
                continue

            # Convert relative URL to absolute URL.
            if href.startswith("/"):
                href = (
                    "https://www.myjobmag.co.ke"
                    + href
                )

            job_links.append(
                {
                    "title": title,
                    "url": href,
                }
            )

        except Exception:
            continue

    # Remove duplicate URLs.
    unique_jobs = []
    seen_urls = set()

    for job in job_links:

        if job["url"] in seen_urls:
            continue

        seen_urls.add(job["url"])
        unique_jobs.append(job)

    return unique_jobs


# ============================================================
# EXTRACT APPLICATION SUBJECT
# ============================================================

def extract_application_subject(
    body_text,
    page,
):
    """
    Try to determine the email subject requested
    by the employer.

    If no explicit subject is found, use the job title
    as a fallback.
    """

    lines = body_text.splitlines()

    subject_patterns = [
        r"subject\s*:\s*(.+)",
        r"position\s+as\s+subject",
        r"email\s+subject",
    ]

    for line in lines:

        cleaned = line.strip()

        if not cleaned:
            continue

        for pattern in subject_patterns:

            match = re.search(
                pattern,
                cleaned,
                flags=re.IGNORECASE,
            )

            if match and match.groups():

                subject = match.group(1).strip()

                if subject:
                    return subject

    # Try the main job heading.
    headings = page.locator(
        "h1, h2"
    ).all()

    for heading in headings:

        try:

            text = heading.inner_text().strip()

            if text:
                return text

        except Exception:
            continue

    return None


# ============================================================
# DETECT APPLICATION METHOD
# ============================================================

def detect_application_method(page):
    """
    Detect how the employer wants candidates to apply.

    Possible methods:

        email
        external
        on_site
        unknown

    This function only detects the method.
    It does not submit an application.
    """

    body_text = page.locator(
        "body"
    ).inner_text()

    normalized_text = body_text.lower()

    # ========================================================
    # 1. EMAIL APPLICATION
    # ========================================================

    email_pattern = (
        r"\b[A-Z0-9._%+-]+"
        r"@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    )

    emails = re.findall(
        email_pattern,
        body_text,
        flags=re.IGNORECASE,
    )

    if emails:

        application_terms = [
            "method of application",
            "send your application",
            "send your cv",
            "send application",
            "email your cv",
            "forward your cv",
            "submit your cv",
            "apply via email",
        ]

        has_email_instruction = any(
            term in normalized_text
            for term in application_terms
        )

        if has_email_instruction:

            return {
                "method": "email",
                "email": emails[0],
                "subject": extract_application_subject(
                    body_text,
                    page,
                ),
                "url": None,
            }

    # ========================================================
    # 2. APPLICATION LINKS
    # ========================================================

    application_links = page.locator(
        "a"
    ).all()

    # First inspect all "Apply" links.
    for link in application_links:

        try:

            text = link.inner_text().strip()
            normalized_link_text = text.lower()

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            if "apply" not in normalized_link_text:
                continue

            # Convert relative URL to absolute URL.
            if href.startswith("/"):
                href = (
                    "https://www.myjobmag.co.ke"
                    + href
                )

            # ------------------------------------------------
            # MyJobMag on-site application.
            # ------------------------------------------------

            if "/job-application/" in href:

                return {
                    "method": "on_site",
                    "email": None,
                    "subject": None,
                    "url": href,
                }

            # ------------------------------------------------
            # External application.
            # ------------------------------------------------

            if (
                href.startswith("http://")
                or href.startswith("https://")
            ):

                if "myjobmag.co.ke" not in href:

                    return {
                        "method": "external",
                        "email": None,
                        "subject": None,
                        "url": href,
                    }

        except Exception:
            continue

    # ========================================================
    # 3. UNKNOWN
    # ========================================================

    return {
        "method": "unknown",
        "email": None,
        "subject": None,
        "url": None,
    }


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(page, job_url):
    """
    Open a specific MyJobMag job and inspect its
    application mechanism.

    Nothing is submitted.
    """

    print()
    print("=" * 60)
    print("INSPECTING JOB")
    print("=" * 60)

    print()
    print(f"URL: {job_url}")

    # --------------------------------------------------------
    # Navigate to the job.
    # --------------------------------------------------------

    response = page.goto(
        job_url,
        wait_until="commit",
        timeout=30000,
    )

    print("Job navigation started.")

    # --------------------------------------------------------
    # Wait for the page to finish loading.
    # --------------------------------------------------------

    try:

        page.wait_for_load_state(
            "domcontentloaded",
            timeout=15000,
        )

        print("Job page loaded.")

    except Exception:

        print(
            "Page did not reach domcontentloaded "
            "within 15 seconds, continuing anyway."
        )

    # --------------------------------------------------------
    # Status.
    # --------------------------------------------------------

    if response:

        print(
            f"Status: {response.status}"
        )

    # --------------------------------------------------------
    # Page title.
    # --------------------------------------------------------

    print(
        f"Page title: {page.title()}"
    )

    # ========================================================
    # APPLICATION METHOD
    # ========================================================

    print()
    print("APPLICATION METHOD")
    print("-" * 60)

    application = detect_application_method(
        page
    )

    print(
        f"Method: {application['method']}"
    )

    if application["email"]:

        print(
            f"Email: {application['email']}"
        )

    if application["subject"]:

        print(
            f"Subject: {application['subject']}"
        )

    if application["url"]:

        print(
            f"Application URL: {application['url']}"
        )

    # ========================================================
    # HEADINGS
    # ========================================================

    print()
    print("HEADINGS")
    print("-" * 60)

    headings = page.locator(
        "h1, h2, h3"
    ).all()

    for heading in headings:

        try:

            text = heading.inner_text().strip()

            if text:

                print(
                    f"• {text}"
                )

        except Exception:
            continue

    # ========================================================
    # BUTTONS
    # ========================================================

    print()
    print("BUTTONS")
    print("-" * 60)

    buttons = page.locator(
        "button"
    ).all()

    for button in buttons:

        try:

            text = button.inner_text().strip()

            if text:

                print(
                    f"• {text}"
                )

        except Exception:
            continue

    # ========================================================
    # APPLICATION-RELATED LINKS
    # ========================================================

    print()
    print("APPLICATION-RELATED LINKS")
    print("-" * 60)

    links = page.locator(
        "a"
    ).all()

    application_words = [
        "apply",
        "application",
        "career",
        "careers",
        "submit",
    ]

    found_application_links = []

    for link in links:

        try:

            text = link.inner_text().strip()

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            combined = (
                f"{text} {href}"
            ).lower()

            if any(
                word in combined
                for word in application_words
            ):

                found_application_links.append(
                    {
                        "text": text,
                        "url": href,
                    }
                )

        except Exception:
            continue

    if found_application_links:

        for link in found_application_links:

            print(
                f"• {link['text']}"
            )

            print(
                f"  {link['url']}"
            )

    else:

        print(
            "No obvious application links found."
        )

    # ========================================================
    # APPLICATION TEXT
    # ========================================================

    print()
    print("APPLICATION TEXT SEARCH")
    print("-" * 60)

    body_text = page.locator(
        "body"
    ).inner_text()

    lines = body_text.splitlines()

    printed_sections = set()

    for index, line in enumerate(lines):

        normalized = line.lower().strip()

        if (
            "how to apply" in normalized
            or "method of application" in normalized
            or "apply for" in normalized
            or "application" in normalized
            or "apply now" in normalized
        ):

            start = max(
                0,
                index - 2,
            )

            end = min(
                len(lines),
                index + 5,
            )

            section = []

            for surrounding_line in lines[
                start:end
            ]:

                cleaned = surrounding_line.strip()

                if cleaned:

                    section.append(
                        cleaned
                    )

            section_text = "\n".join(
                section
            )

            if section_text in printed_sections:
                continue

            printed_sections.add(
                section_text
            )

            for cleaned in section:

                print(
                    cleaned
                )

            print(
                "-" * 40
            )

    # ========================================================
    # RETURN INFORMATION
    # ========================================================

    return {
        "url": job_url,
        "title": page.title(),
        "application_links": found_application_links,
        "application": application,
    }


# ============================================================
# OPEN MYJOBMAG
# ============================================================

def open_myjobmag():
    """
    Launch Chromium, open the MyJobMag Python jobs page,
    and inspect one test job.

    Nothing is submitted.
    """

    playwright = None
    browser = None

    try:

        # ====================================================
        # LAUNCH BROWSER
        # ====================================================

        playwright, browser, context = launch_browser(
            headless=False
        )

        page = context.new_page()

        # ====================================================
        # OPEN LISTING PAGE
        # ====================================================

        print(
            "Opening MyJobMag Python jobs..."
        )

        response = page.goto(
            MYJOBMAG_URL,
            wait_until="commit",
            timeout=30000,
        )

        print(
            "MyJobMag navigation started."
        )

        try:

            page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000,
            )

            print(
                "MyJobMag page loaded."
            )

        except Exception:

            print(
                "Page did not reach domcontentloaded "
                "within 15 seconds, continuing anyway."
            )

        if response:

            print(
                f"Status: {response.status}"
            )

        print(
            f"Title: {page.title()}"
        )

        # ====================================================
        # COLLECT JOB LINKS
        # ====================================================

        job_links = collect_job_links(
            page
        )

        print()
        print(
            f"Found {len(job_links)} job links."
        )

        for index, job in enumerate(
            job_links,
            start=1,
        ):

            print(
                f"{index}. "
                f"{job['title']}"
            )

            print(
                f"   {job['url']}"
            )

        # ====================================================
        # INSPECT TEST JOB
        # ====================================================

        inspect_job(
            page,
            TEST_JOB_URL,
        )

        # ====================================================
        # KEEP BROWSER OPEN BRIEFLY
        # ====================================================

        print()
        print(
            "Keeping browser open for 5 seconds..."
        )

        page.wait_for_timeout(
            5000
        )

    except Exception as error:

        print()
        print(
            f"MyJobMag browser error: {error}"
        )

    finally:

        if browser and playwright:

            close_browser(
                playwright,
                browser,
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    open_myjobmag()