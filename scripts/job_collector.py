
"""
Job collection coordinator.

Collects jobs from all configured job sources,
combines them, and removes duplicate listings.
"""

from scripts.sources.myjobmag import (
    collect_jobs as collect_myjobmag_jobs,
    get_job_details as get_myjobmag_details,
)

from scripts.sources.brighter_monday import (
    collect_jobs as collect_brightermonday_jobs,
    get_job_details as get_brightermonday_details,
)


# ============================================================
# MYJOBMAG
# ============================================================

MYJOBMAG_URLS = [
    (
        "https://www.myjobmag.co.ke/"
        "jobs-by-title/developer-python"
    ),
]


# ============================================================
# BRIGHTERMONDAY
# ============================================================

BRIGHTERMONDAY_URLS = [
    "https://www.brightermonday.co.ke/jobs"
]


# ============================================================
# COLLECT MYJOBMAG
# ============================================================

def collect_myjobmag():
    """
    Collect and fully extract jobs from MyJobMag.
    """

    jobs = []

    for listing_url in MYJOBMAG_URLS:

        try:

            listings = collect_myjobmag_jobs(
                listing_url
            )

        except Exception as error:

            print(
                f"   ⚠ Failed to collect "
                f"MyJobMag listings: {error}"
            )

            continue

        for listing in listings:

            try:

                details = get_myjobmag_details(
                    listing["url"]
                )

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


# ============================================================
# COLLECT BRIGHTERMONDAY
# ============================================================

def collect_brightermonday():
    """
    Collect and fully extract jobs from BrighterMonday.

    BrighterMonday's collector may already have fetched
    complete job details for some listings. When those
    details are available, reuse them instead of making
    another HTTP request.
    """

    jobs = []

    for listing_url in BRIGHTERMONDAY_URLS:

        try:

            listings = collect_brightermonday_jobs(
                listing_url
            )

        except Exception as error:

            print(
                f"   ⚠ Failed to collect "
                f"BrighterMonday listings: {error}"
            )

            continue

        for listing in listings:

            try:

                # ------------------------------------------------
                # Reuse details if the BrighterMonday collector
                # already downloaded the job page.
                # ------------------------------------------------

                details = listing.get(
                    "details"
                )

                if details:

                    details["source"] = "BrighterMonday"

                    jobs.append(
                        details
                    )

                    continue

                # ------------------------------------------------
                # Otherwise fetch the job details normally.
                # ------------------------------------------------

                details = get_brightermonday_details(
                    listing["url"]
                )

                details["source"] = "BrighterMonday"

                jobs.append(
                    details
                )

            except Exception as error:

                print(
                    f"   ⚠ Failed to fetch "
                    f"{listing['url']}: {error}"
                )

    return jobs


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_jobs(jobs):
    """
    Remove duplicate jobs based primarily on URL.

    A URL uniquely identifies a listing on the source.
    """

    unique_jobs = []

    seen_urls = set()

    for job in jobs:

        url = job.get(
            "url",
            ""
        ).strip()

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        unique_jobs.append(
            job
        )

    return unique_jobs


# ============================================================
# COLLECT ALL SOURCES
# ============================================================

def collect_all_jobs():
    """
    Collect jobs from all configured sources,
    combine them, and remove duplicates.
    """

    all_jobs = []

    # ========================================================
    # MYJOBMAG
    # ========================================================

    print(
        "Collecting from MyJobMag..."
    )

    myjobmag_jobs = collect_myjobmag()

    print(
        f"   Found {len(myjobmag_jobs)} jobs"
    )

    all_jobs.extend(
        myjobmag_jobs
    )

    # ========================================================
    # BRIGHTERMONDAY
    # ========================================================

    print()

    print(
        "Collecting from BrighterMonday..."
    )

    brightermonday_jobs = collect_brightermonday()

    print(
        f"   Found {len(brightermonday_jobs)} jobs"
    )

    all_jobs.extend(
        brightermonday_jobs
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique_jobs = remove_duplicate_jobs(
        all_jobs
    )

    # ========================================================
    # REPORT DUPLICATES
    # ========================================================

    duplicate_count = (
        len(all_jobs)
        - len(unique_jobs)
    )

    if duplicate_count > 0:

        print(
            f"   Removed {duplicate_count} "
            f"duplicate jobs"
        )

    return unique_jobs


# ============================================================
# TEST
# ============================================================

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

    print()

    for index, job in enumerate(
        jobs,
        start=1
    ):

        print(
            f"{index}. "
            f"{job.get('title', '')} "
            f"at "
            f"{job.get('company', '')} "
            f"[{job.get('source', '')}]"
        )

