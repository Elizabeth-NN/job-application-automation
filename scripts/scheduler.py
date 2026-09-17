
import subprocess
import sys
import time
from datetime import datetime


# Run automation every 6 hours
INTERVAL_SECONDS = 6 * 60 * 60


def run_automation():
    """Run the complete job-search automation pipeline."""

    print()
    print("=" * 70)
    print("STARTING JOB SEARCH AUTOMATION")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.automation",
            ],
            check=False,
        )

        if result.returncode == 0:
            print()
            print("✓ Automation completed successfully.")
        else:
            print()
            print(
                f"⚠ Automation finished with exit code "
                f"{result.returncode}."
            )

    except Exception as error:
        print()
        print(f"✗ Automation failed: {error}")


def run_scheduler():
    """Run the automation pipeline every 6 hours."""

    print("=" * 70)
    print("JOB SEARCH SCHEDULER")
    print("=" * 70)
    print("Automation interval: Every 6 hours")
    print("Press Ctrl+C to stop the scheduler.")
    print("=" * 70)

    # Run immediately when the scheduler starts
    run_automation()

    while True:
        next_run = datetime.now().timestamp() + INTERVAL_SECONDS
        next_run_time = datetime.fromtimestamp(next_run)

        print()
        print("-" * 70)
        print(
            "Next automation run:",
            next_run_time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        print("Waiting for 6 hours...")
        print("-" * 70)

        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print()
            print("=" * 70)
            print("SCHEDULER STOPPED")
            print("=" * 70)
            break

        run_automation()


if __name__ == "__main__":
    run_scheduler()