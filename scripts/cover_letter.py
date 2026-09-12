"""
Cover letter generator.

Generates a tailored cover letter for each job based on:
- Candidate profile
- Job title
- Company
- Job description
- Matching skills
- Relevant experience
- Relevant projects

Output:
    applications/<job-folder>/cover_letter.docx
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
    Load the candidate profile from JSON.
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
# TEXT UTILITIES
# ============================================================

def normalize_text(text):
    """
    Normalize text for keyword matching.
    """

    if not text:
        return ""

    return re.sub(
        r"[^a-z0-9+#.]",
        " ",
        str(text).lower()
    )


def get_job_text(job):
    """
    Combine all useful job information into one string.
    """

    return normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("company", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        {job.get("responsibilities", "")}
        """
    )


def get_candidate_skills(profile):
    """
    Return all candidate technical skills as a flat list.
    """

    skills = []

    for skill_list in profile.get(
        "technical_skills",
        {}
    ).values():

        skills.extend(skill_list)

    return skills


def find_matching_skills(profile, job):
    """
    Find candidate skills appearing in the job description.
    """

    job_text = get_job_text(job)

    matches = []

    for skill in get_candidate_skills(profile):

        normalized_skill = normalize_text(skill)

        if not normalized_skill:
            continue

        if normalized_skill in job_text:

            matches.append(skill)

    # Remove duplicates while preserving order
    return list(
        dict.fromkeys(matches)
    )


def find_relevant_experience(profile, job):
    """
    Find the candidate's most relevant experience.
    """

    job_text = get_job_text(job)

    selected = []

    # Important technical keywords
    technical_keywords = [
        "python",
        "flask",
        "api",
        "rest",
        "backend",
        "frontend",
        "react",
        "javascript",
        "database",
        "sql",
        "software",
        "web",
        "development",
        "developer"
    ]

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

        # ----------------------------------------------------
        # Strong software-development experience
        # ----------------------------------------------------

        if any(
            keyword in experience_text
            for keyword in technical_keywords
        ):

            selected.append(experience)

            continue

        # ----------------------------------------------------
        # General keyword overlap
        # ----------------------------------------------------

        job_words = set(
            job_text.split()
        )

        experience_words = set(
            experience_text.split()
        )

        overlap = job_words.intersection(
            experience_words
        )

        if len(overlap) >= 2:

            selected.append(
                experience
            )

    return selected


def find_relevant_projects(profile, job):
    """
    Find projects relevant to the job.
    """

    job_text = get_job_text(job)

    scored_projects = []

    for project in profile.get(
        "projects",
        []
    ):

        project_text = normalize_text(
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

        job_words = set(
            job_text.split()
        )

        project_words = set(
            project_text.split()
        )

        overlap = job_words.intersection(
            project_words
        )

        scored_projects.append(
            (
                len(overlap),
                project
            )
        )

    # Highest relevance first
    scored_projects.sort(
        key=lambda item: item[0],
        reverse=True
    )

    # Keep up to three projects
    selected = [
        project
        for score, project
        in scored_projects[:3]
    ]

    return selected


# ============================================================
# ROLE TYPE
# ============================================================

def determine_role_type(job_title):
    """
    Determine the general type of software role.
    """

    title = normalize_text(
        job_title
    )

    if (
        "backend" in title
        or "back end" in title
        or "python developer" in title
    ):
        return "backend"

    if (
        "frontend" in title
        or "front end" in title
        or "react developer" in title
        or "web developer" in title
    ):
        return "frontend"

    if (
        "full stack" in title
        or "fullstack" in title
    ):
        return "fullstack"

    if (
        "software developer" in title
        or "software engineer" in title
        or "developer" in title
        or "engineer" in title
    ):
        return "software"

    return "software"


# ============================================================
# SKILL SELECTION
# ============================================================

def select_top_skills(
    matching_skills,
    max_skills=6
):
    """
    Select the strongest skills to mention in the letter.
    """

    priority = [
        "Python",
        "Flask",
        "Flask-RESTful",
        "REST APIs",
        "React.js",
        "React",
        "JavaScript",
        "SQL",
        "Database Design",
        "Schema Design",
        "Database Implementation",
        "Git",
        "GitHub",
        "HTML",
        "CSS",
        "Next.js"
    ]

    selected = []

    # First use skills in preferred order
    for preferred in priority:

        for skill in matching_skills:

            if skill.lower() == preferred.lower():

                if skill not in selected:

                    selected.append(skill)

    # Then add remaining matching skills
    for skill in matching_skills:

        if skill not in selected:

            selected.append(skill)

    return selected[:max_skills]


# ============================================================
# COVER LETTER CONTENT
# ============================================================

def create_opening(
    candidate_name,
    company,
    job_title
):
    """
    Create the opening paragraph.
    """

    return (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to express my interest in the "
        f"{job_title} position at {company}. "
        f"As a Junior Software Developer with hands-on "
        f"experience building web applications and backend "
        f"services, I am excited about the opportunity to "
        f"contribute my technical skills to your team."
    )


def create_skills_paragraph(
    role_type,
    matching_skills
):
    """
    Create a paragraph focused on technical skills.
    """

    skills = select_top_skills(
        matching_skills
    )

    if skills:

        skill_text = ", ".join(
            skills[:-1]
        )

        if len(skills) > 1:

            skill_text += (
                f", and {skills[-1]}"
            )

        else:

            skill_text = skills[0]

    else:

        skill_text = (
            "Python, Flask, REST APIs, "
            "React, databases, and Git"
        )

    if role_type == "backend":

        return (
            f"My technical background includes "
            f"{skill_text}. I have practical experience "
            f"developing backend functionality, building "
            f"REST APIs, working with databases, and "
            f"contributing to team-based software projects."
        )

    if role_type == "frontend":

        return (
            f"My technical background includes "
            f"{skill_text}. I have practical experience "
            f"building web interfaces with modern "
            f"JavaScript technologies and integrating "
            f"frontend applications with backend services."
        )

    if role_type == "fullstack":

        return (
            f"My technical background includes "
            f"{skill_text}. I have experience working "
            f"across both frontend and backend development, "
            f"including building web interfaces, developing "
            f"backend services, designing databases, and "
            f"integrating REST APIs."
        )

    return (
        f"My technical background includes "
        f"{skill_text}. Through my software engineering "
        f"training and projects, I have developed practical "
        f"experience in web development, backend services, "
        f"databases, and collaborative software development."
    )


def create_experience_paragraph(
    experience
):
    """
    Create a paragraph based on the candidate's
    most relevant professional experience.
    """

    if not experience:

        return (
            "My experience has strengthened my ability "
            "to approach technical problems systematically, "
            "work collaboratively, and deliver practical "
            "software solutions."
        )

    item = experience[0]

    title = item.get(
        "title",
        "Software Developer"
    )

    company = item.get(
        "company",
        ""
    )

    responsibilities = item.get(
        "responsibilities",
        []
    )

    responsibility_text = ""

    if responsibilities:

        responsibility_text = " ".join(
            responsibilities[:2]
        )

    if responsibility_text:

        return (
            f"In my role as {title} at {company}, "
            f"I gained practical experience in "
            f"{responsibility_text.lower()} "
            f"This experience strengthened my ability "
            f"to collaborate with development teams, "
            f"understand technical requirements, and "
            f"deliver reliable solutions."
        )

    return (
        f"My experience as {title} at {company} "
        f"has strengthened my ability to work "
        f"collaboratively, solve problems, and "
        f"contribute to technical projects."
    )


def create_projects_paragraph(
    projects
):
    """
    Mention relevant projects when useful.
    """

    if not projects:

        return (
            "I have also developed practical software "
            "projects that have strengthened my "
            "problem-solving and development skills."
        )

    project_names = [
        project.get(
            "name",
            ""
        )
        for project in projects
        if project.get("name")
    ]

    if len(project_names) >= 3:

        project_text = (
            f"{project_names[0]}, "
            f"{project_names[1]}, and "
            f"{project_names[2]}"
        )

    elif len(project_names) == 2:

        project_text = (
            f"{project_names[0]} and "
            f"{project_names[1]}"
        )

    elif len(project_names) == 1:

        project_text = project_names[0]

    else:

        project_text = (
            "several full-stack web applications"
        )

    return (
        f"Through projects including {project_text}, "
        f"I have applied my knowledge of software "
        f"development in practical settings. "
        f"These projects involved areas such as "
        f"backend development, frontend development, "
        f"database design, REST APIs, and team "
        f"collaboration."
    )


def create_closing(
    candidate_name
):
    """
    Create closing paragraph.
    """

    return (
        "I would welcome the opportunity to discuss "
        "how my background, technical skills, and "
        "enthusiasm for software development could "
        "contribute to your team. Thank you for "
        "considering my application. I look forward "
        "to the possibility of discussing the role "
        "with you.\n\n"
        "Kind regards,\n"
        f"{candidate_name}"
    )


def generate_cover_letter(
    profile,
    job
):
    """
    Generate a complete tailored cover letter.
    """

    personal = profile.get(
        "personal",
        {}
    )

    candidate_name = personal.get(
        "name",
        "Elizabeth Njuguna"
    )

    company = job.get(
        "company",
        "your organization"
    )

    job_title = job.get(
        "title",
        "Software Developer"
    )

    role_type = determine_role_type(
        job_title
    )

    matching_skills = find_matching_skills(
        profile,
        job
    )

    relevant_experience = find_relevant_experience(
        profile,
        job
    )

    relevant_projects = find_relevant_projects(
        profile,
        job
    )

    opening = create_opening(
        candidate_name,
        company,
        job_title
    )

    skills_paragraph = create_skills_paragraph(
        role_type,
        matching_skills
    )

    experience_paragraph = create_experience_paragraph(
        relevant_experience
    )

    projects_paragraph = create_projects_paragraph(
        relevant_projects
    )

    closing = create_closing(
        candidate_name
    )

    return (
        opening
        + "\n\n"
        + skills_paragraph
        + "\n\n"
        + experience_paragraph
        + "\n\n"
        + projects_paragraph
        + "\n\n"
        + closing
    )


# ============================================================
# WORD DOCUMENT
# ============================================================

def create_document():
    """
    Create and configure a Word document.
    """

    document = Document()

    styles = document.styles

    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)

    return document


def add_document_header(
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

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = paragraph.add_run(
        personal.get(
            "name",
            "Elizabeth Njuguna"
        )
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(16)

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    contact_parts = []

    if personal.get("phone"):
        contact_parts.append(
            personal["phone"]
        )

    if personal.get("email"):
        contact_parts.append(
            personal["email"]
        )

    if personal.get("location"):
        contact_parts.append(
            personal["location"]
        )

    run = paragraph.add_run(
        " | ".join(contact_parts)
    )

    run.font.name = "Arial"
    run.font.size = Pt(9)

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    links = []

    if personal.get("linkedin"):
        links.append(
            personal["linkedin"]
        )

    if personal.get("github"):
        links.append(
            personal["github"]
        )

    run = paragraph.add_run(
        " | ".join(links)
    )

    run.font.name = "Arial"
    run.font.size = Pt(9)


def add_letter_content(
    document,
    letter
):
    """
    Add the cover letter text to the document.
    """

    paragraphs = letter.split(
        "\n\n"
    )

    for text in paragraphs:

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(8)
        paragraph.paragraph_format.line_spacing = 1.08

        run = paragraph.add_run(
            text
        )

        run.font.name = "Arial"
        run.font.size = Pt(10.5)


# ============================================================
# FILE NAME
# ============================================================

def create_application_folder_name(
    job
):
    """
    Create a safe folder name for a job application.
    """

    title = job.get(
        "title",
        "job"
    )

    company = job.get(
        "company",
        "company"
    )

    text = (
        f"{title} at {company}"
    )

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "-",
        text
    )

    text = text.strip("-")

    # Prevent excessively long paths
    return text[:150]


# ============================================================
# MAIN TAILORING FUNCTION
# ============================================================

def tailor_cover_letter(
    job,
    output_directory=None
):
    """
    Generate a tailored cover letter for a job.

    Returns:
        Path to the generated DOCX file.
    """

    profile = load_candidate_profile()

    # --------------------------------------------------------
    # Generate letter
    # --------------------------------------------------------

    letter = generate_cover_letter(
        profile,
        job
    )

    # --------------------------------------------------------
    # Determine output directory
    # --------------------------------------------------------

    if output_directory is None:

        folder_name = (
            create_application_folder_name(
                job
            )
        )

        output_directory = (
            APPLICATIONS_DIR / folder_name
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
    # Create Word document
    # --------------------------------------------------------

    document = create_document()

    add_document_header(
        document,
        profile
    )

    add_letter_content(
        document,
        letter
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_file = (
        output_directory
        / "cover_letter.docx"
    )

    document.save(
        output_file
    )

    return output_file


# ============================================================
# TEST HELPERS
# ============================================================

def print_cover_letter_test(
    job
):
    """
    Print generated cover letter information
    for testing purposes.
    """

    profile = load_candidate_profile()

    matching_skills = find_matching_skills(
        profile,
        job
    )

    relevant_experience = find_relevant_experience(
        profile,
        job
    )

    relevant_projects = find_relevant_projects(
        profile,
        job
    )

    letter = generate_cover_letter(
        profile,
        job
    )

    print()
    print("=" * 60)

    print(
        f"Job: {job.get('title', '')}"
    )

    print(
        f"Company: {job.get('company', '')}"
    )

    print()

    print(
        "Matching skills:"
    )

    if matching_skills:

        print(
            "  "
            + ", ".join(
                matching_skills
            )
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

        for item in relevant_experience:

            print(
                f"  {item.get('title', '')} "
                f"at "
                f"{item.get('company', '')}"
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
                f"  {project.get('name', '')}"
            )

    else:

        print(
            "  None"
        )

    print()

    print(
        "Generated cover letter:"
    )

    print(
        "-" * 60
    )

    print(letter)

    print(
        "-" * 60
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("COVER LETTER TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Test jobs
    # --------------------------------------------------------

    test_jobs = [

        {
            "title": "Backend Developer",
            "company": "Test Company",
            "description": """
            We are looking for a Backend Developer
            with experience in Python, Flask, REST APIs,
            SQL, databases and Git.
            The successful candidate will develop APIs,
            implement backend functionality and
            collaborate with the development team.
            """
        },

        {
            "title": "Frontend Developer",
            "company": "Test Company",
            "description": """
            We are looking for a Frontend Developer
            with experience in HTML, CSS, JavaScript,
            React and Next.js.
            The candidate will build responsive web
            interfaces and work with backend developers.
            """
        },

        {
            "title": "Full Stack Developer",
            "company": "Test Company",
            "description": """
            We are looking for a Full Stack Developer
            with experience in Python, Flask, REST APIs,
            JavaScript, React, SQL and Git.
            """
        }
    ]

    # --------------------------------------------------------
    # Test each job
    # --------------------------------------------------------

    for job in test_jobs:

        print_cover_letter_test(
            job
        )

        output = tailor_cover_letter(
            job,
            APPLICATIONS_DIR / "test-application"
        )

        print()
        print(
            f"Created cover letter: {output}"
        )

    print()
    print("=" * 60)
    print("COVER LETTER TEST COMPLETE")
    print("=" * 60)