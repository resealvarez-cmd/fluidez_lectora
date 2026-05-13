import asyncio
from app.database import AsyncSessionLocal
from app.models import Texto, Colegio, Estudiante
import uuid

textos_predefinidos = [
    {
        "titulo": "La foca Filomena",
        "nivel": "1basico",
        "contenido": "La foca Filomena se asoma a la roca. Usa una pelota redonda y hermosa. Juega en la espuma y saluda a la luna."
    },
    {
        "titulo": "El perrito Dido",
        "nivel": "1basico",
        "contenido": "Dido es mi perrito regalón. Mueve su cola cuando le doy un hueso. Le gusta correr por el pasto y jugar con la pelota verde."
    },
    {
        "titulo": "La mariposa Rosa",
        "nivel": "2basico",
        "contenido": "La mariposa Rosa tiene alas hermosas. Vuela de flor en flor en el jardín de mi casa. Sus colores brillan con la luz del sol en la mañana."
    },
    {
        "titulo": "El paseo al parque",
        "nivel": "2basico",
        "contenido": "El domingo fuimos al parque con mi familia. Mi papá llevó la bicicleta y mi mamá preparó unos ricos sándwiches. Jugamos en los columpios toda la tarde."
    }
]

async def seed():
    async with AsyncSessionLocal() as session:
        for t in textos_predefinidos:
            texto = Texto(
                id=str(uuid.uuid4()),
                titulo=t["titulo"],
                contenido=t["contenido"],
                nivel=t["nivel"]
            )
            session.add(texto)
        
        # Add a test school and student
        col = Colegio(id=str(uuid.uuid4()), nombre="Colegio Demo", rbd="12345")
        session.add(col)
        
        est = Estudiante(
            id=str(uuid.uuid4()),
            nombre="Juanito",
            apellido="Pérez",
            curso="1A",
            colegio_id=col.id
        )
        session.add(est)
        
        await session.commit()
        print("Datos insertados correctamente en Supabase.")

if __name__ == "__main__":
    asyncio.run(seed())
