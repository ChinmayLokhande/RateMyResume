from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

from collections.abc import Iterator

from sqlalchemy.orm import Session

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session