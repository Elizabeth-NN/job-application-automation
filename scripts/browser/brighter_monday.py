
"""
BrighterMonday browser automation.

Responsibilities:
- Launch Chromium using the reusable browser manager
- Collect job links from multiple listing pages
- Inspect individual job pages
- Extract structured job information
- Detect application method
- Extract application URL/email

This module is intentionally site-specific.
Generic browser functionality belongs in browser.py.
"""

import re
from urllib.parse import urljoin

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


BASE_URL = "https://www.brightermonday.co.ke"
JOBS_URL = f"{BASE_URL}/jobs"

# Number of listing pages to collect.
MAX_PAGES = 5


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(text):
    """Normalize whitespace."""
    if not text:
        return ""

    return " ".join(text.split())


def absolute_url(url):
    """Convert a relative URL into an absolute BrighterMonday URL."""
    if not url:
        return ""

    return urljoin(BASE_URL, url)


def safe_text(locator):
    """Safely get text from a Playwright locator."""
    try:
        return clean_text(locator.inner_text())
    except Exception:
        return ""


def safe_attribute(locator, attribute):
    """Safely get an element attribute."""
    try:
        return locator.get_attribute(attribute) or ""
    except Exception:
        return ""


def get_body_lines(page):
    """
    Return visible body text as cleaned non-empty lines.
    """
    try:
        body = page.locator("body").inner_text()

        lines = [
            clean_text(line)
            for line in body.splitlines()
        ]

        return [
            line
            for line in lines
            if line
        ]

    except Exception:
        return []


def get_body_text(page):
    """Return the complete cleaned body text."""
    return " ".join(get_body_lines(page))


# ============================================================
# LISTING PAGE
# ============================================================

def collect_job_links(page):
    """
    Collect job links from the currently loaded BrighterMonday
    listing page.

    BrighterMonday job URLs use:

        /listings/<job-slug>

    Returns
    -------
    list[dict]
        Example:

        {
            "title": "Sales Executive",
            "url": "https://www.brightermonday.co.ke/listings/..."
        }
    """

    print()
    print("Collecting job links...")
    print()

    jobs = []
    seen_urls = set()

    try:
        anchors = page.locator("a")

        count = anchors.count()

        for index in range(count):

            anchor = anchors.nth(index)

            href = safe_attribute(
                anchor,
                "href"
            )

            if not href:
                continue

            href = absolute_url(href)

            # Only actual job listing URLs.
            if "/listings/" not in href:
                continue

            # Avoid duplicate links on the same page.
            if href in seen_urls:
                continue

            title = safe_text(anchor)

            if not title:
                continue

            seen_urls.add(href)

            jobs.append(
                {
                    "title": title,
                    "url": href,
                }
            )

    except Exception as error:

        print(
            f"Error collecting job links: {error}"
        )

    print(
        f"Jobs found on page: {len(jobs)}"
    )

    return jobs


def collect_paginated_jobs(
    page,
    max_pages=MAX_PAGES
):
    """
    Collect jobs from multiple BrighterMonday listing pages.

    Returns unique jobs based on their URL.
    """

    print()
    print("=" * 60)
    print("BRIGHTERMONDAY PAGINATED COLLECTION")
    print("=" * 60)

    all_jobs = []
    seen_urls = set()

    for page_number in range(
        1,
        max_pages + 1
    ):

        if page_number == 1:

            url = JOBS_URL

        else:

            url = (
                f"{JOBS_URL}"
                f"?page={page_number}"
            )

        print()
        print(
            f"Listing page "
            f"{page_number}/{max_pages}"
        )

        print(
            f"URL: {url}"
        )

        try:

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("Navigation started.")

            if response:
                print(
                    f"Status: {response.status}"
                )

            else:
                print("Status: unknown")

            # Allow dynamically rendered jobs
            # to appear.
            page.wait_for_timeout(1500)

        except Exception as error:

            print(
                f"Failed to open page: {error}"
            )

            continue

        jobs = collect_job_links(page)

        new_jobs = 0

        for job in jobs:

            url = job["url"]

            if url in seen_urls:
                continue

            seen_urls.add(url)

            all_jobs.append(job)

            new_jobs += 1

        print(
            f"New jobs added: {new_jobs}"
        )

        print(
            f"Total unique jobs: "
            f"{len(all_jobs)}"
        )

    print()
    print("=" * 60)
    print("PAGINATION COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Total unique jobs collected: "
        f"{len(all_jobs)}"
    )

    return all_jobs


# ============================================================
# JOB TITLE
# ============================================================

def extract_job_title(page):
    """
    Extract the actual job title.
    """

    # BrighterMonday job pages use an h1/h2
    # around the job heading.

    selectors = [
        "h1",
        "h2",
        '[data-testid="job-title"]',
    ]

    ignored_titles = {
        "find a job",
        "search",
        "job summary",
        "job descriptions & requirements",
        "job description",
    }

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            )

            count = locator.count()

            for index in range(count):

                text = safe_text(
                    locator.nth(index)
                )

                if not text:
                    continue

                if text.lower() in ignored_titles:
                    continue

                return text

        except Exception:
            continue

    # Fallback to page title.
    try:

        title = clean_text(
            page.title()
        )

        if " at " in title:

            title = title.split(
                " at ",
                1
            )[0]

        return title

    except Exception:
        return ""


# ============================================================
# COMPANY
# ============================================================

def extract_company(page):
    """
    Extract the company name.

    BrighterMonday commonly renders the job section approximately
    as:

        Sales Executive
        Mex Logistics Africa Ltd
        Sales
        Yesterday
        Easy apply
        New
        Featured
        Kenya
        Full Time
        ...

    We therefore inspect the lines immediately following the
    actual job title and filter out known metadata.
    """

    lines = get_body_lines(page)

    title = extract_job_title(page)

    if not title:
        return ""

    ignored = {
        "job seeker",
        "blog",
        "employers",
        "help center",
        "about us",
        "login",
        "sign up",
        "post a job",
        "find a job",
        "search",
        "homepage",
        "job summary",
        "job descriptions & requirements",
        "job description",
        "easy apply",
        "featured",
        "new",
        "full time",
        "part time",
        "contract",
        "internship",
        "temporary",
        "casual",
        "sales",
        "marketing",
        "engineering & technology",
        "shipping & logistics",
        "kenya",
        "nairobi",
        "confidential",
    }

    # Locate the job title.
    title_index = None

    for index, line in enumerate(lines):

        if line.lower() == title.lower():

            title_index = index
            break

    if title_index is not None:

        # Company should normally be immediately after
        # the title.
        for index in range(
            title_index + 1,
            min(
                title_index + 8,
                len(lines)
            )
        ):

            candidate = lines[index]

            if not candidate:
                continue

            if candidate.lower() in ignored:
                continue

            # Skip obvious dates.
            if re.search(
                r"\b(today|yesterday|"
                r"hours?|days?|weeks?|months?)\b",
                candidate.lower()
            ):
                continue

            # Skip obvious job metadata.
            if candidate.lower().startswith(
                (
                    "experience",
                    "qualification",
                    "language",
                    "working hours",
                    "applicant location",
                    "job type",
                    "min qualification",
                )
            ):
                continue

            return candidate

    # Fallback: extract company from page title.
    try:

        page_title = clean_text(
            page.title()
        )

        # Example:
        #
        # Sales Executive at Mex Logistics Africa Ltd
        # | BrighterMonday

        if " at " in page_title:

            company = page_title.split(
                " at ",
                1
            )[1]

            if " | " in company:

                company = company.split(
                    " | ",
                    1
                )[0]

            # Remove date suffixes if present.
            company = re.split(
                r"\s+(?:January|February|March|April|May|June|"
                r"July|August|September|October|November|December)\b",
                company,
                maxsplit=1
            )[0]

            return clean_text(company)

    except Exception:
        pass

    return ""


# ============================================================
# METADATA
# ============================================================

def extract_value_after_label(
    lines,
    label,
    max_distance=3
):
    """
    Extract the value appearing after a metadata label.

    Example:

        Min Qualification:
        Diploma

    Returns:

        Diploma
    """

    normalized_label = (
        label.lower()
        .rstrip(":")
    )

    for index, line in enumerate(lines):

        normalized_line = (
            line.lower()
            .rstrip(":")
        )

        if normalized_line != normalized_label:
            continue

        for next_index in range(
            index + 1,
            min(
                index + 1 + max_distance,
                len(lines)
            )
        ):

            value = clean_text(
                lines[next_index]
            )

            if not value:
                continue

            return value

    return ""


def extract_job_metadata(page):
    """
    Extract structured BrighterMonday metadata.
    """

    lines = get_body_lines(page)

    metadata = {
        "location": "",
        "job_type": "",
        "qualification": "",
        "experience_level": "",
        "experience_length": "",
        "posted": "",
    }

    # --------------------------------------------------------
    # Applicant Location
    # --------------------------------------------------------

    metadata["location"] = (
        extract_value_after_label(
            lines,
            "Applicant Location:"
        )
    )

    # --------------------------------------------------------
    # Working Hours
    # --------------------------------------------------------

    metadata["job_type"] = (
        extract_value_after_label(
            lines,
            "Working Hours:"
        )
    )

    # --------------------------------------------------------
    # Qualification
    # --------------------------------------------------------

    metadata["qualification"] = (
        extract_value_after_label(
            lines,
            "Min Qualification:"
        )
    )

    # --------------------------------------------------------
    # Experience level
    # --------------------------------------------------------

    metadata["experience_level"] = (
        extract_value_after_label(
            lines,
            "Experience Level:"
        )
    )

    # --------------------------------------------------------
    # Experience length
    # --------------------------------------------------------

    metadata["experience_length"] = (
        extract_value_after_label(
            lines,
            "Experience Length:"
        )
    )

    # --------------------------------------------------------
    # Posted date
    # --------------------------------------------------------

    metadata["posted"] = extract_posted_date(
        lines
    )

    return metadata


def extract_posted_date(lines):
    """
    Extract relative posted date.

    Examples:

        Today
        Yesterday
        2 days ago
        3 weeks ago
    """

    pattern = re.compile(
        r"^(today|yesterday|"
        r"\d+\s+hours?\s+ago|"
        r"\d+\s+days?\s+ago|"
        r"\d+\s+weeks?\s+ago|"
        r"\d+\s+months?\s+ago)$",
        re.IGNORECASE
    )

    for line in lines:

        if pattern.match(line):

            return line

    return ""


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(page):
    """
    Extract the job description and requirements.
    """

    lines = get_body_lines(page)

    if not lines:
        return ""

    start_index = None

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            normalized
            == "job descriptions & requirements"
            or normalized
            == "job description & requirements"
            or normalized
            == "job description"
        ):

            start_index = index + 1

            break

    if start_index is None:

        return get_body_text(page)

    stop_phrases = {
        "important safety tips",
        "report job",
        "log in to apply",
        "continue with google",
        "continue with linkedin",
        "forgot password?",
        "don't have an account? sign up to apply",
        "sign up to apply",
        "share link",
        "similar jobs",
        "stay updated",
        "notify me",
    }

    description_lines = []

    for line in lines[start_index:]:

        normalized = line.lower()

        if normalized in stop_phrases:
            break

        if any(
            normalized.startswith(
                phrase
            )
            for phrase in stop_phrases
        ):
            break

        description_lines.append(
            line
        )

    return clean_text(
        " ".join(description_lines)
    )


# ============================================================
# APPLICATION METHOD
# ============================================================

def extract_application_method(page):
    """
    Determine the application method.

    Possible values:

        brightermonday
        email
        external
        unknown
    """

    lines = get_body_lines(page)

    body_text = " ".join(lines).lower()

    # --------------------------------------------------------
    # BrighterMonday internal application
    # --------------------------------------------------------

    if (
        "log in to apply" in body_text
        or "sign up to apply" in body_text
        or "easy apply" in body_text
    ):

        return "brightermonday"

    # --------------------------------------------------------
    # Email application
    # --------------------------------------------------------

    try:

        mailto = page.locator(
            'a[href^="mailto:"]'
        )

        if mailto.count() > 0:

            return "email"

    except Exception:
        pass

    # Search page text.
    emails = re.findall(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        body_text
    )

    if emails:

        return "email"

    # --------------------------------------------------------
    # External application
    # --------------------------------------------------------

    try:

        anchors = page.locator("a")

        count = anchors.count()

        for index in range(count):

            anchor = anchors.nth(index)

            href = safe_attribute(
                anchor,
                "href"
            )

            if not href:
                continue

            href = absolute_url(href)

            if (
                "apply" in href.lower()
                and "brightermonday.co.ke"
                not in href.lower()
            ):

                return "external"

    except Exception:
        pass

    return "unknown"


# ============================================================
# APPLICATION URL
# ============================================================

def extract_application_url(page):
    """
    Extract BrighterMonday or external application URL.
    """

    try:

        anchors = page.locator("a")

        count = anchors.count()

        for index in range(count):

            anchor = anchors.nth(index)

            href = safe_attribute(
                anchor,
                "href"
            )

            if not href:
                continue

            href = absolute_url(href)

            text = safe_text(
                anchor
            ).lower()

            # Internal application button.
            if (
                "log in and apply" in text
                or "sign up to apply" in text
            ):

                return href

            # BrighterMonday apply URL.
            if (
                "/account/customer/sign-up"
                in href
                and "apply=" in href
            ):

                return href

            # External application.
            if (
                "apply" in text
                and "brightermonday.co.ke"
                not in href
            ):

                return href

    except Exception:
        pass

    return ""


# ============================================================
# APPLICATION EMAIL
# ============================================================

def extract_application_email(page):
    """
    Extract an application email address.
    """

    # First check mailto links.
    try:

        mailto = page.locator(
            'a[href^="mailto:"]'
        )

        count = mailto.count()

        for index in range(count):

            href = safe_attribute(
                mailto.nth(index),
                "href"
            )

            if not href:
                continue

            if href.lower().startswith(
                "mailto:"
            ):

                email = (
                    href[7:]
                    .split("?", 1)[0]
                    .strip()
                )

                if email:
                    return email

    except Exception:
        pass

    # Fallback: search page text.
    body_text = get_body_text(page)

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        body_text
    )

    if emails:

        return emails[0]

    return ""


# ============================================================
# COMPLETE JOB INSPECTION
# ============================================================

def inspect_job(
    page,
    job_url
):
    """
    Inspect one BrighterMonday job page.

    Returns a structured dictionary.
    """

    print()
    print("=" * 60)
    print("INSPECTING BRIGHTERMONDAY JOB")
    print("=" * 60)

    print()
    print(
        f"URL: {job_url}"
    )

    try:

        response = page.goto(
            job_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("Navigation started.")

        if response:

            print(
                f"Status: {response.status}"
            )

        else:

            print(
                "Status: unknown"
            )

        print(
            "Job page loaded."
        )

        # Allow dynamic content to finish rendering.
        page.wait_for_timeout(1200)

    except Exception as error:

        print(
            f"Failed to load job page: "
            f"{error}"
        )

        return {
            "title": "",
            "company": "",
            "url": job_url,
            "location": "",
            "job_type": "",
            "qualification": "",
            "experience_level": "",
            "experience_length": "",
            "experience": "",
            "posted": "",
            "description": "",
            "application_method": "unknown",
            "application_url": "",
            "application_email": "",
        }

    # --------------------------------------------------------
    # Extract fields
    # --------------------------------------------------------

    title = extract_job_title(
        page
    )

    company = extract_company(
        page
    )

    metadata = extract_job_metadata(
        page
    )

    description = extract_description(
        page
    )

    application_method = (
        extract_application_method(
            page
        )
    )

    application_url = (
        extract_application_url(
            page
        )
    )

    application_email = (
        extract_application_email(
            page
        )
    )

    # --------------------------------------------------------
    # Combine experience
    # --------------------------------------------------------

    experience = ""

    if metadata["experience_level"]:

        experience = (
            metadata["experience_level"]
        )

        if metadata[
            "experience_length"
        ]:

            experience += (
                f" "
                f"({metadata['experience_length']})"
            )

    elif metadata[
        "experience_length"
    ]:

        experience = (
            metadata["experience_length"]
        )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print()
    print("JOB INFORMATION")
    print("-" * 60)

    print(
        f"Title: "
        f"{title or 'Not found'}"
    )

    print(
        f"Company: "
        f"{company or 'Not found'}"
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
        f"Experience Level: "
        f"{metadata['experience_level'] or 'Not found'}"
    )

    print(
        f"Experience Length: "
        f"{metadata['experience_length'] or 'Not found'}"
    )

    print(
        f"Experience: "
        f"{experience or 'Not found'}"
    )

    print(
        f"Posted: "
        f"{metadata['posted'] or 'Not found'}"
    )

    print(
        f"Description length: "
        f"{len(description)}"
    )

    print()
    print("APPLICATION METHOD")
    print("-" * 60)

    print(
        f"Method: "
        f"{application_method}"
    )

    if application_email:

        print(
            f"Email: "
            f"{application_email}"
        )

    if application_url:

        print(
            f"URL: "
            f"{application_url}"
        )

    return {
        "title": title,
        "company": company,
        "url": job_url,
        "location": metadata["location"],
        "job_type": metadata["job_type"],
        "qualification": metadata["qualification"],
        "experience_level": metadata["experience_level"],
        "experience_length": metadata["experience_length"],
        "experience": experience,
        "posted": metadata["posted"],
        "description": description,
        "application_method": application_method,
        "application_url": application_url,
        "application_email": application_email,
    }


# ============================================================
# MAIN TEST
# ============================================================

def main():
    """
    Run a standalone BrighterMonday browser test.
    """

    playwright = None
    browser = None
    context = None

    try:

        # ----------------------------------------------------
        # Launch browser
        # ----------------------------------------------------

        playwright, browser, context = (
            launch_browser(
                headless=False
            )
        )

        page = context.new_page()

        # ----------------------------------------------------
        # Open BrighterMonday
        # ----------------------------------------------------

        print()
        print(
            "Opening BrighterMonday..."
        )

        response = page.goto(
            JOBS_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print(
            "Navigation started."
        )

        if response:

            print(
                f"Status: {response.status}"
            )

        else:

            print(
                "Status: unknown"
            )

        print(
            f"Page title: "
            f"{page.title()}"
        )

        page.wait_for_timeout(
            1500
        )

        # ----------------------------------------------------
        # Collect all jobs
        # ----------------------------------------------------

        jobs = collect_paginated_jobs(
            page,
            max_pages=MAX_PAGES
        )

        print()
        print(
            f"Found {len(jobs)} "
            f"unique job links."
        )

        # Display first five.
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
        # Test first real job
        # ----------------------------------------------------

        if not jobs:

            print()
            print(
                "No BrighterMonday "
                "job listings found."
            )

            return

        print()
        print("=" * 60)
        print(
            "TESTING FIRST REAL JOB"
        )
        print("=" * 60)

        result = inspect_job(
            page,
            jobs[0]["url"]
        )

        # ----------------------------------------------------
        # Final summary
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print(
            "INSPECTION COMPLETE"
        )
        print("=" * 60)

        print()
        print(
            f"Title: "
            f"{result['title']}"
        )

        print(
            f"Company: "
            f"{result['company']}"
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
            f"{result['application_method']}"
        )

        if result[
            "application_email"
        ]:

            print(
                f"Application email: "
                f"{result['application_email']}"
            )

        if result[
            "application_url"
        ]:

            print(
                f"Application URL: "
                f"{result['application_url']}"
            )

    except Exception as error:

        print()
        print("ERROR")
        print("-" * 60)
        print(error)

    finally:

        print()
        print(
            "Closing browser..."
        )

        if browser and playwright:

            try:

                close_browser(
                    playwright,
                    browser
                )

            except Exception as error:

                print(
                    f"Error closing browser: "
                    f"{error}"
                )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

