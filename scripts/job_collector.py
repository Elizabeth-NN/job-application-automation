import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.myjobmag.co.ke"

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


def extract_value_from_lines(lines, label):
    """
    Extract a metadata value when the label and value
    appear on separate lines.

    Example:

        Location
        Nairobi

    Returns:
        Nairobi
    """

    for index, line in enumerate(lines):

        if line.strip() == label:

            if index + 1 < len(lines):

                value = clean_text(
                    lines[index + 1]
                )

                if value and value not in [
                    "Job Type",
                    "Qualification",
                    "Experience",
                    "Location",
                    "Job Field",
                ]:
                    return value

    return ""


def extract_metadata(lines):
    """
    Extract structured job metadata.

    MyJobMag may display metadata either:
    - on separate lines
    - on one line
    - partially combined

    This function handles both formats.
    """

    metadata = {
        "job_type": "",
        "qualification": "",
        "experience": "",
        "location": "",
    }

    labels = [
        "Job Type",
        "Qualification",
        "Experience",
        "Location",
    ]

    # --------------------------------------------------
    # 1. Try separate-line format
    # --------------------------------------------------

    for label in labels:

        key = label.lower().replace(
            " ",
            "_"
        )

        value = extract_value_from_lines(
            lines,
            label
        )

        if value:
            metadata[key] = value

    # --------------------------------------------------
    # 2. Look for a combined metadata line
    # --------------------------------------------------

    metadata_text = ""

    for line in lines:

        if (
            "Job Type" in line
            and "Qualification" in line
            and "Experience" in line
            and "Location" in line
        ):
            metadata_text = line
            break

    # --------------------------------------------------
    # 3. Parse combined metadata safely
    # --------------------------------------------------

    if metadata_text:

        marker_positions = []

        for label in labels:

            position = metadata_text.find(
                label
            )

            if position != -1:

                marker_positions.append(
                    (position, label)
                )

        marker_positions.sort(
            key=lambda item: item[0]
        )

        for index, (start, label) in enumerate(
            marker_positions
        ):

            if index + 1 < len(marker_positions):

                end = marker_positions[
                    index + 1
                ][0]

            else:

                end = len(
                    metadata_text
                )

            value = metadata_text[
                start + len(label):end
            ]

            value = clean_text(value)

            key = label.lower().replace(
                " ",
                "_"
            )

            if value:
                metadata[key] = value

    return metadata


def extract_posted_and_deadline(lines):
    """Extract posting date and application deadline."""

    posted = ""
    deadline = ""

    for index, line in enumerate(lines):

        if line == "Posted:":

            if index + 1 < len(lines):

                posted = clean_text(
                    lines[index + 1]
                )

        elif line == "Deadline:":

            if index + 1 < len(lines):

                deadline = clean_text(
                    lines[index + 1]
                )

    return posted, deadline


def extract_company(lines):
    """Extract company name from the job page."""

    for line in lines:

        if line.startswith(
            "View Jobs at "
        ):

            return clean_text(
                line.replace(
                    "View Jobs at ",
                    "",
                    1
                )
            )

    return ""


def extract_description(lines):
    """
    Extract the actual job description.

    Starts at common MyJobMag job-content headings.
    """

    description_start = None

    start_headings = [
        "Duties and Responsibilities",
        "Qualifications and Experience",
        "Job Description",
        "Responsibilities",
        "Requirements",
        "Key Responsibilities",
    ]

    for index, line in enumerate(lines):

        if line in start_headings:

            description_start = index

            break

    if description_start is None:

        return ""

    description_lines = lines[
        description_start:
    ]

    return "\n".join(
        description_lines
    )


def get_job_details(job_url):
    """Extract structured information from a job page."""

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
    # PAGE TEXT
    # ==================================================

    page_text = soup.get_text(
        "\n",
        strip=True
    )

    lines = []

    for line in page_text.splitlines():

        cleaned = clean_text(
            line
        )

        if cleaned:

            lines.append(
                cleaned
            )

    # ==================================================
    # METADATA
    # ==================================================

    metadata = extract_metadata(
        lines
    )

    job_type = metadata[
        "job_type"
    ]

    qualification = metadata[
        "qualification"
    ]

    experience = metadata[
        "experience"
    ]

    location = metadata[
        "location"
    ]

    # ==================================================
    # POSTED + DEADLINE
    # ==================================================

    posted, deadline = (
        extract_posted_and_deadline(
            lines
        )
    )

    # ==================================================
    # COMPANY
    # ==================================================

    company = extract_company(
        lines
    )

    # ==================================================
    # DESCRIPTION
    # ==================================================

    description = extract_description(
        lines
    )

    # ==================================================
    # RETURN STRUCTURED DATA
    # ==================================================

    return {
        "title": title,
        "company": company,
        "location": location,
        "job_type": job_type,
        "qualification": qualification,
        "experience": experience,
        "posted": posted,
        "deadline": deadline,
        "description": description,
        "url": job_url,
    }


def collect_jobs(url):
    """Collect job listings from a MyJobMag listing page."""

    soup = get_page(
        url
    )

    jobs = []

    # ==================================================
    # FIND JOB HEADINGS
    # ==================================================

    for heading in soup.find_all("h2"):

        link = heading.find(
            "a"
        )

        if not link:

            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        href = link.get(
            "href"
        )

        if not href:

            continue

        job_url = urljoin(
            BASE_URL,
            href
        )

        jobs.append({
            "title": title,
            "url": job_url
        })

    # ==================================================
    # REMOVE DUPLICATES
    # ==================================================

    unique_jobs = []
    seen_urls = set()

    for job in jobs:

        if job["url"] in seen_urls:

            continue

        seen_urls.add(
            job["url"]
        )

        unique_jobs.append(
            job
        )

    return unique_jobs


if __name__ == "__main__":

    listing_url = (
        "https://www.myjobmag.co.ke/"
        "jobs-by-title/developer-python"
    )

    print(
        "Collecting job listings...\n"
    )

    jobs = collect_jobs(
        listing_url
    )

    print(
        f"Found {len(jobs)} jobs\n"
    )

    if jobs:

        first_job = jobs[0]

        print(
            "Fetching first job:"
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
            "JOB DETAILS"
        )

        print(
            "==========="
        )

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
            f"Qualification: "
            f"{details['qualification']}"
        )

        print(
            f"Experience: "
            f"{details['experience']}"
        )

        print(
            f"Posted: {details['posted']}"
        )

        print(
            f"Deadline: {details['deadline']}"
        )

        print(
            f"URL: {details['url']}"
        )

        print(
            "\nDESCRIPTION"
        )

        print(
            "==========="
        )

        print(
            details["description"][:5000]
        )