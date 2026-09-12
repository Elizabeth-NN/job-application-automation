"""
CV tailoring engine.

Generates a tailored CV for a specific job using the candidate
profile stored in data/candidate_profile.json.

The tailoring process:

    1. Loads the candidate profile.
    2. Builds searchable job text.
    3. Selects relevant technical skills.
    4. Selects relevant professional experience.
    5. Ranks projects by relevance.
    6. Creates a job-specific professional summary.
    7. Generates a formatted Word CV.
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

BASE_DIR = Path(__file__).resolve().parent.parent

PROFILE_FILE = BASE_DIR / "data" / "candidate_profile.json"

APPLICATIONS_DIR = BASE_DIR / "applications"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalize text for keyword matching.

    Converts text to lowercase and keeps characters useful
    for technical terms such as:
        C#
        .NET
        Node.js
        Next.js
        REST APIs
    """

    if not text:
        return ""

    text = str(text).lower()

    text = text.replace("’", "'")

    text = re.sub(
        r"[^a-z0-9+#.\-/ ]",
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
    Check whether a complete word or phrase exists in text.
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


# ============================================================
# PROFILE
# ============================================================

def load_candidate_profile():
    """
    Load candidate profile from JSON.
    """

    if not PROFILE_FILE.exists():

        raise FileNotFoundError(
            f"Candidate profile not found: {PROFILE_FILE}"
        )

    try:

        with open(
            PROFILE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except json.JSONDecodeError as error:

        raise ValueError(
            f"Invalid JSON in {PROFILE_FILE}: "
            f"{error}"
        ) from error


# ============================================================
# JOB TEXT
# ============================================================

def get_job_text(job):
    """
    Build one searchable text string from a job.
    """

    return normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("company", "")}
        {job.get("location", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        {job.get("qualification", "")}
        {job.get("experience", "")}
        """
    )


# ============================================================
# SKILL MATCHING
# ============================================================

def skill_is_relevant(skill, job_text):
    """
    Determine whether a candidate skill appears in the job.
    """

    normalized_skill = normalize_text(skill)

    if not normalized_skill:
        return False

    # --------------------------------------------------------
    # Direct match
    # --------------------------------------------------------

    if contains_term(
        job_text,
        normalized_skill
    ):
        return True

    # --------------------------------------------------------
    # Useful aliases
    # --------------------------------------------------------

    aliases = {

        "react.js": [
            "react",
            "reactjs",
        ],

        "next.js": [
            "next.js",
            "nextjs",
            "next js",
        ],

        "flask-restful": [
            "flask-restful",
            "flask restful",
            "restful api",
            "rest api",
            "rest apis",
        ],

        "rest apis": [
            "rest api",
            "rest apis",
            "restful api",
            "restful apis",
            "api development",
        ],

        "database design": [
            "database design",
            "database schema",
            "schema design",
            "database development",
        ],

        "database implementation": [
            "database implementation",
            "database development",
            "database design",
        ],

        "tailwind css": [
            "tailwind",
            "tailwind css",
        ],

        "sqlalchemy": [
            "sqlalchemy",
        ],

        "html": [
            "html",
            "html5",
        ],

        "css": [
            "css",
            "css3",
        ],

        "javascript": [
            "javascript",
            "js",
        ],

        "github": [
            "github",
        ],
    }

    for alias in aliases.get(
        normalized_skill,
        []
    ):

        if contains_term(
            job_text,
            alias
        ):

            return True

    return False


def select_relevant_skills(profile, job):
    """
    Select candidate skills relevant to the job.

    Returns skills grouped according to the structure in
    candidate_profile.json.
    """

    job_text = get_job_text(job)

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


# ============================================================
# EXPERIENCE MATCHING
# ============================================================

def get_experience_text(experience):
    """
    Convert one experience entry into searchable text.
    """

    return normalize_text(
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


def calculate_experience_relevance(
    experience,
    job_text
):
    """
    Calculate relevance of one experience entry.

    Software engineering experience receives a strong
    baseline because it is directly relevant to the target
    roles.

    Other experience must demonstrate meaningful overlap.
    """

    experience_text = get_experience_text(
        experience
    )

    score = 0

    # --------------------------------------------------------
    # Strong technical indicators
    # --------------------------------------------------------

    technical_terms = [
        "python",
        "flask",
        "rest api",
        "rest apis",
        "api",
        "backend",
        "frontend",
        "software",
        "javascript",
        "react",
        "database",
        "sql",
        "development",
        "programming",
    ]

    for term in technical_terms:

        if (
            contains_term(
                experience_text,
                term
            )
            and contains_term(
                job_text,
                term
            )
        ):

            score += 3

    # --------------------------------------------------------
    # Job-specific keyword overlap
    # --------------------------------------------------------

    job_words = set(
        job_text.split()
    )

    experience_words = set(
        experience_text.split()
    )

    meaningful_overlap = (
        job_words.intersection(
            experience_words
        )
    )

    score += min(
        len(meaningful_overlap),
        6
    )

    # --------------------------------------------------------
    # Direct software experience
    # --------------------------------------------------------

    title = normalize_text(
        experience.get(
            "title",
            ""
        )
    )

    software_titles = [
        "software engineer",
        "software developer",
        "developer",
        "engineer",
        "web developer",
        "backend developer",
        "frontend developer",
    ]

    if any(
        contains_term(title, item)
        for item in software_titles
    ):

        score += 10

    return score


def select_relevant_experience(
    profile,
    job,
    max_items=3
):
    """
    Select the most relevant professional experiences.

    Software engineering experience is prioritized.

    Non-software experience is included only when it provides
    meaningful relevance to the target position.
    """

    job_text = get_job_text(job)

    scored = []

    for index, experience in enumerate(
        profile.get(
            "experience",
            []
        )
    ):

        score = calculate_experience_relevance(
            experience,
            job_text
        )

        scored.append(
            (
                score,
                index,
                experience
            )
        )

    # Highest relevance first.
    scored.sort(
        key=lambda item: (
            item[0],
            -item[1]
        ),
        reverse=True
    )

    selected = []

    for score, index, experience in scored:

        # ----------------------------------------------------
        # Software experience gets priority.
        # ----------------------------------------------------

        experience_title = normalize_text(
            experience.get(
                "title",
                ""
            )
        )

        is_software = any(
            contains_term(
                experience_title,
                keyword
            )
            for keyword in [
                "software",
                "developer",
                "engineer",
            ]
        )

        # ----------------------------------------------------
        # Include strong matches.
        # ----------------------------------------------------

        if score >= 8:

            selected.append(
                experience
            )

        # ----------------------------------------------------
        # Software experience gets included even when the
        # job description has few matching keywords.
        # ----------------------------------------------------

        elif is_software and score >= 3:

            selected.append(
                experience
            )

        if len(selected) >= max_items:

            break

    # --------------------------------------------------------
    # Ensure software engineering internship is retained.
    # --------------------------------------------------------

    software_experience = None

    for experience in profile.get(
        "experience",
        []
    ):

        title = normalize_text(
            experience.get(
                "title",
                ""
            )
        )

        if (
            "software engineering" in title
            or "software developer" in title
        ):

            software_experience = experience
            break

    if (
        software_experience
        and software_experience not in selected
    ):

        if len(selected) >= max_items:

            selected[-1] = software_experience

        else:

            selected.insert(
                0,
                software_experience
            )

    return selected[:max_items]


# ============================================================
# PROJECT MATCHING
# ============================================================

def get_project_text(project):
    """
    Convert project information into searchable text.
    """

    return normalize_text(
        f"""
        {project.get("name", "")}
        {project.get("description", "")}
        {project.get("role", "")}
        {' '.join(
            project.get(
                "responsibilities",
                []
            )
        )}
        {' '.join(
            project.get(
                "technologies",
                []
            )
        )}
        """
    )


def calculate_project_relevance(
    project,
    job_text
):
    """
    Calculate project relevance.

    Direct technology matches are weighted more heavily than
    generic word overlap.
    """

    project_text = get_project_text(
        project
    )

    score = 0

    # --------------------------------------------------------
    # Technical technology matches
    # --------------------------------------------------------

    technologies = project.get(
        "technologies",
        []
    )

    for technology in technologies:

        if skill_is_relevant(
            technology,
            job_text
        ):

            score += 5

    # --------------------------------------------------------
    # Project responsibilities
    # --------------------------------------------------------

    responsibilities = project.get(
        "responsibilities",
        []
    )

    for responsibility in responsibilities:

        responsibility_text = normalize_text(
            responsibility
        )

        if (
            "backend" in responsibility_text
            and (
                "backend" in job_text
                or "server" in job_text
                or "api" in job_text
            )
        ):

            score += 4

        if (
            "frontend" in responsibility_text
            and (
                "frontend" in job_text
                or "front end" in job_text
                or "react" in job_text
            )
        ):

            score += 4

        if (
            "database" in responsibility_text
            and (
                "database" in job_text
                or "sql" in job_text
            )
        ):

            score += 4

    # --------------------------------------------------------
    # Keyword overlap
    # --------------------------------------------------------

    job_words = set(
        job_text.split()
    )

    project_words = set(
        project_text.split()
    )

    overlap = job_words.intersection(
        project_words
    )

    score += min(
        len(overlap),
        8
    )

    return score


def select_relevant_projects(
    profile,
    job,
    max_items=3
):
    """
    Select the most relevant projects.

    Projects are ranked rather than simply selected in their
    original profile order.
    """

    job_text = get_job_text(job)

    scored = []

    for index, project in enumerate(
        profile.get(
            "projects",
            []
        )
    ):

        score = calculate_project_relevance(
            project,
            job_text
        )

        scored.append(
            (
                score,
                index,
                project
            )
        )

    scored.sort(
        key=lambda item: (
            item[0],
            -item[1]
        ),
        reverse=True
    )

    selected = [
        project
        for score, index, project
        in scored
        if score > 0
    ]

    # --------------------------------------------------------
    # If nothing matches, keep the strongest projects from
    # the candidate profile.
    # --------------------------------------------------------

    if not selected:

        selected = profile.get(
            "projects",
            []
        )[:max_items]

    return selected[:max_items]


# ============================================================
# TARGET ROLE
# ============================================================

def detect_target_role(job):
    """
    Determine the role name to use in the tailored summary.
    """

    title = job.get(
        "title",
        ""
    ).strip()

    if title:

        return title

    return "Software Developer"


# ============================================================
# SUMMARY
# ============================================================

def build_tailored_summary(
    profile,
    job,
    relevant_skills
):
    """
    Build a concise job-specific professional summary.

    Only uses information contained in the candidate profile.
    """

    target_role = detect_target_role(
        job
    )

    # --------------------------------------------------------
    # Collect selected skills in a sensible order.
    # --------------------------------------------------------

    priority_categories = [
        "backend",
        "frontend",
        "databases",
        "tools_and_other",
    ]

    selected_skills = []

    for category in priority_categories:

        for skill in relevant_skills.get(
            category,
            []
        ):

            if skill not in selected_skills:

                selected_skills.append(
                    skill
                )

    # --------------------------------------------------------
    # Limit summary length.
    # --------------------------------------------------------

    selected_skills = selected_skills[:6]

    if selected_skills:

        skill_text = ", ".join(
            selected_skills
        )

    else:

        skill_text = (
            "full-stack web development"
        )

    # --------------------------------------------------------
    # Determine focus from job title.
    # --------------------------------------------------------

    normalized_title = normalize_text(
        target_role
    )

    if (
        "backend" in normalized_title
        or "back end" in normalized_title
    ):

        focus = (
            "backend development, REST API "
            "development, and database implementation"
        )

    elif (
        "frontend" in normalized_title
        or "front end" in normalized_title
    ):

        focus = (
            "frontend development and "
            "web application development"
        )

    elif (
        "full stack" in normalized_title
        or "fullstack" in normalized_title
    ):

        focus = (
            "full-stack web development, "
            "backend services, and frontend applications"
        )

    else:

        focus = (
            "software development and "
            "practical web application development"
        )

    summary = (
        "Junior Software Developer with hands-on experience "
        f"building web applications using {skill_text}. "
        f"Experienced in {focus}, collaborating on team-based "
        "software projects, and implementing practical "
        f"technical solutions. Seeking to contribute these "
        f"skills as a {target_role}."
    )

    return summary


# ============================================================
# DOCUMENT CREATION
# ============================================================

def create_document():
    """
    Create a new Word document with basic CV formatting.
    """

    document = Document()

    styles = document.styles

    normal_style = styles["Normal"]

    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(10)

    return document


def add_heading(
    document,
    text,
    size=12
):
    """
    Add a formatted CV section heading.
    """

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(3)

    run = paragraph.add_run(
        text.upper()
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
    Add a CV bullet point.
    """

    paragraph = document.add_paragraph(
        style="List Bullet"
    )

    paragraph.paragraph_format.space_after = Pt(1)

    run = paragraph.add_run(
        text
    )

    run.font.name = "Arial"
    run.font.size = Pt(9.5)

    return paragraph


# ============================================================
# CONTACT HEADER
# ============================================================

def add_contact_header(
    document,
    profile
):
    """
    Add candidate contact information.
    """

    personal = profile.get(
        "personal",
        {}
    )

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    paragraph.paragraph_format.space_after = Pt(2)

    run = paragraph.add_run(
        personal.get(
            "name",
            ""
        )
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(18)

    # --------------------------------------------------------
    # Contact information
    # --------------------------------------------------------

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    paragraph.paragraph_format.space_after = Pt(1)

    contact_items = []

    for key in [
        "phone",
        "email",
        "location",
    ]:

        value = personal.get(
            key
        )

        if value:

            contact_items.append(
                value
            )

    run = paragraph.add_run(
        " | ".join(contact_items)
    )

    run.font.name = "Arial"
    run.font.size = Pt(9)

    # --------------------------------------------------------
    # Professional links
    # --------------------------------------------------------

    links = []

    for key in [
        "linkedin",
        "github",
    ]:

        value = personal.get(
            key
        )

        if value:

            links.append(
                value
            )

    if links:

        paragraph = document.add_paragraph()

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        paragraph.paragraph_format.space_after = Pt(5)

        run = paragraph.add_run(
            " | ".join(links)
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
        "Professional Summary"
    )

    paragraph = document.add_paragraph(
        summary
    )

    paragraph.paragraph_format.space_after = Pt(5)

    for run in paragraph.runs:

        run.font.name = "Arial"
        run.font.size = Pt(9.5)


# ============================================================
# SKILLS SECTION
# ============================================================

def add_skills(
    document,
    skills
):
    """
    Add relevant technical skills grouped by category.
    """

    if not skills:

        return

    add_heading(
        document,
        "Technical Skills"
    )

    category_names = {
        "frontend": "Frontend",
        "backend": "Backend",
        "databases": "Databases",
        "tools_and_other": "Tools & Other",
    }

    for category, skill_list in skills.items():

        if not skill_list:

            continue

        category_name = category_names.get(
            category,
            category.replace(
                "_",
                " "
            ).title()
        )

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(1)

        run = paragraph.add_run(
            f"{category_name}: "
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(9.5)

        run = paragraph.add_run(
            ", ".join(skill_list)
        )

        run.font.name = "Arial"
        run.font.size = Pt(9.5)


# ============================================================
# EXPERIENCE SECTION
# ============================================================

def add_experience(
    document,
    experience
):
    """
    Add selected professional experience.
    """

    if not experience:

        return

    add_heading(
        document,
        "Work Experience"
    )

    for item in experience:

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(1)

        title = item.get(
            "title",
            ""
        )

        company = item.get(
            "company",
            ""
        )

        start_date = item.get(
            "start_date",
            ""
        )

        end_date = item.get(
            "end_date",
            ""
        )

        run = paragraph.add_run(
            title
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(10)

        if company:

            run = paragraph.add_run(
                f" | {company}"
            )

            run.font.name = "Arial"
            run.font.size = Pt(10)

        if start_date:

            date_text = (
                f" | {start_date}"
            )

            if end_date:

                date_text += (
                    f" – {end_date}"
                )

            run = paragraph.add_run(
                date_text
            )

            run.font.name = "Arial"
            run.font.size = Pt(9)

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

    if not projects:

        return

    add_heading(
        document,
        "Projects"
    )

    for project in projects:

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(1)

        run = paragraph.add_run(
            project.get(
                "name",
                ""
            )
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(10)

        github = project.get(
            "github"
        )

        if github:

            run = paragraph.add_run(
                f" | {github}"
            )

            run.font.name = "Arial"
            run.font.size = Pt(9)

        description = project.get(
            "description",
            ""
        )

        if description:

            paragraph = document.add_paragraph(
                description
            )

            paragraph.paragraph_format.space_after = Pt(1)

            for run in paragraph.runs:

                run.font.name = "Arial"
                run.font.size = Pt(9.5)

        if project.get(
            "role"
        ):

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

        technologies = project.get(
            "technologies",
            []
        )

        if technologies:

            add_bullet(
                document,
                "Technologies: "
                + ", ".join(
                    technologies
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
    Add education history.
    """

    if not education:

        return

    add_heading(
        document,
        "Education"
    )

    for item in education:

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(1)

        qualification = item.get(
            "qualification",
            ""
        )

        institution = item.get(
            "institution",
            ""
        )

        run = paragraph.add_run(
            qualification
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(9.5)

        if institution:

            run = paragraph.add_run(
                f" | {institution}"
            )

            run.font.name = "Arial"
            run.font.size = Pt(9.5)

        if item.get(
            "start_date"
        ):

            date_text = (
                f" | {item['start_date']}"
            )

            if item.get(
                "end_date"
            ):

                date_text += (
                    f" – {item['end_date']}"
                )

            run = paragraph.add_run(
                date_text
            )

            run.font.name = "Arial"
            run.font.size = Pt(9)

        if item.get(
            "grade"
        ):

            run = paragraph.add_run(
                f" | Grade: {item['grade']}"
            )

            run.font.name = "Arial"
            run.font.size = Pt(9)


# ============================================================
# FILE NAME
# ============================================================

def create_application_directory(
    job,
    base_directory=APPLICATIONS_DIR
):
    """
    Create a safe directory name for a job application.
    """

    company = normalize_text(
        job.get(
            "company",
            "company"
        )
    )

    title = normalize_text(
        job.get(
            "title",
            "software-job"
        )
    )

    folder_name = (
        f"{company}-{title}"
    )

    # Convert spaces and punctuation into hyphens.
    folder_name = re.sub(
        r"[^a-z0-9]+",
        "-",
        folder_name
    ).strip("-")

    if not folder_name:

        folder_name = "application"

    output_directory = (
        base_directory / folder_name
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return output_directory


# ============================================================
# CV TAILORING
# ============================================================

def tailor_cv(
    job,
    output_directory=None
):
    """
    Generate a tailored CV for a specific job.

    Returns the generated DOCX path.
    """

    profile = load_candidate_profile()

    # --------------------------------------------------------
    # Select relevant content
    # --------------------------------------------------------

    relevant_skills = select_relevant_skills(
        profile,
        job
    )

    relevant_experience = select_relevant_experience(
        profile,
        job
    )

    relevant_projects = select_relevant_projects(
        profile,
        job
    )

    tailored_summary = build_tailored_summary(
        profile,
        job,
        relevant_skills
    )

    # --------------------------------------------------------
    # Determine output directory
    # --------------------------------------------------------

    if output_directory is None:

        output_directory = create_application_directory(
            job
        )

    else:

        output_directory = Path(
            output_directory
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------------
    # Create document
    # --------------------------------------------------------

    document = create_document()

    add_contact_header(
        document,
        profile
    )

    add_summary(
        document,
        tailored_summary
    )

    add_skills(
        document,
        relevant_skills
    )

    add_experience(
        document,
        relevant_experience
    )

    add_projects(
        document,
        relevant_projects
    )

    add_education(
        document,
        profile.get(
            "education",
            []
        )
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_file = (
        output_directory
        / "tailored_cv.docx"
    )

    document.save(
        output_file
    )

    return output_file


# ============================================================
# DISPLAY TEST RESULTS
# ============================================================

def print_tailoring_results(
    job,
    profile
):
    """
    Display what the tailoring engine selected.
    """

    relevant_skills = select_relevant_skills(
        profile,
        job
    )

    relevant_experience = select_relevant_experience(
        profile,
        job
    )

    relevant_projects = select_relevant_projects(
        profile,
        job
    )

    tailored_summary = build_tailored_summary(
        profile,
        job,
        relevant_skills
    )

    print()

    print(
        f"Job: {job.get('title', 'Unknown')}"
    )

    if job.get("company"):

        print(
            f"Company: {job['company']}"
        )

    print()

    print(
        "Relevant skills:"
    )

    if relevant_skills:

        for category, skills in relevant_skills.items():

            print(
                f"  {category}: "
                + ", ".join(skills)
            )

    else:

        print(
            "  None"
        )

    print()

    print(
        "Selected experience:"
    )

    if relevant_experience:

        for experience in relevant_experience:

            print(
                f"  {experience['title']} "
                f"at {experience['company']}"
            )

    else:

        print(
            "  None"
        )

    print()

    print(
        "Selected projects:"
    )

    if relevant_projects:

        for project in relevant_projects:

            print(
                f"  {project['name']}"
            )

    else:

        print(
            "  None"
        )

    print()

    print(
        "Tailored summary:"
    )

    print(
        f"  {tailored_summary}"
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CV TAILOR TEST")
    print("=" * 60)

    profile = load_candidate_profile()

    test_jobs = [

        {
            "title": "Backend Developer",

            "company": "Test Company",

            "location": "Nairobi, Kenya",

            "description": """
                We are looking for a backend developer with
                Python, Flask, REST APIs, SQL and Git experience.

                Experience developing APIs and working with
                databases is preferred.
            """,

            "requirements": """
                Python, Flask, REST APIs, SQL and Git.
            """,
        },

        {
            "title": "Frontend Developer",

            "company": "Test Company",

            "location": "Nairobi, Kenya",

            "description": """
                We are looking for a frontend developer with
                HTML, CSS, JavaScript, React and Next.js.

                Experience building responsive web applications
                is preferred.
            """,

            "requirements": """
                HTML, CSS, JavaScript, React and Next.js.
            """,
        },

        {
            "title": "Full Stack Developer",

            "company": "Test Company",

            "location": "Remote",

            "description": """
                We are looking for a full stack developer with
                Python, Flask, REST APIs, JavaScript, React,
                SQL and Git.

                The successful candidate will work on both
                frontend and backend web applications.
            """,

            "requirements": """
                Python, Flask, REST APIs, JavaScript,
                React, SQL and Git.
            """,
        },
    ]

    for job in test_jobs:

        print_tailoring_results(
            job,
            profile
        )

        print(
            "-" * 60
        )

    # --------------------------------------------------------
    # Generate final test CV using the first test job.
    # --------------------------------------------------------

    test_job = test_jobs[0]

    output_directory = (
        APPLICATIONS_DIR
        / "test-application"
    )

    output = tailor_cv(
        test_job,
        output_directory
    )

    print()

    print(
        f"Created tailored CV: {output}"
    )

    print("=" * 60)