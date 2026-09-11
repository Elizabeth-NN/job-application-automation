import re

import requests

from bs4 import BeautifulSoup

from urllib.parse import urljoin


BASE_URL = "https://www.brightermonday.co.ke"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def get_page(url):
    """Download a public webpage and return BeautifulSoup."""

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def clean_text(text):
    """Clean whitespace from extracted text."""

    if not text:
        return ""

    return " ".join(
        text.split()
    ).strip()


def extract_job_article(soup):
    """
    Return the main BrighterMonday job article.

    BrighterMonday places the actual job information
    inside:

        <article class="job__details">
    """

    article = soup.find(
        "article",
        class_="job__details"
    )

    return article


def extract_metadata(article):
    """
    Extract structured metadata from a BrighterMonday
    job article.

    BrighterMonday may render metadata on one line
    or across multiple HTML elements, so we search
    the complete article text.
    """

    metadata = {
        "qualification": "",
        "experience": "",
        "experience_length": "",
        "location": "",
        "job_type": "",
        "posted": "",
    }

    if not article:
        return metadata

    # Get the complete article text.
    text = clean_text(
        article.get_text(
            " ",
            strip=True
        )
    )

    # --------------------------------------------------
    # Qualification
    # --------------------------------------------------

    match = re.search(
        r"Min Qualification:\s*(.*?)(?=\s+Experience Level:)",
        text,
        re.IGNORECASE
    )

    if match:

        metadata["qualification"] = clean_text(
            match.group(1)
        )

    # --------------------------------------------------
    # Experience level
    # --------------------------------------------------

    match = re.search(
        r"Experience Level:\s*(.*?)(?=\s+Experience Length:)",
        text,
        re.IGNORECASE
    )

    if match:

        metadata["experience"] = clean_text(
            match.group(1)
        )

    # --------------------------------------------------
    # Experience length
    # --------------------------------------------------

    match = re.search(
        r"Experience Length:\s*(.*?)(?=\s+Language Requirement:)",
        text,
        re.IGNORECASE
    )

    if match:

        metadata["experience_length"] = clean_text(
            match.group(1)
        )

    # --------------------------------------------------
    # Job type / working hours
    # --------------------------------------------------

    match = re.search(
        r"Working Hours:\s*(.*?)(?=\s+Applicant Location:)",
        text,
        re.IGNORECASE
    )

    if match:

        metadata["job_type"] = clean_text(
            match.group(1)
        )

    # --------------------------------------------------
    # Applicant location
    # --------------------------------------------------

    match = re.search(
        r"Applicant Location:\s*(.*?)(?=\s+Job descriptions? & requirements)",
        text,
        re.IGNORECASE
    )

    if match:

        metadata["location"] = clean_text(
            match.group(1)
        )

    # --------------------------------------------------
    # Posted date
    # --------------------------------------------------

    posted_match = re.search(
        r"\b(\d+\s+(?:day|days|hour|hours|minute|minutes)\s+ago)\b",
        text,
        re.IGNORECASE
    )

    if posted_match:

        metadata["posted"] = clean_text(
            posted_match.group(1)
        )

    else:

        if re.search(
            r"\btoday\b",
            text,
            re.IGNORECASE
        ):

            metadata["posted"] = "Today"

        elif re.search(
            r"\byesterday\b",
            text,
            re.IGNORECASE
        ):

            metadata["posted"] = "Yesterday"

    return metadata


def extract_company(article):
    """
    Extract company name.

    BrighterMonday pages commonly display the company
    immediately after the job title.

    We inspect the article's text instead of blindly
    taking the first element after <h1>.
    """

    if not article:
        return ""

    lines = [
        clean_text(line)
        for line in article.get_text(
            "\n",
            strip=True
        ).splitlines()
        if clean_text(line)
    ]

    # Find the title first.
    heading = article.find("h1")

    title = ""

    if heading:

        title = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

    if title in lines:

        title_index = lines.index(
            title
        )

        # Inspect the next few lines.
        for line in lines[
            title_index + 1:
            title_index + 6
        ]:

            lower = line.lower()

            # Ignore obvious metadata.
            if lower in [
                "sales",
                "real estate",
                "software & data",
                "engineering & technology",
                "nairobi",
                "mombasa",
                "kisumu",
                "nakuru",
                "eldoret",
                "full time",
                "part time",
                "contract",
                "internship",
                "easy apply",
                "featured",
                "new",
            ]:

                continue

            if (
                "ago" in lower
                or "share" in lower
            ):

                continue

            # Avoid returning extremely long text.
            if len(line) <= 100:

                return line

    return ""


def extract_description(article):
    """
    Extract only the actual job description and
    requirements.

    Starts after:

        Job descriptions & requirements
    """

    if not article:
        return ""

    lines = [
        clean_text(line)
        for line in article.get_text(
            "\n",
            strip=True
        ).splitlines()
        if clean_text(line)
    ]

    start_index = None

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            normalized
            == "job descriptions & requirements"
        ):

            start_index = index + 1

            break

    if start_index is None:

        return ""

    description_lines = []

    # --------------------------------------------------
    # Stop at obvious unrelated sections.
    # --------------------------------------------------

    stop_headings = {
        "how to apply",
        "application deadline",
        "share this job",
        "similar jobs",
        "related jobs",
    }

    for line in lines[
        start_index:
    ]:

        if line.lower() in stop_headings:

            break

        description_lines.append(
            line
        )

    return "\n".join(
        description_lines
    )


def extract_title(soup):
    """Extract job title."""

    heading = soup.find("h1")

    if not heading:

        return ""

    return clean_text(
        heading.get_text(
            " ",
            strip=True
        )
    )


def get_job_details(job_url):
    """
    Extract structured information from a
    BrighterMonday job page.
    """

    soup = get_page(
        job_url
    )

    article = extract_job_article(
        soup
    )

    # ==================================================
    # TITLE
    # ==================================================

    title = extract_title(
        soup
    )

    # ==================================================
    # METADATA
    # ==================================================

    metadata = extract_metadata(
        article
    )

    # ==================================================
    # COMPANY
    # ==================================================

    company = extract_company(
        article
    )

    # ==================================================
    # DESCRIPTION
    # ==================================================

    description = extract_description(
        article
    )

    # ==================================================
    # RETURN
    # ==================================================

    return {
        "title": title,

        "company": company,

        "location": metadata[
            "location"
        ],

        "job_type": metadata[
            "job_type"
        ],

        "qualification": metadata[
            "qualification"
        ],

        "experience": metadata[
            "experience"
        ],

        "experience_length": metadata[
            "experience_length"
        ],

        "posted": metadata[
            "posted"
        ],

        "deadline": "",

        "description": description,

        "url": job_url,

        "source": "BrighterMonday",
    }


def collect_jobs(listing_url):
    """
    Collect job listings from a
    BrighterMonday listing page.
    """

    soup = get_page(
        listing_url
    )

    jobs = []

    seen_urls = set()

    # --------------------------------------------------
    # Find job links
    # --------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        )

        if "/listings/" not in href:

            continue

        job_url = urljoin(
            BASE_URL,
            href
        )

        if job_url in seen_urls:

            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not title:

            continue

        seen_urls.add(
            job_url
        )

        jobs.append({
            "title": title,
            "url": job_url,
        })

    return jobs


if __name__ == "__main__":

    listing_url = (
        "https://www.brightermonday.co.ke/"
        "jobs"
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

    print(
        f"Found {len(jobs)} jobs"
    )

    print()

    if jobs:

        first_job = jobs[0]

        print(
            "Testing first job:"
        )

        print(
            first_job["title"]
        )

        print(
            first_job["url"]
        )

        print()

        details = get_job_details(
            first_job["url"]
        )

        print(
            "=" * 60
        )

        print(
            "JOB DETAILS"
        )

        print(
            "=" * 60
        )

        print(
            f"Title: "
            f"{details['title']}"
        )

        print(
            f"Company: "
            f"{details['company']}"
        )

        print(
            f"Location: "
            f"{details['location']}"
        )

        print(
            f"Job Type: "
            f"{details['job_type']}"
        )

        print(
            f"Qualification: "
            f"{details['qualification']}"
        )

        print(
            f"Experience: "
            f"{details['experience']}"
        )

        print(
            f"Experience Length: "
            f"{details['experience_length']}"
        )

        print(
            f"Posted: "
            f"{details['posted']}"
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