"""
Job collection coordinator.

Collects jobs from all configured job sources.
"""

from scripts.sources.myjobmag import (
    collect_jobs as collect_myjobmag_jobs,
    get_job_details as get_myjobmag_details,
)


MYJOBMAG_URLS = [
    (
        "https://www.myjobmag.co.ke/"
        "jobs-by-title/developer-python"
    ),
]


def collect_myjobmag():
    """
    Collect and fully extract jobs from MyJobMag.
    """

    jobs = []

    for listing_url in MYJOBMAG_URLS:

        listings = collect_myjobmag_jobs(
            listing_url
        )

        for listing in listings:

            try:

                details = get_myjobmag_details(
                    listing["url"]
                )

                # Identify the source.
                details["source"] = "MyJobMag"

                jobs.append(
                    details
                )

            except Exception as error:

                print(
                    f"   ⚠ Failed to fetch "
                    f"{listing['url']}: {error}"
                )

    return jobs


def collect_all_jobs():
    """
    Collect jobs from all available sources.
    """

    all_jobs = []

    # ========================================================
    # MYJOBMAG
    # ========================================================

    print("Collecting from MyJobMag...")

    myjobmag_jobs = collect_myjobmag()

    print(
        f"   Found {len(myjobmag_jobs)} jobs"
    )

    all_jobs.extend(
        myjobmag_jobs
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique_jobs = []
    seen_urls = set()

    for job in all_jobs:

        url = job.get(
            "url",
            ""
        )

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        unique_jobs.append(job)

    return unique_jobs


if __name__ == "__main__":

    print("=" * 60)
    print("JOB COLLECTION TEST")
    print("=" * 60)
    print()

    jobs = collect_all_jobs()

    print()
    print("=" * 60)
    print(
        f"TOTAL JOBS: {len(jobs)}"
    )
    print("=" * 60)

    for index, job in enumerate(
        jobs,
        start=1
    ):

        print(
            f"{index}. "
            f"{job.get('title', '')} "
            f"at "
            f"{job.get('company', '')}"
        )