import subprocess
import sys
import time
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

INTERVAL_HOURS = 6
INTERVAL_SECONDS = INTERVAL_HOURS * 60 * 60


# ============================================================
# LOGGING
# ============================================================

def log(message):
    """Print a timestamped scheduler message."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{timestamp}] {message}", flush=True)


# ============================================================
# AUTOMATION
# ============================================================

def run_automation():
    """Run the complete job-search automation pipeline."""

    print()
    print("=" * 70)
    print("STARTING JOB SEARCH AUTOMATION")
    print("=" * 70)

    log("Launching scripts.automation...")
    print()

    start_time = time.time()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.automation",
            ],
            check=False,
        )

        elapsed = time.time() - start_time

        print()
        print("=" * 70)

        if result.returncode == 0:
            log(
                f"Automation completed successfully "
                f"in {elapsed / 60:.1f} minutes."
            )
        else:
            log(
                f"Automation finished with errors. "
                f"Exit code: {result.returncode}"
            )

        print("=" * 70)

        return result.returncode == 0

    except Exception as error:
        elapsed = time.time() - start_time

        print()
        print("=" * 70)
        log(
            f"Automation failed after "
            f"{elapsed / 60:.1f} minutes: {error}"
        )
        print("=" * 70)

        return False


# ============================================================
# SCHEDULER
# ============================================================

def run_scheduler():
    """Run the automation pipeline every configured interval."""

    print("=" * 70)
    print("JOB SEARCH SCHEDULER")
    print("=" * 70)
    print(f"Automation interval: Every {INTERVAL_HOURS} hours")
    print("Press Ctrl+C to stop the scheduler.")
    print("=" * 70)

    run_number = 1

    while True:

        print()
        print("=" * 70)
        print(f"AUTOMATION RUN #{run_number}")
        print("=" * 70)

        start_time = datetime.now()

        success = run_automation()

        end_time = datetime.now()

        print()
        print("-" * 70)

        if success:
            log(f"Run #{run_number} completed successfully.")
        else:
            log(f"Run #{run_number} completed with errors.")

        log(
            f"Run started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        log(
            f"Run finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # ----------------------------------------------------
        # Calculate next run
        # ----------------------------------------------------

        next_run = time.time() + INTERVAL_SECONDS
        next_run_time = datetime.fromtimestamp(next_run)

        print()
        log(
            f"Next automation run: "
            f"{next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        log(f"Waiting {INTERVAL_HOURS} hours...")
        print("-" * 70)

        run_number += 1

        try:
            time.sleep(INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print()
            print()
            print("=" * 70)
            log("SCHEDULER STOPPED BY USER")
            print("=" * 70)
            break


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        run_scheduler()

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 70)
        log("SCHEDULER STOPPED BY USER")
        print("=" * 70)