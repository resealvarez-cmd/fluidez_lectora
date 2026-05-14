"""
Sesión async de base de datos
- En dev local: SQLite (sin configuración extra)
- En producción: PostgreSQL via Supabase (asyncpg)
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings
from app.models import Base
from sqlalchemy.pool import NullPool

settings = get_settings()


def _build_db_url(url: str) -> str:
    """
    Normaliza la URL de conexión:
    - postgresql://  → postgresql+asyncpg://
    - postgres://    → postgresql+asyncpg://  (formato Supabase/Heroku)
    - sqlite:///     → sqlite+aiosqlite:///
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite:///") and "+aiosqlite" not in url:
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    
    # Asegurar SSL para PostgreSQL en producción (Vital para Render/Supabase)
    if "postgresql" in url and "ssl" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}ssl=require"
        
    return url


_db_url = _build_db_url(settings.DATABASE_URL)
_is_sqlite = "sqlite" in _db_url

kwargs = {
    "echo": False,
}

# Configuración específica para el Pooler de Supabase
if not _is_sqlite:
    kwargs["poolclass"] = NullPool
    kwargs["connect_args"] = {
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0
    }
else:
    kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(_db_url, **kwargs)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """
    Crea las tablas si no existen.
    Funciona tanto en SQLite como en PostgreSQL (Supabase).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
