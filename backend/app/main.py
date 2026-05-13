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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar"""
    await init_db()
    # Crear directorio de audio si no existe
    Path("audio_storage").mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="Fluidez Lectora API",
    description="Sistema de evaluación automática de fluidez lectora para 1° básico",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permitir acceso desde la tablet/frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list if settings.origins_list != ["*"] else [],
    allow_origin_regex=".*" if settings.origins_list == ["*"] else None,
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
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
