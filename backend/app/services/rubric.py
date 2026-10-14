import re
from dataclasses import dataclass

RUBRIC_VERSION = "rubric-v1"

SECTION_PATTERNS = {
    "experience": re.compile(r"\b(experience|employment|internship)"),
    "education": re.compile(r"\b(education|academic|qualification)"),
    "skills": re.compile(r"\b(skills|technologies|tech stack)"),
    "projects": re.compile(r"\b(projects?|portfolio)"),
}
SECTION_POINTS = {"experience": 10, "education": 8, "skills": 6, "projects": 6}
SECTION_LABELS = {
    "experience": "work experience",
    "education": "education",
    "skills": "skills",
    "projects": "projects",
}
METRIC_RE = re.compile(
    r"\d+(\.\d+)?\s?%|[$₹€£]\s?\d"
    r"|\b\d[\d,]*\+?\s?(users|customers|clients|requests|records|hours|ms|x)\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


@dataclass(frozen=True)
class Criterion:
    key: str
    label: str
    points: int
    max_points: int
    explanation: str


@dataclass(frozen=True)
class RubricResult:
    score: int
    criteria: list[Criterion]
    missing: list[str]


def _found_sections(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        line = line.strip().lower()
        if not line or len(line) > 40:  # headings are short
            continue
        for key, pattern in SECTION_PATTERNS.items():
            if pattern.search(line):
                found.add(key)
    return found


def compute_rubric(
    text: str,
    *,
    email: str | None,
    mobile: str | None,
    location: str | None,
    skills: list[str],
) -> RubricResult:
    missing: list[str] = []
    criteria: list[Criterion] = []

    # 1. Contact details (20)
    contact_points, contact_found = 0, 0
    for value, points, label in (
        (email, 10, "Email address"),
        (mobile, 5, "Phone number"),
        (location, 5, "Location"),
    ):
        if value:
            contact_points += points
            contact_found += 1
        else:
            missing.append(f"{label} not found")
    criteria.append(Criterion(
        "contact", "Contact details", contact_points, 20,
        f"Found {contact_found} of 3 contact details (email 10, phone 5, location 5).",
    ))

    # 2. Structure (30)
    found = _found_sections(text)
    structure_points = sum(SECTION_POINTS[key] for key in found)
    for key in SECTION_POINTS:
        if key not in found:
            missing.append(f"No {SECTION_LABELS[key]} section found")
    criteria.append(Criterion(
        "structure", "Structure", structure_points, 30,
        f"Sections found: {', '.join(sorted(found)) or 'none'} "
        "(experience 10, education 8, skills 6, projects 6).",
    ))

    # 3. Skills (15)
    skill_count = len(skills)
    skill_points = 15 if skill_count >= 10 else 10 if skill_count >= 5 else 5 if skill_count >= 1 else 0
    if skill_count < 5:
        missing.append("Fewer than 5 skills identified")
    criteria.append(Criterion(
        "skills", "Skills", skill_points, 15,
        f"{skill_count} skills identified (1+ earns 5, 5+ earns 10, 10+ earns 15).",
    ))

    # 4. Impact (20)
    metric_lines = sum(1 for line in text.splitlines() if METRIC_RE.search(line))
    impact_points = 20 if metric_lines >= 5 else 14 if metric_lines >= 3 else 8 if metric_lines >= 1 else 0
    if metric_lines == 0:
        missing.append("No quantified achievements found")
    criteria.append(Criterion(
        "impact", "Measurable impact", impact_points, 20,
        f"{metric_lines} lines contain measurable results (1+ earns 8, 3+ earns 14, 5+ earns 20).",
    ))

    # 5. Clarity (15)
    words = len(text.split())
    if 250 <= words <= 1000:
        length_points = 8
    elif 150 <= words < 250 or 1000 < words <= 1400:
        length_points = 4
    else:
        length_points = 0
    if words < 150:
        missing.append("Resume text is very short")
    elif words > 1400:
        missing.append("Resume text is very long")
    years = len(YEAR_RE.findall(text))
    date_points = 7 if years >= 2 else 0
    if date_points == 0:
        missing.append("Few or no dates found")
    criteria.append(Criterion(
        "clarity", "Length and dates", length_points + date_points, 15,
        f"{words} words (250-1000 earns 8) and {years} year mentions (2+ earns 7).",
    ))

    return RubricResult(sum(c.points for c in criteria), criteria, missing)