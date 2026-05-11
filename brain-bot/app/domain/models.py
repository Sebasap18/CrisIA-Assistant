# app/domain/models.py
"""
Modelos ORM de SQLAlchemy que mapean las tablas del esquema 'core' en PostgreSQL.
Solo definen la estructura de datos — sin lógica de negocio.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class Client(Base):
    """
    Representa un cliente/empresa registrada en la plataforma OmniMind.
    Cada cliente tiene su propio modelo de IA, prompt de sistema e historial.
    """
    __tablename__ = "client"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    model = Column(String(50), default="llama3", nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)
    history_type = Column(String(20), nullable=False)  # 'POSTGRES' | 'REDIS'
    
    # --- Configuración dinámica del clasificador de intenciones ---
    classifier_prompt = Column(Text, nullable=True)
    classifier_categories = Column(JSONB, nullable=True)
    classifier_fallback = Column(String(50), nullable=True)
    
    instant = Column(DateTime, default=datetime.utcnow, nullable=False)

    def is_active(self) -> bool:
        """Verifica si el cliente está activo."""
        return self.status == "ACTIVE"


class ChatHistory(Base):
    """
    Registro de mensajes de una conversación en PostgreSQL.
    Usado cuando el cliente tiene history_type = 'POSTGRES'.
    """
    __tablename__ = "chat_history"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    role = Column(String(20), nullable=False)    # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    instant = Column(DateTime, default=datetime.utcnow, nullable=False)


class ContextDocument(Base):
    """
    Referencia a un documento de contexto registrado para un cliente.
    El archivo físico se indexa en ChromaDB para búsqueda RAG.
    """
    __tablename__ = "context_document"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(50), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    meta_data = Column(JSONB)   # Etiquetas: {"deals": "sales"} para filtrar en RAG
    instant = Column(DateTime, default=datetime.utcnow, nullable=False)
