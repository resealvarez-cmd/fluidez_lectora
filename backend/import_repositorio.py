import os
import json
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

with open('../repositorio_fluidez_lectora.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Importando {len(data['texts'])} textos...")

for t in data["texts"]:
    # Determine level
    level = "1basico"
    if t["cycle"] == "primer_ciclo":
        # Map difficulties 1-6 to 1-4 basico
        if t["difficulty_level"] <= 2: level = "1basico"
        elif t["difficulty_level"] <= 4: level = "2basico"
        elif t["difficulty_level"] <= 5: level = "3basico"
        else: level = "4basico"
    elif t["cycle"] == "segundo_ciclo":
        # 5-8 basico
        if t["difficulty_level"] <= 2: level = "5basico"
        elif t["difficulty_level"] <= 3: level = "6basico"
        elif t["difficulty_level"] <= 4: level = "7basico"
        else: level = "8basico"
    else:
        # Tercer ciclo -> map to 8basico for now
        level = "8basico"
        
    db_data = {
        "id": str(uuid.uuid4()),
        "titulo": t["title"],
        "contenido": t["text"],
        "nivel": level
    }
    
    supabase.table("textos").insert(db_data).execute()

print("¡Importación completada!")
