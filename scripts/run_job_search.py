"""
Main job search pipeline.

Collects jobs from all configured sources,
matches them against the candidate profile,
saves them to the Excel tracker,
and generates tailored CVs and cover letters
for jobs recommended for application.
"""

from pathlib import Path
import re

from scripts.job_collector import collect_all_jobs
from scripts.job_matcher import calculate_match
from scripts.job_tracker import save_job
from scripts.cv_tailor import tailor_cv
from scripts.cover_letter import save_cover_letter


APPLICATIONS_DIR = Path("applications")


def create_application_directory(job):
    """Create a unique directory for a job application."""

    company = job.get(
        "company",
        "unknown-company"
    )

    title = job.get(
        "title",
        "unknown-job"
    )

    directory_name = f"{company}-{title}"

    directory_name = directory_name.lower()

    directory_name = re.sub(
        r"[^a-z0-9]+",
        "-",
        directory_name
    )

    directory_name = directory_name.strip("-")

    return APPLICATIONS_DIR / directory_name


def generate_application_documents(job, match):
    """Generate the tailored CV and cover letter."""

    application_directory = create_application_directory(
        job
    )

    application_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    # ------------------------------------------------
    # Generate tailored CV
    # ------------------------------------------------

    print(
        "   → Generating tailored CV..."
    )

    cv_file = tailor_cv(
        job,
        application_directory
    )

    print(
        f"   ✓ Tailored CV: {cv_file}"
    )

    # ------------------------------------------------
    # Generate cover letter
    # ------------------------------------------------

    print(
        "   → Generating cover letter..."
    )

    cover_letter_file = save_cover_letter(
        job,
        match,
        application_directory
    )

    print(
        f"   ✓ Cover letter: {cover_letter_file}"
    )

    return (
        application_directory,
        cv_file,
        cover_letter_file
    )


def run_job_search():
    """Collect, match, save, generate documents, and display jobs."""

    print("=" * 60)
    print("AUTOMATED JOB SEARCH")
    print("=" * 60)
    print()

    # ========================================================
    # 1. COLLECT JOBS
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

            title = job.get(
                "title",
                ""
            )

            description = job.get(
                "description",
                ""
            )

            print(
                f"   Company: "
                f"{job.get('company', 'Unknown')}"
            )

            # ------------------------------------------------
            # Calculate match
            # ------------------------------------------------

            match = calculate_match(
                title,
                description
            )

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
            # Combine job and match data
            # ------------------------------------------------

            result = {
                **job,
                **match
            }

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

            # ------------------------------------------------
            # Generate application documents
            #
            # Only APPLY jobs get a CV and cover letter.
            # ------------------------------------------------

            recommendation = (
                match.get(
                    "recommendation",
                    ""
                )
                .strip()
                .upper()
            )

            if recommendation == "APPLY":

                try:

                    (
                        application_directory,
                        cv_file,
                        cover_letter_file
                    ) = generate_application_documents(
                        job,
                        match
                    )

                    result[
                        "application_directory"
                    ] = str(
                        application_directory
                    )

                    result[
                        "cv_file"
                    ] = str(
                        cv_file
                    )

                    result[
                        "cover_letter_file"
                    ] = str(
                        cover_letter_file
                    )

                except Exception as error:

                    print(
                        f"   ✗ Application document error: "
                        f"{error}"
                    )

            results.append(
                result
            )

        except Exception as error:

            print(
                f"   ERROR: {error}"
            )

        print()

    # ========================================================
    # 3. SORT RESULTS BY SCORE
    # ========================================================

    results.sort(
        key=lambda job: job.get(
            "score",
            0
        ),
        reverse=True
    )

    # ========================================================
    # 4. DISPLAY RESULTS
    # ========================================================

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

        if job.get("role_matches"):

            print(
                "   Role match: "
                + ", ".join(
                    job["role_matches"]
                )
            )

        # ------------------------------------------------
        # Matching skills
        # ------------------------------------------------

        if job.get("matching_skills"):

            print(
                "   Matching skills: "
                + ", ".join(
                    job["matching_skills"]
                )
            )

        # ------------------------------------------------
        # Transferable skills
        # ------------------------------------------------

        if job.get("transferable_skills"):

            print(
                "   Transferable skills: "
                + ", ".join(
                    job["transferable_skills"]
                )
            )

        # ------------------------------------------------
        # Missing skills
        # ------------------------------------------------

        if job.get("missing_skills"):

            print(
                "   Missing skills: "
                + ", ".join(
                    job["missing_skills"]
                )
            )

        # ------------------------------------------------
        # Experience
        # ------------------------------------------------

        if job.get("experience"):

            print(
                f"   Experience: "
                f"{job.get('experience')}"
            )

        # ------------------------------------------------
        # Years required
        # ------------------------------------------------

        if job.get("years_required"):

            print(
                f"   Years required: "
                f"{job.get('years_required')}"
            )

        # ------------------------------------------------
        # Warnings
        # ------------------------------------------------

        if job.get("warnings"):

            for warning in job["warnings"]:

                print(
                    f"   ⚠ {warning}"
                )

        # ------------------------------------------------
        # Generated CV
        # ------------------------------------------------

        if job.get("cv_file"):

            print(
                f"   CV: "
                f"{job['cv_file']}"
            )

        # ------------------------------------------------
        # Generated cover letter
        # ------------------------------------------------

        if job.get("cover_letter_file"):

            print(
                f"   Cover letter: "
                f"{job['cover_letter_file']}"
            )

        # ------------------------------------------------
        # Job URL
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