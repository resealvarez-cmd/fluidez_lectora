"""
Router: Textos — CRUD para textos de lectura
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Texto, Usuario
from app.schemas import TextoCreate, TextoOut
from app.routers.auth import get_current_user
from typing import List

router = APIRouter(prefix="/api/textos", tags=["textos"])


@router.post("/", response_model=TextoOut, status_code=status.HTTP_201_CREATED)
async def crear_texto(
    data: TextoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    texto = Texto(**data.model_dump())
    texto.docente_id = current_user.id
    db.add(texto)
    await db.commit()
    await db.refresh(texto)
    return _to_out(texto)


@router.get("/", response_model=List[TextoOut])
async def listar_textos(
    nivel: str | None = None,
    docente_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    from sqlalchemy import or_
    q = select(Texto).order_by(Texto.created_at.desc())
    
    if current_user.rol != "admin":
        q = q.where(or_(Texto.docente_id == current_user.id, Texto.docente_id.is_(None)))
    elif docente_id:
        q = q.where(Texto.docente_id == docente_id)
        
    if nivel:
        q = q.where(Texto.nivel == nivel)
        
    result = await db.execute(q)
    return [_to_out(t) for t in result.scalars().all()]


@router.get("/{texto_id}", response_model=TextoOut)
async def obtener_texto(
    texto_id: str,
    db: AsyncSession = Depends(get_db)
):
    t = await db.get(Texto, texto_id)
    if not t:
        raise HTTPException(status_code=404, detail="Texto no encontrado")
    return _to_out(t)


@router.delete("/{texto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_texto(
    texto_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    t = await db.get(Texto, texto_id)
    if not t or (current_user.rol != "admin" and str(t.docente_id) != str(current_user.id)):
        raise HTTPException(status_code=404, detail="Texto no encontrado o acceso denegado")
    await db.delete(t)
    await db.commit()


def _to_out(t: Texto) -> TextoOut:
    return TextoOut(
        id=t.id,
        titulo=t.titulo,
        contenido=t.contenido,
        nivel=t.nivel,
        palabras_totales=t.palabras_totales,
        docente_id=t.docente_id,
        created_at=t.created_at,
    )
