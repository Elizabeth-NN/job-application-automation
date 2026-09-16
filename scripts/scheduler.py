
import subprocess
import sys


def run_automation():
    """Run the complete job-search automation pipeline."""

    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.automation",
        ],
        check=False,
    )


if __name__ == "__main__":
    run_automation()
