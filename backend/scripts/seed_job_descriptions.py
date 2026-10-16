"""Idempotently seed the five sample job descriptions. Run from backend/: python -m scripts.seed_job_descriptions"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import JobDescription

JOBS = [
    {
        "title": "Full Stack Developer",
        "description": "Build and maintain responsive web applications across frontend and backend. Collaborate with product and design teams, create REST APIs, integrate SQL and NoSQL databases, write tests, and improve application performance. Experience with React.js, Next.js, Node.js, HTML, CSS, and JavaScript is valuable.",
        "required_skills": ["React.js", "Node.js", "REST APIs", "JavaScript"],
        "preferred_skills": ["Next.js", "SQL", "NoSQL", "HTML", "CSS", "TypeScript"],
        "responsibility_keywords": ["frontend development", "backend development", "responsive web applications", "application performance", "database integration"],
        "experience_years": 3,
    },
    {
        "title": "Backend Engineer",
        "description": "Design reliable backend services and APIs using Python and FastAPI. Build secure REST APIs, model data in PostgreSQL, implement asynchronous processing, optimize queries, write automated tests, and operate services in production.",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "API design"],
        "preferred_skills": ["SQLAlchemy", "Redis", "Celery", "Docker", "pytest", "asynchronous processing"],
        "responsibility_keywords": ["backend services", "REST APIs", "query optimization", "automated tests", "production services"],
        "experience_years": 3,
    },
    {
        "title": "DevOps / Cloud Engineer",
        "description": "Automate and operate cloud infrastructure with AWS, containers, CI/CD pipelines, monitoring, and infrastructure automation. Improve deployment reliability, troubleshoot production incidents, manage access and security, and document operational procedures.",
        "required_skills": ["AWS", "Docker", "CI/CD", "monitoring"],
        "preferred_skills": ["Kubernetes", "Terraform", "Linux", "Azure", "infrastructure automation", "networking"],
        "responsibility_keywords": ["cloud infrastructure", "deployment reliability", "production incidents", "access and security", "operational procedures"],
        "experience_years": 3,
    },
    {
        "title": "AI Application Engineer",
        "description": "Develop AI-enabled applications using Python and large language model integrations. Implement retrieval-augmented generation (RAG), connect vector databases, design prompts, evaluate response quality, protect sensitive data, and expose capabilities through reliable APIs.",
        "required_skills": ["Python", "LLM", "RAG", "prompt engineering"],
        "preferred_skills": ["vector databases", "embeddings", "FastAPI", "evaluation", "REST APIs", "retrieval augmented generation"],
        "responsibility_keywords": ["AI-enabled applications", "model integration", "response quality", "sensitive data", "reliable APIs"],
        "experience_years": 2,
    },
    {
        "title": "Technical Implementation Engineer",
        "description": "Own customer implementations from discovery and requirements gathering through integrations, testing, deployment, and post-launch support. Configure SSO, integrate HRMS and third-party systems, customize reports, troubleshoot issues, and communicate clearly with client and internal stakeholders.",
        "required_skills": ["requirements gathering", "system integrations", "SSO", "deployments"],
        "preferred_skills": ["HRMS", "troubleshooting", "client communication", "custom reports", "REST APIs", "project coordination"],
        "responsibility_keywords": ["customer implementations", "post-launch support", "third-party systems", "client stakeholders", "integration testing"],
        "experience_years": 3,
    },
]


def main() -> None:
    with SessionLocal() as db:
        created = updated = 0
        for data in JOBS:
            row = db.scalar(select(JobDescription).where(JobDescription.title == data["title"]))
            if row is None:
                db.add(JobDescription(**data, is_active=True))
                created += 1
            else:
                changed = False
                for key, value in data.items():
                    if getattr(row, key) != value:
                        setattr(row, key, value)
                        changed = True
                if not row.is_active:
                    row.is_active = True
                    changed = True
                if changed:
                    updated += 1
        db.commit()
        print(f"Seed complete: {created} created, {updated} updated.")


if __name__ == "__main__":
    main()