from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    import backend.models.building  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
        if "analysis_json" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE incidents ADD COLUMN analysis_json TEXT DEFAULT '{}'"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
