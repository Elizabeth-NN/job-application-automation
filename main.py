"""
Main entry point for the job application automation system.

Workflow:

    1. Collect jobs from configured sources
    2. Match each job against the candidate profile
    3. Score and categorize each job
    4. Sort jobs by match score
    5. Display the results

Run with:

    python main.py
"""

from scripts.job_collector import collect_all_jobs
from scripts.job_matcher import calculate_match


# ============================================================
# DISPLAY HELPERS
# ============================================================

def print_separator(char="=", length=70):
    """Print a visual separator."""
    print(char * length)


def print_job_result(index, job):
    """
    Display one matched job in a readable format.
    """

    print_separator("-", 70)

    print(
        f"{index}. {job.get('title', 'Unknown title')}"
    )

    print(
        f"   Company:       {job.get('company', 'Unknown')}"
    )

    print(
        f"   Location:      {job.get('location', 'Unknown')}"
    )

    print(
        f"   Source:        {job.get('source', 'Unknown')}"
    )

    print(
        f"   Score:         {job.get('score', 0)}%"
    )

    print(
        f"   Category:      {job.get('category', 'Unknown')}"
    )

    print(
        f"   Recommendation:"
        f" {job.get('recommendation', 'Unknown')}"
    )

    print()

    print(
        f"   Role Score:       "
        f"{job.get('role_score', 0)}/30"
    )

    print(
        f"   Skill Score:      "
        f"{job.get('skill_score', 0)}/35"
    )

    print(
        f"   Experience Score: "
        f"{job.get('experience_score', 0)}/15"
    )

    print(
        f"   Location Score:   "
        f"{job.get('location_score', 0)}/10"
    )

    print(
        f"   Education Score:  "
        f"{job.get('education_score', 0)}/5"
    )

    print(
        f"   Technology Score: "
        f"{job.get('technology_score', 0)}/5"
    )

    print()

    role_matches = job.get(
        "role_matches",
        []
    )

    if role_matches:

        print(
            "   Matching Roles: "
            + ", ".join(role_matches)
        )

    matching_skills = job.get(
        "matching_skills",
        []
    )

    if matching_skills:

        print(
            "   Matching Skills: "
            + ", ".join(matching_skills)
        )

    transferable_skills = job.get(
        "transferable_skills",
        []
    )

    if transferable_skills:

        print(
            "   Transferable Skills: "
            + ", ".join(transferable_skills)
        )

    missing_skills = job.get(
        "missing_skills",
        []
    )

    if missing_skills:

        print(
            "   Missing Skills: "
            + ", ".join(missing_skills)
        )

    outside_technologies = job.get(
        "outside_technologies",
        []
    )

    if outside_technologies:

        print(
            "   Outside Technologies: "
            + ", ".join(outside_technologies)
        )

    experience_level = job.get(
        "experience_level",
        "unknown"
    )

    years_required = job.get(
        "years_required"
    )

    print(
        f"   Experience:      {experience_level}"
    )

    if years_required is not None:

        print(
            f"   Years Required:   "
            f"{years_required}"
        )

    warnings = job.get(
        "warnings",
        []
    )

    if warnings:

        print()

        print("   Warnings:")

        for warning in warnings:

            print(
                f"      ⚠ {warning}"
            )

    print()

    print(
        f"   URL: {job.get('url', '')}"
    )


# ============================================================
# MATCH JOBS
# ============================================================

def match_jobs(jobs):
    """
    Run the job matcher against every collected job.

    Returns:
        list: Jobs containing match information.
    """

    matched_jobs = []

    print()
    print_separator()

    print(
        "MATCHING JOBS AGAINST CANDIDATE PROFILE"
    )

    print_separator()
    print()

    for index, job in enumerate(
        jobs,
        start=1
    ):

        title = job.get(
            "title",
            ""
        )

        description = job.get(
            "description",
            ""
        )

        print(
            f"   Matching {index}/{len(jobs)}: "
            f"{title}"
        )

        try:

            result = calculate_match(
                title,
                description
            )

            # ------------------------------------------------
            # Add matching information to the job itself.
            # ------------------------------------------------

            job.update(
                result
            )

            matched_jobs.append(
                job
            )

            print(
                f"      ↳ "
                f"{result['score']}% "
                f"| "
                f"{result['recommendation']}"
            )

        except Exception as error:

            print(
                f"      ⚠ Matching failed: {error}"
            )

    return matched_jobs


# ============================================================
# SORT JOBS
# ============================================================

def sort_jobs(jobs):
    """
    Sort jobs from highest match score to lowest.
    """

    return sorted(
        jobs,
        key=lambda job: job.get(
            "score",
            0
        ),
        reverse=True
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(jobs):
    """
    Print a summary of the matching results.
    """

    total = len(jobs)

    apply_jobs = [
        job
        for job in jobs
        if job.get("recommendation") == "APPLY"
    ]

    review_jobs = [
        job
        for job in jobs
        if job.get("recommendation") == "REVIEW"
    ]

    skip_jobs = [
        job
        for job in jobs
        if job.get("recommendation") == "SKIP"
    ]

    strong_matches = [
        job
        for job in jobs
        if job.get("category") == "STRONG MATCH"
    ]

    good_matches = [
        job
        for job in jobs
        if job.get("category") == "GOOD MATCH"
    ]

    print()
    print_separator()

    print("MATCHING SUMMARY")

    print_separator()

    print()

    print(
        f"Total jobs:       {total}"
    )

    print(
        f"Strong matches:   {len(strong_matches)}"
    )

    print(
        f"Good matches:     {len(good_matches)}"
    )

    print(
        f"Apply:            {len(apply_jobs)}"
    )

    print(
        f"Review:           {len(review_jobs)}"
    )

    print(
        f"Skip:             {len(skip_jobs)}"
    )


# ============================================================
# MAIN WORKFLOW
# ============================================================

def run():
    """
    Run the complete job-search workflow.
    """

    print_separator()

    print(
        "AUTOMATED JOB SEARCH"
    )

    print_separator()

    print()

    # ========================================================
    # 1. COLLECT JOBS
    # ========================================================

    print(
        "STEP 1: COLLECTING JOBS"
    )

    print_separator("-")

    jobs = collect_all_jobs()

    print()

    print(
        f"Collected {len(jobs)} unique jobs."
    )

    # --------------------------------------------------------
    # Stop if nothing was collected.
    # --------------------------------------------------------

    if not jobs:

        print()

        print(
            "No jobs were collected."
        )

        return

    # ========================================================
    # 2. MATCH JOBS
    # ========================================================

    print()

    print(
        "STEP 2: MATCHING JOBS"
    )

    matched_jobs = match_jobs(
        jobs
    )

    # ========================================================
    # 3. SORT
    # ========================================================

    print()

    print(
        "STEP 3: SORTING JOBS BY MATCH SCORE"
    )

    matched_jobs = sort_jobs(
        matched_jobs
    )

    # ========================================================
    # 4. SUMMARY
    # ========================================================

    print_summary(
        matched_jobs
    )

    # ========================================================
    # 5. DISPLAY RESULTS
    # ========================================================

    print()

    print_separator()

    print(
        "JOB MATCH RESULTS"
    )

    print_separator()

    for index, job in enumerate(
        matched_jobs,
        start=1
    ):

        print_job_result(
            index,
            job
        )

    # ========================================================
    # COMPLETE
    # ========================================================

    print()
    print_separator()

    print(
        "JOB SEARCH COMPLETE"
    )

    print_separator()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run()