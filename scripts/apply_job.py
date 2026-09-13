"""
Job application engine.

Responsible for submitting an application to a job.

The application manager decides which job to process
and prepares the required documents.

This module handles the actual application process.
"""


def apply_to_job(
    job,
    cv_path=None,
    cover_letter_path=None
):
    """
    Apply to a job.

    Args:
        job: Dictionary containing job information.
        cv_path: Path to the CV to use.
        cover_letter_path: Path to the cover letter.

    Returns:
        Dictionary containing the application result.
    """

    print()
    print("=" * 60)
    print("JOB APPLICATION")
    print("=" * 60)
    print()

    print(f"Job: {job.get('title', '')}")
    print(f"Company: {job.get('company', '')}")
    print(f"URL: {job.get('url', '')}")

    if cv_path:
        print(f"CV: {cv_path}")

    if cover_letter_path:
        print(f"Cover Letter: {cover_letter_path}")

    print()
    print("Actual application submission is not implemented yet.")
    print()

    return {
        "success": False,
        "status": "Not Submitted",
        "message": "Application submission not implemented yet.",
    }


if __name__ == "__main__":

    test_job = {
        "title": "Backend Developer",
        "company": "Test Company",
        "url": "https://example.com/job",
    }

    result = apply_to_job(
        test_job,
        cv_path="cv/backend_cv.pdf",
        cover_letter_path="applications/test/cover_letter.docx",
    )

    print(result)