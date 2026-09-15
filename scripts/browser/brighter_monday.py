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

import json
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from scripts.browser.browser import launch_browser, close_browser


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

DETAIL_WAIT = 1200

LISTING_WAIT = 1500


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
    r"\bruby\s+developer\b",

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
    r"\bapplications?\s+&\s+software\b",

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
    r"\bsales\s+engineer\b",
    r"\bfield\s+sales\b",
    r"\btechnical\s+sales\b",
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

    # IT support / management
    r"\bict\s+manager\b",
    r"\bit\s+manager\b",
    r"\binformation\s+systems\s+security\s+manager\b",
    r"\bit\s+maintenance\b",
    r"\bmaintenance\s+assistant\b",
    r"\btechnical\s+support\b",
    r"\bit\s+support\b",
    r"\bhelp\s+desk\b",
    r"\bsupport\s+officer\b",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value: Optional[str]) -> str:
    """Normalize whitespace."""
    if not value:
        return ""

    value = re.sub(r"\s+", " ", str(value))

    return value.strip()


def normalize_url(url: str) -> str:
    """Convert relative URL to absolute URL."""
    if not url:
        return ""

    return urljoin(BASE_URL, url.strip())


def matches_pattern(
    text: str,
    patterns: List[str],
) -> bool:
    """Return True when text matches any pattern."""
    text = clean_text(text)

    if not text:
        return False

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
    Determine whether a title belongs to the technology category.

    Exclusions always take priority over inclusions.
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
# PAGE HELPERS
# ============================================================

def get_page(context):
    """Create a new Playwright page."""
    return context.new_page()


def navigate(page, url: str):
    """Navigate to URL and return Playwright response."""
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
            print(
                "Page does not exist (404)."
            )

    return response


def get_body_text(page) -> str:
    """Return complete visible body text."""
    try:
        return clean_text(
            page.locator("body").inner_text()
        )
    except Exception:
        return ""


def get_body_lines(page) -> List[str]:
    """Return cleaned non-empty body lines."""
    try:
        text = page.locator("body").inner_text()
    except Exception:
        return []

    lines = []

    for line in text.splitlines():
        line = clean_text(line)

        if line:
            lines.append(line)

    return lines


# ============================================================
# LISTING PAGE
# ============================================================

def build_listing_url(
    page_number: int,
) -> str:
    """Build paginated Software & Data URL."""
    if page_number <= 1:
        return SOFTWARE_DATA_URL

    return (
        f"{SOFTWARE_DATA_URL}"
        f"?page={page_number}"
    )


def collect_listing_links(page) -> List[Dict[str, str]]:
    """
    Extract job links from the current page.

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

    try:
        links = page.locator(
            'a[href*="/listings/"]'
        ).all()
    except Exception:
        return results

    for link in links:
        try:
            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            url = normalize_url(href)

            if "/listings/" not in url:
                continue

            title = clean_text(
                link.inner_text()
            )

            if not title:
                title = clean_text(
                    link.get_attribute("title")
                )

            if not title:
                continue

            if title.lower() in {
                "view job",
                "apply now",
                "read more",
                "see more",
            }:
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
# PAGINATION
# ============================================================

def collect_job_links(
    context,
    max_pages: int = MAX_PAGES,
) -> List[Dict[str, str]]:
    """
    Collect unique technology-related jobs.
    """
    print()
    print("=" * 60)
    print(
        "BRIGHTERMONDAY SOFTWARE & DATA COLLECTION"
    )
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

        page = get_page(context)

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
                LISTING_WAIT
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

                all_jobs.append(job)

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
                f"Failed to process page "
                f"{page_number}: {error}"
            )

        finally:
            try:
                page.close()
            except Exception:
                pass

    print()
    print("=" * 60)
    print(
        "SOFTWARE & DATA COLLECTION COMPLETE"
    )
    print("=" * 60)

    print(
        f"Total unique technology jobs: "
        f"{len(all_jobs)}"
    )

    return all_jobs


# ============================================================
# JSON-LD
# ============================================================

def get_json_ld_objects(page) -> List[dict]:
    """
    Extract JSON-LD objects from the page.

    BrighterMonday may expose job information
    through structured JobPosting data. This is
    generally more reliable than scraping visible
    page text.
    """
    objects = []

    try:
        scripts = page.locator(
            "script[type='application/ld+json']"
        ).all()
    except Exception:
        return objects

    for script in scripts:
        try:
            raw = script.inner_text()

            if not raw:
                continue

            raw = raw.strip()

            if not raw:
                continue

            data = json.loads(raw)

        except Exception:
            continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    objects.append(item)

        elif isinstance(data, dict):
            objects.append(data)

            graph = data.get(
                "@graph"
            )

            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        objects.append(item)

    return objects


def get_job_posting_json_ld(
    page,
) -> List[dict]:
    """Return JobPosting JSON-LD objects."""
    postings = []

    for data in get_json_ld_objects(page):
        schema_type = data.get(
            "@type"
        )

        if isinstance(
            schema_type,
            list,
        ):
            if "JobPosting" in schema_type:
                postings.append(data)

        elif schema_type == "JobPosting":
            postings.append(data)

    return postings


# ============================================================
# GENERIC FIELD VALIDATION
# ============================================================

def is_placeholder(value: str) -> bool:
    """Return True for obvious placeholder/UI values."""
    if not value:
        return True

    value = clean_text(value).lower()

    placeholders = {
        "",
        "not found",
        "unknown",
        "unknown company",
        "job summary",
        "job details",
        "job description",
        "job overview",
        "overview",
        "details",
        "location",
        "job location",
        "where",
        "company",
        "employer",
        "employers",
        "qualification",
        "education",
        "experience",
        "experience level",
        "experience length",
        "posted",
        "date posted",
        "deadline",
        "application deadline",
        "apply now",
        "sign in",
        "login",
        "log in",
        "sign up to apply",
        "software & data",
        "software and data",
    }

    return value in placeholders


def valid_short_value(
    value: str,
    max_words: int = 15,
) -> bool:
    """
    Validate a short field.

    This prevents values such as:
        "Job summary Department: Data..."
    from being returned as a field.
    """
    value = clean_text(value)

    if not value:
        return False

    if is_placeholder(value):
        return False

    if len(value) > 200:
        return False

    if len(value.split()) > max_words:
        return False

    return True


# ============================================================
# TITLE
# ============================================================

def extract_title(
    page,
    fallback: str = "",
) -> str:
    """Extract actual job title."""
    try:
        headings = page.locator(
            "h1"
        ).all()

        for heading in headings:
            text = clean_text(
                heading.inner_text()
            )

            if not text:
                continue

            text = re.sub(
                r"\s+at\s+.+$",
                "",
                text,
                flags=re.IGNORECASE,
            )

            if valid_short_value(
                text,
                max_words=25,
            ):
                return text

    except Exception:
        pass

    # JSON-LD fallback
    for data in get_job_posting_json_ld(page):
        value = data.get(
            "title",
            "",
        )

        if isinstance(value, str):
            value = clean_text(value)

            if value:
                return value

    return clean_text(fallback)


# ============================================================
# COMPANY
# ============================================================

def extract_company(page) -> str:
    """
    Extract employer/company.

    Priority:
        1. JSON-LD hiringOrganization
        2. Company links
        3. Explicit company selectors
        4. Page title
        5. Label/value
    """

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    for data in get_job_posting_json_ld(page):
        organization = data.get(
            "hiringOrganization"
        )

        if isinstance(
            organization,
            dict,
        ):
            name = clean_text(
                organization.get(
                    "name",
                    "",
                )
            )

            if valid_company(name):
                return name

        elif isinstance(
            organization,
            str,
        ):
            name = clean_text(
                organization
            )

            if valid_company(name):
                return name

    # --------------------------------------------------------
    # 2. Company links
    # --------------------------------------------------------

    selectors = [
        'a[href*="/companies/"]',
        'a[href*="/company/"]',
        'a[href*="/employers/"]',
        'a[href*="/employer/"]',
    ]

    for selector in selectors:
        try:
            elements = page.locator(
                selector
            ).all()

            for element in elements:
                value = clean_text(
                    element.inner_text()
                )

                if valid_company(value):
                    return value

        except Exception:
            continue

    # --------------------------------------------------------
    # 3. Explicit selectors
    # --------------------------------------------------------

    selectors = [
        "[data-testid*='company']",
        "[data-testid*='employer']",
        "[data-test*='company']",
        "[data-test*='employer']",
        "[class*='company-name']",
        "[class*='company_name']",
        "[class*='companyName']",
        "[class*='employer-name']",
        "[class*='employer_name']",
        "[class*='employerName']",
    ]

    for selector in selectors:
        try:
            elements = page.locator(
                selector
            ).all()

            for element in elements:
                value = clean_text(
                    element.inner_text()
                )

                if valid_company(value):
                    return value

        except Exception:
            continue

    # --------------------------------------------------------
    # 4. Page title
    # --------------------------------------------------------

    try:
        page_title = clean_text(
            page.title()
        )

        match = re.search(
            r"^(.*?)\s+at\s+(.+?)(?:\s*\|\s*BrighterMonday)?$",
            page_title,
            flags=re.IGNORECASE,
        )

        if match:
            company = clean_text(
                match.group(2)
            )

            if valid_company(company):
                return company

    except Exception:
        pass

    # --------------------------------------------------------
    # 5. Label/value
    # --------------------------------------------------------

    value = find_structured_label_value(
        page,
        [
            "Company",
            "Employer",
            "Organisation",
            "Organization",
        ],
    )

    if valid_company(value):
        return value

    return "Unknown Company"


def valid_company(
    value: str,
) -> bool:
    """Validate employer name."""
    value = clean_text(value)

    if not value:
        return False

    lower = value.lower()

    invalid = {
        "company",
        "companies",
        "employer",
        "employers",
        "unknown",
        "unknown company",
        "unknown employer",
        "brightermonday",
        "brighter monday",
        "job summary",
        "job details",
        "job description",
        "job overview",
        "overview",
        "details",
        "software & data",
        "software and data",
        "apply now",
        "login",
        "log in",
        "sign in",
        "nairobi",
        "mombasa",
        "kisumu",
        "nakuru",
        "eldoret",
        "thika",
        "kenya",
    }

    if lower in invalid:
        return False

    if "email address" in lower:
        return False

    if "protection of your data" in lower:
        return False

    if "apply now" in lower:
        return False

    if "sign up" in lower:
        return False

    if "log in" in lower:
        return False

    if "http://" in lower:
        return False

    if "https://" in lower:
        return False

    if "@" in value:
        return False

    if len(value) > 150:
        return False

    if len(value.split()) > 12:
        return False

    return True


# ============================================================
# STRUCTURED LABEL EXTRACTION
# ============================================================

def find_structured_label_value(
    page,
    labels: List[str],
) -> str:
    """
    Extract a label/value pair without treating the
    entire flattened body as a valid field.

    Handles:

        Location
        Nairobi

    and:

        Location: Nairobi

    and:

        Location - Nairobi
    """

    normalized_labels = {
        clean_text(label).lower()
        for label in labels
    }

    # --------------------------------------------------------
    # 1. DOM elements containing exact label
    # --------------------------------------------------------

    for label in normalized_labels:

        # Exact text node
        selector = (
            f"text={label}"
        )

        try:
            locator = page.get_by_text(
                label,
                exact=True,
            )

            count = locator.count()

            for index in range(count):
                element = locator.nth(index)

                # Parent's next sibling
                try:
                    sibling = element.locator(
                        ".."
                    ).locator(
                        "xpath=following-sibling::*[1]"
                    )

                    if sibling.count() > 0:
                        value = clean_text(
                            sibling.first.inner_text()
                        )

                        if valid_short_value(
                            value
                        ):
                            return value
                except Exception:
                    pass

                # Parent contents
                try:
                    parent = element.locator(
                        ".."
                    )

                    text = clean_text(
                        parent.inner_text()
                    )

                    value = extract_value_from_inline_label(
                        text,
                        label,
                    )

                    if valid_short_value(
                        value
                    ):
                        return value

                except Exception:
                    pass

        except Exception:
            pass

    # --------------------------------------------------------
    # 2. Body lines
    # --------------------------------------------------------

    lines = get_body_lines(page)

    for index, line in enumerate(lines):
        lower_line = line.lower()

        for label in normalized_labels:

            # Label: Value
            match = re.match(
                rf"^{re.escape(label)}\s*:\s*(.+)$",
                lower_line,
                flags=re.IGNORECASE,
            )

            if match:
                value = clean_text(
                    line[
                        len(line)
                        - len(match.group(1))
                    :]
                )

                if valid_short_value(value):
                    return value

            # Label - Value
            match = re.match(
                rf"^{re.escape(label)}\s*[-–—]\s*(.+)$",
                lower_line,
                flags=re.IGNORECASE,
            )

            if match:
                value = re.sub(
                    rf"^{re.escape(label)}\s*[-–—]\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                )

                value = clean_text(value)

                if valid_short_value(value):
                    return value

            # Label on one line, value on next
            if lower_line == label:
                if index + 1 < len(lines):
                    value = clean_text(
                        lines[index + 1]
                    )

                    if (
                        valid_short_value(value)
                        and value.lower()
                        not in normalized_labels
                    ):
                        return value

    return ""


def extract_value_from_inline_label(
    text: str,
    label: str,
) -> str:
    """
    Extract a value from:
        Label: Value

    when multiple labels exist in the same text.
    """

    text = clean_text(text)

    if not text:
        return ""

    labels = [
        "Min Qualification",
        "Minimum Qualification",
        "Experience Level",
        "Experience Length",
        "Language Requirement",
        "Working Hours",
        "Applicant Location",
        "Location",
        "Job Type",
        "Posted",
        "Date Posted",
        "Deadline",
        "Application Deadline",
        "Closing Date",
    ]

    escaped_labels = [
        re.escape(item)
        for item in labels
    ]

    next_labels = "|".join(
        escaped_labels
    )

    pattern = (
        rf"{re.escape(label)}"
        rf"\s*:\s*"
        rf"(.*?)"
        rf"(?=\s+(?:{next_labels})\s*:|$)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return clean_text(
        match.group(1)
    )


# ============================================================
# JOB SUMMARY
# ============================================================

JOB_SUMMARY_LABELS = [
    "Min Qualification",
    "Minimum Qualification",
    "Experience Level",
    "Experience Length",
    "Language Requirement",
    "Working Hours",
    "Applicant Location",
]


def extract_job_summary_fields(
    page,
) -> Dict[str, str]:
    """
    Extract BrighterMonday's inline Job summary.

    Example:

        Min Qualification: Bachelors
        Experience Level: Mid level
        Experience Length: 3 years
        Language Requirement: English
        Working Hours: Full Time - 8 to 5
        Applicant Location: Kenya
    """

    body = get_body_text(page)

    if not body:
        return {}

    labels = [
        "Min Qualification",
        "Minimum Qualification",
        "Experience Level",
        "Experience Length",
        "Language Requirement",
        "Working Hours",
        "Applicant Location",
    ]

    escaped = [
        re.escape(label)
        for label in labels
    ]

    label_pattern = "|".join(
        escaped
    )

    matches = list(
        re.finditer(
            rf"({label_pattern})\s*:",
            body,
            flags=re.IGNORECASE,
        )
    )

    fields = {}

    for index, match in enumerate(matches):

        label = clean_text(
            match.group(1)
        ).lower()

        start = match.end()

        if index + 1 < len(matches):
            end = matches[
                index + 1
            ].start()
        else:
            end = len(body)

        value = clean_text(
            body[start:end]
        )

        # Stop obvious page chrome.
        value = re.split(
            r"\b(?:Report Job|Log in to apply now|Continue with Google|"
            r"Continue with Linkedin|Share link|Activate Notifications)\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        value = clean_text(value)

        if valid_short_value(
            value,
            max_words=20,
        ):
            fields[label] = value

    return fields


# ============================================================
# LOCATION
# ============================================================

def normalize_location(
    value: str,
) -> str:
    """Clean location value."""
    value = clean_text(value)

    if not value:
        return ""

    # Remove common country code suffix.
    value = re.sub(
        r",\s*KE\b",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"\bKE\b$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = clean_text(value)

    # Reject page fragments.
    if len(value) > 100:
        return ""

    if "job summary" in value.lower():
        return ""

    if "job descriptions" in value.lower():
        return ""

    if "requirements" in value.lower():
        return ""

    return value


def extract_location(
    page,
) -> str:
    """
    Extract job location.

    Priority:
        1. JSON-LD jobLocation
        2. Dedicated location selectors
        3. Header/meta data
        4. Structured label
        5. Safe location detection
    """

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    for data in get_job_posting_json_ld(page):

        location_data = data.get(
            "jobLocation"
        )

        if isinstance(
            location_data,
            dict,
        ):
            location_data = [
                location_data
            ]

        if not isinstance(
            location_data,
            list,
        ):
            continue

        for item in location_data:

            if not isinstance(
                item,
                dict,
            ):
                continue

            address = item.get(
                "address"
            )

            if not isinstance(
                address,
                dict,
            ):
                continue

            locality = clean_text(
                address.get(
                    "addressLocality",
                    "",
                )
            )

            region = clean_text(
                address.get(
                    "addressRegion",
                    "",
                )
            )

            country = clean_text(
                address.get(
                    "addressCountry",
                    "",
                )
            )

            if country.lower() in {
                "ke",
                "kenya",
            }:
                country = "Kenya"

            parts = []

            for part in (
                locality,
                region,
                country,
            ):
                if (
                    part
                    and part not in parts
                ):
                    parts.append(part)

            value = normalize_location(
                ", ".join(parts)
            )

            if value:
                return value

    # --------------------------------------------------------
    # 2. Dedicated selectors
    # --------------------------------------------------------

    selectors = [
        "[data-testid*='location']",
        "[data-test*='location']",
        "[class*='location']",
        "[class*='job-location']",
        "[class*='job_location']",
        "[class*='location-name']",
        "[class*='location_name']",
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

                if not text:
                    continue

                if not valid_short_value(
                    text,
                    max_words=10,
                ):
                    continue

                location = normalize_location(
                    text
                )

                if location:
                    candidates.append(
                        location
                    )

        except Exception:
            continue

    # Prefer actual Kenyan locations.
    preferred_locations = [
        "Nairobi",
        "Mombasa",
        "Kisumu",
        "Nakuru",
        "Eldoret",
        "Thika",
        "Kiambu",
        "Machakos",
        "Kenya",
        "Remote",
    ]

    for candidate in candidates:
        for preferred in preferred_locations:
            if candidate.lower() == preferred.lower():
                return candidate

    if candidates:
        return candidates[0]

    # --------------------------------------------------------
    # 3. Structured label
    # --------------------------------------------------------

    value = find_structured_label_value(
        page,
        [
            "Job Location",
            "Location",
            "Where",
        ],
    )

    value = normalize_location(
        value
    )

    if value:
        return value

    # --------------------------------------------------------
    # 4. Search safe body lines
    # --------------------------------------------------------

    lines = get_body_lines(page)

    for line in lines:

        value = clean_text(line)

        if not value:
            continue

        # Exact common locations.
        if value.lower() in {
            "nairobi",
            "mombasa",
            "kisumu",
            "nakuru",
            "eldoret",
            "thika",
            "kiambu",
            "machakos",
            "kenya",
            "remote",
        }:
            return value

        # "Nairobi, Kenya"
        if re.fullmatch(
            r"(Nairobi|Mombasa|Kisumu|Nakuru|Eldoret|Thika|Kiambu|Machakos)"
            r"(?:,\s*Kenya)?",
            value,
            flags=re.IGNORECASE,
        ):
            return value

    return ""


# ============================================================
# JOB TYPE
# ============================================================

def normalize_job_type(
    value: str,
) -> str:
    """Normalize employment type."""
    value = clean_text(value)

    if not value:
        return ""

    replacements = {
        "FULL_TIME": "Full Time",
        "PART_TIME": "Part Time",
        "CONTRACTOR": "Contract",
        "CONTRACT": "Contract",
        "TEMPORARY": "Temporary",
        "INTERN": "Internship",
        "VOLUNTEER": "Volunteer",
        "PER_DIEM": "Per Diem",
        "OTHER": "Other",
    }

    values = [
        clean_text(item)
        for item in value.split(",")
        if clean_text(item)
    ]

    normalized = []

    for item in values:
        key = item.upper()

        normalized_value = replacements.get(
            key,
            item.replace(
                "_",
                " ",
            ).title(),
        )

        if normalized_value not in normalized:
            normalized.append(
                normalized_value
            )

    return ", ".join(normalized)


def extract_job_type(
    page,
) -> str:
    """Extract employment type."""

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    for data in get_job_posting_json_ld(page):

        value = data.get(
            "employmentType"
        )

        if isinstance(
            value,
            list,
        ):
            value = ", ".join(
                clean_text(item)
                for item in value
                if clean_text(item)
            )

        if isinstance(
            value,
            str,
        ) and value.strip():

            result = normalize_job_type(
                value
            )

            if result:
                return result

    # --------------------------------------------------------
    # Visible structured field
    # --------------------------------------------------------

    value = find_structured_label_value(
        page,
        [
            "Job Type",
            "Employment Type",
            "Employment",
        ],
    )

    value = normalize_job_type(
        value
    )

    if value:
        return value

    # --------------------------------------------------------
    # Job summary
    # --------------------------------------------------------

    summary = extract_job_summary_fields(
        page
    )

    # Working hours often contains the actual
    # employment schedule, but not always the job type.
    working_hours = summary.get(
        "working hours",
        "",
    )

    if working_hours:
        if "full time" in working_hours.lower():
            return "Full Time"

        if "part time" in working_hours.lower():
            return "Part Time"

        if "intern" in working_hours.lower():
            return "Internship"

        if "contract" in working_hours.lower():
            return "Contract"

    return ""


# ============================================================
# QUALIFICATION
# ============================================================

def extract_qualification(
    page,
) -> str:
    """Extract minimum qualification."""

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    for data in get_job_posting_json_ld(page):

        education = data.get(
            "educationRequirements"
        )

        if isinstance(
            education,
            dict,
        ):

            for key in (
                "credentialCategory",
                "name",
                "description",
                "text",
            ):

                value = education.get(
                    key,
                    "",
                )

                if isinstance(
                    value,
                    str,
                ):

                    value = clean_text(
                        value
                    )

                    if valid_short_value(
                        value,
                        max_words=20,
                    ):
                        return value

        elif isinstance(
            education,
            list,
        ):

            values = []

            for item in education:

                if isinstance(
                    item,
                    dict,
                ):

                    for key in (
                        "credentialCategory",
                        "name",
                        "description",
                        "text",
                    ):

                        value = item.get(
                            key,
                            "",
                        )

                        if isinstance(
                            value,
                            str,
                        ):

                            value = clean_text(
                                value
                            )

                            if value:
                                values.append(
                                    value
                                )

                            break

                elif isinstance(
                    item,
                    str,
                ):
                    value = clean_text(
                        item
                    )

                    if value:
                        values.append(
                            value
                        )

            if values:
                return ", ".join(
                    dict.fromkeys(values)
                )

    # --------------------------------------------------------
    # Visible field
    # --------------------------------------------------------

    value = find_structured_label_value(
        page,
        [
            "Minimum Qualification",
            "Minimum Education",
            "Qualification",
            "Qualifications",
            "Education",
        ],
    )

    if valid_short_value(
        value,
        max_words=20,
    ):
        return value

    # --------------------------------------------------------
    # Job summary
    # --------------------------------------------------------

    summary = extract_job_summary_fields(
        page
    )

    value = summary.get(
        "min qualification",
        "",
    )

    if not value:
        value = summary.get(
            "minimum qualification",
            "",
        )

    if valid_short_value(
        value,
        max_words=20,
    ):
        return value

    return ""


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def extract_experience_level(
    page,
) -> str:
    """
    Extract career/experience level.

    Examples:
        Entry level
        Mid level
        Senior level
        Internship & Graduate
    """

    value = find_structured_label_value(
        page,
        [
            "Experience Level",
            "Career Level",
        ],
    )

    if valid_experience_level(
        value
    ):
        return value

    summary = extract_job_summary_fields(
        page
    )

    value = summary.get(
        "experience level",
        "",
    )

    if valid_experience_level(
        value
    ):
        return value

    return ""


def valid_experience_level(
    value: str,
) -> bool:
    """Validate experience level."""
    value = clean_text(value)

    if not value:
        return False

    lower = value.lower()

    known_levels = [
        "entry",
        "junior",
        "mid",
        "senior",
        "management",
        "executive",
        "intern",
        "graduate",
        "no experience",
    ]

    if not any(
        term in lower
        for term in known_levels
    ):
        return False

    if len(value) > 80:
        return False

    return True


# ============================================================
# EXPERIENCE LENGTH
# ============================================================

def extract_experience_length(
    page,
) -> str:
    """
    Extract required experience duration.

    Examples:
        1 year
        2 years
        3 years
        6 months
    """

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    for data in get_job_posting_json_ld(page):

        requirements = data.get(
            "experienceRequirements"
        )

        if isinstance(
            requirements,
            dict,
        ):

            months = requirements.get(
                "monthsOfExperience"
            )

            if months is not None:
                try:
                    months = int(
                        months
                    )

                    result = format_experience_months(
                        months
                    )

                    if result:
                        return result

                except (
                    ValueError,
                    TypeError,
                ):
                    pass

            description = requirements.get(
                "description",
                "",
            )

            if isinstance(
                description,
                str,
            ):
                result = extract_duration(
                    description
                )

                if result:
                    return result

        elif isinstance(
            requirements,
            str,
        ):

            result = extract_duration(
                requirements
            )

            if result:
                return result

    # --------------------------------------------------------
    # Structured field
    # --------------------------------------------------------

    value = find_structured_label_value(
        page,
        [
            "Experience Length",
            "Years of Experience",
            "Years Experience",
            "Experience Required",
            "Required Experience",
        ],
    )

    result = extract_duration(
        value
    )

    if result:
        return result

    # --------------------------------------------------------
    # Generic Experience field
    # --------------------------------------------------------

    value = find_structured_label_value(
        page,
        ["Experience"],
    )

    result = extract_duration(
        value
    )

    if result:
        return result

    # --------------------------------------------------------
    # Job summary
    # --------------------------------------------------------

    summary = extract_job_summary_fields(
        page
    )

    value = summary.get(
        "experience length",
        "",
    )

    result = extract_duration(
        value
    )

    if result:
        return result

    return ""


def extract_duration(
    value: str,
) -> str:
    """Extract a concise experience duration."""
    value = clean_text(value)

    if not value:
        return ""

    # Examples:
    # 3 years
    # 3+ years
    # 3 - 5 years
    # 6 months
    # 1 year and 6 months

    pattern = (
        r"\b"
        r"\d+(?:\.\d+)?"
        r"\s*(?:\+|[-–—]\s*\d+(?:\.\d+)?)?"
        r"\s*"
        r"(?:years?|months?)"
        r"(?:\s+and\s+\d+\s+months?)?"
        r"\b"
    )

    match = re.search(
        pattern,
        value,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return clean_text(
        match.group(0)
    )


def format_experience_months(
    months: int,
) -> str:
    """Convert months into years/months."""
    if months <= 0:
        return ""

    years = months // 12

    remaining = months % 12

    parts = []

    if years == 1:
        parts.append("1 year")
    elif years > 1:
        parts.append(
            f"{years} years"
        )

    if remaining == 1:
        parts.append("1 month")
    elif remaining > 1:
        parts.append(
            f"{remaining} months"
        )

    return " ".join(parts)


# ============================================================
# POSTED DATE
# ============================================================

def extract_posted(
    page,
) -> str:
    """Extract posted date."""

    # JSON-LD
    for data in get_job_posting_json_ld(page):

        value = data.get(
            "datePosted"
        )

        if isinstance(
            value,
            str,
        ):

            value = clean_text(
                value
            )

            if value:
                return value

    # Visible field
    value = find_structured_label_value(
        page,
        [
            "Posted",
            "Date Posted",
            "Posted Date",
        ],
    )

    if valid_date_value(
        value
    ):
        return value

    # Search common relative date patterns.
    body = get_body_text(page)

    patterns = [
        r"\b\d+\s+day(?:s)?\s+ago\b",
        r"\b\d+\s+week(?:s)?\s+ago\b",
        r"\b\d+\s+month(?:s)?\s+ago\b",
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
    """Extract application deadline."""

    # JSON-LD
    for data in get_job_posting_json_ld(page):

        value = data.get(
            "validThrough"
        )

        if isinstance(
            value,
            str,
        ):

            value = clean_text(
                value
            )

            if value:
                return value

    # Visible field
    value = find_structured_label_value(
        page,
        [
            "Deadline",
            "Application Deadline",
            "Closing Date",
            "Application Closing Date",
            "Closing",
        ],
    )

    if valid_date_value(
        value
    ):
        return value

    return ""


def valid_date_value(
    value: str,
) -> bool:
    """Reject obvious page fragments."""
    value = clean_text(value)

    if not value:
        return False

    lower = value.lower()

    if "job summary" in lower:
        return False

    if "job description" in lower:
        return False

    if "log in" in lower:
        return False

    if "apply" in lower and len(value) > 40:
        return False

    if len(value) > 100:
        return False

    return True


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(
    page,
) -> str:
    """
    Extract the main job description.

    The largest meaningful description block is preferred.
    """

    candidates = []

    selectors = [
        "[data-testid*='description']",
        "[data-test*='description']",
        "[class*='job-description']",
        "[class*='job_description']",
        "[class*='description']",
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

                if len(text) >= 300:
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

    # --------------------------------------------------------
    # Article fallback
    # --------------------------------------------------------

    try:
        articles = page.locator(
            "article"
        ).all()

        for article in articles:

            text = clean_text(
                article.inner_text()
            )

            if len(text) >= 300:
                candidates.append(
                    text
                )

    except Exception:
        pass

    if candidates:
        return max(
            candidates,
            key=len,
        )

    # --------------------------------------------------------
    # Main fallback
    # --------------------------------------------------------

    try:
        mains = page.locator(
            "main"
        ).all()

        for main in mains:

            text = clean_text(
                main.inner_text()
            )

            if len(text) >= 300:
                candidates.append(
                    text
                )

    except Exception:
        pass

    if candidates:
        return max(
            candidates,
            key=len,
        )

    return get_body_text(page)


# ============================================================
# APPLICATION
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

                if not url:
                    continue

                if url in seen:
                    continue

                seen.add(url)

                if (
                    "sign-up?apply=" in url
                    or "?apply=" in url
                    or "/job-application/" in url
                ):
                    application["url"] = url

                    return application

        except Exception:
            continue

    # --------------------------------------------------------
    # Fallback: apply links
    # --------------------------------------------------------

    try:
        links = page.locator(
            "a"
        ).all()

        for link in links:

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            text = clean_text(
                link.inner_text()
            ).lower()

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
    """

    print()
    print("=" * 60)
    print(
        "INSPECTING BRIGHTERMONDAY JOB"
    )
    print("=" * 60)

    print()
    print(
        f"URL: {job_url}"
    )

    page = get_page(context)

    try:
        response = navigate(
            page,
            job_url,
        )

        page.wait_for_timeout(
            DETAIL_WAIT
        )

        print(
            "Job page loaded."
        )

        if response:
            print(
                f"Status: {response.status}"
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
        # Combined experience
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
        # Job dictionary
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
            "application_subject": application.get(
                "subject",
                "",
            ),
        }

        # ----------------------------------------------------
        # Console output
        # ----------------------------------------------------

        print()
        print(
            "JOB INFORMATION"
        )
        print(
            "-" * 60
        )

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
        print(
            "-" * 60
        )

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
        try:
            page.close()
        except Exception:
            pass


# ============================================================
# TEST / MAIN
# ============================================================

def main():
    """
    Test the BrighterMonday browser layer.
    """

    playwright = None

    browser = None

    try:
        # ----------------------------------------------------
        # Launch browser
        # ----------------------------------------------------

        playwright, browser, context = (
            launch_browser(
                headless=HEADLESS
            )
        )

        print()
        print(
            "Opening BrighterMonday..."
        )

        # ----------------------------------------------------
        # Open homepage
        # ----------------------------------------------------

        page = get_page(
            context
        )

        response = navigate(
            page,
            BASE_URL,
        )

        if response:
            print(
                f"Status: "
                f"{response.status}"
            )

        try:
            print(
                f"Page title: "
                f"{page.title()}"
            )
        except Exception:
            pass

        page.close()

        # ----------------------------------------------------
        # Collect technology jobs
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
        # Display first 10
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

        print(
            "-" * 60
        )

        print(
            error
        )

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