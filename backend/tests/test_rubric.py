from app.services.rubric import compute_rubric

GOOD = """Test Person
Pune, India | test@example.com | +919000000000

WORK EXPERIENCE
Software Engineer, Example Corp
2021 - 2024
Built an API serving 50000 users and cut latency by 40%.
Reduced infrastructure cost by 25% through caching.
Automated reports, saving 10 hours per week.
Improved test coverage by 30%.
Migrated 12 services with zero downtime, up 15%.

EDUCATION
BSc Computer Science
2017 - 2020

SKILLS
Python, SQL

PROJECTS
Resume tool
"""
SKILLS_10 = [f"skill{i}" for i in range(10)]


def _score(text=GOOD, **overrides):
    args = dict(email="a@example.com", mobile="+919000000000", location="Pune", skills=SKILLS_10)
    args.update(overrides)
    return compute_rubric(text, **args)


def _points(result, key):
    return {c.key: c.points for c in result.criteria}[key]


def test_contact_points():
    assert _points(_score(), "contact") == 20
    assert _points(_score(email=None, mobile=None), "contact") == 5


def test_sections_are_found_from_headings():
    assert _points(_score(), "structure") == 30
    assert _points(_score("WORK EXPERIENCE\nSomething"), "structure") == 10


def test_quantified_achievements_are_counted_by_line():
    assert _points(_score(), "impact") == 20
    assert _points(_score("Built things."), "impact") == 0


def test_skill_tiers():
    assert _points(_score(skills=[]), "skills") == 0
    assert _points(_score(skills=["a", "b"]), "skills") == 5
    assert _points(_score(skills=["a"] * 5), "skills") == 10
    assert _points(_score(), "skills") == 15


def test_empty_resume_scores_zero_and_explains_gaps():
    result = compute_rubric("hello", email=None, mobile=None, location=None, skills=[])
    assert result.score == 0
    assert "Email address not found" in result.missing
    assert "No quantified achievements found" in result.missing


def test_score_is_sum_of_criteria_and_capped_at_100():
    result = _score()
    assert result.score == sum(c.points for c in result.criteria)
    assert 0 <= result.score <= 100
    assert sum(c.max_points for c in result.criteria) == 100