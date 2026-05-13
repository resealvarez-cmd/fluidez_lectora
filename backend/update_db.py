import asyncio
from sqlalchemy import text
from app.database import engine

async def update_schema():
    async with engine.begin() as conn:
        print("Agregando nuevas columnas a la tabla 'metricas'...")
        try:
            await conn.execute(text("ALTER TABLE metricas ADD COLUMN IF NOT EXISTS wcpm_proyectado BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE metricas ADD COLUMN IF NOT EXISTS es_texto_breve BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE metricas ADD COLUMN IF NOT EXISTS conteo_palabras VARCHAR"))
            await conn.execute(text("ALTER TABLE metricas ADD COLUMN IF NOT EXISTS nivel_ace VARCHAR"))
            print("Esquema actualizado correctamente.")
        except Exception as e:
            print(f"Error al actualizar el esquema: {e}")

if __name__ == "__main__":
    asyncio.run(update_schema())
