"""
Job matching and scoring engine.

Evaluates how well a job matches Elizabeth's profile.
"""

import re


# ============================================================
# ELIZABETH'S JOB PROFILE
# ============================================================

JOB_PROFILE = {

    # --------------------------------------------------------
    # Target roles
    # --------------------------------------------------------

    "target_roles": [
        "python developer",
        "backend developer",
        "backend engineer",
        "software developer",
        "software engineer",
        "full stack developer",
        "fullstack developer",
        "web developer",
    ],

    # --------------------------------------------------------
    # Skills
    #
    # These are the skills Elizabeth currently has.
    # --------------------------------------------------------

    "skills": [
        "python",
        "flask",
        "rest api",
        "database design",
        "sql",
        "git",
        "react",
        "javascript",
        "html",
        "css",
        "next.js",
        "tailwind css",
    ],

    # --------------------------------------------------------
    # Locations
    # --------------------------------------------------------

    "locations": [
        "nairobi",
        "kenya",
        "remote",
    ],

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    "education": [
        "software engineering",
        "computer science",
        "information technology",
    ],
}


# ============================================================
# SKILLS THE MATCHER KNOWS ABOUT
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
]


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
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize(text):
    """
    Normalize text for easier matching.
    """

    if not text:
        return ""

    text = text.lower()

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

    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"

    return re.search(
        pattern,
        text
    ) is not None


# ============================================================
# ROLE MATCHING
# ============================================================

def find_role_matches(title):
    """
    Find target roles appearing in the job title.
    """

    matches = []

    for role in JOB_PROFILE["target_roles"]:

        if contains_term(title, role):

            matches.append(role)

    return list(
        dict.fromkeys(matches)
    )


# ============================================================
# PROFILE SKILL MATCHING
# ============================================================

def find_matching_skills(full_text):
    """
    Find Elizabeth's skills that appear in the job description.

    This function answers:

        "Which skills does Elizabeth have that this job mentions?"
    """

    matching_skills = []

    for skill in JOB_PROFILE["skills"]:

        if contains_term(
            full_text,
            skill
        ):

            matching_skills.append(skill)

    return list(
        dict.fromkeys(matching_skills)
    )


# ============================================================
# JOB SKILL EXTRACTION
# ============================================================

def find_job_skills(full_text):
    """
    Find known skills/technologies mentioned in the job.

    This is different from find_matching_skills().

    find_matching_skills():
        Finds skills Elizabeth has.

    find_job_skills():
        Finds skills mentioned by the employer.
    """

    job_skills = []

    for skill in ALL_SKILLS:

        if contains_term(
            full_text,
            skill
        ):

            job_skills.append(skill)

    return list(
        dict.fromkeys(job_skills)
    )


# ============================================================
# OUTSIDE TECHNOLOGIES
# ============================================================

def find_outside_technologies(full_text):
    """
    Find technologies that are outside Elizabeth's
    primary stack.
    """

    outside = []

    for technology, display_name in (
        OUTSIDE_TECHNOLOGIES.items()
    ):

        if contains_term(
            full_text,
            technology
        ):

            outside.append(
                display_name
            )

    return list(
        dict.fromkeys(outside)
    )


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def detect_experience_level(full_text):
    """
    Detect the approximate experience level required.
    """

    senior_keywords = [
        "senior",
        "lead developer",
        "lead engineer",
        "principal",
        "manager",
        "head of",
    ]

    experienced_keywords = [
        "mid-level",
        "mid level",
        "intermediate",
        "experienced developer",
        "experienced engineer",
    ]

    junior_keywords = [
        "junior",
        "entry level",
        "entry-level",
        "graduate",
        "trainee",
        "intern",
        "internship",
        "fresh graduate",
    ]

    for keyword in senior_keywords:

        if contains_term(
            full_text,
            keyword
        ):

            return "senior"

    for keyword in experienced_keywords:

        if contains_term(
            full_text,
            keyword
        ):

            return "experienced"

    for keyword in junior_keywords:

        if contains_term(
            full_text,
            keyword
        ):

            return "junior"

    return "unknown"


# ============================================================
# REQUIRED EXPERIENCE
# ============================================================

def find_required_experience(full_text):
    """
    Find the number of years of experience required.
    """

    patterns = [
        r"(\d+)\+?\s+years?\s+of\s+experience",
        r"minimum\s+of\s+(\d+)\s+years?",
        r"at\s+least\s+(\d+)\s+years?",
        r"(\d+)\s+years?\s+experience",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text
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
    Identify missing skills that appear to be explicitly
    required by the employer.

    This is used for warnings, not as the primary
    skill-score calculation.
    """

    required_missing = []

    requirement_keywords = [
        "required",
        "requirements",
        "must have",
        "must-have",
        "required skills",
        "qualifications",
        "experience with",
        "proficient in",
        "proficiency in",
        "knowledge of",
    ]

    # Check whether the job contains language indicating
    # that specific skills are required.
    has_requirement_language = any(
        contains_term(
            full_text,
            keyword
        )
        for keyword in requirement_keywords
    )

    if not has_requirement_language:
        return []

    for skill in missing_skills:

        if contains_term(
            full_text,
            skill
        ):

            required_missing.append(
                skill
            )

    return list(
        dict.fromkeys(required_missing)
    )


# ============================================================
# MAIN MATCHING FUNCTION
# ============================================================

def calculate_match(job_title, job_description):
    """
    Calculate how well a job matches Elizabeth's profile.

    Scoring:

        Role relevance:       30 points
        Skills:               30 points
        Experience:           20 points
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

    full_text = f"{title} {description}"

    warnings = []

    # ========================================================
    # 1. ROLE — 30 POINTS
    # ========================================================

    role_matches = find_role_matches(
        title
    )

    if role_matches:

        role_score = 30

    else:

        role_score = 0

    # ========================================================
    # 2. SKILLS — 30 POINTS
    # ========================================================

    # Skills Elizabeth has that are mentioned in the job.
    matching_skills = find_matching_skills(
        full_text
    )

    # Skills mentioned by the employer.
    job_skills = find_job_skills(
        full_text
    )

    # Skills mentioned by the employer that Elizabeth
    # does not currently have.
    missing_skills = [
        skill
        for skill in job_skills
        if skill not in JOB_PROFILE["skills"]
    ]

    # --------------------------------------------------------
    # Calculate the score based on JOB skills.
    #
    # We do NOT divide by the total number of skills
    # Elizabeth has.
    # --------------------------------------------------------

    if job_skills:

        skill_score = (
            len(matching_skills)
            / len(job_skills)
        ) * 30

    else:

        # If no identifiable skills were found, don't give
        # a completely unknown job zero points.
        skill_score = 15

    # Never allow the skill score above the maximum.
    skill_score = min(
        skill_score,
        30
    )

    # ========================================================
    # 3. EXPERIENCE — 20 POINTS
    # ========================================================

    experience_level = detect_experience_level(
        full_text
    )

    years_required = find_required_experience(
        full_text
    )

    if experience_level == "junior":

        experience_score = 20

    elif experience_level == "unknown":

        experience_score = 14

    elif experience_level == "experienced":

        if years_required == 3:

            experience_score = 7

        elif (
            years_required
            and years_required >= 4
        ):

            experience_score = 3

        else:

            experience_score = 7

        warnings.append(
            f"Requires approximately "
            f"{years_required} years of experience."
        )

    elif experience_level == "senior":

        experience_score = 0

        warnings.append(
            "This appears to be a senior/experienced "
            "position."
        )

    else:

        experience_score = 14

    # ========================================================
    # 4. LOCATION — 10 POINTS
    # ========================================================

    location_matches = []

    for location in JOB_PROFILE["locations"]:

        if contains_term(
            full_text,
            location
        ):

            location_matches.append(
                location
            )

    if location_matches:

        location_score = 10

    else:

        # Location not specified.
        location_score = 5

    # ========================================================
    # 5. EDUCATION — 5 POINTS
    # ========================================================

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

    education_match = any(
        contains_term(
            full_text,
            keyword
        )
        for keyword in education_keywords
    )

    if education_match:

        education_score = 5

    else:

        education_score = 0

    # ========================================================
    # 6. TECHNOLOGY FIT — 5 POINTS
    # ========================================================

    outside_technologies = (
        find_outside_technologies(
            full_text
        )
    )

    outside_count = len(
        outside_technologies
    )

    if outside_count == 0:

        technology_score = 5

    elif outside_count == 1:

        technology_score = 3

    elif outside_count == 2:

        technology_score = 1

    else:

        technology_score = 0

    if outside_count >= 1:

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

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We no longer subtract points here.
    #
    # Missing job skills are already reflected in the
    # skill score because skill_score compares:
    #
    #     matching job skills
    #     -------------------
    #          all job skills
    #
    # Required missing skills are therefore warnings rather
    # than a second penalty.
    # --------------------------------------------------------

    if required_missing_skills:

        warnings.append(
            "Missing potentially required skills: "
            + ", ".join(
                required_missing_skills
            )
        )

    # ========================================================
    # 8. EXTRA PENALTY FOR STRONGLY MISALIGNED ROLES
    # ========================================================

    if not role_matches and outside_count >= 1:

        misalignment_penalty = min(
            outside_count * 5,
            15
        )

        technology_score -= (
            misalignment_penalty
        )

        technology_score = max(
            0,
            technology_score
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

    score = max(
        0,
        min(
            round(score),
            100
        )
    )

    # ========================================================
    # 10. CATEGORY + RECOMMENDATION
    # ========================================================

    if score >= 70:

        category = "STRONG MATCH"
        recommendation = "APPLY"

    elif score >= 55:

        category = "POSSIBLE MATCH"
        recommendation = "REVIEW"

    elif score >= 40:

        category = "WEAK MATCH"
        recommendation = "REVIEW"

    else:

        category = "POOR MATCH"
        recommendation = "SKIP"

    # ========================================================
    # 11. SAFETY RULES FOR APPLICATION RECOMMENDATION
    # ========================================================

    # Never automatically recommend APPLY for a senior job.
    if experience_level == "senior":

        recommendation = "SKIP"

        if category == "STRONG MATCH":

            category = "POSSIBLE MATCH"

    # Never recommend APPLY when there is a major
    # technology mismatch.
    if outside_count >= 3:

        recommendation = "SKIP"

        if score >= 55:

            category = "POSSIBLE MATCH"

    # ========================================================
    # RETURN RESULTS
    # ========================================================

    return {
        "score": score,
        "category": category,
        "recommendation": recommendation,

        # Score breakdown
        "role_score": role_score,
        "skill_score": round(
            skill_score
        ),
        "experience_score": experience_score,
        "location_score": location_score,
        "education_score": education_score,
        "technology_score": technology_score,

        # Matching details
        "role_matches": role_matches,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "job_skills": job_skills,
        "location_matches": location_matches,
        "experience_level": experience_level,
        "years_required": years_required,
        "outside_technologies": outside_technologies,
        "required_missing_skills": (
            required_missing_skills
        ),

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
            "title": "Senior Dynamics 365 Developer",
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
            f"Skills {result['skill_score']}/30 | "
            f"Experience {result['experience_score']}/20 | "
            f"Location {result['location_score']}/10 | "
            f"Education {result['education_score']}/5 | "
            f"Technology {result['technology_score']}/5"
        )

        print(
            f"Category: {result['category']}"
        )

        print(
            f"Recommendation: "
            f"{result['recommendation']}"
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
            "Missing skills:",
            ", ".join(
                result["missing_skills"]
            )
            if result["missing_skills"]
            else "None"
        )

        print(
            "Roles:",
            ", ".join(
                result["role_matches"]
            )
            if result["role_matches"]
            else "None"
        )

        for warning in result["warnings"]:

            print(
                f"WARNING: {warning}"
            )