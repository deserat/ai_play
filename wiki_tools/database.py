from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Settings
from wiki_tools.models import Base

settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
