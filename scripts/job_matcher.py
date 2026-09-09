from config.profile import JOB_PROFILE


def calculate_match(job_title, job_description):
    """
    Calculate how well a job matches Elizabeth's profile.
    """

    title = job_title.lower()
    description = job_description.lower()
    full_text = f"{title} {description}"

    target_roles = JOB_PROFILE["target_roles"]
    skills = JOB_PROFILE["skills"]

    score = 0
    matching_skills = []
    missing_skills = []
    warnings = []

    # --------------------------------
    # 1. Job title matching
    # --------------------------------

    title_matches = [
        role for role in target_roles
        if role.lower() in title
    ]

    if title_matches:
        score += 30

    # --------------------------------
    # 2. Skills matching
    # --------------------------------

    for skill in skills:
        if skill.lower() in description:
            matching_skills.append(skill)

    if skills:
        skill_score = (
            len(matching_skills) / len(skills)
        ) * 50

        score += skill_score

    # --------------------------------
    # 3. Experience level
    # --------------------------------

    junior_keywords = [
        "junior",
        "entry level",
        "entry-level",
        "graduate",
        "intern",
        "internship",
        "0-2 years",
        "0–2 years",
        "1-2 years",
        "1–2 years",
        "0 to 2 years",
        "1 to 2 years",
    ]

    senior_keywords = [
        "senior",
        "lead developer",
        "lead engineer",
        "principal",
        "staff engineer",
        "manager",
        "5+ years",
        "5 or more years",
        "6+ years",
        "7+ years",
        "8+ years",
    ]

    if any(keyword in full_text for keyword in junior_keywords):
        score += 20

    if any(keyword in full_text for keyword in senior_keywords):
        score -= 30
        warnings.append(
            "This appears to be a senior/experienced position."
        )

    # --------------------------------
    # 4. Experience requirements
    # --------------------------------

    experience_requirements = {
        "3+ years": 3,
        "4+ years": 4,
        "5+ years": 5,
        "6+ years": 6,
        "7+ years": 7,
        "8+ years": 8,
    }

    for requirement, years in experience_requirements.items():
        if requirement in full_text and years >= 3:
            score -= 15
            warnings.append(
                f"Requires approximately {requirement} of experience."
            )
            break

    # --------------------------------
    # 5. Missing skills
    # --------------------------------

    for skill in skills:
        if skill.lower() not in description:
            missing_skills.append(skill)

    # --------------------------------
    # 6. Keep score between 0 and 100
    # --------------------------------

    score = max(0, min(round(score), 100))

    # --------------------------------
    # 7. Match category
    # --------------------------------

    if score >= 80:
        category = "STRONG MATCH"
    elif score >= 60:
        category = "POSSIBLE MATCH"
    else:
        category = "POOR MATCH"

    return {
        "score": score,
        "category": category,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "warnings": warnings,
    }