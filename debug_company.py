import requests
from bs4 import BeautifulSoup

URL = "https://www.brightermonday.co.ke/listings/senior-data-analyst-j6jmez"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status:", response.status_code)
print("URL:", response.url)
print()

soup = BeautifulSoup(response.text, "html.parser")

print("=" * 60)
print("TITLE")
print("=" * 60)

print(soup.title.get_text(" ", strip=True) if soup.title else "NO TITLE")

print()
print("=" * 60)
print("H1")
print("=" * 60)

for h1 in soup.find_all("h1"):
    print(h1.get_text(" ", strip=True))

print()
print("=" * 60)
print("JSON-LD")
print("=" * 60)

for script in soup.find_all(
    "script",
    type="application/ld+json"
):
    print(script.get_text(strip=True))
    print("-" * 60)

print()
print("=" * 60)
print("TEXT AROUND 'Senior Data Analyst'")
print("=" * 60)

text = soup.get_text("\n", strip=True)

lines = text.splitlines()

for i, line in enumerate(lines):

    if "Senior Data Analyst" in line:
        start = max(0, i - 10)
        end = min(len(lines), i + 30)

        for item in lines[start:end]:
            print(item)

        print("-" * 60)

print()
print("=" * 60)
print("POSSIBLE COMPANY ELEMENTS")
print("=" * 60)

selectors = [
    "[class*='company']",
    "[class*='employer']",
    "[data-testid*='company']",
    "[data-testid*='employer']",
]

for selector in selectors:

    print()
    print("SELECTOR:", selector)

    elements = soup.select(selector)

    for element in elements:

        print(
            "TEXT:",
            element.get_text(" ", strip=True)
        )

        print(
            "HTML:",
            str(element)[:1000]
        )

        print("-" * 40)
