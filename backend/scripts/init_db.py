"""Initialize the PostgreSQL database (extensions + ORM schema).

Usage:
    python scripts/init_db.py

For production, prefer ``alembic upgrade head`` so migrations stay auditable.
This helper is intended for local development / quick demos where the database
is empty and no migration history exists yet.
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401  (register all tables)
from app.core.config import settings
from app.core.database import Base


async def init_db() -> None:
    print(f"Connecting to: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    for extension in ("uuid-ossp", "vector"):
        try:
            async with engine.begin() as conn:
                if extension == "vector":
                    # Native Windows installs often expose pgvector's type and
                    # functions from a staged DLL without an extension control
                    # file. Running CREATE EXTENSION in that setup can load a
                    # second copy of the library and break vector queries.
                    type_exists = await conn.scalar(
                        text("SELECT 1 FROM pg_type WHERE typname = 'vector'")
                    )
                    if type_exists:
                        print("  ✓ extension ready: vector (type already present)")
                        continue
                await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{extension}";'))
            print(f"  ✓ extension ready: {extension}")
        except Exception as exc:
            print(f"  ! could not enable extension {extension}: {exc}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓ tables created / verified")

    await engine.dispose()
    print("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
