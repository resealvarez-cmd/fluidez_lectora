"""
Aplicación FastAPI — Entry point
"""
import asyncio
import logging
import uvicorn
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import init_db

settings = get_settings()
logger = logging.getLogger(__name__)

# ─── KEEPALIVE: Mantiene Supabase despierto ────────────────────────────────────

KEEPALIVE_INTERVAL_HOURS = 6  # Ping a la DB cada 6 horas

async def _db_keepalive_loop():
    """
    Tarea de fondo que ejecuta un SELECT 1 cada 6 horas.
    Previene que Supabase pause el proyecto por inactividad.
    (Supabase pausa proyectos gratuitos tras 7 días sin actividad)
    """
    from app.database import engine
    from sqlalchemy import text

    while True:
        await asyncio.sleep(KEEPALIVE_INTERVAL_HOURS * 3600)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info(f"[keepalive] ✅ Ping a Supabase OK — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        except Exception as e:
            logger.warning(f"[keepalive] ⚠️  Ping a Supabase falló: {e}")


# ─── LIFESPAN ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la DB y lanza el keepalive al arrancar"""
    try:
        await init_db()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"⚠️  No se pudo conectar a la DB al arrancar: {e}")
        logger.warning("El servidor arrancará de todas formas. Verifica DATABASE_URL y el estado de Supabase.")

    Path("audio_storage").mkdir(exist_ok=True)

    # Lanzar keepalive en background
    keepalive_task = asyncio.create_task(_db_keepalive_loop())
    logger.info(f"🔄 Keepalive iniciado — ping cada {KEEPALIVE_INTERVAL_HOURS}h")

    yield

    # Cancelar keepalive al apagar el servidor
    keepalive_task.cancel()
    try:
        await keepalive_task
    except asyncio.CancelledError:
        pass


# ─── APP ──────────────────────────────────────────────────────────────────────

from app.routers import estudiantes, textos, lecturas, auth

app = FastAPI(
    title="Fluidez Lectora API",
    description="Sistema de evaluación automática de fluidez lectora para 1° básico",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = [
    "https://fluidezcmp.netlify.app",
    "https://fluidez-lectora.onrender.com",
    "http://localhost:3000",
    "http://localhost:8000",
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

# Audios locales
audio_dir = Path("audio_storage")
audio_dir.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")


# ─── ENDPOINTS DE SISTEMA ─────────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    """Endpoint ultraliviano para servicios de monitoreo externos (UptimeRobot, cron-job.org).
    No consulta la DB — solo confirma que el servidor está vivo."""
    return {"pong": True}


@app.get("/health")
async def health():
    """Estado completo del servidor + conexión a la base de datos."""
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
        "keepalive_interval_hours": KEEPALIVE_INTERVAL_HOURS,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
