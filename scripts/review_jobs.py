from pathlib import Path

from openpyxl import load_workbook


TRACKER_FILE = Path("data/job_tracker.xlsx")


def load_jobs():
    """Load jobs that still need attention."""

    if not TRACKER_FILE.exists():
        print("Job tracker not found.")
        print(f"Expected file: {TRACKER_FILE}")
        return []

    workbook = load_workbook(
        TRACKER_FILE,
        read_only=True
    )

    sheet = workbook["Jobs"]

    jobs = []

    for row_number, row in enumerate(
        sheet.iter_rows(
            min_row=2,
            values_only=True
        ),
        start=2
    ):

        if not row[1]:
            continue

        recommendation = row[6]
        status = row[14] or "Not Applied"

        if (
            status == "Not Applied"
            and recommendation in ("APPLY", "REVIEW")
        ):

            jobs.append({
                "row_number": row_number,
                "date_found": row[0],
                "title": row[1],
                "company": row[2],
                "location": row[3],
                "score": row[4] or 0,
                "category": row[5],
                "recommendation": recommendation,
                "role_match": row[7],
                "matching_skills": row[8],
                "missing_skills": row[9],
                "warnings": row[10],
                "posted": row[11],
                "deadline": row[12],
                "url": row[13],
                "status": status,
            })

    workbook.close()

    jobs.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    return jobs


def display_job_list(jobs):
    """Display the jobs that need attention."""

    print()
    print("=" * 60)
    print("JOBS TO REVIEW")
    print("=" * 60)
    print()

    if not jobs:
        print("No jobs currently require review.")
        return

    print(
        f"Found {len(jobs)} jobs to review."
    )
    print()

    for index, job in enumerate(jobs, start=1):

        print(
            f"{index}. "
            f"{job['score']}% — "
            f"{job['title']}"
        )

        print(
            f"   {job['company']} | "
            f"{job['location']} | "
            f"{job['recommendation']}"
        )

    print()


def display_job(job):
    """Display detailed information about a job."""

    print()
    print("=" * 60)
    print(job["title"])
    print("=" * 60)

    print(
        f"Company: {job['company']}"
    )

    print(
        f"Location: {job['location']}"
    )

    print(
        f"Score: {job['score']}%"
    )

    print(
        f"Category: {job['category']}"
    )

    print(
        f"Recommendation: "
        f"{job['recommendation']}"
    )

    if job["role_match"]:
        print(
            f"Role match: "
            f"{job['role_match']}"
        )

    if job["matching_skills"]:
        print()
        print("Matching skills:")
        print(
            f"  {job['matching_skills']}"
        )

    if job["missing_skills"]:
        print()
        print("Missing skills:")
        print(
            f"  {job['missing_skills']}"
        )

    if job["warnings"]:
        print()
        print("Warnings:")
        print(
            f"  {job['warnings']}"
        )

    if job["posted"]:
        print()
        print(
            f"Posted: {job['posted']}"
        )

    if job["deadline"]:
        print(
            f"Deadline: {job['deadline']}"
        )

    print()
    print("URL:")
    print(job["url"])

    print()


def update_status(row_number, status):
    """Update the application status in Excel."""

    workbook = load_workbook(
        TRACKER_FILE
    )

    sheet = workbook["Jobs"]

    # Column O = Application Status
    sheet.cell(
        row=row_number,
        column=15
    ).value = status

    workbook.save(TRACKER_FILE)

    workbook.close()


def job_actions(job):
    """Show actions for a selected job."""

    while True:

        print("-" * 60)
        print("What do you want to do?")
        print()
        print("1. Mark as To Apply")
        print("2. Mark as Applied")
        print("3. Mark as Rejected")
        print("4. Skip")
        print("5. Back")
        print()

        choice = input(
            "Choose an option: "
        ).strip()

        if choice == "1":

            update_status(
                job["row_number"],
                "To Apply"
            )

            print()
            print("✓ Job marked as To Apply.")
            return

        elif choice == "2":

            update_status(
                job["row_number"],
                "Applied"
            )

            print()
            print("✓ Job marked as Applied.")
            return

        elif choice == "3":

            update_status(
                job["row_number"],
                "Rejected"
            )

            print()
            print("✓ Job marked as Rejected.")
            return

        elif choice == "4":

            update_status(
                job["row_number"],
                "Withdrawn"
            )

            print()
            print("✓ Job skipped.")
            return

        elif choice == "5":

            return

        else:

            print()
            print("Invalid option.")
            print("Please choose 1-5.")


def review_jobs():
    """Interactive job review."""

    while True:

        jobs = load_jobs()

        display_job_list(jobs)

        if not jobs:
            return

        print(
            "Enter a job number to view details."
        )

        print(
            "Enter 'q' to quit."
        )

        print()

        choice = input(
            "Select job: "
        ).strip().lower()

        if choice == "q":
            print()
            print("Exiting job review.")
            return

        try:
            job_number = int(choice)

        except ValueError:

            print()
            print(
                "Please enter a valid job number."
            )

            continue

        if not 1 <= job_number <= len(jobs):

            print()
            print(
                "Invalid job number."
            )

            continue

        selected_job = jobs[
            job_number - 1
        ]

        display_job(selected_job)

        job_actions(selected_job)


if __name__ == "__main__":
    review_jobs()