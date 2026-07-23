"""
Aplicación FastAPI — Entry point
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import init_db
from app.routers import estudiantes, textos, lecturas, auth

settings = get_settings()


import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar (tolerante a fallos)"""
    try:
        await init_db()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"⚠️  No se pudo conectar a la base de datos al arrancar: {e}")
        logger.warning("El servidor arrancará de todas formas. Verifica DATABASE_URL y el estado de Supabase.")
    # Crear directorio de audio si no existe
    Path("audio_storage").mkdir(exist_ok=True)
    yield



app = FastAPI(
    title="Fluidez Lectora API",
    description="Sistema de evaluación automática de fluidez lectora para 1° básico",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Configuración unificada para producción
origins = [
    "https://fluidezcmp.netlify.app",
    "https://fluidez-lectora.onrender.com",
    "http://localhost:3000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(estudiantes.router)
app.include_router(textos.router)
app.include_router(lecturas.router)

# Servir audios guardados localmente
audio_dir = Path("audio_storage")
audio_dir.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")


@app.get("/health")
async def health():
    from app.database import engine
    from sqlalchemy import text
    db_status = "unknown"
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)[:120]}"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "database": db_status,
    }



if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
