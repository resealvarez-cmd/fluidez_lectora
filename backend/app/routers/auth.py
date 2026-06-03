"""
Router: Auth — Login y registro de docentes
"""
from jose import jwt  # Regresamos a python-jose por requerimiento de producción
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, LoginRequest, TokenResponse, UsuarioOut
from app.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire}, 
        settings.SECRET_KEY, 
        algorithm=ALGORITHM
    )


def _to_out(u: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=u.id,
        email=u.email,
        nombre=u.nombre,
        rol=u.rol,
        colegio_id=u.colegio_id,
        created_at=u.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    usuario = Usuario(
        email=data.email,
        nombre=data.nombre,
        hashed_password=hash_password(data.password),
        rol=data.rol,
        colegio_id=data.colegio_id,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    
    return TokenResponse(
        access_token=create_token(usuario.id),
        usuario=_to_out(usuario),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    usuario = result.scalar_one_or_none()
    
    if not usuario or not verify_password(data.password, usuario.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    return TokenResponse(
        access_token=create_token(usuario.id),
        usuario=_to_out(usuario),
    )


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except Exception as e:
        print(f"Error decodificando JWT: {e}")
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    usuario = await db.get(Usuario, user_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.get("/me", response_model=UsuarioOut)
async def me(usuario: Usuario = Depends(get_current_user)):
    return _to_out(usuario)


# ── Admin: gestión de usuarios ────────────────────────────────────────────────

@router.get("/usuarios", response_model=List[UsuarioOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todos los usuarios (solo admin)"""
    from typing import List as _List
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    result = await db.execute(select(Usuario).order_by(Usuario.created_at))
    return [_to_out(u) for u in result.scalars().all()]


class ResetPasswordRequest(BaseModel):
    nueva_password: str


@router.post("/usuarios/{usuario_id}/reset-password")
async def reset_password(
    usuario_id: str,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Resetea la contraseña de un usuario (solo admin)"""
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if len(data.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    usuario.hashed_password = hash_password(data.nueva_password)
    await db.commit()
    return {"status": "ok", "email": usuario.email}


@router.delete("/usuarios/{usuario_id}")
async def eliminar_usuario(
    usuario_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Elimina un usuario (solo admin, no puede eliminarse a sí mismo)"""
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    if str(current_user.id) == usuario_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.delete(usuario)
    await db.commit()
    return {"status": "ok"}
