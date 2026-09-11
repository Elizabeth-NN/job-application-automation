from pathlib import Path
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter


TRACKER_FILE = Path("data/job_tracker.xlsx")


HEADERS = [
    "Date Found",
    "Job Title",
    "Company",
    "Location",
    "Score",
    "Category",
    "Recommendation",
    "Role Match",
    "Matching Skills",
    "Missing Skills",
    "Warnings",
    "Posted",
    "Deadline",
    "URL",
    "Application Status",
    "Review Decision",
    "CV Version",
    "Cover Letter",
    "Notes",
]


def create_tracker():
    """Create the Excel tracker if it does not exist."""

    TRACKER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if TRACKER_FILE.exists():
        return

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Jobs"

    # Add headers
    sheet.append(HEADERS)

    # Header formatting
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # Freeze header row
    sheet.freeze_panes = "A2"

    # Add filter
    sheet.auto_filter.ref = sheet.dimensions

    # ==========================================================
    # APPLICATION STATUS DROPDOWN
    # ==========================================================

    status_dropdown = DataValidation(
        type="list",
        formula1=(
            '"Not Applied,To Apply,Applied,'
            'Interview,Rejected,Offer,Withdrawn"'
        ),
        allow_blank=False
    )

    sheet.add_data_validation(status_dropdown)

    # Application Status = column O
    status_dropdown.add("O2:O1000")

    # ==========================================================
    # REVIEW DECISION DROPDOWN
    # ==========================================================

    review_dropdown = DataValidation(
        type="list",
        formula1='"Apply,Maybe,Skip"',
        allow_blank=True
    )

    sheet.add_data_validation(review_dropdown)

    # Review Decision = column P
    review_dropdown.add("P2:P1000")

    # ==========================================================
    # COLUMN WIDTHS
    # ==========================================================

    widths = {
        1: 14,   # Date Found
        2: 45,   # Job Title
        3: 30,   # Company
        4: 20,   # Location
        5: 10,   # Score
        6: 20,   # Category
        7: 18,   # Recommendation
        8: 30,   # Role Match
        9: 45,   # Matching Skills
        10: 45,  # Missing Skills
        11: 50,  # Warnings
        12: 15,  # Posted
        13: 15,  # Deadline
        14: 70,  # URL
        15: 20,  # Application Status
        16: 18,  # Review Decision
        17: 20,  # CV Version
        18: 20,  # Cover Letter
        19: 40,  # Notes
    }

    for column, width in widths.items():
        sheet.column_dimensions[
            get_column_letter(column)
        ].width = width

    workbook.save(TRACKER_FILE)

    print(
        f"Created tracker: {TRACKER_FILE}"
    )


def job_exists(url):
    """Check whether a job already exists in the tracker."""

    if not TRACKER_FILE.exists():
        return False

    workbook = load_workbook(
        TRACKER_FILE,
        read_only=True
    )

    sheet = workbook["Jobs"]

    for row in sheet.iter_rows(
        min_row=2,
        values_only=True
    ):
        # URL is column N (index 13)
        existing_url = row[13]

        if existing_url == url:
            workbook.close()
            return True

    workbook.close()

    return False


def save_job(job, match_result):
    """Save a matched job to the Excel tracker."""

    create_tracker()

    url = job.get("url", "")

    # Don't save duplicate jobs
    if job_exists(url):
        return False

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

    # ==========================================================
    # MATCH RESULT DATA
    # ==========================================================

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

    # ==========================================================
    # ADD JOB
    # ==========================================================

    sheet.append([
        # Date Found
        datetime.now().strftime("%Y-%m-%d"),

        # Job Title
        job.get("title", ""),

        # Company
        job.get("company", ""),

        # Location
        job.get("location", ""),

        # Score
        match_result.get(
            "score",
            0
        ),

        # Category
        match_result.get(
            "category",
            ""
        ),

        # Recommendation
        match_result.get(
            "recommendation",
            ""
        ),

        # Role Match
        ", ".join(role_matches),

        # Matching Skills
        ", ".join(matching_skills),

        # Missing Skills
        ", ".join(missing_skills),

        # Warnings
        " | ".join(warnings),

        # Posted
        job.get("posted", ""),

        # Deadline
        job.get("deadline", ""),

        # URL
        url,

        # Application Status
        "Not Applied",

        # Review Decision
        "",

        # CV Version
        "",

        # Cover Letter
        "",

        # Notes
        "",
    ])

    workbook.save(TRACKER_FILE)

    workbook.close()

    return True