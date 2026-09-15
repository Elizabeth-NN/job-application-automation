
"""
MyJobMag browser automation.

Reusable Playwright functions for:

    1. Opening MyJobMag
    2. Collecting job links
    3. Inspecting individual job pages
    4. Extracting application information

This module does NOT:
    - launch Chromium automatically when imported
    - close Chromium automatically
    - submit applications
"""

import re
from urllib.parse import urljoin


# ============================================================
# SETTINGS
# ============================================================

MYJOBMAG_BASE_URL = "https://www.myjobmag.co.ke"

MYJOBMAG_URL = (
    f"{MYJOBMAG_BASE_URL}/"
    "jobs-by-title/developer-python"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """Normalize whitespace in a string."""

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def normalize_url(url):
    """Ensure URLs are absolute."""

    if not url:
        return ""

    url = str(url).strip()

    return urljoin(
        MYJOBMAG_BASE_URL,
        url
    )


def get_page_text(page):
    """Safely return visible page text."""

    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


# ============================================================
# EMAIL EXTRACTION
# ============================================================

def extract_emails(text):
    """
    Extract all email addresses from text.

    MyJobMag's own email addresses are filtered out.
    """

    if not text:
        return []

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    results = []

    for email in emails:

        email = email.strip()

        if email.lower().endswith(
            "@myjobmag.co.ke"
        ):
            continue

        if email not in results:
            results.append(email)

    return results


def extract_email(text):
    """Return the first non-MyJobMag email address."""

    emails = extract_emails(text)

    if emails:
        return emails[0]

    return None


# ============================================================
# APPLICATION LINKS
# ============================================================

def extract_application_links(page):
    """
    Extract links that may be related to applying.

    Returns:

        [
            {
                "text": "...",
                "url": "..."
            }
        ]
    """

    links = []
    seen_urls = set()

    try:

        anchors = page.locator(
            "a[href]"
        ).all()

        for anchor in anchors:

            try:

                text = clean_text(
                    anchor.inner_text()
                )

                href = anchor.get_attribute(
                    "href"
                )

            except Exception:
                continue

            if not href:
                continue

            href = normalize_url(
                href
            )

            combined = (
                f"{text} {href}"
            ).lower()

            application_keywords = (
                "apply",
                "application",
                "career",
                "workday",
                "greenhouse",
                "lever",
                "ashby",
                "smartrecruiters",
                "job-application",
            )

            if not any(
                keyword in combined
                for keyword in application_keywords
            ):
                continue

            if href in seen_urls:
                continue

            seen_urls.add(href)

            links.append(
                {
                    "text": text,
                    "url": href,
                }
            )

    except Exception as error:

        print(
            f"Application-link extraction error: {error}"
        )

    return links


# ============================================================
# EXTERNAL APPLICATION DETECTION
# ============================================================

def is_external_application_url(url):
    """
    Determine whether a URL appears to point directly
    to an employer/ATS application system.

    MyJobMag's own application pages are NOT treated as
    external application destinations.
    """

    if not url:
        return False

    lower_url = url.lower()

    if "myjobmag.co.ke" in lower_url:
        return False

    external_domains = (
        "workday",
        "greenhouse",
        "lever.co",
        "ashby",
        "smartrecruiters",
        "icims",
        "bamboohr",
        "jobvite",
        "successfactors",
        "oraclecloud",
        "recruitee",
        "teamtailor",
    )

    return any(
        domain in lower_url
        for domain in external_domains
    )


# ============================================================
# SUBJECT EXTRACTION
# ============================================================

def extract_application_subject(
    text,
    job_title=None
):
    """
    Extract the expected application email subject.

    If the page says something like:

        "using the position as subject of email"

    the actual job title is used as the subject.
    """

    if not text:
        return None

    normalized = clean_text(text)

    subject_patterns = [
        r"subject(?:\s+line)?\s*(?:is|should be|:|-)\s*[\"“]?([^\"”\n]+)",
        r"subject\s+of\s+(?:the\s+)?email\s*(?:is|:|-)?\s*[\"“]?([^\"”\n]+)",
        r"email\s+subject\s*(?:is|:|-)\s*[\"“]?([^\"”\n]+)",
    ]

    for pattern in subject_patterns:

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if match:

            subject = clean_text(
                match.group(1)
            )

            if subject:
                return subject

    # --------------------------------------------------------
    # Common MyJobMag wording
    # --------------------------------------------------------

    position_subject_patterns = (
        "using the position as subject",
        "use the position as subject",
        "position as the subject",
        "position as subject",
        "using the job title as subject",
        "use the job title as subject",
    )

    lower_text = normalized.lower()

    if any(
        phrase in lower_text
        for phrase in position_subject_patterns
    ):

        if job_title:
            return clean_text(
                job_title
            )

    return None


# ============================================================
# APPLICATION METHOD
# ============================================================

def extract_application_method(
    page,
    text,
    job_title=None
):
    """
    Determine how the candidate is expected to apply.

    Priority:

        1. Direct external application link
        2. Employer email
        3. MyJobMag application page
        4. Unknown

    Returns:

        {
            "method": "email" | "external" |
                      "myjobmag" | "unknown",

            "email": "...",
            "subject": "...",
            "url": "..."
        }
    """

    text = text or ""

    links = extract_application_links(
        page
    )

    # --------------------------------------------------------
    # 1. Direct external application link
    # --------------------------------------------------------

    for link in links:

        url = link.get(
            "url",
            ""
        )

        if is_external_application_url(
            url
        ):

            return {
                "method": "external",
                "email": None,
                "subject": None,
                "url": url,
            }

    # --------------------------------------------------------
    # 2. Employer email
    # --------------------------------------------------------

    email = extract_email(
        text
    )

    if email:

        subject = extract_application_subject(
            text,
            job_title=job_title
        )

        return {
            "method": "email",
            "email": email,
            "subject": subject,
            "url": None,
        }

    # --------------------------------------------------------
    # 3. MyJobMag application page
    # --------------------------------------------------------

    for link in links:

        url = link.get(
            "url",
            ""
        )

        lower_url = url.lower()

        if (
            "myjobmag.co.ke/apply-now/"
            in lower_url
            or "myjobmag.co.ke/job-application/"
            in lower_url
        ):

            return {
                "method": "myjobmag",
                "email": None,
                "subject": None,
                "url": url,
            }

    # --------------------------------------------------------
    # 4. Unknown
    # --------------------------------------------------------

    return {
        "method": "unknown",
        "email": None,
        "subject": None,
        "url": None,
    }


# ============================================================
# COLLECT JOB LINKS
# ============================================================

def collect_job_links(page):
    """
    Collect job links from a MyJobMag listing page.

    Returns:

        [
            {
                "title": "...",
                "url": "..."
            }
        ]
    """

    jobs = []
    seen_urls = set()

    try:

        anchors = page.locator(
            "a[href]"
        ).all()

        for anchor in anchors:

            try:

                href = anchor.get_attribute(
                    "href"
                )

                title = clean_text(
                    anchor.inner_text()
                )

            except Exception:
                continue

            if not href:
                continue

            href = normalize_url(
                href
            )

            # Only actual MyJobMag job pages.
            if "/job/" not in href:
                continue

            if href in seen_urls:
                continue

            if not title:
                continue

            seen_urls.add(
                href
            )

            jobs.append(
                {
                    "title": title,
                    "url": href,
                }
            )

    except Exception as error:

        print(
            f"Job-link collection error: {error}"
        )

    return jobs


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(
    page,
    url
):
    """
    Navigate to and inspect one MyJobMag job.

    Returns:

        {
            "title": "...",
            "text": "...",
            "application": {
                "method": "...",
                "email": "...",
                "subject": "...",
                "url": "..."
            }
        }
    """

    print()
    print("=" * 60)
    print("INSPECTING JOB")
    print("=" * 60)

    print()
    print(
        f"URL: {url}"
    )

    # --------------------------------------------------------
    # Navigate
    # --------------------------------------------------------

    try:

        response = page.goto(
            url,
            wait_until="commit",
            timeout=30000,
        )

        print(
            "Job navigation started."
        )

        try:

            page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000,
            )

            print(
                "Job page loaded."
            )

        except Exception:

            print(
                "Page did not reach "
                "domcontentloaded. "
                "Continuing."
            )

        if response:

            print(
                f"Status: {response.status}"
            )

        page_title = page.title()

        print(
            f"Page title: {page_title}"
        )

    except Exception as error:

        print(
            f"Job navigation error: {error}"
        )

        raise

    # --------------------------------------------------------
    # Get page text
    # --------------------------------------------------------

    text = get_page_text(
        page
    )

    # --------------------------------------------------------
    # Determine job title
    # --------------------------------------------------------

    actual_title = ""

    try:

        h1 = page.locator(
            "h1"
        ).first

        if h1.count():

            actual_title = clean_text(
                h1.inner_text()
            )

    except Exception:
        pass

    if not actual_title:
        actual_title = clean_text(
            page_title
        )

    # --------------------------------------------------------
    # Application method
    # --------------------------------------------------------

    application = extract_application_method(
        page,
        text,
        job_title=actual_title,
    )

    print()
    print(
        "APPLICATION METHOD"
    )
    print("-" * 60)

    print(
        f"Method: "
        f"{application.get('method', 'unknown')}"
    )

    if application.get("email"):

        print(
            f"Email: "
            f"{application['email']}"
        )

    if application.get("subject"):

        print(
            f"Subject: "
            f"{application['subject']}"
        )

    if application.get("url"):

        print(
            f"URL: "
            f"{application['url']}"
        )

    # --------------------------------------------------------
    # Headings
    # --------------------------------------------------------

    print()
    print(
        "HEADINGS"
    )
    print("-" * 60)

    try:

        headings = page.locator(
            "h1, h2"
        ).all()

        for heading in headings:

            try:

                heading_text = clean_text(
                    heading.inner_text()
                )

                if heading_text:

                    print(
                        f"• {heading_text}"
                    )

            except Exception:
                continue

    except Exception:
        pass

    # --------------------------------------------------------
    # Application links
    # --------------------------------------------------------

    print()
    print(
        "APPLICATION-RELATED LINKS"
    )
    print("-" * 60)

    links = extract_application_links(
        page
    )

    seen_links = set()

    for link in links:

        link_url = link.get(
            "url",
            ""
        )

        if link_url in seen_links:
            continue

        seen_links.add(
            link_url
        )

        print(
            f"• {link.get('text', '')}"
        )

        print(
            f"  {link_url}"
        )

    # --------------------------------------------------------
    # Return inspection
    # --------------------------------------------------------

    return {
        "title": actual_title,
        "page_title": page_title,
        "text": text,
        "application": application,
        "application_links": links,
    }

# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    from scripts.browser.browser import launch_browser, close_browser

    playwright = None
    browser = None

    try:

        # ----------------------------------------------------
        # Launch browser
        # ----------------------------------------------------

        playwright, browser, context = launch_browser(
            headless=False
        )

        page = context.new_page()

        # ----------------------------------------------------
        # Open MyJobMag Python jobs
        # ----------------------------------------------------

        print()
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

        # ----------------------------------------------------
        # Collect jobs
        # ----------------------------------------------------

        print()
        print("Collecting job links...")
        print()

        jobs = collect_job_links(
            page
        )

        print(
            f"Found {len(jobs)} job links."
        )

        # ----------------------------------------------------
        # Display first 5
        # ----------------------------------------------------

        for index, job in enumerate(
            jobs[:5],
            start=1
        ):

            print(
                f"{index}. {job['title']}"
            )

            print(
                f"   {job['url']}"
            )

        # ----------------------------------------------------
        # Inspect first job
        # ----------------------------------------------------

        if jobs:

            first_job = jobs[0]

            print()
            print("=" * 60)
            print("TESTING FIRST JOB")
            print("=" * 60)

            result = inspect_job(
                page,
                first_job["url"]
            )

            print()
            print("=" * 60)
            print("INSPECTION COMPLETE")
            print("=" * 60)

            print()
            print(
                f"Title: {result['title']}"
            )

            print(
                f"Application method: "
                f"{result['application']['method']}"
            )

            if result["application"].get("email"):

                print(
                    f"Application email: "
                    f"{result['application']['email']}"
                )

            if result["application"].get("subject"):

                print(
                    f"Application subject: "
                    f"{result['application']['subject']}"
                )

            if result["application"].get("url"):

                print(
                    f"Application URL: "
                    f"{result['application']['url']}"
                )

    except Exception as error:

        print()
        print(
            f"MyJobMag test error: {error}"
        )

    finally:

        if browser and playwright:

            print()
            print("Closing browser...")

            close_browser(
                playwright,
                browser
            )