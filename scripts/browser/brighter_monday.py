
"""
BrighterMonday browser-based job collector.

Collects technology jobs from the BrighterMonday Software & Data
category and extracts structured information from individual listings.

Run with:

    python -m scripts.browser.brighter_monday
"""

import re
import time
from datetime import datetime
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


BASE_URL = "https://www.brightermonday.co.ke"
LISTING_URL = f"{BASE_URL}/jobs/software-data"

MAX_PAGES = 5


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

def launch_browser(playwright):
    """Launch Chromium and return browser + page."""
    browser = playwright.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    )

    print("Chromium launched successfully.")

    return browser, page


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def navigate(page, url, timeout=60000):
    """Navigate to a URL and return the response."""
    print("Navigation started.")

    try:
        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout,
        )

        status = response.status if response else None

        print(f"Status: {status}")

        return response

    except PlaywrightTimeoutError:
        print("Navigation timed out.")

        return None

    except Exception as exc:
        print(f"Navigation error: {exc}")

        return None


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def clean_text(value):
    """Normalize whitespace in text."""
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def normalize_label(value):
    """Normalize labels for comparisons."""
    return clean_text(value).lower().rstrip(":")


def extract_first_match(text, patterns, default="Not found"):
    """Return the first regex match from a list of patterns."""
    if not text:
        return default

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            value = clean_text(match.group(1))

            if value:
                return value

    return default


def parse_date(value):
    """
    Normalize ISO dates and common date strings.

    Returns the original cleaned value when it cannot be parsed.
    """
    value = clean_text(value)

    if not value or value == "Not found":
        return "Not found"

    # ISO datetime:
    # 2026-09-08T00:00:00.000000Z
    iso_match = re.match(r"(\d{4}-\d{2}-\d{2})", value)

    if iso_match:
        return iso_match.group(1)

    # Common formats.
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%d %b %Y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return value


# ---------------------------------------------------------------------------
# Listing collection
# ---------------------------------------------------------------------------

def get_listing_job_cards(page):
    """
    Extract job cards from the current BrighterMonday listing page.

    Returns:
        list[dict]
    """

    cards = []

    # Try several common selectors because BrighterMonday's markup can vary.
    selectors = [
        "a[href*='/listings/']",
        "article a[href*='/listings/']",
        "[data-testid*='job'] a[href*='/listings/']",
    ]

    elements = []

    for selector in selectors:
        try:
            found = page.locator(selector).all()

            if found:
                elements = found
                break

        except Exception:
            continue

    seen_urls = set()

    for element in elements:
        try:
            href = element.get_attribute("href")
            text = clean_text(element.inner_text())

            if not href:
                continue

            url = urljoin(BASE_URL, href)

            if "/listings/" not in url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            # The anchor text is sometimes the title and sometimes
            # contains additional information. Keep the first useful line.
            title = text.split("\n")[0].strip()

            if not title:
                continue

            cards.append(
                {
                    "title": title,
                    "url": url,
                }
            )

        except Exception:
            continue

    return cards


def is_technology_job(job):
    """
    Filter jobs relevant to the user's technology/software targets.

    The browser layer intentionally performs broad filtering.
    Detailed matching happens later in job_matcher.py.
    """

    title = clean_text(job.get("title", "")).lower()

    technology_keywords = [
        "software",
        "developer",
        "development",
        "programmer",
        "programming",
        "engineer",
        "engineering",
        "python",
        "flask",
        "react",
        "frontend",
        "front-end",
        "backend",
        "back-end",
        "full stack",
        "fullstack",
        "web developer",
        "website developer",
        "data analyst",
        "data scientist",
        "data science",
        "data engineer",
        "database",
        "devops",
        "cloud",
        "systems",
        "it assistant",
        "applications",
        "dynamics",
        "technology",
        "technical",
        "qa engineer",
        "quality assurance",
    ]

    return any(keyword in title for keyword in technology_keywords)


def collect_job_links(page):
    """
    Collect unique technology job links across listing pages.
    """

    all_jobs = []
    seen_urls = set()

    print()
    print("=" * 60)
    print("BRIGHTERMONDAY SOFTWARE & DATA COLLECTION")
    print("=" * 60)

    for page_number in range(1, MAX_PAGES + 1):

        if page_number == 1:
            url = LISTING_URL
        else:
            url = f"{LISTING_URL}?page={page_number}"

        print()
        print(f"Listing page {page_number}/{MAX_PAGES}")
        print(f"URL: {url}")

        response = navigate(page, url)

        if not response:
            print("Could not load page.")
            continue

        status = response.status

        if status == 404:
            print("Page does not exist (404).")
            print("Stopping pagination.")
            break

        if status >= 400:
            print(f"Unexpected HTTP status: {status}")
            continue

        # Allow client-side content to finish rendering.
        try:
            page.wait_for_timeout(1500)
        except Exception:
            pass

        print()
        print("Collecting job links...")

        jobs = get_listing_job_cards(page)

        print()
        print(f"Jobs found on page: {len(jobs)}")

        technology_count = 0
        non_technology_count = 0

        for job in jobs:

            if not is_technology_job(job):
                non_technology_count += 1
                continue

            technology_count += 1

            if job["url"] in seen_urls:
                continue

            seen_urls.add(job["url"])
            all_jobs.append(job)

        print(f"New technology jobs added: {technology_count}")
        print(f"Non-technology jobs filtered: {non_technology_count}")
        print(f"Total technology jobs: {len(all_jobs)}")

    print()
    print("=" * 60)
    print("SOFTWARE & DATA COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Total unique technology jobs: {len(all_jobs)}")

    return all_jobs


# ---------------------------------------------------------------------------
# Job detail extraction
# ---------------------------------------------------------------------------

def get_page_text(page):
    """Return cleaned visible text from the current page."""
    try:
        return clean_text(page.locator("body").inner_text())
    except Exception:
        return ""


def extract_job_title(page, body_text):
    """Extract job title."""
    selectors = [
        "h1",
        "[data-testid='job-title']",
        "[class*='job-title']",
        "[class*='listing-title']",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count():
                value = clean_text(locator.inner_text())

                if value:
                    return value

        except Exception:
            continue

    return extract_first_match(
        body_text,
        [
            r"Job Title\s*:?\s*(.+?)(?:Company|Location|Job Type|Qualification)",
        ],
    )


def extract_company(page, body_text):
    """Extract company name."""
    selectors = [
        "[data-testid='company-name']",
        "[class*='company-name']",
        "[class*='company']",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count():
                value = clean_text(locator.inner_text())

                if value and len(value) < 150:
                    return value

        except Exception:
            continue

    return extract_first_match(
        body_text,
        [
            r"Company\s*:?\s*(.+?)(?:Location|Job Type|Qualification|Experience)",
        ],
    )


def extract_summary_value(body_text, label):
    """
    Extract a value from BrighterMonday's job-summary section.

    The page text can be arranged differently depending on the listing,
    so this function uses bounded patterns rather than fixed selectors.
    """

    next_labels = (
        r"(?:Location|Job Type|Qualification|Language Requirement|"
        r"Working Hours|Applicant Location|Experience Level|"
        r"Experience Length|Experience|Posted|Deadline|"
        r"Job descriptions & requirements|Description)"
    )

    pattern = rf"{re.escape(label)}\s*:?\s*(.*?)(?=\s+{next_labels}\s*:|\Z)"

    return extract_first_match(body_text, [pattern])


def extract_location(page, body_text):
    """Extract location without accidentally capturing the description."""
    selectors = [
        "[data-testid='location']",
        "[class*='location']",
    ]

    for selector in selectors:
        try:
            locators = page.locator(selector).all()

            for locator in locators:
                value = clean_text(locator.inner_text())

                if not value:
                    continue

                # Reject obvious non-location content.
                lowered = value.lower()

                if (
                    len(value) <= 100
                    and "job description" not in lowered
                    and "requirements" not in lowered
                    and "department" not in lowered
                ):
                    return value

        except Exception:
            continue

    value = extract_summary_value(body_text, "Location")

    if value == "Not found":
        return value

    # Remove common contamination.
    value = re.split(
        r"\s+(?:Job descriptions & requirements|Department|Reports To)\b",
        value,
        flags=re.IGNORECASE,
    )[0]

    return clean_text(value) or "Not found"


def extract_job_type(page, body_text):
    """Extract employment type."""
    selectors = [
        "[data-testid='job-type']",
        "[class*='job-type']",
    ]

    for selector in selectors:
        try:
            locators = page.locator(selector).all()

            for locator in locators:
                value = clean_text(locator.inner_text())

                if value and len(value) <= 100:
                    return value

        except Exception:
            continue

    value = extract_summary_value(body_text, "Job Type")

    return value


def extract_qualification(page, body_text):
    """Extract qualification."""
    value = extract_summary_value(body_text, "Qualification")

    if value != "Not found":
        value = re.split(
            r"\s+(?:Language Requirement|Working Hours|Applicant Location|"
            r"Experience Level|Experience Length|Experience|Posted|Deadline)\b",
            value,
            flags=re.IGNORECASE,
        )[0]

    return clean_text(value) or "Not found"


def extract_experience(page, body_text):
    """
    Extract experience length and experience level.

    Experience may appear as:
        4 years
        3 years
        1 month
        Mid level
        Entry level

    The page sometimes places the experience requirement inside the
    description rather than in a dedicated summary field.
    """

    experience_length = "Not found"
    experience_level = "Not found"

    # First try the explicit summary labels.
    summary_length = extract_summary_value(
        body_text,
        "Experience Length",
    )

    if summary_length != "Not found":
        summary_length = re.split(
            r"\s+(?:Experience|Posted|Deadline|Job descriptions & requirements)\b",
            summary_length,
            flags=re.IGNORECASE,
        )[0]

        experience_length = clean_text(summary_length)

    summary_level = extract_summary_value(
        body_text,
        "Experience Level",
    )

    if summary_level != "Not found":
        summary_level = re.split(
            r"\s+(?:Experience Length|Experience|Posted|Deadline|"
            r"Job descriptions & requirements)\b",
            summary_level,
            flags=re.IGNORECASE,
        )[0]

        experience_level = clean_text(summary_level)

    # If no dedicated experience length exists, search the job text.
    if experience_length == "Not found":
        match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(years?|months?|weeks?)\s+(?:of\s+)?"
            r"(?:relevant\s+)?experience\b",
            body_text,
            flags=re.IGNORECASE,
        )

        if match:
            experience_length = clean_text(match.group(0))

    # Common level indicators.
    if experience_level == "Not found":
        level_patterns = [
            r"\bentry[\s-]?level\b",
            r"\bjunior\b",
            r"\bgraduate\b",
            r"\bintern(?:ship)?\b",
            r"\bmid[\s-]?level\b",
            r"\bintermediate\b",
            r"\bsenior\b",
            r"\blead\b",
            r"\bmanager\b",
        ]

        for pattern in level_patterns:
            match = re.search(
                pattern,
                body_text,
                flags=re.IGNORECASE,
            )

            if match:
                experience_level = clean_text(match.group(0))
                break

    # Experience field follows the same value in the site's summary.
    experience = experience_length

    if experience == "Not found" and experience_level != "Not found":
        experience = experience_level

    return experience_level, experience_length, experience


def extract_posted_date(page, body_text):
    """Extract posted date."""
    value = extract_summary_value(body_text, "Posted")

    if value == "Not found":
        # Try common relative date patterns.
        match = re.search(
            r"\b(?:posted\s+)?"
            r"(?:today|yesterday|\d+\s+(?:day|days|week|weeks|month|months)\s+ago)\b",
            body_text,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(match.group(0))

    return parse_date(value)


def extract_deadline(page, body_text):
    """Extract application deadline."""
    value = extract_summary_value(body_text, "Deadline")

    return parse_date(value)


def extract_description(page, body_text):
    """
    Extract the job description and requirements.

    Prefer the dedicated description container. Fall back to body text
    between the job-description section and application UI.
    """

    selectors = [
        "[data-testid='job-description']",
        "[class*='job-description']",
        "[class*='description']",
    ]

    candidates = []

    for selector in selectors:
        try:
            locators = page.locator(selector).all()

            for locator in locators:
                text = clean_text(locator.inner_text())

                if len(text) > 200:
                    candidates.append(text)

        except Exception:
            continue

    if candidates:
        # Usually the longest candidate is the actual job description.
        return max(candidates, key=len)

    # Fallback: locate the description section in body text.
    description = body_text

    start_patterns = [
        r"Job descriptions & requirements",
        r"Job Description",
        r"Description",
        r"Role Overview",
    ]

    start_position = None

    for pattern in start_patterns:
        match = re.search(
            pattern,
            body_text,
            flags=re.IGNORECASE,
        )

        if match:
            start_position = match.start()
            break

    if start_position is not None:
        description = body_text[start_position:]

    # Remove application/footer content.
    end_patterns = [
        r"\bLog in to apply now\b",
        r"\bContinue with Google\b",
        r"\bContinue with Linkedin\b",
        r"\bForgot Password\b",
        r"\bSimilar jobs\b",
        r"\bStay Updated\b",
        r"\bAbout Companies Hiring\b",
        r"\bPrivacy Policy\b",
    ]

    end_position = None

    for pattern in end_patterns:
        match = re.search(
            pattern,
            description,
            flags=re.IGNORECASE,
        )

        if match:
            if end_position is None or match.start() < end_position:
                end_position = match.start()

    if end_position is not None:
        description = description[:end_position]

    return clean_text(description)


# ---------------------------------------------------------------------------
# Application extraction
# ---------------------------------------------------------------------------

def extract_application_url(page):
    """Extract the BrighterMonday application URL."""

    selectors = [
        "a[href*='apply=']",
        "a[href*='/account/customer/']",
    ]

    for selector in selectors:
        try:
            locators = page.locator(selector).all()

            for locator in locators:
                href = locator.get_attribute("href")

                if href and ("apply=" in href or "/account/customer/" in href):
                    return urljoin(BASE_URL, href)

        except Exception:
            continue

    # Search page links as a fallback.
    try:
        links = page.locator("a").all()

        for link in links:
            href = link.get_attribute("href")

            if href and "apply=" in href:
                return urljoin(BASE_URL, href)

    except Exception:
        pass

    return "Not found"


def extract_application_method(page):
    """Return the application method."""
    return "brightermonday"


# ---------------------------------------------------------------------------
# Individual job
# ---------------------------------------------------------------------------

def get_job_details(page, job):
    """
    Visit a BrighterMonday job listing and extract structured data.
    """

    url = job["url"]

    print()
    print("=" * 60)
    print("INSPECTING BRIGHTERMONDAY JOB")
    print("=" * 60)
    print()
    print(f"URL: {url}")

    response = navigate(page, url)

    if not response:
        return {
            **job,
            "company": "Not found",
            "location": "Not found",
            "job_type": "Not found",
            "qualification": "Not found",
            "experience_level": "Not found",
            "experience_length": "Not found",
            "experience": "Not found",
            "posted": "Not found",
            "deadline": "Not found",
            "description": "",
            "application_method": "brightermonday",
            "application_url": "Not found",
        }

    if response.status == 404:
        print("Job page does not exist (404).")

        return {
            **job,
            "company": "Not found",
            "location": "Not found",
            "job_type": "Not found",
            "qualification": "Not found",
            "experience_level": "Not found",
            "experience_length": "Not found",
            "experience": "Not found",
            "posted": "Not found",
            "deadline": "Not found",
            "description": "",
            "application_method": "brightermonday",
            "application_url": "Not found",
        }

    try:
        page.wait_for_timeout(1000)
    except Exception:
        pass

    print("Job page loaded.")
    print(f"Status: {response.status}")

    body_text = get_page_text(page)

    title = extract_job_title(page, body_text)

    # Keep the listing title if the page title extraction fails.
    if title == "Not found":
        title = job.get("title", "Not found")

    company = extract_company(page, body_text)

    location = extract_location(page, body_text)

    job_type = extract_job_type(page, body_text)

    qualification = extract_qualification(page, body_text)

    (
        experience_level,
        experience_length,
        experience,
    ) = extract_experience(page, body_text)

    posted = extract_posted_date(page, body_text)

    deadline = extract_deadline(page, body_text)

    description = extract_description(page, body_text)

    application_url = extract_application_url(page)

    application_method = extract_application_method(page)

    result = {
        "title": title,
        "company": company,
        "location": location,
        "job_type": job_type,
        "qualification": qualification,
        "experience_level": experience_level,
        "experience_length": experience_length,
        "experience": experience,
        "posted": posted,
        "deadline": deadline,
        "description": description,
        "url": url,
        "application_method": application_method,
        "application_url": application_url,
    }

    print()
    print("JOB INFORMATION")
    print("-" * 60)
    print(f"Title: {result['title']}")
    print(f"Company: {result['company']}")
    print(f"Location: {result['location']}")
    print(f"Job Type: {result['job_type']}")
    print(f"Qualification: {result['qualification']}")
    print(f"Experience Level: {result['experience_level']}")
    print(f"Experience Length: {result['experience_length']}")
    print(f"Experience: {result['experience']}")
    print(f"Posted: {result['posted']}")
    print(f"Deadline: {result['deadline']}")
    print(f"Description length: {len(result['description'])}")

    print()
    print("APPLICATION METHOD")
    print("-" * 60)
    print(f"Method: {result['application_method']}")
    print(f"URL: {result['application_url']}")

    return result


# ---------------------------------------------------------------------------
# Full collection
# ---------------------------------------------------------------------------

def collect_jobs(page):
    """
    Collect all technology jobs and inspect every listing.

    Returns:
        list[dict]
    """

    job_links = collect_job_links(page)

    print()
    print(f"Found {len(job_links)} technology job links.")

    for index, job in enumerate(job_links, start=1):
        print(f"{index}. {job['title']}")
        print(f"   {job['url']}")

    if not job_links:
        return []

    print()
    print("=" * 60)
    print("COLLECTING JOB DETAILS")
    print("=" * 60)

    jobs = []

    for index, job in enumerate(job_links, start=1):

        print()
        print(f"Processing job {index}/{len(job_links)}")
        print(f"Title: {job['title']}")

        try:
            details = get_job_details(page, job)

            jobs.append(details)

        except Exception as exc:
            print(f"Error collecting job: {exc}")

            jobs.append(
                {
                    **job,
                    "company": "Not found",
                    "location": "Not found",
                    "job_type": "Not found",
                    "qualification": "Not found",
                    "experience_level": "Not found",
                    "experience_length": "Not found",
                    "experience": "Not found",
                    "posted": "Not found",
                    "deadline": "Not found",
                    "description": "",
                    "application_method": "brightermonday",
                    "application_url": "Not found",
                }
            )

        # Small delay between listings.
        time.sleep(0.5)

    return jobs


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

def main():
    """Run the BrighterMonday browser collector."""

    with sync_playwright() as playwright:

        browser, page = launch_browser(playwright)

        try:
            print()
            print("Opening BrighterMonday...")

            response = navigate(page, BASE_URL)

            if not response:
                print("Could not open BrighterMonday.")
                return

            if response.status >= 400:
                print(f"BrighterMonday returned HTTP {response.status}.")
                return

            try:
                page.wait_for_timeout(1500)
            except Exception:
                pass

            print(f"Page title: {page.title()}")

            jobs = collect_jobs(page)

            print()
            print("=" * 60)
            print("BRIGHTERMONDAY BROWSER COLLECTION COMPLETE")
            print("=" * 60)
            print(f"Total jobs collected: {len(jobs)}")

            # Summary only.
            print()

            for index, job in enumerate(jobs, start=1):
                print(
                    f"{index}. {job['title']} | "
                    f"{job['company']} | "
                    f"{job['location']} | "
                    f"{job['experience']}"
                )

        finally:
            print()
            print("Closing browser...")

            try:
                browser.close()
            except Exception:
                pass

            print("Browser closed.")


if __name__ == "__main__":
    main()

