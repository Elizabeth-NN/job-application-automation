from scripts.job_collector import collect_all_jobs
from scripts.job_matcher import calculate_match
from scripts.job_tracker import save_job


def run_job_search():
    """Collect, match, save, and display jobs."""

    print("=" * 60)
    print("AUTOMATED JOB SEARCH")
    print("=" * 60)
    print()

    # ========================================================
    # 1. COLLECT JOBS FROM ALL SOURCES
    # ========================================================

    print("Collecting jobs...\n")

    jobs = collect_all_jobs()

    print()
    print(f"Found {len(jobs)} jobs\n")

    results = []

    # ========================================================
    # 2. PROCESS EACH JOB
    # ========================================================

    for index, job in enumerate(
        jobs,
        start=1
    ):

        print(
            f"[{index}/{len(jobs)}] "
            f"Processing: "
            f"{job['title']}"
        )

        try:

            # ------------------------------------------------
            # Job details are already extracted by the
            # source collector.
            # ------------------------------------------------

            match = calculate_match(
                job["title"],
                job["description"]
            )

            result = {
                **job,
                **match
            }

            results.append(
                result
            )

            # ------------------------------------------------
            # Save job to Excel tracker
            # ------------------------------------------------

            saved = save_job(
                job,
                match
            )

            if saved:

                print(
                    "   ✓ Saved to Excel tracker"
                )

            else:

                print(
                    "   → Already in tracker"
                )

        except Exception as error:

            print(
                f"   ERROR: {error}"
            )

    # ========================================================
    # 3. SORT BY MATCH SCORE
    # ========================================================

    results.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    # ========================================================
    # 4. DISPLAY RESULTS
    # ========================================================

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
            f"{job['title']} "
            f"at "
            f"{job['company']}"
        )

        print(
            f"   Source: "
            f"{job.get('source', 'Unknown')}"
        )

        print(
            f"   Location: "
            f"{job.get('location', '')}"
        )

        print(
            f"   Category: "
            f"{job['category']}"
        )

        print(
            f"   Recommendation: "
            f"{job['recommendation']}"
        )

        # ------------------------------------------------
        # Role matches
        # ------------------------------------------------

        if job["role_matches"]:

            print(
                "   Role match: "
                + ", ".join(
                    job["role_matches"]
                )
            )

        # ------------------------------------------------
        # Matching skills
        # ------------------------------------------------

        if job["matching_skills"]:

            print(
                "   Matching skills: "
                + ", ".join(
                    job["matching_skills"]
                )
            )

        # ------------------------------------------------
        # Missing skills
        # ------------------------------------------------

        if job["missing_skills"]:

            print(
                "   Missing skills: "
                + ", ".join(
                    job["missing_skills"]
                )
            )

        # ------------------------------------------------
        # Warnings
        # ------------------------------------------------

        if job["warnings"]:

            for warning in job["warnings"]:

                print(
                    f"   ⚠ {warning}"
                )

        # ------------------------------------------------
        # URL
        # ------------------------------------------------

        print(
            f"   URL: {job['url']}"
        )

        print()


if __name__ == "__main__":

    run_job_search()