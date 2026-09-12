
"""
Main job search pipeline.

Collects jobs from all configured sources,
matches them against the user's profile,
saves them to the Excel tracker,
generates tailored CVs for APPLY jobs,
and displays ranked results.
"""

from pathlib import Path

from scripts.job_collector import collect_all_jobs
from scripts.job_matcher import calculate_match
from scripts.job_tracker import save_job
from scripts.cv_tailor import tailor_cv


# ============================================================
# APPLICATIONS DIRECTORY
# ============================================================

APPLICATIONS_DIR = Path("applications")


# ============================================================
# APPLICATION FOLDER
# ============================================================

def create_application_directory(job):
    """
    Create a unique directory for a job application.

    Example:

        applications/
            backend-developer-two-max-group/
    """

    title = job.get(
        "title",
        "unknown-job"
    )

    company = job.get(
        "company",
        "unknown-company"
    )

    folder_name = (
        f"{company}-{title}"
        .lower()
    )

    # Replace anything unsafe for a filename.
    import re

    folder_name = re.sub(
        r"[^a-z0-9]+",
        "-",
        folder_name
    )

    folder_name = folder_name.strip("-")

    # Limit folder name length.
    folder_name = folder_name[:100]

    output_directory = (
        APPLICATIONS_DIR
        / folder_name
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return output_directory


# ============================================================
# GENERATE TAILORED CV
# ============================================================

def generate_tailored_cv(job, match):
    """
    Generate a tailored CV only for jobs recommended
    as APPLY.
    """

    if match.get(
        "recommendation"
    ) != "APPLY":

        return None

    try:

        output_directory = (
            create_application_directory(
                job
            )
        )

        cv_file = tailor_cv(
            job,
            output_directory
        )

        return cv_file

    except Exception as error:

        print(
            f"   ⚠ CV tailoring failed: {error}"
        )

        return None


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_job_search():
    """
    Collect, match, save, tailor, sort,
    and display jobs.
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

        title = job.get(
            "title",
            ""
        )

        company = job.get(
            "company",
            "Unknown company"
        )

        print(
            f"[{index}/{len(jobs)}] "
            f"Processing: "
            f"{title}"
        )

        print(
            f"   Company: {company}"
        )

        try:

            # ------------------------------------------------
            # Job description
            # ------------------------------------------------

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
            # Display score
            # ------------------------------------------------

            print(
                f"   Score: "
                f"{match.get('score', 0)}%"
            )

            print(
                f"   Category: "
                f"{match.get('category', '')}"
            )

            print(
                f"   Recommendation: "
                f"{match.get('recommendation', '')}"
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

            # ------------------------------------------------
            # Generate tailored CV
            # ------------------------------------------------

            if match.get(
                "recommendation"
            ) == "APPLY":

                print(
                    "   → Generating tailored CV..."
                )

                cv_file = generate_tailored_cv(
                    job,
                    match
                )

                if cv_file:

                    print(
                        f"   ✓ Tailored CV: "
                        f"{cv_file}"
                    )

            print()

        except Exception as error:

            print(
                f"   ERROR: {error}"
            )

            print()

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
        # Transferable skills
        # ------------------------------------------------

        if job.get(
            "transferable_skills"
        ):

            print(
                "   Transferable skills: "
                + ", ".join(
                    job["transferable_skills"]
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
        # Experience
        # ------------------------------------------------

        if job.get(
            "experience_level"
        ):

            print(
                f"   Experience: "
                f"{job['experience_level']}"
            )

        # ------------------------------------------------
        # Years required
        # ------------------------------------------------

        if job.get(
            "years_required"
        ) is not None:

            print(
                f"   Years required: "
                f"{job['years_required']}"
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

