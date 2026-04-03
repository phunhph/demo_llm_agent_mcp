# database/db_config.py
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)
# File DB cố định trong thư mục project (không phụ thuộc cwd)
_DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{(_ROOT / 'warehouse_demo.db').as_posix()}"

# Thứ tự ưu tiên:
# 1) WAREHOUSE_SQLITE_DEMO=1 → luôn dùng SQLite (hữu ích khi DATABASE_URL Postgres trong .env bị sai).
# 2) DATABASE_URL được set → dùng (thường là PostgreSQL).
# 3) Không set → SQLite mặc định (demo không cần Postgres).
_raw = (os.getenv("DATABASE_URL") or "").strip()
_force_sqlite = os.getenv("WAREHOUSE_SQLITE_DEMO", "").lower() in ("1", "true", "yes")
if _force_sqlite:
    DATABASE_URL = _DEFAULT_SQLITE_URL
elif _raw:
    DATABASE_URL = _raw
else:
    DATABASE_URL = _DEFAULT_SQLITE_URL

IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def ensure_demo_schema() -> None:
    """SQLite: tự tạo bảng. PostgreSQL: giả định đã migrate (Alembic)."""
    if not IS_SQLITE:
        return
    from database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
