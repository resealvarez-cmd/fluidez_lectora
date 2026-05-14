import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, Usuario
from app.routers.auth import hash_password
from app.config import get_settings
import sys

async def create_admin():
    settings = get_settings()
    
    # Normalización de URL para asyncpg (misma lógica que database.py)
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    if "postgresql" in url and "ssl" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}ssl=require"

    print(f"Conectando a: {url.split('@')[-1]}") # No mostrar password
    
    engine = create_async_engine(url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        email = "admin@profeic.cl"
        password = "admin.fluidez.2026" # Cambiar tras primer login
        
        from sqlalchemy import select
        result = await db.execute(select(Usuario).where(Usuario.email == email))
        if result.scalar_one_or_none():
            print(f"El usuario {email} ya existe.")
            return

        new_user = Usuario(
            email=email,
            nombre="Administrador ProfeIC",
            hashed_password=hash_password(password),
            rol="docente",
            colegio_id="PROFEIC-MAIN"
        )
        
        db.add(new_user)
        await db.commit()
        print(f"✅ Usuario {email} creado exitosamente.")
        print(f"🔑 Password temporal: {password}")

if __name__ == "__main__":
    asyncio.run(create_admin())
