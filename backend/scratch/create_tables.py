import asyncio
from app.database import engine
from app.models import Base

async def create_tables():
    print("Conectando a Supabase para crear tablas...")
    async with engine.begin() as conn:
        # Esto creará las tablas que no existan sin borrar los datos de las existentes
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tablas creadas/actualizadas correctamente en Supabase.")

if __name__ == "__main__":
    asyncio.run(create_tables())
