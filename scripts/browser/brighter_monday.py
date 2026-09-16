from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin
import json
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

# ---------------------------------------------------------------------------
# BrighterMonday renders a single-line "facts strip" on every job page, e.g.:
#
#   Min Qualification: Bachelors Experience Level: Entry level
#   Experience Length: 2 years Language Requirement: English
#   Working Hours: Full Time - 8 to 5 Applicant Location: Kenya
#
# The labels are stable even though the surrounding CSS classes are not, so
# we parse this strip by label rather than hunting for specific classes.
# Order of labels on the page can vary slightly, so the parser below does not
# assume a fixed order — it just needs the label set below to be accurate.
# ---------------------------------------------------------------------------
FACT_LABELS = [
    "Min Qualification",
    "Experience Level",
    "Experience Length",
    "Language Requirement",
    "Working Hours",
    "Applicant Location",
]

_FACT_LABEL_ALT = "|".join(re.escape(label) for label in FACT_LABELS)
_FACT_LINE_PATTERN = re.compile(
    rf"({_FACT_LABEL_ALT})\s*:\s*(.*?)(?=(?:{_FACT_LABEL_ALT})\s*:|$)",
    re.IGNORECASE,
)


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


# ---------------------------------------------------------------------------
# Company extraction
# ---------------------------------------------------------------------------

def _get_meta_content(page, selector):
    """Read a <meta ... content="..."> tag's value. Safe no-op if absent."""

    try:
        locator = page.locator(selector).first
        if locator.count():
            content = locator.get_attribute("content", timeout=3000)
            if content:
                return clean_text(content)
    except Exception:
        pass

    return None


def _parse_meta_company_and_location(page):
    """
    BrighterMonday auto-generates <head> meta tags for every listing in one
    of these forms, independent of which visual template the job uses:

        <meta name="description" content="Apply online for the flutter
            developer vacancy at Tourlast Limited in Nairobi today. ...">
        <meta property="og:description" content="Hiring now at Tourlast
            Limited">

    These live in <head>, so unlike the visible page body they are never
    polluted by sidebar/filter navigation markup, which makes them a more
    reliable source for company (and a reasonable fallback for location)
    than DOM traversal of the body.
    """

    company = None
    location = None

    description = _get_meta_content(page, 'meta[name="description"]')
    if description:
        match = re.search(
            r"vacancy at (.+?) in (.+?) today", description, re.IGNORECASE
        )
        if match:
            company = clean_text(match.group(1))
            location = clean_text(match.group(2))

    if not company:
        og_description = _get_meta_content(page, 'meta[property="og:description"]')
        if og_description:
            match = re.search(r"Hiring now at (.+)$", og_description, re.IGNORECASE)
            if match:
                company = clean_text(match.group(1))

    return company, location


def extract_company(page, jsonld=None):
    """
    Extract the hiring company name.

    BrighterMonday job pages do not label this field ("Company:" /
    "Employer:" does not appear on the page), and the visible heading
    structure around the job title is not reliable for this either — it
    turned out to pick up hidden nav/menu headings rather than the company
    name. The <head> meta description is generated consistently for every
    listing template and isolated from that body clutter, so it's used as
    the primary source instead.

    Fallback chain:
        1. JSON-LD hiringOrganization.name, when this template includes it.
        2. Meta description / og:description (reliable across templates —
           see _parse_meta_company_and_location).
        3. Link to a /company/ page (present when the employer has a
           public profile).
        4. Label-based text search, in case a particular listing template
           does include an explicit "Company"/"Employer" label.
        5. None.
    """

    if jsonld and jsonld.get("company"):
        return jsonld["company"]

    company, _location = _parse_meta_company_and_location(page)
    if company:
        return company

    # 3. Direct link to the company's profile page.
    try:
        locator = page.locator("a[href*='/company/']").first
        if locator.count():
            text = clean_text(locator.inner_text(timeout=3000))
            if text:
                return text
    except Exception:
        pass

    # 3. Explicit label fallback, for templates that do include one.
    try:
        body_text = clean_text(page.locator("body").inner_text(timeout=5000))
    except Exception:
        body_text = ""

    for pattern in (
        r"\bCompany\s*:?\s*([A-Za-z0-9&.,'()\- ]{2,150})",
        r"\bEmployer\s*:?\s*([A-Za-z0-9&.,'()\- ]{2,150})",
    ):
        match = re.search(pattern, body_text, re.IGNORECASE)
        if match:
            value = clean_text(match.group(1))
            if value:
                return value

    return None


# ---------------------------------------------------------------------------
# Facts-strip metadata extraction (qualification / experience / job type /
# location), with a selector fallback hierarchy:
#   specific selector -> alternative selector -> label-based extraction -> None
# ---------------------------------------------------------------------------

def _get_facts_strip_text(page):
    """
    Locate the small text block that contains the "Min Qualification: ...
    Applicant Location: ..." facts strip, without pulling in the rest of
    the page (nav, similar-jobs, footer, filters, etc. can all contain
    stray words like "Location" and would otherwise cause false matches).
    """

    # 1. Specific selector: the element that actually contains the
    #    "Min Qualification" label. Playwright's text engine returns the
    #    smallest matching element, which is normally just this one line.
    try:
        locator = page.locator("text=/Min Qualification\\s*:/i").first
        if locator.count():
            text = clean_text(locator.inner_text(timeout=3000))
            if text and "Min Qualification" in text:
                return text
    except Exception:
        pass

    # 2. Alternative selector: some templates wrap the strip in a
    #    dedicated summary/details container instead of a bare text node.
    for selector in (
        "[class*='job-summary']",
        "[class*='jobSummary']",
        "[class*='job-details']",
        "[class*='details']",
    ):
        try:
            locator = page.locator(selector).first
            if locator.count():
                text = clean_text(locator.inner_text(timeout=3000))
                if "Min Qualification" in text or "Experience Level" in text:
                    return text
        except Exception:
            continue

    # 3. Last resort: scan the full body text but only keep a narrow
    #    window starting at "Min Qualification" so unrelated page content
    #    can't leak into the parsed fields.
    try:
        body_text = clean_text(page.locator("body").inner_text(timeout=5000))
    except Exception:
        body_text = ""

    match = re.search(r"Min Qualification\s*:.*", body_text, re.IGNORECASE)
    if match:
        # Cut off well before any subsequent, unrelated page section.
        window = match.group(0)[:400]
        cutoff = re.search(r"Job descriptions?|Important safety tips", window, re.IGNORECASE)
        if cutoff:
            window = window[: cutoff.start()]
        return clean_text(window)

    return ""


def _parse_facts_strip(text):
    """Split the facts strip into a {label: value} dict."""

    facts = {}

    if not text:
        return facts

    for match in _FACT_LINE_PATTERN.finditer(text):
        label = match.group(1).strip()
        # Normalize label casing/spacing so lookups are predictable.
        label = " ".join(word.capitalize() for word in label.split())
        value = clean_text(match.group(2))
        if value:
            facts[label] = value

    return facts


def extract_experience_from_description(description):
    """
    Fallback when no structured "Experience Length" field is present:
    look for an explicit years-of-experience requirement in the job
    description/requirements text.

    Returns a normalized "N+ years" string when a clean number is found.
    If experience is clearly discussed but no clean number can be pulled
    out, the original sentence is preserved instead of fabricating a
    value.

    Recruiter/agency-posted listings often open with the agency's own
    pitch ("HR Box Africa has over 20 years of experience placing top
    talent..."), which otherwise gets mistaken for the job's experience
    requirement. Matches whose immediate preceding context reads like
    that kind of self-description are skipped in favor of a later match
    that actually describes what the candidate needs.
    """

    if not description:
        return None

    disqualifying_context = [
        "founded", "established", "since", "in business", "in operation",
        "years in the industry", "recruitment agency", "years in placing",
        "has been operating", "our company", "our agency", "we have over",
        "with over", "has over", "combined", "our client", "leading",
        "team has", "boasts",
    ]
    requirement_context = [
        "minimum", "at least", "least", "required", "must have", "must",
        "need", "requires",
    ]

    def is_self_description(start_index):
        context = description[max(0, start_index - 60):start_index].lower()
        return any(bad in context for bad in disqualifying_context)

    def contains_disqualifying_language(text):
        lowered = text.lower()
        return any(bad in lowered for bad in disqualifying_context)

    def is_implausible_without_requirement_wording(number, start_index):
        # A double-digit-plus "years of experience" figure is very rarely
        # an individual hire's requirement (that's usually a company's or
        # team's aggregate track record) unless the text explicitly frames
        # it as a requirement right next to the number.
        if number <= 15:
            return False
        narrow_context = description[max(0, start_index - 25):start_index].lower()
        return not any(req in narrow_context for req in requirement_context)

    patterns = [
        r"(\d+)\+?\s*(?:to\s*\d+\s*)?years?(?:\s+of)?(?:\s+\w+){0,3}\s+experience",
        r"experience\s+of\s+(?:at least\s+)?(\d+)\+?\s*years?",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, description, re.IGNORECASE):
            if is_self_description(match.start()):
                continue
            number = int(match.group(1))
            if is_implausible_without_requirement_wording(number, match.start()):
                continue
            return f"{number}+ years"

    # Preserve the requirement sentence verbatim rather than guessing.
    sentence_match = re.search(
        r"([^.]*\d+[^.]*experience[^.]*\.)", description, re.IGNORECASE
    )
    if sentence_match:
        candidate = sentence_match.group(1)
        if not is_self_description(sentence_match.start()) and not contains_disqualifying_language(candidate):
            return clean_text(candidate)

    return None


QUALIFICATION_PATTERNS = [
    (r"\bPh\.?D\b", "PhD"),
    (r"Master'?s degree", "Masters"),
    (r"Bachelor'?s degree", "Bachelors"),
    (r"\bDiploma\b", "Diploma"),
    (r"\bCertificate\b", "Certificate"),
]


def extract_qualification_from_description(description):
    """
    Fallback when no structured "Min Qualification" field is present:
    detect an explicitly stated minimum-qualification phrase in the job
    description. This only recognizes qualifications the listing actually
    states outright — it never infers a qualification from context.
    """

    if not description:
        return None

    for pattern, label in QUALIFICATION_PATTERNS:
        if re.search(pattern, description, re.IGNORECASE):
            return label

    return None


JOB_TYPE_PILL_SLUGS = [
    "full-time",
    "part-time",
    "contract",
    "internship-graduate",
    "temporary",
    "volunteer",
]


def extract_job_type_from_pills(page):
    """
    Fallback when no structured "Working Hours" field is present: every
    job detail page (regardless of template) renders a row of breadcrumb-
    style pills near the title that link to top-level job-type filter
    pages, e.g. a "Full Time" pill linking to /jobs/full-time. Verified
    present on a live listing page. This is a much more stable signal
    than any CSS class, since it's how the site's own navigation works.
    """

    for slug in JOB_TYPE_PILL_SLUGS:
        try:
            locator = page.locator(f"a[href*='/jobs/{slug}']").first
            if locator.count():
                text = clean_text(locator.inner_text(timeout=2000))
                if text:
                    return text
        except Exception:
            continue

    return None


def extract_metadata(page, description="", jsonld=None):
    """
    Extract structured metadata (qualification, experience, job type,
    location) from the facts strip on a BrighterMonday job page.
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

    facts_text = _get_facts_strip_text(page)
    facts = _parse_facts_strip(facts_text)

    result["qualification"] = facts.get("Min Qualification")
    result["experience_level"] = facts.get("Experience Level")
    result["experience_length"] = facts.get("Experience Length")
    result["job_type"] = facts.get("Working Hours")
    result["location"] = facts.get("Applicant Location")

    # Qualification fallback: an explicitly stated degree/certificate
    # requirement in the description, when this template has no facts
    # strip at all (common for agency/recruiter-posted listings).
    if not result["qualification"]:
        result["qualification"] = extract_qualification_from_description(description)

    # Job type fallback #1: JSON-LD employmentType, when this template
    # includes it (e.g. "FULL_TIME" -> present it in a readable form).
    if not result["job_type"] and jsonld and jsonld.get("job_type"):
        raw_type = jsonld["job_type"]
        result["job_type"] = clean_text(str(raw_type).replace("_", " ").title())

    # Job type fallback #2: the breadcrumb-style pill link every job page
    # renders regardless of template (see extract_job_type_from_pills).
    if not result["job_type"]:
        result["job_type"] = extract_job_type_from_pills(page)

    # Location fallback, in priority order: JSON-LD jobLocation (when
    # present, usually fairly granular) -> the <head> meta description,
    # which reliably names a (coarser) location for every listing
    # regardless of template — see _parse_meta_company_and_location.
    # Coarse-but-present beats "Not found" here, and we never invent
    # anything the page doesn't state.
    if not result["location"] and jsonld and jsonld.get("location"):
        result["location"] = jsonld["location"]

    if not result["location"]:
        _company, meta_location = _parse_meta_company_and_location(page)
        if meta_location:
            result["location"] = meta_location

    # Experience: prefer the structured field; otherwise fall back to the
    # description text. Never fabricate a value.
    if result["experience_length"]:
        number_match = re.match(r"(\d+)", result["experience_length"])
        if number_match:
            result["experience"] = f"{number_match.group(1)}+ years"
        else:
            result["experience"] = result["experience_length"]
    else:
        result["experience"] = extract_experience_from_description(description)

    # Posted / deadline: pulled separately from JSON-LD structured data
    # (see extract_dates_from_jsonld) and merged in by the caller, since
    # that is a much more reliable source than scraping visible text.

    return result


def _stringify_jsonld_location(place):
    """
    schema.org jobLocation is typically a Place with a nested
    PostalAddress. Different posting templates populate different subsets
    of its fields, so this joins whatever is actually present rather than
    assuming a fixed shape.
    """

    if not isinstance(place, dict):
        return None

    address = place.get("address", place)
    if not isinstance(address, dict):
        return None

    parts = [
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("addressCountry"),
    ]

    parts = [clean_text(p) for p in parts if p and clean_text(p)]

    return ", ".join(parts) if parts else None


def extract_jsonld_jobposting(page):
    """
    Extract whatever schema.org JobPosting fields are present in the
    page's JSON-LD structured data.

    This is far more reliable than regex-matching visible text for fields
    like posted/deadline dates, since those are frequently only present in
    <script type="application/ld+json"> blocks rather than anywhere a user
    can see. Not every listing template includes this data (or includes
    every field within it) — any field left out here is left as None
    rather than guessed at.

    Returns a dict with keys: posted, deadline, company, location,
    job_type.
    """

    result = {
        "posted": None,
        "deadline": None,
        "company": None,
        "location": None,
        "job_type": None,
    }

    try:
        scripts = page.locator('script[type="application/ld+json"]').all()
    except Exception:
        return result

    for script in scripts:
        try:
            raw = script.text_content()
        except Exception:
            continue

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]

        for item in candidates:
            if not isinstance(item, dict):
                continue

            item_type = item.get("@type", "")
            is_job_posting = (
                item_type == "JobPosting"
                or (isinstance(item_type, list) and "JobPosting" in item_type)
            )

            if not is_job_posting and "datePosted" not in item:
                continue

            result["posted"] = result["posted"] or item.get("datePosted")
            result["deadline"] = result["deadline"] or item.get("validThrough")
            result["job_type"] = result["job_type"] or item.get("employmentType")

            hiring_org = item.get("hiringOrganization")
            if isinstance(hiring_org, dict) and not result["company"]:
                name = hiring_org.get("name")
                if name:
                    result["company"] = clean_text(name)

            job_location = item.get("jobLocation")
            if job_location and not result["location"]:
                if isinstance(job_location, list):
                    for loc in job_location:
                        parsed = _stringify_jsonld_location(loc)
                        if parsed:
                            result["location"] = parsed
                            break
                else:
                    result["location"] = _stringify_jsonld_location(job_location)

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

    # The "main"/"article" landmarks on this site can wrap the entire page
    # (including the filter sidebar and nav dropdowns), not just the job
    # content, which leaks text like "Find a Job Any Job Functions Any
    # Industries ..." in ahead of the actual posting. That preamble is
    # bounded on every template we've seen: real content always starts at
    # "Job summary" or the requirements heading. Cut anything before that.
    start_markers = [
        "Job summary",
        "Job descriptions & requirements",
        "Job Description",
    ]

    earliest_start = None
    for marker in start_markers:
        index = best_text.find(marker)
        if index != -1 and (earliest_start is None or index < earliest_start):
            earliest_start = index

    if earliest_start is not None:
        best_text = best_text[earliest_start:]

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
        # STRUCTURED DATA (JSON-LD JobPosting, when present)
        # ========================================================
        # Read once and reused below for company / location / job type /
        # posted / deadline, since it's an accurate, template-independent
        # source whenever a listing includes it.

        jsonld = extract_jsonld_jobposting(page)

        # ========================================================
        # COMPANY
        # ========================================================

        company = extract_company(page, jsonld=jsonld)

        # ========================================================
        # DESCRIPTION
        # ========================================================

        description = extract_description(
            page
        )

        # ========================================================
        # METADATA (qualification / experience / job type / location)
        # ========================================================

        metadata = extract_metadata(page, description=description, jsonld=jsonld)

        # ========================================================
        # POSTED / DEADLINE (structured data only — never fabricated)
        # ========================================================

        metadata["posted"] = jsonld.get("posted")
        metadata["deadline"] = jsonld.get("deadline")

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
            f"Company: {result['company'] or 'Not found'}"
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


def get_job_details(page, job):
    """
    Fetch full details for a single job link using the shared page's own
    browser context.
    """

    return inspect_brightermonday_job(page.context, job["url"], job["title"])


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

        # A page opened via browser.new_page() lives in an implicit
        # context that Playwright won't let you open further pages from
        # (context.new_page() on it raises "Please use
        # browser.new_context()"). inspect_brightermonday_job() opens a
        # fresh page per job via page.context.new_page(), so we need an
        # explicit context here for that to work.
        context = browser.new_context()
        page = context.new_page()

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
            try:
                context.close()
            except Exception:
                pass
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