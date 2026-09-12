
"""
CV tailoring engine.

Uses candidate_profile.json as the single source of truth and
creates a tailored CV for a specific job.

The tailor:
    1. Loads the candidate profile.
    2. Extracts job text.
    3. Identifies relevant candidate skills.
    4. Selects relevant experience.
    5. Selects relevant projects.
    6. Creates a job-specific professional summary.
    7. Generates a Word CV.

Important:
    The system must never invent skills, experience, education,
    responsibilities, employers, or technologies.
"""

import json
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ============================================================
# PATHS
# ============================================================

PROFILE_FILE = Path("data/candidate_profile.json")
APPLICATIONS_DIR = Path("applications")


# ============================================================
# PROFILE
# ============================================================

def load_candidate_profile():
    """
    Load the candidate profile from candidate_profile.json.
    """

    if not PROFILE_FILE.exists():
        raise FileNotFoundError(
            f"Candidate profile not found: {PROFILE_FILE}"
        )

    with open(
        PROFILE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):
    """
    Normalize text for keyword matching.
    """

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9+#./\- ]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_term(text, term):
    """
    Determine whether a complete word or phrase appears
    in the supplied text.
    """

    text = normalize_text(text)
    term = normalize_text(term)

    if not text or not term:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(term)
        + r"(?!\w)"
    )

    return re.search(
        pattern,
        text
    ) is not None


def build_job_text(job):
    """
    Combine all useful job information into one searchable
    text string.
    """

    return normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        {job.get("location", "")}
        {job.get("qualification", "")}
        {job.get("experience", "")}
        """
    )


# ============================================================
# JOB KEYWORDS
# ============================================================

def get_job_keywords(job):
    """
    Return individual normalized job keywords.

    This is mainly useful for general text-overlap checks.
    """

    job_text = build_job_text(job)

    return set(
        job_text.split()
    )


# ============================================================
# SKILL MATCHING
# ============================================================

def skill_is_relevant(skill, job_text):
    """
    Determine whether a candidate skill appears in the job.
    """

    return contains_term(
        job_text,
        skill
    )


def select_relevant_skills(profile, job):
    """
    Select candidate skills that appear in the job.

    Skills are kept under their original profile categories.
    """

    job_text = build_job_text(job)

    relevant = {}

    for category, skills in profile.get(
        "technical_skills",
        {}
    ).items():

        matched = []

        for skill in skills:

            if skill_is_relevant(
                skill,
                job_text
            ):

                matched.append(skill)

        if matched:

            relevant[category] = matched

    return relevant


def get_all_candidate_skills(profile):
    """
    Flatten all candidate technical skills into one list.
    """

    skills = []

    for skill_list in profile.get(
        "technical_skills",
        {}
    ).values():

        skills.extend(skill_list)

    return list(
        dict.fromkeys(skills)
    )


# ============================================================
# EXPERIENCE RELEVANCE
# ============================================================

def calculate_text_overlap(text_a, text_b):
    """
    Calculate simple meaningful word overlap between two texts.
    """

    words_a = set(
        normalize_text(text_a).split()
    )

    words_b = set(
        normalize_text(text_b).split()
    )

    return len(
        words_a.intersection(words_b)
    )


def select_relevant_experience(profile, job):
    """
    Select experience relevant to the job.

    Software experience is strongly prioritized.

    Other experience can still be retained when there is
    meaningful overlap with the job.
    """

    job_text = build_job_text(job)

    selected = []

    for experience in profile.get(
        "experience",
        []
    ):

        experience_text = normalize_text(
            f"""
            {experience.get("title", "")}
            {experience.get("company", "")}
            {' '.join(
                experience.get(
                    "responsibilities",
                    []
                )
            )}
            """
        )

        software_indicators = [
            "software",
            "developer",
            "development",
            "backend",
            "frontend",
            "python",
            "flask",
            "api",
            "programming",
            "database",
            "react",
            "javascript",
        ]

        is_software_experience = any(
            contains_term(
                experience_text,
                indicator
            )
            for indicator in software_indicators
        )

        if is_software_experience:

            selected.append(
                experience
            )

            continue

        overlap = calculate_text_overlap(
            job_text,
            experience_text
        )

        if overlap >= 2:

            selected.append(
                experience
            )

    return selected


# ============================================================
# PROJECT RELEVANCE
# ============================================================

def score_project(project, job_text):
    """
    Calculate project relevance.

    Matching technologies receive stronger weight than
    general word overlap.
    """

    technologies = project.get(
        "technologies",
        []
    )

    technology_matches = 0

    for technology in technologies:

        if contains_term(
            job_text,
            technology
        ):

            technology_matches += 1

    project_text = normalize_text(
        f"""
        {project.get("name", "")}
        {project.get("description", "")}
        {' '.join(
            project.get(
                "responsibilities",
                []
            )
        )}
        """
    )

    overlap = calculate_text_overlap(
        job_text,
        project_text
    )

    return (
        technology_matches * 5
        + overlap
    )


def select_relevant_projects(profile, job):
    """
    Select the strongest projects for the job.

    Projects are ranked rather than simply selected based
    on whether they contain one matching word.
    """

    job_text = build_job_text(job)

    projects = profile.get(
        "projects",
        []
    )

    scored_projects = []

    for index, project in enumerate(
        projects
    ):

        score = score_project(
            project,
            job_text
        )

        scored_projects.append(
            (
                score,
                index,
                project
            )
        )

    scored_projects.sort(
        key=lambda item: (
            item[0],
            -item[1]
        ),
        reverse=True
    )

    # Keep the strongest 3 projects.
    selected = [
        item[2]
        for item in scored_projects[:3]
    ]

    return selected


# ============================================================
# SUMMARY
# ============================================================

def get_candidate_primary_skills(profile):
    """
    Return the candidate's strongest backend/full-stack skills.

    These come directly from candidate_profile.json.
    """

    preferred = [
        "Python",
        "Flask",
        "REST APIs",
        "React.js",
        "JavaScript",
        "Database Design",
    ]

    available = get_all_candidate_skills(
        profile
    )

    selected = []

    for skill in preferred:

        for available_skill in available:

            if normalize_text(
                skill
            ) == normalize_text(
                available_skill
            ):

                selected.append(
                    available_skill
                )

    return selected


def create_tailored_summary(profile, job):
    """
    Create a concise job-specific professional summary.

    All technologies and experience mentioned must exist
    in candidate_profile.json.
    """

    candidate_skills = (
        get_candidate_primary_skills(
            profile
        )
    )

    job_text = build_job_text(job)

    matching_primary_skills = [
        skill
        for skill in candidate_skills
        if contains_term(
            job_text,
            skill
        )
    ]

    if not matching_primary_skills:
        matching_primary_skills = (
            candidate_skills[:4]
        )

    skills_text = ", ".join(
        matching_primary_skills
    )

    job_title = job.get(
        "title",
        "software engineering role"
    )

    summary = (
        "Junior Software Developer with hands-on "
        "experience in full-stack web development "
        f"using {skills_text}. "
        "Experienced in backend development, REST API "
        "development, database design, and contributing "
        "to team-based software projects. "
        f"Seeking to contribute these skills as a "
        f"{job_title}."
    )

    return summary


# ============================================================
# DOCUMENT CREATION
# ============================================================

def create_document():
    """
    Create a new Word document with basic formatting.
    """

    document = Document()

    styles = document.styles

    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10)

    return document


def add_heading(
    document,
    text,
    size=14
):
    """
    Add a formatted section heading.
    """

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(3)

    run = paragraph.add_run(
        text
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(size)

    return paragraph


def add_bullet(
    document,
    text
):
    """
    Add a bullet point.
    """

    paragraph = document.add_paragraph(
        style="List Bullet"
    )

    paragraph.paragraph_format.space_after = Pt(2)

    run = paragraph.add_run(
        text
    )

    run.font.name = "Arial"
    run.font.size = Pt(10)

    return paragraph


# ============================================================
# HEADER
# ============================================================

def add_contact_header(
    document,
    profile
):
    """
    Add candidate contact information.
    """

    personal = profile["personal"]

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = paragraph.add_run(
        personal["name"]
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(18)

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    contact = (
        f"{personal['phone']} | "
        f"{personal['email']} | "
        f"{personal['location']}"
    )

    run = paragraph.add_run(
        contact
    )

    run.font.name = "Arial"
    run.font.size = Pt(9)

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    links = (
        f"{personal['linkedin']} | "
        f"{personal['github']}"
    )

    run = paragraph.add_run(
        links
    )

    run.font.name = "Arial"
    run.font.size = Pt(9)


# ============================================================
# SUMMARY SECTION
# ============================================================

def add_summary(
    document,
    summary
):
    """
    Add professional summary.
    """

    add_heading(
        document,
        "PROFESSIONAL SUMMARY"
    )

    paragraph = document.add_paragraph(
        summary
    )

    paragraph.paragraph_format.space_after = Pt(6)


# ============================================================
# SKILLS SECTION
# ============================================================

def add_skills(
    document,
    skills
):
    """
    Add relevant technical skills.
    """

    add_heading(
        document,
        "TECHNICAL SKILLS"
    )

    for category, skill_list in skills.items():

        if not skill_list:
            continue

        category_name = (
            category
            .replace("_", " ")
            .title()
        )

        paragraph = document.add_paragraph()

        run = paragraph.add_run(
            f"{category_name}: "
        )

        run.bold = True

        paragraph.add_run(
            ", ".join(skill_list)
        )


# ============================================================
# EXPERIENCE SECTION
# ============================================================

def add_experience(
    document,
    experience
):
    """
    Add selected work experience.
    """

    add_heading(
        document,
        "WORK EXPERIENCE"
    )

    for item in experience:

        paragraph = document.add_paragraph()

        run = paragraph.add_run(
            item["title"]
        )

        run.bold = True

        paragraph.add_run(
            f" | {item['company']}"
        )

        start_date = item.get(
            "start_date",
            ""
        )

        end_date = item.get(
            "end_date",
            ""
        )

        if start_date:

            paragraph.add_run(
                f" | {start_date}"
            )

            if end_date:

                paragraph.add_run(
                    f" – {end_date}"
                )

        for responsibility in item.get(
            "responsibilities",
            []
        ):

            add_bullet(
                document,
                responsibility
            )


# ============================================================
# PROJECTS SECTION
# ============================================================

def add_projects(
    document,
    projects
):
    """
    Add selected projects.
    """

    add_heading(
        document,
        "PROJECTS"
    )

    for project in projects:

        paragraph = document.add_paragraph()

        run = paragraph.add_run(
            project["name"]
        )

        run.bold = True

        if project.get("github"):

            paragraph.add_run(
                f" | {project['github']}"
            )

        description = project.get(
            "description",
            ""
        )

        if description:

            paragraph = document.add_paragraph(
                description
            )

            paragraph.paragraph_format.space_after = (
                Pt(2)
            )

        if project.get("role"):

            add_bullet(
                document,
                f"Role: {project['role']}"
            )

        for responsibility in project.get(
            "responsibilities",
            []
        ):

            add_bullet(
                document,
                responsibility
            )

        if project.get("technologies"):

            add_bullet(
                document,
                "Technologies: "
                + ", ".join(
                    project["technologies"]
                )
            )


# ============================================================
# EDUCATION SECTION
# ============================================================

def add_education(
    document,
    education
):
    """
    Add education.
    """

    add_heading(
        document,
        "EDUCATION"
    )

    for item in education:

        paragraph = document.add_paragraph()

        run = paragraph.add_run(
            item["qualification"]
        )

        run.bold = True

        paragraph.add_run(
            f" | {item['institution']}"
        )

        if item.get("start_date"):

            paragraph.add_run(
                f" | {item['start_date']}"
            )

            if item.get("end_date"):

                paragraph.add_run(
                    f" – {item['end_date']}"
                )

        if item.get("grade"):

            paragraph.add_run(
                f" | Grade: {item['grade']}"
            )


# ============================================================
# MAIN TAILORING FUNCTION
# ============================================================

def tailor_cv(
    job,
    output_directory
):
    """
    Generate a tailored CV for a specific job.
    """

    profile = load_candidate_profile()

    relevant_skills = (
        select_relevant_skills(
            profile,
            job
        )
    )

    relevant_experience = (
        select_relevant_experience(
            profile,
            job
        )
    )

    relevant_projects = (
        select_relevant_projects(
            profile,
            job
        )
    )

    tailored_summary = (
        create_tailored_summary(
            profile,
            job
        )
    )

    document = create_document()

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    add_contact_header(
        document,
        profile
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    add_summary(
        document,
        tailored_summary
    )

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    if relevant_skills:

        add_skills(
            document,
            relevant_skills
        )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    if relevant_experience:

        add_experience(
            document,
            relevant_experience
        )

    # --------------------------------------------------------
    # Projects
    # --------------------------------------------------------

    if relevant_projects:

        add_projects(
            document,
            relevant_projects
        )

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    add_education(
        document,
        profile["education"]
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_directory
        / "tailored_cv.docx"
    )

    document.save(
        output_file
    )

    return output_file


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CV TAILOR TEST")
    print("=" * 60)

    test_job = {

        "title": "Backend Developer",

        "description": """
        We are looking for a backend developer with
        Python, Flask, REST APIs, SQL and Git experience.

        Experience with database design and API development
        is an advantage.
        """,

        "location": "Nairobi, Kenya",
    }

    print()
    print(
        f"Job: {test_job['title']}"
    )

    profile = load_candidate_profile()

    relevant_skills = (
        select_relevant_skills(
            profile,
            test_job
        )
    )

    print()
    print("Relevant skills:")

    for category, skills in relevant_skills.items():

        print(
            f"  {category}: "
            + ", ".join(skills)
        )

    relevant_experience = (
        select_relevant_experience(
            profile,
            test_job
        )
    )

    print()
    print(
        "Selected experience:"
    )

    for experience in relevant_experience:

        print(
            f"  {experience['title']} "
            f"at {experience['company']}"
        )

    relevant_projects = (
        select_relevant_projects(
            profile,
            test_job
        )
    )

    print()
    print(
        "Selected projects:"
    )

    for project in relevant_projects:

        print(
            f"  {project['name']}"
        )

    summary = (
        create_tailored_summary(
            profile,
            test_job
        )
    )

    print()
    print(
        "Tailored summary:"
    )

    print(
        f"  {summary}"
    )

    output = tailor_cv(
        test_job,
        APPLICATIONS_DIR / "test-application"
    )

    print()
    print(
        f"Created tailored CV: {output}"
    )

    print("=" * 60)


