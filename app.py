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
# CARD DESIGN — CSS + HTML RENDERING
# ============================================================
#
# Streamlit's built-in st.container(border=True) / st.metric can't
# render a score ring, an inline warning banner, or a collapsible
# skills breakdown. So each job card is split in two:
#
#   1. An HTML block (title, ring, warning, badges, skills) drawn
#      with st.markdown(unsafe_allow_html=True) — this is a fully
#      self-contained rounded card.
#   2. Real Streamlit widgets (st.button, st.link_button) placed
#      directly underneath in their own row. Streamlit doesn't
#      let custom CSS classes attach to its own containers, so
#      these sit just below the card rather than fused to it.
#
# The CSS below is injected once per page load.

CARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

:root {
    --paper-raised: #FFFFFF;
    --ink: #22261F;
    --ink-soft: #5B5F52;
    --line: #DEDACB;
    --moss: #55694A;
    --moss-soft: #E4E9DC;
    --amber: #A8631E;
    --amber-soft: #F3E6D4;
    --clay: #8A4A3C;
    --clay-soft: #F1DFD9;
    --grey: #9A9784;
    --grey-soft: #E9E7DE;
}

.jc-card {
    background: var(--paper-raised);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 20px 22px 16px 22px;
    margin-bottom: 6px;
    font-family: 'Inter', sans-serif;
    color: var(--ink);
}

.jc-card.jc-done { opacity: 0.72; }

.jc-row-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
}

.jc-title {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 500;
    margin: 0 0 4px 0;
    line-height: 1.25;
}

.jc-company {
    font-size: 14px;
    color: var(--ink-soft);
    margin: 0;
}

.jc-company b { color: var(--ink); font-weight: 600; }

.jc-ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    gap: 4px;
}

.jc-ring-label {
    font-size: 10.5px;
    color: var(--ink-soft);
}

.jc-ring-pct {
    font-family: 'Fraunces', serif;
    font-size: 14px;
    font-weight: 600;
    fill: var(--ink);
}

.jc-warning {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background: var(--clay-soft);
    border: 1px solid #E2C4BA;
    color: var(--clay);
    border-radius: 7px;
    padding: 10px 13px;
    font-size: 13.5px;
    margin-top: 14px;
    line-height: 1.4;
}

.jc-warning svg { flex-shrink: 0; margin-top: 1px; }

.jc-meta {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    align-items: center;
    font-size: 13px;
    color: var(--ink-soft);
    margin-top: 14px;
}

.jc-badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

.jc-badge-apply { background: var(--moss-soft); color: var(--moss); }
.jc-badge-review { background: var(--amber-soft); color: var(--amber); }
.jc-badge-applied { background: var(--grey-soft); color: var(--ink-soft); }
.jc-badge-neutral { background: var(--grey-soft); color: var(--ink-soft); }

.jc-card details {
    margin-top: 14px;
    border-top: 1px solid var(--line);
    padding-top: 10px;
}

.jc-card summary {
    cursor: pointer;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--moss);
    list-style: none;
}

.jc-card summary::-webkit-details-marker { display: none; }

.jc-skills-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 12px;
    font-size: 13px;
}

.jc-skills-grid h4 {
    margin: 0 0 6px 0;
    font-size: 11.5px;
    color: var(--ink-soft);
    font-weight: 600;
}

.jc-pill-list { display: flex; flex-wrap: wrap; gap: 6px; }

.jc-pill {
    padding: 3px 9px;
    border-radius: 5px;
    font-size: 12px;
}

.jc-pill.jc-have { background: var(--moss-soft); color: var(--moss); }
.jc-pill.jc-miss { background: var(--grey-soft); color: var(--ink-soft); }

.jc-notes {
    font-size: 13px;
    color: var(--ink-soft);
    margin-top: 10px;
}

/* ---------- dashboard header ---------- */

@keyframes dash-rise {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes dash-fade-up {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

.dash-header {
    background: var(--paper-raised);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 28px 30px 24px 30px;
    margin-bottom: 8px;
    font-family: 'Inter', sans-serif;
}

.dash-animate .dash-header {
    animation: dash-rise 0.5s ease-out forwards;
}

.dash-greeting {
    font-family: 'Fraunces', serif;
    font-size: 25px;
    font-weight: 500;
    margin: 0 0 6px 0;
    color: var(--ink);
    line-height: 1.25;
}

.dash-subtitle {
    color: var(--ink-soft);
    font-size: 14px;
    margin: 0 0 22px 0;
}

.dash-pipeline {
    display: flex;
    border-radius: 8px;
    overflow: hidden;
    height: 10px;
    background: var(--grey-soft);
}

.dash-pipeline-segment {
    height: 100%;
    width: var(--seg-width);
}

.dash-animate .dash-pipeline-segment {
    /* Grows from 0 to its real width once, on first load. Pure
       CSS — no JS is needed (and st.markdown's injected <script>
       tags don't execute anyway, since Streamlit inserts this
       HTML via innerHTML and browsers don't run scripts added
       that way). Gated behind .dash-animate so it plays once per
       session rather than replaying on every Streamlit rerun. */
    animation: dash-fill-bar 0.9s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    animation-delay: 0.15s;
}

@keyframes dash-fill-bar {
    from { width: 0%; }
    to { width: var(--seg-width); }
}

.dash-seg-found { background: var(--grey); }
.dash-seg-review { background: var(--amber); }
.dash-seg-applied { background: var(--moss); }
.dash-seg-interview { background: #3E4A35; }

.dash-pipeline-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 12px;
    font-size: 12.5px;
    color: var(--ink-soft);
}

.dash-pipeline-labels > div {
    opacity: 1;
}

.dash-animate .dash-pipeline-labels > div {
    opacity: 0;
    animation: dash-fade-up 0.4s ease-out forwards;
}

.dash-animate .dash-pipeline-labels > div:nth-child(1) { animation-delay: 0.35s; }
.dash-animate .dash-pipeline-labels > div:nth-child(2) { animation-delay: 0.45s; }
.dash-animate .dash-pipeline-labels > div:nth-child(3) { animation-delay: 0.55s; }
.dash-animate .dash-pipeline-labels > div:nth-child(4) { animation-delay: 0.65s; }

.dash-pipeline-labels b {
    display: block;
    color: var(--ink);
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 16px;
    margin-top: 2px;
}

.dash-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 5px;
}

/* ---------- sidebar ---------- */

[data-testid="stSidebar"] {
    background: var(--paper);
    border-right: 1px solid var(--line);
}

/* Color is safe to apply broadly — it doesn't affect how icons
   render. Font-family is NOT applied via a universal selector,
   because Streamlit's collapse arrow (and other icons) are text
   ligatures like "keyboard_double_arrow_left" rendered through a
   dedicated icon font. A blanket `* { font-family: Inter }` wins
   the specificity/source-order fight against that icon font and
   the icon shows up as literal text instead of an arrow. Inter is
   applied only to the specific text elements below instead. */
[data-testid="stSidebar"] {
    color: var(--ink);
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] h1 {
    font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] h1 {
    font-family: 'Fraunces', serif !important;
    font-weight: 500 !important;
    font-size: 22px !important;
    margin-bottom: 2px !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: var(--ink-soft) !important;
    font-size: 13px !important;
}

[data-testid="stSidebar"] hr {
    border-color: var(--line);
    margin: 18px 0;
}

/* Nav radio: recolor the native control and turn the selected
   option into a filled pill. accent-color and :has() are both
   supported by current evergreen browsers, so this avoids
   depending on Streamlit/BaseWeb's internal class names, which
   change across versions. */

[data-testid="stSidebar"] input[type="radio"] {
    accent-color: var(--moss);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    border-radius: 8px;
    padding: 6px 10px;
    margin-bottom: 2px;
    transition: background 0.15s ease;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: var(--moss-soft);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: var(--moss-soft);
    font-weight: 600;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
    color: var(--moss) !important;
    font-weight: 600;
}

/* ---------- sidebar: fully hide below a small viewport width ----------
   Streamlit already auto-collapses the sidebar on narrow viewports by
   sliding it off-canvas and flipping its wrapping <section> to
   aria-expanded="false" — but depending on the Streamlit version this
   can still leave a thin sliver or reserved spacing rather than a clean
   disappearance. This rule only fires when the sidebar is ALREADY in
   that collapsed state (aria-expanded="false"), so it does not fight
   Streamlit's own toggle: tapping the arrow sets aria-expanded="true"
   again, this rule stops applying, and the sidebar reappears as its
   normal overlay panel. Adjust the 768px breakpoint to taste. */
@media (max-width: 768px) {
    section[data-testid="stSidebar"][aria-expanded="false"] {
        display: none;
    }
}

/* Streamlit doesn't expose a way to attach a custom class to its
   own button/column containers, so the action row below each
   card is a separate block rather than visually fused to it.
   Tightening the card's bottom margin and the block's own top
   spacing keeps the two reading as one unit without relying on
   a selector that can't actually be targeted. */
div[data-testid="stHorizontalBlock"] {
    margin-bottom: 22px;
}
</style>
"""


def inject_card_css():
    """
    Inject the card CSS once per page render.
    """

    st.markdown(
        CARD_CSS,
        unsafe_allow_html=True,
    )


def render_score_ring(score, color="var(--moss)"):
    """
    Return an inline SVG ring showing a percentage score.
    """

    radius = 22
    circumference = 2 * 3.14159 * radius
    fraction = max(0, min(score, 100)) / 100
    offset = circumference * (1 - fraction)

    return f"""
    <svg width="52" height="52" viewBox="0 0 52 52">
        <circle cx="26" cy="26" r="{radius}" fill="none" stroke="var(--grey-soft)" stroke-width="5"/>
        <circle cx="26" cy="26" r="{radius}" fill="none" stroke="{color}" stroke-width="5"
            stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}"
            stroke-linecap="round" transform="rotate(-90 26 26)"/>
        <text x="26" y="30" text-anchor="middle" class="jc-ring-pct">{score:.0f}%</text>
    </svg>
    """


def ring_color_for(recommendation):
    """
    Pick a ring color based on the recommendation.
    """

    if recommendation == "APPLY":
        return "var(--moss)"

    if recommendation == "REVIEW":
        return "var(--amber)"

    return "var(--grey)"


def badge_html(job):
    """
    Return the HTML for the status/recommendation badge shown
    in the card's meta line.
    """

    status = get_status(job)

    if status == "Applied":
        applied_note = f"Applied"

        if job.get("notes") and "Applied:" in str(job.get("notes")):
            # Pull the recorded date out of the notes field, which
            # record_application() prefixes as "Applied: YYYY-MM-DD".
            try:
                applied_note = str(job["notes"]).split("|")[0].strip()
            except Exception:
                applied_note = "Applied"

        return f'<span class="jc-badge jc-badge-applied">{applied_note}</span>'

    if status in ("Interview", "Rejected"):
        return f'<span class="jc-badge jc-badge-neutral">{status}</span>'

    recommendation = job.get("recommendation")

    if recommendation == "APPLY":
        return '<span class="jc-badge jc-badge-apply">Apply</span>'

    if recommendation == "REVIEW":
        return '<span class="jc-badge jc-badge-review">Review</span>'

    return '<span class="jc-badge jc-badge-neutral">Not specified</span>'


def warning_html(job):
    """
    Return the HTML for the surfaced warning banner, or an empty
    string if the job has no warnings.
    """

    warnings = job.get("warnings")

    if not warnings:
        return ""

    return f"""
    <div class="jc-warning">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        </svg>
        <span>{warnings}</span>
    </div>
    """


def skills_pills(skills_text, pill_class):
    """
    Turn a comma-separated skills string into a row of pills.
    """

    if not skills_text:
        return '<span class="jc-pill jc-miss">None listed</span>'

    items = [
        item.strip()
        for item in str(skills_text).split(",")
        if item.strip()
    ]

    return "".join(
        f'<span class="jc-pill {pill_class}">{item}</span>'
        for item in items
    )


def skills_details_html(job):
    """
    Return the collapsible skills-breakdown block.
    """

    matching = skills_pills(job.get("matching_skills"), "jc-have")
    missing = skills_pills(job.get("missing_skills"), "jc-miss")

    return f"""
    <details>
        <summary>▸ Skills breakdown</summary>
        <div class="jc-skills-grid">
            <div>
                <h4>Matching</h4>
                <div class="jc-pill-list">{matching}</div>
            </div>
            <div>
                <h4>Missing</h4>
                <div class="jc-pill-list">{missing}</div>
            </div>
        </div>
    </details>
    """


def flatten_html(html):
    """
    Remove leading whitespace from every line of an HTML string.

    Streamlit's st.markdown() runs standard Markdown parsing before
    rendering unsafe HTML, and Markdown treats any line indented by
    4+ spaces as a literal code block rather than as HTML to parse.
    Since the HTML fragments below are built inside indented Python
    functions, every line inherits that indentation — so without
    this step, chunks of the card render as raw escaped tags instead
    of the styled card.
    """

    return "\n".join(
        line.strip()
        for line in html.strip().splitlines()
    )


def render_dashboard_header(total_jobs, jobs_to_review, applications, interviews, animate=True):
    """
    Render the dashboard's header: a time-of-day greeting, a live
    one-line summary, and a pipeline bar (Found / Reviewing /
    Applied / Interview) that fills in on first load.

    animate controls whether the entrance animation plays. It
    should only be True the first time this renders in a session —
    Streamlit reruns the whole script on every interaction, so
    without gating, the "one orchestrated moment" would replay on
    every button click and filter change instead of playing once.
    """

    hour = datetime.now().hour

    if hour < 12:
        greeting = "Good morning, Elizabeth"
    elif hour < 18:
        greeting = "Good afternoon, Elizabeth"
    else:
        greeting = "Good evening, Elizabeth"

    subtitle_parts = [f"{total_jobs} jobs in your tracker"]

    if jobs_to_review > 0:
        subtitle_parts.append(f"{jobs_to_review} waiting on your review")

    subtitle = " · ".join(subtitle_parts)

    # Segment widths as a share of total_jobs, so the bar reflects
    # real proportions rather than four equal slices.
    total_for_bar = max(total_jobs, 1)

    segments = [
        ("dash-seg-found", "var(--grey)", "Found", total_jobs),
        ("dash-seg-review", "var(--amber)", "Reviewing", jobs_to_review),
        ("dash-seg-applied", "var(--moss)", "Applied", applications),
        ("dash-seg-interview", "#3E4A35", "Interview", interviews),
    ]

    segment_html = "".join(
        f'<div class="dash-pipeline-segment {css_class}" '
        f'style="--seg-width:{(count / total_for_bar) * 100:.1f}%"></div>'
        for css_class, _color, _label, count in segments
    )

    label_html = "".join(
        f'<div><span class="dash-dot" style="background:{color}"></span>'
        f'{label}<b>{count}</b></div>'
        for _css_class, color, label, count in segments
    )

    wrapper_class = "dash-animate" if animate else ""

    html = f"""
    <div class="{wrapper_class}">
        <div class="dash-header">
            <p class="dash-greeting">{greeting}</p>
            <p class="dash-subtitle">{subtitle}</p>
            <div class="dash-pipeline">
                {segment_html}
            </div>
            <div class="dash-pipeline-labels">
                {label_html}
            </div>
        </div>
    </div>
    """

    return flatten_html(html)


def render_job_card_html(job, extra_meta=""):
    """
    Render the top (non-interactive) portion of a job card:
    title, company, score ring, warning banner, status badge,
    meta line, and the collapsible skills breakdown.

    extra_meta is an optional string of additional <span> meta
    items to append to the meta line (e.g. CV version used).
    """

    score = get_score(job)
    ring_color = ring_color_for(job.get("recommendation"))
    is_done = get_status(job) in ("Applied", "Rejected")
    card_class = "jc-card jc-done" if is_done else "jc-card"

    deadline = job.get("deadline") or "No deadline listed"
    posted = job.get("posted") or "Posting date not specified"

    html = f"""
    <div class="{card_class}">
        <div class="jc-row-top">
            <div>
                <p class="jc-title">{job.get('title') or 'Untitled role'}</p>
                <p class="jc-company"><b>{job.get('company') or 'Unknown company'}</b> · {job.get('location') or 'Location not specified'}</p>
            </div>
            <div class="jc-ring-wrap">
                {render_score_ring(score, ring_color)}
                <span class="jc-ring-label">match</span>
            </div>
        </div>
        {warning_html(job)}
        <div class="jc-meta">
            {badge_html(job)}
            <span>{posted}</span>
            <span>{deadline}</span>
            {extra_meta}
        </div>
        {skills_details_html(job)}
    </div>
    """

    return flatten_html(html)


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

    def get_value(sheet, row_number, column_name):
        column = columns.get(column_name)

        if not column:
            return ""

        return sheet.cell(
            row=row_number,
            column=column,
        ).value

    jobs = []

    for row_number in range(2, sheet.max_row + 1):

        job = {
            "row": row_number,
            "date_found": get_value(sheet, row_number, "Date Found"),
            "title": get_value(sheet, row_number, "Job Title"),
            "company": get_value(sheet, row_number, "Company"),
            "location": get_value(sheet, row_number, "Location"),
            "score": get_value(sheet, row_number, "Score"),
            "category": get_value(sheet, row_number, "Category"),
            "recommendation": get_value(sheet, row_number, "Recommendation"),
            "role_match": get_value(sheet, row_number, "Role Match"),
            "matching_skills": get_value(sheet, row_number, "Matching Skills"),
            "missing_skills": get_value(sheet, row_number, "Missing Skills"),
            "warnings": get_value(sheet, row_number, "Warnings"),
            "posted": get_value(sheet, row_number, "Posted"),
            "deadline": get_value(sheet, row_number, "Deadline"),
            "url": get_value(sheet, row_number, "URL"),
            "application_status": get_value(sheet, row_number, "Application Status"),
            "cv_version": get_value(sheet, row_number, "CV Version"),
            "cover_letter": get_value(sheet, row_number, "Cover Letter"),
            "notes": get_value(sheet, row_number, "Notes"),
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

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Jobs",
        "Applications",
    ],
    label_visibility="collapsed",
)


# ============================================================
# LOAD DATA
# ============================================================

inject_card_css()

if not TRACKER_FILE.exists():
    st.error(
        f"Tracker file not found at `{TRACKER_FILE}`. "
        "Add a job_tracker.xlsx with a 'Jobs' worksheet to get started."
    )

jobs = load_jobs()


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    # --------------------------------------------------------
    # Statistics (computed first so the header can use them)
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

    animate_header = (
        "dashboard_header_shown"
        not in st.session_state
    )

    st.session_state["dashboard_header_shown"] = True

    st.markdown(
        render_dashboard_header(
            total_jobs,
            jobs_to_review,
            applications,
            interviews,
            animate=animate_header,
        ),
        unsafe_allow_html=True,
    )

    st.divider()

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

            st.markdown(
                render_job_card_html(job),
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns([1, 1])

            with col1:
                if job["url"]:
                    st.link_button(
                        "Open listing",
                        job["url"],
                        use_container_width=True,
                    )
            with col2:
                st.button(
                    "Go to Jobs to prepare",
                    key=f"dash_prepare_{job['row']}",
                    disabled=True,
                    use_container_width=True,
                    help="Open the Jobs page to prepare this application.",
                )

            st.write("")

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
            use_container_width=True,
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

            # ------------------------------------------------
            # Card info block (title, ring, warning, skills)
            # ------------------------------------------------

            st.markdown(
                render_job_card_html(job),
                unsafe_allow_html=True,
            )

            # ------------------------------------------------
            # Actions — real Streamlit widgets, styled to sit
            # flush under the HTML block above.
            # ------------------------------------------------

            can_prepare = (
                get_status(job)
                not in [
                    "Applied",
                    "Rejected",
                ]
            )

            action_container = st.container()

            with action_container:

                col1, col2 = st.columns([1, 1])

                with col1:

                    if job["url"]:

                        st.link_button(
                            "Open listing",
                            job["url"],
                            use_container_width=True,
                        )

                with col2:

                    if can_prepare:

                        prepare_key = (
                            f"prepare_{job['row']}"
                        )

                        if st.button(
                            "Prepare application",
                            key=prepare_key,
                            type="primary",
                            use_container_width=True,
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

                        st.button(
                            "Already applied",
                            key=f"done_{job['row']}",
                            disabled=True,
                            use_container_width=True,
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

                with st.container(border=True):

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

            st.write("")  # small breathing room between cards


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
            use_container_width=True,
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

            extra_meta = (
                f'<span>CV: {job["cv_version"] or "Not specified"}</span>'
                f'<span>Cover letter: {job["cover_letter"] or "No"}</span>'
            )

            st.markdown(
                render_job_card_html(job, extra_meta=extra_meta),
                unsafe_allow_html=True,
            )

            with st.container():

                col1, col2 = st.columns([1, 1])

                with col1:

                    if job["url"]:

                        st.link_button(
                            "Open listing",
                            job["url"],
                            use_container_width=True,
                        )

                with col2:

                    st.button(
                        "Already applied",
                        key=f"submitted_{job['row']}",
                        disabled=True,
                        use_container_width=True,
                    )

            st.write("")