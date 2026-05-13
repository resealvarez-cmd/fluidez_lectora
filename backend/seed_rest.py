import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

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

def seed():
    print("Seed via REST...")
    for t in textos_predefinidos:
        data = {
            "id": str(uuid.uuid4()),
            "titulo": t["titulo"],
            "contenido": t["contenido"],
            "nivel": t["nivel"]
        }
        supabase.table("textos").insert(data).execute()
        
    print("Textos creados")

if __name__ == "__main__":
    seed()
