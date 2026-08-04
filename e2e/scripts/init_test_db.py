"""
Inicializa banco SQLite isolado para testes E2E.
"""

import asyncio
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

DB_PATH = ROOT / "e2e-test.db"
UPLOAD_DIR = ROOT / "e2e-uploads"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"
os.environ["UPLOAD_DIR"] = str(UPLOAD_DIR)

from app.database import Base, engine  # noqa: E402
from app.models import (  # noqa: E402, F401
    Analysis,
    Correction,
    Document,
    DocumentItem,
    LegalDocument,
    LegalChunk,
)


async def init_db() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    if UPLOAD_DIR.exists():
        for file in UPLOAD_DIR.iterdir():
            if file.is_file():
                file.unlink()
    else:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
    print(f"Banco E2E inicializado: {DB_PATH}")
