
"""
BrighterMonday browser automation.

This module provides reusable Playwright functions for:

    1. Opening BrighterMonday
    2. Collecting job links
    3. Inspecting individual job pages
    4. Extracting job information
    5. Extracting application information

This module does NOT:

    - launch Chromium automatically when imported
    - close Chromium automatically
    - submit applications

Browser lifecycle is handled by:

    scripts.browser.browser
"""

import re


# ============================================================
# SETTINGS
# ============================================================

BRIGHTER_MONDAY_URL = (
    "https://www.brightermonday.co.ke/jobs"
)

BRIGHTER_MONDAY_DOMAIN = (
    "brightermonday.co.ke"
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
    """
    Ensure BrighterMonday URLs are absolute.
    """

    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return (
            "https://www.brightermonday.co.ke"
            + url
        )

    return url


def get_page_text(page):
    """
    Safely return visible page text.
    """

    try:

        return page.locator(
            "body"
        ).inner_text()

    except Exception:

        return ""


# ============================================================
# EMAIL EXTRACTION
# ============================================================

def extract_emails(text):
    """
    Extract email addresses from text.
    """

    if not text:
        return []

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    return list(
        dict.fromkeys(
            email.lower().strip()
            for email in emails
        )
    )


def extract_application_email(text):
    """
    Extract an application email address.

    BrighterMonday/platform emails are ignored where possible.
    """

    emails = extract_emails(
        text
    )

    for email in emails:

        if (
            email.endswith(
                "@brightermonday.co.ke"
            )
            or email.endswith(
                "@brightermonday.com"
            )
        ):
            continue

        return email

    return None


# ============================================================
# APPLICATION LINKS
# ============================================================

def extract_application_links(page):
    """
    Extract links that appear related to applying.

    Returns:

        [
            {
                "text": "...",
                "url": "..."
            }
        ]
    """

    links = []
    seen = set()

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

            if not any(
                keyword in combined
                for keyword in (
                    "apply",
                    "application",
                    "career",
                    "workday",
                    "greenhouse",
                    "lever",
                    "ashby",
                    "smartrecruiters",
                )
            ):

                continue

            if href in seen:

                continue

            seen.add(
                href
            )

            links.append(
                {
                    "text": text,
                    "url": href,
                }
            )

    except Exception as error:

        print(
            "Application-link extraction error: "
            f"{error}"
        )

    return links


# ============================================================
# APPLICATION METHOD
# ============================================================

def extract_application_method(
    page,
    text
):
    """
    Determine how the candidate is expected to apply.

    Possible methods:

        email
        external
        brightermonday
        unknown
    """

    text = text or ""

    links = extract_application_links(
        page
    )

    # --------------------------------------------------------
    # 1. Employer email
    # --------------------------------------------------------

    email = extract_application_email(
        text
    )

    if email:

        subject = extract_application_subject(
            text
        )

        return {
            "method": "email",
            "email": email,
            "subject": subject,
            "url": None,
        }

    # --------------------------------------------------------
    # 2. Direct external application
    # --------------------------------------------------------

    for link in links:

        url = link.get(
            "url",
            ""
        )

        if not url:
            continue

        lower_url = url.lower()

        if (
            lower_url.startswith("http")
            and BRIGHTER_MONDAY_DOMAIN
            not in lower_url
        ):

            return {
                "method": "external",
                "email": None,
                "subject": None,
                "url": url,
            }

    # --------------------------------------------------------
    # 3. BrighterMonday application page/button
    # --------------------------------------------------------

    for link in links:

        url = link.get(
            "url",
            ""
        )

        lower_url = url.lower()

        if (
            BRIGHTER_MONDAY_DOMAIN
            in lower_url
        ):

            return {
                "method": "brightermonday",
                "email": None,
                "subject": None,
                "url": url,
            }

    # --------------------------------------------------------
    # 4. Look for application instructions
    # --------------------------------------------------------

    lower_text = text.lower()

    if any(
        phrase in lower_text
        for phrase in (
            "apply on brightermonday",
            "apply through brightermonday",
            "apply via brightermonday",
        )
    ):

        return {
            "method": "brightermonday",
            "email": None,
            "subject": None,
            "url": None,
        }

    # --------------------------------------------------------
    # 5. Unknown
    # --------------------------------------------------------

    return {
        "method": "unknown",
        "email": None,
        "subject": None,
        "url": None,
    }


def extract_application_subject(text):
    """
    Attempt to identify an email application subject.

    Returns None when no reliable subject is found.
    """

    if not text:
        return None

    patterns = [
        (
            r"subject(?:\s+line)?\s*[:\-]\s*"
            r"[\"']?([^\"'\n]+)"
        ),
        (
            r"use\s+(?:the\s+)?"
            r"position\s+as\s+subject"
        ),
        (
            r"subject\s+of\s+email"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        if match.lastindex:

            value = clean_text(
                match.group(1)
            )

        else:

            value = clean_text(
                match.group(0)
            )

        if value:

            return value

    return None


# ============================================================
# JOB METADATA EXTRACTION
# ============================================================

def extract_job_title(
    page
):
    """
    Extract the most likely job title.
    """

    selectors = [
        "h1",
        "[data-testid='job-title']",
        ".job-title",
        ".title",
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            )

            if locator.count() == 0:
                continue

            value = clean_text(
                locator.first.inner_text()
            )

            if value:

                return value

        except Exception:

            continue

    return ""


def extract_metadata_value(
    page,
    labels
):
    """
    Try to extract a metadata value based on
    common BrighterMonday labels.

    This is intentionally defensive because
    page layouts can change.
    """

    for label in labels:

        try:

            locator = page.get_by_text(
                label,
                exact=False
            )

            if locator.count() == 0:

                continue

            for index in range(
                min(locator.count(), 5)
            ):

                try:

                    element = locator.nth(
                        index
                    )

                    parent = element.locator(
                        ".."
                    )

                    text = clean_text(
                        parent.inner_text()
                    )

                    if (
                        text
                        and len(text) > len(label)
                    ):

                        return text

                except Exception:

                    continue

        except Exception:

            continue

    return ""


def extract_job_metadata(
    page
):
    """
    Extract common job metadata.

    Returns:

        {
            "location": "...",
            "job_type": "...",
            "qualification": "...",
            "experience": "...",
            "posted": "..."
        }
    """

    metadata = {
        "location": "",
        "job_type": "",
        "qualification": "",
        "experience": "",
        "posted": "",
    }

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    metadata["location"] = extract_metadata_value(
        page,
        [
            "Location",
            "Locations",
        ]
    )

    # --------------------------------------------------------
    # Job type
    # --------------------------------------------------------

    metadata["job_type"] = extract_metadata_value(
        page,
        [
            "Job Type",
            "Employment Type",
            "Job type",
        ]
    )

    # --------------------------------------------------------
    # Qualification
    # --------------------------------------------------------

    metadata["qualification"] = extract_metadata_value(
        page,
        [
            "Qualification",
            "Qualifications",
            "Education",
        ]
    )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    metadata["experience"] = extract_metadata_value(
        page,
        [
            "Experience",
            "Experience Level",
            "Experience Length",
        ]
    )

    # --------------------------------------------------------
    # Posted
    # --------------------------------------------------------

    metadata["posted"] = extract_metadata_value(
        page,
        [
            "Posted",
            "Posted Date",
            "Date Posted",
        ]
    )

    return metadata


# ============================================================
# DESCRIPTION EXTRACTION
# ============================================================

def extract_description(
    page
):
    """
    Extract the main visible job description.

    Uses several possible selectors and falls back
    to body text when necessary.
    """

    selectors = [
        "[data-testid='job-description']",
        ".job-description",
        ".job-description-content",
        ".description",
        "article",
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            )

            if locator.count() == 0:

                continue

            texts = []

            for index in range(
                min(locator.count(), 5)
            ):

                try:

                    value = clean_text(
                        locator.nth(
                            index
                        ).inner_text()
                    )

                    if value:

                        texts.append(
                            value
                        )

                except Exception:

                    continue

            if texts:

                description = "\n".join(
                    texts
                )

                if len(description) >= 100:

                    return description

        except Exception:

            continue

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return get_page_text(
        page
    )


# ============================================================
# COLLECT JOB LINKS
# ============================================================

def collect_job_links(
    page
):
    """
    Collect job links from a BrighterMonday
    listing page.

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

            lower_url = href.lower()

            # Only BrighterMonday job pages.
            if (
                BRIGHTER_MONDAY_DOMAIN
                not in lower_url
            ):

                continue

            # Avoid navigation/category links.
            if not any(
                indicator in lower_url
                for indicator in (
                    "/listings/",
                    "/jobs/",
                    "/job/",
                )
            ):

                continue

            if href in seen_urls:

                continue

            if not title:

                continue

            # Remove obvious navigation text.
            if title.lower() in (
                "apply now",
                "view job",
                "read more",
                "see more",
                "learn more",
            ):

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
    Navigate to and inspect one BrighterMonday job.

    Returns:

        {
            "title": "...",
            "text": "...",
            "description": "...",
            "metadata": {...},
            "application": {...}
        }
    """

    print()
    print("=" * 60)
    print("INSPECTING BRIGHTERMONDAY JOB")
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

        print(
            f"Page title: {page.title()}"
        )

    except Exception as error:

        print(
            f"Job navigation error: {error}"
        )

        raise

    # --------------------------------------------------------
    # Page text
    # --------------------------------------------------------

    text = get_page_text(
        page
    )

    # --------------------------------------------------------
    # Job title
    # --------------------------------------------------------

    title = extract_job_title(
        page
    )

    if not title:

        title = clean_text(
            page.title()
        )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = extract_job_metadata(
        page
    )

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    description = extract_description(
        page
    )

    # --------------------------------------------------------
    # Application method
    # --------------------------------------------------------

    application = extract_application_method(
        page,
        text,
    )

    # --------------------------------------------------------
    # Display metadata
    # --------------------------------------------------------

    print()
    print(
        "JOB INFORMATION"
    )
    print("-" * 60)

    print(
        f"Title: "
        f"{title or 'Not found'}"
    )

    print(
        f"Location: "
        f"{metadata['location'] or 'Not found'}"
    )

    print(
        f"Job Type: "
        f"{metadata['job_type'] or 'Not found'}"
    )

    print(
        f"Qualification: "
        f"{metadata['qualification'] or 'Not found'}"
    )

    print(
        f"Experience: "
        f"{metadata['experience'] or 'Not found'}"
    )

    print(
        f"Posted: "
        f"{metadata['posted'] or 'Not found'}"
    )

    print(
        f"Description length: "
        f"{len(description)}"
    )

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

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

    for link in links:

        print(
            f"• {link.get('text', '')}"
        )

        print(
            f"  {link.get('url', '')}"
        )

    # --------------------------------------------------------
    # Return inspection
    # --------------------------------------------------------

    return {
        "title": title,
        "text": text,
        "description": description,
        "metadata": metadata,
        "application": application,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    from scripts.browser.browser import (
        launch_browser,
        close_browser,
    )

    playwright = None
    browser = None

    try:

        playwright, browser, context = launch_browser(
            headless=False
        )

        page = context.new_page()

        print()
        print(
            "Opening BrighterMonday..."
        )

        response = page.goto(
            BRIGHTER_MONDAY_URL,
            wait_until="commit",
            timeout=30000,
        )

        try:

            page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000,
            )

        except Exception:

            pass

        print(
            "BrighterMonday page loaded."
        )

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
        print(
            "Collecting job links..."
        )

        jobs = collect_job_links(
            page
        )

        print()
        print(
            f"Found {len(jobs)} job links."
        )

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

            print()
            print("=" * 60)
            print("TESTING FIRST JOB")
            print("=" * 60)

            inspection = inspect_job(
                page,
                jobs[0]["url"]
            )

            print()
            print("=" * 60)
            print("INSPECTION COMPLETE")
            print("=" * 60)

            print()
            print(
                f"Title: "
                f"{inspection['title']}"
            )

            print(
                f"Location: "
                f"{inspection['metadata']['location']}"
            )

            print(
                f"Job Type: "
                f"{inspection['metadata']['job_type']}"
            )

            print(
                f"Qualification: "
                f"{inspection['metadata']['qualification']}"
            )

            print(
                f"Experience: "
                f"{inspection['metadata']['experience']}"
            )

            print(
                f"Posted: "
                f"{inspection['metadata']['posted']}"
            )

            print(
                f"Description length: "
                f"{len(inspection['description'])}"
            )

            print(
                f"Application method: "
                f"{inspection['application']['method']}"
            )

    except Exception as error:

        print()
        print(
            f"Automation error: {error}"
        )

    finally:

        if browser and playwright:

            print()
            print(
                "Closing browser..."
            )

            close_browser(
                playwright,
                browser
            )
