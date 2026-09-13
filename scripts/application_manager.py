"""
Application manager.

Coordinates the generation of a complete job application:

    Job
      ↓
    Tailored CV
      ↓
    Tailored Cover Letter
      ↓
    Application folder

The manager does not decide whether a candidate should apply.
That decision is handled by the job matcher/reviewer.
"""

from pathlib import Path

from scripts.cv_tailor import tailor_cv
from scripts.cover_letter import save_cover_letter


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

APPLICATIONS_DIR = BASE_DIR / "applications"


# ============================================================
# APPLICATION DIRECTORY
# ============================================================

def create_application_directory(job):
    """
    Create the directory for a specific job application.

    Example:

        applications/
        └── company-backend-developer/
    """

    company = job.get(
        "company",
        "company"
    )

    title = job.get(
        "title",
        "software-developer"
    )

    # Convert to strings in case the source gives us
    # unexpected values.
    company = str(company).strip()
    title = str(title).strip()

    directory_name = (
        f"{company}-{title}"
    )

    # Keep only filesystem-safe characters.
    safe_name = "".join(
        character.lower()
        if character.isalnum()
        else "-"
        for character in directory_name
    )

    # Remove repeated hyphens.
    while "--" in safe_name:
        safe_name = safe_name.replace(
            "--",
            "-"
        )

    safe_name = safe_name.strip("-")

    if not safe_name:
        safe_name = "application"

    # Prevent excessively long directory names.
    safe_name = safe_name[:120]

    output_directory = (
        APPLICATIONS_DIR / safe_name
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return output_directory


# ============================================================
# APPLICATION GENERATION
# ============================================================

def generate_application(
    job,
    match=None
):
    """
    Generate a complete application for one job.

    Generates:

        tailored_cv.docx
        cover_letter.docx

    Returns a dictionary containing the generated files.
    """

    print()
    print("=" * 60)
    print("GENERATING APPLICATION")
    print("=" * 60)

    print()
    print(
        f"Job: {job.get('title', 'Unknown')}"
    )

    print(
        f"Company: {job.get('company', 'Unknown')}"
    )

    # --------------------------------------------------------
    # Create application directory
    # --------------------------------------------------------

    output_directory = create_application_directory(
        job
    )

    print()
    print(
        f"Application directory:"
    )
    print(
        f"  {output_directory}"
    )

    # --------------------------------------------------------
    # Generate tailored CV
    # --------------------------------------------------------

    print()
    print("Generating tailored CV...")

    cv_path = tailor_cv(
        job,
        output_directory=output_directory
    )

    print(
        f"✓ CV created:"
    )

    print(
        f"  {cv_path}"
    )

    # --------------------------------------------------------
    # Generate cover letter
    # --------------------------------------------------------

    print()
    print("Generating cover letter...")

    cover_letter_path = save_cover_letter(
        job,
        match=match,
        output_directory=output_directory
    )

    print(
        f"✓ Cover letter created:"
    )

    print(
        f"  {cover_letter_path}"
    )

    # --------------------------------------------------------
    # Return generated files
    # --------------------------------------------------------

    return {
        "directory": output_directory,
        "cv": cv_path,
        "cover_letter": cover_letter_path,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("APPLICATION MANAGER TEST")
    print("=" * 60)

    test_job = {
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
    }

    result = generate_application(
        test_job
    )

    print()
    print("=" * 60)
    print("APPLICATION GENERATED")
    print("=" * 60)

    print()
    print(
        f"Directory: {result['directory']}"
    )

    print(
        f"CV: {result['cv']}"
    )

    print(
        f"Cover letter: {result['cover_letter']}"
    )

    print()