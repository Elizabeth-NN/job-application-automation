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


def collect_jobs(listing_url):
    """
    Collect job links from a BrighterMonday
    listing page.
    """

    soup = get_page(
        listing_url
    )

    jobs = []
    seen_urls = set()

    # BrighterMonday job listings use links
    # containing /listings/
    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get("href", "")

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
            "url": job_url
        })

    return jobs


def extract_description(soup):
    """
    Extract the job description and requirements.
    """

    description_parts = []

    # Look for common job-detail headings.
    headings = soup.find_all(
        ["h2", "h3"]
    )

    for heading in headings:

        heading_text = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        ).lower()

        if (
            "job summary" in heading_text
            or "job descriptions" in heading_text
            or "requirements" in heading_text
            or "job description" in heading_text
        ):

            # Collect following content.
            for element in heading.find_all_next():

                text = clean_text(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if text:
                    description_parts.append(
                        text
                    )

    # Remove duplicates while preserving order.
    unique_parts = []
    seen = set()

    for part in description_parts:

        if part in seen:
            continue

        seen.add(part)

        unique_parts.append(
            part
        )

    return "\n".join(
        unique_parts
    )


def extract_metadata(soup):
    """
    Extract basic metadata from a BrighterMonday
    job page.
    """

    text = soup.get_text(
        "\n",
        strip=True
    )

    lines = [
        clean_text(line)
        for line in text.splitlines()
        if clean_text(line)
    ]

    metadata = {
        "location": "",
        "job_type": "",
        "experience": "",
        "qualification": "",
        "posted": "",
        "deadline": "",
    }

    # --------------------------------------------------
    # Look for known metadata values.
    # --------------------------------------------------

    for index, line in enumerate(lines):

        lower_line = line.lower()

        if (
            "full time" in lower_line
            or "part time" in lower_line
            or "contract" in lower_line
            or "internship" in lower_line
        ):

            if not metadata["job_type"]:
                metadata["job_type"] = line

        if (
            line in [
                "Today",
                "Yesterday",
            ]
            or "days ago" in lower_line
            or "hours ago" in lower_line
        ):

            if not metadata["posted"]:
                metadata["posted"] = line

    # --------------------------------------------------
    # Extract location from common page text.
    # --------------------------------------------------

    location_candidates = [
        "Nairobi",
        "Mombasa",
        "Kisumu",
        "Nakuru",
        "Eldoret",
        "Thika",
        "Kenya",
        "Remote",
        "Outside Kenya",
        "Rest of Kenya",
    ]

    for candidate in location_candidates:

        for line in lines:

            if candidate.lower() == line.lower():

                metadata["location"] = candidate

                break

        if metadata["location"]:
            break

    return metadata


def extract_company(soup):
    """
    Extract company name from the job page.
    """

    # BrighterMonday job pages display the company
    # close to the main job title.
    heading = soup.find("h1")

    if not heading:
        return ""

    # Look at nearby text after the title.
    for element in heading.find_all_next():

        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        # Skip common category labels.
        if text in [
            "Software & Data",
            "Engineering & Technology",
        ]:
            continue

        # Return the first useful short company name.
        if len(text) < 150:
            return text

    return ""


def get_job_details(job_url):
    """
    Extract structured information from a
    BrighterMonday job page.
    """

    soup = get_page(
        job_url
    )

    # ==================================================
    # TITLE
    # ==================================================

    heading = soup.find("h1")

    if heading:

        title = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

    else:

        title = ""

    # ==================================================
    # METADATA
    # ==================================================

    metadata = extract_metadata(
        soup
    )

    # ==================================================
    # COMPANY
    # ==================================================

    company = extract_company(
        soup
    )

    # ==================================================
    # DESCRIPTION
    # ==================================================

    description = extract_description(
        soup
    )

    # Fallback if structured extraction fails.
    if not description:

        description = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

    return {
        "title": title,
        "company": company,
        "location": metadata["location"],
        "job_type": metadata["job_type"],
        "qualification": metadata["qualification"],
        "experience": metadata["experience"],
        "posted": metadata["posted"],
        "deadline": metadata["deadline"],
        "description": description,
        "url": job_url,
        "source": "BrighterMonday",
    }


if __name__ == "__main__":

    listing_url = (
        "https://www.brightermonday.co.ke/"
        "jobs"
    )

    print(
        "Collecting BrighterMonday jobs...\n"
    )

    jobs = collect_jobs(
        listing_url
    )

    print(
        f"Found {len(jobs)} jobs\n"
    )

    for index, job in enumerate(
        jobs[:10],
        start=1
    ):

        print(
            f"{index}. "
            f"{job['title']}"
        )

        print(
            f"   {job['url']}"
        )