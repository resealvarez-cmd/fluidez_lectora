"""
Modelos SQLAlchemy — Base de datos completa para Fluidez Lectora
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text,
    DateTime, Date, ForeignKey, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


def new_uuid():
    return uuid.uuid4()


class Colegio(Base):
    __tablename__ = "colegios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    nombre = Column(String, nullable=False)
    rbd = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    estudiantes = relationship("Estudiante", back_populates="colegio")
    usuarios = relationship("Usuario", back_populates="colegio")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String, unique=True, nullable=False)
    nombre = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    rol = Column(String, default="docente")  # docente | admin
    colegio_id = Column(UUID(as_uuid=True), ForeignKey("colegios.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    colegio = relationship("Colegio", back_populates="usuarios")
    textos = relationship("Texto", back_populates="docente")


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    curso = Column(String, nullable=False)  # '1A', '1B', etc.
    colegio_id = Column(UUID(as_uuid=True), ForeignKey("colegios.id"), nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    colegio = relationship("Colegio", back_populates="estudiantes")
    lecturas = relationship("Lectura", back_populates="estudiante")


class Texto(Base):
    __tablename__ = "textos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    titulo = Column(String, nullable=False)
    contenido = Column(Text, nullable=False)
    nivel = Column(String, default="1basico")
    docente_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    docente = relationship("Usuario", back_populates="textos")
    lecturas = relationship("Lectura", back_populates="texto")

    @property
    def palabras_totales(self) -> int:
        return len(self.contenido.split())


class Lectura(Base):
    __tablename__ = "lecturas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False)
    texto_id = Column(UUID(as_uuid=True), ForeignKey("textos.id"), nullable=False)
    audio_url = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    duracion_segundos = Column(Float, nullable=True)
    transcripcion_raw = Column(Text, nullable=True)
    estado = Column(String, default="pendiente")  # pendiente | procesando | completado | error
    error_mensaje = Column(Text, nullable=True)
    feedback_ia = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    estudiante = relationship("Estudiante", back_populates="lecturas")
    texto = relationship("Texto", back_populates="lecturas")
    metricas = relationship("Metrica", back_populates="lectura", uselist=False)
    errores = relationship("ErrorDetalle", back_populates="lectura")


class Metrica(Base):
    __tablename__ = "metricas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    lectura_id = Column(UUID(as_uuid=True), ForeignKey("lecturas.id", ondelete="CASCADE"), unique=True, nullable=False)
    wcpm = Column(Float, nullable=False)
    precision_pct = Column(Float, nullable=False)
    total_palabras_texto = Column(Integer, nullable=False)
    palabras_correctas = Column(Integer, nullable=False)
    omisiones = Column(Integer, default=0)
    sustituciones = Column(Integer, default=0)
    inserciones = Column(Integer, default=0)
    repeticiones = Column(Integer, default=0)
    vacilaciones = Column(Integer, default=0)
    pausas_largas = Column(Integer, default=0)
    nivel_fluidez = Column(String, nullable=True)  # bajo | en_desarrollo | logrado | avanzado
    
    # Nuevos campos para el contrato de datos (Análisis de textos breves)
    wcpm_proyectado = Column(Boolean, default=False)
    es_texto_breve = Column(Boolean, default=False)
    conteo_palabras = Column(String, nullable=True) # Ej: "13/15"
    nivel_ace = Column(String, nullable=True)      # Ej: "Logro 2"
    created_at = Column(DateTime, default=datetime.utcnow)

    lectura = relationship("Lectura", back_populates="metricas")


class ErrorDetalle(Base):
    __tablename__ = "errores_detalle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    lectura_id = Column(UUID(as_uuid=True), ForeignKey("lecturas.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String, nullable=False)  # omision | sustitucion | insercion | repeticion
    posicion_en_texto = Column(Integer, nullable=True)
    palabra_esperada = Column(String, nullable=True)
    palabra_leida = Column(String, nullable=True)
    timestamp_inicio = Column(Float, nullable=True)
    timestamp_fin = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lectura = relationship("Lectura", back_populates="errores")
