"""
MyJobMag browser automation.

Reusable Playwright functions for:

    1. Opening MyJobMag
    2. Collecting job links
    3. Inspecting individual job pages
    4. Extracting structured job information
    5. Detecting application methods
    6. Extracting application emails and subjects
    7. Extracting responsibilities, requirements, skills, etc.

This module does NOT:
    - launch Chromium automatically when imported
    - close Chromium automatically when imported
    - submit applications
"""

import json
import re
from urllib.parse import urljoin


# ============================================================
# SETTINGS
# ============================================================

MYJOBMAG_BASE_URL = "https://www.myjobmag.co.ke"

MYJOBMAG_URL = (
    f"{MYJOBMAG_BASE_URL}/"
    "jobs-by-title/developer-python"
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value):
    """Normalize whitespace in a string."""

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def normalize_url(url):
    """Convert a relative URL into an absolute MyJobMag URL."""

    if not url:
        return ""

    return urljoin(
        MYJOBMAG_BASE_URL,
        str(url).strip()
    )


def get_page_text(page):
    """Safely return visible body text."""

    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def safe_inner_text(locator):
    """Safely extract inner text from a Playwright locator."""

    try:
        if locator.count() == 0:
            return ""

        return clean_text(locator.first.inner_text())

    except Exception:
        return ""


def first_non_empty(*values):
    """Return the first non-empty value."""

    for value in values:
        value = clean_text(value)

        if value:
            return value

    return None


# ============================================================
# JSON-LD
# ============================================================

def extract_json_ld_job(page):
    """
    Extract JobPosting information from JSON-LD.

    Returns:
        dict | None
    """

    try:
        scripts = page.locator(
            'script[type="application/ld+json"]'
        ).all()

        for script in scripts:

            try:
                raw = script.inner_text()

                if not raw:
                    continue

                data = json.loads(raw)

            except Exception:
                continue

            candidates = []

            if isinstance(data, dict):
                candidates.append(data)

                graph = data.get("@graph")

                if isinstance(graph, list):
                    candidates.extend(graph)

            elif isinstance(data, list):
                candidates.extend(data)

            for item in candidates:

                if not isinstance(item, dict):
                    continue

                item_type = item.get("@type")

                if item_type == "JobPosting":
                    return item

                if isinstance(item_type, list):
                    if "JobPosting" in item_type:
                        return item

    except Exception:
        pass

    return None


# ============================================================
# EMAIL EXTRACTION
# ============================================================

def extract_emails(text):
    """
    Extract employer email addresses.

    MyJobMag's own email addresses are ignored.
    """

    if not text:
        return []

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    results = []

    for email in emails:

        email = email.strip()

        if email.lower().endswith(
            "@myjobmag.co.ke"
        ):
            continue

        if email not in results:
            results.append(email)

    return results


def extract_email(text):
    """Return the first non-MyJobMag email address."""

    emails = extract_emails(text)

    if emails:
        return emails[0]

    return None


# ============================================================
# APPLICATION SUBJECT
# ============================================================

def extract_application_subject(
    text,
    job_title=None
):
    """
    Extract the expected email application subject.

    Supports wording such as:

        Subject: Backend Developer
        Email subject should be Backend Developer
        Use the position as subject
        Use the job title as subject
    """

    if not text:
        return None

    normalized = clean_text(text)

    subject_patterns = [

        r"subject(?:\s+line)?\s*(?:is|should be|:|-)\s*[\"“']?(.+?)[\"”']?(?:\.|$)",

        r"subject\s+of\s+(?:the\s+)?email\s*(?:is|should be|:|-)?\s*[\"“']?(.+?)[\"”']?(?:\.|$)",

        r"email\s+subject\s*(?:is|should be|:|-)\s*[\"“']?(.+?)[\"”']?(?:\.|$)",
    ]

    for pattern in subject_patterns:

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if match:

            subject = clean_text(
                match.group(1)
            )

            if subject:
                return subject

    lower_text = normalized.lower()

    position_subject_patterns = (
        "using the position as subject",
        "use the position as subject",
        "position as the subject",
        "position as subject",
        "using the job title as subject",
        "use the job title as subject",
        "job title as the subject",
        "job title as subject",
    )

    if any(
        phrase in lower_text
        for phrase in position_subject_patterns
    ):

        if job_title:
            return clean_text(job_title)

    return None


# ============================================================
# APPLICATION LINKS
# ============================================================

APPLICATION_KEYWORDS = (
    "apply",
    "application",
    "career",
    "workday",
    "greenhouse",
    "lever",
    "ashby",
    "smartrecruiters",
    "icims",
    "bamboohr",
    "jobvite",
    "successfactors",
    "oraclecloud",
    "recruitee",
    "teamtailor",
    "job-application",
)


def extract_application_links(page):
    """
    Extract links that may be related to applying.

    Returns:

        [
            {
                "text": "...",
                "url": "..."
            }
        ]
    """

    links = []
    seen_urls = set()

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

            href = normalize_url(href)

            combined = (
                f"{text} {href}"
            ).lower()

            if not any(
                keyword in combined
                for keyword in APPLICATION_KEYWORDS
            ):
                continue

            if href in seen_urls:
                continue

            seen_urls.add(href)

            links.append(
                {
                    "text": text,
                    "url": href,
                }
            )

    except Exception as error:

        print(
            f"Application-link extraction error: {error}"
        )

    return links


# ============================================================
# EXTERNAL APPLICATION DETECTION
# ============================================================

def is_external_application_url(url):
    """
    Determine whether a URL appears to point directly
    to an employer or ATS application system.
    """

    if not url:
        return False

    lower_url = url.lower()

    if "myjobmag.co.ke" in lower_url:
        return False

    external_domains = (
        "workday",
        "greenhouse",
        "lever.co",
        "ashby",
        "smartrecruiters",
        "icims",
        "bamboohr",
        "jobvite",
        "successfactors",
        "oraclecloud",
        "recruitee",
        "teamtailor",
    )

    return any(
        domain in lower_url
        for domain in external_domains
    )


# ============================================================
# APPLICATION METHOD
# ============================================================

def extract_application_method(
    page,
    text,
    job_title=None
):
    """
    Determine how the candidate is expected to apply.

    Priority:

        1. Direct external ATS/application link
        2. Employer email
        3. MyJobMag application page
        4. Unknown
    """

    text = text or ""

    links = extract_application_links(page)

    # --------------------------------------------------------
    # 1. External application
    # --------------------------------------------------------

    for link in links:

        url = link.get(
            "url",
            ""
        )

        if is_external_application_url(url):

            return {
                "method": "external",
                "email": None,
                "subject": None,
                "url": url,
            }

    # --------------------------------------------------------
    # 2. Employer email
    # --------------------------------------------------------

    email = extract_email(text)

    if email:

        subject = extract_application_subject(
            text,
            job_title=job_title
        )

        return {
            "method": "email",
            "email": email,
            "subject": subject,
            "url": None,
        }

    # --------------------------------------------------------
    # 3. MyJobMag application page
    # --------------------------------------------------------

    for link in links:

        url = link.get(
            "url",
            ""
        )

        lower_url = url.lower()

        if (
            "myjobmag.co.ke/apply-now/"
            in lower_url
            or
            "myjobmag.co.ke/job-application/"
            in lower_url
        ):

            return {
                "method": "myjobmag",
                "email": None,
                "subject": None,
                "url": url,
            }

    # --------------------------------------------------------
    # 4. Unknown
    # --------------------------------------------------------

    return {
        "method": "unknown",
        "email": None,
        "subject": None,
        "url": None,
    }


# ============================================================
# JOB LINK COLLECTION
# ============================================================

def collect_job_links(page):
    """
    Collect actual MyJobMag job pages from a listing page.

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

            href = normalize_url(href)

            # Only actual job pages.
            if "/job/" not in href:
                continue

            # Exclude non-job pages containing /job/
            # in query strings or unrelated URLs.
            if not href.startswith(
                f"{MYJOBMAG_BASE_URL}/job/"
            ):
                continue

            if href in seen_urls:
                continue

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
            f"Job-link collection error: {error}"
        )

    return jobs


# ============================================================
# META INFORMATION EXTRACTION
# ============================================================

def extract_labeled_value(
    text,
    label,
    stop_labels=None
):
    """
    Extract a value following a label.

    Example:

        Location Nairobi Job Field ICT

    can return:

        Nairobi
    """

    if not text:
        return None

    stop_labels = stop_labels or []

    escaped_label = re.escape(label)

    if stop_labels:

        escaped_stops = "|".join(
            re.escape(item)
            for item in stop_labels
        )

        pattern = (
            rf"{escaped_label}\s*[:\-]?\s*"
            rf"(.*?)"
            rf"(?=\s+(?:{escaped_stops})\b|$)"
        )

    else:

        pattern = (
            rf"{escaped_label}\s*[:\-]?\s*"
            rf"(.*?)(?=\s+[A-Z][A-Za-z ]+\s*[:\-]|$)"
        )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = clean_text(
        match.group(1)
    )

    return value or None


# ============================================================
# LOCATION EXTRACTION
# ============================================================

def extract_location(
    page,
    text,
    json_ld=None
):
    """
    Extract job location.

    Priority:

        1. JSON-LD
        2. Structured page elements
        3. MyJobMag metadata text
    """

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    if json_ld:

        location = json_ld.get(
            "jobLocation"
        )

        if isinstance(location, dict):

            address = location.get(
                "address"
            )

            if isinstance(address, dict):

                value = first_non_empty(
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("addressCountry"),
                )

                if value:
                    return value

            elif isinstance(address, str):

                value = clean_text(address)

                if value:
                    return value

        elif isinstance(location, list):

            values = []

            for item in location:

                if not isinstance(item, dict):
                    continue

                address = item.get("address")

                if isinstance(address, dict):

                    value = first_non_empty(
                        address.get("addressLocality"),
                        address.get("addressRegion"),
                        address.get("addressCountry"),
                    )

                    if value and value not in values:
                        values.append(value)

            if values:
                return ", ".join(values)

    # --------------------------------------------------------
    # Structured HTML
    # --------------------------------------------------------

    selectors = (
        '[class*="location"]',
        '[class*="Location"]',
        '[itemprop="jobLocation"]',
        '[itemprop="addressLocality"]',
    )

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            ).all()

            for element in elements:

                value = safe_inner_text(element)

                if not value:
                    continue

                lower_value = value.lower()

                # Ignore navigation/footer junk.
                if lower_value in (
                    "jobs by location",
                    "location",
                    "remote jobs",
                ):
                    continue

                if len(value) > 150:
                    continue

                return value

        except Exception:
            continue

    # --------------------------------------------------------
    # Text-based extraction
    # --------------------------------------------------------

    normalized = clean_text(text)

    match = re.search(
        r"\bLocation\s*[:\-]?\s*"
        r"([A-Za-z][A-Za-z0-9 ,./&()\-]{1,80}?)"
        r"(?=\s+(?:Job Field|Experience|Qualification|"
        r"Job Type|Salary|Posted|Deadline)\b|$)",
        normalized,
        re.IGNORECASE
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value:
            return value

    return None


# ============================================================
# JOB TYPE EXTRACTION
# ============================================================

def extract_job_type(
    page,
    text,
    json_ld=None
):
    """Extract employment/job type."""

    if json_ld:

        value = json_ld.get(
            "employmentType"
        )

        if isinstance(value, list):
            value = ", ".join(
                clean_text(item)
                for item in value
                if clean_text(item)
            )

        value = clean_text(value)

        if value:
            return value

    normalized = clean_text(text)

    match = re.search(
        r"\bJob Type\s*[:\-]?\s*"
        r"(.*?)(?=\s+Qualification\b|"
        r"\s+Experience\b|"
        r"\s+Location\b|$)",
        normalized,
        re.IGNORECASE
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value:
            return value

    return None


# ============================================================
# QUALIFICATION EXTRACTION
# ============================================================

def extract_qualification(
    page,
    text,
    json_ld=None
):
    """Extract minimum qualification."""

    if json_ld:

        value = first_non_empty(
            json_ld.get("educationRequirements"),
            json_ld.get("qualifications"),
        )

        if value:
            return value

    normalized = clean_text(text)

    match = re.search(
        r"\bQualification\s*[:\-]?\s*"
        r"(.*?)(?=\s+Experience\b|"
        r"\s+Location\b|"
        r"\s+Job Field\b|$)",
        normalized,
        re.IGNORECASE
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value:
            return value

    return None


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience(
    page,
    text,
    json_ld=None
):
    """Extract required experience."""

    if json_ld:

        value = first_non_empty(
            json_ld.get("experienceRequirements"),
        )

        if value:
            return value

    normalized = clean_text(text)

    match = re.search(
        r"\bExperience\s*[:\-]?\s*"
        r"(.*?)(?=\s+Location\b|"
        r"\s+Job Field\b|"
        r"\s+Job Purpose\b|"
        r"\s+Responsibilities\b|$)",
        normalized,
        re.IGNORECASE
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value:
            return value

    return None


# ============================================================
# JOB FIELD
# ============================================================

def extract_job_field(
    page,
    text
):
    """Extract MyJobMag job field."""

    normalized = clean_text(text)

    match = re.search(
        r"\bJob Field\s*[:\-]?\s*"
        r"(.*?)(?=\s+Job Purpose\b|"
        r"\s+Responsibilities\b|"
        r"\s+Requirements\b|"
        r"\s+Qualifications\b|$)",
        normalized,
        re.IGNORECASE
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value:
            return value

    return None


# ============================================================
# POSTED DATE
# ============================================================

def extract_posted(
    text,
    json_ld=None
):
    """Extract job posting date."""

    if json_ld:

        value = first_non_empty(
            json_ld.get("datePosted")
        )

        if value:
            return value

    normalized = clean_text(text)

    match = re.search(
        r"\bPosted\s*[:\-]?\s*"
        r"([A-Za-z]{3,12}\s+\d{1,2},\s+\d{4})",
        normalized,
        re.IGNORECASE
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
    text,
    json_ld=None
):
    """Extract application deadline."""

    if json_ld:

        value = first_non_empty(
            json_ld.get("validThrough")
        )

        if value:
            return value

    normalized = clean_text(text)

    patterns = (
        r"\bDeadline\s*[:\-]?\s*"
        r"([A-Za-z]{3,12}\s+\d{1,2},\s+\d{4})",

        r"\bDeadline\s*[:\-]?\s*"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})",

        r"\bApplication Deadline\s*[:\-]?\s*"
        r"(.+?)(?=\s+[A-Z][A-Za-z ]+\s*:|$)",
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:
                return value

    return None


# ============================================================
# SALARY
# ============================================================

def extract_salary(
    text,
    json_ld=None
):
    """Extract salary information."""

    if json_ld:

        salary = json_ld.get(
            "baseSalary"
        )

        if isinstance(salary, dict):

            value = salary.get(
                "value"
            )

            if isinstance(value, dict):

                min_value = value.get(
                    "minValue"
                )

                max_value = value.get(
                    "maxValue"
                )

                currency = salary.get(
                    "currency"
                )

                if min_value and max_value:
                    return (
                        f"{currency or ''} "
                        f"{min_value} - {max_value}"
                    ).strip()

                if min_value:
                    return (
                        f"{currency or ''} "
                        f"{min_value}"
                    ).strip()

        elif isinstance(salary, str):

            value = clean_text(salary)

            if value:
                return value

    normalized = clean_text(text)

    # Only inspect the actual salary area.
    match = re.search(
        r"\bSalary\s*[:\-]?\s*"
        r"(.{1,150})",
        normalized,
        re.IGNORECASE
    )

    if not match:
        return None

    value = clean_text(
        match.group(1)
    )

    # Remove obvious unrelated footer text.
    value = re.split(
        r"\b(?:Popular Jobs|Career Advice|"
        r"Jobs You Might Be Interested In)\b",
        value,
        flags=re.IGNORECASE
    )[0]

    return value or None


# ============================================================
# DESCRIPTION EXTRACTION
# ============================================================

DESCRIPTION_STOP_HEADINGS = (
    "Method of Application",
    "How to Apply",
    "Jobs You Might Be Interested In",
    "Related Companies Hiring Now",
    "Career Advice",
    "Subscribe to Job Alert",
    "Find Your Dream Job",
    "Back To Home",
)


def extract_description_from_json_ld(json_ld):
    """Extract description from JobPosting JSON-LD."""

    if not json_ld:
        return ""

    description = json_ld.get(
        "description"
    )

    if not description:
        return ""

    # JSON-LD descriptions are often HTML.
    description = re.sub(
        r"<br\s*/?>",
        "\n",
        str(description),
        flags=re.IGNORECASE
    )

    description = re.sub(
        r"</p\s*>",
        "\n",
        description,
        flags=re.IGNORECASE
    )

    description = re.sub(
        r"<[^>]+>",
        " ",
        description
    )

    return clean_text(description)


def extract_main_job_container(page):
    """
    Find the main content container for the job.

    This deliberately avoids using the entire body because
    MyJobMag places navigation, related jobs, salary widgets,
    career advice and footer content in the body.
    """

    selectors = (
        "article",
        '[itemtype*="JobPosting"]',
        '[class*="job-details"]',
        '[class*="job-detail"]',
        '[class*="job_description"]',
        '[class*="job-description"]',
        '[class*="job-content"]',
        '[class*="job-content-area"]',
        "main",
    )

    best_locator = None
    best_length = 0

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            ).all()

            for element in elements:

                try:
                    text = clean_text(
                        element.inner_text()
                    )
                except Exception:
                    continue

                length = len(text)

                if length > best_length:
                    best_length = length
                    best_locator = element

        except Exception:
            continue

    return best_locator


def extract_main_job_text(page):
    """
    Extract the main job section while removing obvious
    navigation/footer noise.
    """

    container = extract_main_job_container(page)

    if container:

        try:
            text = container.inner_text()

            if text:
                return clean_text(text)

        except Exception:
            pass

    # Fallback to body text.
    text = get_page_text(page)

    if not text:
        return ""

    # Remove common footer sections.
    for heading in DESCRIPTION_STOP_HEADINGS:

        pattern = re.compile(
            rf"\b{re.escape(heading)}\b",
            re.IGNORECASE
        )

        match = pattern.search(text)

        if match:
            text = text[:match.start()]
            break

    return clean_text(text)


def extract_description(
    page,
    text,
    json_ld=None
):
    """
    Extract the actual job description.

    Priority:

        1. JSON-LD description
        2. Main job content container
        3. Text-based extraction
    """

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    json_description = (
        extract_description_from_json_ld(
            json_ld
        )
    )

    if json_description:
        return json_description

    # --------------------------------------------------------
    # Main job container
    # --------------------------------------------------------

    main_text = extract_main_job_text(
        page
    )

    if not main_text:
        main_text = text or ""

    # --------------------------------------------------------
    # Remove the Method of Application section
    # --------------------------------------------------------

    for heading in (
        "Method of Application",
        "How to Apply",
    ):

        match = re.search(
            rf"\b{re.escape(heading)}\b",
            main_text,
            re.IGNORECASE
        )

        if match:
            main_text = main_text[:match.start()]
            break

    # --------------------------------------------------------
    # Remove common MyJobMag UI text from beginning/end
    # --------------------------------------------------------

    noise_patterns = (
        r"Check how your CV aligns with this job",
        r"Build your CV for free",
        r"Download in different templates",
        r"Share Save Email Report",
    )

    for pattern in noise_patterns:

        main_text = re.sub(
            pattern,
            " ",
            main_text,
            flags=re.IGNORECASE
        )

    return clean_text(
        main_text
    )


# ============================================================
# SECTION EXTRACTION
# ============================================================

def extract_section(
    text,
    headings,
    stop_headings
):
    """
    Extract a section between headings.

    Example:

        Responsibilities:
        Design APIs...
        Maintain databases...

        Requirements:
        Python...
    """

    if not text:
        return ""

    heading_pattern = "|".join(
        re.escape(item)
        for item in headings
    )

    stop_pattern = "|".join(
        re.escape(item)
        for item in stop_headings
    )

    pattern = (
        rf"(?:{heading_pattern})"
        rf"\s*[:\-]?\s*"
        rf"(.*?)"
        rf"(?=\s+(?:{stop_pattern})\s*[:\-]?|$)"
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


def extract_responsibilities(
    text
):
    """Extract responsibilities/duties."""

    headings = (
        "Key Responsibilities",
        "Responsibilities",
        "Duties and Responsibilities",
        "Duties",
        "Roles and Responsibilities",
    )

    stop_headings = (
        "Requirements",
        "Qualifications",
        "Knowledge, Experience",
        "Knowledge and Experience",
        "Skills",
        "Essential Competencies",
        "Technical/ Functional competencies",
        "Method of Application",
        "How to Apply",
    )

    return extract_section(
        text,
        headings,
        stop_headings
    )


def extract_requirements(
    text
):
    """Extract requirements/qualifications."""

    headings = (
        "Requirements",
        "Requirements and Qualifications",
        "Qualifications",
        "Knowledge, Experience and Qualifications required",
        "Knowledge and Experience",
        "Essential Competencies",
    )

    stop_headings = (
        "Technical/ Functional competencies",
        "Technical Competencies",
        "Skills",
        "Method of Application",
        "How to Apply",
    )

    return extract_section(
        text,
        headings,
        stop_headings
    )


# ============================================================
# SKILLS
# ============================================================

COMMON_SKILLS = (
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C#",
    "C++",
    "PHP",
    "Go",
    "Ruby",
    "Dart",
    "React",
    "React.js",
    "Next.js",
    "Angular",
    "Vue",
    "Flask",
    "Django",
    "FastAPI",
    "Node.js",
    "Express",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "SQLite",
    "MongoDB",
    "Redis",
    "SQLAlchemy",
    "REST API",
    "REST APIs",
    "API",
    "Git",
    "GitHub",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "GCP",
    "Linux",
    "HTML",
    "CSS",
    "Tailwind CSS",
    "Bootstrap",
    "Power BI",
    "Tableau",
    "Machine Learning",
    "Deep Learning",
    "Artificial Intelligence",
    "AI",
    "Data Science",
    "Data Engineering",
    "Spark",
    "PySpark",
    "Microsoft Fabric",
    "SAS",
    "R",
    "Automation",
    "CI/CD",
    "Jenkins",
    "Terraform",
    "Oracle",
    "SAP",
    "Salesforce",
    "Dynamics 365",
)


def extract_skills(
    text,
    json_ld=None
):
    """
    Detect technical/professional skills mentioned
    in the job description.
    """

    search_text = text or ""

    if json_ld:

        skills_data = json_ld.get(
            "skills"
        )

        if isinstance(skills_data, str):
            search_text += " " + skills_data

        elif isinstance(skills_data, list):

            search_text += " " + " ".join(
                str(item)
                for item in skills_data
            )

    search_lower = search_text.lower()

    found = []

    for skill in COMMON_SKILLS:

        skill_lower = skill.lower()

        if skill_lower not in search_lower:
            continue

        # Avoid duplicate React / React.js.
        if skill == "React" and "react.js" in search_lower:
            continue

        if skill == "API" and (
            "rest api" in search_lower
            or "rest apis" in search_lower
        ):
            continue

        if skill == "Artificial Intelligence" and (
            "artificial intelligence" in search_lower
        ):
            found.append(skill)
            continue

        if skill not in found:
            found.append(skill)

    return found


# ============================================================
# COMPANY EXTRACTION
# ============================================================

def extract_company(
    page,
    json_ld=None,
    job_title=None
):
    """
    Extract employer/company name.

    Priority:

        1. JSON-LD hiringOrganization
        2. Structured HTML
        3. Page title
        4. Job title 'at Company' pattern
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
            dict
        ):

            name = clean_text(
                organization.get("name")
            )

            if name:
                return name

        elif isinstance(
            organization,
            str
        ):

            name = clean_text(
                organization
            )

            if name:
                return name

    # --------------------------------------------------------
    # Structured HTML
    # --------------------------------------------------------

    selectors = (
        '[itemprop="hiringOrganization"]',
        '[itemprop="name"]',
        '[class*="company-name"]',
        '[class*="company_name"]',
        '[class*="employer"]',
    )

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            ).all()

            for element in elements:

                value = safe_inner_text(
                    element
                )

                if not value:
                    continue

                if len(value) > 120:
                    continue

                lower_value = value.lower()

                if lower_value in (
                    "myjobmag",
                    "myjobmag kenya",
                    "company",
                ):
                    continue

                return value

        except Exception:
            continue

    # --------------------------------------------------------
    # Page title
    # --------------------------------------------------------

    try:
        page_title = clean_text(
            page.title()
        )
    except Exception:
        page_title = ""

    match = re.search(
        r"\bat\s+(.+?)(?:\s+September|\s+October|\s+November|"
        r"\s+December|\s+January|\s+February|\s+March|"
        r"\s+April|\s+May|\s+June|\s+July|\s+August|"
        r"\s+202\d|\s+\||$)",
        page_title,
        re.IGNORECASE
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        if value:
            return value

    # --------------------------------------------------------
    # Job title
    # --------------------------------------------------------

    if job_title:

        match = re.search(
            r"\bat\s+(.+)$",
            job_title,
            re.IGNORECASE
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:
                return value

    return None


# ============================================================
# TITLE EXTRACTION
# ============================================================

def extract_job_title(
    page,
    json_ld=None
):
    """Extract the actual job title."""

    if json_ld:

        value = clean_text(
            json_ld.get("title")
        )

        if value:
            return value

    selectors = (
        "h1",
        '[itemprop="title"]',
    )

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            ).all()

            for element in elements:

                value = safe_inner_text(
                    element
                )

                if value:
                    return value

        except Exception:
            continue

    try:

        title = clean_text(
            page.title()
        )

        # Remove common MyJobMag suffix.
        title = re.sub(
            r"\s+at\s+.+?\s+\w+\s+\d{1,2},?\s+\d{4}\s*\|\s*MyJobMag$",
            "",
            title,
            flags=re.IGNORECASE
        )

        title = re.sub(
            r"\s*\|\s*MyJobMag$",
            "",
            title,
            flags=re.IGNORECASE
        )

        return clean_text(title)

    except Exception:
        return ""


# ============================================================
# MAIN JOB EXTRACTION
# ============================================================

def extract_job_data(
    page
):
    """
    Extract structured information from the current
    MyJobMag job page.
    """

    # --------------------------------------------------------
    # JSON-LD
    # --------------------------------------------------------

    json_ld = extract_json_ld_job(
        page
    )

    if json_ld:

        print(
            "JSON-LD JobPosting found."
        )

    else:

        print(
            "No JSON-LD JobPosting found. "
            "Using page extraction."
        )

    # --------------------------------------------------------
    # Page text
    # --------------------------------------------------------

    body_text = get_page_text(
        page
    )

    main_text = extract_main_job_text(
        page
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title = extract_job_title(
        page,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Company
    # --------------------------------------------------------

    company = extract_company(
        page,
        json_ld=json_ld,
        job_title=title
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    location = extract_location(
        page,
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Job type
    # --------------------------------------------------------

    job_type = extract_job_type(
        page,
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Qualification
    # --------------------------------------------------------

    qualification = extract_qualification(
        page,
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    experience = extract_experience(
        page,
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Job field
    # --------------------------------------------------------

    job_field = extract_job_field(
        page,
        body_text
    )

    # --------------------------------------------------------
    # Posted
    # --------------------------------------------------------

    posted = extract_posted(
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Deadline
    # --------------------------------------------------------

    deadline = extract_deadline(
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Salary
    # --------------------------------------------------------

    salary = extract_salary(
        body_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    description = extract_description(
        page,
        main_text,
        json_ld=json_ld
    )

    # --------------------------------------------------------
    # Responsibilities
    # --------------------------------------------------------

    responsibilities = extract_responsibilities(
        description
    )

    # --------------------------------------------------------
    # Requirements
    # --------------------------------------------------------

    requirements = extract_requirements(
        description
    )

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    skills = extract_skills(
        description,
        json_ld=json_ld
    )

    return {
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
    }


# ============================================================
# INSPECT JOB
# ============================================================

def inspect_job(
    page,
    url
):
    """
    Navigate to and inspect one MyJobMag job.

    Returns:

        {
            "title": "...",
            "company": "...",
            "location": "...",
            "job_type": "...",
            "qualification": "...",
            "experience": "...",
            "job_field": "...",
            "posted": "...",
            "deadline": "...",
            "salary": "...",
            "description": "...",
            "responsibilities": "...",
            "requirements": "...",
            "skills": [...],
            "application": {...},
            "application_links": [...]
        }
    """

    print()
    print("=" * 60)
    print("INSPECTING MYJOBMAG JOB")
    print("=" * 60)

    print()
    print(
        f"URL: {url}"
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

        page_title = page.title()

        print(
            f"Page title: {page_title}"
        )

    except Exception as error:

        print(
            f"Job navigation error: {error}"
        )

        raise

    # --------------------------------------------------------
    # Extract job
    # --------------------------------------------------------

    job = extract_job_data(
        page
    )

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    text = get_page_text(
        page
    )

    application = extract_application_method(
        page,
        text,
        job_title=job.get("title")
    )

    # --------------------------------------------------------
    # Display extracted data
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("EXTRACTED JOB")
    print("=" * 60)

    print(
        f"Title: {job.get('title')}"
    )

    print(
        f"Company: {job.get('company')}"
    )

    print(
        f"Location: {job.get('location')}"
    )

    print(
        f"Job type: {job.get('job_type')}"
    )

    print(
        f"Qualification: {job.get('qualification')}"
    )

    print(
        f"Experience: {job.get('experience')}"
    )

    print(
        f"Job field: {job.get('job_field')}"
    )

    print(
        f"Posted: {job.get('posted')}"
    )

    print(
        f"Deadline: {job.get('deadline')}"
    )

    print(
        f"Salary: {job.get('salary')}"
    )

    print(
        f"Description length: "
        f"{len(job.get('description') or '')}"
    )

    print(
        f"Responsibilities length: "
        f"{len(job.get('responsibilities') or '')}"
    )

    print(
        f"Requirements length: "
        f"{len(job.get('requirements') or '')}"
    )

    print(
        f"Skills: "
        f"{', '.join(job.get('skills') or [])}"
    )

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    print()
    print("APPLICATION")
    print("-" * 60)

    print(
        f"Method: "
        f"{application.get('method')}"
    )

    if application.get("email"):

        print(
            f"Email: "
            f"{application['email']}"
        )

    if application.get("subject"):

        print(
            f"Subject: "
            f"{application['subject']}"
        )

    if application.get("url"):

        print(
            f"URL: "
            f"{application['url']}"
        )

    # --------------------------------------------------------
    # Application-related links
    # --------------------------------------------------------

    application_links = extract_application_links(
        page
    )

    print()
    print("APPLICATION-RELATED LINKS")
    print("-" * 60)

    seen_links = set()

    for link in application_links:

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
    # Return complete result
    # --------------------------------------------------------

    job["page_title"] = page_title
    job["url"] = url
    job["text"] = text
    job["application"] = application
    job["application_links"] = application_links

    return job


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    from scripts.browser.browser import (
        launch_browser,
        close_browser,
    )

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
        # Open MyJobMag Python jobs
        # ----------------------------------------------------

        print()
        print(
            "Opening MyJobMag Python jobs..."
        )

        response = page.goto(
            MYJOBMAG_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print(
            "MyJobMag page loaded."
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

        print()
        print(
            "Collecting job links..."
        )
        print()

        jobs = collect_job_links(
            page
        )

        print(
            f"Found {len(jobs)} job links."
        )

        # ----------------------------------------------------
        # Display first five
        # ----------------------------------------------------

        for index, job in enumerate(
            jobs[:5],
            start=1
        ):

            print(
                f"{index}. {job['title']}"
            )

            print(
                f"   {job['url']}"
            )

        # ----------------------------------------------------
        # Inspect first job
        # ----------------------------------------------------

        if jobs:

            first_job = jobs[0]

            print()
            print("=" * 60)
            print(
                "TESTING FIRST JOB"
            )
            print("=" * 60)

            result = inspect_job(
                page,
                first_job["url"]
            )

            print()
            print("=" * 60)
            print(
                "INSPECTION COMPLETE"
            )
            print("=" * 60)

            print()

            print(
                f"Title: "
                f"{result.get('title')}"
            )

            print(
                f"Company: "
                f"{result.get('company')}"
            )

            print(
                f"Location: "
                f"{result.get('location')}"
            )

            print(
                f"Job type: "
                f"{result.get('job_type')}"
            )

            print(
                f"Qualification: "
                f"{result.get('qualification')}"
            )

            print(
                f"Experience: "
                f"{result.get('experience')}"
            )

            print(
                f"Job field: "
                f"{result.get('job_field')}"
            )

            print(
                f"Posted: "
                f"{result.get('posted')}"
            )

            print(
                f"Deadline: "
                f"{result.get('deadline')}"
            )

            print(
                f"Description length: "
                f"{len(result.get('description') or '')}"
            )

            print(
                f"Responsibilities length: "
                f"{len(result.get('responsibilities') or '')}"
            )

            print(
                f"Requirements length: "
                f"{len(result.get('requirements') or '')}"
            )

            print(
                f"Skills: "
                f"{', '.join(result.get('skills') or [])}"
            )

            print(
                f"Application method: "
                f"{result['application'].get('method')}"
            )

            if result["application"].get(
                "email"
            ):

                print(
                    f"Application email: "
                    f"{result['application']['email']}"
                )

            if result["application"].get(
                "subject"
            ):

                print(
                    f"Application subject: "
                    f"{result['application']['subject']}"
                )

            if result["application"].get(
                "url"
            ):

                print(
                    f"Application URL: "
                    f"{result['application']['url']}"
                )

    except Exception as error:

        print()
        print(
            f"MyJobMag test error: {error}"
        )

    finally:

        if browser and playwright:

            print()
            print(
                "Closing browser..."
            )

            close_browser(
                playwright,
                browser
            )