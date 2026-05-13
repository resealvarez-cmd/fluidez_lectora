"""
Schemas Pydantic para validación y serialización
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


# ─── COLEGIO ────────────────────────────────────────────────────────────────
class ColegioCreate(BaseModel):
    nombre: str
    rbd: Optional[str] = None


class ColegioOut(ColegioCreate):
    id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── USUARIO ─────────────────────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str
    password: str
    rol: str = "docente"
    colegio_id: Optional[str] = None


class UsuarioOut(BaseModel):
    id: UUID
    email: str
    nombre: str
    rol: str
    colegio_id: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ─── ESTUDIANTE ──────────────────────────────────────────────────────────────
class EstudianteCreate(BaseModel):
    nombre: str
    apellido: str
    curso: str
    colegio_id: Optional[UUID] = None
    fecha_nacimiento: Optional[date] = None


class EstudianteOut(EstudianteCreate):
    id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── TEXTO ───────────────────────────────────────────────────────────────────
class TextoCreate(BaseModel):
    titulo: str
    contenido: str
    nivel: str = "1basico"
    docente_id: Optional[UUID] = None


class TextoOut(BaseModel):
    id: UUID
    titulo: str
    contenido: str
    nivel: str
    palabras_totales: int
    docente_id: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── LECTURA ─────────────────────────────────────────────────────────────────
class LecturaCreate(BaseModel):
    estudiante_id: UUID
    texto_id: UUID


class LecturaOut(BaseModel):
    id: UUID
    estudiante_id: UUID
    texto_id: UUID
    audio_url: Optional[str]
    duracion_segundos: Optional[float]
    transcripcion_raw: Optional[str]
    estado: str
    error_mensaje: Optional[str]
    feedback_ia: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── MÉTRICAS ────────────────────────────────────────────────────────────────
class ErrorDetalleOut(BaseModel):
    id: UUID
    tipo: str
    posicion_en_texto: Optional[int]
    palabra_esperada: Optional[str]
    palabra_leida: Optional[str]
    timestamp_inicio: Optional[float]
    timestamp_fin: Optional[float]
    model_config = {"from_attributes": True}


class MetricaOut(BaseModel):
    id: UUID
    lectura_id: UUID
    wcpm: float
    precision_pct: float
    total_palabras_texto: int
    palabras_correctas: int
    omisiones: int
    sustituciones: int
    inserciones: int
    repeticiones: int
    vacilaciones: int
    pausas_largas: int
    nivel_fluidez: Optional[str]
    # Campos del nuevo contrato
    wcpm_proyectado: bool = False
    es_texto_breve: bool = False
    conteo_palabras: Optional[str] = None
    nivel_ace: Optional[str] = None
    precision: Optional[float] = None # Alias para precision_pct en el JSON
    created_at: datetime
    model_config = {"from_attributes": True}


class ResultadoLecturaOut(BaseModel):
    lectura: LecturaOut
    metricas: Optional[MetricaOut]
    errores: List[ErrorDetalleOut] = []
    model_config = {"from_attributes": True}


# ─── HISTORIAL ───────────────────────────────────────────────────────────────
class HistorialEntrada(BaseModel):
    lectura_id: UUID
    fecha: datetime
    texto_titulo: str
    wcpm: float
    precision_pct: float
    nivel_fluidez: Optional[str]
    model_config = {"from_attributes": True}
