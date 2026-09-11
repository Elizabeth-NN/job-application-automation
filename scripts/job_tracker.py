from pathlib import Path
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
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


# ==========================================================
# COLORS
# ==========================================================

STRONG_FILL = PatternFill(
    fill_type="solid",
    fgColor="C6EFCE"
)

GOOD_FILL = PatternFill(
    fill_type="solid",
    fgColor="E2F0D9"
)

POSSIBLE_FILL = PatternFill(
    fill_type="solid",
    fgColor="FFF2CC"
)

WEAK_FILL = PatternFill(
    fill_type="solid",
    fgColor="FCE4D6"
)

POOR_FILL = PatternFill(
    fill_type="solid",
    fgColor="FFC7CE"
)


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

    # ======================================================
    # HEADERS
    # ======================================================

    sheet.append(HEADERS)

    for cell in sheet[1]:
        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # ======================================================
    # FREEZE HEADER
    # ======================================================

    sheet.freeze_panes = "A2"

    # ======================================================
    # FILTER
    # ======================================================

    sheet.auto_filter.ref = "A1:S1"

    # ======================================================
    # APPLICATION STATUS DROPDOWN
    # ======================================================

    status_dropdown = DataValidation(
        type="list",
        formula1=(
            '"Not Applied,To Apply,Applied,'
            'Interview,Rejected,Offer,Withdrawn"'
        ),
        allow_blank=False
    )

    sheet.add_data_validation(
        status_dropdown
    )

    status_dropdown.add(
        "O2:O1000"
    )

    # ======================================================
    # REVIEW DECISION DROPDOWN
    # ======================================================

    review_dropdown = DataValidation(
        type="list",
        formula1='"Apply,Maybe,Skip"',
        allow_blank=True
    )

    sheet.add_data_validation(
        review_dropdown
    )

    review_dropdown.add(
        "P2:P1000"
    )

    # ======================================================
    # COLUMN WIDTHS
    # ======================================================

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
        11: 50,
        12: 15,
        13: 15,
        14: 70,
        15: 20,
        16: 18,
        17: 20,
        18: 20,
        19: 40,
    }

    for column, width in widths.items():

        sheet.column_dimensions[
            get_column_letter(column)
        ].width = width

    # ======================================================
    # DEFAULT ALIGNMENT
    # ======================================================

    for row in sheet.iter_rows():

        for cell in row:

            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )

    workbook.save(
        TRACKER_FILE
    )

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

        # URL is column N
        existing_url = row[13]

        if existing_url == url:

            workbook.close()

            return True

    workbook.close()

    return False


def apply_category_formatting(sheet, row_number):
    """Apply color formatting based on match category."""

    category = sheet.cell(
        row=row_number,
        column=6
    ).value

    if not category:
        return

    category = str(category).upper()

    fill = None

    if category == "STRONG MATCH":
        fill = STRONG_FILL

    elif category == "GOOD MATCH":
        fill = GOOD_FILL

    elif category == "POSSIBLE MATCH":
        fill = POSSIBLE_FILL

    elif category == "WEAK MATCH":
        fill = WEAK_FILL

    elif category == "POOR MATCH":
        fill = POOR_FILL

    if fill:

        for column in range(
            1,
            len(HEADERS) + 1
        ):

            sheet.cell(
                row=row_number,
                column=column
            ).fill = fill


def save_job(job, match_result):
    """Save a matched job to the Excel tracker."""

    create_tracker()

    url = job.get(
        "url",
        ""
    )

    # ======================================================
    # DUPLICATE CHECK
    # ======================================================

    if job_exists(url):
        return False

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

    # ======================================================
    # MATCH DATA
    # ======================================================

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

    # ======================================================
    # ADD JOB
    # ======================================================

    sheet.append([
        datetime.now().strftime(
            "%Y-%m-%d"
        ),

        job.get(
            "title",
            ""
        ),

        job.get(
            "company",
            ""
        ),

        job.get(
            "location",
            ""
        ),

        match_result.get(
            "score",
            0
        ),

        match_result.get(
            "category",
            ""
        ),

        match_result.get(
            "recommendation",
            ""
        ),

        ", ".join(
            role_matches
        ),

        ", ".join(
            matching_skills
        ),

        ", ".join(
            missing_skills
        ),

        " | ".join(
            warnings
        ),

        job.get(
            "posted",
            ""
        ),

        job.get(
            "deadline",
            ""
        ),

        url,

        "Not Applied",

        "",

        "",

        "",

        "",
    ])

    # ======================================================
    # GET NEW ROW
    # ======================================================

    row_number = sheet.max_row

    # ======================================================
    # MAKE URL CLICKABLE
    # ======================================================

    url_cell = sheet.cell(
        row=row_number,
        column=14
    )

    if url:

        url_cell.hyperlink = url
        url_cell.style = "Hyperlink"

    # ======================================================
    # ROW FORMATTING
    # ======================================================

    for column in range(
        1,
        len(HEADERS) + 1
    ):

        cell = sheet.cell(
            row=row_number,
            column=column
        )

        cell.alignment = Alignment(
            vertical="top",
            wrap_text=True
        )

    # ======================================================
    # CATEGORY COLOR
    # ======================================================

    apply_category_formatting(
        sheet,
        row_number
    )

    # ======================================================
    # SCORE FORMATTING
    # ======================================================

    score_cell = sheet.cell(
        row=row_number,
        column=5
    )

    score_cell.alignment = Alignment(
        horizontal="center",
        vertical="top"
    )

    # ======================================================
    # SAVE
    # ======================================================

    workbook.save(
        TRACKER_FILE
    )

    workbook.close()

    return True