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
# HELPERS
# ============================================================

def clean_text(value) -> str:
    """
    Normalize whitespace and remove surrounding whitespace.
    """

    if value is None:
        return ""

    text = str(value)

    text = text.replace("\xa0", " ")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_url(url: str) -> str:
    """
    Convert a relative MyJobMag URL into an absolute URL.
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
    Safely extract the current page HTML.
    """

    try:
        return page.content()
    except Exception:
        return ""


def safe_inner_text(locator) -> str:
    """
    Safely get inner text from a Playwright locator.
    """

    try:
        return clean_text(
            locator.inner_text()
        )
    except Exception:
        return ""


def first_non_empty(values: List[str]) -> str:
    """
    Return the first non-empty string.
    """

    for value in values:
        value = clean_text(value)

        if value:
            return value

    return ""


# ============================================================
# JOB LINK COLLECTION
# ============================================================

def is_job_url(url: str) -> bool:
    """
    Determine whether a URL is a MyJobMag job detail page.

    Real MyJobMag job pages use:

        /job/

    We intentionally reject:
        /jobs/
        /apply-now/
        /blog/
        /companies/
        etc.
    """

    if not url:
        return False

    parsed = urlparse(url)

    if parsed.netloc:
        hostname = parsed.netloc.lower()

        if (
            hostname != "www.myjobmag.co.ke"
            and hostname != "myjobmag.co.ke"
        ):
            return False

    path = parsed.path.lower()

    return (
        path.startswith("/job/")
        and len(path) > len("/job/")
    )


def get_listing_title(anchor) -> str:
    """
    Extract a job title from a listing anchor.

    MyJobMag markup can contain nested elements, so we try:
        1. anchor text
        2. title attribute
        3. aria-label
    """

    try:
        text = clean_text(
            anchor.inner_text()
        )
    except Exception:
        text = ""

    if text:
        return text

    try:
        title = clean_text(
            anchor.get_attribute("title")
        )
    except Exception:
        title = ""

    if title:
        return title

    try:
        aria = clean_text(
            anchor.get_attribute("aria-label")
        )
    except Exception:
        aria = ""

    return aria


def collect_job_links(page) -> List[Dict]:
    """
    Collect unique MyJobMag job links from the listing page.

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

        # Remove query strings/fragments.
        parsed = urlparse(href)

        href = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{parsed.path}"
        )

        if href in seen_urls:
            continue

        title = get_listing_title(
            anchor
        )

        if not title:
            continue

        # MyJobMag sometimes places duplicate/nested links
        # on the page. Avoid obvious non-job text.
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
    Extract JSON-LD objects.

    Handles:
        - dictionaries
        - lists
        - @graph
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
                        objects.append(
                            item
                        )

    return objects


def get_job_posting_json_ld(
    soup: BeautifulSoup,
) -> Optional[dict]:
    """
    Return the first JSON-LD JobPosting object.
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
# JOB TITLE
# ============================================================

def extract_title(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
    fallback_title: str = "",
) -> str:
    """
    Extract the actual job title.
    """

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    if json_ld:

        title = clean_text(
            json_ld.get(
                "title"
            )
        )

        if title:
            return title

    # --------------------------------------------------------
    # 2. Main H1
    # --------------------------------------------------------

    for selector in [
        "main h1",
        "article h1",
        "h1",
    ]:

        element = soup.select_one(
            selector
        )

        if element:

            title = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if title:
                return remove_title_suffix(
                    title
                )

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

    return clean_text(
        fallback_title
    )


def remove_title_suffix(
    title: str,
) -> str:
    """
    Remove common MyJobMag page-title suffixes.

    Example:

        ICT Data Scientist & AI Developer at Britam
        September, 2026 | MyJobMag

    becomes:

        ICT Data Scientist & AI Developer at Britam
    """

    title = clean_text(
        title
    )

    patterns = [
        r"\s+\|\s*MyJobMag.*$",
        r"\s+September,\s+\d{4}.*$",
        r"\s+August,\s+\d{4}.*$",
        r"\s+July,\s+\d{4}.*$",
        r"\s+June,\s+\d{4}.*$",
        r"\s+May,\s+\d{4}.*$",
        r"\s+April,\s+\d{4}.*$",
        r"\s+March,\s+\d{4}.*$",
        r"\s+February,\s+\d{4}.*$",
        r"\s+January,\s+\d{4}.*$",
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
}


def is_valid_company(
    value: str,
) -> bool:
    """
    Reject navigation/salary/widget text accidentally
    captured as a company.
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
        "jobs by industry",
        "jobs by education",
        "remote jobs",
        "career advice",
        "login",
        "sign up",
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
    Extract employer from:

        Job Title at Company

    This is an important fallback because MyJobMag's
    surrounding page contains many unrelated links.
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
        1. JSON-LD hiringOrganization
        2. Explicit employer/company metadata
        3. Job title "at Company"
        4. Carefully selected links
    """

    # --------------------------------------------------------
    # 1. JSON-LD
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
    # 2. Meta tags
    # --------------------------------------------------------

    meta_selectors = [
        "meta[property='job:company']",
        "meta[name='job:company']",
        "meta[name='company']",
        "meta[property='og:site_name']",
    ]

    for selector in meta_selectors:

        element = soup.select_one(
            selector
        )

        if not element:
            continue

        value = clean_text(
            element.get(
                "content"
            )
        )

        if is_valid_company(
            value
        ) and value.lower() != "myjobmag":
            return value

    # --------------------------------------------------------
    # 3. Extract from title
    # --------------------------------------------------------

    company = extract_company_from_title(
        title
    )

    if company:
        return company

    # --------------------------------------------------------
    # 4. Explicit HTML labels
    # --------------------------------------------------------

    label_patterns = [
        r"company",
        r"employer",
        r"hiring\s+organization",
    ]

    for element in soup.find_all(
        string=True
    ):

        label = clean_text(
            str(element)
        )

        if not label:
            continue

        if not any(
            re.fullmatch(
                pattern,
                label,
                flags=re.IGNORECASE,
            )
            for pattern in label_patterns
        ):
            continue

        parent = element.parent

        if not parent:
            continue

        # Check next sibling.
        sibling = parent.find_next_sibling()

        if sibling:

            value = clean_text(
                sibling.get_text(
                    " ",
                    strip=True,
                )
            )

            if is_valid_company(
                value
            ):
                return value

    return ""


# ============================================================
# GENERIC LABEL EXTRACTION
# ============================================================

def extract_labeled_value(
    soup: BeautifulSoup,
    labels: List[str],
) -> str:
    """
    Extract a value associated with a label.

    Handles:
        - definition lists
        - tables
        - label/value containers
        - nearby sibling elements
    """

    expected = {
        clean_text(label).lower()
        for label in labels
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
        ).lower()

        if label not in expected:
            continue

        dd = dt.find_next_sibling(
            "dd"
        )

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

        cells = row.select(
            "th, td"
        )

        if len(cells) < 2:
            continue

        label = clean_text(
            cells[0].get_text(
                " ",
                strip=True,
            )
        ).lower()

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
    # 3. Label/value HTML elements
    # --------------------------------------------------------

    for element in soup.find_all(
        ["span", "div", "p", "li"]
    ):

        text = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if not text:
            continue

        lower = text.lower()

        for expected_label in expected:

            if lower == expected_label:

                sibling = (
                    element.find_next_sibling()
                )

                if sibling:

                    value = clean_text(
                        sibling.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    if value:
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
    # 1. JSON-LD
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

                city = clean_text(
                    address.get(
                        "addressLocality"
                    )
                )

                region = clean_text(
                    address.get(
                        "addressRegion"
                    )
                )

                country = clean_text(
                    address.get(
                        "addressCountry"
                    )
                )

                parts = [
                    part
                    for part in [
                        city,
                        region,
                        country,
                    ]
                    if part
                ]

                if parts:
                    return ", ".join(parts)

            value = clean_text(
                location.get(
                    "name"
                )
            )

            if value:
                return value

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

                city = clean_text(
                    address.get(
                        "addressLocality"
                    )
                )

                region = clean_text(
                    address.get(
                        "addressRegion"
                    )
                )

                country = clean_text(
                    address.get(
                        "addressCountry"
                    )
                )

                parts = [
                    part
                    for part in [
                        city,
                        region,
                        country,
                    ]
                    if part
                ]

                if parts:
                    return ", ".join(parts)

    # --------------------------------------------------------
    # 2. Explicit location label
    # --------------------------------------------------------

    value = extract_labeled_value(
        soup,
        [
            "location",
            "job location",
            "location:",
        ],
    )

    if value:

        value = clean_text(
            value
        )

        if len(value) < 100:
            return value

    # --------------------------------------------------------
    # 3. MyJobMag metadata pattern
    # --------------------------------------------------------

    body = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\bLocation\s+([A-Za-z][A-Za-z ,/&-]{1,60}?)(?=\s+(?:Job Field|Job Type|Qualification|Experience|Posted|Deadline)\b)",
        body,
        flags=re.IGNORECASE,
    )

    if match:

        location = clean_text(
            match.group(1)
        )

        if location:
            return location

    return ""


# ============================================================
# JOB TYPE / QUALIFICATION / EXPERIENCE
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
            "type",
        ],
    )


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


def extract_experience(
    soup: BeautifulSoup,
) -> str:

    return extract_labeled_value(
        soup,
        [
            "experience",
            "years of experience",
        ],
    )


# ============================================================
# DATE / DEADLINE
# ============================================================

DEADLINE_HEAD_RE = re.compile(
    r"^(?:"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"        # 16 Sep 2026
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"     # Sep 16, 2026
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"          # 16/09/2026
    r"|\d{4}-\d{2}-\d{2}"                      # 2026-09-16
    r"|Not specified|Open|Rolling"
    r")",
    flags=re.IGNORECASE,
)


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

    # Explicit label.
    value = extract_labeled_value(
        soup,
        [
            "posted",
            "date posted",
            "posted on",
        ],
    )

    if value:
        return value

    # MyJobMag commonly exposes:
    #
    # Posted: Sep 16, 2026
    #
    text = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\bPosted\s*:\s*"
        r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return clean_text(
            match.group(1)
        )

    return None


def extract_deadline(
    soup: BeautifulSoup,
    json_ld: Optional[dict],
) -> Optional[str]:
    """
    Extract the application deadline.

    IMPORTANT: We only accept values that *start* with a real
    date (or the literal "Not specified"). MyJobMag's page
    layout places the deadline next to other metadata, and a
    naive label lookup or a broad regex will happily return
    the entire surrounding paragraph.
    """

    if json_ld:

        value = clean_text(
            json_ld.get(
                "validThrough"
            )
        )

        if value:
            return value

    # --------------------------------------------------------
    # 1. Labelled value — but only trust it if it starts
    #    like a date (or a known "empty" marker).
    # --------------------------------------------------------

    value = extract_labeled_value(
        soup,
        [
            "deadline",
            "application deadline",
            "closing date",
        ],
    )

    if value:

        match = DEADLINE_HEAD_RE.match(value)

        if match:
            return clean_text(
                match.group(0)
            )

    # --------------------------------------------------------
    # 2. Text scan — bounded match.
    # --------------------------------------------------------

    text = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\bDeadline\s*:?\s*"
        r"(Not specified"
        r"|Open"
        r"|Rolling"
        r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
        r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
        r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{4}-\d{2}-\d{2})",
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

    # Use only explicitly labelled salary.
    # Do NOT search the entire page for "KSh" because MyJobMag
    # places salary widgets for the company elsewhere on the page.
    value = extract_labeled_value(
        soup,
        [
            "salary",
            "salary range",
            "remuneration",
        ],
    )

    if value:

        lower = value.lower()

        if (
            "salary structure" not in lower
            and "mysalaryscale" not in lower
        ):
            return value

    return None


# ============================================================
# JOB CONTENT
# ============================================================
#
# MyJobMag does not use semantic <h2>/<h3> tags for section
# headings on every job page. The most common shape is:
#
#     <p><strong>Job Description</strong></p>
#     <p>...</p>
#
#     <p><strong>Key Responsibilities</strong></p>
#     <ul>...</ul>
#
#     <p><strong>Knowledge, Skills and Experience</strong></p>
#     <ul>...</ul>
#
# Sometimes they are <h2>/<h3>, sometimes bolded <p>. We
# therefore:
#   1. Detect "heading-like" elements (h2-h6, or a <p>/<div>/
#      <li> whose only content is a <strong>/<b>).
#   2. Classify each heading by *keyword* rather than exact
#      alias so headings like "Knowledge, Skills and
#      Experience" are correctly identified.
#   3. Stop a section at the *next heading of any kind*, not
#      just the next known one.

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

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_WRAPPER_TAGS = {"p", "div", "li"}
_BOLD_TAGS = {"strong", "b"}


def _heading_text(el) -> str:
    """
    Return the visible text of a heading-like element.
    """

    name = getattr(el, "name", None)

    if not name:
        return ""

    name = name.lower()

    if name in _WRAPPER_TAGS:

        strong = el.find(["strong", "b"])

        if strong is not None:
            return clean_text(
                strong.get_text(" ", strip=True)
            )

    return clean_text(
        el.get_text(" ", strip=True)
    )


def _is_heading_like(el) -> bool:
    """
    True if `el` looks like a section heading.

    Accepts:
        - h1-h6
        - a <p>/<div>/<li> whose *only* content is a short
          <strong>/<b> (MyJobMag's most common pattern)
        - a bare short <strong>/<b>
    """

    name = getattr(el, "name", None)

    if not name:
        return False

    name = name.lower()

    # --------------------------------------------------------
    # Real heading tags
    # --------------------------------------------------------

    if name in _HEADING_TAGS:

        text = clean_text(
            el.get_text(" ", strip=True)
        )

        return 0 < len(text) < 150

    # --------------------------------------------------------
    # Wrapper whose only content is a bold heading
    # --------------------------------------------------------

    if name in _WRAPPER_TAGS:

        strong = el.find(["strong", "b"])

        if strong is None:
            return False

        wrapper_text = clean_text(
            el.get_text(" ", strip=True)
        )

        strong_text = clean_text(
            strong.get_text(" ", strip=True)
        )

        if not strong_text:
            return False

        if len(strong_text) >= 150:
            return False

        # The wrapper must contain *only* the bold text.
        if wrapper_text != strong_text:
            return False

        return True

    # --------------------------------------------------------
    # Bare bold text acting as a heading
    # --------------------------------------------------------

    if name in _BOLD_TAGS:

        text = clean_text(
            el.get_text(" ", strip=True)
        )

        return 0 < len(text) < 150

    return False


def _heading_matches_keywords(
    heading_text: str,
    keywords: List[str],
) -> bool:
    """
    True if the heading text contains one of the keywords.
    """

    heading_text = heading_text.lower().strip(": -")

    if not heading_text:
        return False

    if len(heading_text) > 150:
        return False

    return any(
        keyword in heading_text
        for keyword in keywords
    )


def extract_section_by_heading(
    soup: BeautifulSoup,
    keywords: List[str],
) -> str:
    """
    Extract content belonging to a section heading.

    The heading is identified by keyword, and the section ends
    at the next heading-like element (of any kind). This makes
    the extractor resilient to headings the module does not
    explicitly know about (e.g. "How to Apply").
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
            "strong",
            "b",
        ]
    )

    target = None

    for el in candidates:

        if not _is_heading_like(el):
            continue

        text = _heading_text(el)

        if _heading_matches_keywords(
            text,
            keywords,
        ):
            target = el
            break

    if target is None:
        return ""

    collected = []

    for sibling in target.next_siblings:

        # Stop at the next heading of any kind.
        if (
            getattr(sibling, "name", None)
            and _is_heading_like(sibling)
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

    return clean_text(
        " ".join(collected)
    )


def find_main_content_container(
    soup: BeautifulSoup,
):
    """
    Find the most likely MyJobMag job-content container.

    We deliberately prefer semantic containers instead of body.
    """

    selectors = [
        "main",
        "article",
        "[role='main']",
        ".job-details",
        ".job-description",
        ".job-detail",
        ".details",
        ".job-content",
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

            if len(text) >= 300:
                candidates.append(
                    (
                        len(text),
                        element,
                    )
                )

    if candidates:

        # Choose the smallest meaningful container.
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

    JSON-LD description is used as a fallback, not as the
    primary source for the individual sections.
    """

    content = {
        "description": "",
        "responsibilities": "",
        "requirements": "",
    }

    # --------------------------------------------------------
    # Individual sections
    # --------------------------------------------------------

    for key, keywords in SECTION_KEYWORDS.items():

        content[key] = extract_section_by_heading(
            soup,
            keywords,
        )

    # --------------------------------------------------------
    # JSON-LD fallback
    # --------------------------------------------------------

    if not content["description"] and json_ld:

        description = clean_text(
            json_ld.get(
                "description"
            )
        )

        if description:
            content["description"] = (
                description
            )

    # --------------------------------------------------------
    # If there is no separate description section,
    # use the meaningful job content container.
    # --------------------------------------------------------

    if not content["description"]:

        container = (
            find_main_content_container(
                soup
            )
        )

        if container:

            text = clean_text(
                container.get_text(
                    " ",
                    strip=True,
                )
            )

            # Avoid returning the whole page if the container
            # is clearly enormous.
            if 100 <= len(text) <= 15000:
                content["description"] = text

    return content


# ============================================================
# SKILL EXTRACTION
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
    ("GCP", r"\bgoogle cloud\b|\bgcp\b"),
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
    Detect known technical skills from the actual job
    description/content.

    Returns skills in a stable order.
    """

    text = clean_text(
        text
    )

    if not text:
        return []

    skills = []

    for skill, pattern in SKILL_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            skills.append(
                skill
            )

    return skills


# ============================================================
# APPLICATION INFORMATION
# ============================================================

def is_myjobmag_apply_url(
    url: str,
) -> bool:

    if not url:
        return False

    return (
        "myjobmag.co.ke/apply-now/"
        in url.lower()
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

    return (
        "myjobmag.co.ke"
        not in hostname
    )


def detect_application(
    soup: BeautifulSoup,
    page_url: str,
) -> Dict:
    """
    Detect the application method without submitting anything.

    MyJobMag commonly exposes an /apply-now/ intermediary page.
    External employer URLs are also collected where visible.
    """

    application_url = ""
    external_urls = []
    application_links = []

    for anchor in soup.select(
        "a[href]"
    ):

        href = anchor.get(
            "href"
        )

        if not href:
            continue

        href = normalize_url(
            href
        )

        text = clean_text(
            anchor.get_text(
                " ",
                strip=True,
            )
        )

        lower_text = text.lower()
        lower_href = href.lower()

        # ----------------------------------------------------
        # MyJobMag application URL
        # ----------------------------------------------------

        if is_myjobmag_apply_url(
            href
        ):

            if not application_url:
                application_url = href

            application_links.append(
                {
                    "text": text,
                    "url": href,
                }
            )

            continue

        # ----------------------------------------------------
        # Explicit application language
        # ----------------------------------------------------

        application_words = [
            "apply",
            "application",
            "apply now",
            "go to",
            "interested and qualified",
            "method of application",
        ]

        looks_like_application = (
            any(
                word in lower_text
                for word in application_words
            )
            or "apply" in lower_href
            or "careers" in lower_href
            or "taleo" in lower_href
            or "workday" in lower_href
            or "greenhouse" in lower_href
        )

        if (
            looks_like_application
            and is_external_application_url(
                href
            )
        ):

            if href not in external_urls:
                external_urls.append(
                    href
                )

                application_links.append(
                    {
                        "text": text,
                        "url": href,
                    }
                )

    # --------------------------------------------------------
    # Determine primary application URL
    # --------------------------------------------------------

    if application_url:

        method = "myjobmag"

    elif external_urls:

        application_url = external_urls[0]

        method = "external"

    else:

        method = "unknown"

    return {
        "method": method,
        "url": application_url,
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
    Navigate to a URL and wait for the page to settle.
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
        # Some pages never reach networkidle because of
        # analytics or advertising requests.
        pass

    return response


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(
    context,
    url: str,
    fallback_title: str = "",
) -> Dict:
    """
    Inspect a MyJobMag job page and return structured data.
    """

    page = context.new_page()

    try:

        print()
        print(
            "=" * 60
        )
        print(
            "INSPECTING MYJOBMAG JOB"
        )
        print(
            "=" * 60
        )
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
            print(
                f"Status: {response.status}"
            )

        try:
            print(
                f"Page title: {page.title()}"
            )
        except Exception:
            pass

        # ----------------------------------------------------
        # Obtain HTML
        # ----------------------------------------------------

        html = get_page_html(
            page
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        # ----------------------------------------------------
        # JSON-LD
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title = extract_title(
            soup,
            json_ld,
            fallback_title,
        )

        # ----------------------------------------------------
        # Company
        # ----------------------------------------------------

        company = extract_company(
            soup,
            json_ld,
            title,
        )

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location = extract_location(
            soup,
            json_ld,
        )

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Job content
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Skills
        # ----------------------------------------------------

        skill_text = " ".join(
            [
                description,
                responsibilities,
                requirements,
            ]
        )

        skills = extract_skills(
            skill_text
        )

        # ----------------------------------------------------
        # Application
        # ----------------------------------------------------

        application = detect_application(
            soup,
            url,
        )

        # ----------------------------------------------------
        # Build result
        # ----------------------------------------------------

        job = {
            "title": title,
            "company": company,
            "location": location,
            "job_type": job_type,
            "qualification": qualification,
            "experience": experience,
            "job_field": extract_labeled_value(
                soup,
                [
                    "job field",
                    "field",
                    "job category",
                ],
            ),
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

        # ----------------------------------------------------
        # Print result
        # ----------------------------------------------------

        print()
        print(
            "=" * 60
        )
        print(
            "EXTRACTED JOB"
        )
        print(
            "=" * 60
        )

        print(
            f"Title: {job['title']}"
        )
        print(
            f"Company: {job['company'] or 'Not found'}"
        )
        print(
            f"Location: {job['location'] or 'Not specified'}"
        )
        print(
            f"Job type: {job['job_type'] or 'Not specified'}"
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

        # ----------------------------------------------------
        # Application output
        # ----------------------------------------------------

        print()
        print(
            "APPLICATION"
        )
        print(
            "-" * 60
        )

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

        # ----------------------------------------------------
        # Application-related links
        # ----------------------------------------------------

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
                    link.get(
                        "text"
                    )
                    or "Application link"
                )

                print(
                    f"• {text}"
                )
                print(
                    f"  {link.get('url', '')}"
                )

        print()
        print(
            "=" * 60
        )
        print(
            "INSPECTION COMPLETE"
        )
        print(
            "=" * 60
        )

        return job

    finally:

        try:
            page.close()
        except Exception:
            pass


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

    try:

        # ----------------------------------------------------
        # Launch browser
        # ----------------------------------------------------

        playwright, browser, context = (
            launch_browser(
                headless=HEADLESS
            )
        )

        # ----------------------------------------------------
        # Open MyJobMag listing
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
            print(
                f"Status: {response.status}"
            )

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

        page.close()

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
        print(
            "=" * 60
        )
        print(
            "TESTING FIRST JOB"
        )
        print(
            "=" * 60
        )

        inspect_job(
            context,
            jobs[0]["url"],
            jobs[0]["title"],
        )

    except Exception as error:

        print()
        print(
            "=" * 60
        )
        print(
            "ERROR"
        )
        print(
            "=" * 60
        )

        print(
            str(error)
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


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()