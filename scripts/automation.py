"""
Main job application automation pipeline.

Pipeline:

    MyJobMag + BrighterMonday
            ↓
        Collect links
            ↓
        Inspect jobs
            ↓
        Match against candidate profile
            ↓
        Save to job tracker
            ↓
        Prepare applications for APPLY jobs

Automatic application submission is disabled.
"""

from pathlib import Path
import re


# ============================================================
# BROWSER
# ============================================================

from scripts.browser.browser import (
    launch_browser,
    close_browser,
)


# ============================================================
# MYJOBMAG BROWSER LAYER
# ============================================================

from scripts.browser.myjobmag import (
    MYJOBMAG_URL,
    collect_job_links as collect_myjobmag_links,
    inspect_job as inspect_myjobmag_job,
)


# ============================================================
# BRIGHTERMONDAY BROWSER LAYER
# ============================================================

from scripts.browser.brighter_monday import (
    collect_job_links as collect_brightermonday_links,
    
)


# ============================================================
# MATCHING
# ============================================================

from scripts.job_matcher import calculate_match


# ============================================================
# TRACKING
# ============================================================

from scripts.job_tracker import save_job


# ============================================================
# APPLICATION PREPARATION
# ============================================================

try:
    from scripts.cv_tailor import tailor_cv
except ImportError:
    tailor_cv = None


try:
    from scripts.cover_letter import save_cover_letter
except ImportError:
    save_cover_letter = None


try:
    from scripts.job_tracker import update_application_documents
except ImportError:
    update_application_documents = None


# ============================================================
# SETTINGS
# ============================================================

# Keep this small while testing.
#
# Set to None when the pipeline is confirmed to be working.
MAX_JOBS = 3


# Automatic application submission is intentionally disabled.
AUTO_SUBMIT_APPLICATIONS = False


# Directory for generated application documents.
APPLICATIONS_DIR = Path("applications")


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value):
    """
    Normalize whitespace.

    Returns an empty string when value is missing.
    """

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def get_job_title(job):
    """
    Safely return the job title.
    """

    return clean_text(
        job.get(
            "title",
            "Unknown title"
        )
    )


def get_job_description(job):
    """
    Safely return the job description.
    """

    return clean_text(
        job.get(
            "description",
            ""
        )
    )


# ============================================================
# APPLICATION PREPARATION HELPERS
# ============================================================

def create_application_directory(job):
    """
    Create a safe directory for one job application.
    """

    company = clean_text(
        job.get(
            "company",
            "unknown-company"
        )
    )

    title = clean_text(
        job.get(
            "title",
            "unknown-job"
        )
    )

    directory_name = (
        f"{company}-{title}"
    )

    directory_name = directory_name.lower()

    directory_name = re.sub(
        r"[^a-z0-9]+",
        "-",
        directory_name
    )

    directory_name = directory_name.strip("-")

    if not directory_name:
        directory_name = "application"

    return (
        APPLICATIONS_DIR
        / directory_name
    )


def prepare_application_documents(
    job,
    match_result
):
    """
    Generate a tailored CV and cover letter
    for a job recommended as APPLY.

    No application is submitted.
    """

    if tailor_cv is None:
        raise RuntimeError(
            "scripts.cv_tailor.tailor_cv could not be imported."
        )

    if save_cover_letter is None:
        raise RuntimeError(
            "scripts.cover_letter.save_cover_letter "
            "could not be imported."
        )

    application_directory = (
        create_application_directory(job)
    )

    application_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print(
        "APPLICATION PREPARATION"
    )
    print("-" * 60)

    print(
        "Generating tailored CV..."
    )

    cv_file = tailor_cv(
        job,
        application_directory
    )

    print(
        f"✓ Tailored CV: {cv_file}"
    )

    print(
        "Generating cover letter..."
    )

    cover_letter_file = save_cover_letter(
        job,
        match_result,
        application_directory
    )

    print(
        f"✓ Cover letter: {cover_letter_file}"
    )

    # --------------------------------------------------------
    # Update tracker with generated documents.
    # --------------------------------------------------------

    if update_application_documents is not None:

        try:

            update_application_documents(
                job.get(
                    "url",
                    ""
                ),
                cv_path=cv_file,
                cover_letter_path=cover_letter_file,
            )

            print(
                "✓ Tracker updated with application documents."
            )

        except Exception as error:

            print(
                "⚠ Could not update tracker with "
                f"application documents: {error}"
            )

    return {
        "application_directory": str(
            application_directory
        ),
        "cv_file": str(
            cv_file
        ),
        "cover_letter_file": str(
            cover_letter_file
        ),
    }


# ============================================================
# DISPLAY MATCH RESULT
# ============================================================

def display_match_result(
    match_result
):
    """
    Display the important matcher results.
    """

    print()
    print(
        "MATCH RESULT"
    )
    print("-" * 60)

    print(
        f"Score: "
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

    role_matches = match_result.get(
        "role_matches",
        []
    )

    matching_skills = match_result.get(
        "matching_skills",
        []
    )

    missing_skills = match_result.get(
        "missing_skills",
        []
    )

    warnings = match_result.get(
        "warnings",
        []
    )

    print(
        "Role matches: "
        + (
            ", ".join(
                str(value)
                for value in role_matches
            )
            if role_matches
            else "None"
        )
    )

    print(
        "Matching skills: "
        + (
            ", ".join(
                str(value)
                for value in matching_skills
            )
            if matching_skills
            else "None"
        )
    )

    print(
        "Missing skills: "
        + (
            ", ".join(
                str(value)
                for value in missing_skills
            )
            if missing_skills
            else "None"
        )
    )

    if warnings:

        print(
            "Warnings:"
        )

        for warning in warnings:

            print(
                f"  ⚠ {warning}"
            )


# ============================================================
# PROCESS ONE JOB
# ============================================================

def process_job(
    page,
    context,
    job
):
    """
    Inspect, match and track one job.

    Parameters
    ----------
    page:
        Shared Playwright page used by MyJobMag.

    context:
        Shared Playwright browser context used by
        BrighterMonday.

    job:
        Job dictionary containing at least:
            source
            title
            url

    Returns
    -------
    dict or None
        Processing result.
    """

    print()
    print(
        "=" * 70
    )
    print(
        "PROCESSING JOB"
    )
    print(
        "=" * 70
    )

    source = clean_text(
        job.get(
            "source",
            ""
        )
    ).lower()

    title = get_job_title(
        job
    )

    url = clean_text(
        job.get(
            "url",
            ""
        )
    )

    print(
        f"Source: {source}"
    )

    print(
        f"Title: {title}"
    )

    print(
        f"URL: {url}"
    )

    if not url:

        print(
            "✗ Job has no URL."
        )

        return None

    # ========================================================
    # INSPECTION
    # ========================================================

    try:

        if source == "myjobmag":

            print()
            print(
                "Inspecting with MyJobMag browser layer..."
            )

            inspected_job = inspect_myjobmag_job(
                page,
                url
            )

        elif source == "brightermonday":

            print()
            print(
                "Inspecting with BrighterMonday "
                "browser layer..."
            )

            inspected_job = (
                inspect_brightermonday_job(
                    context,
                    url,
                    title
                )
            )

        else:

            raise ValueError(
                f"Unsupported job source: {source}"
            )

    except Exception as error:

        print(
            f"✗ Inspection error: {error}"
        )

        raise

    # ========================================================
    # MERGE ORIGINAL + INSPECTED DATA
    # ========================================================

    combined_job = {
        **job,
        **(
            inspected_job
            if inspected_job
            else {}
        ),
    }

    # Preserve the original source.
    combined_job["source"] = (
        job.get(
            "source",
            inspected_job.get(
                "source",
                ""
            )
            if inspected_job
            else ""
        )
    )

    # Preserve the original URL.
    if not combined_job.get("url"):
        combined_job["url"] = url

    # Preserve the original title if inspection
    # failed to extract one.
    if not combined_job.get("title"):
        combined_job["title"] = title

    # ========================================================
    # NORMALIZE COMMON FIELDS
    # ========================================================

    combined_job["title"] = clean_text(
        combined_job.get(
            "title",
            title
        )
    )

    combined_job["company"] = clean_text(
        combined_job.get(
            "company",
            ""
        )
    )

    combined_job["location"] = clean_text(
        combined_job.get(
            "location",
            ""
        )
    )

    combined_job["description"] = clean_text(
        combined_job.get(
            "description",
            ""
        )
    )

    combined_job["url"] = clean_text(
        combined_job.get(
            "url",
            url
        )
    )

    # ========================================================
    # DISPLAY BASIC INFORMATION
    # ========================================================

    print()
    print(
        "INSPECTED JOB"
    )
    print("-" * 60)

    print(
        f"Title: "
        f"{combined_job.get('title', 'Not found')}"
    )

    print(
        f"Company: "
        f"{combined_job.get('company', 'Not found')}"
    )

    print(
        f"Location: "
        f"{combined_job.get('location', 'Not found')}"
    )

    print(
        f"Job Type: "
        f"{combined_job.get('job_type', 'Not found')}"
    )

    print(
        f"Qualification: "
        f"{combined_job.get('qualification', 'Not found')}"
    )

    print(
        f"Experience: "
        f"{combined_job.get('experience', 'Not found')}"
    )

    print(
        f"Posted: "
        f"{combined_job.get('posted', 'Not found')}"
    )

    print(
        f"Deadline: "
        f"{combined_job.get('deadline', 'Not found')}"
    )

    description = combined_job.get(
        "description",
        ""
    )

    print(
        f"Description length: "
        f"{len(description)}"
    )

    # ========================================================
    # MATCH
    # ========================================================

    print()
    print(
        "Calculating job match..."
    )

    match_result = calculate_match(
        combined_job.get(
            "title",
            ""
        ),
        description
    )

    display_match_result(
        match_result
    )

    # ========================================================
    # APPLICATION INFORMATION
    # ========================================================

    application = combined_job.get(
        "application",
        {}
    )

    if not isinstance(
        application,
        dict
    ):
        application = {}

    application_method = (
        combined_job.get(
            "application_method"
        )
        or application.get(
            "method",
            ""
        )
    )

    application_url = (
        combined_job.get(
            "application_url"
        )
        or application.get(
            "url",
            ""
        )
    )

    application_email = (
        combined_job.get(
            "application_email"
        )
        or application.get(
            "email",
            ""
        )
    )

    application_subject = (
        combined_job.get(
            "application_subject"
        )
        or application.get(
            "subject",
            ""
        )
    )

    print()
    print(
        "APPLICATION INFORMATION"
    )
    print("-" * 60)

    print(
        f"Method: "
        f"{application_method or 'Unknown'}"
    )

    if application_url:

        print(
            f"Application URL: "
            f"{application_url}"
        )

    if application_email:

        print(
            f"Application Email: "
            f"{application_email}"
        )

    if application_subject:

        print(
            f"Application Subject: "
            f"{application_subject}"
        )

    # ========================================================
    # SAVE TO TRACKER
    # ========================================================

    print()
    print(
        "Saving to job tracker..."
    )

    saved = save_job(
        combined_job,
        match_result
    )

    if saved:

        print(
            "✓ Job added to tracker."
        )

    else:

        print(
            "✓ Job already exists in tracker."
        )

    # ========================================================
    # APPLICATION PREPARATION
    # ========================================================

    recommendation = clean_text(
        match_result.get(
            "recommendation",
            ""
        )
    ).upper()

    application_result = {}

    if recommendation == "APPLY":

        print()
        print(
            "Job recommendation is APPLY."
        )

        print(
            "Preparing application documents..."
        )

        try:

            application_result = (
                prepare_application_documents(
                    combined_job,
                    match_result
                )
            )

        except Exception as error:

            print(
                "✗ Application preparation failed:"
            )

            print(
                f"  {error}"
            )

    else:

        print()
        print(
            "Application preparation skipped."
        )

        print(
            f"Recommendation: {recommendation}"
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {
        **combined_job,
        **match_result,
        "application_method": (
            application_method
        ),
        "application_url": (
            application_url
        ),
        "application_email": (
            application_email
        ),
        "application_subject": (
            application_subject
        ),
        **application_result,
    }

    return result


# ============================================================
# MAIN AUTOMATION
# ============================================================

def run_automation():
    """
    Run the complete browser-based job automation pipeline.
    """

    print(
        "=" * 70
    )

    print(
        "JOB APPLICATION AUTOMATION"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Pipeline:"
    )

    print(
        "MyJobMag + BrighterMonday"
    )

    print(
        "        ↓"
    )

    print(
        "Collect → Inspect → Match → Track"
    )

    print(
        "        → Application Preparation"
    )

    print()

    print(
        "Automatic application submission: "
        f"{'ENABLED' if AUTO_SUBMIT_APPLICATIONS else 'DISABLED'}"
    )

    # ========================================================
    # START BROWSER
    # ========================================================

    print()
    print(
        "Starting shared browser..."
    )

    playwright = None
    browser = None
    context = None
    page = None

    try:

        playwright, browser, context = (
            launch_browser(
                headless=False
            )
        )

        print(
            "Browser page created."
        )

        # ----------------------------------------------------
        # Shared page for MyJobMag.
        #
        # BrighterMonday creates its own pages from
        # the shared browser context.
        # ----------------------------------------------------

        page = context.new_page()

        # ====================================================
        # COLLECT JOBS
        # ====================================================

        myjobmag_jobs = []
        brightermonday_jobs = []

        # ====================================================
        # MYJOBMAG COLLECTION
        # ====================================================

        print()
        print(
            "=" * 70
        )
        print(
            "MYJOBMAG COLLECTION"
        )
        print(
            "=" * 70
        )

        try:

            print(
                "Opening MyJobMag..."
            )

            response = page.goto(
                MYJOBMAG_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            if response:

                print(
                    f"Status: {response.status}"
                )

            page.wait_for_timeout(
                1500
            )

            myjobmag_jobs = (
                collect_myjobmag_links(
                    page
                )
            )

            for job in myjobmag_jobs:

                job["source"] = (
                    "myjobmag"
                )

            print()
            print(
                "MyJobMag jobs found: "
                f"{len(myjobmag_jobs)}"
            )

        except Exception as error:

            print(
                "MyJobMag collection error: "
                f"{error}"
            )

        # ====================================================
        # BRIGHTERMONDAY COLLECTION
        # ====================================================

        print()
        print(
            "=" * 70
        )
        print(
            "BRIGHTERMONDAY COLLECTION"
        )
        print(
            "=" * 70
        )

        try:

            print(
                "Collecting BrighterMonday "
                "job links..."
            )

            # IMPORTANT:
            #
            # BrighterMonday's current browser layer
            # expects a BrowserContext, NOT a Page.
            #
            # It creates and closes its own pages.
            #

            brightermonday_jobs = (
                collect_brightermonday_links(
                    context
                )
            )

            for job in brightermonday_jobs:

                job["source"] = (
                    "brightermonday"
                )

            print()
            print(
                "BrighterMonday technology "
                "jobs found: "
                f"{len(brightermonday_jobs)}"
            )

        except Exception as error:

            print(
                "BrighterMonday collection error: "
                f"{error}"
            )

        # ====================================================
        # COMBINE
        # ====================================================

        all_jobs = (
            myjobmag_jobs
            + brightermonday_jobs
        )

        print()
        print(
            "=" * 70
        )

        print(
            "JOB COLLECTION SUMMARY"
        )

        print(
            "=" * 70
        )

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

        # ====================================================
        # LIMIT FOR TESTING
        # ====================================================

        if MAX_JOBS is None:

            jobs_to_process = all_jobs

        else:

            jobs_to_process = all_jobs[
                :MAX_JOBS
            ]

        print()
        print(
            "Testing with first "
            f"{len(jobs_to_process)} jobs."
        )

        # ====================================================
        # PROCESS JOBS
        # ====================================================

        print()
        print(
            "=" * 70
        )

        print(
            "PROCESSING COLLECTED JOBS"
        )

        print(
            "=" * 70
        )

        results = []

        successful = 0
        failed = 0

        myjobmag_processed = 0
        brightermonday_processed = 0

        apply_count = 0
        review_count = 0
        skip_count = 0

        preparation_count = 0

        for index, job in enumerate(
            jobs_to_process,
            start=1
        ):

            print()
            print(
                f"[{index}/"
                f"{len(jobs_to_process)}]"
            )

            source = clean_text(
                job.get(
                    "source",
                    ""
                )
            ).lower()

            try:

                result = process_job(
                    page,
                    context,
                    job
                )

                if result is None:

                    failed += 1

                    continue

                results.append(
                    result
                )

                successful += 1

                # --------------------------------------------
                # Source counters
                # --------------------------------------------

                if source == "myjobmag":

                    myjobmag_processed += 1

                elif source == "brightermonday":

                    brightermonday_processed += 1

                # --------------------------------------------
                # Recommendation counters
                # --------------------------------------------

                recommendation = (
                    clean_text(
                        result.get(
                            "recommendation",
                            ""
                        )
                    ).upper()
                )

                if recommendation == "APPLY":

                    apply_count += 1

                elif recommendation == "REVIEW":

                    review_count += 1

                elif recommendation == "SKIP":

                    skip_count += 1

                # --------------------------------------------
                # Application preparation counter
                # --------------------------------------------

                if result.get(
                    "cv_file"
                ) and result.get(
                    "cover_letter_file"
                ):

                    preparation_count += 1

            except Exception as error:

                failed += 1

                print()
                print(
                    "Processing error: "
                    f"{error}"
                )

        # ====================================================
        # FINAL SUMMARY
        # ====================================================

        print()
        print(
            "=" * 70
        )

        print(
            "AUTOMATION COMPLETE"
        )

        print(
            "=" * 70
        )

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
            f"{'ENABLED' if AUTO_SUBMIT_APPLICATIONS else 'DISABLED'}"
        )

        print()

        print(
            "Results saved to the job tracker."
        )

        return results

    except Exception as error:

        print()
        print(
            "=" * 70
        )

        print(
            "AUTOMATION ERROR"
        )

        print(
            "=" * 70
        )

        print(
            error
        )

        return []

    finally:

        # ====================================================
        # CLOSE SHARED PAGE
        # ====================================================

        if page:

            try:

                page.close()

            except Exception:

                pass

        # ====================================================
        # CLOSE BROWSER
        # ====================================================

        if browser and playwright:

            print()
            print(
                "Closing browser..."
            )

            try:

                close_browser(
                    playwright,
                    browser
                )

            except Exception as error:

                print(
                    "Browser close error: "
                    f"{error}"
                )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_automation()