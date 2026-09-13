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

APPLICATIONS_DIR = BASE_DIR / "applications"


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
        in [
            "Not Applied",
            "To Apply",
            None,
            "",
        ]
    )


def format_score(job):
    """
    Return a formatted score.
    """

    return f"{get_score(job):.0f}%"


def get_status(job):
    """
    Return a readable application status.
    """

    status = job.get(
        "application_status"
    )

    if not status:
        return "Not Applied"

    return str(status)


# ============================================================
# APPLICATION PREPARATION
# ============================================================

def prepare_application(job):
    """
    Generate a tailored CV and cover letter.
    """

    application_directory = create_application_directory(
        job,
        base_directory=APPLICATIONS_DIR,
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
        "job_row": job["row"],
        "job_title": job["title"],
        "company": job["company"],
        "application_directory": application_directory,
        "cv_path": cv_path,
        "cover_letter_path": cover_letter_path,
    }


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "💼 Elizabeth Njuguna"
)

st.sidebar.caption(
    "Job Application Assistant"
)

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

    st.title(
        "💼 Elizabeth Njuguna's Job Application Assistant"
    )

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

    st.subheader(
        "Application Overview"
    )

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

    st.subheader(
        "Top Matching Jobs"
    )

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

            with st.container(
                border=True
            ):

                col1, col2, col3 = st.columns(
                    [5, 2, 2]
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
                        "**Recommendation**"
                    )

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

    st.title(
        "📋 Jobs"
    )

    st.write(
        "Browse, filter and prepare applications for matched jobs."
    )

    st.divider()

    # ========================================================
    # FILTERS
    # ========================================================

    st.subheader(
        "Filter Jobs"
    )

    col1, col2, col3, col4 = st.columns(4)

    # --------------------------------------------------------
    # Recommendation filter
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Status filter
    # --------------------------------------------------------

    with col2:

        statuses = sorted(
            {
                get_status(job)
                for job in jobs
            }
        )

        status_filter = st.selectbox(
            "Application Status",
            ["All"] + statuses,
        )

    # --------------------------------------------------------
    # Location filter
    # --------------------------------------------------------

    with col3:

        locations = sorted(
            {
                str(job["location"])
                for job in jobs
                if job["location"]
            }
        )

        location_filter = st.selectbox(
            "Location",
            ["All"] + locations,
        )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    with col4:

        search = st.text_input(
            "Search",
            placeholder="Job title or company",
        ).strip().lower()

    # ========================================================
    # APPLY FILTERS
    # ========================================================

    filtered_jobs = []

    for job in jobs:

        # Recommendation

        if (
            recommendation_filter != "All"
            and job["recommendation"]
            != recommendation_filter
        ):
            continue

        # Application status

        if (
            status_filter != "All"
            and get_status(job)
            != status_filter
        ):
            continue

        # Location

        if (
            location_filter != "All"
            and job["location"]
            != location_filter
        ):
            continue

        # Search

        if search:

            searchable_text = (
                f"{job['title']} "
                f"{job['company']} "
                f"{job['location']} "
                f"{job['role_match']} "
                f"{job['matching_skills']}"
            ).lower()

            if search not in searchable_text:
                continue

        filtered_jobs.append(job)

    # --------------------------------------------------------
    # Sort highest score first
    # --------------------------------------------------------

    filtered_jobs.sort(
        key=get_score,
        reverse=True,
    )

    st.write(
        f"Showing **{len(filtered_jobs)}** jobs."
    )

    # ========================================================
    # ALL JOBS DISPLAY
    # ========================================================

    if not filtered_jobs:

        st.info(
            "No jobs match your filters."
        )

    else:

        st.subheader(
            "Available Jobs"
        )

        # ----------------------------------------------------
        # Summary table
        # ----------------------------------------------------

        table_data = []

        for job in filtered_jobs:

            table_data.append(
                {
                    "Score": format_score(job),
                    "Job Title": job["title"],
                    "Company": job["company"],
                    "Location": job["location"],
                    "Recommendation": job["recommendation"],
                    "Status": get_status(job),
                    "Deadline": (
                        job["deadline"]
                        or "Not specified"
                    ),
                }
            )

        st.dataframe(
            table_data,
            width=True,
            hide_index=True,
        )

        st.divider()

        # ====================================================
        # INDIVIDUAL JOB CARDS
        # ====================================================

        st.subheader(
            "Job Listings"
        )

        for index, job in enumerate(
            filtered_jobs
        ):

            score = get_score(job)

            with st.container(
                border=True
            ):

                # ------------------------------------------------
                # Header
                # ------------------------------------------------

                col1, col2, col3, col4 = st.columns(
                    [5, 2, 2, 2]
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

                with col3:

                    st.write(
                        "**Location**"
                    )

                    st.write(
                        job["location"]
                        or "Not specified"
                    )

                with col4:

                    st.write(
                        "**Recommendation**"
                    )

                    st.write(
                        job["recommendation"]
                        or "Not specified"
                    )

                # ------------------------------------------------
                # Basic information
                # ------------------------------------------------

                info_col1, info_col2, info_col3 = st.columns(
                    3
                )

                with info_col1:

                    st.write(
                        f"**Role Match:** "
                        f"{job['role_match'] or 'Not specified'}"
                    )

                with info_col2:

                    st.write(
                        f"**Deadline:** "
                        f"{job['deadline'] or 'Not specified'}"
                    )

                with info_col3:

                    st.write(
                        f"**Status:** "
                        f"{get_status(job)}"
                    )

                # ------------------------------------------------
                # Details
                # ------------------------------------------------

                with st.expander(
                    "View Job Details"
                ):

                    st.write(
                        f"**Matching Skills:** "
                        f"{job['matching_skills'] or 'None'}"
                    )

                    st.write(
                        f"**Missing Skills:** "
                        f"{job['missing_skills'] or 'None'}"
                    )

                    st.write(
                        f"**Warnings:** "
                        f"{job['warnings'] or 'None'}"
                    )

                    st.write(
                        f"**Posted:** "
                        f"{job['posted'] or 'Not specified'}"
                    )

                    st.write(
                        f"**Application Status:** "
                        f"{get_status(job)}"
                    )

                    if job["notes"]:

                        st.write(
                            f"**Notes:** "
                            f"{job['notes']}"
                        )

                # ------------------------------------------------
                # Actions
                # ------------------------------------------------

                action_col1, action_col2 = st.columns(
                    [1, 1]
                )

                with action_col1:

                    if job["url"]:

                        st.link_button(
                            "🔗 Open Job Listing",
                            job["url"],
                            width=True,
                        )

                with action_col2:

                    can_prepare = (
                        get_status(job)
                        not in [
                            "Applied",
                            "Rejected",
                        ]
                    )

                    if can_prepare:

                        prepare_key = (
                            f"prepare_{job['row']}"
                        )

                        if st.button(
                            "📄 Prepare Application",
                            key=prepare_key,
                            type="primary",
                            width=True,
                        ):

                            with st.spinner(
                                "Generating tailored CV and cover letter..."
                            ):

                                try:

                                    application = prepare_application(
                                        job
                                    )

                                    st.session_state[
                                        "last_application"
                                    ] = application

                                    st.success(
                                        "Application documents generated successfully."
                                    )

                                except Exception as error:

                                    st.error(
                                        "Could not generate application: "
                                        f"{error}"
                                    )

                    else:

                        st.info(
                            "Application already processed."
                        )

                # ------------------------------------------------
                # Show generated documents if this is the job
                # ------------------------------------------------

                last_application = (
                    st.session_state.get(
                        "last_application"
                    )
                )

                if (
                    last_application
                    and last_application.get(
                        "job_row"
                    ) == job["row"]
                ):

                    st.divider()

                    st.success(
                        "Application documents are ready."
                    )

                    st.write(
                        "**Tailored CV:**"
                    )

                    st.code(
                        str(
                            last_application[
                                "cv_path"
                            ]
                        ),
                        language="text",
                    )

                    st.write(
                        "**Cover Letter:**"
                    )

                    st.code(
                        str(
                            last_application[
                                "cover_letter_path"
                            ]
                        ),
                        language="text",
                    )

                    st.write(
                        "**Application Folder:**"
                    )

                    st.code(
                        str(
                            last_application[
                                "application_directory"
                            ]
                        ),
                        language="text",
                    )

                    st.info(
                        "Review the generated CV and cover letter "
                        "before marking the application as submitted."
                    )


# ============================================================
# APPLICATIONS PAGE
# ============================================================

elif page == "Applications":

    st.title(
        "📁 Applications"
    )

    st.write(
        "Track applications that have been prepared or submitted."
    )

    st.divider()

    # ========================================================
    # APPLICATION COUNTS
    # ========================================================

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

    interviews = [
        job
        for job in jobs
        if job["application_status"] == "Interview"
    ]

    rejected = [
        job
        for job in jobs
        if job["application_status"] == "Rejected"
    ]

    col1, col2, col3, col4 = st.columns(4)

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

    with col3:

        st.metric(
            "Interviews",
            len(interviews),
        )

    with col4:

        st.metric(
            "Rejected",
            len(rejected),
        )

    st.divider()

    # ========================================================
    # LATEST GENERATED APPLICATION
    # ========================================================

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
            f"**Job:** "
            f"{application.get('job_title', 'Unknown')}"
        )

        st.write(
            f"**Company:** "
            f"{application.get('company', 'Unknown')}"
        )

        # ----------------------------------------------------
        # CV
        # ----------------------------------------------------

        st.write(
            "**Tailored CV:**"
        )

        st.code(
            str(
                application["cv_path"]
            ),
            language="text",
        )

        # ----------------------------------------------------
        # Cover letter
        # ----------------------------------------------------

        st.write(
            "**Cover Letter:**"
        )

        st.code(
            str(
                application["cover_letter_path"]
            ),
            language="text",
        )

        # ----------------------------------------------------
        # Folder
        # ----------------------------------------------------

        st.write(
            "**Application Folder:**"
        )

        st.code(
            str(
                application[
                    "application_directory"
                ]
            ),
            language="text",
        )

        st.divider()

        # ====================================================
        # RECORD APPLICATION
        # ====================================================

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
            placeholder=(
                "Optional notes about this application..."
            ),
        )

        if st.button(
            "✅ Mark as Applied",
            type="primary",
            width=True,
        ):

            # ------------------------------------------------
            # Find job using stored row number.
            # ------------------------------------------------

            job_row = application.get(
                "job_row"
            )

            matching_job = None

            for job in jobs:

                if job["row"] == job_row:

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

    # ========================================================
    # SUBMITTED APPLICATIONS
    # ========================================================

    st.divider()

    st.subheader(
        "Submitted Applications"
    )

    if not applied_jobs:

        st.info(
            "No applications have been recorded yet."
        )

    else:

        applied_jobs.sort(
            key=get_score,
            reverse=True,
        )

        for job in applied_jobs:

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### {job['title']}"
                )

                st.write(
                    f"**{job['company']}**"
                )

                col1, col2, col3, col4 = st.columns(
                    4
                )

                with col1:

                    st.write(
                        f"**Match:** "
                        f"{get_score(job):.0f}%"
                    )

                with col2:

                    st.write(
                        f"**Location:** "
                        f"{job['location'] or 'Not specified'}"
                    )

                with col3:

                    st.write(
                        f"**CV:** "
                        f"{job['cv_version'] or 'Not specified'}"
                    )

                with col4:

                    st.write(
                        f"**Cover Letter:** "
                        f"{job['cover_letter'] or 'No'}"
                    )

                st.write(
                    f"**Notes:** "
                    f"{job['notes'] or 'None'}"
                )

                if job["url"]:

                    st.link_button(
                        "🔗 Open Job Listing",
                        job["url"],
                    )