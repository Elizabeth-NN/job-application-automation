# Job Application Assistant

A Python-based job search and application-preparation system that collects software and technology job opportunities, analyzes them against a candidate profile, tracks applications, and generates tailored CVs and cover letters.

The project uses browser automation with Playwright to collect and inspect jobs from **MyJobMag** and **BrighterMonday**, then processes each opportunity through a job-matching pipeline.

## Features

* Collects job listings from MyJobMag and BrighterMonday
* Uses Playwright for browser-based job inspection
* Extracts job details, requirements, skills, experience, and application information
* Filters BrighterMonday listings to identify technology-related roles
* Matches jobs against a candidate profile
* Calculates a compatibility score
* Categorizes jobs as strong, weak, or poor matches
* Recommends jobs for application or skipping
* Detects external application links and application methods
* Prevents duplicate jobs from being repeatedly added to the tracker
* Generates tailored CVs for suitable positions
* Generates customized cover letters
* Stores job and application information in an Excel tracker
* Provides a Streamlit interface for reviewing job opportunities and application data
* Supports scheduled execution through Linux cron
* Keeps automatic application submission disabled, allowing applications to be reviewed and submitted manually

## Architecture

```text
                    Job Application Assistant
                              |
                 +------------+------------+
                 |                         |
                 v                         v
          Job Collection             Streamlit UI
                 |
        +--------+--------+
        |                 |
        v                 v
    MyJobMag        BrighterMonday
        |                 |
        +--------+--------+
                 |
                 v
          Browser Inspection
                 |
                 v
           Job Matching
                 |
                 v
           Job Tracker
                 |
        +--------+--------+
        |                 |
        v                 v
      SKIP              APPLY
                          |
                          v
              Tailored CV + Cover Letter
```

## Project Structure

```text
job-application-automation/
│
├── README.md
├── app.py
├── push.sh
├── requirements.txt
│
├── applications/
│   └── <company-job>/
│       ├── tailored_cv.docx
│       └── cover_letter.docx
│
├── config/
│   └── __init__.py
│
├── data/
│   ├── candidate_profile.json
│   └── job_tracker.xlsx
│
└── scripts/
    ├── __init__.py
    ├── automation.py
    ├── cover_letter.py
    ├── cv_tailor.py
    ├── job_matcher.py
    ├── job_tracker.py
    ├── review_jobs.py
    ├── scheduler.py
    │
    └── browser/
        ├── __init__.py
        ├── browser.py
        ├── brighter_monday.py
        └── myjobmag.py
```

## Technologies

* **Python**
* **Playwright**
* **Streamlit**
* **pandas**
* **openpyxl**
* **python-docx**
* **Flask/REST API experience reflected in candidate matching**
* **Git/GitHub**
* **Linux/WSL**
* **cron**

## Job Processing Pipeline

Each collected job goes through the following process:

### 1. Collection

The system collects job listings from:

* MyJobMag
* BrighterMonday

### 2. Browser Inspection

Playwright opens individual job pages and extracts information such as:

* Job title
* Company
* Location
* Job type
* Qualification
* Experience
* Responsibilities
* Requirements
* Skills
* Posting date
* Deadline
* Application method
* Application URL

### 3. Job Matching

The extracted job information is compared with the candidate profile.

The matching system considers factors including:

* Role relevance
* Technical skills
* Experience
* Location
* Education
* Technology stack

The result includes a compatibility score and recommendation.

### 4. Tracking

Jobs are stored in:

```text
data/job_tracker.xlsx
```

The tracker records information such as:

* Date found
* Job title
* Company
* Location
* Match score
* Recommendation
* Matching skills
* Missing skills
* Warnings
* Posting information
* Deadline
* Application URL
* Application status
* CV version
* Cover letter
* Notes

### 5. Application Preparation

For suitable opportunities, the system creates an application directory containing:

```text
tailored_cv.docx
cover_letter.docx
```

For example:

```text
applications/
└── simplepay-backend-developer/
    ├── tailored_cv.docx
    └── cover_letter.docx
```

## Streamlit Interface

The project includes a Streamlit interface through:

```text
app.py
```

Run it with:

```bash
streamlit run app.py
```

The interface provides a user-friendly way to review the jobs and application information produced by the automation pipeline.

The Streamlit interface and the browser automation are intentionally separated.

```text
Automation
    ↓
job_tracker.xlsx
    ↓
Streamlit
    ↓
Review jobs and applications
```

This allows the automation to be run independently without requiring the Streamlit application to remain open.

## Running the Automation

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run the complete automation pipeline:

```bash
python -m scripts.automation
```

The pipeline will:

```text
Collect jobs
    ↓
Inspect jobs
    ↓
Match jobs
    ↓
Update tracker
    ↓
Prepare applications for suitable jobs
```

Automatic application submission is currently disabled. The system prepares the relevant documents and application information for manual review and submission.

## Scheduling

The project supports Linux cron for scheduled job searches.

A cron job can execute the automation every six hours:

```text
00:00
06:00
12:00
18:00
```

The automation output can be redirected to:

```text
logs/automation.log
```

However, scheduled execution is optional. The automation can also be run manually whenever required.

## Browser Layers

Browser-specific functionality is separated into individual modules.

### MyJobMag

```text
scripts/browser/myjobmag.py
```

Responsible for:

* Collecting job links
* Inspecting job pages
* Extracting structured information
* Detecting application methods

### BrighterMonday

```text
scripts/browser/brighter_monday.py
```

Responsible for:

* Searching the Software & Data category
* Paginating through listings
* Filtering technology-related jobs
* Inspecting individual job pages
* Extracting job and application information

### Shared Browser

```text
scripts/browser/browser.py
```

Provides shared browser startup and shutdown functionality.

The browser modules do **not** automatically submit applications.

## Configuration

Candidate information used by the matching and document-generation system is stored in:

```text
data/candidate_profile.json
```

This keeps candidate-specific information separate from the application logic.

Sensitive personal information should not be committed to a public repository.

## Installation

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd job-application-automation
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the Playwright browser:

```bash
playwright install chromium
```

## Usage

### Run job automation

```bash
python -m scripts.automation
```

### Launch the Streamlit interface

```bash
streamlit run app.py
```

### Run the Python scheduler manually

```bash
python -m scripts.scheduler
```

The Python scheduler is available as an alternative scheduling mechanism. For regular Linux scheduling, cron can execute `scripts.automation` directly.

## Current Scope

The system currently focuses on:

* Job discovery
* Job analysis
* Candidate-job matching
* Application tracking
* CV customization
* Cover-letter generation
* Application preparation

Automatic submission of job applications is intentionally **not implemented**.

This allows the candidate to review each opportunity before submitting an application, particularly when external application systems require different workflows.

## Future Improvements

Potential future enhancements include:

* Additional job sources
* More advanced job-ranking and matching
* Email notifications for new matches
* Improved Streamlit analytics
* Application status management
* Automated application workflows for supported platforms
* Cloud/server-based scheduled execution
* More detailed execution logs
* Database-backed job tracking instead of Excel
* Authentication and user accounts for the Streamlit interface

## Project Goal

The goal of the project is to reduce the repetitive work involved in searching for software development opportunities and preparing applications while keeping the candidate in control of the final application decision.

The system automates the repetitive parts of the workflow:

```text
Discover
   ↓
Inspect
   ↓
Match
   ↓
Track
   ↓
Prepare
   ↓
Review
   ↓
Apply
```

It is designed as a practical automation project combining **Python, web automation, data processing, document generation, and a Streamlit interface**.
