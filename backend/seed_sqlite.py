import asyncio
import json
import uuid
from app.database import AsyncSessionLocal, init_db
from app.models import Texto

async def seed():
    await init_db()
    with open('../repositorio_fluidez_lectora.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    async with AsyncSessionLocal() as session:
        for t in data["texts"]:
            level = "1basico"
            if t["cycle"] == "primer_ciclo":
                if t["difficulty_level"] <= 2: level = "1basico"
                elif t["difficulty_level"] <= 4: level = "2basico"
                elif t["difficulty_level"] <= 5: level = "3basico"
                else: level = "4basico"
            elif t["cycle"] == "segundo_ciclo":
                if t["difficulty_level"] <= 2: level = "5basico"
                elif t["difficulty_level"] <= 3: level = "6basico"
                elif t["difficulty_level"] <= 4: level = "7basico"
                else: level = "8basico"
            else:
                level = "8basico"
                
            texto = Texto(
                id=str(uuid.uuid4()),
                titulo=t["title"],
                contenido=t["text"],
                nivel=level
            )
            session.add(texto)
        await session.commit()
    print("¡Importado a SQLite local!")

if __name__ == "__main__":
    asyncio.run(seed())
