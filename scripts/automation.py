
"""
Main job-search automation pipeline.

Pipeline:

    MyJobMag + BrighterMonday
            ↓
      Collect job links
            ↓
      Inspect jobs with Playwright
            ↓
      Match jobs against candidate profile
            ↓
      Save results to job tracker
            ↓
      Identify APPLY jobs

This module does NOT submit applications.
"""

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)

from scripts.browser.myjobmag import (
    MYJOBMAG_URL,
    collect_job_links as collect_myjobmag_job_links,
    inspect_job as inspect_myjobmag_job,
)

from scripts.browser.brighter_monday import (
    collect_job_links as collect_brightermonday_job_links,
    get_job_details as inspect_brightermonday_job,
)

from scripts.job_matcher import calculate_match
from scripts.job_tracker import save_job


# ============================================================
# SETTINGS
# ============================================================

MAX_JOBS = 3

ENABLE_MYJOBMAG = True
ENABLE_BRIGHTERMONDAY = True


# ============================================================
# HELPERS
# ============================================================

def get_page_text(page):
    """Safely extract visible text from the current page."""

    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def get_job_title(page, fallback_title=""):
    """Try to obtain the actual job title from the page."""

    try:
        headings = page.locator("h1, h2").all()
    except Exception:
        headings = []

    for heading in headings:
        try:
            text = heading.inner_text().strip()

            if text:
                return text

        except Exception:
            continue

    return fallback_title


def should_prepare_application(match_result):
    """Return True only when the matcher recommends APPLY."""

    recommendation = match_result.get(
        "recommendation",
        "",
    )

    return str(recommendation).upper() == "APPLY"


def normalize_job(job):
    """
    Make sure jobs from different sources have the same
    basic fields.
    """

    normalized = dict(job)

    fields = [
        "title",
        "company",
        "location",
        "job_type",
        "qualification",
        "experience_level",
        "experience_length",
        "experience",
        "posted",
        "deadline",
        "description",
        "url",
        "application_method",
        "application_url",
        "application_email",
        "application_subject",
        "source",
    ]

    for field in fields:
        normalized.setdefault(field, "")

    return normalized


def build_tracker_record(
    job,
    match_result,
    application,
):
    """Build a record compatible with the job tracker."""

    return {
        "Job Title": job.get("title", ""),
        "Company": job.get("company", ""),
        "Location": job.get("location", ""),
        "Posted": job.get("posted", ""),
        "Deadline": job.get("deadline", ""),
        "URL": job.get("url", ""),

        "Score": match_result.get("score", 0),
        "Category": match_result.get("category", ""),
        "Recommendation": match_result.get(
            "recommendation",
            "",
        ),

        "Role Match": ", ".join(
            match_result.get(
                "role_matches",
                [],
            )
        ),

        "Matching Skills": ", ".join(
            match_result.get(
                "matching_skills",
                [],
            )
        ),

        "Missing Skills": ", ".join(
            match_result.get(
                "missing_skills",
                [],
            )
        ),

        "Warnings": " | ".join(
            match_result.get(
                "warnings",
                [],
            )
        ),

        "Application Method": application.get(
            "method",
            "unknown",
        ),

        "Application Email": application.get(
            "email",
            "",
        ),

        "Application Subject": application.get(
            "subject",
            "",
        ),

        "Application URL": application.get(
            "url",
            "",
        ),

        "Application Status": "Not Applied",
        "Review Decision": "",
        "CV Version": "",
        "Cover Letter": "",
        "Notes": "",
    }


# ============================================================
# SOURCE INSPECTION
# ============================================================

def inspect_collected_job(page, job):
    """
    Inspect a job using the browser layer belonging to its source.
    """

    source = str(
        job.get(
            "source",
            "",
        )
    ).lower()

    # --------------------------------------------------------
    # MyJobMag
    # --------------------------------------------------------

    if source == "myjobmag":

        return inspect_myjobmag_job(
            page,
            job["url"],
        )

    # --------------------------------------------------------
    # BrighterMonday
    # --------------------------------------------------------

    if source == "brightermonday":

        details = inspect_brightermonday_job(
            page,
            job,
        )

        if not details:
            return None

        application = {
            "method": details.get(
                "application_method",
                "brightermonday",
            ),

            "email": details.get(
                "application_email",
                "",
            ),

            "subject": details.get(
                "application_subject",
                "",
            ),

            "url": details.get(
                "application_url",
                "",
            ),
        }

        return {
            "title": details.get(
                "title",
                job.get(
                    "title",
                    "",
                ),
            ),

            "company": details.get(
                "company",
                "",
            ),

            "location": details.get(
                "location",
                "",
            ),

            "job_type": details.get(
                "job_type",
                "",
            ),

            "qualification": details.get(
                "qualification",
                "",
            ),

            "experience_level": details.get(
                "experience_level",
                "",
            ),

            "experience_length": details.get(
                "experience_length",
                "",
            ),

            "experience": details.get(
                "experience",
                "",
            ),

            "posted": details.get(
                "posted",
                "",
            ),

            "deadline": details.get(
                "deadline",
                "",
            ),

            "description": details.get(
                "description",
                "",
            ),

            "application": application,
        }

    raise ValueError(
        f"Unsupported job source: {source}"
    )


# ============================================================
# PROCESS ONE JOB
# ============================================================

def process_job(page, job):
    """
    Inspect, match and save one job.

    No application is submitted.
    """

    job = normalize_job(job)

    source = str(
        job.get(
            "source",
            "unknown",
        )
    ).lower()

    print()
    print("=" * 70)
    print("PROCESSING JOB")
    print("=" * 70)

    print(
        f"Source: {source}"
    )

    print(
        f"Title: {job.get('title', 'Unknown')}"
    )

    print(
        f"URL: {job.get('url', '')}"
    )

    try:

        # ----------------------------------------------------
        # 1. INSPECT
        # ----------------------------------------------------

        inspection = inspect_collected_job(
            page,
            job,
        )

        if not inspection:

            print()
            print(
                "✗ Unable to inspect job."
            )

            return {
                "success": False,
                "job": job,
                "error": "Job inspection failed.",
                "prepare_application": False,
            }

        # ----------------------------------------------------
        # 2. APPLICATION INFORMATION
        # ----------------------------------------------------

        application = inspection.get(
            "application",
            {},
        )

        if not application:

            application = {
                "method": job.get(
                    "application_method",
                    "unknown",
                ),

                "email": job.get(
                    "application_email",
                    "",
                ),

                "subject": job.get(
                    "application_subject",
                    "",
                ),

                "url": job.get(
                    "application_url",
                    "",
                ),
            }

        print()
        print("APPLICATION METHOD")
        print("-" * 60)

        print(
            "Method:",
            application.get(
                "method",
                "unknown",
            ),
        )

        if application.get("email"):

            print(
                "Email:",
                application["email"],
            )

        if application.get("subject"):

            print(
                "Subject:",
                application["subject"],
            )

        if application.get("url"):

            print(
                "URL:",
                application["url"],
            )

        # ----------------------------------------------------
        # 3. PAGE CONTENT
        # ----------------------------------------------------

        page_text = get_page_text(page)

        actual_title = (
            inspection.get(
                "title",
                "",
            )
            or get_job_title(
                page,
                job.get(
                    "title",
                    "",
                ),
            )
        )

        print()
        print(
            f"Actual title: {actual_title}"
        )

        # ----------------------------------------------------
        # 4. MATCH
        # ----------------------------------------------------

        match_result = calculate_match(
            actual_title,
            page_text,
        )

        print()
        print(
            f"Match score: "
            f"{match_result.get('score', 0)}%"
        )

        print(
            f"Category: "
            f"{match_result.get('category', '')}"
        )

        print(
            f"Recommendation: "
            f"{match_result.get('recommendation', '')}"
        )

        print()
        print(
            "Matching skills:",
            ", ".join(
                match_result.get(
                    "matching_skills",
                    [],
                )
            )
            or "None",
        )

        print(
            "Missing skills:",
            ", ".join(
                match_result.get(
                    "missing_skills",
                    [],
                )
            )
            or "None",
        )

        warnings = match_result.get(
            "warnings",
            [],
        )

        if warnings:

            print(
                "Warnings:",
                " | ".join(warnings),
            )

        # ----------------------------------------------------
        # 5. APPLICATION PREPARATION
        # ----------------------------------------------------

        prepare_application = (
            should_prepare_application(
                match_result
            )
        )

        print()

        if prepare_application:

            print(
                "Application preparation: READY"
            )

        else:

            print(
                "Application preparation: "
                "NOT SELECTED"
            )

        # ----------------------------------------------------
        # 6. PREPARE JOB FOR TRACKER
        # ----------------------------------------------------

        job_for_tracker = dict(job)

        job_for_tracker["title"] = (
            actual_title
        )

        fields_from_inspection = [
            "company",
            "location",
            "job_type",
            "qualification",
            "experience_level",
            "experience_length",
            "experience",
            "posted",
            "deadline",
            "description",
        ]

        for field in fields_from_inspection:

            value = inspection.get(
                field,
                "",
            )

            if value:
                job_for_tracker[field] = value

        job_for_tracker[
            "application_method"
        ] = application.get(
            "method",
            "",
        )

        job_for_tracker[
            "application_email"
        ] = application.get(
            "email",
            "",
        )

        job_for_tracker[
            "application_subject"
        ] = application.get(
            "subject",
            "",
        )

        job_for_tracker[
            "application_url"
        ] = application.get(
            "url",
            "",
        )

        # ----------------------------------------------------
        # 7. BUILD TRACKER RECORD
        # ----------------------------------------------------

        tracker_record = build_tracker_record(
            job_for_tracker,
            match_result,
            application,
        )

        # ----------------------------------------------------
        # 8. SAVE
        # ----------------------------------------------------

        saved = save_job(
            tracker_record,
            match_result,
        )

        print()

        if saved:

            print(
                "✓ Job saved to tracker."
            )

        else:

            print(
                "Already in tracker."
            )

        # ----------------------------------------------------
        # 9. RETURN
        # ----------------------------------------------------

        return {
            "success": True,
            "job": job_for_tracker,
            "match": match_result,
            "application": application,
            "prepare_application": (
                prepare_application
            ),
            "saved": saved,
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
            "prepare_application": False,
        }


# ============================================================
# MYJOBMAG COLLECTION
# ============================================================

def collect_myjobmag_jobs(page):
    """Collect MyJobMag jobs using the shared browser page."""

    print()
    print("=" * 70)
    print("MYJOBMAG COLLECTION")
    print("=" * 70)

    print()
    print("Opening MyJobMag...")

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
            "MyJobMag page did not reach "
            "domcontentloaded. Continuing."
        )

    if response:

        print(
            f"Status: {response.status}"
        )

    print(
        f"Title: {page.title()}"
    )

    print()
    print(
        "Collecting MyJobMag job links..."
    )

    jobs = collect_myjobmag_job_links(
        page
    )

    normalized_jobs = []

    for job in jobs:

        normalized = normalize_job(
            job
        )

        normalized["source"] = "myjobmag"

        normalized_jobs.append(
            normalized
        )

    print()
    print(
        f"MyJobMag jobs found: "
        f"{len(normalized_jobs)}"
    )

    return normalized_jobs


# ============================================================
# BRIGHTERMONDAY COLLECTION
# ============================================================

def collect_brightermonday_jobs(page):
    """
    Collect BrighterMonday jobs using the existing shared
    Playwright page.

    We intentionally DO NOT call:

        brighter_monday.collect_jobs()

    because that function creates another sync_playwright()
    instance and another browser.

    Instead we use its page-level functions directly.
    """

    print()
    print("=" * 70)
    print("BRIGHTERMONDAY COLLECTION")
    print("=" * 70)

    print()
    print(
        "Collecting BrighterMonday job links..."
    )

    job_links = collect_brightermonday_job_links(
        page
    )

    print()
    print(
        f"BrighterMonday technology jobs found: "
        f"{len(job_links)}"
    )

    if not job_links:

        print(
            "No BrighterMonday jobs found."
        )

        return []

    jobs = []

    print()
    print(
        "Inspecting BrighterMonday jobs..."
    )

    for index, job in enumerate(
        job_links,
        start=1,
    ):

        print()
        print(
            f"BrighterMonday job "
            f"{index}/{len(job_links)}"
        )

        try:

            details = inspect_brightermonday_job(
                page,
                job,
            )

            if not details:

                print(
                    "Could not retrieve job details."
                )

                continue

            details = normalize_job(
                details
            )

            details["source"] = (
                "brightermonday"
            )

            jobs.append(
                details
            )

        except Exception as error:

            print(
                "BrighterMonday job error:",
                error,
            )

    print()
    print(
        "BrighterMonday details collected:",
        len(jobs),
    )

    return jobs


# ============================================================
# MAIN AUTOMATION
# ============================================================

def run_automation():
    """
    Run the complete job-search automation pipeline.
    """

    print("=" * 70)
    print("JOB APPLICATION AUTOMATION")
    print("=" * 70)

    print()
    print("Pipeline:")
    print("MyJobMag + BrighterMonday")
    print("        ↓")
    print("Collect → Inspect → Match → Track")
    print("        → Application Preparation")

    print()
    print(
        "Automatic application submission: DISABLED"
    )

    print()
    print(
        "Starting shared browser..."
    )

    playwright = None
    browser = None
    context = None

    all_jobs = []
    results = []

    try:

        # ----------------------------------------------------
        # START SHARED BROWSER
        # ----------------------------------------------------

        playwright, browser, context = (
            launch_browser(
                headless=False
            )
        )

        page = context.new_page()

        # ----------------------------------------------------
        # MYJOBMAG
        # ----------------------------------------------------

        myjobmag_jobs = []

        if ENABLE_MYJOBMAG:

            try:

                myjobmag_jobs = (
                    collect_myjobmag_jobs(
                        page
                    )
                )

                all_jobs.extend(
                    myjobmag_jobs
                )

            except Exception as error:

                print()
                print(
                    "MyJobMag collection error:",
                    error,
                )

        # ----------------------------------------------------
        # BRIGHTERMONDAY
        # ----------------------------------------------------

        brightermonday_jobs = []

        if ENABLE_BRIGHTERMONDAY:

            try:

                brightermonday_jobs = (
                    collect_brightermonday_jobs(
                        page
                    )
                )

                all_jobs.extend(
                    brightermonday_jobs
                )

            except Exception as error:

                print()
                print(
                    "BrighterMonday collection error:",
                    error,
                )

        # ----------------------------------------------------
        # COLLECTION SUMMARY
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("JOB COLLECTION SUMMARY")
        print("=" * 70)

        print()
        print(
            f"MyJobMag jobs: "
            f"{len(myjobmag_jobs)}"
        )

        print(
            f"BrighterMonday jobs: "
            f"{len(brightermonday_jobs)}"
        )

        print(
            f"Total collected jobs: "
            f"{len(all_jobs)}"
        )

        if not all_jobs:

            print()
            print(
                "No jobs collected."
            )

            return

        # ----------------------------------------------------
        # TEST LIMIT
        # ----------------------------------------------------

        jobs_to_process = list(
            all_jobs
        )

        if MAX_JOBS is not None:

            jobs_to_process = (
                jobs_to_process[:MAX_JOBS]
            )

            print()
            print(
                f"Testing with first "
                f"{len(jobs_to_process)} jobs."
            )

        # ----------------------------------------------------
        # PROCESS
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("PROCESSING COLLECTED JOBS")
        print("=" * 70)

        for index, job in enumerate(
            jobs_to_process,
            start=1,
        ):

            print()
            print(
                f"[{index}/{len(jobs_to_process)}]"
            )

            result = process_job(
                page,
                job,
            )

            results.append(
                result
            )

        # ----------------------------------------------------
        # SUMMARY COUNTERS
        # ----------------------------------------------------

        successful = sum(
            1
            for result in results
            if result.get("success")
        )

        failed = (
            len(results)
            - successful
        )

        apply_count = 0
        review_count = 0
        skip_count = 0
        preparation_count = 0

        myjobmag_processed = 0
        brightermonday_processed = 0

        for result in results:

            if not result.get(
                "success"
            ):
                continue

            source = str(
                result.get(
                    "job",
                    {},
                ).get(
                    "source",
                    "",
                )
            ).lower()

            if source == "myjobmag":

                myjobmag_processed += 1

            elif source == "brightermonday":

                brightermonday_processed += 1

            recommendation = str(
                result.get(
                    "match",
                    {},
                ).get(
                    "recommendation",
                    "",
                )
            ).upper()

            if recommendation == "APPLY":

                apply_count += 1

            elif recommendation == "REVIEW":

                review_count += 1

            elif recommendation == "SKIP":

                skip_count += 1

            if result.get(
                "prepare_application",
                False,
            ):

                preparation_count += 1

        # ----------------------------------------------------
        # FINAL SUMMARY
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("AUTOMATION COMPLETE")
        print("=" * 70)

        print()

        print(
            f"Jobs collected: "
            f"{len(all_jobs)}"
        )

        print(
            f"Jobs processed: "
            f"{len(results)}"
        )

        print()

        print(
            f"MyJobMag processed: "
            f"{myjobmag_processed}"
        )

        print(
            f"BrighterMonday processed: "
            f"{brightermonday_processed}"
        )

        print()

        print(
            f"Successful: "
            f"{successful}"
        )

        print(
            f"Failed: "
            f"{failed}"
        )

        print()

        print(
            f"APPLY: "
            f"{apply_count}"
        )

        print(
            f"REVIEW: "
            f"{review_count}"
        )

        print(
            f"SKIP: "
            f"{skip_count}"
        )

        print()

        print(
            "Ready for application preparation: "
            f"{preparation_count}"
        )

        print()

        print(
            "Automatic application submission: "
            "DISABLED"
        )

        print(
            "Results saved to the job tracker."
        )

    except Exception as error:

        print()
        print("=" * 70)
        print(
            f"AUTOMATION ERROR: {error}"
        )
        print("=" * 70)

    finally:

        if browser and playwright:

            print()
            print(
                "Closing browser..."
            )

            close_browser(
                playwright,
                browser,
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_automation()
