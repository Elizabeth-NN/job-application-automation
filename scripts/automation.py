"""
Main job-search automation pipeline.

Pipeline:

    MyJobMag listing
        ↓
    Collect job links
        ↓
    Inspect each job with Playwright
        ↓
    Match job against candidate profile
        ↓
    Save results to job tracker

This module does NOT submit applications.
It does NOT modify the Streamlit interface.
"""

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)

from scripts.browser.myjobmag import (
    MYJOBMAG_URL,
    collect_job_links,
    inspect_job,
)

from scripts.job_matcher import calculate_match
from scripts.job_tracker import save_job


# ============================================================
# SETTINGS
# ============================================================

# Use a small number while testing.
# Change to None when everything works.
MAX_JOBS = 3


# ============================================================
# HELPERS
# ============================================================

def get_page_text(page):
    """
    Safely extract the visible text from the current page.
    """

    try:

        return page.locator(
            "body"
        ).inner_text()

    except Exception:

        return ""


def get_job_title(
    page,
    fallback_title=""
):
    """
    Try to obtain the actual job title from the job page.
    """

    headings = page.locator(
        "h1, h2"
    ).all()

    for heading in headings:

        try:

            text = heading.inner_text().strip()

            if text:

                return text

        except Exception:

            continue

    return fallback_title


def build_tracker_record(
    job,
    match_result,
    application,
):
    """
    Combine job information, matcher results and
    application information into one tracker record.
    """

    return {

        # ----------------------------------------------------
        # Job information
        # ----------------------------------------------------

        "Job Title": job.get(
            "title",
            ""
        ),

        "Company": job.get(
            "company",
            ""
        ),

        "Location": job.get(
            "location",
            ""
        ),

        "URL": job.get(
            "url",
            ""
        ),

        # ----------------------------------------------------
        # Matcher information
        # ----------------------------------------------------

        "Score": match_result.get(
            "score",
            0
        ),

        "Category": match_result.get(
            "category",
            ""
        ),

        "Recommendation": match_result.get(
            "recommendation",
            ""
        ),

        "Role Match": ", ".join(
            match_result.get(
                "role_matches",
                []
            )
        ),

        "Matching Skills": ", ".join(
            match_result.get(
                "matching_skills",
                []
            )
        ),

        "Missing Skills": ", ".join(
            match_result.get(
                "missing_skills",
                []
            )
        ),

        "Warnings": " | ".join(
            match_result.get(
                "warnings",
                []
            )
        ),

        # ----------------------------------------------------
        # Application information
        # ----------------------------------------------------

        "Application Method": application.get(
            "method",
            "unknown"
        ),

        "Application Email": application.get(
            "email",
            ""
        ),

        "Application Subject": application.get(
            "subject",
            ""
        ),

        "Application URL": application.get(
            "url",
            ""
        ),

        # ----------------------------------------------------
        # Initial status
        # ----------------------------------------------------

        "Application Status": "Not Applied",

        "CV Version": "",

        "Cover Letter": "",

        "Notes": "",
    }


# ============================================================
# PROCESS ONE JOB
# ============================================================

def process_job(
    page,
    job,
):
    """
    Open and process one job.

    Nothing is submitted.
    """

    print()
    print("=" * 70)
    print("PROCESSING JOB")
    print("=" * 70)

    print(
        f"Title: {job.get('title', 'Unknown')}"
    )

    print(
        f"URL: {job.get('url', '')}"
    )

    try:

        # ----------------------------------------------------
        # Inspect job
        # ----------------------------------------------------

        inspection = inspect_job(
            page,
            job["url"],
        )

        # ----------------------------------------------------
        # Get application information
        # ----------------------------------------------------

        application = inspection.get(
            "application",
            {
                "method": "unknown",
                "email": None,
                "subject": None,
                "url": None,
            },
        )

        print()
        print(
            "Application method:",
            application.get(
                "method",
                "unknown",
            )
        )

        if application.get("email"):

            print(
                "Application email:",
                application["email"]
            )

        if application.get("subject"):

            print(
                "Application subject:",
                application["subject"]
            )

        if application.get("url"):

            print(
                "Application URL:",
                application["url"]
            )

        # ----------------------------------------------------
        # Get actual page content
        # ----------------------------------------------------

        page_text = get_page_text(
            page
        )

        actual_title = get_job_title(
            page,
            job.get("title", "")
        )

        # ----------------------------------------------------
        # Match job
        # ----------------------------------------------------

        match_result = calculate_match(
            actual_title,
            page_text,
        )

        print()
        print(
            f"Match score: "
            f"{match_result['score']}%"
        )

        print(
            f"Category: "
            f"{match_result['category']}"
        )

        print(
            f"Recommendation: "
            f"{match_result['recommendation']}"
        )

        print()
        print(
            "Matching skills:",
            ", ".join(
                match_result.get(
                    "matching_skills",
                    []
                )
            )
            or "None"
        )

        print(
            "Missing skills:",
            ", ".join(
                match_result.get(
                    "missing_skills",
                    []
                )
            )
            or "None"
        )

        # ----------------------------------------------------
        # Build tracker record
        # ----------------------------------------------------

        job_for_tracker = dict(
            job
        )

        job_for_tracker["title"] = (
            actual_title
        )

        tracker_record = (
            build_tracker_record(
                job_for_tracker,
                match_result,
                application,
            )
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        save_job(
            tracker_record,
            match_result,
        )

        print()
        print(
            "✓ Job saved to tracker."
        )

        return {
            "success": True,
            "job": job,
            "match": match_result,
            "application": application,
        }

    except Exception as error:

        print()
        print(
            f"✗ Error processing job: {error}"
        )

        return {
            "success": False,
            "job": job,
            "error": str(error),
        }


# ============================================================
# MAIN AUTOMATION
# ============================================================

def run_automation():
    """
    Run the complete MyJobMag automation pipeline.
    """

    print("=" * 70)
    print("JOB APPLICATION AUTOMATION")
    print("=" * 70)

    print()

    print(
        "Pipeline:"
    )

    print(
        "Collect → Inspect → Match → Track"
    )

    print()

    print(
        "Automatic application submission: DISABLED"
    )

    playwright = None
    browser = None

    results = []

    try:

        # ====================================================
        # 1. START BROWSER
        # ====================================================

        playwright, browser, context = (
            launch_browser(
                headless=False
            )
        )

        page = context.new_page()

        # ====================================================
        # 2. OPEN JOB LISTING
        # ====================================================

        print()
        print(
            "Opening MyJobMag..."
        )

        response = page.goto(
            MYJOBMAG_URL,
            wait_until="commit",
            timeout=30000,
        )

        print(
            "MyJobMag navigation started."
        )

        try:

            page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000,
            )

            print(
                "MyJobMag page loaded."
            )

        except Exception:

            print(
                "Page did not reach "
                "domcontentloaded. "
                "Continuing."
            )

        if response:

            print(
                f"Status: {response.status}"
            )

        print(
            f"Title: {page.title()}"
        )

        # ====================================================
        # 3. COLLECT JOB LINKS
        # ====================================================

        print()
        print(
            "Collecting job links..."
        )

        jobs = collect_job_links(
            page
        )

        print()
        print(
            f"Found {len(jobs)} job links."
        )

        if not jobs:

            print(
                "No jobs found."
            )

            return

        # ----------------------------------------------------
        # Limit jobs during testing
        # ----------------------------------------------------

        if MAX_JOBS is not None:

            jobs = jobs[:MAX_JOBS]

            print()
            print(
                f"Testing with first "
                f"{len(jobs)} jobs."
            )

        # ====================================================
        # 4. PROCESS JOBS
        # ====================================================

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            print()
            print(
                f"[{index}/{len(jobs)}]"
            )

            result = process_job(
                page,
                job,
            )

            results.append(
                result
            )

        # ====================================================
        # 5. SUMMARY
        # ====================================================

        successful = sum(
            1
            for result in results
            if result["success"]
        )

        failed = (
            len(results)
            - successful
        )

        apply_count = 0
        review_count = 0
        skip_count = 0

        for result in results:

            if not result["success"]:

                continue

            recommendation = (
                result["match"].get(
                    "recommendation"
                )
            )

            if recommendation == "APPLY":

                apply_count += 1

            elif recommendation == "REVIEW":

                review_count += 1

            elif recommendation == "SKIP":

                skip_count += 1

        print()
        print("=" * 70)
        print("AUTOMATION COMPLETE")
        print("=" * 70)

        print()

        print(
            f"Jobs processed: {len(results)}"
        )

        print(
            f"Successful: {successful}"
        )

        print(
            f"Failed: {failed}"
        )

        print()

        print(
            f"APPLY: {apply_count}"
        )

        print(
            f"REVIEW: {review_count}"
        )

        print(
            f"SKIP: {skip_count}"
        )

        print()

        print(
            "Results saved to the job tracker."
        )

    except Exception as error:

        print()
        print(
            "=" * 70
        )

        print(
            f"AUTOMATION ERROR: {error}"
        )

        print(
            "=" * 70
        )

    finally:

        if browser and playwright:

            close_browser(
                playwright,
                browser,
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_automation()