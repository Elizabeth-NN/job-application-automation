from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin
import re
import time


BASE_URL = "https://www.brightermonday.co.ke"
LISTING_URL = f"{BASE_URL}/jobs/software-data"

MAX_PAGES = 5

TECHNOLOGY_KEYWORDS = [
    "software",
    "developer",
    "development",
    "programmer",
    "programming",
    "python",
    "flask",
    "django",
    "react",
    "javascript",
    "typescript",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "full stack",
    "full-stack",
    "web developer",
    "web development",
    "data analyst",
    "data scientist",
    "data science",
    "data engineer",
    "machine learning",
    "artificial intelligence",
    "ai",
    "database",
    "devops",
    "cloud",
    "systems",
    "information technology",
    "it assistant",
    "software engineer",
    "software engineering",
    "qa",
    "quality assurance",
    "cybersecurity",
    "cyber security",
    "technical",
    "technology",
]


def clean_text(text):
    """Clean whitespace from extracted text."""

    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_technology_job(title, url="", text=""):
    """
    Determine whether a listing is relevant to technology/software/data.

    Title is weighted most heavily because BrighterMonday's category can
    contain unrelated jobs.
    """

    combined = f"{title} {url} {text}".lower()

    title_lower = title.lower()

    # Strong title signals.
    strong_title_keywords = [
        "developer",
        "software",
        "programmer",
        "programming",
        "data analyst",
        "data scientist",
        "data engineer",
        "machine learning",
        "artificial intelligence",
        "ai engineer",
        "devops",
        "database",
        "frontend",
        "front-end",
        "backend",
        "back-end",
        "full stack",
        "full-stack",
        "cybersecurity",
        "cyber security",
        "systems",
        "it assistant",
        "information technology",
    ]

    if any(keyword in title_lower for keyword in strong_title_keywords):
        return True

    # Weaker signals require more than one occurrence.
    matches = sum(
        1 for keyword in TECHNOLOGY_KEYWORDS
        if keyword in combined
    )

    return matches >= 2


def extract_job_links(page):
    """Extract technology job links from a BrighterMonday listing page."""

    jobs = []
    seen_urls = set()

    links = page.locator("a").all()

    for link in links:
        try:
            href = link.get_attribute("href")
            title = clean_text(link.inner_text())
        except Exception:
            continue

        if not href:
            continue

        if "/listings/" not in href:
            continue

        url = urljoin(BASE_URL, href)

        # Remove query strings/fragments.
        url = url.split("?")[0].split("#")[0]

        if url in seen_urls:
            continue

        if not title:
            continue

        if not is_technology_job(title, url):
            continue

        seen_urls.add(url)

        jobs.append(
            {
                "title": title,
                "url": url,
            }
        )

    return jobs


def collect_job_links(page):
    """
    Collect technology job links across BrighterMonday pagination.
    """

    all_jobs = []
    seen_urls = set()

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

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            status = response.status if response else None

            print("Navigation started.")
            print(f"Status: {status}")

            if status == 404:
                print("Page does not exist (404).")
                print("Stopping pagination.")
                break

            if status and status >= 400:
                print(f"HTTP error {status}.")
                continue

            page.wait_for_timeout(1500)

        except PlaywrightTimeoutError:
            print("Navigation timed out.")
            continue

        except Exception as exc:
            print(f"Navigation error: {exc}")
            continue

        print()
        print("Collecting job links...")

        jobs = extract_job_links(page)

        new_jobs = 0
        filtered_jobs = 0

        # Count all listing links for useful diagnostics.
        listing_links = page.locator('a[href*="/listings/"]').count()

        for job in jobs:
            if job["url"] in seen_urls:
                continue

            seen_urls.add(job["url"])
            all_jobs.append(job)
            new_jobs += 1

        filtered_jobs = max(listing_links - len(jobs), 0)

        print()
        print(f"Jobs found on page: {listing_links}")
        print(f"New technology jobs added: {new_jobs}")
        print(f"Non-technology jobs filtered: {filtered_jobs}")
        print(f"Total technology jobs: {len(all_jobs)}")

    print()
    print("=" * 60)
    print("SOFTWARE & DATA COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Total unique technology jobs: {len(all_jobs)}")

    return all_jobs


def find_value_after_label(text, labels):
    """
    Extract a value appearing after one of several labels.

    This is intentionally conservative because BrighterMonday's page
    structure changes periodically.
    """

    if not text:
        return None

    for label in labels:
        pattern = rf"{re.escape(label)}\s*:?\s*([^\n|]+)"
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = clean_text(match.group(1))

            if value:
                return value

    return None


def extract_metadata(page):
    """
    Extract structured metadata from an individual BrighterMonday job page.
    """

    result = {
        "location": None,
        "job_type": None,
        "qualification": None,
        "experience_level": None,
        "experience_length": None,
        "experience": None,
        "posted": None,
        "deadline": None,
    }

    # ---------------------------------------------------------
    # Structured metadata
    # ---------------------------------------------------------

    # BrighterMonday commonly renders metadata as cards/rows.
    # Try several selector patterns without depending on one CSS class.
    selectors = [
        "[class*='job-details']",
        "[class*='job-detail']",
        "[class*='details']",
        "[class*='summary']",
        "main",
    ]

    page_text = ""

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count():
                text = locator.inner_text(timeout=3000)

                if len(text) > len(page_text):
                    page_text = text

        except Exception:
            continue

    page_text = clean_text(page_text)

    # ---------------------------------------------------------
    # Location
    # ---------------------------------------------------------

    location_patterns = [
        r"\bLocation\s*:?\s*(Nairobi|Mombasa|Kisumu|Nakuru|Eldoret|Kenya|Remote|Hybrid|[A-Z][A-Za-z\s]+)",
        r"\bApplicant Location\s*:?\s*(Nairobi|Mombasa|Kisumu|Nakuru|Eldoret|Kenya|Remote|Hybrid)",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)

        if match:
            result["location"] = clean_text(match.group(1))
            break

    # ---------------------------------------------------------
    # Job type
    # ---------------------------------------------------------

    job_type_patterns = [
        r"\bJob Type\s*:?\s*(Full Time(?:\s*-\s*[^|]+)?|Part Time|Contract|Temporary|Internship|Volunteer)",
        r"\bWorking Hours\s*:?\s*(Full Time(?:\s*-\s*[^|]+)?|Part Time)",
    ]

    for pattern in job_type_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)

        if match:
            result["job_type"] = clean_text(match.group(1))
            break

    # ---------------------------------------------------------
    # Qualification
    # ---------------------------------------------------------

    qualification_patterns = [
        r"\bQualification\s*:?\s*(Certificate|Diploma|Bachelors?|Bachelor's|Masters?|Master's|PhD|Degree)",
        r"\bQualification\s*:?\s*([A-Za-z][A-Za-z\s&/-]{2,60}?)(?=\s+(?:Language|Working|Applicant|Experience|Posted|Deadline)\b)",
    ]

    for pattern in qualification_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)

        if match:
            result["qualification"] = clean_text(match.group(1))
            break

    # ---------------------------------------------------------
    # Experience
    # ---------------------------------------------------------

    experience_patterns = [
        r"\bExperience Length\s*:?\s*([^\n|]+)",
        r"\bExperience\s*:?\s*(\d+\+?\s*(?:months?|years?))",
        r"\bExperience\s*:?\s*(?:At least\s+)?(\d+\+?\s*(?:months?|years?))",
    ]

    for pattern in experience_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)

        if match:
            value = clean_text(match.group(1))

            # Reject obvious description fragments.
            if len(value) < 50:
                result["experience_length"] = value
                result["experience"] = value
                break

    # ---------------------------------------------------------
    # Experience level
    # ---------------------------------------------------------

    experience_level_patterns = [
        r"\bExperience Level\s*:?\s*(Entry level|Junior|Mid level|Senior|Executive|No experience)",
        r"\bLevel\s*:?\s*(Entry level|Junior|Mid level|Senior|Executive)",
    ]

    for pattern in experience_level_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)

        if match:
            result["experience_level"] = clean_text(match.group(1))
            break

    # ---------------------------------------------------------
    # Posted / deadline
    # ---------------------------------------------------------

    date_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?"

    dates = re.findall(date_pattern, page_text)

    if dates:
        result["posted"] = dates[0]

        if len(dates) > 1:
            result["deadline"] = dates[1]

    # Human-readable posted date.
    if not result["posted"]:
        posted_match = re.search(
            r"\bPosted\s*:?\s*(\d+\s+(?:day|days|week|weeks|month|months)\s+ago)",
            page_text,
            re.IGNORECASE,
        )

        if posted_match:
            result["posted"] = clean_text(posted_match.group(1))

    # Deadline fallback.
    if not result["deadline"]:
        deadline_match = re.search(
            r"\bDeadline\s*:?\s*([A-Za-z0-9,\-/ ]+)",
            page_text,
            re.IGNORECASE,
        )

        if deadline_match:
            result["deadline"] = clean_text(deadline_match.group(1))

    return result


def extract_description(page):
    """
    Extract the job description and requirements while removing
    obvious navigation/footer noise.
    """

    candidates = [
        "main",
        "article",
        "[class*='description']",
        "[class*='job-description']",
        "[class*='jobDescription']",
    ]

    best_text = ""

    for selector in candidates:
        try:
            locator = page.locator(selector).first

            if not locator.count():
                continue

            text = clean_text(locator.inner_text(timeout=5000))

            if len(text) > len(best_text):
                best_text = text

        except Exception:
            continue

    if not best_text:
        try:
            best_text = clean_text(page.locator("body").inner_text())
        except Exception:
            best_text = ""

    # Remove obvious website noise.
    noise_markers = [
        "Important safety tips",
        "Activate Notifications",
        "Stay Updated",
        "About Companies Hiring",
        "Privacy Policy",
        "© 2026 BrighterMonday",
        "Accept All Cookies",
    ]

    for marker in noise_markers:
        index = best_text.find(marker)

        if index != -1:
            best_text = best_text[:index]

    return clean_text(best_text)


def extract_application_method(page):
    """
    Determine how the job is applied for.

    For BrighterMonday-hosted applications, retain the apply URL.
    """

    apply_url = None

    selectors = [
        "a[href*='apply=']",
        "a[href*='/account/customer/']",
        "a:has-text('Apply')",
        "button:has-text('Apply')",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count():
                href = locator.get_attribute("href")

                if href:
                    apply_url = urljoin(BASE_URL, href)
                    break

        except Exception:
            continue

    return {
        "application_method": "brightermonday",
        "application_url": apply_url,
    }


def inspect_brightermonday_job(context, url, title):
    """
    Inspect one BrighterMonday job using the shared browser context.

    Parameters
    ----------
    context : BrowserContext
        Shared Playwright browser context.

    url : str
        BrighterMonday job URL.

    title : str
        Job title collected from the listing page.

    Returns
    -------
    dict
        Normalized inspected job.
    """

    print()
    print("=" * 60)
    print("INSPECTING BRIGHTERMONDAY JOB")
    print("=" * 60)
    print()
    print(f"URL: {url}")

    page = context.new_page()

    try:

        # ========================================================
        # NAVIGATION
        # ========================================================

        try:

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            status = response.status if response else None

            print("Job navigation started.")
            print(f"Status: {status}")

            if status and status >= 400:

                print(
                    f"Unable to load job page: HTTP {status}"
                )

                return None

            page.wait_for_timeout(1500)

        except PlaywrightTimeoutError:

            print(
                "Job page navigation timed out."
            )

            return None

        except Exception as exc:

            print(
                f"Job page error: {exc}"
            )

            return None

        print("Job page loaded.")
        print(f"Status: {status}")

        # ========================================================
        # PAGE TITLE
        # ========================================================

        actual_title = clean_text(title)

        try:

            page_title = clean_text(
                page.title()
            )

            if (
                page_title
                and "brightermonday" not in page_title.lower()
                and len(page_title) < 200
            ):

                actual_title = page_title

        except Exception:
            pass

        # ========================================================
        # BODY TEXT
        # ========================================================

        try:

            body_text = clean_text(
                page.locator("body").inner_text(
                    timeout=10000
                )
            )

        except Exception:

            body_text = ""

        # ========================================================
        # COMPANY
        # ========================================================

        company = None

        company_patterns = [

            r"\bCompany\s*:?\s*([A-Za-z0-9&.,'()\- ]+)",

            r"\bEmployer\s*:?\s*([A-Za-z0-9&.,'()\- ]+)",

        ]

        for pattern in company_patterns:

            match = re.search(
                pattern,
                body_text,
                re.IGNORECASE,
            )

            if match:

                value = clean_text(
                    match.group(1)
                )

                if value and len(value) < 150:

                    company = value

                    break

        # ========================================================
        # METADATA
        # ========================================================

        metadata = extract_metadata(page)

        # ========================================================
        # DESCRIPTION
        # ========================================================

        description = extract_description(
            page
        )

        # ========================================================
        # APPLICATION
        # ========================================================

        application = extract_application_method(
            page
        )

        # ========================================================
        # NORMALIZED RESULT
        # ========================================================

        result = {

            "title": actual_title,

            "company": company,

            "location": metadata.get(
                "location"
            ),

            "job_type": metadata.get(
                "job_type"
            ),

            "qualification": metadata.get(
                "qualification"
            ),

            "experience_level": metadata.get(
                "experience_level"
            ),

            "experience_length": metadata.get(
                "experience_length"
            ),

            "experience": metadata.get(
                "experience"
            ),

            "posted": metadata.get(
                "posted"
            ),

            "deadline": metadata.get(
                "deadline"
            ),

            "description": description,

            "url": url,

            "application_method": application.get(
                "application_method"
            ),

            "application_url": application.get(
                "application_url"
            ),

            "source": "brightermonday",

        }

        # ========================================================
        # DISPLAY
        # ========================================================

        print()
        print("INSPECTED JOB")
        print("-" * 60)

        print(
            f"Title: {result['title']}"
        )

        print(
            f"Company: {result['company'] or ''}"
        )

        print(
            f"Location: {result['location'] or 'Not found'}"
        )

        print(
            f"Job Type: {result['job_type'] or 'Not found'}"
        )

        print(
            f"Qualification: "
            f"{result['qualification'] or 'Not found'}"
        )

        print(
            f"Experience: "
            f"{result['experience'] or 'Not found'}"
        )

        print(
            f"Posted: "
            f"{result['posted'] or 'Not found'}"
        )

        print(
            f"Deadline: "
            f"{result['deadline'] or 'Not found'}"
        )

        print(
            f"Description length: "
            f"{len(result['description'] or '')}"
        )

        return result

    finally:

        try:
            page.close()
        except Exception:
            pass

def collect_jobs():
    """
    Main BrighterMonday browser collector.

    Returns a list of fully populated technology jobs.
    """

    jobs = []

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        print("Chromium launched successfully.")
        print()

        page = browser.new_page()

        try:
            print("Opening BrighterMonday...")

            response = page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print("Navigation started.")

            if response:
                print(f"Status: {response.status}")

            page.wait_for_timeout(1000)

            print(f"Page title: {page.title()}")

            job_links = collect_job_links(page)

            print()
            print(f"Found {len(job_links)} technology job links.")

            for index, job in enumerate(job_links, start=1):
                print(f"{index}. {job['title']}")
                print(f"   {job['url']}")

            print()
            print("=" * 60)
            print("COLLECTING FULL JOB DETAILS")
            print("=" * 60)

            for index, job in enumerate(job_links, start=1):

                print()
                print(f"Processing job {index}/{len(job_links)}")

                details = get_job_details(page, job)

                if details:
                    jobs.append(details)

                time.sleep(0.5)

        finally:
            print()
            print("Closing browser...")
            browser.close()
            print("Browser closed.")

    print()
    print("=" * 60)
    print("BRIGHTERMONDAY BROWSER COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Jobs successfully collected: {len(jobs)}")

    return jobs


if __name__ == "__main__":
    jobs = collect_jobs()

    print()
    print("Collected jobs:")
    print("-" * 60)

    for index, job in enumerate(jobs, start=1):
        print(
            f"{index}. "
            f"{job.get('title')} | "
            f"{job.get('company')} | "
            f"{job.get('location')}"
        )