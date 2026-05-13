import sys
import os
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar .env de backend
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Credenciales de Supabase no encontradas en .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def import_to_supabase():
    print(f"Conectando a Supabase ({SUPABASE_URL})...")
    
    excel_path = "../Listas_Cursos_20260506_1359.xlsx"
    xl = pd.ExcelFile(excel_path)
    
    # Obtener el primer colegio para asociarlo (si existe)
    res_colegios = supabase.table('colegios').select('id').limit(1).execute()
    colegio_id = None
    if res_colegios.data:
        colegio_id = res_colegios.data[0]['id']
        print(f"Asignando al colegio ID: {colegio_id}")
    else:
        print("No se encontraron colegios, se insertarán sin colegio_id")

    estudiantes_a_insertar = []

    for sheet_name in xl.sheet_names:
        print(f"Procesando curso: {sheet_name}")
        df = xl.parse(sheet_name, skiprows=3)
        
        curso_parts = sheet_name.split()
        if len(curso_parts) >= 3:
            curso_clean = f"{curso_parts[0][0]}{curso_parts[-1]}"
        else:
            curso_clean = sheet_name
        
        for index, row in df.iterrows():
            nombre_completo = row.get('NOMBRE COMPLETO')
            if pd.isna(nombre_completo):
                continue
                
            alumno_str = str(nombre_completo).strip()
            
            parts = alumno_str.split(' ', 2)
            if len(parts) >= 3:
                apellido = f"{parts[0]} {parts[1]}"
                nombre = parts[2]
            elif len(parts) == 2:
                apellido = parts[0]
                nombre = parts[1]
            else:
                apellido = parts[0]
                nombre = ""
                
            fecha_nac_val = row.get('NACIMIENTO')
            fecha_nac_str = None
            if pd.notna(fecha_nac_val) and isinstance(fecha_nac_val, datetime):
                fecha_nac_str = fecha_nac_val.date().isoformat()
                
            estudiante = {
                "nombre": nombre.title(),
                "apellido": apellido.title(),
                "curso": curso_clean,
                "colegio_id": colegio_id,
                "fecha_nacimiento": fecha_nac_str
            }
            estudiantes_a_insertar.append(estudiante)

    # Insertar en lotes de 100 para no saturar la API
    print(f"Insertando {len(estudiantes_a_insertar)} estudiantes en Supabase...")
    batch_size = 100
    for i in range(0, len(estudiantes_a_insertar), batch_size):
        batch = estudiantes_a_insertar[i:i+batch_size]
        res = supabase.table('estudiantes').insert(batch).execute()
        print(f"Lote insertado: {i} al {i+len(batch)}")

    print(f"¡Éxito! {len(estudiantes_a_insertar)} estudiantes subidos a Supabase.")

if __name__ == "__main__":
    import_to_supabase()
