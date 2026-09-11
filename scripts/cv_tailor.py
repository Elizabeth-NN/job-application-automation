import json
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


PROFILE_FILE = Path("data/candidate_profile.json")
APPLICATIONS_DIR = Path("applications")


def load_candidate_profile():
    """Load the candidate profile."""

    if not PROFILE_FILE.exists():
        raise FileNotFoundError(
            f"Candidate profile not found: {PROFILE_FILE}"
        )

    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(text):
    """Normalize text for keyword matching."""

    return re.sub(
        r"[^a-z0-9+#.]",
        " ",
        text.lower()
    )


def get_job_keywords(job):
    """Extract useful keywords from a job description."""

    text = normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        """
    )

    return set(text.split())


def skill_is_relevant(skill, job_text):
    """Check whether a candidate skill appears relevant to the job."""

    normalized_skill = normalize_text(skill)

    if not normalized_skill:
        return False

    return normalized_skill in job_text


def select_relevant_skills(profile, job):
    """Select candidate skills relevant to the job."""

    job_text = normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        """
    )

    relevant = {}

    for category, skills in profile["technical_skills"].items():

        matched = []

        for skill in skills:

            if skill_is_relevant(skill, job_text):
                matched.append(skill)

        if matched:
            relevant[category] = matched

    return relevant


def select_relevant_experience(profile, job):
    """Select experience containing skills relevant to the job."""

    job_text = normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        """
    )

    selected = []

    for experience in profile["experience"]:

        experience_text = normalize_text(
            f"""
            {experience['title']}
            {experience['company']}
            {' '.join(experience['responsibilities'])}
            """
        )

        # Keep software experience by default
        if (
            "software" in experience_text
            or "backend" in experience_text
            or "python" in experience_text
            or "flask" in experience_text
            or "api" in experience_text
        ):
            selected.append(experience)
            continue

        # Keep other experience if it has meaningful keyword overlap
        job_words = set(job_text.split())
        experience_words = set(experience_text.split())

        overlap = job_words.intersection(experience_words)

        if len(overlap) >= 2:
            selected.append(experience)

    return selected


def select_relevant_projects(profile, job):
    """Select projects relevant to the job."""

    job_text = normalize_text(
        f"""
        {job.get("title", "")}
        {job.get("description", "")}
        {job.get("requirements", "")}
        {job.get("skills", "")}
        """
    )

    selected = []

    for project in profile["projects"]:

        project_text = normalize_text(
            f"""
            {project['name']}
            {project.get('description', '')}
            {' '.join(project.get('responsibilities', []))}
            {' '.join(project.get('technologies', []))}
            """
        )

        job_words = set(job_text.split())
        project_words = set(project_text.split())

        overlap = job_words.intersection(project_words)

        if len(overlap) >= 1:
            selected.append(project)

    # Always keep the strongest software projects
    if not selected:
        selected = profile["projects"][:2]

    return selected


def create_document():
    """Create a new Word document."""

    document = Document()

    styles = document.styles

    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10)

    return document


def add_heading(document, text, size=14):
    """Add a formatted section heading."""

    paragraph = document.add_paragraph()

    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(size)

    return paragraph


def add_bullet(document, text):
    """Add a bullet point."""

    paragraph = document.add_paragraph(
        style="List Bullet"
    )

    paragraph.paragraph_format.space_after = Pt(2)

    run = paragraph.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(10)

    return paragraph


def add_contact_header(document, profile):
    """Add candidate contact information."""

    personal = profile["personal"]

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = paragraph.add_run(personal["name"])
    run.bold = True
    run.font.size = Pt(18)
    run.font.name = "Arial"

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    contact = (
        f"{personal['phone']} | "
        f"{personal['email']} | "
        f"{personal['location']}"
    )

    run = paragraph.add_run(contact)
    run.font.size = Pt(9)

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    links = (
        f"{personal['linkedin']} | "
        f"{personal['github']}"
    )

    run = paragraph.add_run(links)
    run.font.size = Pt(9)


def add_summary(document, profile):
    """Add professional summary."""

    add_heading(document, "PROFESSIONAL SUMMARY")

    paragraph = document.add_paragraph(
        profile["professional_summary"]
    )

    paragraph.paragraph_format.space_after = Pt(6)


def add_skills(document, skills):
    """Add relevant technical skills."""

    add_heading(document, "TECHNICAL SKILLS")

    for category, skill_list in skills.items():

        if not skill_list:
            continue

        category_name = category.replace(
            "_",
            " "
        ).title()

        paragraph = document.add_paragraph()

        run = paragraph.add_run(
            f"{category_name}: "
        )

        run.bold = True

        paragraph.add_run(
            ", ".join(skill_list)
        )


def add_experience(document, experience):
    """Add selected work experience."""

    add_heading(document, "WORK EXPERIENCE")

    for item in experience:

        paragraph = document.add_paragraph()

        run = paragraph.add_run(
            item["title"]
        )

        run.bold = True

        paragraph.add_run(
            f" | {item['company']}"
        )

        paragraph.add_run(
            f" | {item['start_date']} – "
            f"{item['end_date']}"
        )

        for responsibility in item["responsibilities"]:
            add_bullet(
                document,
                responsibility
            )


def add_projects(document, projects):
    """Add selected projects."""

    add_heading(document, "PROJECTS")

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

        paragraph = document.add_paragraph(
            project.get("description", "")
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


def add_education(document, education):
    """Add education."""

    add_heading(document, "EDUCATION")

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


def tailor_cv(job, output_directory):
    """
    Generate a tailored CV for a specific job.
    """

    profile = load_candidate_profile()

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

    document = create_document()

    add_contact_header(
        document,
        profile
    )

    add_summary(
        document,
        profile
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
        profile["education"]
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_directory / "tailored_cv.docx"
    )

    document.save(output_file)

    return output_file


if __name__ == "__main__":

    # Simple test job
    test_job = {
        "title": "Backend Developer",
        "description": """
        We are looking for a backend developer with
        Python, Flask, REST APIs, SQL and Git experience.
        """
    }

    output = tailor_cv(
        test_job,
        APPLICATIONS_DIR / "test-application"
    )

    print(
        f"Created tailored CV: {output}"
    )