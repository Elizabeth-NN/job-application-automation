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

    sheet.append(HEADERS)

    # Header formatting
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # Freeze header
    sheet.freeze_panes = "A2"

    # Filter
    sheet.auto_filter.ref = sheet.dimensions

    # Application status dropdown
    status_dropdown = DataValidation(
        type="list",
        formula1=(
            '"Not Applied,To Apply,Applied,'
            'Interview,Rejected,Offer,Withdrawn"'
        ),
        allow_blank=False
    )

    sheet.add_data_validation(status_dropdown)

    status_dropdown.add(
        f"O2:O1000"
    )

    # Default status
    for row in range(2, 1001):
        sheet.cell(
            row=row,
            column=15
        ).value = "Not Applied"

    # Column widths
    widths = {
        1: 14,
        2: 45,
        3: 30,
        4: 20,
        5: 10,
        6: 20,
        7: 18,
        8: 30,
        9: 45,
        10: 45,
        11: 45,
        12: 15,
        13: 15,
        14: 70,
        15: 20,
        16: 20,
        17: 20,
        18: 40,
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
    """Check whether a job already exists."""

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

    if job_exists(url):
        return False

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

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

    sheet.append([
        datetime.now().strftime("%Y-%m-%d"),

        job.get("title", ""),

        job.get("company", ""),

        job.get("location", ""),

        match_result.get("score", 0),

        match_result.get("category", ""),

        match_result.get(
            "recommendation",
            ""
        ),

        ", ".join(role_matches),

        ", ".join(matching_skills),

        ", ".join(missing_skills),

        " | ".join(warnings),

        job.get("posted", ""),

        job.get("deadline", ""),

        url,

        "Not Applied",

        "",

        "",

        "",
    ])

    workbook.save(TRACKER_FILE)

    workbook.close()

    return True