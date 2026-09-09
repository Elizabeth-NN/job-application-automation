from scripts.job_collector import collect_jobs, get_job_details
from scripts.job_matcher import calculate_match


LISTING_URL = (
    "https://www.myjobmag.co.ke/"
    "jobs-by-title/developer-python"
)


def run_job_search():
    """Collect, match, and display jobs."""

    print("=" * 60)
    print("AUTOMATED JOB SEARCH")
    print("=" * 60)
    print()

    # --------------------------------
    # 1. Collect job listings
    # --------------------------------

    print("Collecting jobs...\n")

    jobs = collect_jobs(LISTING_URL)

    print(f"Found {len(jobs)} jobs\n")

    results = []

    # --------------------------------
    # 2. Process each job
    # --------------------------------

    for index, job in enumerate(jobs, start=1):

        print(
            f"[{index}/{len(jobs)}] "
            f"Processing: {job['title']}"
        )

        try:

            details = get_job_details(
                job["url"]
            )

            match = calculate_match(
                details["title"],
                details["description"]
            )

            result = {
                **details,
                **match
            }

            results.append(result)

        except Exception as error:

            print(
                f"  ERROR: {error}"
            )

    # --------------------------------
    # 3. Sort by match score
    # --------------------------------

    results.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    # --------------------------------
    # 4. Display results
    # --------------------------------

    print()
    print("=" * 60)
    print("JOB MATCH RESULTS")
    print("=" * 60)
    print()

    for index, job in enumerate(
        results,
        start=1
    ):

        print(
            f"{index}. "
            f"{job['score']}% — "
            f"{job['title']}"
        )

        print(
            f"   Company: {job['company']}"
        )

        print(
            f"   Category: {job['category']}"
        )

        if job["matching_skills"]:

            print(
                "   Matching skills: "
                + ", ".join(
                    job["matching_skills"]
                )
            )

        if job["warnings"]:

            for warning in job["warnings"]:

                print(
                    f"   ⚠ {warning}"
                )

        print(
            f"   URL: {job['url']}"
        )

        print()


if __name__ == "__main__":
    run_job_search()