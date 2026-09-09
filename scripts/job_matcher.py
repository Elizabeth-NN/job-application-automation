import re

from config.profile import JOB_PROFILE


# Skills that are especially important for Elizabeth's target roles
CORE_SKILLS = {
    "Python",
    "Flask",
    "Flask-RESTful",
    "REST API",
    "React",
    "JavaScript",
    "Next.js",
    "SQLAlchemy",
    "SQLite",
    "Database Design",
    "Schema Design",
}


SKILL_ALIASES = {
    "Python": [
        "python",
    ],
    "Flask": [
        "flask",
    ],
    "Flask-RESTful": [
        "flask-restful",
        "flask restful",
    ],
    "REST API": [
        "rest api",
        "restful api",
        "rest apis",
        "restful apis",
        "rest services",
    ],
    "React": [
        "react",
        "react.js",
        "reactjs",
    ],
    "JavaScript": [
        "javascript",
        "js",
    ],
    "Next.js": [
        "next.js",
        "nextjs",
        "next js",
    ],
    "HTML": [
        "html",
    ],
    "CSS": [
        "css",
    ],
    "Tailwind CSS": [
        "tailwind",
        "tailwind css",
    ],
    "SQLite": [
        "sqlite",
    ],
    "SQLAlchemy": [
        "sqlalchemy",
    ],
    "Git": [
        "git",
    ],
    "GitHub": [
        "github",
    ],
    "Database Design": [
        "database design",
        "database architecture",
        "database management",
        "database development",
    ],
    "Schema Design": [
        "schema design",
        "database schema",
    ],
    "Role-Based Authentication": [
        "role-based authentication",
        "role based authentication",
        "role-based access control",
        "rbac",
    ],
}


ROLE_ALIASES = {
    "Junior Software Developer": [
        "junior software developer",
        "junior developer",
    ],
    "Junior Software Engineer": [
        "junior software engineer",
        "junior software developer",
    ],
    "Backend Developer": [
        "backend developer",
        "back-end developer",
        "backend engineer",
        "back-end engineer",
    ],
    "Python Developer": [
        "python developer",
        "python engineer",
    ],
    "Flask Developer": [
        "flask developer",
        "flask engineer",
    ],
    "Junior Full Stack Developer": [
        "junior full stack developer",
        "junior full-stack developer",
        "junior fullstack developer",
    ],
    "Full Stack Developer": [
        "full stack developer",
        "full-stack developer",
        "fullstack developer",
    ],
    "React Developer": [
        "react developer",
        "react engineer",
    ],
    "Frontend Developer": [
        "frontend developer",
        "front-end developer",
        "front end developer",
    ],
}


def extract_required_years(text):
    """
    Detect experience requirements such as:
    3+ years
    3 years
    at least three years
    minimum of 3 years
    3-5 years
    """

    text = text.lower()

    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    # Convert "three (3)" to "3"
    for word, number in number_words.items():
        text = re.sub(
            rf"\b{word}\s*\(\s*{number}\s*\)",
            str(number),
            text,
        )

        text = re.sub(
            rf"\b{word}\b",
            str(number),
            text,
        )

    patterns = [
        r"at least\s+(\d+)\s*years?",
        r"minimum\s+of\s+(\d+)\s*years?",
        r"minimum\s+(\d+)\s*years?",
        r"(\d+)\s*\+\s*years?",
        r"(\d+)\s*-\s*\d+\s*years?",
        r"(\d+)\s*years?\s+of\s+(?:relevant\s+)?experience",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    return 0


def find_role_matches(title):
    """Find target roles represented by the job title."""

    matches = []

    for role, aliases in ROLE_ALIASES.items():

        for alias in aliases:

            if alias in title:
                matches.append(role)
                break

    return list(dict.fromkeys(matches))


def find_skill_matches(text):
    """Find skills using aliases."""

    matches = []

    for skill in JOB_PROFILE["skills"]:

        aliases = SKILL_ALIASES.get(
            skill,
            [skill.lower()],
        )

        for alias in aliases:

            if alias.lower() in text:
                matches.append(skill)
                break

    return matches


def calculate_match(job_title, job_description):
    """
    Calculate how well a job matches Elizabeth's profile.

    Score:
        Role relevance:       35
        Skills:               35
        Experience:           20
        Location:             10
        Total:               100
    """

    title = job_title.lower()
    description = job_description.lower()
    full_text = f"{title} {description}"

    # ==================================================
    # 1. ROLE MATCH — 35 POINTS
    # ==================================================

    role_matches = find_role_matches(title)

    if role_matches:
        role_score = 35
    else:
        role_score = 0

    # Strong role signals even when wording differs
    if not role_matches:

        if "software developer" in title:
            role_score = 30

        elif "software engineer" in title:
            role_score = 30

        elif "web developer" in title:
            role_score = 28

        elif "developer" in title:
            role_score = 20

    # ==================================================
    # 2. SKILLS — 35 POINTS
    # ==================================================

    matching_skills = find_skill_matches(full_text)

    missing_skills = [
        skill
        for skill in JOB_PROFILE["skills"]
        if skill not in matching_skills
    ]

    core_matches = [
        skill
        for skill in matching_skills
        if skill in CORE_SKILLS
    ]

    supporting_matches = [
        skill
        for skill in matching_skills
        if skill not in CORE_SKILLS
    ]

    # Core skills: up to 28 points
    core_score = min(
        len(core_matches) * 4,
        28,
    )

    # Supporting skills: up to 7 points
    supporting_score = min(
        len(supporting_matches) * 1.5,
        7,
    )

    skill_score = core_score + supporting_score

    # ==================================================
    # 3. TITLE-BASED TECHNICAL SIGNALS
    # ==================================================

    # A Full Stack title itself is evidence of relevance
    if any(
        term in title
        for term in [
            "fullstack",
            "full-stack",
            "full stack",
        ]
    ):
        skill_score = max(skill_score, 20)

    # Backend roles are particularly relevant to Python/Flask
    if "backend" in title or "back-end" in title:

        if "python" in full_text or "flask" in full_text:
            skill_score = max(skill_score, 24)

        else:
            skill_score = max(skill_score, 15)

    skill_score = min(skill_score, 35)

    # ==================================================
    # 4. EXPERIENCE — 20 POINTS
    # ==================================================

    required_years = extract_required_years(full_text)

    warnings = []

    if required_years >= 5:

        experience_score = 0

        warnings.append(
            f"Requires approximately {required_years}+ "
            "years of experience."
        )

    elif required_years >= 3:

        experience_score = 7

        warnings.append(
            f"Requires approximately {required_years} "
            "years of experience."
        )

    elif required_years > 0:

        experience_score = 15

    else:

        junior_terms = [
            "junior",
            "entry level",
            "entry-level",
            "graduate",
            "intern",
            "internship",
            "trainee",
        ]

        senior_terms = [
            "senior",
            "lead developer",
            "lead engineer",
            "principal",
            "staff engineer",
            "manager",
            "director",
        ]

        if any(term in full_text for term in senior_terms):

            experience_score = 3

            warnings.append(
                "This appears to be a senior/experienced position."
            )

        elif any(term in full_text for term in junior_terms):

            experience_score = 20

        else:

            # Unknown experience requirement
            experience_score = 14

    # ==================================================
    # 5. LOCATION — 10 POINTS
    # ==================================================

    location_score = 0

    for location in JOB_PROFILE["locations"]:

        if location.lower() in full_text:

            location_score = 10
            break

    # ==================================================
    # 6. FINAL SCORE
    # ==================================================

    score = (
        role_score
        + skill_score
        + experience_score
        + location_score
    )

    score = max(
        0,
        min(round(score), 100),
    )

    # ==================================================
    # 7. CATEGORY
    # ==================================================

    if score >= 75:
        category = "STRONG MATCH"

    elif score >= 55:
        category = "POSSIBLE MATCH"

    elif score >= 40:
        category = "WEAK MATCH"

    else:
        category = "POOR MATCH"
    # ==================================================
    # 8. RECOMMENDATION
    # ==================================================

    # Jobs requiring 5+ years are automatically skipped
    if required_years >= 5:

        recommendation = "SKIP"

    # Jobs requiring 3+ years need manual review
    elif required_years >= 3:

        if score >= 55:
            recommendation = "REVIEW"
        else:
            recommendation = "SKIP"

    # Senior/lead positions should not be automatically applied to
    elif any(
        term in full_text
        for term in [
            "senior",
            "lead developer",
            "lead engineer",
            "principal",
            "staff engineer",
            "manager",
        ]
    ):

        recommendation = "REVIEW" if score >= 55 else "SKIP"

    # Strong matches
    elif score >= 70:

        recommendation = "APPLY"

    # Reasonable matches
    elif score >= 50:

        recommendation = "REVIEW"

    # Everything else
    else:

        recommendation = "SKIP"    

   
    return {
        "score": score,
        "category": category,
        "recommendation": recommendation,
        "role_matches": role_matches,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "warnings": warnings,
    }