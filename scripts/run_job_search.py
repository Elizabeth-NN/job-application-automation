
"""
Main job search pipeline.

Collects jobs from all configured sources,
matches them against the user's profile,
saves them to the Excel tracker,
and displays ranked results.
"""

from scripts.job_collector import collect_all_jobs
from scripts.job_matcher import calculate_match
from scripts.job_tracker import save_job


def run_job_search():
    """
    Collect, match, save, sort, and display jobs.
    """

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
    print(
        f"Found {len(jobs)} jobs\n"
    )

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
            f"{job.get('title', 'Unknown title')}"
        )

        try:

            # ------------------------------------------------
            # Job details have already been extracted by the
            # individual source scraper.
            # ------------------------------------------------

            title = job.get(
                "title",
                ""
            )

            description = job.get(
                "description",
                ""
            )

            # ------------------------------------------------
            # Calculate match
            # ------------------------------------------------

            match = calculate_match(
                title,
                description
            )

            # ------------------------------------------------
            # Combine job details and match results
            # ------------------------------------------------

            result = {
                **job,
                **match
            }

            results.append(
                result
            )

            # ------------------------------------------------
            # Save to Excel tracker
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
    # 3. SORT RESULTS BY MATCH SCORE
    # ========================================================

    results.sort(
        key=lambda job: job.get(
            "score",
            0
        ),
        reverse=True
    )

    # ========================================================
    # 4. DISPLAY MATCH RESULTS
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
            f"{job.get('score', 0)}% — "
            f"{job.get('title', '')} "
            f"at "
            f"{job.get('company', '')}"
        )

        # ------------------------------------------------
        # Source
        # ------------------------------------------------

        print(
            f"   Source: "
            f"{job.get('source', 'Unknown')}"
        )

        # ------------------------------------------------
        # Location
        # ------------------------------------------------

        print(
            f"   Location: "
            f"{job.get('location', '')}"
        )

        # ------------------------------------------------
        # Category
        # ------------------------------------------------

        print(
            f"   Category: "
            f"{job.get('category', '')}"
        )

        # ------------------------------------------------
        # Recommendation
        # ------------------------------------------------

        print(
            f"   Recommendation: "
            f"{job.get('recommendation', '')}"
        )

        # ------------------------------------------------
        # Role matches
        # ------------------------------------------------

        if job.get(
            "role_matches"
        ):

            print(
                "   Role match: "
                + ", ".join(
                    job["role_matches"]
                )
            )

        # ------------------------------------------------
        # Matching skills
        # ------------------------------------------------

        if job.get(
            "matching_skills"
        ):

            print(
                "   Matching skills: "
                + ", ".join(
                    job["matching_skills"]
                )
            )

        # ------------------------------------------------
        # Missing skills
        # ------------------------------------------------

        if job.get(
            "missing_skills"
        ):

            print(
                "   Missing skills: "
                + ", ".join(
                    job["missing_skills"]
                )
            )

        # ------------------------------------------------
        # Warnings
        # ------------------------------------------------

        if job.get(
            "warnings"
        ):

            for warning in job[
                "warnings"
            ]:

                print(
                    f"   ⚠ {warning}"
                )

        # ------------------------------------------------
        # URL
        # ------------------------------------------------

        print(
            f"   URL: "
            f"{job.get('url', '')}"
        )

        print()


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_job_search()

