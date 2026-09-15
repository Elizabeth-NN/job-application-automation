
"""
BrighterMonday browser automation.

This module provides reusable Playwright functions for:

    1. Opening BrighterMonday
    2. Collecting job links
    3. Inspecting individual job pages
    4. Extracting job information
    5. Detecting the BrighterMonday application method

This module does NOT:
    - submit applications
    - automatically launch when imported
    - automatically close the browser when imported

Run directly with:

    python -m scripts.browser.brighter_monday
"""

import re

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


# ============================================================
# SETTINGS
# ============================================================

BRIGHTER_MONDAY_URL = (
    "https://www.brightermonday.co.ke/jobs"
)

BRIGHTER_MONDAY_DOMAIN = (
    "https://www.brightermonday.co.ke"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """
    Normalize whitespace in a string.
    """

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def normalize_url(url):
    """
    Convert relative BrighterMonday URLs into absolute URLs.
    """

    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return (
            BRIGHTER_MONDAY_DOMAIN
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
# JOB PAGE DEBUGGING
# ============================================================

def debug_page_links(page):
    """
    Print links currently visible on the BrighterMonday
    jobs page.

    Used while developing and maintaining the browser layer.
    """

    print()
    print("=" * 60)
    print("DEBUGGING BRIGHTERMONDAY LINKS")
    print("=" * 60)

    try:

        anchors = page.locator(
            "a[href]"
        ).all()

        print(
            f"Total anchors found: {len(anchors)}"
        )

        print()

        for index, anchor in enumerate(
            anchors[:100],
            start=1
        ):

            try:

                href = anchor.get_attribute(
                    "href"
                )

                text = clean_text(
                    anchor.inner_text()
                )

                print(
                    f"{index}. TEXT: {text[:100]}"
                )

                print(
                    f"   HREF: {href}"
                )

            except Exception as error:

                print(
                    f"{index}. "
                    f"Could not inspect anchor: {error}"
                )

    except Exception as error:

        print(
            f"Link debugging failed: {error}"
        )


def debug_job_page(page):
    """
    Print the visible text of a BrighterMonday job page.

    Used while developing and maintaining the browser layer.
    """

    print()
    print("=" * 60)
    print("DEBUGGING JOB PAGE")
    print("=" * 60)

    text = get_page_text(
        page
    )

    print()
    print(text)

    print()
    print("=" * 60)
    print("END JOB PAGE DEBUG")
    print("=" * 60)


# ============================================================
# JOB LINK VALIDATION
# ============================================================

def is_job_listing_url(url):
    """
    Determine whether a URL is a real BrighterMonday
    job listing.

    BrighterMonday job listings use:

        /listings/
    """

    if not url:
        return False

    url = url.lower()

    if "brightermonday.co.ke" not in url:
        return False

    if "/listings/" not in url:
        return False

    return True


# ============================================================
# COLLECT JOB LINKS
# ============================================================

def collect_job_links(page):
    """
    Collect real job listing links from BrighterMonday.

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

    print()
    print("Collecting job links...")
    print()

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

            if not is_job_listing_url(
                href
            ):
                continue

            if href in seen_urls:
                continue

            if not title:
                continue

            lower_title = title.lower()

            if lower_title in {
                "apply",
                "view job",
                "view jobs",
                "learn more",
                "read more",
            }:
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
            "Job-link collection error: "
            f"{error}"
        )

    return jobs


# ============================================================
# FIELD EXTRACTION
# ============================================================

def extract_field(page, labels):
    """
    Generic field extraction fallback.

    This is intentionally kept as a fallback because
    BrighterMonday's metadata is better handled by the
    dedicated extraction functions below.
    """

    if isinstance(labels, str):
        labels = [labels]

    for label in labels:

        try:

            locator = page.get_by_text(
                re.compile(
                    rf"^{re.escape(label)}$",
                    re.IGNORECASE
                )
            )

            count = locator.count()

            for index in range(count):

                element = locator.nth(
                    index
                )

                try:

                    parent = element.locator(
                        ".."
                    )

                    parent_text = clean_text(
                        parent.inner_text()
                    )

                    if not parent_text:
                        continue

                    value = re.sub(
                        rf"^{re.escape(label)}\s*:?\s*",
                        "",
                        parent_text,
                        flags=re.IGNORECASE
                    )

                    value = clean_text(
                        value
                    )

                    if (
                        value
                        and value.lower()
                        != label.lower()
                    ):

                        return value

                except Exception:
                    continue

        except Exception:
            continue

    return ""


# ============================================================
# METADATA EXTRACTION FROM PAGE TEXT
# ============================================================

def extract_metadata_value(text, label):
    """
    Extract a metadata value from the BrighterMonday
    job-page text.

    Example:

        Experience Level:
        Entry level

    returns:

        Entry level
    """

    if not text or not label:
        return ""

    pattern = (
        rf"{re.escape(label)}\s*:\s*"
        rf"([^\n]+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return ""

    return clean_text(
        match.group(1)
    )


def extract_top_posted_value(text):
    """
    Extract the posting-time value from the metadata
    appearing near the job title.

    BrighterMonday currently displays values such as:

        Yesterday
        2 days ago
        5 days ago
        1 week ago

    """

    if not text:
        return ""

    patterns = [
        r"\bToday\b",
        r"\bYesterday\b",
        r"\b\d+\s+hours?\s+ago\b",
        r"\b\d+\s+days?\s+ago\b",
        r"\b\d+\s+weeks?\s+ago\b",
        r"\b\d+\s+months?\s+ago\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return clean_text(
                match.group(0)
            )

    return ""


# ============================================================
# JOB TITLE
# ============================================================

def extract_job_title(page):
    """
    Extract the actual job title.
    """

    try:

        h1 = page.locator(
            "h1"
        ).first

        if h1.count():

            title = clean_text(
                h1.inner_text()
            )

            if title:
                return title

    except Exception:
        pass

    try:

        title = clean_text(
            page.title()
        )

        title = re.sub(
            r"\s*\|\s*BrighterMonday.*$",
            "",
            title,
            flags=re.IGNORECASE
        )

        if title:
            return title

    except Exception:
        pass

    return ""


# ============================================================
# LOCATION
# ============================================================

def extract_location(page, text):
    """
    Extract applicant/job location.

    BrighterMonday currently exposes:

        Applicant Location:
        Kenya
    """

    value = extract_metadata_value(
        text,
        "Applicant Location"
    )

    if value:
        return value

    value = extract_metadata_value(
        text,
        "Location"
    )

    if value:
        return value

    value = extract_field(
        page,
        [
            "Applicant Location",
            "Location",
            "Job Location",
        ]
    )

    return value


# ============================================================
# JOB TYPE
# ============================================================

def extract_job_type(page, text):
    """
    Extract job type / working hours.

    BrighterMonday currently exposes:

        Working Hours:
        Full Time - 8 to 5

    The broader job type is also displayed as:

        Full Time
    """

    value = extract_metadata_value(
        text,
        "Working Hours"
    )

    if value:
        return value

    # Fallback to the standalone job type value.
    try:

        lines = [
            clean_text(line)
            for line in text.splitlines()
        ]

        for index, line in enumerate(lines):

            if line.lower() == "full time":
                return line

            if line.lower() == "part time":
                return line

            if line.lower() == "contract":
                return line

            if line.lower() == "internship":
                return line

    except Exception:
        pass

    return extract_field(
        page,
        [
            "Job Type",
            "Employment Type",
        ]
    )


# ============================================================
# QUALIFICATION
# ============================================================

def extract_qualification(page, text):
    """
    Extract minimum qualification.

    BrighterMonday currently exposes:

        Min Qualification:
        Diploma
    """

    value = extract_metadata_value(
        text,
        "Min Qualification"
    )

    if value:
        return value

    value = extract_metadata_value(
        text,
        "Qualification"
    )

    if value:
        return value

    return extract_field(
        page,
        [
            "Min Qualification",
            "Qualification",
            "Qualifications",
        ]
    )


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def extract_experience_level(page, text):
    """
    Extract experience level.

    Example:

        Experience Level:
        Entry level
    """

    value = extract_metadata_value(
        text,
        "Experience Level"
    )

    if value:
        return value

    return extract_field(
        page,
        [
            "Experience Level",
        ]
    )


# ============================================================
# EXPERIENCE LENGTH
# ============================================================

def extract_experience_length(page, text):
    """
    Extract required experience length.

    Example:

        Experience Length:
        2 years
    """

    value = extract_metadata_value(
        text,
        "Experience Length"
    )

    if value:
        return value

    return extract_field(
        page,
        [
            "Experience Length",
        ]
    )


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience(page, text):
    """
    Return the most useful experience value.

    Preference:

        Experience Level

    followed by:

        Experience Length
    """

    level = extract_experience_level(
        page,
        text
    )

    length = extract_experience_length(
        page,
        text
    )

    if level and length:
        return f"{level} ({length})"

    if level:
        return level

    if length:
        return length

    return ""


# ============================================================
# POSTED
# ============================================================

def extract_posted(page, text):
    """
    Extract relative posting time.

    BrighterMonday currently displays values such as:

        Yesterday
        2 days ago
        1 week ago
    """

    return extract_top_posted_value(
        text
    )


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(page, text):
    """
    Extract the job description.

    We first look for common description sections.
    If they cannot be located, return the visible page text.
    """

    selectors = [
        "[data-testid*='description']",
        "[class*='description']",
        "[id*='description']",
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            )

            count = locator.count()

            for index in range(count):

                try:

                    value = clean_text(
                        locator.nth(
                            index
                        ).inner_text()
                    )

                    if len(value) > 200:
                        return value

                except Exception:
                    continue

        except Exception:
            continue

    return clean_text(
        text
    )


# ============================================================
# APPLICATION LINKS
# ============================================================

def extract_application_links(page):
    """
    Extract links that appear relevant to applying.
    """

    links = []

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

            if any(
                keyword in combined
                for keyword in (
                    "apply",
                    "application",
                    "career",
                    "cv",
                )
            ):

                links.append(
                    {
                        "text": text,
                        "url": href,
                    }
                )

    except Exception:
        pass

    return links


def extract_application_method(page):
    """
    Detect the BrighterMonday application method.
    """

    try:

        current_url = page.url

    except Exception:

        current_url = ""

    links = extract_application_links(
        page
    )

    for link in links:

        link_text = (
            link.get(
                "text",
                ""
            )
            .lower()
        )

        if "apply" in link_text:

            return {
                "method": "brightermonday",
                "url": link.get(
                    "url"
                ),
            }

    return {
        "method": "brightermonday",
        "url": current_url,
    }


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(page, url):
    """
    Navigate to and inspect one BrighterMonday job.

    Returns a structured job dictionary.
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
    # Validate URL
    # --------------------------------------------------------

    if not is_job_listing_url(
        url
    ):

        raise ValueError(
            "Not a valid BrighterMonday "
            f"job listing URL: {url}"
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
    # Get page text
    # --------------------------------------------------------

    text = get_page_text(
        page
    )

    # --------------------------------------------------------
    # Extract fields
    # --------------------------------------------------------

    title = extract_job_title(
        page
    )

    location = extract_location(
        page,
        text
    )

    job_type = extract_job_type(
        page,
        text
    )

    qualification = extract_qualification(
        page,
        text
    )

    experience_level = extract_experience_level(
        page,
        text
    )

    experience_length = extract_experience_length(
        page,
        text
    )

    experience = extract_experience(
        page,
        text
    )

    posted = extract_posted(
        page,
        text
    )

    description = extract_description(
        page,
        text
    )

    application = extract_application_method(
        page
    )

    # --------------------------------------------------------
    # Display information
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
        f"{location or 'Not found'}"
    )

    print(
        f"Job Type: "
        f"{job_type or 'Not found'}"
    )

    print(
        f"Qualification: "
        f"{qualification or 'Not found'}"
    )

    print(
        f"Experience Level: "
        f"{experience_level or 'Not found'}"
    )

    print(
        f"Experience Length: "
        f"{experience_length or 'Not found'}"
    )

    print(
        f"Experience: "
        f"{experience or 'Not found'}"
    )

    print(
        f"Posted: "
        f"{posted or 'Not found'}"
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
    # Return structured result
    # --------------------------------------------------------

    return {
        "title": title,
        "location": location,
        "job_type": job_type,
        "qualification": qualification,
        "experience": experience,
        "experience_level": experience_level,
        "experience_length": experience_length,
        "posted": posted,
        "description": description,
        "application": application,
        "url": url,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

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
        # Open BrighterMonday jobs page
        # ----------------------------------------------------

        print()
        print(
            "Opening BrighterMonday..."
        )

        response = page.goto(
            BRIGHTER_MONDAY_URL,
            wait_until="commit",
            timeout=60000,
        )

        print(
            "BrighterMonday navigation started."
        )

        try:

            page.wait_for_load_state(
                "domcontentloaded",
                timeout=20000,
            )

            print(
                "BrighterMonday page loaded."
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
            f"Title: {page.title()}"
        )

        # ----------------------------------------------------
        # Collect jobs
        # ----------------------------------------------------

        jobs = collect_job_links(
            page
        )

        print()
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
                f"{index}. "
                f"{job['title']}"
            )

            print(
                f"   {job['url']}"
            )

        # ----------------------------------------------------
        # Test first job
        # ----------------------------------------------------

        if jobs:

            print()
            print("=" * 60)
            print("TESTING FIRST REAL JOB")
            print("=" * 60)

            result = inspect_job(
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
                f"{result['title']}"
            )

            print(
                f"Location: "
                f"{result['location']}"
            )

            print(
                f"Job Type: "
                f"{result['job_type']}"
            )

            print(
                f"Qualification: "
                f"{result['qualification']}"
            )

            print(
                f"Experience Level: "
                f"{result['experience_level']}"
            )

            print(
                f"Experience Length: "
                f"{result['experience_length']}"
            )

            print(
                f"Experience: "
                f"{result['experience']}"
            )

            print(
                f"Posted: "
                f"{result['posted']}"
            )

            print(
                f"Description length: "
                f"{len(result['description'])}"
            )

            print(
                f"Application method: "
                f"{result['application']['method']}"
            )

        else:

            print()
            print(
                "No BrighterMonday job listings found."
            )

    except Exception as error:

        print()
        print("=" * 60)
        print(
            f"BRIGHTERMONDAY ERROR: {error}"
        )
        print("=" * 60)

    finally:

        print()
        print(
            "Closing browser..."
        )

        if browser and playwright:

            close_browser(
                playwright,
                browser
            )

