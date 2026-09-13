
from pathlib import Path
from datetime import datetime

import streamlit as st
from openpyxl import load_workbook

from scripts.cv_tailor import (
    tailor_cv,
    create_application_directory,
)

from scripts.cover_letter import (
    save_cover_letter,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRACKER_FILE = BASE_DIR / "data" / "job_tracker.xlsx"


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Job Application Assistant: Elizabeth Njuguna",
    page_icon="💼",
    layout="wide",
)


# ============================================================
# TRACKER FUNCTIONS
# ============================================================

@st.cache_data
def load_jobs():
    """
    Load jobs from the Excel tracker.
    """

    if not TRACKER_FILE.exists():
        return []

    workbook = load_workbook(
        TRACKER_FILE,
        data_only=True,
    )

    if "Jobs" not in workbook.sheetnames:
        workbook.close()
        return []

    sheet = workbook["Jobs"]

    # --------------------------------------------------------
    # Build column mapping
    # --------------------------------------------------------

    columns = {}

    for cell in sheet[1]:
        if cell.value:
            columns[cell.value] = cell.column

    jobs = []

    for row_number in range(2, sheet.max_row + 1):

        def get_value(column_name):
            column = columns.get(column_name)

            if not column:
                return ""

            return sheet.cell(
                row=row_number,
                column=column,
            ).value

        job = {
            "row": row_number,
            "date_found": get_value("Date Found"),
            "title": get_value("Job Title"),
            "company": get_value("Company"),
            "location": get_value("Location"),
            "score": get_value("Score"),
            "category": get_value("Category"),
            "recommendation": get_value("Recommendation"),
            "role_match": get_value("Role Match"),
            "matching_skills": get_value("Matching Skills"),
            "missing_skills": get_value("Missing Skills"),
            "warnings": get_value("Warnings"),
            "posted": get_value("Posted"),
            "deadline": get_value("Deadline"),
            "url": get_value("URL"),
            "application_status": get_value("Application Status"),
            "cv_version": get_value("CV Version"),
            "cover_letter": get_value("Cover Letter"),
            "notes": get_value("Notes"),
        }

        # Ignore completely empty rows.
        if job["title"]:
            jobs.append(job)

    workbook.close()

    return jobs


def clear_job_cache():
    """
    Clear cached tracker data after changing the Excel file.
    """

    load_jobs.clear()


# ============================================================
# APPLICATION TRACKER UPDATE
# ============================================================

def record_application(
    job,
    cv_version,
    cover_letter_used,
    notes,
):
    """
    Record an application in the Excel tracker.
    """

    if not TRACKER_FILE.exists():
        return False, "Tracker file does not exist."

    workbook = load_workbook(
        TRACKER_FILE
    )

    if "Jobs" not in workbook.sheetnames:
        workbook.close()
        return False, "Jobs worksheet does not exist."

    sheet = workbook["Jobs"]

    columns = {}

    for cell in sheet[1]:
        if cell.value:
            columns[cell.value] = cell.column

    row = job["row"]

    # --------------------------------------------------------
    # Application status
    # --------------------------------------------------------

    sheet.cell(
        row=row,
        column=columns["Application Status"],
    ).value = "Applied"

    # --------------------------------------------------------
    # CV version
    # --------------------------------------------------------

    sheet.cell(
        row=row,
        column=columns["CV Version"],
    ).value = cv_version

    # --------------------------------------------------------
    # Cover letter
    # --------------------------------------------------------

    sheet.cell(
        row=row,
        column=columns["Cover Letter"],
    ).value = (
        "Yes"
        if cover_letter_used
        else "No"
    )

    # --------------------------------------------------------
    # Notes
    # --------------------------------------------------------

    existing_notes = sheet.cell(
        row=row,
        column=columns["Notes"],
    ).value

    application_date = datetime.now().strftime(
        "%Y-%m-%d"
    )

    date_note = (
        f"Applied: {application_date}"
    )

    if notes:
        date_note += f" | {notes}"

    if existing_notes:
        final_notes = (
            f"{date_note} | {existing_notes}"
        )
    else:
        final_notes = date_note

    sheet.cell(
        row=row,
        column=columns["Notes"],
    ).value = final_notes

    workbook.save(
        TRACKER_FILE
    )

    workbook.close()

    return True, "Application recorded successfully."


# ============================================================
# JOB HELPERS
# ============================================================

def get_score(job):
    """
    Safely return a numeric job score.
    """

    score = job.get("score")

    try:
        return float(score)
    except (TypeError, ValueError):
        return 0


def is_pending_application(job):
    """
    Determine whether a job still needs application attention.
    """

    return (
        job.get("recommendation")
        in ["APPLY", "REVIEW"]
        and job.get("application_status")
        in ["Not Applied", "To Apply", None, ""]
    )


# ============================================================
# APPLICATION PREPARATION
# ============================================================

def prepare_application(job):
    """
    Generate a tailored CV and cover letter.
    """

    application_directory = create_application_directory(
        job,
        base_directory=BASE_DIR / "applications",
    )

    # --------------------------------------------------------
    # Tailored CV
    # --------------------------------------------------------

    cv_path = tailor_cv(
        job,
        output_directory=application_directory,
    )

    # --------------------------------------------------------
    # Cover letter
    # --------------------------------------------------------

    cover_letter_path = save_cover_letter(
        job,
        output_directory=application_directory,
    )

    return {
        "application_directory": application_directory,
        "cv_path": cv_path,
        "cover_letter_path": cover_letter_path,
    }


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("💼 Job Application Assistant: Elizabeth Njuguna")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Jobs",
        "Applications",
    ],
)


# ============================================================
# LOAD DATA
# ============================================================

jobs = load_jobs()


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.title("💼 Job Application Assistant: Elizabeth Njuguna")

    st.caption(
        "Your job search and application management dashboard."
    )

    st.divider()

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total_jobs = len(jobs)

    jobs_to_apply = sum(
        1
        for job in jobs
        if is_pending_application(job)
        and job.get("recommendation") == "APPLY"
    )

    jobs_to_review = sum(
        1
        for job in jobs
        if is_pending_application(job)
        and job.get("recommendation") == "REVIEW"
    )

    applications = sum(
        1
        for job in jobs
        if job.get("application_status") == "Applied"
    )

    interviews = sum(
        1
        for job in jobs
        if job.get("application_status") == "Interview"
    )

    rejected = sum(
        1
        for job in jobs
        if job.get("application_status") == "Rejected"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Jobs Found",
            total_jobs,
        )

    with col2:
        st.metric(
            "Recommended",
            jobs_to_apply,
        )

    with col3:
        st.metric(
            "To Review",
            jobs_to_review,
        )

    with col4:
        st.metric(
            "Applications",
            applications,
        )

    st.divider()

    # --------------------------------------------------------
    # Application statistics
    # --------------------------------------------------------

    st.subheader("Application Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Interviews",
            interviews,
        )

    with col2:
        st.metric(
            "Rejected",
            rejected,
        )

    with col3:

        if applications > 0:

            interview_rate = (
                interviews / applications
            ) * 100

            st.metric(
                "Interview Rate",
                f"{interview_rate:.1f}%",
            )

        else:

            st.metric(
                "Interview Rate",
                "0%",
            )

    st.divider()

    # --------------------------------------------------------
    # Top jobs
    # --------------------------------------------------------

    st.subheader("Top Matching Jobs")

    pending_jobs = [
        job
        for job in jobs
        if is_pending_application(job)
    ]

    pending_jobs.sort(
        key=get_score,
        reverse=True,
    )

    if pending_jobs:

        for job in pending_jobs[:5]:

            score = get_score(job)

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [5, 3, 1]
                )

                with col1:

                    st.markdown(
                        f"### {job['title']}"
                    )

                    st.write(
                        f"**{job['company']}**"
                    )

                with col2:

                    st.metric(
                        "Match",
                        f"{score:.0f}%",
                    )

                    st.write(
                        f"📍 {job['location']}"
                    )

                with col3:

                    st.write(
                        job["recommendation"]
                    )

    else:

        st.info(
            "There are currently no jobs waiting for review."
        )


# ============================================================
# JOBS PAGE
# ============================================================

elif page == "Jobs":

    st.title("📋 Jobs")

    st.write(
        "Browse and prepare applications for matched jobs."
    )

    st.divider()

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        recommendations = sorted(
            {
                str(job["recommendation"])
                for job in jobs
                if job["recommendation"]
            }
        )

        recommendation_filter = st.selectbox(
            "Recommendation",
            ["All"] + recommendations,
        )

    with col2:

        statuses = sorted(
            {
                str(job["application_status"])
                for job in jobs
                if job["application_status"]
            }
        )

        status_filter = st.selectbox(
            "Application Status",
            ["All"] + statuses,
        )

    with col3:

        search = st.text_input(
            "Search",
            placeholder="Job title or company",
        ).strip().lower()

    # --------------------------------------------------------
    # Apply filters
    # --------------------------------------------------------

    filtered_jobs = []

    for job in jobs:

        if (
            recommendation_filter != "All"
            and job["recommendation"]
            != recommendation_filter
        ):
            continue

        if (
            status_filter != "All"
            and job["application_status"]
            != status_filter
        ):
            continue

        if search:

            searchable_text = (
                f"{job['title']} "
                f"{job['company']}"
            ).lower()

            if search not in searchable_text:
                continue

        filtered_jobs.append(job)

    filtered_jobs.sort(
        key=get_score,
        reverse=True,
    )

    st.write(
        f"Showing **{len(filtered_jobs)}** jobs."
    )

    # --------------------------------------------------------
    # Job list
    # --------------------------------------------------------

    if not filtered_jobs:

        st.info(
            "No jobs match your filters."
        )

    else:

        job_options = {}

        for index, job in enumerate(
            filtered_jobs
        ):

            label = (
                f"{get_score(job):.0f}% — "
                f"{job['title']} — "
                f"{job['company']}"
            )

            job_options[label] = index

        selected_label = st.selectbox(
            "Select a job",
            list(job_options.keys()),
        )

        selected_job = filtered_jobs[
            job_options[selected_label]
        ]

        st.divider()

        # ----------------------------------------------------
        # Job details
        # ----------------------------------------------------

        st.subheader(
            selected_job["title"]
        )

        st.write(
            f"### {selected_job['company']}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Match Score",
                f"{get_score(selected_job):.0f}%",
            )

        with col2:

            st.write("**Location**")
            st.write(
                selected_job["location"]
                or "Not specified"
            )

        with col3:

            st.write("**Recommendation**")
            st.write(
                selected_job["recommendation"]
                or "Not specified"
            )

        # ----------------------------------------------------
        # Details
        # ----------------------------------------------------

        with st.expander(
            "Job Details",
            expanded=True,
        ):

            st.write(
                f"**Role Match:** "
                f"{selected_job['role_match'] or 'Not specified'}"
            )

            st.write(
                f"**Matching Skills:** "
                f"{selected_job['matching_skills'] or 'None'}"
            )

            st.write(
                f"**Missing Skills:** "
                f"{selected_job['missing_skills'] or 'None'}"
            )

            st.write(
                f"**Warnings:** "
                f"{selected_job['warnings'] or 'None'}"
            )

            st.write(
                f"**Posted:** "
                f"{selected_job['posted'] or 'Not specified'}"
            )

            st.write(
                f"**Deadline:** "
                f"{selected_job['deadline'] or 'Not specified'}"
            )

            st.write(
                f"**Application Status:** "
                f"{selected_job['application_status'] or 'Not Applied'}"
            )

        # ----------------------------------------------------
        # Application URL
        # ----------------------------------------------------

        if selected_job["url"]:

            st.link_button(
                "🔗 Open Job Listing",
                selected_job["url"],
            )

        st.divider()

        # ----------------------------------------------------
        # Prepare application
        # ----------------------------------------------------

        can_prepare = (
            selected_job["application_status"]
            not in [
                "Applied",
                "Rejected",
            ]
        )

        if can_prepare:

            if st.button(
                "📄 Prepare Application",
                type="primary",
            ):

                with st.spinner(
                    "Generating tailored CV and cover letter..."
                ):

                    try:

                        application = prepare_application(
                            selected_job
                        )

                        st.session_state[
                            "last_application"
                        ] = application

                        st.success(
                            "Application documents generated successfully."
                        )

                    except Exception as error:

                        st.error(
                            f"Could not generate application: {error}"
                        )

        else:

            st.info(
                "This job has already been processed."
            )


# ============================================================
# APPLICATIONS PAGE
# ============================================================

elif page == "Applications":

    st.title("📁 Applications")

    st.write(
        "Track applications that have been prepared or submitted."
    )

    st.divider()

    applied_jobs = [
        job
        for job in jobs
        if job["application_status"] == "Applied"
    ]

    pending_jobs = [
        job
        for job in jobs
        if is_pending_application(job)
    ]

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Applications Submitted",
            len(applied_jobs),
        )

    with col2:

        st.metric(
            "Still To Apply",
            len(pending_jobs),
        )

    st.divider()

    # --------------------------------------------------------
    # Recently generated application
    # --------------------------------------------------------

    if "last_application" in st.session_state:

        application = st.session_state[
            "last_application"
        ]

        st.subheader(
            "Latest Generated Application"
        )

        st.success(
            "Your application documents are ready for review."
        )

        st.write(
            "**Tailored CV:**"
        )

        st.code(
            str(application["cv_path"]),
            language="text",
        )

        st.write(
            "**Cover Letter:**"
        )

        st.code(
            str(application["cover_letter_path"]),
            language="text",
        )

        st.write(
            "**Application Folder:**"
        )

        st.code(
            str(application["application_directory"]),
            language="text",
        )

        st.divider()

        st.subheader(
            "Record Application"
        )

        cv_version = st.text_input(
            "CV Version",
            value="Tailored CV",
        )

        cover_letter_used = st.checkbox(
            "Cover letter used",
            value=True,
        )

        notes = st.text_area(
            "Notes",
            placeholder="Optional notes about this application...",
        )

        if st.button(
            "✅ Mark as Applied",
            type="primary",
        ):

            # Find the corresponding job using the
            # application directory name.

            directory_name = Path(
                application["application_directory"]
            ).name

            matching_job = None

            for job in jobs:

                expected_directory = create_application_directory(
                    job,
                    base_directory=BASE_DIR / "applications",
                )

                if expected_directory.name == directory_name:

                    matching_job = job
                    break

            if matching_job is None:

                st.error(
                    "Could not identify the job in the tracker."
                )

            else:

                success, message = record_application(
                    matching_job,
                    cv_version,
                    cover_letter_used,
                    notes,
                )

                if success:

                    st.success(
                        message
                    )

                    clear_job_cache()

                    st.session_state.pop(
                        "last_application",
                        None,
                    )

                    st.rerun()

                else:

                    st.error(
                        message
                    )

    # --------------------------------------------------------
    # Submitted applications
    # --------------------------------------------------------

    st.subheader(
        "Submitted Applications"
    )

    if not applied_jobs:

        st.info(
            "No applications have been recorded yet."
        )

    else:

        applied_jobs.sort(
            key=lambda job: get_score(job),
            reverse=True,
        )

        for job in applied_jobs:

            with st.container(border=True):

                st.markdown(
                    f"### {job['title']}"
                )

                st.write(
                    f"**{job['company']}**"
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.write(
                        f"Match: "
                        f"{get_score(job):.0f}%"
                    )

                with col2:

                    st.write(
                        f"CV: "
                        f"{job['cv_version'] or 'Not specified'}"
                    )

                with col3:

                    st.write(
                        f"Cover Letter: "
                        f"{job['cover_letter'] or 'No'}"
                    )

                st.write(
                    f"Notes: "
                    f"{job['notes'] or 'None'}"
                )

