"""
Job matching and scoring engine.

Evaluates how well a job matches Elizabeth's profile.

The matcher considers:

    1. Whether the job is actually a software/technology role
    2. Role relevance
    3. Technical skill overlap
    4. Transferable skills
    5. Missing skills
    6. Experience requirements
    7. Location
    8. Education
    9. Technology stack compatibility

The candidate profile is loaded from:

    data/candidate_profile.json

The goal is to estimate whether a job is realistically worth
applying for, rather than simply counting keywords.
"""

import json
import re
from pathlib import Path


# ============================================================
# CANDIDATE PROFILE
# ============================================================

PROFILE_FILE = Path("data/candidate_profile.json")


def load_candidate_profile():
    """
    Load Elizabeth's candidate profile from JSON.
    """

    if not PROFILE_FILE.exists():
        raise FileNotFoundError(
            f"Candidate profile not found: {PROFILE_FILE}"
        )

    with open(
        PROFILE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def get_job_profile():
    """
    Build the job-matching profile from candidate_profile.json.

    The candidate JSON remains the single source of truth for
    Elizabeth's skills and education.
    """

    profile = load_candidate_profile()

    target_roles = [
        "python developer",
        "backend developer",
        "backend engineer",
        "software developer",
        "software engineer",
        "full stack developer",
        "fullstack developer",
        "web developer",
        "frontend developer",
        "frontend engineer",
    ]

    core_skills = []

    for skills in profile.get(
        "technical_skills",
        {}
    ).values():

        core_skills.extend(
            skill.lower()
            for skill in skills
        )

    return {
        "target_roles": list(
            dict.fromkeys(target_roles)
        ),

        "core_skills": list(
            dict.fromkeys(core_skills)
        ),

        "locations": [
            "nairobi",
            "kenya",
            "remote",
            "hybrid",
        ],

        "education": [
            education["qualification"].lower()
            for education in profile.get(
                "education",
                []
            )
            if education.get("qualification")
        ],
    }


# ============================================================
# KNOWN SKILLS
# ============================================================

ALL_SKILLS = [

    # Python / Backend
    "python",
    "flask",
    "django",
    "fastapi",

    # APIs
    "rest api",
    "restful api",
    "api development",

    # Databases
    "sql",
    "postgresql",
    "mysql",
    "database design",
    "database",
    "mongodb",
    "oracle",
    "sqlite",
    "sqlalchemy",

    # Frontend
    "react",
    "react.js",
    "javascript",
    "typescript",
    "html",
    "css",
    "next.js",
    "tailwind css",
    "angular",
    "vue.js",

    # Tools
    "git",
    "github",
    "docker",
    "aws",

    # Other technologies
    "java",
    "spring boot",
    "go",
    "node.js",
    "node",
    "rpa",
    "erp",
    "fineract",
    "dynamics 365",
    "servicenow",
    ".net",
    "c#",
]


# ============================================================
# TRANSFERABLE SKILLS
# ============================================================

TRANSFERABLE_SKILLS = {

    "postgresql",
    "mysql",
    "mongodb",
    "django",
    "fastapi",
    "typescript",
    "node.js",
    "node",
    "github",
    "docker",
}


# ============================================================
# TECHNOLOGIES OUTSIDE PRIMARY STACK
# ============================================================

OUTSIDE_TECHNOLOGIES = {

    "go": "Go",
    "java": "Java",
    "spring boot": "Spring Boot",
    "angular": "Angular",
    "oracle": "Oracle",
    "dynamics 365": "Dynamics 365",
    "servicenow": "ServiceNow",
    "rpa": "RPA",
    "erp": "ERP",
    "fineract": "Fineract",
    ".net": ".NET",
    "c#": "C#",
    "vue.js": "Vue.js",
}


# ============================================================
# NON-SOFTWARE JOB INDICATORS
# ============================================================

NON_SOFTWARE_ROLES = [

    "sales representative",
    "sales agent",
    "sales associate",
    "sales officer",
    "sales manager",
    "sales executive",
    "sales and marketing",
    "business development officer",
    "business development executive",
    "relationship officer",
    "relationship manager",
    "field collection officer",
    "collection officer",
    "delivery driver",
    "driver",
    "teacher",
    "accountant",
    "finance assistant",
    "finance officer",
    "administrator",
    "hr administrator",
    "human resources",
    "marketer",
    "marketing officer",
    "graphic designer",
    "project assistant",
    "program officer",
    "wines and spirits attendant",
]


# ============================================================
# SOFTWARE ROLE INDICATORS
# ============================================================

SOFTWARE_ROLE_KEYWORDS = [

    "developer",
    "development",
    "software",
    "software engineer",
    "engineer",
    "engineering",
    "programmer",
    "programming",
    "webmaster",
    "web developer",
    "backend",
    "back-end",
    "frontend",
    "front-end",
    "full stack",
    "fullstack",
    "devops",
    "data engineer",
    "data developer",
    "application developer",
    "applications developer",
    "systems developer",
    "systems engineer",
    "technical developer",
    "technology developer",
    "it developer",
    "api developer",
]


# ============================================================
# EXPERIENCE KEYWORDS
# ============================================================

SENIOR_TITLE_KEYWORDS = [
    "senior",
    "lead",
    "principal",
    "head of",
    "manager",
    "director",
]

EXPERIENCED_TITLE_KEYWORDS = [
    "mid-level",
    "mid level",
    "midlevel",
    "intermediate",
    "experienced",
]

JUNIOR_TITLE_KEYWORDS = [
    "junior",
    "entry level",
    "entry-level",
    "graduate",
    "trainee",
    "intern",
    "internship",
    "fresh graduate",
]


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize(text):
    """
    Normalize text for easier matching.
    """

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9+#.\-/ ]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_term(text, term):
    """
    Check whether a term exists as a meaningful word/phrase.
    """

    text = normalize(text)
    term = normalize(term)

    if not text or not term:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(term)
        + r"(?!\w)"
    )

    return re.search(
        pattern,
        text
    ) is not None


# ============================================================
# JOB TYPE
# ============================================================

def is_software_role(title, description=""):
    """
    Determine whether a job is primarily a software /
    technology position.

    The title receives more importance than generic words
    appearing in the description.
    """

    normalized_title = normalize(title)

    # Strong non-software title detection.
    for keyword in NON_SOFTWARE_ROLES:

        if contains_term(
            normalized_title,
            keyword
        ):

            return False

    # Strong software title detection.
    for keyword in SOFTWARE_ROLE_KEYWORDS:

        if contains_term(
            normalized_title,
            keyword
        ):

            return True

    # If the title is ambiguous, inspect the description.
    normalized_description = normalize(
        description
    )

    software_indicators = 0

    for keyword in SOFTWARE_ROLE_KEYWORDS:

        if contains_term(
            normalized_description,
            keyword
        ):

            software_indicators += 1

    # Technology stack can also indicate a software role.
    technology_matches = find_job_skills(
        normalized_description
    )

    if len(technology_matches) >= 2:
        software_indicators += 2

    return software_indicators >= 3


# ============================================================
# ROLE MATCHING
# ============================================================

def find_role_matches(title):
    """
    Find target roles appearing in the job title.
    """

    job_profile = get_job_profile()

    matches = []

    normalized_title = normalize(title)

    for role in job_profile["target_roles"]:

        if contains_term(
            normalized_title,
            role
        ):

            matches.append(role)

    return list(
        dict.fromkeys(matches)
    )


# ============================================================
# PROFILE SKILL MATCHING
# ============================================================

def find_matching_skills(full_text):
    """
    Find core skills Elizabeth has that appear in the job.
    """

    job_profile = get_job_profile()

    matching_skills = []

    for skill in job_profile["core_skills"]:

        if contains_term(
            full_text,
            skill
        ):

            matching_skills.append(skill)

    return list(
        dict.fromkeys(matching_skills)
    )


# ============================================================
# TRANSFERABLE SKILLS
# ============================================================

def find_transferable_skills(full_text):
    """
    Find technologies that are related to Elizabeth's
    existing skills.
    """

    matches = []

    for skill in TRANSFERABLE_SKILLS:

        if contains_term(
            full_text,
            skill
        ):

            matches.append(skill)

    return list(
        dict.fromkeys(matches)
    )


# ============================================================
# JOB SKILL EXTRACTION
# ============================================================

def find_job_skills(full_text):
    """
    Find known skills/technologies mentioned in the job.
    """

    job_skills = []

    for skill in ALL_SKILLS:

        if contains_term(
            full_text,
            skill
        ):

            job_skills.append(skill)

    # Remove aliases where appropriate.
    if (
        "react.js" in job_skills
        and "react" in job_skills
    ):

        job_skills.remove("react.js")

    if (
        "node" in job_skills
        and "node.js" in job_skills
    ):

        job_skills.remove("node")

    return list(
        dict.fromkeys(job_skills)
    )


# ============================================================
# OUTSIDE TECHNOLOGIES
# ============================================================

def find_outside_technologies(full_text):
    """
    Find technologies that are significantly outside
    Elizabeth's current stack.
    """

    outside = []

    for technology, display_name in (
        OUTSIDE_TECHNOLOGIES.items()
    ):

        if contains_term(
            full_text,
            technology
        ):

            # Don't treat transferable technologies
            # as completely outside the stack.
            if technology in TRANSFERABLE_SKILLS:
                continue

            outside.append(display_name)

    return list(
        dict.fromkeys(outside)
    )


# ============================================================
# MISSING SKILLS
# ============================================================

def find_missing_skills(full_text):
    """
    Find employer technologies that are not currently
    listed as core or transferable skills.
    """

    job_profile = get_job_profile()

    job_skills = find_job_skills(
        full_text
    )

    known_skills = set(
        job_profile["core_skills"]
        + list(TRANSFERABLE_SKILLS)
    )

    missing = []

    for skill in job_skills:

        if skill not in known_skills:

            missing.append(skill)

    return list(
        dict.fromkeys(missing)
    )


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def detect_experience_level(
    full_text,
    job_title=""
):
    """
    Detect approximate experience level.

    Title-based detection has priority because words such as
    "experienced" appearing elsewhere in a job description
    do not necessarily describe the applicant.
    """

    title = normalize(
        job_title
    )

    # --------------------------------------------------------
    # Title first
    # --------------------------------------------------------

    for keyword in SENIOR_TITLE_KEYWORDS:

        if contains_term(
            title,
            keyword
        ):

            return "senior"

    for keyword in JUNIOR_TITLE_KEYWORDS:

        if contains_term(
            title,
            keyword
        ):

            return "junior"

    for keyword in EXPERIENCED_TITLE_KEYWORDS:

        if contains_term(
            title,
            keyword
        ):

            return "experienced"

    # --------------------------------------------------------
    # Explicit experience requirements
    # --------------------------------------------------------

    years = find_required_experience(
        full_text
    )

    if years is not None:

        if years >= 5:
            return "senior"

        if years >= 3:
            return "experienced"

        if years <= 1:
            return "junior"

        return "experienced"

    # --------------------------------------------------------
    # Description-level indicators.
    # --------------------------------------------------------

    description = normalize(
        full_text
    )

    senior_phrases = [
        "senior level",
        "lead developer",
        "lead engineer",
        "principal developer",
        "principal engineer",
        "lead a team",
        "manage a team",
    ]

    for phrase in senior_phrases:

        if contains_term(
            description,
            phrase
        ):

            return "senior"

    junior_phrases = [
        "entry level",
        "entry-level",
        "recent graduate",
        "fresh graduate",
        "graduate trainee",
        "suitable for graduates",
    ]

    for phrase in junior_phrases:

        if contains_term(
            description,
            phrase
        ):

            return "junior"

    return "unknown"


# ============================================================
# REQUIRED EXPERIENCE
# ============================================================

def find_required_experience(full_text):
    """
    Find the number of years of experience required.

    Only patterns that explicitly connect the number to
    professional/job experience are considered.
    """

    patterns = [

        r"(\d+)\+?\s+years?\s+of\s+(?:professional\s+)?experience",

        r"minimum\s+of\s+(\d+)\+?\s+years?\s+of\s+experience",

        r"at\s+least\s+(\d+)\+?\s+years?\s+of\s+experience",

        r"(\d+)\+?\s+years?\s+experience",

        r"(\d+)\+?\s+years?\s+in\s+(?:software|web|backend|frontend|development|engineering)",
    ]

    normalized = normalize(
        full_text
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized
        )

        if match:

            return int(
                match.group(1)
            )

    return None


# ============================================================
# REQUIRED MISSING SKILLS
# ============================================================

def find_required_missing_skills(
    full_text,
    missing_skills
):
    """
    Identify missing skills that occur near explicit
    requirement language.

    This is a warning mechanism and is not used as a
    second scoring penalty.
    """

    normalized = normalize(
        full_text
    )

    requirement_patterns = [
        r"required",
        r"requirements",
        r"must have",
        r"must-have",
        r"required skills",
        r"qualifications",
        r"experience with",
        r"proficient in",
        r"proficiency in",
        r"knowledge of",
        r"strong knowledge",
        r"strong experience",
        r"essential",
    ]

    has_requirement_language = any(
        re.search(
            pattern,
            normalized
        )
        for pattern in requirement_patterns
    )

    if not has_requirement_language:

        return []

    required_missing = []

    for skill in missing_skills:

        if contains_term(
            normalized,
            skill
        ):

            required_missing.append(
                skill
            )

    return list(
        dict.fromkeys(
            required_missing
        )
    )


# ============================================================
# ROLE SCORE
# ============================================================

def calculate_role_score(role_matches):
    """
    Role relevance: 30 points.
    """

    if not role_matches:
        return 0

    return 30


# ============================================================
# SKILL SCORE
# ============================================================

def calculate_skill_score(
    matching_skills,
    transferable_skills,
    job_skills,
):
    """
    Technical skill score: 35 points.

    Core skills are worth more than transferable skills.
    """

    if not job_skills:

        return 17

    core_matches = len(
        matching_skills
    )

    transferable_matches = len(
        transferable_skills
    )

    total_job_skills = len(
        job_skills
    )

    weighted_matches = (
        core_matches
        + (transferable_matches * 0.65)
    )

    ratio = (
        weighted_matches
        / total_job_skills
    )

    score = ratio * 35

    return round(
        min(
            score,
            35
        )
    )


# ============================================================
# EXPERIENCE SCORE
# ============================================================

def calculate_experience_score(
    experience_level,
    years_required
):
    """
    Experience: 15 points.
    """

    if experience_level == "junior":

        return 15

    if experience_level == "unknown":

        return 11

    if experience_level == "experienced":

        if years_required is None:
            return 8

        if years_required <= 2:
            return 10

        if years_required == 3:
            return 7

        return 4

    if experience_level == "senior":

        return 0

    return 11


# ============================================================
# LOCATION SCORE
# ============================================================

def find_location_matches(full_text):
    """
    Find matching preferred locations.
    """

    job_profile = get_job_profile()

    matches = []

    for location in job_profile["locations"]:

        if contains_term(
            full_text,
            location
        ):

            matches.append(location)

    return list(
        dict.fromkeys(matches)
    )


def calculate_location_score(
    location_matches
):
    """
    Location: 10 points.
    """

    if location_matches:
        return 10

    # Unknown location is neutral rather than a penalty.
    return 5


# ============================================================
# EDUCATION SCORE
# ============================================================

def calculate_education_score(full_text):
    """
    Education: 5 points.
    """

    job_profile = get_job_profile()

    education_keywords = [

        "computer science",
        "software engineering",
        "information technology",
        "information systems",
        "web development",
        "bachelor's degree",
        "bachelor degree",
        "bachelor",
        "degree",
    ]

    # Also include qualifications from the candidate profile.
    education_keywords.extend(
        job_profile["education"]
    )

    for keyword in education_keywords:

        if contains_term(
            full_text,
            keyword
        ):

            return 5

    return 0


# ============================================================
# TECHNOLOGY FIT
# ============================================================

def calculate_technology_score(
    outside_technologies
):
    """
    Technology fit: 5 points.

    One outside technology is acceptable.

    Several unrelated technologies reduce the score.
    """

    count = len(
        outside_technologies
    )

    if count == 0:
        return 5

    if count == 1:
        return 4

    if count == 2:
        return 2

    return 0


# ============================================================
# MAIN MATCHING FUNCTION
# ============================================================

def calculate_match(
    job_title,
    job_description
):
    """
    Calculate how well a job matches Elizabeth's profile.

    Scoring:

        Role relevance:       30 points
        Technical skills:     35 points
        Experience:           15 points
        Location:             10 points
        Education:             5 points
        Technology fit:        5 points
        --------------------------------
        Total:               100 points
    """

    title = normalize(
        job_title
    )

    description = normalize(
        job_description
    )

    full_text = (
        f"{title} {description}"
    )

    warnings = []

    # ========================================================
    # 0. JOB TYPE
    # ========================================================

    software_role = is_software_role(
        title,
        description
    )

    # --------------------------------------------------------
    # Non-software jobs are handled separately.
    # --------------------------------------------------------

    if not software_role:

        warnings.append(
            "This does not appear to be a "
            "software/technology role."
        )

        return {
            "score": 15,
            "category": "POOR MATCH",
            "recommendation": "SKIP",

            "role_score": 0,
            "skill_score": 0,
            "experience_score": 5,
            "location_score": 5,
            "education_score": 0,
            "technology_score": 5,

            "role_matches": [],
            "matching_skills": [],
            "transferable_skills": [],
            "missing_skills": [],
            "job_skills": [],
            "location_matches": [],

            "experience_level": "unknown",
            "years_required": None,

            "outside_technologies": [],
            "required_missing_skills": [],

            "software_role": False,

            "warnings": warnings,
        }

    # ========================================================
    # 1. ROLE — 30 POINTS
    # ========================================================

    role_matches = find_role_matches(
        title
    )

    role_score = calculate_role_score(
        role_matches
    )

    # ========================================================
    # 2. SKILLS — 35 POINTS
    # ========================================================

    matching_skills = find_matching_skills(
        full_text
    )

    transferable_skills = (
        find_transferable_skills(
            full_text
        )
    )

    job_skills = find_job_skills(
        full_text
    )

    missing_skills = find_missing_skills(
        full_text
    )

    skill_score = calculate_skill_score(
        matching_skills,
        transferable_skills,
        job_skills
    )

    # ========================================================
    # 3. EXPERIENCE — 15 POINTS
    # ========================================================

    experience_level = detect_experience_level(
        full_text,
        title
    )

    years_required = find_required_experience(
        full_text
    )

    experience_score = calculate_experience_score(
        experience_level,
        years_required
    )

    if experience_level == "senior":

        warnings.append(
            "This appears to be a senior/lead "
            "position."
        )

    elif (
        experience_level == "experienced"
        and years_required
        and years_required >= 3
    ):

        warnings.append(
            f"Requires approximately "
            f"{years_required} years of experience."
        )

    # ========================================================
    # 4. LOCATION — 10 POINTS
    # ========================================================

    location_matches = find_location_matches(
        full_text
    )

    location_score = calculate_location_score(
        location_matches
    )

    # ========================================================
    # 5. EDUCATION — 5 POINTS
    # ========================================================

    education_score = calculate_education_score(
        full_text
    )

    # ========================================================
    # 6. TECHNOLOGY FIT — 5 POINTS
    # ========================================================

    outside_technologies = (
        find_outside_technologies(
            full_text
        )
    )

    technology_score = calculate_technology_score(
        outside_technologies
    )

    if outside_technologies:

        warnings.append(
            "Role focuses on technology outside "
            "your primary stack: "
            + ", ".join(
                outside_technologies
            )
        )

    # ========================================================
    # 7. REQUIRED MISSING SKILLS
    # ========================================================

    required_missing_skills = (
        find_required_missing_skills(
            full_text,
            missing_skills
        )
    )

    if required_missing_skills:

        warnings.append(
            "Missing potentially required skills: "
            + ", ".join(
                required_missing_skills
            )
        )

    # ========================================================
    # 8. ROLE / TECHNOLOGY ALIGNMENT
    # ========================================================

    if not role_matches:

        warnings.append(
            "The job is technical, but the title does "
            "not directly match your target roles."
        )

    # ========================================================
    # 9. FINAL SCORE
    # ========================================================

    score = (
        role_score
        + skill_score
        + experience_score
        + location_score
        + education_score
        + technology_score
    )

    # --------------------------------------------------------
    # Additional guard against severe technology mismatch.
    # --------------------------------------------------------

    if len(outside_technologies) >= 4:

        score -= 10

    elif len(outside_technologies) == 3:

        score -= 5

    score = max(
        0,
        min(
            round(score),
            100
        )
    )

    # ========================================================
    # 10. CATEGORY
    # ========================================================

    if score >= 70:

        category = "STRONG MATCH"

    elif score >= 55:

        category = "GOOD MATCH"

    elif score >= 40:

        category = "POSSIBLE MATCH"

    elif score >= 25:

        category = "WEAK MATCH"

    else:

        category = "POOR MATCH"

    # ========================================================
    # 11. RECOMMENDATION
    # ========================================================

    if score >= 70:

        recommendation = "APPLY"

    elif score >= 55:

        recommendation = "REVIEW"

    else:

        recommendation = "SKIP"

    # --------------------------------------------------------
    # Safety rule: senior roles.
    # --------------------------------------------------------

    if experience_level == "senior":

        recommendation = "SKIP"

        if category == "STRONG MATCH":

            category = "GOOD MATCH"

    # --------------------------------------------------------
    # Safety rule: severe technology mismatch.
    # --------------------------------------------------------

    if len(outside_technologies) >= 4:

        recommendation = "SKIP"

    # --------------------------------------------------------
    # Safety rule: no role match + weak skills.
    # --------------------------------------------------------

    if (
        not role_matches
        and skill_score < 18
    ):

        recommendation = "SKIP"

    # ========================================================
    # RETURN RESULTS
    # ========================================================

    return {

        "score": score,

        "category": category,

        "recommendation": recommendation,

        # Score breakdown
        "role_score": role_score,

        "skill_score": skill_score,

        "experience_score": experience_score,

        "location_score": location_score,

        "education_score": education_score,

        "technology_score": technology_score,

        # Matching details
        "role_matches": role_matches,

        "matching_skills": matching_skills,

        "transferable_skills": transferable_skills,

        "missing_skills": missing_skills,

        "job_skills": job_skills,

        "location_matches": location_matches,

        "experience_level": experience_level,

        "years_required": years_required,

        "outside_technologies": outside_technologies,

        "required_missing_skills": (
            required_missing_skills
        ),

        "software_role": software_role,

        # Warnings
        "warnings": list(
            dict.fromkeys(
                warnings
            )
        ),
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JOB MATCHER TEST")
    print("=" * 60)

    test_jobs = [

        {
            "title": "Junior Python Developer",

            "description": """
                We are looking for a junior Python developer
                with experience in Python, Flask, REST API
                development and Git.

                Bachelor's degree in software engineering
                or computer science is preferred.
            """
        },

        {
            "title": "Senior Dynamics 365 Business Central Developer",

            "description": """
                We are looking for a senior Dynamics 365
                developer with 5 years of experience.

                Experience with Dynamics 365, ERP and
                Microsoft technologies is required.
            """
        },

        {
            "title": "Backend Developer",

            "description": """
                We are looking for a backend developer
                with Python, Flask, REST API, database design
                and Git experience.

                Knowledge of SQL is an advantage.
            """
        },

        {
            "title": "Backend Developer - Go & PostgreSQL",

            "description": """
                We are looking for a backend developer
                with experience in Go and PostgreSQL.

                Experience with REST APIs, databases and
                software development is required.
            """
        },

        {
            "title": "Sales Representative",

            "description": """
                We are looking for a sales representative
                to promote products and acquire customers.

                Previous sales experience is preferred.
            """
        },
    ]

    for job in test_jobs:

        result = calculate_match(
            job["title"],
            job["description"]
        )

        print()

        print(
            f"Job: {job['title']}"
        )

        print(
            f"Score: {result['score']}%"
        )

        print(
            f"Breakdown: "
            f"Role {result['role_score']}/30 | "
            f"Skills {result['skill_score']}/35 | "
            f"Experience {result['experience_score']}/15 | "
            f"Location {result['location_score']}/10 | "
            f"Education {result['education_score']}/5 | "
            f"Technology {result['technology_score']}/5"
        )

        print(
            f"Category: "
            f"{result['category']}"
        )

        print(
            f"Recommendation: "
            f"{result['recommendation']}"
        )

        print(
            "Software role:",
            result["software_role"]
        )

        print(
            "Job skills:",
            ", ".join(
                result["job_skills"]
            )
            if result["job_skills"]
            else "None"
        )

        print(
            "Matching skills:",
            ", ".join(
                result["matching_skills"]
            )
            if result["matching_skills"]
            else "None"
        )

        print(
            "Transferable skills:",
            ", ".join(
                result["transferable_skills"]
            )
            if result["transferable_skills"]
            else "None"
        )

        print(
            "Missing skills:",
            ", ".join(
                result["missing_skills"]
            )
            if result["missing_skills"]
            else "None"
        )

        print(
            "Experience:",
            result["experience_level"]
        )

        print(
            "Years required:",
            result["years_required"]
            if result["years_required"] is not None
            else "Not specified"
        )

        print(
            "Warnings:"
        )

        if result["warnings"]:

            for warning in result["warnings"]:

                print(
                    f"  ⚠ {warning}"
                )

        else:

            print(
                "  None"
            )

        print("-" * 60)