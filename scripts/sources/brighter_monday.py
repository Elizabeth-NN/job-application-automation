
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.brightermonday.co.ke"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


# ============================================================
# TECHNOLOGY KEYWORDS
# ============================================================

# Strong technology keywords.
#
# These are deliberately more specific than generic words such
# as "system", "data", "digital", or "software".
#
# The matcher will make the final decision about how well the
# job matches the user's profile.

STRONG_TECHNOLOGY_KEYWORDS = {
    # Software development
    "software developer",
    "software engineer",
    "software development",
    "software engineering",
    "web developer",
    "webmaster",
    "frontend developer",
    "front-end developer",
    "backend developer",
    "back-end developer",
    "full stack developer",
    "fullstack developer",
    "mobile developer",
    "application developer",
    "application engineer",
    "programmer",
    "programming",

    # Python / backend
    "python developer",
    "python engineer",
    "flask",
    "django",
    "fastapi",
    "rest api",
    "restful api",
    "api development",
    "api developer",
    "backend",

    # JavaScript / frontend
    "javascript developer",
    "typescript",
    "react developer",
    "react.js",
    "next.js",
    "node.js",
    "nodejs",
    "vue.js",
    "angular developer",

    # Databases
    "database developer",
    "database administrator",
    "database engineer",
    "postgresql",
    "mysql",
    "mongodb",
    "sql developer",

    # Other programming languages
    "java developer",
    "c# developer",
    ".net developer",
    "php developer",
    "ruby developer",
    "go developer",
    "golang developer",

    # DevOps / cloud
    "devops engineer",
    "devops developer",
    "cloud engineer",
    "cloud developer",
    "site reliability engineer",

    # Data / AI
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "machine learning developer",
    "artificial intelligence engineer",
    "ai engineer",

    # Security / infrastructure
    "cybersecurity",
    "cyber security",
    "security engineer",
    "network engineer",
    "network administrator",
    "systems engineer",
    "systems developer",

    # Mobile
    "android developer",
    "ios developer",
    "flutter developer",
    "mobile application developer",
}


# Generic technology terms.
#
# These are NOT enough on their own to classify a job as
# technology-related. They need supporting technical context.
GENERIC_TECHNOLOGY_KEYWORDS = {
    "developer",
    "development",
    "programmer",
    "programming",
    "software",
    "api",
    "database",
    "sql",
    "python",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "nodejs",
    "java",
    "c#",
    ".net",
    "php",
    "go",
    "golang",
    "flutter",
    "devops",
    "cloud",
    "cybersecurity",
    "cyber security",
    "machine learning",
    "artificial intelligence",
    "data engineer",
    "data scientist",
}


# Words that frequently appear in non-technical jobs even though
# they may mention technology, systems, software, data, etc.
NON_TECHNOLOGY_TITLE_KEYWORDS = {
    "accountant",
    "accounting",
    "sales",
    "sales representative",
    "sales agent",
    "business development officer",
    "business development",
    "marketing",
    "social media",
    "graphic designer",
    "administrator",
    "administration",
    "hr",
    "human resource",
    "human resources",
    "finance assistant",
    "finance officer",
    "credit analyst",
    "relationship officer",
    "collection officer",
    "field collection",
    "waiter",
    "waitress",
    "project assistant",
    "program officer",
    "policy and advocacy",
    "real estate",
    "procurement",
    "customer service",
    "customer care",
    "operations officer",
    "office assistant",
    "receptionist",
}


# ============================================================
# HTTP / HTML HELPERS
# ============================================================

def get_page(url):
    """
    Download a public webpage and return BeautifulSoup.
    """

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def clean_text(text):
    """
    Normalize whitespace and remove unnecessary spacing.
    """

    if not text:
        return ""

    return " ".join(
        text.split()
    ).strip()


def normalize_text(text):
    """
    Return lowercase normalized text.
    """

    return clean_text(text).lower()


# ============================================================
# TECHNOLOGY FILTERING
# ============================================================

def contains_keyword(text, keyword):
    """
    Check whether a keyword occurs as a meaningful phrase.

    Short / special keywords are handled using word boundaries
    where appropriate to reduce accidental matches.
    """

    text = normalize_text(text)
    keyword = normalize_text(keyword)

    if not keyword:
        return False

    # Multi-word phrases can safely be searched directly.
    if " " in keyword:
        return keyword in text

    # Escape special regex characters such as . in .net.
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"

    return bool(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
    )


def title_is_clearly_non_technology(title):
    """
    Determine whether the title clearly represents a non-tech role.

    This prevents descriptions containing words such as
    'software', 'system', 'database', or 'digital' from causing
    unrelated jobs to enter the technology pipeline.
    """

    normalized_title = normalize_text(title)

    for keyword in NON_TECHNOLOGY_TITLE_KEYWORDS:

        if contains_keyword(
            normalized_title,
            keyword,
        ):
            return True

    return False


def is_strong_technology_title(title):
    """
    Determine whether the title itself strongly identifies
    a technology role.
    """

    if not title:
        return False

    if title_is_clearly_non_technology(title):
        return False

    normalized_title = normalize_text(title)

    for keyword in STRONG_TECHNOLOGY_KEYWORDS:

        if contains_keyword(
            normalized_title,
            keyword,
        ):
            return True

    return False


def is_technology_job(title, description=""):
    """
    Determine whether a listing is likely technology-related.

    Strategy:

    1. Reject clearly non-technology titles.
    2. Accept strong technology titles immediately.
    3. For generic titles, inspect the description.
    4. Require multiple technical signals in the description
       rather than relying on one generic word.
    """

    if not title:
        return False

    # --------------------------------------------------------
    # Step 1: Reject obvious non-tech titles.
    # --------------------------------------------------------

    if title_is_clearly_non_technology(title):
        return False

    # --------------------------------------------------------
    # Step 2: Strong technology title.
    # --------------------------------------------------------

    if is_strong_technology_title(title):
        return True

    # --------------------------------------------------------
    # Step 3: Description analysis for generic titles.
    # --------------------------------------------------------

    if not description:
        return False

    normalized_description = normalize_text(
        description
    )

    matched_keywords = []

    for keyword in GENERIC_TECHNOLOGY_KEYWORDS:

        if contains_keyword(
            normalized_description,
            keyword,
        ):
            matched_keywords.append(
                keyword
            )

    # No technical signals.
    if not matched_keywords:
        return False

    # --------------------------------------------------------
    # Step 4: Require stronger evidence for generic titles.
    # --------------------------------------------------------
    #
    # A single occurrence of "software", "system", "data",
    # "digital", etc. is not enough.
    #
    # Examples:
    #
    # Accountant + "accounting software"
    # Sales + "CRM system"
    # Administrator + "information systems"
    #
    # These should not become technology jobs.

    technical_development_terms = {
        "developer",
        "development",
        "programmer",
        "programming",
        "api",
        "python",
        "javascript",
        "typescript",
        "react",
        "node.js",
        "nodejs",
        "java",
        "c#",
        ".net",
        "php",
        "go",
        "golang",
        "flask",
        "django",
        "fastapi",
        "postgresql",
        "mysql",
        "mongodb",
        "database developer",
        "database engineer",
        "frontend",
        "backend",
        "full stack",
        "fullstack",
        "software engineering",
        "software developer",
        "software engineer",
        "web developer",
        "mobile developer",
        "android developer",
        "ios developer",
        "flutter",
        "devops",
        "cloud engineer",
        "cloud developer",
        "cybersecurity",
        "machine learning",
        "data engineer",
        "data scientist",
    }

    strong_description_matches = []

    for keyword in technical_development_terms:

        if contains_keyword(
            normalized_description,
            keyword,
        ):
            strong_description_matches.append(
                keyword
            )

    # At least one strong technical development signal
    # is required for a generic-title listing.
    if strong_description_matches:
        return True

    return False


# ============================================================
# ARTICLE EXTRACTION
# ============================================================

def extract_job_article(soup):
    """
    Return the main BrighterMonday job article.

    BrighterMonday commonly places job information inside:

        <article class="job__details">

    Multiple fallbacks are included in case the markup changes.
    """

    if not soup:
        return None

    # Primary selector.
    article = soup.find(
        "article",
        class_="job__details",
    )

    if article:
        return article

    # Other possible class names.
    selectors = [
        "article.job-details",
        "article.job__detail",
        ".job__details",
        ".job-details",
        "[class*='job__details']",
        "[class*='job-details']",
    ]

    for selector in selectors:

        article = soup.select_one(
            selector
        )

        if article:
            return article

    # Generic article fallback.
    article = soup.find(
        "article"
    )

    if article:
        return article

    return None


def extract_text_lines(article):
    """
    Return cleaned non-empty text lines from an article.
    """

    if not article:
        return []

    lines = []

    raw_lines = article.get_text(
        "\n",
        strip=True,
    ).splitlines()

    for line in raw_lines:

        cleaned = clean_text(
            line
        )

        if cleaned:
            lines.append(
                cleaned
            )

    return lines


# ============================================================
# METADATA EXTRACTION
# ============================================================

def extract_value_between_labels(
    text,
    start_label,
    end_labels,
):
    """
    Extract text appearing between two metadata labels.

    Example:

        Min Qualification: Diploma
        Experience Level: Mid level

    returns:

        Diploma
    """

    if not text:
        return ""

    end_pattern = "|".join(
        re.escape(label)
        for label in end_labels
    )

    pattern = (
        rf"{re.escape(start_label)}"
        rf"\s*:?\s*"
        rf"(.*?)"
        rf"(?=\s+(?:{end_pattern})\s*:|\Z)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE,
    )

    if not match:
        return ""

    return clean_text(
        match.group(1)
    )


def extract_metadata(article):
    """
    Extract structured metadata from a BrighterMonday
    job article.

    Returns:

        qualification
        experience
        experience_length
        location
        job_type
        posted
        deadline
    """

    metadata = {
        "qualification": "",
        "experience": "",
        "experience_length": "",
        "location": "",
        "job_type": "",
        "posted": "",
        "deadline": "",
    }

    if not article:
        return metadata

    text = clean_text(
        article.get_text(
            " ",
            strip=True,
        )
    )

    # --------------------------------------------------------
    # Qualification
    # --------------------------------------------------------

    metadata["qualification"] = (
        extract_value_between_labels(
            text,
            "Min Qualification",
            [
                "Experience Level",
                "Experience Length",
                "Language Requirement",
                "Working Hours",
                "Applicant Location",
                "Job descriptions",
            ],
        )
    )

    # --------------------------------------------------------
    # Experience level
    # --------------------------------------------------------

    metadata["experience"] = (
        extract_value_between_labels(
            text,
            "Experience Level",
            [
                "Experience Length",
                "Language Requirement",
                "Working Hours",
                "Applicant Location",
                "Job descriptions",
            ],
        )
    )

    # --------------------------------------------------------
    # Experience length
    # --------------------------------------------------------

    metadata["experience_length"] = (
        extract_value_between_labels(
            text,
            "Experience Length",
            [
                "Language Requirement",
                "Working Hours",
                "Applicant Location",
                "Job descriptions",
                "How to Apply",
            ],
        )
    )

    # --------------------------------------------------------
    # Working hours / job type
    # --------------------------------------------------------

    metadata["job_type"] = (
        extract_value_between_labels(
            text,
            "Working Hours",
            [
                "Applicant Location",
                "Job descriptions",
                "How to Apply",
            ],
        )
    )

    # --------------------------------------------------------
    # Applicant location
    # --------------------------------------------------------

    metadata["location"] = (
        extract_value_between_labels(
            text,
            "Applicant Location",
            [
                "Job descriptions",
                "How to Apply",
                "Application Deadline",
                "Deadline",
                "Closing Date",
            ],
        )
    )

    # --------------------------------------------------------
    # Posted date
    # --------------------------------------------------------

    posted_patterns = [
        r"\b\d+\s+(?:day|days|hour|hours|minute|minutes)\s+ago\b",
        r"\btoday\b",
        r"\byesterday\b",
    ]

    for pattern in posted_patterns:

        posted_match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if posted_match:

            metadata["posted"] = clean_text(
                posted_match.group(0)
            )

            break

    # --------------------------------------------------------
    # Application deadline
    # --------------------------------------------------------

    deadline_patterns = [
        (
            r"Application Deadline\s*:?\s*(.*?)"
            r"(?=\s+(?:How to Apply|Share This Job|"
            r"Similar Jobs|Related Jobs)|$)"
        ),
        (
            r"Deadline\s*:?\s*(.*?)"
            r"(?=\s+(?:How to Apply|Share This Job|"
            r"Similar Jobs|Related Jobs)|$)"
        ),
        (
            r"Closing Date\s*:?\s*(.*?)"
            r"(?=\s+(?:How to Apply|Share This Job|"
            r"Similar Jobs|Related Jobs)|$)"
        ),
    ]

    for pattern in deadline_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            deadline = clean_text(
                match.group(1)
            )

            if deadline:

                metadata["deadline"] = (
                    deadline
                )

                break

    return metadata


# ============================================================
# TITLE / COMPANY
# ============================================================

def extract_title(soup):
    """
    Extract the job title from the page.
    """

    if not soup:
        return ""

    heading = soup.find(
        "h1"
    )

    if not heading:
        # Fallback to page title.
        page_title = soup.find(
            "title"
        )

        if page_title:
            title = clean_text(
                page_title.get_text(
                    " ",
                    strip=True,
                )
            )

            # Remove common site suffix.
            title = re.sub(
                r"\s*\|\s*BrighterMonday.*$",
                "",
                title,
                flags=re.IGNORECASE,
            )

            return title.strip()

        return ""

    return clean_text(
        heading.get_text(
            " ",
            strip=True,
        )
    )


def extract_company(article):
    """
    Extract company name from the job article.

    Several strategies are attempted before falling back
    to nearby text.
    """

    if not article:
        return ""

    # --------------------------------------------------------
    # Strategy 1: Known company-related selectors
    # --------------------------------------------------------

    company_selectors = [
        ".job__company",
        ".company-name",
        ".company",
        ".job-company",
        "[class*='company']",
    ]

    for selector in company_selectors:

        element = article.select_one(
            selector
        )

        if not element:
            continue

        company = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if (
            company
            and len(company) <= 150
        ):
            return company

    # --------------------------------------------------------
    # Strategy 2: Look for explicit company labels.
    # --------------------------------------------------------

    lines = extract_text_lines(
        article
    )

    company_labels = {
        "company",
        "employer",
        "company name",
    }

    for index, line in enumerate(lines):

        normalized = normalize_text(
            line
        )

        if normalized in company_labels:

            if index + 1 < len(lines):

                company = clean_text(
                    lines[index + 1]
                )

                if (
                    company
                    and len(company) <= 150
                ):
                    return company

    # --------------------------------------------------------
    # Strategy 3: Look at lines after title.
    # --------------------------------------------------------

    heading = article.find(
        "h1"
    )

    title = ""

    if heading:

        title = clean_text(
            heading.get_text(
                " ",
                strip=True,
            )
        )

    if title in lines:

        title_index = lines.index(
            title
        )

        ignored_values = {
            "sales",
            "real estate",
            "software & data",
            "engineering & technology",
            "technology",
            "nairobi",
            "mombasa",
            "kisumu",
            "nakuru",
            "eldoret",
            "kenya",
            "full time",
            "full-time",
            "part time",
            "part-time",
            "contract",
            "internship",
            "temporary",
            "easy apply",
            "featured",
            "new",
        }

        for line in lines[
            title_index + 1:
            title_index + 8
        ]:

            lower = normalize_text(
                line
            )

            if lower in ignored_values:
                continue

            if "ago" in lower:
                continue

            if "share" in lower:
                continue

            if (
                "qualification" in lower
                or "experience level" in lower
                or "experience length" in lower
            ):
                continue

            if len(line) <= 100:

                return line

    return ""


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(article):
    """
    Extract the actual job description and requirements.

    Starts after:

        Job descriptions & requirements

    and stops at common unrelated sections.
    """

    if not article:
        return ""

    lines = extract_text_lines(
        article
    )

    start_index = None

    # --------------------------------------------------------
    # Locate description heading.
    # --------------------------------------------------------

    exact_headings = {
        "job descriptions & requirements",
        "job description & requirements",
        "job description and requirements",
        "job description",
        "job descriptions",
    }

    for index, line in enumerate(lines):

        normalized = normalize_text(
            line
        )

        if normalized in exact_headings:

            start_index = index + 1

            break

    # --------------------------------------------------------
    # Fallback: partial heading match.
    # --------------------------------------------------------

    if start_index is None:

        for index, line in enumerate(lines):

            normalized = normalize_text(
                line
            )

            if (
                "job description" in normalized
                and "requirement" in normalized
            ):

                start_index = index + 1

                break

    if start_index is None:
        return ""

    # --------------------------------------------------------
    # Extract until unrelated section.
    # --------------------------------------------------------

    description_lines = []

    stop_headings = {
        "how to apply",
        "application deadline",
        "share this job",
        "similar jobs",
        "related jobs",
        "report this job",
        "important safety tips",
        "log in and apply",
    }

    for line in lines[start_index:]:

        normalized = normalize_text(
            line
        )

        if normalized in stop_headings:
            break

        if normalized.startswith(
            "application deadline"
        ):
            break

        if normalized.startswith(
            "how to apply"
        ):
            break

        description_lines.append(
            line
        )

    return "\n".join(
        description_lines
    ).strip()


# ============================================================
# JOB DETAILS
# ============================================================

def get_job_details(job_url):
    """
    Extract structured information from a BrighterMonday
    job page.
    """

    soup = get_page(
        job_url
    )

    article = extract_job_article(
        soup
    )

    title = extract_title(
        soup
    )

    metadata = extract_metadata(
        article
    )

    company = extract_company(
        article
    )

    description = extract_description(
        article
    )

    return {
        "title": title,
        "company": company,
        "location": metadata["location"],
        "job_type": metadata["job_type"],
        "qualification": metadata["qualification"],
        "experience": metadata["experience"],
        "experience_length": metadata[
            "experience_length"
        ],
        "posted": metadata["posted"],
        "deadline": metadata["deadline"],
        "description": description,
        "url": job_url,
        "source": "BrighterMonday",
    }


# ============================================================
# COLLECTION
# ============================================================

def collect_jobs(listing_url):
    """
    Collect technology-related job listings from BrighterMonday.

    The listing page may contain many non-technology jobs.

    Candidate listings are therefore handled in two stages:

        1. Strong technology titles are accepted immediately.
        2. Generic titles are inspected individually.

    Only jobs that appear technology-related are returned.
    """

    soup = get_page(
        listing_url
    )

    candidate_jobs = []
    seen_urls = set()

    # --------------------------------------------------------
    # Find candidate job links.
    # --------------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True,
    ):

        href = link.get(
            "href",
            "",
        )

        if "/listings/" not in href:
            continue

        job_url = urljoin(
            BASE_URL,
            href,
        )

        # Remove fragments.
        job_url = job_url.split(
            "#"
        )[0]

        if job_url in seen_urls:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if not title:
            continue

        seen_urls.add(
            job_url
        )

        candidate_jobs.append({
            "title": title,
            "url": job_url,
        })

    print(
        f"   Found {len(candidate_jobs)} candidate listings"
    )

    # --------------------------------------------------------
    # Inspect candidate listings.
    # --------------------------------------------------------

    technology_jobs = []
    filtered_count = 0

    for index, candidate in enumerate(
        candidate_jobs,
        start=1,
    ):

        title = candidate["title"]
        url = candidate["url"]

        print(
            f"   → Inspecting {index}/"
            f"{len(candidate_jobs)}: {title}"
        )

        # ----------------------------------------------------
        # Obvious non-technology title.
        # ----------------------------------------------------

        if title_is_clearly_non_technology(
            title
        ):

            filtered_count += 1

            print(
                "      ↳ Filtered out: "
                "non-technology job"
            )

            continue

        # ----------------------------------------------------
        # Strong technology title.
        #
        # No extra request is necessary.
        # ----------------------------------------------------

        if is_strong_technology_title(
            title
        ):

            print(
                "      ↳ Technology-related title"
            )

            technology_jobs.append(
                candidate
            )

            continue

        # ----------------------------------------------------
        # Generic title.
        #
        # Inspect the actual job page.
        # ----------------------------------------------------

        try:

            details = get_job_details(
                url
            )

            description = details.get(
                "description",
                "",
            )

            if is_technology_job(
                title,
                description,
            ):

                print(
                    "      ↳ Technology-related "
                    "job description"
                )

                # Keep details so run_job_search.py
                # does not download the page again.
                candidate["details"] = (
                    details
                )

                technology_jobs.append(
                    candidate
                )

            else:

                filtered_count += 1

                print(
                    "      ↳ Filtered out: "
                    "non-technology job"
                )

        except requests.RequestException as error:

            print(
                f"      ↳ Could not inspect page: "
                f"{error}"
            )

        except Exception as error:

            print(
                f"      ↳ Error inspecting page: "
                f"{error}"
            )

    print(
        f"   Filtered out {filtered_count} "
        f"non-technology jobs"
    )

    print(
        f"   Found {len(technology_jobs)} "
        f"technology jobs"
    )

    return technology_jobs


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    listing_url = (
    f"{BASE_URL}/jobs/software-data"
    )

    print("=" * 60)
    print("BRIGHTERMONDAY COLLECTION TEST")
    print("=" * 60)
    print()

    print(
        "Collecting BrighterMonday jobs..."
    )

    jobs = collect_jobs(
        listing_url
    )

    print()

    print(
        f"Final technology jobs: {len(jobs)}"
    )

    print()

    if jobs:

        first_job = jobs[0]

        print(
            "Testing first technology job:"
        )

        print(
            f"Title: {first_job['title']}"
        )

        print(
            f"URL: {first_job['url']}"
        )

        print()

        # Reuse details if collect_jobs()
        # already fetched them.
        details = first_job.get(
            "details"
        )

        if not details:

            details = get_job_details(
                first_job["url"]
            )

        print("=" * 60)
        print("JOB DETAILS")
        print("=" * 60)

        print(
            f"Title: {details['title']}"
        )

        print(
            f"Company: {details['company']}"
        )

        print(
            f"Location: {details['location']}"
        )

        print(
            f"Job Type: {details['job_type']}"
        )

        print(
            f"Qualification: {details['qualification']}"
        )

        print(
            f"Experience: {details['experience']}"
        )

        print(
            f"Experience Length: "
            f"{details['experience_length']}"
        )

        print(
            f"Posted: {details['posted']}"
        )

        print(
            f"Deadline: {details['deadline']}"
        )

        print(
            f"Description length: "
            f"{len(details['description'])}"
        )

        print()

        print(
            "DESCRIPTION PREVIEW"
        )

        print(
            "==================="
        )

        print(
            details["description"][:1000]
        )

    else:

        print(
            "No technology jobs found."
        )

