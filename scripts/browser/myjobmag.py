
"""
MyJobMag browser automation layer.

Responsibilities
----------------
1. Open MyJobMag.
2. Collect Python/developer job links.
3. Inspect individual job pages.
4. Extract structured job information.
5. Detect the MyJobMag application method and links.

This module does NOT:
    - match jobs against the candidate profile
    - generate CVs
    - generate cover letters
    - submit applications
    - modify the job tracker

Run directly with:

    python -m scripts.browser.myjobmag
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


# ============================================================
# CONFIGURATION
# ============================================================

MYJOBMAG_URL = (
    "https://www.myjobmag.co.ke/"
    "jobs-by-title/developer-python"
)

MYJOBMAG_DOMAIN = "https://www.myjobmag.co.ke"

HEADLESS = False
PAGE_TIMEOUT = 60000


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value) -> str:
    """
    Normalize whitespace and remove invisible characters.
    """

    if value is None:
        return ""

    text = str(value)

    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_url(url: str) -> str:
    """
    Convert relative MyJobMag URLs to absolute URLs.
    """

    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return urljoin(
            MYJOBMAG_DOMAIN,
            url,
        )

    return url


def strip_url_query(url: str) -> str:
    """
    Remove query parameters and fragments.
    """

    if not url:
        return ""

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return url

    return (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
        f"{parsed.path}"
    )


def safe_inner_text(locator) -> str:
    """
    Safely get Playwright locator text.
    """

    try:
        return clean_text(
            locator.inner_text()
        )
    except Exception:
        return ""


def get_page_text(page) -> str:
    """
    Safely extract visible body text.
    """

    try:
        return clean_text(
            page.locator("body").inner_text()
        )
    except Exception:
        return ""


def get_page_html(page) -> str:
    """
    Safely extract page HTML.
    """

    try:
        return page.content()
    except Exception:
        return ""


def first_non_empty(values: List[str]) -> str:
    """
    Return the first non-empty value.
    """

    for value in values:

        value = clean_text(value)

        if value:
            return value

    return ""


def unique_preserve_order(
    values: List[str],
) -> List[str]:
    """
    Remove duplicates while preserving order.
    """

    result = []
    seen = set()

    for value in values:

        value = clean_text(value)

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


# ============================================================
# JOB LINK COLLECTION
# ============================================================

def is_job_url(url: str) -> bool:
    """
    Return True only for MyJobMag job detail URLs.
    """

    if not url:
        return False

    parsed = urlparse(url)

    if parsed.netloc:

        hostname = parsed.netloc.lower()

        if hostname not in {
            "www.myjobmag.co.ke",
            "myjobmag.co.ke",
        }:
            return False

    path = parsed.path.lower()

    return (
        path.startswith("/job/")
        and len(path) > len("/job/")
    )


def get_listing_title(anchor) -> str:
    """
    Extract a listing title from an anchor.
    """

    text = safe_inner_text(anchor)

    if text:
        return text

    try:
        text = clean_text(
            anchor.get_attribute("title")
        )
    except Exception:
        text = ""

    if text:
        return text

    try:
        text = clean_text(
            anchor.get_attribute("aria-label")
        )
    except Exception:
        text = ""

    return text


def collect_job_links(page) -> List[Dict]:
    """
    Collect unique MyJobMag job detail links.

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

    except Exception:

        anchors = []

    for anchor in anchors:

        try:

            href = anchor.get_attribute(
                "href"
            )

        except Exception:

            continue

        if not href:
            continue

        href = normalize_url(href)

        if not is_job_url(href):
            continue

        href = strip_url_query(
            href
        )

        if href in seen_urls:
            continue

        title = get_listing_title(
            anchor
        )

        if not title:
            continue

        lower_title = title.lower()

        if lower_title in {
            "view job",
            "apply now",
            "read more",
            "details",
        }:
            continue

        seen_urls.add(href)

        jobs.append(
            {
                "title": title,
                "url": href,
            }
        )

    print(
        f"Found {len(jobs)} job links."
    )

    for index, job in enumerate(
        jobs[:5],
        start=1,
    ):

        print(
            f"{index}. {job['title']}"
        )

        print(
            f"   {job['url']}"
        )

    return jobs


# ============================================================
# JSON-LD
# ============================================================

def get_json_ld_objects(
    soup: BeautifulSoup,
) -> List[dict]:
    """
    Extract JSON-LD objects from the page.
    """

    objects = []

    for script in soup.select(
        "script[type='application/ld+json']"
    ):

        raw = (
            script.string
            or script.get_text()
        )

        if not raw:
            continue

        raw = raw.strip()

        if not raw:
            continue

        try:

            data = json.loads(
                raw
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):

            continue

        if isinstance(data, list):

            for item in data:

                if isinstance(
                    item,
                    dict,
                ):
                    objects.append(item)

        elif isinstance(
            data,
            dict,
        ):

            objects.append(data)

            graph = data.get(
                "@graph"
            )

            if isinstance(
                graph,
                list,
            ):

                for item in graph:

                    if isinstance(
                        item,
                        dict,
                    ):
                        objects.append(item)

    return objects


def get_job_posting_json_ld(
    soup: BeautifulSoup,
) -> Optional[dict]:
    """
    Return a JobPosting JSON-LD object if present.
    """

    for data in get_json_ld_objects(
        soup
    ):

        schema_type = data.get(
            "@type"
        )

        if isinstance(
            schema_type,
            list,
        ):

            if "JobPosting" in schema_type:
                return data

        elif schema_type == "JobPosting":

            return data

    return None


# ============================================================
# TITLE
# ============================================================

def remove_title_suffix(
    title: str,
) -> str:
    """
    Remove common MyJobMag title suffixes.
    """

    title = clean_text(
        title
    )

    patterns = [
        r"\s+\|\s*MyJobMag.*$",
        r"\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December),?"
        r"\s+\d{4}.*$",
    ]

    for pattern in patterns:

        title = re.sub(
            pattern,
            "",
            title,
            flags=re.IGNORECASE,
        )

    return clean_text(
        title
    )


def extract_title(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
    fallback_title: str = "",
) -> str:
    """
    Extract the actual MyJobMag job title.

    Priority:
        1. JSON-LD title
        2. Main job-page H1
        3. Page title
        4. Listing-page fallback title
    """

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    if json_ld:

        title = clean_text(
            json_ld.get(
                "title",
                "",
            )
        )

        if title:
            return remove_title_suffix(
                title
            )

    # --------------------------------------------------------
    # 2. Job-page H1
    # --------------------------------------------------------

    for selector in [
        "main h1",
        "article h1",
        ".job-detail h1",
        ".job-details h1",
        "h1",
    ]:

        element = soup.select_one(
            selector
        )

        if not element:
            continue

        title = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if not title:
            continue

        title = remove_title_suffix(
            title
        )

        if title:
            return title

    # --------------------------------------------------------
    # 3. Page title
    # --------------------------------------------------------

    if soup.title:

        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

        title = remove_title_suffix(
            title
        )

        if title:
            return title

    # --------------------------------------------------------
    # 4. Original listing title
    # --------------------------------------------------------

    return clean_text(
        fallback_title
    )

# ============================================================
# COMPANY
# ============================================================

INVALID_COMPANY_VALUES = {
    "",
    "company",
    "employer",
    "jobs",
    "jobs by education",
    "jobs by industry",
    "remote jobs",
    "checkout salary structure",
    "view jobs",
    "view current vacancies",
    "myjobmag",
}


def is_valid_company(
    value: str,
) -> bool:
    """
    Reject navigation, salary and footer text.
    """

    value = clean_text(
        value
    )

    if not value:
        return False

    lower = value.lower()

    if lower in INVALID_COMPANY_VALUES:
        return False

    bad_fragments = [
        "salary structure",
        "checkout salary",
        "mysalaryscale",
        "view jobs",
        "view current vacancies",
        "jobs by industry",
        "jobs by education",
        "remote jobs",
        "career advice",
        "login",
        "sign up",
        "never pay",
    ]

    if any(
        fragment in lower
        for fragment in bad_fragments
    ):
        return False

    if len(value) > 150:
        return False

    return True


def extract_company_from_title(
    title: str,
) -> str:
    """
    Extract company from:

        Job Title at Company
    """

    title = clean_text(
        title
    )

    if not title:
        return ""

    match = re.search(
        r"\s+at\s+(.+)$",
        title,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    company = clean_text(
        match.group(1)
    )

    if is_valid_company(
        company
    ):
        return company

    return ""


def extract_company(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
    title: str,
) -> str:
    """
    Extract employer/company.

    Priority:
        1. JSON-LD
        2. Explicit metadata
        3. Job title
        4. Carefully selected employer links
    """

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    if json_ld:

        organization = json_ld.get(
            "hiringOrganization"
        )

        if isinstance(
            organization,
            dict,
        ):

            name = clean_text(
                organization.get(
                    "name"
                )
            )

            if is_valid_company(
                name
            ):
                return name

        elif isinstance(
            organization,
            str,
        ):

            name = clean_text(
                organization
            )

            if is_valid_company(
                name
            ):
                return name

    # --------------------------------------------------------
    # Meta
    # --------------------------------------------------------

    for selector in [
        "meta[property='job:company']",
        "meta[name='job:company']",
        "meta[name='company']",
    ]:

        element = soup.select_one(
            selector
        )

        if not element:
            continue

        value = clean_text(
            element.get("content")
        )

        if is_valid_company(
            value
        ):
            return value

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    company = extract_company_from_title(
        title
    )

    if company:
        return company

    # --------------------------------------------------------
    # Employer links
    # --------------------------------------------------------

    for anchor in soup.select(
        "a[href]"
    ):

        href = normalize_url(
            anchor.get("href", "")
        )

        text = clean_text(
            anchor.get_text(
                " ",
                strip=True,
            )
        )

        if not text:
            continue

        lower_href = href.lower()

        if (
            "company" not in lower_href
            and "employer" not in lower_href
            and "/companies/" not in lower_href
        ):
            continue

        if is_valid_company(
            text
        ):
            return text

    return ""


# ============================================================
# LABELED VALUE EXTRACTION
# ============================================================

def extract_labeled_value(
    soup: BeautifulSoup,
    labels: List[str],
) -> str:
    """
    Extract a metadata value associated with a label.

    MyJobMag pages contain a lot of navigation, sidebar,
    salary and footer text. Therefore this function prioritizes
    structured HTML relationships and avoids searching the
    entire page as one large text string.
    """

    expected = {
        clean_text(label).lower().rstrip(":")
        for label in labels
        if clean_text(label)
    }

    # --------------------------------------------------------
    # 1. Definition lists
    # --------------------------------------------------------

    for dt in soup.select("dt"):

        label = clean_text(
            dt.get_text(
                " ",
                strip=True,
            )
        ).lower().rstrip(":")

        if label not in expected:
            continue

        dd = dt.find_next_sibling("dd")

        if dd:

            value = clean_text(
                dd.get_text(
                    " ",
                    strip=True,
                )
            )

            if value:
                return value

    # --------------------------------------------------------
    # 2. Tables
    # --------------------------------------------------------

    for row in soup.select("tr"):

        cells = row.select("th, td")

        if len(cells) < 2:
            continue

        label = clean_text(
            cells[0].get_text(
                " ",
                strip=True,
            )
        ).lower().rstrip(":")

        if label not in expected:
            continue

        value = clean_text(
            cells[1].get_text(
                " ",
                strip=True,
            )
        )

        if value:
            return value

    # --------------------------------------------------------
    # 3. Label/value containers
    #
    # Look for a small element containing ONLY the label,
    # then inspect its immediate siblings or parent.
    # --------------------------------------------------------

    for element in soup.find_all(
        ["span", "strong", "b", "label"]
    ):

        label = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        ).lower().rstrip(":")

        if label not in expected:
            continue

        # ----------------------------------------------------
        # Same parent: label + value
        # ----------------------------------------------------

        parent = element.parent

        if parent:

            children = list(
                parent.children
            )

            try:
                index = children.index(
                    element
                )
            except ValueError:
                index = -1

            if index >= 0:

                for sibling in children[
                    index + 1:
                ]:

                    if not hasattr(
                        sibling,
                        "get_text",
                    ):
                        continue

                    value = clean_text(
                        sibling.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    if value and value.lower() != label:
                        if len(value) < 300:
                            return value

        # ----------------------------------------------------
        # Immediate next sibling
        # ----------------------------------------------------

        sibling = element.find_next_sibling()

        if sibling:

            value = clean_text(
                sibling.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                value
                and value.lower() != label
                and len(value) < 300
            ):
                return value

    # --------------------------------------------------------
    # 4. Common MyJobMag metadata blocks
    #
    # Search only relatively small containers instead of the
    # entire webpage.
    # --------------------------------------------------------

    for container in soup.find_all(
        ["li", "div", "p"]
    ):

        text = clean_text(
            container.get_text(
                " ",
                strip=True,
            )
        )

        if not text or len(text) > 500:
            continue

        lower_text = text.lower()

        for label in expected:

            prefix_patterns = [
                f"{label}:",
                f"{label} :",
                label,
            ]

            for prefix in prefix_patterns:

                if not lower_text.startswith(
                    prefix
                ):
                    continue

                value = clean_text(
                    text[len(prefix):]
                )

                if not value:
                    continue

                # Reject obvious navigation contamination.
                value_lower = value.lower()

                if value_lower in {
                    "jobs by",
                    "view jobs",
                    "view current vacancies",
                    "remote jobs",
                    "career advice",
                }:
                    continue

                if len(value) < 300:
                    return value

    return ""

# ============================================================
# LOCATION
# ============================================================

def extract_location(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> str:
    """
    Extract job location.
    """

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    if json_ld:

        location = json_ld.get(
            "jobLocation"
        )

        if isinstance(
            location,
            dict,
        ):

            address = location.get(
                "address"
            )

            if isinstance(
                address,
                dict,
            ):

                parts = [
                    clean_text(
                        address.get(
                            "addressLocality"
                        )
                    ),
                    clean_text(
                        address.get(
                            "addressRegion"
                        )
                    ),
                    clean_text(
                        address.get(
                            "addressCountry"
                        )
                    ),
                ]

                parts = [
                    value
                    for value in parts
                    if value
                ]

                if parts:
                    return ", ".join(parts)

            name = clean_text(
                location.get("name")
            )

            if name:
                return name

        elif isinstance(
            location,
            list,
        ):

            for item in location:

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

                parts = [
                    clean_text(
                        address.get(
                            "addressLocality"
                        )
                    ),
                    clean_text(
                        address.get(
                            "addressRegion"
                        )
                    ),
                    clean_text(
                        address.get(
                            "addressCountry"
                        )
                    ),
                ]

                parts = [
                    value
                    for value in parts
                    if value
                ]

                if parts:
                    return ", ".join(parts)

    # --------------------------------------------------------
    # Explicit metadata
    # --------------------------------------------------------

    value = extract_labeled_value(
        soup,
        [
            "location",
            "job location",
        ],
    )

    if value:

        value = clean_text(
            value
        )

        if len(value) <= 100:
            return value

    # --------------------------------------------------------
    # MyJobMag metadata row
    # --------------------------------------------------------

    text = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\bLocation\s*:?\s*"
        r"(.+?)"
        r"(?=\s+\b(?:"
        r"Job Field|Job Type|Qualification|"
        r"Experience|Posted|Deadline|Salary"
        r")\b)",
        text,
        flags=re.IGNORECASE,
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value and len(value) <= 100:
            return value

    return ""


# ============================================================
# JOB TYPE
# ============================================================

def extract_job_type(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> str:

    if json_ld:

        value = clean_text(
            json_ld.get(
                "employmentType"
            )
        )

        if value:
            return value

    return extract_labeled_value(
        soup,
        [
            "job type",
            "employment type",
        ],
    )


# ============================================================
# QUALIFICATION
# ============================================================

def extract_qualification(
    soup: BeautifulSoup,
) -> str:

    return extract_labeled_value(
        soup,
        [
            "qualification",
            "qualifications",
            "education",
        ],
    )


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience(
    soup: BeautifulSoup,
) -> str:
    """
    Extract the required experience from MyJobMag.

    Accepts common formats such as:
        2 - 4 years
        3 years
        5+ years
        2 years experience
        1-2 years

    Rejects values that appear to be unrelated page text.
    """

    value = extract_labeled_value(
        soup,
        [
            "experience",
            "years of experience",
        ],
    )

    value = clean_text(
        value
    )

    if not value:
        return ""

    # --------------------------------------------------------
    # Valid experience patterns
    # --------------------------------------------------------

    patterns = [
        r"\b\d+\s*-\s*\d+\s+years?\b",
        r"\b\d+\s+to\s+\d+\s+years?\b",
        r"\b\d+\+?\s+years?\b",
        r"\b\d+\s*-\s*\d+\s+year\s+experience\b",
        r"\b\d+\+?\s+years?\s+experience\b",
        r"\bno\s+experience\b",
        r"\bno\s+work\s+experience\b",
        r"\bentry\s+level\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            value,
            flags=re.IGNORECASE,
        )

        if match:

            return clean_text(
                match.group(0)
            )

    # --------------------------------------------------------
    # Reject obvious metadata contamination
    # --------------------------------------------------------

    lower_value = value.lower()

    invalid_fragments = [
        "location",
        "job field",
        "job type",
        "qualification",
        "posted",
        "deadline",
        "salary",
        "jobs by",
    ]

    if any(
        fragment in lower_value
        for fragment in invalid_fragments
    ):
        return ""

    # --------------------------------------------------------
    # Final safety check
    # --------------------------------------------------------

    if len(value) > 100:
        return ""

    return value

# ============================================================
# JOB FIELD
# ============================================================

def extract_job_field(
    soup: BeautifulSoup,
) -> str:
    """
    Extract the MyJobMag job field/category.

    Rejects navigation and unrelated page text.
    """

    value = extract_labeled_value(
        soup,
        [
            "job field",
            "field",
            "job category",
        ],
    )

    value = clean_text(
        value
    )

    if not value:
        return ""

    # --------------------------------------------------------
    # Reject obvious navigation/footer contamination
    # --------------------------------------------------------

    lower_value = value.lower()

    invalid_values = {
        "jobs by",
        "jobs by industry",
        "jobs by education",
        "jobs by title",
        "jobs by location",
        "remote jobs",
    }

    if lower_value in invalid_values:
        return ""

    invalid_fragments = [
        "career advice",
        "salary structure",
        "mysalaryscale",
        "view jobs",
        "view current vacancies",
        "never pay",
        "login",
        "sign up",
    ]

    if any(
        fragment in lower_value
        for fragment in invalid_fragments
    ):
        return ""

    # --------------------------------------------------------
    # Protect against accidentally capturing a paragraph
    # --------------------------------------------------------

    if len(value) > 200:
        return ""

    return value

# ============================================================
# POSTED DATE
# ============================================================

def extract_posted(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> Optional[str]:

    if json_ld:

        value = clean_text(
            json_ld.get(
                "datePosted"
            )
        )

        if value:
            return value

    value = extract_labeled_value(
        soup,
        [
            "posted",
            "date posted",
            "posted on",
        ],
    )

    if value:

        match = re.search(
            r"(?:"
            r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
            r"|"
            r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
            r"|"
            r"\d{4}-\d{2}-\d{2}"
            r")",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(0)
            )

    text = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\bPosted\s*:?\s*"
        r"("
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
        r"|"
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
        r"|"
        r"\d{4}-\d{2}-\d{2}"
        r")",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return clean_text(
            match.group(1)
        )

    return None


# ============================================================
# DEADLINE
# ============================================================

def extract_deadline(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> Optional[str]:
    """
    Extract only a real deadline value.

    This intentionally avoids returning surrounding
    paragraph text.
    """

    if json_ld:

        value = clean_text(
            json_ld.get(
                "validThrough"
            )
        )

        if value:
            return value

    date_pattern = (
        r"(?:"
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
        r"|"
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
        r"|"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|"
        r"\d{4}-\d{2}-\d{2}"
        r")"
    )

    value = extract_labeled_value(
        soup,
        [
            "deadline",
            "application deadline",
            "closing date",
        ],
    )

    if value:

        match = re.search(
            date_pattern,
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(0)
            )

        if value.lower() in {
            "not specified",
            "open",
            "rolling",
        }:
            return value

    text = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\bDeadline\s*:?\s*"
        r"("
        r"Not specified"
        r"|Open"
        r"|Rolling"
        r"|"
        + date_pattern +
        r")",
        text,
        flags=re.IGNORECASE,
    )

    if match:

        return clean_text(
            match.group(1)
        )

    return None


# ============================================================
# SALARY
# ============================================================

def extract_salary(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> Optional[str]:
    """
    Extract the job salary.

    Returns a real salary value when available and rejects
    MyJobMag salary-widget/navigation text.
    """

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    if json_ld:

        value = json_ld.get(
            "baseSalary"
        )

        if isinstance(
            value,
            dict,
        ):

            value = value.get(
                "value"
            )

            if isinstance(
                value,
                dict,
            ):
                value = value.get(
                    "value"
                )

            value = clean_text(
                value
            )

            if value:
                return value

        elif isinstance(
            value,
            str,
        ):

            value = clean_text(
                value
            )

            if value:
                return value

    # --------------------------------------------------------
    # 2. Explicit salary metadata
    # --------------------------------------------------------

    value = extract_labeled_value(
        soup,
        [
            "salary",
            "salary range",
            "remuneration",
        ],
    )

    value = clean_text(
        value
    )

    if not value:
        return None

    lower_value = value.lower()

    # --------------------------------------------------------
    # 3. Reject MyJobMag salary-widget text
    # --------------------------------------------------------

    invalid_fragments = [
        "salary structure",
        "mysalaryscale",
        "checkout",
        "employees",
        "from employees",
        "view salary",
        "salary insights",
    ]

    if any(
        fragment in lower_value
        for fragment in invalid_fragments
    ):
        return None

    # --------------------------------------------------------
    # 4. Reject obvious navigation/footer content
    # --------------------------------------------------------

    invalid_values = {
        "not specified",
        "salary",
        "remuneration",
        "n/a",
        "na",
        "-",
    }

    if lower_value in invalid_values:
        return None

    # --------------------------------------------------------
    # 5. Protect against long paragraph capture
    # --------------------------------------------------------

    if len(value) > 200:
        return None

    return value

# ============================================================
# JOB CONTENT
# ============================================================

SECTION_KEYWORDS = {
    "description": [
        "job description",
        "role description",
        "position description",
        "about the job",
        "about the role",
        "about this role",
        "about this position",
        "job purpose",
        "role purpose",
        "job overview",
        "role overview",
        "position overview",
    ],

    "responsibilities": [
        "key responsibilities",
        "main responsibilities",
        "responsibilities",
        "responsibility",
        "roles and responsibilities",
        "key duties",
        "main duties",
        "duties and responsibilities",
        "job duties",
        "duties",
        "key tasks",
        "key accountabilities",
    ],

    "requirements": [
        "requirements",
        "requirement",
        "key requirements",
        "minimum requirements",
        "qualifications",
        "qualification",
        "qualifications and requirements",
        "academic qualifications",
        "professional qualifications",
        "education and experience",
        "knowledge, skills and experience",
        "knowledge, experience and qualifications",
        "skills and experience",
        "experience and qualifications",
        "knowledge and skills",
        "essential skills",
        "desired skills",
        "who you are",
        "what we are looking for",
    ],
}


HEADING_TAGS = {
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}


WRAPPER_TAGS = {
    "p",
    "div",
    "li",
}


def heading_text(
    element,
) -> str:

    name = getattr(
        element,
        "name",
        None,
    )

    if not name:
        return ""

    name = name.lower()

    if name in WRAPPER_TAGS:

        strong = element.find(
            ["strong", "b"]
        )

        if strong is not None:

            return clean_text(
                strong.get_text(
                    " ",
                    strip=True,
                )
            )

    return clean_text(
        element.get_text(
            " ",
            strip=True,
        )
    )


def is_heading_like(
    element,
) -> bool:

    name = getattr(
        element,
        "name",
        None,
    )

    if not name:
        return False

    name = name.lower()

    if name in HEADING_TAGS:

        text = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        return 0 < len(text) < 150

    if name in WRAPPER_TAGS:

        strong = element.find(
            ["strong", "b"]
        )

        if strong is None:
            return False

        wrapper_text = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        strong_text = clean_text(
            strong.get_text(
                " ",
                strip=True,
            )
        )

        if not strong_text:
            return False

        if len(strong_text) >= 150:
            return False

        return (
            wrapper_text
            == strong_text
        )

    return False


def heading_matches(
    text: str,
    keywords: List[str],
) -> bool:

    text = clean_text(
        text
    ).lower().strip(
        ": -"
    )

    if not text:
        return False

    return any(
        keyword in text
        for keyword in keywords
    )


def extract_section_by_heading(
    soup: BeautifulSoup,
    keywords: List[str],
) -> str:
    """
    Extract text belonging to a section heading.

    Supports:
        - h2/h3/h4/h5/h6 headings
        - bold/strong paragraph headings
        - nested content containers
        - sibling paragraphs/divs/lists

    Stops when another heading-like section is reached.
    """

    candidates = soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "li",
        ]
    )

    target = None

    # --------------------------------------------------------
    # Find matching heading
    # --------------------------------------------------------

    for element in candidates:

        if not is_heading_like(element):
            continue

        text = heading_text(element)

        if heading_matches(
            text,
            keywords,
        ):

            target = element
            break

    if target is None:
        return ""

    collected = []

    # --------------------------------------------------------
    # First inspect direct siblings
    # --------------------------------------------------------

    for sibling in target.next_siblings:

        name = getattr(
            sibling,
            "name",
            None,
        )

        # Stop at the next heading
        if (
            name
            and is_heading_like(sibling)
        ):
            break

        if hasattr(
            sibling,
            "get_text",
        ):

            text = clean_text(
                sibling.get_text(
                    " ",
                    strip=True,
                )
            )

        else:

            text = clean_text(
                str(sibling)
            )

        if text:
            collected.append(text)

    direct_text = clean_text(
        " ".join(collected)
    )

    if direct_text:
        return direct_text

    # --------------------------------------------------------
    # Nested-container fallback
    # --------------------------------------------------------

    parent = target.parent

    if parent:

        collected = []

        for element in parent.find_all(
            recursive=False
        ):

            if element is target:
                continue

            if is_heading_like(element):

                heading = heading_text(
                    element
                )

                if heading_matches(
                    heading,
                    keywords,
                ):
                    continue

                # Another section begins.
                break

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if text:
                collected.append(text)

        nested_text = clean_text(
            " ".join(collected)
        )

        if nested_text:
            return nested_text

    # --------------------------------------------------------
    # Parent-container fallback
    # --------------------------------------------------------

    container = target.parent

    if container:

        text_parts = []

        for element in container.find_all(
            [
                "p",
                "li",
                "div",
            ]
        ):

            if element is target:
                continue

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            if len(text) > 3000:
                continue

            text_parts.append(text)

        fallback_text = unique_preserve_order(
            text_parts
        )

        if fallback_text:

            return clean_text(
                " ".join(
                    fallback_text
                )
            )

    return ""

def find_main_content_container(
    soup: BeautifulSoup,
):
    """
    Find the smallest meaningful job content container.
    """

    selectors = [
        "main",
        "article",
        "[role='main']",
        ".job-details",
        ".job-description",
        ".job-detail",
        ".job-content",
        ".details",
    ]

    candidates = []

    for selector in selectors:

        for element in soup.select(
            selector
        ):

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if 300 <= len(text) <= 15000:

                candidates.append(
                    (
                        len(text),
                        element,
                    )
                )

    if candidates:

        candidates.sort(
            key=lambda item: item[0]
        )

        return candidates[0][1]

    return soup.body

def extract_job_content(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> Dict[str, str]:
    """
    Extract description, responsibilities and requirements.

    Uses section-heading extraction first, then JSON-LD and
    main-container fallbacks.
    """

    content = {
        "description": "",
        "responsibilities": "",
        "requirements": "",
    }

    # --------------------------------------------------------
    # 1. Find sections using headings
    # --------------------------------------------------------

    for key, keywords in SECTION_KEYWORDS.items():

        value = extract_section_by_heading(
            soup,
            keywords,
        )

        if value:
            content[key] = clean_text(
                value
            )

    # --------------------------------------------------------
    # 2. JSON-LD description fallback
    # --------------------------------------------------------

    if not content["description"] and json_ld:

        description = clean_text(
            json_ld.get(
                "description",
                "",
            )
        )

        if description:
            content["description"] = description

    # --------------------------------------------------------
    # 3. Main content container fallback
    # --------------------------------------------------------

    container = find_main_content_container(
        soup
    )

    if container:

        # -----------------------------------------------
        # Description fallback
        # -----------------------------------------------

        if not content["description"]:

            text = clean_text(
                container.get_text(
                    " ",
                    strip=True,
                )
            )

            if 100 <= len(text) <= 15000:

                content["description"] = text

        # -----------------------------------------------
        # Section fallback inside the container
        # -----------------------------------------------

        for key, keywords in SECTION_KEYWORDS.items():

            if content[key]:
                continue

            candidates = container.find_all(
                [
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                    "p",
                    "div",
                    "li",
                ]
            )

            for element in candidates:

                if not is_heading_like(
                    element
                ):
                    continue

                heading = heading_text(
                    element
                )

                if not heading_matches(
                    heading,
                    keywords,
                ):
                    continue

                collected = []

                # ---------------------------------------
                # First try following siblings
                # ---------------------------------------

                for sibling in element.next_siblings:

                    if (
                        getattr(
                            sibling,
                            "name",
                            None,
                        )
                        and is_heading_like(
                            sibling
                        )
                    ):
                        break

                    if hasattr(
                        sibling,
                        "get_text",
                    ):

                        text = clean_text(
                            sibling.get_text(
                                " ",
                                strip=True,
                            )
                        )

                    else:

                        text = clean_text(
                            str(sibling)
                        )

                    if text:
                        collected.append(
                            text
                        )

                value = clean_text(
                    " ".join(
                        collected
                    )
                )

                if value:
                    content[key] = value
                    break

    # --------------------------------------------------------
    # 4. Prevent duplicate full-page content
    # --------------------------------------------------------

    for key in content:

        value = clean_text(
            content[key]
        )

        if len(value) > 15000:
            value = value[:15000]

        content[key] = value

    return content


# ============================================================
# SKILLS
# ============================================================

SKILL_PATTERNS = [
    ("Python", r"\bpython\b"),
    ("JavaScript", r"\bjavascript\b"),
    ("TypeScript", r"\btypescript\b"),
    ("React", r"\breact(?:\.js)?\b"),
    ("Next.js", r"\bnext\.?js\b"),
    ("Node.js", r"\bnode(?:\.js)?\b"),
    ("Flask", r"\bflask\b"),
    ("Django", r"\bdjango\b"),
    ("FastAPI", r"\bfastapi\b"),
    ("Java", r"\bjava\b"),
    ("PHP", r"\bphp\b"),
    ("C#", r"\bc#\b"),
    ("C++", r"\bc\+\+\b"),
    ("Go", r"\bgo(?:lang)?\b"),
    ("Ruby", r"\bruby\b"),
    ("SQL", r"\bsql\b"),
    ("MySQL", r"\bmysql\b"),
    ("PostgreSQL", r"\bpostgres(?:ql)?\b"),
    ("MongoDB", r"\bmongodb\b"),
    ("SQLite", r"\bsqlite\b"),
    ("Database Management", r"\bdatabase management\b"),
    ("REST API", r"\brest(?:ful)?\s+api(?:s)?\b"),
    ("API", r"\bapi(?:s)?\b"),
    ("Git", r"\bgit\b"),
    ("GitHub", r"\bgithub\b"),
    ("Docker", r"\bdocker\b"),
    ("Kubernetes", r"\bkubernetes\b"),
    ("AWS", r"\baws\b"),
    ("Azure", r"\bazure\b"),
    ("GCP", r"\b(?:google cloud|gcp)\b"),
    ("Power BI", r"\bpower\s+bi\b"),
    ("Machine Learning", r"\bmachine learning\b"),
    ("Artificial Intelligence", r"\bartificial intelligence\b"),
    ("AI", r"\bai\b"),
    ("Data Engineering", r"\bdata engineering\b"),
    ("Spark", r"\bspark\b"),
    ("Microsoft Fabric", r"\bmicrosoft fabric\b"),
    ("SAS", r"\bsas\b"),
    ("R", r"(?<![A-Za-z])R(?![A-Za-z])"),
    ("Automation", r"\bautomation\b"),
    ("Tailwind CSS", r"\btailwind(?:\s+css)?\b"),
    ("HTML", r"\bhtml5?\b"),
    ("CSS", r"\bcss3?\b"),
]


def extract_skills(
    text: str,
) -> List[str]:
    """
    Extract known technical skills from job text.

    Uses the existing SKILL_PATTERNS definitions while
    protecting against false positives from very short or
    generic terms.
    """

    text = clean_text(
        text
    )

    if not text:
        return []

    skills = []

    for skill, pattern in SKILL_PATTERNS:

        # ----------------------------------------------------
        # Avoid extremely short generic skills being detected
        # from unrelated text.
        # ----------------------------------------------------

        if skill == "AI":

            if re.search(
                r"\bAI\b",
                text,
                flags=re.IGNORECASE,
            ):
                skills.append(skill)

            continue

        if skill == "R":

            if re.search(
                r"(?<![A-Za-z])R(?![A-Za-z])",
                text,
            ):
                skills.append(skill)

            continue

        # ----------------------------------------------------
        # Normal skill matching
        # ----------------------------------------------------

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            skills.append(skill)

    return unique_preserve_order(
        skills
    )

# ============================================================
# APPLICATION DETECTION
# ============================================================

def is_myjobmag_apply_url(
    url: str,
) -> bool:

    if not url:
        return False

    parsed = urlparse(
        url
    )

    return (
        parsed.netloc.lower()
        in {
            "www.myjobmag.co.ke",
            "myjobmag.co.ke",
        }
        and parsed.path.lower().startswith(
            "/apply-now/"
        )
    )


def is_external_application_url(
    url: str,
) -> bool:

    if not url:
        return False

    parsed = urlparse(
        url
    )

    hostname = (
        parsed.netloc.lower()
    )

    if not hostname:
        return False

    return hostname not in {
        "www.myjobmag.co.ke",
        "myjobmag.co.ke",
    }

def detect_application(
    page,
    soup: BeautifulSoup,
    page_url: str,
) -> Dict:
    """
    Detect the actual application method and destination.

    MyJobMag may expose an /apply-now/<id> intermediary URL.
    A separate temporary Playwright page is used to follow that
    URL so the original job page remains untouched.

    No application is submitted.
    """

    application_url = ""
    myjobmag_url = ""
    external_urls = []
    application_links = []

    # --------------------------------------------------------
    # Find MyJobMag application URL
    # --------------------------------------------------------

    for anchor in soup.select("a[href]"):

        href = anchor.get("href")

        if not href:
            continue

        href = normalize_url(href)
        href = strip_url_query(href)

        text = clean_text(
            anchor.get_text(
                " ",
                strip=True,
            )
        )

        if is_myjobmag_apply_url(href):

            myjobmag_url = href

            application_links.append(
                {
                    "text": text,
                    "url": href,
                }
            )

            break

    # --------------------------------------------------------
    # Follow MyJobMag application redirect
    # using a separate temporary page
    # --------------------------------------------------------

    if myjobmag_url:

        print()
        print(
            "Following MyJobMag application redirect..."
        )

        temp_page = None

        try:

            temp_page = page.context.new_page()

            temp_page.goto(
                myjobmag_url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT,
            )

            try:

                temp_page.wait_for_load_state(
                    "networkidle",
                    timeout=10000,
                )

            except Exception:

                pass

            final_url = clean_text(
                temp_page.url
            )

            # ------------------------------------------------
            # Detect external destination
            # ------------------------------------------------

            if (
                final_url
                and is_external_application_url(
                    final_url
                )
            ):

                final_url = strip_url_query(
                    final_url
                )

                external_urls.append(
                    final_url
                )

                application_links.append(
                    {
                        "text": "External application",
                        "url": final_url,
                    }
                )

        except Exception as error:

            print(
                "Could not follow application redirect:"
            )

            print(
                f"  {error}"
            )

        finally:

            if temp_page:

                try:
                    temp_page.close()
                except Exception:
                    pass

    # --------------------------------------------------------
    # Determine primary application method
    # --------------------------------------------------------

    if external_urls:

        method = "external"
        primary_url = external_urls[0]

    elif myjobmag_url:

        method = "myjobmag"
        primary_url = myjobmag_url

    else:

        method = "unknown"
        primary_url = ""

    return {
        "method": method,
        "url": primary_url,
        "myjobmag_url": myjobmag_url,
        "external_urls": external_urls,
        "links": application_links,
    }

# ============================================================
# NAVIGATION
# ============================================================

def navigate(
    page,
    url: str,
):
    """
    Navigate the supplied Playwright Page.
    """

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=PAGE_TIMEOUT,
    )

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=10000,
        )

    except Exception:

        pass

    return response


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(
    page,
    url: str,
    fallback_title: str = "",
) -> Dict:
    """
    Inspect a MyJobMag job page.

    IMPORTANT:
        `page` must be a Playwright Page.

    The automation pipeline already owns the page,
    so this function does NOT call context.new_page().
    """

    print()
    print("=" * 60)
    print("INSPECTING MYJOBMAG JOB")
    print("=" * 60)
    print()

    print(
        f"URL: {url}"
    )

    response = navigate(
        page,
        url,
    )

    print(
        "Job navigation started."
    )

    print(
        "Job page loaded."
    )

    if response:

        try:

            print(
                f"Status: {response.status}"
            )

        except Exception:

            pass

    try:

        print(
            f"Page title: {page.title()}"
        )

    except Exception:

        pass

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    html = get_page_html(
        page
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    json_ld = (
        get_job_posting_json_ld(
            soup
        )
    )

    if json_ld:

        print(
            "JSON-LD JobPosting found."
        )

    else:

        print(
            "No JSON-LD JobPosting found. "
            "Using DOM/container extraction."
        )

    # --------------------------------------------------------
    # Core metadata
    # --------------------------------------------------------

    title = extract_title(
        soup,
        json_ld,
        fallback_title,
    )

    company = extract_company(
        soup,
        json_ld,
        title,
    )

    location = extract_location(
        soup,
        json_ld,
    )

    job_type = extract_job_type(
        soup,
        json_ld,
    )

    qualification = extract_qualification(
        soup
    )

    experience = extract_experience(
        soup
    )

    job_field = extract_job_field(
        soup
    )

    posted = extract_posted(
        soup,
        json_ld,
    )

    deadline = extract_deadline(
        soup,
        json_ld,
    )

    salary = extract_salary(
        soup,
        json_ld,
    )

    # --------------------------------------------------------
    # Content
    # --------------------------------------------------------

    content = extract_job_content(
        soup,
        json_ld,
    )

    description = content.get(
        "description",
        "",
    )

    responsibilities = content.get(
        "responsibilities",
        "",
    )

    requirements = content.get(
        "requirements",
        "",
    )

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    skill_text = " ".join(
        [
            title,
            description,
            responsibilities,
            requirements,
        ]
    )

    skills = extract_skills(
        skill_text
    )

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    application = detect_application(
        page,
        soup,
        url,
    )

    # --------------------------------------------------------
    # Final structured result
    # --------------------------------------------------------

    job = {
        "title": title,
        "company": company,
        "location": location,
        "job_type": job_type,
        "qualification": qualification,
        "experience": experience,
        "job_field": job_field,
        "posted": posted,
        "deadline": deadline,
        "salary": salary,
        "description": description,
        "responsibilities": responsibilities,
        "requirements": requirements,
        "skills": skills,
        "url": url,
        "application": application,
        "application_method": application.get(
            "method",
            "unknown",
        ),
        "application_url": application.get(
            "url",
            "",
        ),
    }

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("EXTRACTED JOB")
    print("=" * 60)

    print(
        f"Title: {job['title']}"
    )

    print(
        f"Company: "
        f"{job['company'] or 'Not found'}"
    )

    print(
        f"Location: "
        f"{job['location'] or 'Not specified'}"
    )

    print(
        f"Job type: "
        f"{job['job_type'] or 'Not specified'}"
    )

    print(
        f"Qualification: "
        f"{job['qualification'] or 'Not specified'}"
    )

    print(
        f"Experience: "
        f"{job['experience'] or 'Not specified'}"
    )

    print(
        f"Job field: "
        f"{job['job_field'] or 'Not specified'}"
    )

    print(
        f"Posted: "
        f"{job['posted'] or 'Not specified'}"
    )

    print(
        f"Deadline: "
        f"{job['deadline'] or 'Not specified'}"
    )

    print(
        f"Salary: "
        f"{job['salary'] or 'Not specified'}"
    )

    print(
        f"Description length: "
        f"{len(job['description'])}"
    )

    print(
        f"Responsibilities length: "
        f"{len(job['responsibilities'])}"
    )

    print(
        f"Requirements length: "
        f"{len(job['requirements'])}"
    )

    print(
        "Skills: "
        + (
            ", ".join(
                job["skills"]
            )
            if job["skills"]
            else "None detected"
        )
    )

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    print()
    print("APPLICATION")
    print("-" * 60)

    print(
        f"Method: "
        f"{application.get('method', 'unknown')}"
    )

    if application.get(
        "url"
    ):

        print(
            f"URL: "
            f"{application['url']}"
        )

    links = application.get(
        "links",
        [],
    )

    if links:

        print()
        print(
            "APPLICATION-RELATED LINKS"
        )

        print(
            "-" * 60
        )

        for link in links:

            text = (
                link.get("text")
                or "Application link"
            )

            print(
                f"• {text}"
            )

            print(
                f"  {link.get('url', '')}"
            )

    print()
    print("=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)

    return job


# ============================================================
# TEST
# ============================================================

def main():
    """
    Test the MyJobMag browser layer.
    """

    playwright = None
    browser = None
    context = None
    page = None

    try:

        # ----------------------------------------------------
        # Launch browser
        # ----------------------------------------------------

        (
            playwright,
            browser,
            context,
        ) = launch_browser(
            headless=HEADLESS
        )

        # ----------------------------------------------------
        # Open listing page
        # ----------------------------------------------------

        print()
        print(
            "Opening MyJobMag Python jobs..."
        )

        page = context.new_page()

        response = navigate(
            page,
            MYJOBMAG_URL,
        )

        print(
            "MyJobMag page loaded."
        )

        if response:

            try:

                print(
                    f"Status: {response.status}"
                )

            except Exception:

                pass

        try:

            print(
                f"Title: {page.title()}"
            )

        except Exception:

            pass

        # ----------------------------------------------------
        # Collect jobs
        # ----------------------------------------------------

        jobs = collect_job_links(
            page
        )

        # ----------------------------------------------------
        # Test first job
        # ----------------------------------------------------

        if not jobs:

            print()
            print(
                "No MyJobMag job listings found."
            )

            return

        print()
        print("=" * 60)
        print("TESTING FIRST JOB")
        print("=" * 60)

        inspect_job(
            page,
            jobs[0]["url"],
            jobs[0]["title"],
        )

    except Exception as error:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)

        print(
            str(error)
        )

    finally:

        if page:

            try:
                page.close()
            except Exception:
                pass

        if browser and playwright:

            print()
            print(
                "Closing browser..."
            )

            close_browser(
                playwright,
                browser,
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

