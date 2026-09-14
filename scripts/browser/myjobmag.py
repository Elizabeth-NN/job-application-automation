
"""
MyJobMag browser automation.

Uses Playwright to inspect MyJobMag job listings and
determine how applications are handled.

Browser lifecycle is intentionally kept separate from the
reusable MyJobMag functions.

Reusable functions:
    collect_job_links(page)
    extract_application_subject(body_text, page)
    detect_application_method(page)
    inspect_job(page, job_url)

The browser is only launched/closed by open_myjobmag()
when this file is run directly as a test.
"""

import re
from urllib.parse import urljoin

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


# ============================================================
# CONSTANTS
# ============================================================

BASE_URL = "https://www.myjobmag.co.ke"

MYJOBMAG_URL = (
    f"{BASE_URL}/"
    "jobs-by-title/developer-python"
)

TEST_JOB_URL = (
    f"{BASE_URL}/"
    "job/fullstack-developer-itravel-holidays"
)


# ============================================================
# URL HELPERS
# ============================================================

def make_absolute_url(href):
    """
    Convert a MyJobMag relative URL into an absolute URL.

    Examples:

        /job/example
        -> https://www.myjobmag.co.ke/job/example

        https://example.com/job
        -> unchanged
    """

    if not href:
        return None

    return urljoin(
        BASE_URL,
        href,
    )


# ============================================================
# COLLECT JOB LINKS
# ============================================================

def collect_job_links(page):
    """
    Find job listing links on the current MyJobMag page.

    Parameters:
        page: Existing Playwright Page object.

    Returns:
        List of dictionaries containing:
            title
            url

    This function does NOT launch or close a browser.
    """

    job_links = []

    links = page.locator("a").all()

    for link in links:

        try:
            href = link.get_attribute("href")
            title = link.inner_text().strip()

            if not href or not title:
                continue

            # Only collect actual MyJobMag job URLs.
            if "/job/" not in href:
                continue

            job_url = make_absolute_url(href)

            if not job_url:
                continue

            job_links.append(
                {
                    "title": title,
                    "url": job_url,
                }
            )

        except Exception:
            continue

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

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

    If an explicit subject is found, return it.

    Otherwise, use the main job heading as a fallback.

    This function does not interact with the browser
    beyond reading the current page.
    """

    lines = body_text.splitlines()

    # ========================================================
    # EXPLICIT SUBJECT PATTERNS
    # ========================================================

    subject_patterns = [
        r"subject\s*:\s*(.+)",
        r"subject\s*[-–—]\s*(.+)",
        r"email\s+subject\s*:\s*(.+)",
        r"position\s+as\s+subject\s*:\s*(.+)",
        r"using\s+the\s+position\s+as\s+subject",
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

            if not match:
                continue

            # Some patterns contain a captured subject.
            if match.groups():

                subject = match.group(1).strip()

                if subject:
                    return subject

            # If the instruction only says
            # "using the position as subject", we continue
            # and use the job heading as the fallback.

    # ========================================================
    # FALLBACK TO JOB HEADING
    # ========================================================

    headings = page.locator(
        "h1, h2"
    ).all()

    for heading in headings:

        try:

            text = heading.inner_text().strip()

            if not text:
                continue

            # Prefer an actual job title over generic headings.
            generic_headings = {
                "send this job to a friend",
                "did you notice an error or suspect this job is scam? tell us.",
                "method of application",
                "send your application",
                "related companies hiring now",
                "career advice",
                "subscribe to job alert",
            }

            if text.lower() in generic_headings:
                continue

            return text

        except Exception:
            continue

    return None


# ============================================================
# EXTRACT EMAILS
# ============================================================

def extract_emails(body_text):
    """
    Extract email addresses from page text.

    Returns:
        List of email addresses.
    """

    email_pattern = (
        r"\b[A-Z0-9._%+-]+"
        r"@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    )

    emails = re.findall(
        email_pattern,
        body_text,
        flags=re.IGNORECASE,
    )

    # Remove duplicates while preserving order.
    unique_emails = []

    seen = set()

    for email in emails:

        normalized = email.lower()

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_emails.append(email)

    return unique_emails


# ============================================================
# DETECT EMAIL APPLICATION
# ============================================================

def detect_email_application(
    body_text,
    page,
):
    """
    Detect an employer email application.

    Returns:
        Dictionary if an email application is detected,
        otherwise None.
    """

    normalized_text = body_text.lower()

    emails = extract_emails(
        body_text
    )

    if not emails:
        return None

    application_terms = [
        "method of application",
        "send your application",
        "send your cv",
        "send application",
        "email your cv",
        "forward your cv",
        "submit your cv",
        "apply via email",
        "send your resume",
        "forward your resume",
        "email your resume",
        "using the position as subject",
    ]

    has_email_instruction = any(
        term in normalized_text
        for term in application_terms
    )

    if not has_email_instruction:
        return None

    return {
        "method": "email",
        "email": emails[0],
        "subject": extract_application_subject(
            body_text,
            page,
        ),
        "url": None,
    }


# ============================================================
# DETECT APPLICATION LINKS
# ============================================================

def find_application_links(page):
    """
    Find links that appear to be related to applying
    for the current job.

    Returns:
        List of dictionaries:

            {
                "text": "...",
                "url": "..."
            }
    """

    application_links = []

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

            if not any(
                word in combined
                for word in application_words
            ):
                continue

            absolute_url = make_absolute_url(
                href
            )

            application_links.append(
                {
                    "text": text,
                    "url": absolute_url,
                }
            )

        except Exception:
            continue

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique_links = []
    seen_urls = set()

    for link in application_links:

        url = link["url"]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        unique_links.append(
            link
        )

    return unique_links


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

    Priority:

        1. Explicit employer email instruction
        2. MyJobMag on-site application
        3. External application
        4. Unknown

    This function only detects the method.

    It does NOT submit an application.
    It does NOT launch or close the browser.
    """

    body_text = page.locator(
        "body"
    ).inner_text()

    # ========================================================
    # 1. EMAIL APPLICATION
    # ========================================================

    email_application = detect_email_application(
        body_text,
        page,
    )

    if email_application:

        return email_application

    # ========================================================
    # 2. APPLICATION LINKS
    # ========================================================

    application_links = find_application_links(
        page
    )

    # --------------------------------------------------------
    # First look for MyJobMag on-site application.
    # --------------------------------------------------------

    for link in application_links:

        href = link["url"]

        if not href:
            continue

        if "/job-application/" in href:

            return {
                "method": "on_site",
                "email": None,
                "subject": None,
                "url": href,
            }

    # --------------------------------------------------------
    # Then look for external application.
    # --------------------------------------------------------

    for link in application_links:

        href = link["url"]

        if not href:
            continue

        if not (
            href.startswith("http://")
            or href.startswith("https://")
        ):
            continue

        if "myjobmag.co.ke" not in href:

            return {
                "method": "external",
                "email": None,
                "subject": None,
                "url": href,
            }

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
# EXTRACT PAGE HEADINGS
# ============================================================

def extract_headings(page):
    """
    Extract h1, h2 and h3 headings from the current page.

    Returns:
        List of heading strings.
    """

    headings = []

    elements = page.locator(
        "h1, h2, h3"
    ).all()

    for element in elements:

        try:

            text = element.inner_text().strip()

            if text:
                headings.append(text)

        except Exception:
            continue

    return headings


# ============================================================
# EXTRACT BUTTONS
# ============================================================

def extract_buttons(page):
    """
    Extract visible button text from the current page.

    Returns:
        List of button labels.
    """

    buttons = []

    elements = page.locator(
        "button"
    ).all()

    for element in elements:

        try:

            text = element.inner_text().strip()

            if text:
                buttons.append(text)

        except Exception:
            continue

    return buttons


# ============================================================
# INSPECT APPLICATION TEXT
# ============================================================

def extract_application_text(
    body_text,
):
    """
    Extract useful sections around application-related
    text from a MyJobMag job page.

    Returns:
        List of text sections.
    """

    lines = body_text.splitlines()

    sections = []
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

            if not section_text:
                continue

            if section_text in printed_sections:
                continue

            printed_sections.add(
                section_text
            )

            sections.append(
                section_text
            )

    return sections


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(
    page,
    job_url,
    verbose=True,
):
    """
    Open a specific MyJobMag job and inspect its
    application mechanism.

    Parameters:
        page:
            Existing Playwright Page object.

        job_url:
            MyJobMag job URL.

        verbose:
            If True, print inspection details.

    Returns:
        Dictionary containing:

            {
                "url": ...,
                "title": ...,
                "application_links": [...],
                "application": {...},
                "headings": [...],
                "buttons": [...],
                "application_text": [...]
            }

    Nothing is submitted.

    This function does NOT launch or close the browser.
    """

    if verbose:

        print()
        print("=" * 60)
        print("INSPECTING JOB")
        print("=" * 60)

        print()
        print(f"URL: {job_url}")

    # ========================================================
    # NAVIGATE
    # ========================================================

    response = page.goto(
        job_url,
        wait_until="commit",
        timeout=30000,
    )

    if verbose:
        print("Job navigation started.")

    # ========================================================
    # WAIT FOR PAGE
    # ========================================================

    try:

        page.wait_for_load_state(
            "domcontentloaded",
            timeout=15000,
        )

        if verbose:
            print("Job page loaded.")

    except Exception:

        if verbose:

            print(
                "Page did not reach domcontentloaded "
                "within 15 seconds, continuing anyway."
            )

    # ========================================================
    # RESPONSE STATUS
    # ========================================================

    status = None

    if response:

        status = response.status

        if verbose:
            print(
                f"Status: {status}"
            )

    # ========================================================
    # PAGE TITLE
    # ========================================================

    page_title = page.title()

    if verbose:

        print(
            f"Page title: {page_title}"
        )

    # ========================================================
    # PAGE TEXT
    # ========================================================

    body_text = page.locator(
        "body"
    ).inner_text()

    # ========================================================
    # APPLICATION METHOD
    # ========================================================

    application = detect_application_method(
        page
    )

    # ========================================================
    # APPLICATION LINKS
    # ========================================================

    application_links = find_application_links(
        page
    )

    # ========================================================
    # HEADINGS
    # ========================================================

    headings = extract_headings(
        page
    )

    # ========================================================
    # BUTTONS
    # ========================================================

    buttons = extract_buttons(
        page
    )

    # ========================================================
    # APPLICATION TEXT
    # ========================================================

    application_text = extract_application_text(
        body_text
    )

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    if verbose:

        # ----------------------------------------------------
        # APPLICATION METHOD
        # ----------------------------------------------------

        print()
        print("APPLICATION METHOD")
        print("-" * 60)

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

        # ----------------------------------------------------
        # HEADINGS
        # ----------------------------------------------------

        print()
        print("HEADINGS")
        print("-" * 60)

        for heading in headings:

            print(
                f"• {heading}"
            )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        print()
        print("BUTTONS")
        print("-" * 60)

        for button in buttons:

            print(
                f"• {button}"
            )

        # ----------------------------------------------------
        # APPLICATION LINKS
        # ----------------------------------------------------

        print()
        print("APPLICATION-RELATED LINKS")
        print("-" * 60)

        if application_links:

            for link in application_links:

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

        # ----------------------------------------------------
        # APPLICATION TEXT
        # ----------------------------------------------------

        print()
        print("APPLICATION TEXT SEARCH")
        print("-" * 60)

        if application_text:

            for section in application_text:

                print(section)

                print(
                    "-" * 40
                )

        else:

            print(
                "No application-related text found."
            )

    # ========================================================
    # RETURN STRUCTURED INFORMATION
    # ========================================================

    return {
        "url": job_url,
        "title": page_title,
        "status": status,
        "application_links": application_links,
        "application": application,
        "headings": headings,
        "buttons": buttons,
        "application_text": application_text,
    }


# ============================================================
# OPEN MYJOBMAG - TEST ONLY
# ============================================================

def open_myjobmag():
    """
    Standalone test function.

    This is the ONLY function in this module that launches
    and closes the browser.

    The main automation pipeline should NOT use this function.

    Instead, automation.py should do:

        playwright, browser, context = launch_browser(
            headless=False
        )

        page = context.new_page()

        collect_job_links(page)

        inspect_job(page, job_url)

        ...

        close_browser(
            playwright,
            browser,
        )
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

        # ====================================================
        # WAIT FOR PAGE
        # ====================================================

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

        # ====================================================
        # STATUS
        # ====================================================

        if response:

            print(
                f"Status: {response.status}"
            )

        # ====================================================
        # TITLE
        # ====================================================

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
                f"{index}. {job['title']}"
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

        # ====================================================
        # CLOSE BROWSER
        # ====================================================

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

