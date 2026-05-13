"""
Router: Estudiantes — CRUD completo
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Estudiante, Lectura, Metrica, Texto, Usuario
from app.schemas import EstudianteCreate, EstudianteOut, HistorialEntrada
from app.routers.auth import get_current_user
from typing import List

router = APIRouter(prefix="/api/estudiantes", tags=["estudiantes"])


@router.post("/", response_model=EstudianteOut, status_code=status.HTTP_201_CREATED)
async def crear_estudiante(
    data: EstudianteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    estudiante = Estudiante(**data.model_dump())
    if current_user.colegio_id and not estudiante.colegio_id:
        estudiante.colegio_id = current_user.colegio_id
    db.add(estudiante)
    await db.commit()
    await db.refresh(estudiante)
    return estudiante


@router.get("/", response_model=List[EstudianteOut])
async def listar_estudiantes(
    colegio_id: str | None = None,
    curso: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    q = select(Estudiante).order_by(Estudiante.apellido, Estudiante.nombre)
    
    # Restrict to teacher's school if applicable
    if current_user.rol != "admin" and current_user.colegio_id:
        q = q.where(Estudiante.colegio_id == current_user.colegio_id)
    elif colegio_id:
        q = q.where(Estudiante.colegio_id == colegio_id)
        
    if curso:
        q = q.where(Estudiante.curso == curso)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{estudiante_id}", response_model=EstudianteOut)
async def obtener_estudiante(
    estudiante_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    est = await db.get(Estudiante, estudiante_id)
    if not est or (current_user.rol != "admin" and str(est.colegio_id) != str(current_user.colegio_id)):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return est


@router.put("/{estudiante_id}", response_model=EstudianteOut)
async def actualizar_estudiante(
    estudiante_id: str,
    data: EstudianteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    est = await db.get(Estudiante, estudiante_id)
    if not est or (current_user.rol != "admin" and str(est.colegio_id) != str(current_user.colegio_id)):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(est, k, v)
    await db.commit()
    await db.refresh(est)
    return est


@router.delete("/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_estudiante(
    estudiante_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    est = await db.get(Estudiante, estudiante_id)
    if not est or (current_user.rol != "admin" and str(est.colegio_id) != str(current_user.colegio_id)):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    await db.delete(est)
    await db.commit()


@router.get("/{estudiante_id}/historial", response_model=List[HistorialEntrada])
async def historial_estudiante(
    estudiante_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Historial de lecturas de un estudiante con métricas"""
    est = await db.get(Estudiante, estudiante_id)
    if not est or (current_user.rol != "admin" and str(est.colegio_id) != str(current_user.colegio_id)):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    result = await db.execute(
        select(Lectura, Metrica, Texto)
        .join(Metrica, Metrica.lectura_id == Lectura.id, isouter=True)
        .join(Texto, Texto.id == Lectura.texto_id)
        .where(Lectura.estudiante_id == estudiante_id)
        .where(Lectura.estado == "completado")
        .order_by(desc(Lectura.created_at))
    )
    rows = result.all()

    historial = []
    for lectura, metrica, texto in rows:
        if metrica:
            historial.append(HistorialEntrada(
                lectura_id=lectura.id,
                fecha=lectura.created_at,
                texto_titulo=texto.titulo,
                wcpm=metrica.wcpm,
                precision_pct=metrica.precision_pct,
                nivel_fluidez=metrica.nivel_fluidez,
            ))
    return historial
