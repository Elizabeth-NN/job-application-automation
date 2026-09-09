
import re

from config.profile import JOB_PROFILE


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize(text):
    """Normalize text for reliable matching."""
    if not text:
        return ""

    text = str(text).lower()

    # Normalize common punctuation variations
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return re.sub(r"\s+", " ", text).strip()


def contains_term(text, term):
    """
    Check whether a term exists as a meaningful word/phrase.

    This prevents things like:
        "go" matching "good"
        "sql" matching unrelated words
    """
    text = normalize(text)
    term = normalize(term)

    if not term:
        return False

    # Multi-word terms
    if " " in term or "-" in term:
        return term in text

    pattern = rf"\b{re.escape(term)}\b"

    return bool(re.search(pattern, text))


# ============================================================
# EXPERIENCE DETECTION
# ============================================================

def find_required_experience(text):
    """
    Find the highest explicit experience requirement.

    Examples:
        3+ years
        3 years
        4 yrs
        5 or more years
        2-3 years
        at least 3 years
    """

    text = normalize(text)

    patterns = [
        # 3+ years
        r"\b(\d+)\s*\+\s*(?:years?|yrs?)\b",

        # 3 or more years
        r"\b(\d+)\s+(?:or\s+more)\s+(?:years?|yrs?)\b",

        # at least 3 years
        r"\bat\s+least\s+(\d+)\s+(?:years?|yrs?)\b",

        # minimum of 3 years
        r"\bminimum\s+(?:of\s+)?(\d+)\s+(?:years?|yrs?)\b",

        # 3 years of experience
        r"\b(\d+)\s+(?:years?|yrs?)\s+(?:of\s+)?experience\b",

        # experience of 3 years
        r"\bexperience\s+of\s+(\d+)\s+(?:years?|yrs?)\b",

        # 2-3 years
        r"\b(\d+)\s*-\s*(\d+)\s+(?:years?|yrs?)\b",

        # 2 to 3 years
        r"\b(\d+)\s+to\s+(\d+)\s+(?:years?|yrs?)\b",
    ]

    years_found = []

    for pattern in patterns:

        for match in re.finditer(pattern, text):

            try:

                if match.lastindex and match.lastindex >= 2:

                    first = int(match.group(1))
                    second = int(match.group(2))

                    years_found.append(
                        max(first, second)
                    )

                else:

                    years_found.append(
                        int(match.group(1))
                    )

            except (ValueError, TypeError):
                continue

    if not years_found:
        return None

    return max(years_found)


def detect_experience_level(text):
    """Determine the likely experience level of a job."""

    text = normalize(text)

    senior_keywords = [
        "senior",
        "senior developer",
        "senior engineer",
        "lead developer",
        "lead engineer",
        "principal developer",
        "principal engineer",
        "staff engineer",
        "engineering manager",
        "software development manager",
        "technical lead",
        "team lead",
        "head of software",
        "head of engineering",
    ]

    junior_keywords = [
        "junior",
        "entry level",
        "entry-level",
        "graduate",
        "graduate trainee",
        "intern",
        "internship",
        "trainee",
        "apprentice",
        "0-2 years",
        "0–2 years",
        "1-2 years",
        "1–2 years",
        "0 to 2 years",
        "1 to 2 years",
    ]

    if any(
        contains_term(text, keyword)
        for keyword in senior_keywords
    ):
        return "senior"

    if any(
        contains_term(text, keyword)
        for keyword in junior_keywords
    ):
        return "junior"

    years_required = find_required_experience(text)

    if years_required is not None:

        if years_required <= 2:
            return "junior"

        if years_required >= 3:
            return "experienced"

    return "unknown"


# ============================================================
# ROLE MATCHING
# ============================================================

def find_role_matches(title):
    """
    Find genuine target-role matches.

    Important:
    We DO NOT match generic words such as "Developer"
    by themselves.
    """

    title = normalize(title)

    role_matches = []

    for role in JOB_PROFILE["target_roles"]:

        role_normalized = normalize(role)

        if contains_term(title, role_normalized):

            role_matches.append(role)

    # Remove overly generic matches.
    generic_roles = {
        "developer",
        "software developer",
        "software engineer",
        "engineer",
    }

    role_matches = [
        role
        for role in role_matches
        if normalize(role) not in generic_roles
    ]

    return list(dict.fromkeys(role_matches))


# ============================================================
# TECHNOLOGY DETECTION
# ============================================================

# Technologies that are relevant to Elizabeth's current stack.
PRIMARY_TECHNOLOGIES = [
    "python",
    "flask",
    "flask-restful",
    "rest api",
    "react",
    "javascript",
    "next.js",
    "nextjs",
    "html",
    "css",
    "tailwind css",
    "sqlite",
    "sqlalchemy",
    "git",
    "github",
    "database design",
    "schema design",
    "role-based authentication",
]


# Technologies that indicate the role is substantially
# outside the user's current target stack.
OUTSIDE_TECHNOLOGIES = {
    "go": "Go",
    "golang": "Go",
    "java": "Java",
    "spring boot": "Spring Boot",
    "c#": "C#",
    ".net": ".NET",
    "dotnet": ".NET",
    "php": "PHP",
    "laravel": "Laravel",
    "ruby": "Ruby",
    "rails": "Ruby on Rails",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "flutter": "Flutter",
    "dart": "Dart",
    "android": "Android",
    "ios": "iOS",
    "angular": "Angular",
    "vue": "Vue",
    "vue.js": "Vue.js",
    "django": "Django",
    "fastapi": "FastAPI",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express.js": "Express.js",
    "express": "Express.js",
    "typescript": "TypeScript",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "oracle": "Oracle",
    "microsoft dynamics": "Dynamics 365",
    "dynamics 365": "Dynamics 365",
    "servicenow": "ServiceNow",
    "rpa": "RPA",
    "uipath": "UiPath",
    "erp": "ERP",
    "fineract": "Fineract",
    "salesforce": "Salesforce",
    "sap": "SAP",
}


def find_matching_skills(full_text):
    """Find skills from Elizabeth's profile present in the job."""

    matching_skills = []

    for skill in JOB_PROFILE["skills"]:

        if contains_term(full_text, skill):

            matching_skills.append(skill)

    return list(dict.fromkeys(matching_skills))


def find_outside_technologies(full_text):
    """
    Find technologies that are outside the primary stack.
    """

    found = []

    for technology, display_name in OUTSIDE_TECHNOLOGIES.items():

        if contains_term(full_text, technology):

            found.append(display_name)

    return list(dict.fromkeys(found))


# ============================================================
# REQUIRED TECHNOLOGY DETECTION
# ============================================================

def extract_required_sections(full_text):
    """
    Extract text surrounding phrases that normally introduce
    mandatory requirements.
    """

    patterns = [
        r"required[^.]{0,300}",
        r"must have[^.]{0,300}",
        r"must-have[^.]{0,300}",
        r"mandatory[^.]{0,300}",
        r"requirements?[^.]{0,300}",
        r"proficiency in[^.]{0,300}",
        r"experience with[^.]{0,300}",
        r"experience in[^.]{0,300}",
        r"knowledge of[^.]{0,300}",
    ]

    sections = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            full_text
        )

        sections.extend(matches)

    return " ".join(sections)


def find_required_missing_skills(
    full_text,
    missing_skills
):
    """
    Determine which profile skills appear to be explicitly
    required but are missing from the job/profile match.
    """

    required_text = extract_required_sections(
        full_text
    )

    required_missing = []

    for skill in missing_skills:

        if contains_term(
            required_text,
            skill
        ):

            required_missing.append(skill)

    return list(
        dict.fromkeys(required_missing)
    )


# ============================================================
# CALCULATE MATCH
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

    title = normalize(job_title)
    description = normalize(job_description)

    full_text = f"{title} {description}"

    warnings = []

    # ========================================================
    # 1. ROLE — 30 POINTS
    # ========================================================

    role_matches = find_role_matches(title)

    if role_matches:

        # Strong match for explicit target role.
        role_score = 30

    else:

        role_score = 0

    # ========================================================
    # 2. SKILLS — 30 POINTS
    # ========================================================

    matching_skills = find_matching_skills(
        full_text
    )

    skills = JOB_PROFILE["skills"]

    if skills:

        skill_score = (
            len(matching_skills)
            / len(skills)
        ) * 30

    else:

        skill_score = 0

    missing_skills = [
        skill
        for skill in skills
        if skill not in matching_skills
    ]

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

        elif years_required and years_required >= 4:

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

            location_matches.append(location)

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
        contains_term(full_text, keyword)
        for keyword in education_keywords
    )

    if education_match:

        education_score = 5

    else:

        education_score = 0

    # ========================================================
    # 6. TECHNOLOGY FIT — 5 POINTS
    # ========================================================

    outside_technologies = find_outside_technologies(
        full_text
    )

    # Count only technologies that are actually present.
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

    # Warn when the role is strongly focused on
    # technology outside the user's stack.
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

    if required_missing_skills:

        penalty = min(
            len(required_missing_skills) * 3,
            9
        )

        skill_score -= penalty

        warnings.append(
            "Missing potentially required skills: "
            + ", ".join(
                required_missing_skills
            )
        )

    # Never allow skills below zero.
    skill_score = max(
        0,
        skill_score
    )

    # ========================================================
    # 8. EXTRA PENALTY FOR STRONGLY MISALIGNED ROLES
    # ========================================================

    # If the job has no genuine target-role match AND
    # clearly focuses on outside technologies, penalize it.
    #
    # This prevents:
    #   ServiceNow Developer
    #   Dynamics 365 Developer
    #   RPA Developer
    #   ERP Developer
    #
    # from appearing artificially relevant merely because
    # they contain the word "Developer".

    if not role_matches and outside_count >= 1:

        misalignment_penalty = min(
            outside_count * 5,
            15
        )

        technology_score -= misalignment_penalty

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
        "role_matches": role_matches,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "location_matches": location_matches,
        "experience_level": experience_level,
        "years_required": years_required,
        "outside_technologies": outside_technologies,
        "warnings": list(
            dict.fromkeys(warnings)
        ),
    }


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_jobs = [
        {
            "title": "Junior Python Developer",
            "description": """
                We are looking for a junior Python developer
                with Flask, REST API, Git and SQL experience.
                0-2 years of experience.
                Nairobi, Kenya.
                Bachelor's degree in Computer Science.
            """
        },
        {
            "title": "Senior Dynamics 365 Developer",
            "description": """
                We require a senior Dynamics 365 developer
                with 5 years of experience.
                Experience with Microsoft Dynamics 365,
                C# and .NET is required.
                Nairobi, Kenya.
            """
        },
        {
            "title": "Backend Developer",
            "description": """
                Backend developer required with Python,
                Flask, REST API and database design.
                1-2 years of experience.
                Remote, Kenya.
            """
        },
    ]

    print("=" * 60)
    print("JOB MATCHER TEST")
    print("=" * 60)

    for job in test_jobs:

        result = calculate_match(
            job["title"],
            job["description"]
        )

        print()
        print(f"Job: {job['title']}")
        print(f"Score: {result['score']}%")
        print(f"Category: {result['category']}")
        print(
            f"Recommendation: "
            f"{result['recommendation']}"
        )

        print(
            "Roles:",
            ", ".join(
                result["role_matches"]
            )
            if result["role_matches"]
            else "None"
        )

        print(
            "Skills:",
            ", ".join(
                result["matching_skills"]
            )
            if result["matching_skills"]
            else "None"
        )

        if result["warnings"]:

            for warning in result["warnings"]:

                print(
                    f"WARNING: {warning}"
                )

