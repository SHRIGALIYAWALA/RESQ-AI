"""Create or upgrade the RESQ-AI schema for the configured database.

This is intentionally idempotent for local and first-time PostgreSQL deployments.
Use Alembic revisions for future destructive or data-transforming migrations.
"""

from backend.database.database import Base, engine
import backend.models.building  # noqa: F401


def upgrade() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    upgrade()
    print(f"Schema ready on {engine.dialect.name}")