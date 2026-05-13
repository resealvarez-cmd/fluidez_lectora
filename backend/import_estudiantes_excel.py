import sys
import os
import pandas as pd
import asyncio
from datetime import datetime

# Añadir el path para que encuentre "app"
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.database import AsyncSessionLocal, init_db
from app.models import Estudiante, Colegio
from sqlalchemy.future import select

async def import_excel():
    print("Iniciando importación de estudiantes desde Excel...")
    await init_db()
    
    excel_path = "../Listas_Cursos_20260506_1359.xlsx"
    xl = pd.ExcelFile(excel_path)
    
    async with AsyncSessionLocal() as session:
        # Obtener el colegio por defecto si existe
        stmt = select(Colegio).limit(1)
        result = await session.execute(stmt)
        colegio = result.scalars().first()
        
        colegio_id = colegio.id if colegio else None
        
        # Eliminar estudiantes existentes para evitar duplicados si se corre varias veces
        # (Opcional, pero recomendado si se reimporta)
        # await session.execute("DELETE FROM estudiantes")
        
        count = 0
        for sheet_name in xl.sheet_names:
            print(f"Procesando curso: {sheet_name}")
            # Saltar las 3 primeras filas de encabezados del colegio
            df = xl.parse(sheet_name, skiprows=3)
            
            # Formatear el curso a "1A", "1B", "2A", etc.
            curso_parts = sheet_name.split()
            if len(curso_parts) >= 3:
                curso_clean = f"{curso_parts[0][0]}{curso_parts[-1]}" # Ej: "1° básico A" -> "1A"
            else:
                curso_clean = sheet_name
            
            for index, row in df.iterrows():
                nombre_completo = row.get('NOMBRE COMPLETO')
                if pd.isna(nombre_completo):
                    continue
                    
                alumno_str = str(nombre_completo).strip()
                
                # Asumimos formato "PATERNO MATERNO NOMBRES"
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
                fecha_nac_date = None
                if pd.notna(fecha_nac_val) and isinstance(fecha_nac_val, datetime):
                    fecha_nac_date = fecha_nac_val.date()
                    
                # Crear estudiante en la DB
                estudiante = Estudiante(
                    nombre=nombre.title(),
                    apellido=apellido.title(),
                    curso=curso_clean,
                    colegio_id=colegio_id,
                    fecha_nacimiento=fecha_nac_date
                )
                session.add(estudiante)
                count += 1
                
        await session.commit()
        print(f"¡Éxito! {count} estudiantes importados en la base de datos.")

if __name__ == "__main__":
    asyncio.run(import_excel())
