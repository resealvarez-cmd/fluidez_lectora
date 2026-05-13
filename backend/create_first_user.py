import asyncio
import os
import sys
from sqlalchemy import select
from dotenv import load_dotenv

# Añadir el path para que encuentre "app"
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.database import AsyncSessionLocal, init_db
from app.models import Usuario
from app.routers.auth import hash_password

async def create_user():
    print("Iniciando creación de usuario en Supabase...")
    
    # Asegurar que las tablas existan
    try:
        await init_db()
        print("Tablas verificadas/creadas con éxito.")
    except Exception as e:
        print(f"Error al conectar o crear tablas: {e}")
        return

    async with AsyncSessionLocal() as session:
        # Datos del usuario (basado en lo que intentó el usuario en la captura)
        email = "director@madrepaulina.cl"
        nombre = "René Álvarez"
        password = "admin123" # Una contraseña temporal segura
        
        # Verificar si ya existe
        stmt = select(Usuario).where(Usuario.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            print(f"El usuario {email} ya existe en la base de datos.")
        else:
            new_user = Usuario(
                email=email,
                nombre=nombre,
                hashed_password=hash_password(password),
                rol="admin"
            )
            session.add(new_user)
            await session.commit()
            print(f"¡Éxito! Usuario {email} creado con la contraseña: {password}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(create_user())
