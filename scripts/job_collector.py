import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.myjobmag.co.ke"


def get_page(url):
    """Download a public MyJobMag page."""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def collect_jobs(url):
    """Collect job listings from a public MyJobMag listing page."""

    soup = get_page(url)

    jobs = []

    # MyJobMag job listings
    for article in soup.select("li.job-list"):

        link = article.select_one("h2 a")

        if not link:
            continue

        title = link.get_text(
            " ",
            strip=True
        )

        job_url = urljoin(
            BASE_URL,
            link.get("href", "")
        )

        text = article.get_text(
            " ",
            strip=True
        )

        jobs.append({
            "title": title,
            "url": job_url,
            "summary": text,
        })

    return jobs


if __name__ == "__main__":

    url = (
        "https://www.myjobmag.co.ke/"
        "jobs-by-title/developer-python"
    )

    jobs = collect_jobs(url)

    print(f"\nFound {len(jobs)} jobs\n")

    for job in jobs:
        print(job["title"])
        print(job["url"])
        print()