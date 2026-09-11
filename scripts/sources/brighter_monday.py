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
    Extract structured metadata from the job article.

    Example:

        Min Qualification: Diploma
        Experience Level: Mid level
        Experience Length: 3 years
        Applicant Location: Nairobi, Kenya
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

    text = article.get_text(
        "\n",
        strip=True
    )

    lines = [
        clean_text(line)
        for line in text.splitlines()
        if clean_text(line)
    ]

    for index, line in enumerate(lines):

        lower = line.lower()

        # ---------------------------------------------
        # Minimum qualification
        # ---------------------------------------------

        if lower.startswith(
            "min qualification:"
        ):

            value = line.split(
                ":",
                1
            )[1]

            metadata["qualification"] = (
                clean_text(value)
            )

        # ---------------------------------------------
        # Experience level
        # ---------------------------------------------

        elif lower.startswith(
            "experience level:"
        ):

            value = line.split(
                ":",
                1
            )[1]

            metadata["experience"] = (
                clean_text(value)
            )

        # ---------------------------------------------
        # Experience length
        # ---------------------------------------------

        elif lower.startswith(
            "experience length:"
        ):

            value = line.split(
                ":",
                1
            )[1]

            metadata["experience_length"] = (
                clean_text(value)
            )

        # ---------------------------------------------
        # Applicant location
        # ---------------------------------------------

        elif lower.startswith(
            "applicant location:"
        ):

            value = line.split(
                ":",
                1
            )[1]

            metadata["location"] = (
                clean_text(value)
            )

        # ---------------------------------------------
        # Working hours / job type
        # ---------------------------------------------

        elif lower.startswith(
            "working hours:"
        ):

            value = line.split(
                ":",
                1
            )[1]

            metadata["job_type"] = (
                clean_text(value)
            )

        # ---------------------------------------------
        # Posted date
        # ---------------------------------------------

        elif (
            "days ago" in lower
            or "day ago" in lower
            or "hours ago" in lower
            or lower == "today"
            or lower == "yesterday"
        ):

            if not metadata["posted"]:

                metadata["posted"] = line

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