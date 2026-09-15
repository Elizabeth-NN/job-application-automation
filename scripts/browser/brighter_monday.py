"""
BrighterMonday browser automation layer.

Responsibilities
----------------
1. Open BrighterMonday.
2. Search the Software & Data category.
3. Paginate through job listings.
4. Collect unique job links.
5. Inspect individual jobs.
6. Extract job information and application details.

This module uses Playwright for browser-based collection.

It does NOT:
    - match jobs against the candidate profile
    - generate CVs
    - generate cover letters
    - submit applications
    - modify the job tracker
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.brightermonday.co.ke"

SOFTWARE_DATA_URL = (
    f"{BASE_URL}/jobs/software-data"
)

MAX_PAGES = 5

HEADLESS = False

PAGE_TIMEOUT = 60000


# ============================================================
# TECHNOLOGY FILTERS
# ============================================================

TECH_TITLE_PATTERNS = [
    # Software development
    r"\bsoftware\s+developer\b",
    r"\bsoftware\s+engineer\b",
    r"\bsoftware\s+development\b",

    # Web development
    r"\bweb\s+developer\b",
    r"\bwebsite\s+developer\b",
    r"\bwebmaster\b",

    # Backend
    r"\bbackend\s+developer\b",
    r"\bback[-\s]?end\s+developer\b",

    # Frontend
    r"\bfrontend\s+developer\b",
    r"\bfront[-\s]?end\s+developer\b",

    # Full stack
    r"\bfull[-\s]?stack\s+developer\b",
    r"\bfullstack\s+developer\b",

    # Programming languages
    r"\bpython\s+developer\b",
    r"\bjavascript\s+developer\b",
    r"\btypescript\s+developer\b",
    r"\bjava\s+developer\b",
    r"\bphp\s+developer\b",
    r"\bnode(?:\.js)?\s+developer\b",
    r"\breact\s+developer\b",
    r"\bgolang\s+developer\b",
    r"\bgo\s+developer\b",

    # Applications / systems
    r"\bapplication\s+developer\b",
    r"\bapplications\s+developer\b",
    r"\bsystems?\s+developer\b",
    r"\bprogrammer\b",

    # Data
    r"\bdata\s+analyst\b",
    r"\bdata\s+engineer\b",
    r"\bdata\s+scientist\b",
    r"\bdata\s+developer\b",

    # Database
    r"\bdatabase\s+developer\b",
    r"\bdatabase\s+administrator\b",

    # Cloud / DevOps
    r"\bdevops\b",
    r"\bdevops\s+engineer\b",
    r"\bcloud\s+engineer\b",
    r"\bcloud\s+developer\b",

    # QA
    r"\bqa\s+engineer\b",
    r"\bquality\s+assurance\s+engineer\b",
    r"\bsoftware\s+tester\b",
    r"\bsoftware\s+testing\b",
    r"\btest\s+engineer\b",
    r"\btest\s+analyst\b",

    # Automation
    r"\bautomation\s+engineer\b",
    r"\bautomation\s+developer\b",
    r"\brpa\s+developer\b",

    # Enterprise technology
    r"\bservicenow\s+developer\b",
    r"\bdynamics\s+365\b",
    r"\bpower\s+platform\b",
    r"\berp\s+developer\b",
    r"\bfineract\s+developer\b",

    # IT development
    r"\btechnical\s+developer\b",
    r"\bict\s+developer\b",
    r"\bit\s+developer\b",
    r"\bsoftware\s+officer\b",

    # Security
    r"\bsecurity\s+analyst\b",
    r"\bcyber\s+security\s+analyst\b",
    r"\bcybersecurity\s+analyst\b",
]


EXCLUDED_TITLE_PATTERNS = [
    # Sales
    r"\bsales\s+representative\b",
    r"\bsales\s+executive\b",
    r"\bsales\s+agent\b",
    r"\bsales\s+consultant\b",
    r"\bsales\s+manager\b",
    r"\bfield\s+sales\b",
    r"\bsales\s+and\s+marketing\b",

    # Business development
    r"\bbusiness\s+development\b",

    # Finance
    r"\baccountant\b",
    r"\baccounting\b",
    r"\bfinance\s+assistant\b",
    r"\bfinance\s+officer\b",
    r"\bfinancial\s+analyst\b",
    r"\bcredit\s+analyst\b",

    # HR / administration
    r"\bhuman\s+resources\b",
    r"\bhr\s+officer\b",
    r"\bhr\s+manager\b",
    r"\badministrator\b",
    r"\boffice\s+admin\b",
    r"\boffice\s+administrator\b",
    r"\breceptionist\b",

    # Marketing / content
    r"\bmarketing\b",
    r"\bdigital\s+marketer\b",
    r"\bgraphic\s+designer\b",
    r"\bcontent\s+lead\b",

    # Operations
    r"\boperations\s+manager\b",
    r"\boperations\s+officer\b",
    r"\boperations\s+executive\b",

    # Customer service
    r"\bcustomer\s+service\b",
    r"\brelationship\s+officer\b",
    r"\brelationship\s+manager\b",

    # Unrelated occupations
    r"\breal\s+estate\b",
    r"\bproperty\s+manager\b",
    r"\bwaiter\b",
    r"\bwaitress\b",
    r"\bdriver\b",
    r"\bchef\b",
    r"\bnurse\b",
    r"\bteacher\b",
    r"\bpharmaceutical\s+sales\b",
    r"\bprogram\s+officer\b",
    r"\bproject\s+assistant\b",
    r"\binstrumentation\s+engineer\b",
    r"\bcctv\b",
    r"\btechnical\s+operator\b",
    r"\bhousekeeper\b",
    r"\blogistics\b",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value: Optional[str]) -> str:
    """Normalize whitespace."""

    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url: str) -> str:
    """Convert a relative URL into an absolute BrighterMonday URL."""

    if not url:
        return ""

    return urljoin(BASE_URL, url)


def matches_pattern(
    text: str,
    patterns: List[str],
) -> bool:
    """Return True if text matches any supplied regex."""

    text = clean_text(text).lower()

    for pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def is_technology_job(title: str) -> bool:
    """
    Determine whether a job title belongs to the
    technology-oriented search.

    Explicit exclusions take priority.
    """

    title = clean_text(title)

    if not title:
        return False

    if matches_pattern(
        title,
        EXCLUDED_TITLE_PATTERNS,
    ):
        return False

    return matches_pattern(
        title,
        TECH_TITLE_PATTERNS,
    )


# ============================================================
# PAGE NAVIGATION
# ============================================================

def get_page(context):
    """Create a new Playwright page."""

    return context.new_page()


def navigate(
    page,
    url: str,
):
    """Navigate to a URL and return the response."""

    print("Navigation started.")

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=PAGE_TIMEOUT,
    )

    if response:
        print(
            f"Status: {response.status}"
        )

        if response.status == 404:
            print("Page does not exist (404).")

    return response


# ============================================================
# LISTING PAGE
# ============================================================

def build_listing_url(
    page_number: int,
) -> str:
    """Build a paginated Software & Data URL."""

    if page_number == 1:
        return SOFTWARE_DATA_URL

    return (
        f"{SOFTWARE_DATA_URL}"
        f"?page={page_number}"
    )


def collect_listing_links(
    page,
) -> List[Dict[str, str]]:
    """
    Extract job links from the current listing page.

    Returns:
        [
            {
                "title": "...",
                "url": "..."
            }
        ]
    """

    print()
    print("Collecting job links...")
    print()

    results = []

    seen = set()

    links = page.locator(
        'a[href*="/listings/"]'
    ).all()

    for link in links:

        try:

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            url = normalize_url(
                href
            )

            if "/listings/" not in url:
                continue

            title = clean_text(
                link.inner_text()
            )

            if not title:
                title = clean_text(
                    link.get_attribute(
                        "title"
                    )
                )

            if not title:
                continue

            if url in seen:
                continue

            seen.add(url)

            results.append(
                {
                    "title": title,
                    "url": url,
                }
            )

        except Exception:
            continue

    return results


# ============================================================
# PAGINATED COLLECTION
# ============================================================

def collect_job_links(
    context,
    max_pages: int = MAX_PAGES,
) -> List[Dict[str, str]]:
    """
    Collect unique technology-related jobs.

    Stops pagination when BrighterMonday returns 404.
    """

    print()
    print("=" * 60)
    print("BRIGHTERMONDAY SOFTWARE & DATA COLLECTION")
    print("=" * 60)

    all_jobs = []

    seen_urls = set()

    for page_number in range(
        1,
        max_pages + 1,
    ):

        listing_url = build_listing_url(
            page_number
        )

        print()
        print(
            f"Listing page "
            f"{page_number}/{max_pages}"
        )

        print(
            f"URL: {listing_url}"
        )

        page = get_page(
            context
        )

        try:

            response = navigate(
                page,
                listing_url,
            )

            if (
                response
                and response.status == 404
            ):
                print(
                    "Stopping pagination."
                )
                break

            page.wait_for_timeout(
                1500
            )

            jobs = collect_listing_links(
                page
            )

            print(
                f"Jobs found on page: "
                f"{len(jobs)}"
            )

            new_jobs = 0
            filtered_jobs = 0

            for job in jobs:

                url = job["url"]
                title = job["title"]

                if url in seen_urls:
                    continue

                seen_urls.add(url)

                if not is_technology_job(
                    title
                ):
                    filtered_jobs += 1
                    continue

                all_jobs.append(
                    job
                )

                new_jobs += 1

            print(
                f"New technology jobs added: "
                f"{new_jobs}"
            )

            print(
                f"Non-technology jobs filtered: "
                f"{filtered_jobs}"
            )

            print(
                f"Total technology jobs: "
                f"{len(all_jobs)}"
            )

        except Exception as error:

            print(
                f"⚠ Failed to process page "
                f"{page_number}: {error}"
            )

        finally:

            page.close()

    print()
    print("=" * 60)
    print("SOFTWARE & DATA COLLECTION COMPLETE")
    print("=" * 60)

    print(
        f"Total unique technology jobs: "
        f"{len(all_jobs)}"
    )

    return all_jobs


# ============================================================
# BODY / PAGE TEXT HELPERS
# ============================================================

def get_body_text(page) -> str:
    """Return normalized visible body text."""

    try:

        return clean_text(
            page.locator(
                "body"
            ).inner_text()
        )

    except Exception:

        return ""


def get_body_lines(page) -> List[str]:
    """Return cleaned non-empty body lines."""

    try:

        raw = page.locator(
            "body"
        ).inner_text()

    except Exception:

        return []

    lines = []

    for line in raw.splitlines():

        line = clean_text(line)

        if line:
            lines.append(line)

    return lines


def find_text_pattern(
    page,
    pattern: str,
    group: int = 1,
) -> str:
    """
    Search the complete visible page text with regex.
    """

    body = get_body_text(page)

    if not body:
        return ""

    match = re.search(
        pattern,
        body,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    try:
        return clean_text(
            match.group(group)
        )
    except IndexError:
        return ""


# ============================================================
# GENERIC LABEL EXTRACTION
# ============================================================

def find_labeled_value(
    page,
    labels: List[str],
) -> str:
    """
    Extract a value following a visible label.

    Supports:

        Location: Nairobi

    and:

        Location
        Nairobi
    """

    lines = get_body_lines(
        page
    )

    if not lines:
        return ""

    normalized_labels = {
        clean_text(label).lower()
        for label in labels
    }

    for index, line in enumerate(lines):

        normalized = line.lower()

        for label in normalized_labels:

            # ----------------------------------------------
            # Label: Value
            # ----------------------------------------------

            prefix = f"{label}:"

            if normalized.startswith(prefix):

                value = clean_text(
                    line[len(prefix):]
                )

                if value:
                    return value

            # ----------------------------------------------
            # Label
            # Value
            # ----------------------------------------------

            if normalized == label:

                if index + 1 < len(lines):

                    value = clean_text(
                        lines[index + 1]
                    )

                    if (
                        value
                        and value.lower()
                        not in normalized_labels
                    ):
                        return value

    return ""


# ============================================================
# TITLE
# ============================================================

def extract_title(
    page,
    fallback: str = "",
) -> str:
    """Extract the actual job title."""

    try:

        headings = page.locator(
            "h1"
        ).all()

        for heading in headings:

            text = clean_text(
                heading.inner_text()
            )

            if text:

                text = re.sub(
                    r"\s+at\s+.+$",
                    "",
                    text,
                    flags=re.IGNORECASE,
                )

                return clean_text(
                    text
                )

    except Exception:
        pass

    return clean_text(
        fallback
    )


# ============================================================
# COMPANY
# ============================================================

def extract_company(
    page,
) -> str:
    """
    Extract company name.

    Uses structured elements first and
    page title as a fallback.
    """

    selectors = [
        'a[href*="/companies/"]',
        '[class*="company"] a',
        '[class*="company-name"]',
        '[data-testid*="company"]',
    ]

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            ).all()

            for element in elements:

                text = clean_text(
                    element.inner_text()
                )

                if (
                    text
                    and 1 < len(text) < 150
                    and text.lower()
                    not in {
                        "company",
                        "employer",
                    }
                ):
                    return text

        except Exception:
            continue

    # Page title fallback.
    try:

        page_title = clean_text(
            page.title()
        )

        match = re.search(
            r"^(.+?)\s+at\s+(.+?)"
            r"(?:\s*\|\s*BrighterMonday)?$",
            page_title,
            flags=re.IGNORECASE,
        )

        if match:

            company = clean_text(
                match.group(2)
            )

            if company:
                return company

    except Exception:
        pass

    return find_labeled_value(
        page,
        [
            "Company",
            "Employer",
            "Organisation",
            "Organization",
        ],
    )


# ============================================================
# LOCATION
# ============================================================

def extract_location(
    page,
) -> str:
    """
    Extract location from the current BrighterMonday
    job header.

    Current BrighterMonday pages commonly expose:

        Nairobi Full Time Confidential

    or:

        Kenya Full Time IT & Telecoms Confidential

    rather than a separate Location label.
    """

    # ----------------------------------------------
    # Strategy 1: explicit label
    # ----------------------------------------------

    value = find_labeled_value(
        page,
        [
            "Location",
            "Job Location",
            "Where",
            "Applicant Location",
        ],
    )

    if value:
        return value

    # ----------------------------------------------
    # Strategy 2: structured text containing
    # known BrighterMonday location names.
    # ----------------------------------------------

    body = get_body_text(
        page
    )

    if not body:
        return ""

    location_patterns = [
        r"\bNairobi\b",
        r"\bMombasa\b",
        r"\bKisumu\b",
        r"\bNakuru\b",
        r"\bEldoret\b",
        r"\bThika\b",
        r"\bKiambu\b",
        r"\bMachakos\b",
        r"\bNyeri\b",
        r"\bMeru\b",
        r"\bKajiado\b",
        r"\bKenya\b",
        r"\bRest of Kenya\b",
        r"\bOutside Kenya\b",
        r"\bRemote\b",
        r"\bWork From Home\b",
    ]

    for pattern in location_patterns:

        match = re.search(
            pattern,
            body,
            flags=re.IGNORECASE,
        )

        if match:

            location = clean_text(
                match.group(0)
            )

            # Normalize common location values.
            if location.lower() == "work from home":
                return "Remote"

            return location

    return ""


# ============================================================
# JOB TYPE
# ============================================================

def extract_job_type(
    page,
) -> str:
    """
    Extract employment type.

    Current BrighterMonday pages expose values such as:

        Full Time
        Part Time
        Contract
        Internship, Volunteer
    """

    value = find_labeled_value(
        page,
        [
            "Job Type",
            "Employment Type",
            "Job type",
            "Work Type",
        ],
    )

    if value:
        return value

    body = get_body_text(
        page
    )

    if not body:
        return ""

    patterns = [
        r"\bFull Time\b",
        r"\bPart Time\b",
        r"\bContract\b",
        r"\bInternship(?:,\s*Volunteer)?\b",
        r"\bVolunteer\b",
        r"\bTemporary\b",
        r"\bFreelance\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(0)
            )

    return ""


# ============================================================
# QUALIFICATION
# ============================================================

def extract_qualification(
    page,
) -> str:
    """
    Extract minimum qualification.

    Current BrighterMonday pages expose:

        Min Qualification: Bachelors
    """

    value = find_labeled_value(
        page,
        [
            "Min Qualification",
            "Minimum Qualification",
            "Qualification",
            "Education",
        ],
    )

    if value:
        return value

    value = find_text_pattern(
        page,
        r"Min\s+Qualification\s*:\s*"
        r"(.+?)(?=\s+"
        r"(?:Language Requirement|"
        r"Working Hours|"
        r"Applicant Location|"
        r"Experience Level|"
        r"Experience Length)"
        r"|$)",
    )

    return value


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def extract_experience_level(
    page,
) -> str:
    """
    Extract BrighterMonday experience level.
    """

    value = find_labeled_value(
        page,
        [
            "Experience Level",
            "Career Level",
            "Experience level",
        ],
    )

    if value:
        return value

    value = find_text_pattern(
        page,
        r"Experience\s+Level\s*:\s*"
        r"(.+?)(?=\s+"
        r"(?:Experience Length|"
        r"Language Requirement|"
        r"Working Hours|"
        r"Applicant Location)"
        r"|$)",
    )

    if value:
        return value

    body = get_body_text(
        page
    )

    levels = [
        "Executive level",
        "Senior level",
        "Mid level",
        "Entry level",
        "Internship & Graduate",
        "No Experience",
    ]

    for level in levels:

        if re.search(
            rf"\b{re.escape(level)}\b",
            body,
            flags=re.IGNORECASE,
        ):
            return level

    return ""


# ============================================================
# EXPERIENCE LENGTH
# ============================================================

def extract_experience_length(
    page,
) -> str:
    """
    Extract required years/months of experience.
    """

    value = find_labeled_value(
        page,
        [
            "Experience Length",
            "Years of Experience",
            "Experience",
        ],
    )

    if value:
        return value

    value = find_text_pattern(
        page,
        r"Experience\s+Length\s*:\s*"
        r"(.+?)(?=\s+"
        r"(?:Language Requirement|"
        r"Working Hours|"
        r"Applicant Location)"
        r"|$)",
    )

    if value:
        return value

    body = get_body_text(
        page
    )

    # Avoid taking arbitrary years from the job description.
    patterns = [
        r"\b\d+\+?\s+years?\b",
        r"\b\d+\s+months?\b",
        r"\b1\s+month\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body,
            flags=re.IGNORECASE,
        )

        if match:

            value = clean_text(
                match.group(0)
            )

            if value:
                return value

    return ""


# ============================================================
# POSTED DATE
# ============================================================

def extract_posted(
    page,
) -> str:
    """
    Extract the relative published date shown by
    BrighterMonday, e.g. "5 days ago".
    """

    value = find_labeled_value(
        page,
        [
            "Posted",
            "Date Posted",
            "Published",
        ],
    )

    if value:
        return value

    body = get_body_text(
        page
    )

    patterns = [
        r"\b\d+\s+days?\s+ago\b",
        r"\b\d+\s+weeks?\s+ago\b",
        r"\b\d+\s+months?\s+ago\b",
        r"\byesterday\b",
        r"\btoday\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(0)
            )

    return ""


# ============================================================
# DEADLINE
# ============================================================

def extract_deadline(
    page,
) -> str:
    """
    Extract the application deadline.

    Tries:
        - visible Deadline label
        - Application Deadline label
        - Closing Date label
        - common date formats
        - page HTML as a final fallback
    """

    value = find_labeled_value(
        page,
        [
            "Deadline",
            "Application Deadline",
            "Closing Date",
            "Application closing date",
            "Expires",
        ],
    )

    if value:
        return value

    body = get_body_text(
        page
    )

    if not body:
        return ""

    # Explicit date labels.
    labeled_patterns = [
        r"(?:Deadline|Application Deadline|"
        r"Closing Date|Expires)\s*[:\-]?\s*"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})",

        r"(?:Deadline|Application Deadline|"
        r"Closing Date|Expires)\s*[:\-]?\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",

        r"(?:Deadline|Application Deadline|"
        r"Closing Date|Expires)\s*[:\-]?\s*"
        r"(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in labeled_patterns:

        match = re.search(
            pattern,
            body,
            flags=re.IGNORECASE,
        )

        if match:

            return clean_text(
                match.group(1)
            )

    # ----------------------------------------------
    # HTML fallback.
    #
    # Some BrighterMonday data is present in the
    # page source but not visible in body text.
    # ----------------------------------------------

    try:

        html = page.content()

    except Exception:

        html = ""

    if html:

        html_patterns = [
            r'"deadline"\s*:\s*"([^"]+)"',
            r'"closingDate"\s*:\s*"([^"]+)"',
            r'"applicationDeadline"\s*:\s*"([^"]+)"',
            r'"expiresAt"\s*:\s*"([^"]+)"',
        ]

        for pattern in html_patterns:

            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:

                value = clean_text(
                    match.group(1)
                )

                if value:
                    return value

    return ""


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(
    page,
) -> str:
    """
    Extract the job description.

    Several selectors are attempted because BrighterMonday
    uses different containers across listings.
    """

    selectors = [
        '[class*="description"]',
        '[class*="job-description"]',
        '[data-testid*="description"]',
        'article',
        'main',
    ]

    candidates = []

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            ).all()

            for element in elements:

                text = clean_text(
                    element.inner_text()
                )

                if len(text) > 300:
                    candidates.append(
                        text
                    )

        except Exception:
            continue

    if candidates:

        return max(
            candidates,
            key=len,
        )

    return get_body_text(
        page
    )


# ============================================================
# APPLICATION EXTRACTION
# ============================================================

def extract_application(
    page,
) -> Dict[str, str]:
    """
    Extract BrighterMonday application details.

    Returns:
        {
            "method": "brightermonday",
            "url": "...",
            "email": "",
            "subject": ""
        }
    """

    application = {
        "method": "brightermonday",
        "url": "",
        "email": "",
        "subject": "",
    }

    selectors = [
        'a[href*="/account/customer/sign-up"]',
        'a[href*="?apply="]',
        'a[href*="/job-application/"]',
        'a:has-text("Apply")',
        'a:has-text("Log In and Apply")',
        'a:has-text("Sign Up to Apply")',
    ]

    seen = set()

    for selector in selectors:

        try:

            links = page.locator(
                selector
            ).all()

            for link in links:

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                url = normalize_url(
                    href
                )

                if url in seen:
                    continue

                seen.add(url)

                if (
                    "sign-up?apply="
                    in url
                    or "?apply="
                    in url
                ):

                    application["url"] = url

                    return application

        except Exception:
            continue

    # Fallback: inspect all links.
    try:

        links = page.locator(
            "a"
        ).all()

        for link in links:

            href = link.get_attribute(
                "href"
            )

            text = clean_text(
                link.inner_text()
            ).lower()

            if not href:
                continue

            url = normalize_url(
                href
            )

            if (
                "apply" in text
                or "apply" in url.lower()
            ):

                application["url"] = url

                return application

    except Exception:
        pass

    return application


# ============================================================
# INSPECT ONE JOB
# ============================================================

def inspect_job(
    context,
    job_url: str,
    fallback_title: str = "",
) -> Dict:
    """
    Open and inspect one BrighterMonday job.

    Returns a normalized job dictionary.
    """

    print()
    print("=" * 60)
    print("INSPECTING BRIGHTERMONDAY JOB")
    print("=" * 60)

    print()
    print(
        f"URL: {job_url}"
    )

    page = get_page(
        context
    )

    try:

        response = navigate(
            page,
            job_url,
        )

        page.wait_for_timeout(
            1200
        )

        print(
            "Job page loaded."
        )

        if response:

            print(
                f"Status: "
                f"{response.status}"
            )

        # ----------------------------------------------------
        # Extract fields
        # ----------------------------------------------------

        title = extract_title(
            page,
            fallback_title,
        )

        company = extract_company(
            page
        )

        location = extract_location(
            page
        )

        job_type = extract_job_type(
            page
        )

        qualification = extract_qualification(
            page
        )

        experience_level = extract_experience_level(
            page
        )

        experience_length = extract_experience_length(
            page
        )

        posted = extract_posted(
            page
        )

        deadline = extract_deadline(
            page
        )

        description = extract_description(
            page
        )

        application = extract_application(
            page
        )

        # ----------------------------------------------------
        # Build combined experience
        # ----------------------------------------------------

        experience = ""

        if (
            experience_level
            and experience_length
        ):

            experience = (
                f"{experience_level} "
                f"({experience_length})"
            )

        elif experience_level:

            experience = experience_level

        elif experience_length:

            experience = experience_length

        # ----------------------------------------------------
        # Normalized job
        # ----------------------------------------------------

        job = {
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
            "url": job_url,
            "application": application,
            "application_method": application.get(
                "method",
                "",
            ),
            "application_url": application.get(
                "url",
                "",
            ),
            "application_email": application.get(
                "email",
                "",
            ),
        }

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

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
            f"Company: "
            f"{company or 'Not found'}"
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
            f"Deadline: "
            f"{deadline or 'Not found'}"
        )

        print(
            f"Description length: "
            f"{len(description)}"
        )

        print()
        print(
            "APPLICATION METHOD"
        )
        print("-" * 60)

        print(
            f"Method: "
            f"{application.get('method', '')}"
        )

        if application.get("url"):

            print(
                f"URL: "
                f"{application['url']}"
            )

        if application.get("email"):

            print(
                f"Email: "
                f"{application['email']}"
            )

        return job

    finally:

        page.close()


# ============================================================
# TEST
# ============================================================

def main():
    """
    Test the BrighterMonday browser layer.
    """

    playwright = None
    browser = None

    try:

        # ----------------------------------------------------
        # Start browser
        # ----------------------------------------------------

        playwright, browser, context = launch_browser(
            headless=HEADLESS
        )

        # ----------------------------------------------------
        # Open BrighterMonday
        # ----------------------------------------------------

        print()
        print(
            "Opening BrighterMonday..."
        )

        page = get_page(
            context
        )

        response = navigate(
            page,
            BASE_URL,
        )

        if response:

            print(
                f"Status: {response.status}"
            )

        print(
            f"Page title: {page.title()}"
        )

        page.close()

        # ----------------------------------------------------
        # Collect jobs
        # ----------------------------------------------------

        jobs = collect_job_links(
            context,
            max_pages=MAX_PAGES,
        )

        print()
        print(
            f"Found {len(jobs)} "
            f"technology job links."
        )

        # ----------------------------------------------------
        # Show first 10
        # ----------------------------------------------------

        print()

        for index, job in enumerate(
            jobs[:10],
            start=1,
        ):

            print(
                f"{index}. "
                f"{job['title']}"
            )

            print(
                f"   {job['url']}"
            )

        # ----------------------------------------------------
        # Inspect first job
        # ----------------------------------------------------

        if jobs:

            print()
            print(
                "=" * 60
            )
            print(
                "TESTING FIRST TECHNOLOGY JOB"
            )
            print(
                "=" * 60
            )

            inspect_job(
                context,
                jobs[0]["url"],
                jobs[0]["title"],
            )

        else:

            print()
            print(
                "No technology jobs found."
            )

    except Exception as error:

        print()
        print(
            "ERROR"
        )
        print("-" * 60)
        print(error)

    finally:

        if browser and playwright:

            print()
            print(
                "Closing browser..."
            )

            close_browser(
                playwright,
                browser,
            )


if __name__ == "__main__":
    main()