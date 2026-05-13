"""
Router: Lecturas — Upload de audio + pipeline de evaluación
============================================================
Flujo:
  POST /api/lecturas/           → crea registro de lectura (pendiente)
  POST /api/lecturas/{id}/audio → sube audio, lanza evaluación async
  GET  /api/lecturas/{id}       → estado + resultado
  GET  /api/lecturas/{id}/resultado → resultado completo con errores
"""
import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Lectura, Texto, Metrica, ErrorDetalle
from app.schemas import LecturaCreate, LecturaOut, ResultadoLecturaOut, MetricaOut, ErrorDetalleOut
from app.services.evaluacion import evaluar_lectura
from app.routers.auth import get_current_user
from app.models import Usuario, Estudiante
from typing import List

router = APIRouter(prefix="/api/lecturas", tags=["lecturas"])

# Directorio para almacenar audios en desarrollo
AUDIO_DIR = Path("audio_storage")
AUDIO_DIR.mkdir(exist_ok=True)


@router.post("/", response_model=LecturaOut, status_code=status.HTTP_201_CREATED)
async def crear_lectura(data: LecturaCreate, db: AsyncSession = Depends(get_db)):
    """Crea una sesión de lectura (sin audio todavía)"""
    lectura = Lectura(
        estudiante_id=data.estudiante_id,
        texto_id=data.texto_id,
        estado="pendiente",
    )
    db.add(lectura)
    await db.commit()
    await db.refresh(lectura)
    return lectura


@router.get("/")
async def listar_lecturas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todas las lecturas con sus métricas y estudiante asociado"""
    from sqlalchemy.orm import selectinload
    stmt = select(Lectura).options(
        selectinload(Lectura.estudiante),
        selectinload(Lectura.texto)
    )
    
    if current_user.rol != "admin" and current_user.colegio_id:
        stmt = stmt.join(Estudiante).where(Estudiante.colegio_id == current_user.colegio_id)
        
    stmt = stmt.order_by(Lectura.created_at.desc())
    
    res = await db.execute(stmt)
    lecturas = res.scalars().all()
    
    result = []
    for l in lecturas:
        # Obtener métricas para cada una (podría optimizarse con JOIN)
        m_stmt = select(Metrica).where(Metrica.lectura_id == str(l.id))
        m_res = await db.execute(m_stmt)
        metrica = m_res.scalar_one_or_none()
        
        result.append({
            "id": str(l.id),
            "estudiante": f"{l.estudiante.nombre} {l.estudiante.apellido}" if l.estudiante else "Desconocido",
            "curso": l.estudiante.curso if l.estudiante else "-",
            "texto_id": str(l.texto_id), # Añadido para filtros
            "texto_titulo": l.texto.titulo if l.texto else "Texto borrado",
            "estado": l.estado,
            "fecha": l.created_at.isoformat(),
            "metricas": {
                "wcpm": metrica.wcpm,
                "precision_pct": metrica.precision_pct,
                "precision": metrica.precision_pct, # Alias
                "nivel_fluidez": metrica.nivel_fluidez,
                "wcpm_proyectado": metrica.wcpm_proyectado,
                "es_texto_breve": metrica.es_texto_breve,
                "conteo_palabras": metrica.conteo_palabras,
                "nivel_ace": metrica.nivel_ace
            } if metrica else None,
            "feedback_ia": l.feedback_ia,
            "created_at": l.created_at.isoformat() # Asegurar para el frontend
        })
    return result

@router.post("/{lectura_id}/audio", response_model=LecturaOut)
async def subir_audio(
    lectura_id: str,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe el audio grabado, lo guarda localmente y lanza
    la evaluación de forma asíncrona (no bloquea al cliente).
    """
    lectura = await db.get(Lectura, lectura_id)
    if not lectura:
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    if lectura.estado not in ("pendiente", "error"):
        raise HTTPException(status_code=400, detail=f"Estado inválido: {lectura.estado}")

    # Guardar audio localmente o en Supabase
    ext = Path(audio.filename).suffix if audio.filename else ".webm"
    audio_filename = f"{lectura_id}{ext}"
    audio_path = AUDIO_DIR / audio_filename
    
    audio_bytes = await audio.read()
    
    # Supabase Storage si está configurado
    from app.config import get_settings
    settings = get_settings()
    
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client, Client
            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            
            # Subir a Supabase Storage
            res = supabase.storage.from_(settings.AUDIO_STORAGE_BUCKET).upload(
                path=audio_filename,
                file=audio_bytes,
                file_options={"content-type": "audio/webm"}
            )
            # Generar URL pública
            public_url = supabase.storage.from_(settings.AUDIO_STORAGE_BUCKET).get_public_url(audio_filename)
            lectura.audio_url = public_url
            lectura.audio_path = f"supabase://{settings.AUDIO_STORAGE_BUCKET}/{audio_filename}"
        except Exception as e:
            print(f"Error subiendo a Supabase Storage: {e}")
            # Fallback a local
            async with aiofiles.open(audio_path, "wb") as f:
                await f.write(audio_bytes)
            lectura.audio_url = f"/audio/{audio_filename}"
            lectura.audio_path = str(audio_path)
    else:
        # Modo local (dev)
        async with aiofiles.open(audio_path, "wb") as f:
            await f.write(audio_bytes)
        lectura.audio_url = f"/audio/{audio_filename}"
        lectura.audio_path = str(audio_path)

    # Actualizar estado a 'procesando'
    lectura.estado = "procesando"
    await db.commit()
    await db.refresh(lectura)

    # Lanzar evaluación en background (no bloquea la respuesta)
    background_tasks.add_task(
        _procesar_audio_background,
        lectura_id=lectura_id,
        audio_bytes=audio_bytes,
        audio_filename=audio_filename,
    )

    return lectura


async def _procesar_audio_background(
    lectura_id: str, audio_bytes: bytes, audio_filename: str
):
    """
    Tarea de fondo: evalúa el audio y guarda resultados en la DB.
    Se ejecuta después de que la respuesta HTTP ya fue enviada al cliente.
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Cargar lectura y texto
            lectura = await db.get(Lectura, lectura_id)
            if not lectura:
                return

            texto = await db.get(Texto, lectura.texto_id)
            if not texto:
                lectura.estado = "error"
                lectura.error_mensaje = "Texto no encontrado"
                await db.commit()
                return

            # Evaluar
            resultado = await evaluar_lectura(
                audio_bytes=audio_bytes,
                texto_esperado=texto.contenido,
                audio_filename=audio_filename,
            )

            # 3. Manejar métricas (Update or Create)
            import uuid
            uid = uuid.UUID(lectura_id)
            
            from sqlalchemy import select
            stmt_m = select(Metrica).where(Metrica.lectura_id == uid)
            res_m = await db.execute(stmt_m)
            metrica = res_m.scalar_one_or_none()
            
            if not metrica:
                metrica = Metrica(lectura_id=uid)
                db.add(metrica)
            
            metrica.wcpm = resultado.wcpm
            metrica.precision_pct = resultado.precision_pct
            metrica.total_palabras_texto = resultado.total_palabras_texto
            metrica.palabras_correctas = resultado.palabras_correctas
            metrica.omisiones = resultado.omisiones
            metrica.sustituciones = resultado.sustituciones
            metrica.inserciones = resultado.inserciones
            metrica.repeticiones = resultado.repeticiones
            metrica.vacilaciones = resultado.vacilaciones
            metrica.pausas_largas = resultado.pausas_largas
            metrica.nivel_fluidez = resultado.nivel_fluidez
            metrica.wcpm_proyectado = resultado.wcpm_proyectado
            metrica.es_texto_breve = resultado.es_texto_breve
            metrica.conteo_palabras = resultado.conteo_palabras
            metrica.nivel_ace = resultado.nivel_ace

            # 4. Limpiar errores detallados viejos y crear nuevos
            from sqlalchemy import delete
            await db.execute(delete(ErrorDetalle).where(ErrorDetalle.lectura_id == lectura_id))
            
            for op in resultado.operaciones:
                if op.tipo != "MATCH":
                    error = ErrorDetalle(
                        lectura_id=lectura_id,
                        tipo=op.tipo.lower(),
                        posicion_en_texto=op.posicion_texto,
                        palabra_esperada=op.palabra_esperada,
                        palabra_leida=op.palabra_leida,
                        timestamp_inicio=op.token.start if op.token else None,
                        timestamp_fin=op.token.end if op.token else None,
                    )
                    db.add(error)

            # 5. Actualizar estado y feedback de la lectura
            lectura.duracion_segundos = resultado.duracion_segundos
            lectura.transcripcion_raw = resultado.transcripcion_raw
            lectura.feedback_ia = resultado.feedback_ia
            lectura.estado = "completado"

            await db.commit()

        except Exception as e:
            # Marcar como error para que el frontend pueda mostrarlo
            async with AsyncSessionLocal() as db_err:
                lectura_err = await db_err.get(Lectura, lectura_id)
                if lectura_err:
                    lectura_err.estado = "error"
                    lectura_err.error_mensaje = str(e)
                    await db_err.commit()
            raise


@router.get("/{lectura_id}", response_model=LecturaOut)
async def obtener_lectura(lectura_id: str, db: AsyncSession = Depends(get_db)):
    """Polling de estado de la lectura"""
    lectura = await db.get(Lectura, lectura_id)
    if not lectura:
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    return lectura


@router.get("/{lectura_id}/resultado", response_model=ResultadoLecturaOut)
async def obtener_resultado(lectura_id: str, db: AsyncSession = Depends(get_db)):
    """Resultado completo: métricas + errores detallados"""
    lectura = await db.get(Lectura, lectura_id)
    if not lectura:
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    
    # Permitimos ver resultados si hay métricas, incluso si el estado es 'error' o 'procesando'
    # (El frontend manejará la visualización parcial)

    # Cargar métricas
    result_m = await db.execute(
        select(Metrica).where(Metrica.lectura_id == lectura_id)
    )
    metrica = result_m.scalar_one_or_none()

    # Cargar errores
    result_e = await db.execute(
        select(ErrorDetalle).where(ErrorDetalle.lectura_id == lectura_id)
    )
    errores = result_e.scalars().all()

    return ResultadoLecturaOut(
        lectura=lectura,
        metricas=metrica,
        errores=errores,
    )


@router.delete("/{lectura_id}")
async def eliminar_lectura(lectura_id: str, db: AsyncSession = Depends(get_db)):
    """Elimina una sesión de lectura"""
    lectura = await db.get(Lectura, lectura_id)
    if not lectura:
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    await db.delete(lectura)
    await db.commit()
    return {"status": "ok"}


@router.post("/{lectura_id}/reanalizar")
async def reanalizar_lectura(
    lectura_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Vuelve a lanzar el proceso de IA sobre un audio ya existente"""
    lectura = await db.get(Lectura, lectura_id)
    if not lectura or not lectura.audio_path:
        raise HTTPException(status_code=404, detail="Lectura o audio no encontrado")
    
    # Leer el audio desde el path (local o supabase)
    audio_bytes = None
    if lectura.audio_path.startswith("supabase://"):
        # Descargar de Supabase
        from app.config import get_settings
        settings = get_settings()
        from supabase import create_client, Client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        filename = lectura.audio_path.split("/")[-1]
        res = supabase.storage.from_(settings.AUDIO_STORAGE_BUCKET).download(filename)
        audio_bytes = res
    else:
        # Local
        async with aiofiles.open(lectura.audio_path, "rb") as f:
            audio_bytes = await f.read()

    lectura.estado = "procesando"
    await db.commit()

    background_tasks.add_task(
        _procesar_audio_background,
        lectura_id=lectura_id,
        audio_bytes=audio_bytes,
        audio_filename=Path(lectura.audio_path).name,
    )
    return {"status": "re-proceso iniciado"}
