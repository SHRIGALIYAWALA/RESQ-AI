from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
pool_args = {"poolclass": NullPool} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True, **pool_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    import backend.models.building  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        for table_name, column_sql in (("buildings", "tenant_id TEXT NOT NULL DEFAULT 'demo'"), ("incidents", "tenant_id TEXT NOT NULL DEFAULT 'demo'")):
            columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
            if "tenant_id" not in columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
        columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
        if "analysis_json" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE incidents ADD COLUMN analysis_json TEXT DEFAULT '{}'"))
        columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
        if "summary" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE incidents ADD COLUMN summary TEXT DEFAULT ''"))
        review_cols = {
            "review_status": "TEXT DEFAULT 'pending_review'",
            "review_decision": "TEXT DEFAULT ''",
            "reviewed_by": "TEXT DEFAULT ''",
            "reviewed_at": "TEXT DEFAULT ''",
            "review_notes": "TEXT DEFAULT ''",
        }
        incident_columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
        for col_name, col_def in review_cols.items():
            if col_name not in incident_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_def}"))
        # Migrate Notification table
        notif_columns = {column["name"] for column in inspect(engine).get_columns("notifications")}
        for col_def in (
            ("recipient_type", "TEXT DEFAULT 'occupant'"),
            ("channel", "TEXT DEFAULT 'local_display'"),
            ("address", "TEXT DEFAULT ''"),
            ("approved", "INTEGER DEFAULT 0"),
        ):
            if col_def[0] not in notif_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE notifications ADD COLUMN {col_def[0]} {col_def[1]}"))
        # Building geolocation columns
        building_columns = {column["name"] for column in inspect(engine).get_columns("buildings")}
        for col_name, col_type in (("latitude", "REAL"), ("longitude", "REAL")):
            if col_name not in building_columns:
                try:
                    with engine.begin() as connection:
                        connection.execute(text(f"ALTER TABLE buildings ADD COLUMN {col_name} {col_type}"))
                except Exception:
                    pass
        camera_columns = {column["name"] for column in inspect(engine).get_columns("cameras")}
        if "source" not in camera_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE cameras ADD COLUMN source TEXT DEFAULT ''"))
        # Drop deprecated simulations table if present
        if "simulations" in inspect(engine).get_table_names():
            try:
                with engine.begin() as connection:
                    connection.execute(text("DROP TABLE IF EXISTS simulations"))
            except Exception:
                pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
