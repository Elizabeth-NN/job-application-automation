from pathlib import Path

from openpyxl import load_workbook


TRACKER_FILE = Path("data/job_tracker.xlsx")


def review_jobs():
    """Display jobs that need to be reviewed or applied for."""

    if not TRACKER_FILE.exists():
        print("Job tracker not found.")
        print(f"Expected file: {TRACKER_FILE}")
        return

    workbook = load_workbook(TRACKER_FILE, read_only=True)
    sheet = workbook["Jobs"]

    jobs = []

    for row in sheet.iter_rows(min_row=2, values_only=True):

        if not row[1]:
            continue

        job = {
            "date_found": row[0],
            "title": row[1],
            "company": row[2],
            "location": row[3],
            "score": row[4] or 0,
            "category": row[5],
            "recommendation": row[6],
            "role_match": row[7],
            "matching_skills": row[8],
            "missing_skills": row[9],
            "warnings": row[10],
            "posted": row[11],
            "deadline": row[12],
            "url": row[13],
            "status": row[14] or "Not Applied",
        }

        # Only show jobs that still need attention
        if (
            job["status"] == "Not Applied"
            and job["recommendation"] in ("APPLY", "REVIEW")
        ):
            jobs.append(job)

    workbook.close()

    # Highest score first
    jobs.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    print("=" * 60)
    print("JOBS TO REVIEW")
    print("=" * 60)
    print()

    if not jobs:
        print("No jobs currently require review.")
        return

    print(f"Found {len(jobs)} jobs to review.")
    print()

    for index, job in enumerate(jobs, start=1):

        print("-" * 60)

        print(
            f"{index}. {job['score']}% — "
            f"{job['title']}"
        )

        print(
            f"   Company: {job['company']}"
        )

        print(
            f"   Location: {job['location']}"
        )

        print(
            f"   Category: {job['category']}"
        )

        print(
            f"   Recommendation: "
            f"{job['recommendation']}"
        )

        if job["role_match"]:
            print(
                f"   Role match: "
                f"{job['role_match']}"
            )

        if job["matching_skills"]:
            print(
                f"   Matching skills: "
                f"{job['matching_skills']}"
            )

        if job["missing_skills"]:
            print(
                f"   Missing skills: "
                f"{job['missing_skills']}"
            )

        if job["warnings"]:
            print(
                f"   Warnings: "
                f"{job['warnings']}"
            )

        if job["deadline"]:
            print(
                f"   Deadline: "
                f"{job['deadline']}"
            )

        print(
            f"   URL: {job['url']}"
        )

        print()


if __name__ == "__main__":
    review_jobs()