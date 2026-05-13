import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Lectura

async def check_errors():
    async with AsyncSessionLocal() as db:
        stmt = select(Lectura).where(Lectura.estado == "error").order_by(Lectura.created_at.desc()).limit(5)
        res = await db.execute(stmt)
        lecturas = res.scalars().all()
        for l in lecturas:
            print(f"Lectura ID: {l.id} | Error: {l.error_mensaje}")

if __name__ == "__main__":
    asyncio.run(check_errors())
