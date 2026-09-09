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
    """Download a public webpage."""

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

    return " ".join(text.split())


def get_job_details(job_url):
    """Extract structured information from a job page."""

    soup = get_page(job_url)

    # ---------------------------------
    # Title
    # ---------------------------------

    heading = soup.find("h1")

    title = clean_text(
        heading.get_text(" ", strip=True)
        if heading
        else ""
    )

    # ---------------------------------
    # Main job content
    # ---------------------------------

    page_text = soup.get_text(
        "\n",
        strip=True
    )

    lines = [
        clean_text(line)
        for line in page_text.splitlines()
        if clean_text(line)
    ]

        # ---------------------------------
    # Extract metadata
    # ---------------------------------

    company = ""
    location = ""
    experience = ""
    qualification = ""
    job_type = ""
    posted = ""
    deadline = ""

    # MyJobMag displays the metadata in a block
    # containing these labels.
    metadata_labels = [
        "Job Type",
        "Qualification",
        "Experience",
        "Location",
        "Job Field",
    ]

    # Find the line containing "Posted:"
    # and inspect the surrounding metadata.
    for i, line in enumerate(lines):

        if line == "Posted:" and i + 1 < len(lines):
            posted = lines[i + 1]

        elif line == "Deadline:" and i + 1 < len(lines):
            deadline = lines[i + 1]

    # ---------------------------------
    # Extract the metadata block
    # ---------------------------------

    metadata_index = None

    for i, line in enumerate(lines):

        if (
            "Job Type" in line
            and "Qualification" in line
            and "Experience" in line
        ):
            metadata_index = i
            break

    if metadata_index is not None:

        metadata_block = lines[
            metadata_index:
            metadata_index + 10
        ]

        for line in metadata_block:

            # Only process the actual metadata line.
            if line.startswith("Job Type"):
                value = line.replace(
                    "Job Type",
                    "",
                    1
                ).strip()

                if value:
                    job_type = value

            elif line.startswith("Qualification"):
                value = line.replace(
                    "Qualification",
                    "",
                    1
                ).strip()

                if value:
                    qualification = value

            elif line.startswith("Experience"):
                value = line.replace(
                    "Experience",
                    "",
                    1
                ).strip()

                if value:
                    experience = value

            elif line.startswith("Location"):
                value = line.replace(
                    "Location",
                    "",
                    1
                ).strip()

                if value:
                    location = value

        # ---------------------------------
    # Handle metadata on a single line
    # ---------------------------------

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

    if metadata_text:

        markers = [
            "Job Type",
            "Qualification",
            "Experience",
            "Location",
            "Job Field",
        ]

        values = {}

        for index, marker in enumerate(markers):

            if marker not in metadata_text:
                continue

            start = (
                metadata_text.find(marker)
                + len(marker)
            )

            if index + 1 < len(markers):

                next_marker = markers[index + 1]

                end = metadata_text.find(
                    next_marker,
                    start
                )

                if end == -1:
                    value = metadata_text[start:]
                else:
                    value = metadata_text[start:end]

            else:
                value = metadata_text[start:]

            values[marker] = value.strip()

        job_type = values.get(
            "Job Type",
            job_type
        )

        qualification = values.get(
            "Qualification",
            qualification
        )

        experience = values.get(
            "Experience",
            experience
        )

        location = values.get(
            "Location",
            location
        )
    # ---------------------------------
    # Extract company
    # ---------------------------------

    for line in lines:

        if line.startswith("View Jobs at "):

            company = line.replace(
                "View Jobs at ",
                "",
                1
            ).strip()

            break

    # ---------------------------------
    # Find the actual job content
    # ---------------------------------

    description_start = None

    for i, line in enumerate(lines):

        if (
            line == "Duties and Responsibilities"
            or line == "Qualifications and Experience"
            or line == "Job Description"
        ):
            description_start = i
            break

    if description_start is not None:

        description_lines = lines[
            description_start:
        ]

        description = "\n".join(
            description_lines
        )

    else:
        description = ""

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
    """Collect job URLs from a public listing page."""

    soup = get_page(url)

    jobs = []

    for heading in soup.find_all("h2"):

        link = heading.find("a")

        if not link:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        href = link.get("href")

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

    return jobs


if __name__ == "__main__":

    listing_url = (
        "https://www.myjobmag.co.ke/"
        "jobs-by-title/developer-python"
    )

    print("Collecting job listings...\n")

    jobs = collect_jobs(listing_url)

    print(f"Found {len(jobs)} jobs\n")

    if jobs:

        first_job = jobs[0]

        print("Fetching first job:")
        print(first_job["title"])
        print(first_job["url"])
        print()

        details = get_job_details(
            first_job["url"]
        )

        print("JOB DETAILS")
        print("===========")

        print(f"Title: {details['title']}")
        print(f"Company: {details['company']}")
        print(f"Location: {details['location']}")
        print(f"Job Type: {details['job_type']}")
        print(f"Qualification: {details['qualification']}")
        print(f"Experience: {details['experience']}")
        print(f"Posted: {details['posted']}")
        print(f"Deadline: {details['deadline']}")
        print(f"URL: {details['url']}")

        print("\nDESCRIPTION")
        print("===========")

        print(
            details["description"][:5000]
        )