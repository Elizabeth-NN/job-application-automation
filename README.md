# 💼 Job Application Assistant

A Python-based job search and application management tool that helps streamline the process of finding relevant software development opportunities, evaluating job matches, and preparing tailored application documents.

The application collects job listings, evaluates them against a candidate's technical profile, tracks applications, and generates job-specific CVs and cover letters.

A Streamlit web interface provides a graphical alternative to the command-line workflow.

---

## 🚀 Features

### Job Collection

The application can collect job listings from supported job boards and extract information such as:

* Job title
* Company
* Location
* Job description
* Requirements
* Skills
* Experience requirements
* Application deadline
* Job URL
* Posting information

### Job Matching

Each job is evaluated against the candidate profile using a matching engine.

The matching system considers factors such as:

* Target role
* Technical skills
* Experience level
* Location
* Education
* Technologies

Jobs receive a match score and recommendation, such as:

* `APPLY`
* `REVIEW`
* `SKIP`

The system also identifies:

* Matching skills
* Missing skills
* Potential warnings
* Role alignment

### Job Tracker

Job information is stored in an Excel-based tracker.

The tracker records:

* Date found
* Job title
* Company
* Location
* Match score
* Recommendation
* Matching skills
* Missing skills
* Warnings
* Posting date
* Deadline
* Application URL
* Application status
* CV version
* Cover letter status
* Notes

### Tailored CV Generation

The CV tailoring engine creates a job-specific CV from the candidate profile.

It can:

* Identify relevant technical skills
* Select relevant professional experience
* Rank relevant projects
* Generate a tailored professional summary
* Create a formatted `.docx` CV

The goal is to emphasize information that is relevant to each individual job rather than using exactly the same CV for every application.

### Cover Letter Generation

The application can generate a job-specific cover letter using:

* Target job title
* Company
* Matching technical skills
* Relevant experience
* Relevant projects

Cover letters are generated as Word documents.

### Application Management

The application manager brings the process together by allowing the user to:

1. Review matched jobs
2. Select a job
3. Prepare application documents
4. Review the generated CV and cover letter
5. Record the application
6. Track application status

### Streamlit Web Interface

The project also includes a Streamlit interface that provides a graphical dashboard.

The web application provides:

* Dashboard
* Job listings
* Job filtering
* Job search
* Match scores
* Job recommendations
* Job details
* Application preparation
* Tailored CV generation
* Cover letter generation
* Application tracking

---

## 🏗️ How It Works

The application follows a pipeline:

```text
Job Sources
     │
     ▼
Job Collector
     │
     ▼
Job Details
     │
     ▼
Job Matcher
     │
     ▼
Match Score & Recommendation
     │
     ▼
Excel Job Tracker
     │
     ▼
Application Manager
     │
     ├───────────────┐
     ▼               ▼
Tailored CV      Cover Letter
     │               │
     └───────┬───────┘
             ▼
      Application Review
             │
             ▼
      Application Tracker
```

The Streamlit application provides a graphical interface over this workflow.

---

## 📁 Project Structure

```text
job-application-automation/
│
├── app.py
│
├── main.py
│
├── requirements.txt
│
├── README.md
│
├── config/
│   ├── __init__.py
│   └── profile.py
│
├── data/
│   ├── candidate_profile.json
│   └── job_tracker.xlsx
│
├── applications/
│   └── ...
│
└── scripts/
    ├── __init__.py
    ├── application_manager.py
    ├── cover_letter.py
    ├── cv_tailor.py
    ├── job_collector.py
    ├── job_matcher.py
    ├── job_tracker.py
    ├── run_job_search.py
    │
    └── sources/
        ├── __init__.py
        ├── myjobmag.py
        └── brighter_monday.py
```

### Main Components

| File                     | Purpose                                                         |
| ------------------------ | --------------------------------------------------------------- |
| `app.py`                 | Streamlit web interface                                         |
| `main.py`                | Main application entry point                                    |
| `candidate_profile.json` | Candidate information used for matching and document generation |
| `job_collector.py`       | Coordinates job collection                                      |
| `job_matcher.py`         | Calculates job compatibility                                    |
| `job_tracker.py`         | Creates and updates the Excel job tracker                       |
| `application_manager.py` | Command-line application workflow                               |
| `cv_tailor.py`           | Generates tailored CVs                                          |
| `cover_letter.py`        | Generates tailored cover letters                                |
| `run_job_search.py`      | Runs the job collection and matching process                    |
| `myjobmag.py`            | MyJobMag job source                                             |
| `brighter_monday.py`     | BrighterMonday job source                                       |

---

## 🛠️ Technologies Used

### Programming Language

* Python

### Web Interface

* Streamlit

### Document Generation

* `python-docx`

### Data Storage

* Excel
* `openpyxl`
* JSON

### Web Scraping / Job Collection

* `requests`
* `BeautifulSoup`

### Development Tools

* Git
* GitHub
* WSL / Ubuntu
* Python virtual environments

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/job-application-automation.git
```

Move into the project:

```bash
cd job-application-automation
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

### Streamlit Interface

Start the web application with:

```bash
streamlit run app.py
```

Streamlit will provide a local URL that can be opened in a web browser.

Typically:

```text
http://localhost:8501
```

### Command-Line Job Search

The job search pipeline can be run with:

```bash
python -m scripts.run_job_search
```

### Command-Line Application Manager

The original command-line application workflow can be started with:

```bash
python -m scripts.application_manager
```

### Testing the CV Tailoring Engine

```bash
python -m scripts.cv_tailor
```

### Testing the Cover Letter Generator

```bash
python -m scripts.cover_letter
```

---

## 📊 Job Matching

The matching system evaluates jobs using multiple factors rather than relying only on keyword matching.

The current matching approach considers:

```text
Role Match
    +
Technical Skills
    +
Experience
    +
Location
    +
Education
    +
Technology
    =
Overall Match Score
```

The result helps prioritize jobs that are more closely aligned with the candidate's background.

---

## 📄 Application Documents

When an application is prepared, the system creates a dedicated application directory.

For example:

```text
applications/
└── company-job-title/
    ├── tailored_cv.docx
    └── cover_letter.docx
```

This keeps documents for different applications separate and makes it easier to review applications individually.

---

## 🔐 Personal Information & Security

The application uses a candidate profile to generate personalized CVs and cover letters.

The repository should **not contain sensitive personal information, credentials, API keys, passwords, or private configuration values**.

Before publishing the repository publicly:

* Remove personal data that should not be public
* Do not commit passwords or API keys
* Do not commit authentication credentials
* Add sensitive files to `.gitignore`
* Use environment variables for secrets
* Review files before pushing them to GitHub

Example:

```text
.env
*.key
*.pem
credentials.json
```

Personal application documents should also be kept out of the public repository unless they are intentionally meant to be public.

---

## 🌐 Deployment

The Streamlit interface can be deployed to a cloud hosting service that supports Streamlit applications.

For Streamlit Community Cloud, the application needs to be stored in a GitHub repository.

The deployment entry point is:

```text
app.py
```

The repository should also contain:

```text
requirements.txt
```

so that the deployment environment can install the required Python packages.

> **Important:** A public repository should not contain private candidate information or generated application documents.

---

## 🔄 Current Workflow

The current workflow is:

```text
1. Collect jobs
        ↓
2. Extract job information
        ↓
3. Match jobs against candidate profile
        ↓
4. Store jobs in Excel tracker
        ↓
5. Review jobs
        ↓
6. Select a job
        ↓
7. Generate tailored CV
        ↓
8. Generate cover letter
        ↓
9. Review documents
        ↓
10. Apply manually
        ↓
11. Record application
```

The application is intentionally designed so that the user reviews the job and generated documents before submitting an application.

---

## 🧪 Development Status

This project is currently under active development.

### Completed

* [x] Job collection
* [x] Job matching
* [x] Match scoring
* [x] Excel job tracker
* [x] Application tracking
* [x] CV tailoring
* [x] Cover letter generation
* [x] Command-line application manager
* [x] Streamlit web interface
* [x] Job filtering
* [x] Application preparation through the web interface

### Planned

* [ ] Automated job searching
* [ ] More job-board sources
* [ ] Improved job matching
* [ ] Better CV tailoring
* [ ] Improved cover-letter personalization
* [ ] Automated application workflows
* [ ] Application status management
* [ ] Email/application notifications
* [ ] Improved dashboard analytics

---

## 🎯 Project Goal

The goal of this project is to reduce the repetitive work involved in a modern job search while keeping the candidate in control of the final application.

Instead of manually searching for jobs, comparing every job against a CV, preparing documents, and maintaining a separate application tracker, the system brings these tasks together into one workflow.

The long-term objective is to develop a personal job-search assistant capable of:

* Finding relevant opportunities
* Evaluating job compatibility
* Prioritizing applications
* Tailoring application documents
* Tracking application progress
* Reducing repetitive application tasks

---

## ⚠️ Disclaimer

This project is intended as a personal job-search productivity tool.

Job listings, requirements, deadlines, and application processes may change. Generated CVs and cover letters should always be reviewed before submission.

The application does not guarantee employment or application success.

---

## 👩‍💻 Author

Developed as a personal software engineering project.

Built with Python, Streamlit, and related open-source technologies.
