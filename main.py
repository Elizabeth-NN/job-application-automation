from scripts.job_matcher import calculate_match


job_title = "Junior Backend Developer"

job_description = """
We are looking for a Junior Backend Developer.

Requirements:

Python
Flask
REST APIs
Git
SQL
Database design
React is an advantage
0-2 years of experience

The successful candidate will work with the development
team to build and maintain web applications and APIs.
"""


result = calculate_match(
    job_title,
    job_description
)


print("\nJOB MATCH RESULTS")
print("=================")

print(f"Job: {job_title}")
print(f"Match Score: {result['score']}%")
print(f"Category: {result['category']}")

print("\nMatching Skills:")

for skill in result["matching_skills"]:
    print(f"  ✓ {skill}")

print("\nWarnings:")

if result["warnings"]:
    for warning in result["warnings"]:
        print(f"  ⚠ {warning}")
else:
    print("  None")

print("\nMissing Skills:")

for skill in result["missing_skills"]:
    print(f"  - {skill}")