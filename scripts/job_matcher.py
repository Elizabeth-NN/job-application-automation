from config.profile import JOB_PROFILE


def calculate_match(job_title, job_description):
    """
    Calculate how well a job matches Elizabeth's profile.
    Returns a score, matching skills and missing skills.
    """

    title = job_title.lower()
    description = job_description.lower()

    target_roles = JOB_PROFILE["target_roles"]
    skills = JOB_PROFILE["skills"]

    score = 0
    matching_skills = []
    missing_skills = []

    # -------------------------
    # Job title matching
    # -------------------------

    title_matches = 0

    for role in target_roles:
        if role.lower() in title:
            title_matches += 1

    if title_matches > 0:
        score += 30

    # -------------------------
    # Skills matching
    # -------------------------

    for skill in skills:
        if skill.lower() in description:
            matching_skills.append(skill)

    if skills:
        skill_score = (len(matching_skills) / len(skills)) * 60
        score += skill_score

    # -------------------------
    # Experience level
    # -------------------------

    experience_keywords = [
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
    ]

    if any(keyword in title or keyword in description
           for keyword in experience_keywords):
        score += 10

    # -------------------------
    # Missing skills
    # -------------------------

    for skill in skills:
        if skill.lower() not in description:
            missing_skills.append(skill)

    # Never exceed 100
    score = min(round(score), 100)

    return {
        "score": score,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
    }