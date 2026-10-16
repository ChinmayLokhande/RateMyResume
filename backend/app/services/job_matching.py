"""Deterministic resume-to-JD matching. Scores estimate alignment, not hiring odds.

Score = 65% required skills + 15% preferred skills + 20% responsibility keywords.
Empty categories are skipped and the weights are rebalanced.
"""
import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobDescription, Resume, ResumeJobMatch

SCORING_VERSION = "keyword-rubric-v1"

# alias -> canonical name, so "ReactJS" counts as "React.js"
ALIASES = {
    "react": "react.js", "reactjs": "react.js", "nextjs": "next.js",
    "node": "node.js", "nodejs": "node.js", "postgres": "postgresql",
    "amazon web services": "aws", "continuous integration": "ci/cd",
    "continuous deployment": "ci/cd", "large language model": "llm",
    "large language models": "llm", "retrieval augmented generation": "rag",
    "single sign on": "sso", "rest api": "rest apis", "restful api": "rest apis",
    "microsoft azure": "azure",
}


def _clean(s: str) -> str:
    return re.sub(r"[\s_-]+", " ", s.lower().strip())


def contains_term(text: str, term: str) -> bool:
    canonical = ALIASES.get(_clean(term), _clean(term))
    variants = {canonical, _clean(term)} | {a for a, c in ALIASES.items() if c == canonical}
    haystack = _clean(text)
    for v in variants:
        pattern = r"(?<![a-z0-9])" + re.escape(v).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
        if re.search(pattern, haystack):
            return True
    return False


def _strings(values: Any) -> list[str]:
    return [v.strip() for v in values if isinstance(v, str) and v.strip()] if isinstance(values, list) else []


def score_resume(text: str, job: JobDescription) -> dict[str, Any]:
    req, pref, resp = _strings(job.required_skills), _strings(job.preferred_skills), _strings(job.responsibility_keywords)
    got_req = [s for s in req if contains_term(text, s)]
    got_pref = [s for s in pref if contains_term(text, s)]
    got_resp = [s for s in resp if contains_term(text, s)]

    parts = [(w, len(g), len(a)) for w, g, a in ((0.65, got_req, req), (0.15, got_pref, pref), (0.20, got_resp, resp)) if a]
    weight = sum(p[0] for p in parts)
    raw = sum(w * g / n for w, g, n in parts) / weight if weight else 0
    pct = max(0, min(100, round(raw * 100)))

    skills = list(dict.fromkeys(got_req + got_pref))
    evidence = [f"Resume text mentions {s}." for s in skills[:6]]
    evidence += [f"Resume text includes experience related to {t}." for t in got_resp[:3]]
    summary = (f"Matched {len(got_req)} of {len(req)} required and {len(got_pref)} of {len(pref)} preferred skills."
               if skills else "Few or none of the job's listed skills were found in the resume text.")
    if got_resp:
        summary += f" Found {len(got_resp)} relevant responsibility keywords."
    return {
        "fit_percentage": pct,
        "matching_skills": skills,
        "missing_required_skills": [s for s in req if s not in got_req],
        "relevant_evidence": evidence,
        "match_summary": summary,
    }


def get_saved_matches(db: Session, resume_id) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ResumeJobMatch, JobDescription)
        .join(JobDescription, JobDescription.id == ResumeJobMatch.job_description_id)
        .where(ResumeJobMatch.resume_id == resume_id, JobDescription.is_active.is_(True))
        .order_by(ResumeJobMatch.fit_percentage.desc(), JobDescription.title.asc())
        .limit(3)  # top three only
    ).all()
    return [{
        "job_id": j.id, "job_title": j.title, "fit_percentage": m.fit_percentage,
        "matching_skills": _strings(m.matching_skills),
        "missing_required_skills": _strings(m.missing_required_skills),
        "relevant_evidence": _strings(m.relevant_evidence),
        "match_summary": m.match_summary, "calculated_at": m.calculated_at,
    } for m, j in rows]


def calculate_and_save_matches(db: Session, resume: Resume) -> list[dict[str, Any]]:
    text = (resume.extracted_text or "").strip()
    if not text:
        raise ValueError("Resume text is not available yet.")
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    jobs = db.scalars(select(JobDescription).where(JobDescription.is_active.is_(True))).all()
    if not jobs:
        raise LookupError("No active job descriptions. Run the seed script.")

    # one query for all existing matches (no N+1)
    existing = {m.job_description_id: m for m in db.scalars(
        select(ResumeJobMatch).where(ResumeJobMatch.resume_id == resume.id))}
    now = datetime.now(timezone.utc)
    for job in jobs:
        row = existing.get(job.id)
        # reuse the saved score unless resume text, JD, or scoring version changed
        if row and row.resume_text_hash == text_hash and row.job_updated_at == job.updated_at \
                and row.scoring_version == SCORING_VERSION:
            continue
        result = score_resume(text, job)
        if row is None:
            row = ResumeJobMatch(resume_id=resume.id, job_description_id=job.id)
            db.add(row)
        for key, value in result.items():
            setattr(row, key, value)
        row.resume_text_hash = text_hash
        row.job_updated_at = job.updated_at or now
        row.scoring_version = SCORING_VERSION
        row.calculated_at = now
    db.commit()
    return get_saved_matches(db, resume.id)