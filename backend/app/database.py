"""
Sesión async de base de datos
- En dev local: SQLite (sin configuración extra)
- En producción: PostgreSQL via Supabase (asyncpg)
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings
from app.models import Base
from sqlalchemy.pool import NullPool
import ssl

settings = get_settings()


def _build_db_url(url: str) -> tuple[str, dict]:
    """
    Normaliza la URL de conexión y devuelve (url_limpia, connect_args).
    - asyncpg NO acepta ssl= como query param → va en connect_args
    - postgresql://  → postgresql+asyncpg://
    - postgres://    → postgresql+asyncpg://  (formato Supabase/Heroku)
    - sqlite:///     → sqlite+aiosqlite:///
    """
    connect_args: dict = {}

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite:///") and "+aiosqlite" not in url:
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    if "postgresql" in url:
        # Eliminar ssl= de la URL (asyncpg no lo soporta como query param)
        import re
        url = re.sub(r'[?&]ssl=[^&]*', '', url)
        url = re.sub(r'[?&]sslmode=[^&]*', '', url)
        url = url.rstrip('?&')

        # Pasar SSL correctamente via connect_args
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args = {
            "ssl": ssl_ctx,
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        }

    return url, connect_args


_db_url, _connect_args = _build_db_url(settings.DATABASE_URL)
_is_sqlite = "sqlite" in _db_url

# Configuración del motor (Engine)
if not _is_sqlite:
    # Producción: NullPool para compatibilidad con Supabase Pooler (PgBouncer)
    engine = create_async_engine(
        _db_url,
        poolclass=NullPool,
        connect_args=_connect_args,
    )
else:
    # Desarrollo local: SQLite
    engine = create_async_engine(
        _db_url,
        connect_args={"check_same_thread": False}
    )

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
