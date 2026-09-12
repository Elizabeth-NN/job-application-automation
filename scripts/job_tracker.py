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


# ==========================================================
# HELPERS
# ==========================================================

def _as_list(value):
    """Convert a value into a list of strings."""

    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value else []

    return list(value)


def _join_values(values, separator=", "):
    """Safely convert values into a string."""

    return separator.join(
        str(value)
        for value in _as_list(values)
        if value
    )


# ==========================================================
# TRACKER CREATION
# ==========================================================

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
        17: 35,
        18: 35,
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

    workbook.close()

    print(
        f"Created tracker: {TRACKER_FILE}"
    )


# ==========================================================
# FIND JOB
# ==========================================================

def find_job_row(url):
    """
    Find a job row using its URL.

    Returns:
        Row number if found.
        None if not found.
    """

    if not url:
        return None

    create_tracker()

    workbook = load_workbook(
        TRACKER_FILE,
        read_only=True
    )

    sheet = workbook["Jobs"]

    try:
        for row in sheet.iter_rows(
            min_row=2,
            values_only=True
        ):
            # URL is column N = index 13
            existing_url = row[13]

            if existing_url == url:
                return row[0] and sheet._current_row or None

    finally:
        workbook.close()

    return None


# ==========================================================
# JOB EXISTS
# ==========================================================

def job_exists(url):
    """Check whether a job already exists."""

    if not url:
        return False

    create_tracker()

    workbook = load_workbook(
        TRACKER_FILE,
        read_only=True
    )

    sheet = workbook["Jobs"]

    try:
        for row in sheet.iter_rows(
            min_row=2,
            values_only=True
        ):
            # URL is column N
            existing_url = row[13]

            if existing_url == url:
                return True

    finally:
        workbook.close()

    return False


# ==========================================================
# FIND ROW NUMBER
# ==========================================================

def get_job_row(url):
    """
    Return the actual Excel row number for a job URL.

    Returns None if the job does not exist.
    """

    if not url:
        return None

    create_tracker()

    workbook = load_workbook(
        TRACKER_FILE,
        read_only=True
    )

    sheet = workbook["Jobs"]

    try:
        for row_number in range(
            2,
            sheet.max_row + 1
        ):
            existing_url = sheet.cell(
                row=row_number,
                column=14
            ).value

            if existing_url == url:
                return row_number

    finally:
        workbook.close()

    return None


# ==========================================================
# CATEGORY FORMATTING
# ==========================================================

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


# ==========================================================
# FORMAT ROW
# ==========================================================

def format_job_row(sheet, row_number):
    """Apply formatting to a job row."""

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

    # Category colors
    apply_category_formatting(
        sheet,
        row_number
    )

    # Score alignment
    score_cell = sheet.cell(
        row=row_number,
        column=5
    )

    score_cell.alignment = Alignment(
        horizontal="center",
        vertical="top"
    )

    # URL hyperlink
    url_cell = sheet.cell(
        row=row_number,
        column=14
    )

    url = url_cell.value

    if url:
        url_cell.hyperlink = url
        url_cell.style = "Hyperlink"


# ==========================================================
# SAVE NEW JOB
# ==========================================================

def save_job(job, match_result):
    """
    Save a matched job to the Excel tracker.

    If the job already exists, it is not duplicated.

    Returns:
        True  -> new job was added
        False -> job already existed
    """

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

        _join_values(
            role_matches
        ),

        _join_values(
            matching_skills
        ),

        _join_values(
            missing_skills
        ),

        _join_values(
            warnings,
            separator=" | "
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

    row_number = sheet.max_row

    format_job_row(
        sheet,
        row_number
    )

    workbook.save(
        TRACKER_FILE
    )

    workbook.close()

    return True


# ==========================================================
# UPDATE APPLICATION DOCUMENTS
# ==========================================================

def update_application_documents(
    url,
    cv_path=None,
    cover_letter_path=None
):
    """
    Update CV and cover-letter paths for an existing job.

    This is intentionally separate from save_job() because
    document generation happens after the job has already
    been saved to the tracker.

    Args:
        url:
            Job URL used to locate the tracker row.

        cv_path:
            Path to the generated tailored CV.

        cover_letter_path:
            Path to the generated cover letter.

    Returns:
        True if the tracker was updated.
        False if the job could not be found.
    """

    if not url:
        return False

    create_tracker()

    row_number = get_job_row(
        url
    )

    if row_number is None:
        return False

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

    # ======================================================
    # CV PATH
    # ======================================================

    if cv_path:
        sheet.cell(
            row=row_number,
            column=17
        ).value = str(
            Path(cv_path)
        )

    # ======================================================
    # COVER LETTER PATH
    # ======================================================

    if cover_letter_path:
        sheet.cell(
            row=row_number,
            column=18
        ).value = str(
            Path(cover_letter_path)
        )

    # ======================================================
    # APPLICATION STATUS
    # ======================================================

    cv_exists = bool(cv_path)
    cover_letter_exists = bool(
        cover_letter_path
    )

    if cv_exists and cover_letter_exists:
        sheet.cell(
            row=row_number,
            column=15
        ).value = "To Apply"

    elif cv_exists or cover_letter_exists:
        sheet.cell(
            row=row_number,
            column=15
        ).value = "To Apply"

    # ======================================================
    # FORMAT DOCUMENT CELLS
    # ======================================================

    for column in (17, 18):
        cell = sheet.cell(
            row=row_number,
            column=column
        )

        cell.alignment = Alignment(
            vertical="top",
            wrap_text=True
        )

    workbook.save(
        TRACKER_FILE
    )

    workbook.close()

    return True


# ==========================================================
# UPDATE NOTES
# ==========================================================

def update_job_notes(url, notes):
    """Update the Notes column for an existing job."""

    if not url:
        return False

    create_tracker()

    row_number = get_job_row(
        url
    )

    if row_number is None:
        return False

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

    sheet.cell(
        row=row_number,
        column=19
    ).value = notes or ""

    sheet.cell(
        row=row_number,
        column=19
    ).alignment = Alignment(
        vertical="top",
        wrap_text=True
    )

    workbook.save(
        TRACKER_FILE
    )

    workbook.close()

    return True


# ==========================================================
# UPDATE APPLICATION STATUS
# ==========================================================

def update_application_status(
    url,
    status
):
    """Update the application status for an existing job."""

    if not url:
        return False

    create_tracker()

    row_number = get_job_row(
        url
    )

    if row_number is None:
        return False

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

    sheet.cell(
        row=row_number,
        column=15
    ).value = status

    workbook.save(
        TRACKER_FILE
    )

    workbook.close()

    return True