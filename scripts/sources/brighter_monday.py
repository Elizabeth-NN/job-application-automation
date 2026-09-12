"""
BrighterMonday job source.

Collects technology-related jobs from BrighterMonday using
multiple category/search URLs, removes duplicates, fetches
full job details, and filters unrelated jobs.

Compatible with:
    scripts.job_collector

Exports:
    collect_jobs()
    get_job_details()
    get_page()
"""

from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.brightermonday.co.ke"

SEARCH_URLS = [
    f"{BASE_URL}/jobs",
    f"{BASE_URL}/jobs/software-data",
    f"{BASE_URL}/jobs/software-data/nairobi",
    f"{BASE_URL}/jobs/software-data/full-time",
    f"{BASE_URL}/jobs/software-data/nairobi/full-time",
    f"{BASE_URL}/jobs/software-data/remote",
    f"{BASE_URL}/jobs/software-data/remote/full-time",
]

MAX_PAGES = 5

REQUEST_TIMEOUT = 20

MAX_RETRIES = 3

RETRY_DELAYS = [2, 4, 8]

REQUEST_DELAY = 0.5

DETAIL_DELAY = 0.3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 "
        "Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


# ============================================================
# TITLE FILTERS
# ============================================================

TECH_TITLE_PATTERNS = [
    # Software development
    r"\bsoftware\s+developer\b",
    r"\bsoftware\s+engineer\b",
    r"\bsoftware\s+development\b",
    r"\bweb\s+developer\b",
    r"\bwebsite\s+developer\b",
    r"\bwebmaster\b",

    # Backend / frontend / full stack
    r"\bbackend\s+developer\b",
    r"\bback[-\s]?end\s+developer\b",
    r"\bfrontend\s+developer\b",
    r"\bfront[-\s]?end\s+developer\b",
    r"\bfull[-\s]?stack\s+developer\b",
    r"\bfullstack\s+developer\b",

    # Languages
    r"\bpython\s+developer\b",
    r"\breact\s+developer\b",
    r"\bjavascript\s+developer\b",
    r"\bphp\s+developer\b",
    r"\bjava\s+developer\b",
    r"\bnode(?:\.js)?\s+developer\b",
    r"\bruby\s+developer\b",
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

    # DevOps / cloud
    r"\bdevops\s+engineer\b",
    r"\bdevops\b",
    r"\bcloud\s+engineer\b",
    r"\bcloud\s+developer\b",

    # QA / testing
    r"\bqa\s+engineer\b",
    r"\bquality\s+assurance\s+engineer\b",
    r"\bsoftware\s+tester\b",
    r"\bsoftware\s+testing\b",
    r"\btest\s+engineer\b",
    r"\btest\s+analyst\b",

    # Automation
    r"\bautomation\s+engineer\b",
    r"\brpa\s+developer\b",

    # Enterprise technology
    r"\bservicenow\s+developer\b",
    r"\bservice\s+now\s+developer\b",
    r"\bdynamics\s+365\b",
    r"\bpower\s+platform\b",
    r"\berp\s+developer\b",
    r"\bfineract\s+developer\b",

    # Technical development
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
    r"\bsales\s+engineer\b",
    r"\bsales\s+consultant\b",
    r"\bsales\s+agent\b",
    r"\bfield\s+sales\b",
    r"\btechnical\s+sales\b",
    r"\bsales\s+and\s+marketing\b",

    # Business development
    r"\bbusiness\s+development\b",

    # Finance/accounting
    r"\baccountant\b",
    r"\baccounting\b",
    r"\bfinance\s+assistant\b",
    r"\bfinance\s+officer\b",
    r"\bfinancial\s+analyst\b",
    r"\bcredit\s+analyst\b",
    r"\bdebt\s+recovery\b",

    # HR/admin
    r"\bhuman\s+resources\b",
    r"\bhr\s+officer\b",
    r"\bhr\s+manager\b",
    r"\bhr\s*&\s*administration\b",
    r"\bhuman\s+resource\s+manager\b",
    r"\badministrator\b",
    r"\boffice\s+admin\b",
    r"\boffice\s+administrator\b",
    r"\breceptionist\b",

    # Marketing/design/content
    r"\bmarketing\b",
    r"\bdigital\s+marketer\b",
    r"\bgraphic\s+designer\b",
    r"\bcontent\s+lead\b",
    r"\bcommunications?\s+officer\b",

    # Operations
    r"\boperations\s+manager\b",
    r"\boperations\s+officer\b",
    r"\boperations\s+executive\b",

    # Customer-facing
    r"\brelationship\s+officer\b",
    r"\brelationship\s+manager\b",
    r"\bcustomer\s+service\b",

    # Other unrelated occupations
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
    r"\bdomain\s+expert\b",
    r"\bllm\s+trainer\b",
    r"\bpersonalization\s+officer\b",
    r"\btechnical\s+operator\b",

    # IT management / support
    r"\bict\s+manager\b",
    r"\bit\s+manager\b",
    r"\binformation\s+systems\s+security\s+manager\b",
    r"\bit\s+maintenance\b",
    r"\bmaintenance\s+assistant\b",
    r"\btechnical\s+support\b",
    r"\bit\s+support\b",
    r"\bhelp\s*desk\b",
    r"\bsupport\s+officer\b",
]


# ============================================================
# DESCRIPTION TECHNOLOGY SIGNALS
# ============================================================

TECHNOLOGY_KEYWORD_GROUPS = [
    # Programming languages
    [
        "python",
        "javascript",
        "typescript",
        "java",
        "php",
        "c#",
        "c++",
        "ruby",
        "golang",
        "go programming",
    ],

    # Frameworks
    [
        "flask",
        "django",
        "react",
        "next.js",
        "node.js",
        "express.js",
        "laravel",
        "spring boot",
        "fastapi",
    ],

    # Development
    [
        "software development",
        "web development",
        "application development",
        "backend development",
        "frontend development",
        "api development",
        "rest api",
        "restful api",
        "programming",
        "coding",
        "develop applications",
        "develop software",
        "develop websites",
    ],

    # Databases
    [
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "sqlite",
        "database design",
        "database development",
        "database management",
    ],

    # Tools / infrastructure
    [
        "git",
        "github",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "ci/cd",
        "devops",
    ],
]


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value: Optional[str]) -> str:
    """Normalize whitespace."""

    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url: str) -> str:
    """Return a normalized absolute URL."""

    if not url:
        return ""

    url = url.strip()

    if url.startswith("/"):
        url = urljoin(BASE_URL, url)

    parsed = urlparse(url)

    if not parsed.scheme:
        return ""

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            parsed.query,
            "",
        )
    )


def normalize_title(title: str) -> str:
    """Normalize title for matching."""

    return clean_text(title).lower()


def page_url(base_url: str, page: int) -> str:
    """Build pagination URL."""

    if page <= 1:
        return base_url

    parsed = urlparse(base_url)

    query = parse_qs(
        parsed.query,
        keep_blank_values=True,
    )

    query["page"] = [str(page)]

    new_query = urlencode(
        query,
        doseq=True,
    )

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def clean_value(value: str) -> str:
    """
    Clean common placeholder values returned by BrighterMonday.
    """

    value = clean_text(value)

    if not value:
        return ""

    value = re.sub(
        r"\s*\|\s*BrighterMonday.*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"\s*-\s*BrighterMonday.*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    return clean_text(value)


# ============================================================
# HTTP
# ============================================================

def get_page(
    url: str,
    retries: int = MAX_RETRIES,
) -> Optional[BeautifulSoup]:
    """
    Download a page and return BeautifulSoup.

    404 is treated as the end of pagination.
    Temporary failures are retried.
    """

    for attempt in range(1, retries + 1):

        try:
            response = SESSION.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 404:
                print(
                    f"      ↳ Page does not exist (404): {url}"
                )
                return None

            response.raise_for_status()

            return BeautifulSoup(
                response.text,
                "html.parser",
            )

        except requests.exceptions.HTTPError as error:

            status_code = getattr(
                error.response,
                "status_code",
                None,
            )

            if status_code == 404:
                print(
                    f"      ↳ Page does not exist (404): {url}"
                )
                return None

            if attempt >= retries:
                print(
                    f"      ↳ Request failed: {error}"
                )
                return None

            delay = RETRY_DELAYS[
                min(
                    attempt - 1,
                    len(RETRY_DELAYS) - 1,
                )
            ]

            print(
                f"      ↳ Request attempt "
                f"{attempt}/{retries} failed; "
                f"retrying in {delay}s..."
            )

            time.sleep(delay)

        except requests.exceptions.RequestException as error:

            if attempt >= retries:
                print(
                    f"      ↳ Request failed: {error}"
                )
                return None

            delay = RETRY_DELAYS[
                min(
                    attempt - 1,
                    len(RETRY_DELAYS) - 1,
                )
            ]

            print(
                f"      ↳ Request attempt "
                f"{attempt}/{retries} failed; "
                f"retrying in {delay}s..."
            )

            time.sleep(delay)

    return None


# ============================================================
# JOB URL DETECTION
# ============================================================

def is_job_url(url: str) -> bool:
    """Determine whether URL looks like a BrighterMonday job."""

    if not url:
        return False

    parsed = urlparse(url)

    if parsed.netloc:
        hostname = parsed.netloc.lower()

        if hostname not in {
            "brightermonday.co.ke",
            "www.brightermonday.co.ke",
        }:
            return False

    return "/listings/" in parsed.path.lower()


# ============================================================
# LISTING EXTRACTION
# ============================================================

def extract_listing_url(card) -> str:
    """Extract job URL from a listing card."""

    for link in card.select("a[href]"):

        href = normalize_url(
            link.get("href", "")
        )

        if is_job_url(href):
            return href

    return ""


def extract_listing_title(card) -> str:
    """Extract title from a listing card."""

    selectors = [
        "h2",
        "h3",
        "h4",
        "[class*='title']",
        "a[href]",
    ]

    ignored_titles = {
        "view job",
        "apply now",
        "see more",
        "read more",
    }

    for selector in selectors:

        for element in card.select(selector):

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if len(text) < 3:
                continue

            if text.lower() in ignored_titles:
                continue

            return text

    return ""


def find_listing_cards(
    soup: BeautifulSoup,
) -> List:
    """Find probable job cards."""

    selectors = [
        "div.job-card",
        "article.job-card",
        "div[class*='job-card']",
        "article[class*='job']",
        "div[class*='listing']",
        "article",
    ]

    cards = []

    seen_urls = set()

    for selector in selectors:

        for card in soup.select(selector):

            url = extract_listing_url(card)

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            cards.append(card)

    return cards


def extract_listings_from_page(
    soup: BeautifulSoup,
) -> List[Dict[str, str]]:
    """Extract basic listings."""

    listings = []

    seen_urls = set()

    cards = find_listing_cards(soup)

    for card in cards:

        url = extract_listing_url(card)

        if not url:
            continue

        if url in seen_urls:
            continue

        title = extract_listing_title(card)

        if not title:
            continue

        seen_urls.add(url)

        listings.append(
            {
                "title": title,
                "url": url,
            }
        )

    # Fallback if card detection fails.
    if not listings:

        for link in soup.select("a[href]"):

            url = normalize_url(
                link.get("href", "")
            )

            if not is_job_url(url):
                continue

            title = clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            if len(title) < 3:
                continue

            if title.lower() in {
                "view job",
                "apply now",
                "see more",
                "read more",
            }:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            listings.append(
                {
                    "title": title,
                    "url": url,
                }
            )

    return listings


# ============================================================
# SEARCH COLLECTION
# ============================================================

def collect_search_results(
    search_url: str,
) -> List[Dict[str, str]]:
    """Collect listings from one search URL."""

    listings = []

    seen_urls = set()

    for page in range(1, MAX_PAGES + 1):

        url = page_url(
            search_url,
            page,
        )

        soup = get_page(url)

        if soup is None:
            break

        page_listings = extract_listings_from_page(
            soup
        )

        if not page_listings:
            break

        new_count = 0

        for listing in page_listings:

            job_url = listing.get(
                "url",
                "",
            )

            if not job_url:
                continue

            if job_url in seen_urls:
                continue

            seen_urls.add(job_url)

            listings.append(listing)

            new_count += 1

        if new_count == 0:
            break

        time.sleep(REQUEST_DELAY)

    return listings


# ============================================================
# TECHNOLOGY FILTER
# ============================================================

def title_is_excluded(title: str) -> bool:
    """Return True if title clearly belongs to an excluded category."""

    normalized = normalize_title(title)

    if not normalized:
        return True

    for pattern in EXCLUDED_TITLE_PATTERNS:

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def title_matches_technology(title: str) -> bool:
    """
    Return True when the title clearly indicates a
    technology-related position.
    """

    normalized = normalize_title(title)

    if not normalized:
        return False

    if title_is_excluded(normalized):
        return False

    for pattern in TECH_TITLE_PATTERNS:

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def description_matches_technology(
    title: str,
    description: str,
) -> bool:
    """
    Conservative description-based technology detection.

    An ambiguous title must have at least two independent
    technical keyword groups.
    """

    if title_is_excluded(title):
        return False

    description = clean_text(
        description
    ).lower()

    if not description:
        return False

    matched_groups = 0

    for group in TECHNOLOGY_KEYWORD_GROUPS:

        if any(
            keyword in description
            for keyword in group
        ):
            matched_groups += 1

    return matched_groups >= 2


def is_technology_job(
    title: str,
    description: str = "",
) -> bool:
    """Determine whether job is technology-related."""

    if title_is_excluded(title):
        return False

    if title_matches_technology(title):
        return True

    return description_matches_technology(
        title,
        description,
    )


# ============================================================
# JSON-LD HELPERS
# ============================================================

def get_json_ld_objects(
    soup: BeautifulSoup,
) -> List[dict]:
    """
    Extract JSON-LD objects from the page.

    Handles dictionaries, lists and @graph structures.
    """

    objects = []

    for script in soup.select(
        "script[type='application/ld+json']"
    ):

        raw = script.string or script.get_text()

        if not raw:
            continue

        raw = raw.strip()

        if not raw:
            continue

        try:
            data = json.loads(raw)

        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, list):

            for item in data:

                if isinstance(item, dict):
                    objects.append(item)

        elif isinstance(data, dict):

            objects.append(data)

            graph = data.get("@graph")

            if isinstance(graph, list):

                for item in graph:

                    if isinstance(item, dict):
                        objects.append(item)

    return objects


def get_job_posting_json_ld(
    soup: BeautifulSoup,
) -> List[dict]:
    """Return only JSON-LD JobPosting objects."""

    job_postings = []

    for data in get_json_ld_objects(soup):

        schema_type = data.get("@type")

        if isinstance(schema_type, list):

            if "JobPosting" in schema_type:
                job_postings.append(data)

        elif schema_type == "JobPosting":

            job_postings.append(data)

    return job_postings


# ============================================================
# LABEL EXTRACTION
# ============================================================

def extract_text_by_label(
    soup: BeautifulSoup,
    labels: List[str],
) -> str:
    """
    Extract a value associated with a label.

    Supports:
        - definition lists
        - tables
        - nearby elements
        - text/sibling structures
    """

    expected_labels = [
        clean_text(label).lower()
        for label in labels
    ]

    # --------------------------------------------------------
    # Strategy 1: definition lists
    # --------------------------------------------------------

    for dt in soup.select("dt"):

        label = clean_text(
            dt.get_text(
                " ",
                strip=True,
            )
        ).lower()

        if not label:
            continue

        if any(
            expected == label
            or expected in label
            for expected in expected_labels
        ):

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
    # Strategy 2: tables
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
        ).lower()

        value = clean_text(
            cells[1].get_text(
                " ",
                strip=True,
            )
        )

        if any(
            expected == label
            or expected in label
            for expected in expected_labels
        ):

            if value:
                return value

    # --------------------------------------------------------
    # Strategy 3: exact text label + sibling
    # --------------------------------------------------------

    for element in soup.find_all(string=True):

        text = clean_text(str(element))

        if not text:
            continue

        lower_text = text.lower()

        if lower_text not in expected_labels:
            continue

        parent = element.parent

        if not parent:
            continue

        sibling = parent.find_next_sibling()

        if sibling:

            value = clean_text(
                sibling.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                value
                and value.lower()
                not in expected_labels
            ):
                return value

    return ""


# ============================================================
# COMPANY EXTRACTION
# ============================================================

def extract_company(
    soup: BeautifulSoup,
) -> str:
    """
    Extract employer/company name.

    The order is important:

    1. JobPosting JSON-LD
    2. Explicit company selectors
    3. Company/employer labels
    4. Job-page heading structure
    5. Meta tags
    6. Safe fallback

    Never return generic values such as "Employers".
    """

    invalid_values = {
        "",
        "brightermonday",
        "brighter monday",
        "anonymous employer",
        "unknown company",
        "unknown employer",
        "employer",
        "employers",
        "company",
        "companies",
        "email address",
        "notify me",
        "sign in",
        "login",
        "confidential",
    }

    def valid_company(value: str) -> bool:
        value = clean_value(value)

        if not value:
            return False

        lower = value.lower()

        if lower in invalid_values:
            return False

        blocked_phrases = [
            "brightermonday",
            "email address",
            "notify me",
            "read our",
            "protection of your data",
            "sign in",
            "log in",
            "job alert",
            "search jobs",
            "filter results",
        ]

        if any(
            phrase in lower
            for phrase in blocked_phrases
        ):
            return False

        if len(value) > 150:
            return False

        if len(value.split()) > 15:
            return False

        return True

    # --------------------------------------------------------
    # Strategy 1: JobPosting JSON-LD
    # --------------------------------------------------------

    for data in get_job_posting_json_ld(soup):

        organization = data.get(
            "hiringOrganization"
        )

        if isinstance(organization, dict):

            company = organization.get(
                "name",
                "",
            )

            if valid_company(company):
                return clean_value(company)

        elif isinstance(organization, str):

            if valid_company(organization):
                return clean_value(organization)

    # --------------------------------------------------------
    # Strategy 2: Explicit company selectors
    # --------------------------------------------------------

    selectors = [
        "[data-testid*='company']",
        "[data-testid*='employer']",
        "[class*='company-name']",
        "[class*='company_name']",
        "[class*='companyName']",
        "[class*='employer-name']",
        "[class*='employer_name']",
        "[class*='employerName']",
    ]

    for selector in selectors:

        for element in soup.select(selector):

            value = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if valid_company(value):
                return clean_value(value)

    # --------------------------------------------------------
    # Strategy 3: Look for company/employer labels.
    # --------------------------------------------------------

    company = extract_text_by_label(
        soup,
        [
            "company",
            "employer",
            "organisation",
            "organization",
        ],
    )

    if valid_company(company):
        return clean_value(company)

    # --------------------------------------------------------
    # Strategy 4: Job page heading structure.
    #
    # Current BrighterMonday pages place the employer
    # immediately around the main job heading.
    # --------------------------------------------------------

    title_element = soup.find("h1")

    if title_element:

        # Look at the next few siblings/elements.
        candidates = []

        for element in title_element.find_all_next(
            limit=10
        ):

            if element.name not in {
                "h2",
                "h3",
                "a",
                "span",
                "div",
            }:
                continue

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            if text.lower() == normalize_title(
                extract_title(soup)
            ):
                continue

            candidates.append(text)

        for candidate in candidates:

            if valid_company(candidate):

                # Avoid accidentally selecting category names.
                lower = candidate.lower()

                if lower in {
                    "software & data",
                    "software and data",
                    "full time",
                    "part time",
                    "internship & graduate",
                    "nairobi",
                    "kenya",
                    "confidential",
                }:
                    continue

                return clean_value(candidate)

    # --------------------------------------------------------
    # Strategy 5: Meta tags
    # --------------------------------------------------------

    meta_selectors = [
        "meta[name='author']",
        "meta[name='company']",
        "meta[name='employer']",
        "meta[property='article:author']",
    ]

    for selector in meta_selectors:

        element = soup.select_one(selector)

        if not element:
            continue

        value = clean_text(
            element.get(
                "content",
                "",
            )
        )

        if valid_company(value):
            return clean_value(value)

    # --------------------------------------------------------
    # Strategy 6: Page text patterns
    # --------------------------------------------------------

    page_text = soup.get_text(
        "\n",
        strip=True,
    )

    patterns = [
        r"(?:company|employer)\s*:\s*([^\n|]+)",
        r"(?:company|employer)\s*\n\s*([^\n|]+)",
    ]

    for pattern in patterns:

        matches = re.finditer(
            pattern,
            page_text,
            flags=re.IGNORECASE,
        )

        for match in matches:

            value = clean_text(
                match.group(1)
            )

            if valid_company(value):
                return clean_value(value)

    return "Unknown Company"


# ============================================================
# TITLE
# ============================================================

def extract_title(
    soup: BeautifulSoup,
) -> str:
    """Extract full job title."""

    selectors = [
        "h1",
        "[data-testid*='job-title']",
        "[class*='job-title']",
        "[class*='job_title']",
        "meta[property='og:title']",
    ]

    for selector in selectors:

        element = soup.select_one(selector)

        if not element:
            continue

        if element.name == "meta":

            value = clean_text(
                element.get(
                    "content",
                    "",
                )
            )

        else:

            value = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

        if not value:
            continue

        value = clean_value(value)

        return value

    return ""


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(
    soup: BeautifulSoup,
) -> str:
    """Extract the main job description."""

    # First preference: JSON-LD JobPosting.
    for data in get_job_posting_json_ld(soup):

        description = data.get(
            "description",
            "",
        )

        if isinstance(description, str):

            description = BeautifulSoup(
                description,
                "html.parser",
            ).get_text(
                " ",
                strip=True,
            )

            description = clean_text(description)

            if len(description) >= 100:
                return description

    selectors = [
        "[data-testid*='description']",
        "[class*='job-description']",
        "[class*='job_description']",
    ]

    candidates = []

    for selector in selectors:

        for element in soup.select(selector):

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if len(text) >= 200:
                candidates.append(text)

    if candidates:
        return max(
            candidates,
            key=len,
        )

    # Article is a reasonable fallback, but avoid grabbing
    # the entire page unless absolutely necessary.
    article = soup.find("article")

    if article:

        text = clean_text(
            article.get_text(
                " ",
                strip=True,
            )
        )

        if len(text) >= 200:
            return text

    return ""


# ============================================================
# LOCATION
# ============================================================

def extract_location(
    soup: BeautifulSoup,
) -> str:
    """Extract job location."""

    # JSON-LD is the cleanest source.
    for data in get_job_posting_json_ld(soup):

        location_data = data.get(
            "jobLocation"
        )

        if isinstance(location_data, list):

            for item in location_data:

                if not isinstance(item, dict):
                    continue

                address = item.get(
                    "address"
                )

                if isinstance(address, dict):

                    parts = [
                        address.get(
                            "addressLocality",
                            "",
                        ),
                        address.get(
                            "addressRegion",
                            "",
                        ),
                        address.get(
                            "addressCountry",
                            "",
                        ),
                    ]

                    parts = [
                        clean_text(part)
                        for part in parts
                        if clean_text(part)
                    ]

                    if parts:
                        return ", ".join(parts)

        elif isinstance(location_data, dict):

            address = location_data.get(
                "address"
            )

            if isinstance(address, dict):

                parts = [
                    address.get(
                        "addressLocality",
                        "",
                    ),
                    address.get(
                        "addressRegion",
                        "",
                    ),
                    address.get(
                        "addressCountry",
                        "",
                    ),
                ]

                parts = [
                    clean_text(part)
                    for part in parts
                    if clean_text(part)
                ]

                if parts:
                    return ", ".join(parts)

    location = extract_text_by_label(
        soup,
        [
            "location",
            "job location",
            "where",
        ],
    )

    if location:
        return clean_value(location)

    # Look for common BrighterMonday location text.
    text = soup.get_text(
        " ",
        strip=True,
    )

    patterns = [
        r"\b(Nairobi|Mombasa|Kisumu|Nakuru|Thika|Eldoret|Kenya)\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(1)
            )

    return ""


# ============================================================
# JOB TYPE
# ============================================================

def extract_job_type(
    soup: BeautifulSoup,
) -> str:
    """Extract employment type."""

    for data in get_job_posting_json_ld(soup):

        value = data.get(
            "employmentType"
        )

        if isinstance(value, list):

            return ", ".join(
                clean_text(item)
                for item in value
                if clean_text(item)
            )

        if isinstance(value, str) and value.strip():

            return clean_text(value)

    return extract_text_by_label(
        soup,
        [
            "job type",
            "employment type",
            "employment",
            "type",
        ],
    )


# ============================================================
# QUALIFICATION
# ============================================================

def extract_qualification(
    soup: BeautifulSoup,
) -> str:
    """Extract qualification."""

    return extract_text_by_label(
        soup,
        [
            "qualification",
            "qualifications",
            "education",
            "minimum qualification",
            "min qualification",
        ],
    )


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience(
    soup: BeautifulSoup,
) -> str:
    """Extract experience level."""

    return extract_text_by_label(
        soup,
        [
            "experience level",
            "experience",
        ],
    )


def extract_experience_length(
    soup: BeautifulSoup,
) -> str:
    """Extract required experience length."""

    for data in get_job_posting_json_ld(soup):

        value = data.get(
            "experienceRequirements"
        )

        if isinstance(value, dict):

            text = value.get(
                "monthsOfExperience"
            )

            if text:
                return str(text)

        if isinstance(value, str):

            value = clean_text(value)

            if value:
                return value

    return extract_text_by_label(
        soup,
        [
            "experience length",
            "years of experience",
            "years experience",
            "experience required",
        ],
    )


# ============================================================
# POSTED DATE
# ============================================================

def extract_posted(
    soup: BeautifulSoup,
) -> str:
    """Extract posted date."""

    for data in get_job_posting_json_ld(soup):

        value = data.get(
            "datePosted"
        )

        if isinstance(value, str):

            return clean_text(value)

    return extract_text_by_label(
        soup,
        [
            "posted",
            "date posted",
            "date",
        ],
    )


# ============================================================
# DEADLINE
# ============================================================

def extract_deadline(
    soup: BeautifulSoup,
) -> str:
    """Extract application deadline."""

    for data in get_job_posting_json_ld(soup):

        value = data.get(
            "validThrough"
        )

        if isinstance(value, str):

            return clean_text(value)

    return extract_text_by_label(
        soup,
        [
            "deadline",
            "application deadline",
            "closing date",
        ],
    )


# ============================================================
# GET JOB DETAILS
# ============================================================

def get_job_details(
    url: str,
) -> Dict[str, str]:
    """
    Fetch and parse a complete BrighterMonday job.

    Returns a dictionary compatible with the existing
    job matcher and tracker.
    """

    url = normalize_url(url)

    if not url:
        raise ValueError(
            "Invalid BrighterMonday job URL."
        )

    soup = get_page(url)

    if soup is None:

        raise RuntimeError(
            f"Could not fetch job page: {url}"
        )

    title = extract_title(soup)

    company = extract_company(soup)

    location = extract_location(soup)

    job_type = extract_job_type(soup)

    qualification = extract_qualification(soup)

    experience = extract_experience(soup)

    experience_length = extract_experience_length(
        soup
    )

    posted = extract_posted(soup)

    deadline = extract_deadline(soup)

    description = extract_description(soup)

    time.sleep(DETAIL_DELAY)

    return {
        "title": title,
        "company": company,
        "location": location,
        "job_type": job_type,
        "qualification": qualification,
        "experience": experience,
        "experience_length": experience_length,
        "years_required": experience_length,
        "posted": posted,
        "deadline": deadline,
        "description": description,
        "url": url,
        "source": "BrighterMonday",
    }


# ============================================================
# COLLECT JOBS
# ============================================================

def collect_jobs(
    listing_url: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Collect BrighterMonday technology jobs.

    listing_url is retained for compatibility with the
    existing job_collector.py.
    """

    print(
        "Collecting BrighterMonday jobs..."
    )

    search_urls = list(SEARCH_URLS)

    # Add custom listing URL if supplied.
    if listing_url:

        listing_url = normalize_url(
            listing_url
        )

        if (
            listing_url
            and listing_url not in search_urls
        ):

            search_urls.insert(
                0,
                listing_url,
            )

    # --------------------------------------------------------
    # Collect candidate listings.
    # --------------------------------------------------------

    all_listings = []

    seen_urls = set()

    print(
        f"   Running {len(search_urls)} "
        f"BrighterMonday category searches"
    )

    for index, search_url in enumerate(
        search_urls,
        start=1,
    ):

        print(
            f"   → Search {index}/{len(search_urls)}: "
            f"{search_url}"
        )

        try:

            listings = collect_search_results(
                search_url
            )

        except Exception as error:

            print(
                f"      ↳ Search failed: {error}"
            )

            continue

        new_count = 0

        for listing in listings:

            url = listing.get(
                "url",
                "",
            )

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            all_listings.append(listing)

            new_count += 1

        print(
            f"      ↳ Found {len(listings)} listings, "
            f"{new_count} new"
        )

    print()

    print(
        f"   Found {len(all_listings)} "
        f"unique candidate listings"
    )

    # --------------------------------------------------------
    # Filter and inspect jobs.
    # --------------------------------------------------------

    technology_jobs = []

    filtered_count = 0

    for index, listing in enumerate(
        all_listings,
        start=1,
    ):

        title = listing.get(
            "title",
            "Unknown title",
        )

        url = listing.get(
            "url",
            "",
        )

        print(
            f"   → Inspecting "
            f"{index}/{len(all_listings)}: "
            f"{title}"
        )

        # ----------------------------------------------------
        # Explicitly excluded title.
        # ----------------------------------------------------

        if title_is_excluded(title):

            print(
                "      ↳ Filtered out: "
                "excluded job category"
            )

            filtered_count += 1

            continue

        # ----------------------------------------------------
        # Strong technology title.
        # ----------------------------------------------------

        if title_matches_technology(title):

            print(
                "      ↳ Technology-related title"
            )

            try:

                details = get_job_details(
                    url
                )

            except Exception as error:

                print(
                    f"      ↳ Failed to fetch details: "
                    f"{error}"
                )

                filtered_count += 1

                continue

            technology_jobs.append(
                details
            )

            continue

        # ----------------------------------------------------
        # Ambiguous title.
        # ----------------------------------------------------

        try:

            details = get_job_details(
                url
            )

        except Exception as error:

            print(
                f"      ↳ Could not inspect job: "
                f"{error}"
            )

            filtered_count += 1

            continue

        description = details.get(
            "description",
            "",
        )

        if description_matches_technology(
            title,
            description,
        ):

            print(
                "      ↳ Technology-related "
                "job description"
            )

            technology_jobs.append(
                details
            )

        else:

            print(
                "      ↳ Filtered out: "
                "non-technology job"
            )

            filtered_count += 1

    print()

    print(
        f"   Filtered out "
        f"{filtered_count} "
        f"non-technology jobs"
    )

    print(
        f"   Found "
        f"{len(technology_jobs)} "
        f"technology jobs"
    )

    return technology_jobs


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("BRIGHTERMONDAY COLLECTION TEST")
    print("=" * 60)
    print()

    jobs = collect_jobs()

    print()

    print("=" * 60)
    print(
        f"FINAL TECHNOLOGY JOBS: {len(jobs)}"
    )
    print("=" * 60)

    print()

    if not jobs:

        print(
            "No technology jobs found."
        )

    else:

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            print(
                f"{index}. "
                f"{job.get('title', '')}"
            )

            print(
                f"   Company: "
                f"{job.get('company', '')}"
            )

            print(
                f"   Location: "
                f"{job.get('location', '')}"
            )

            print(
                f"   Job Type: "
                f"{job.get('job_type', '')}"
            )

            print(
                f"   Qualification: "
                f"{job.get('qualification', '')}"
            )

            print(
                f"   Experience: "
                f"{job.get('experience', '')}"
            )

            print(
                f"   Experience Length: "
                f"{job.get('experience_length', '')}"
            )

            print(
                f"   Posted: "
                f"{job.get('posted', '')}"
            )

            print(
                f"   Deadline: "
                f"{job.get('deadline', '')}"
            )

            print(
                f"   URL: "
                f"{job.get('url', '')}"
            )

            print()