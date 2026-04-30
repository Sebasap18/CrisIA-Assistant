from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid
from datetime import datetime
from database import Base

class Client(Base):
    __tablename__ = "client"
    __table_args__ = {"schema": "core"}  # <--- CRUCIAL: Le dice a Python que busque en el esquema "core"
    
    # Mapeo exacto de las columnas de tu SQL
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(50), unique=True, nullable=False)
    company_name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    model = Column(String(50), default="llama3")
    status = Column(String(20), default="ACTIVE")
    instant = Column(DateTime, default=datetime.utcnow)
    history_type = Column(String(20))

class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = {"schema": "core"}  # <--- CRUCIAL: Le dice a Python que busque en el esquema "core"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(50), nullable=False)
    session_id = Column(String(50), nullable=False)  # Para recordar el hilo de la conversación
    role = Column(String(20), nullable=False)  # "user" o "assistant"
    content = Column(Text, nullable=False)
    instant = Column(DateTime, default=datetime.utcnow)  # Para saber dónde se guarda esta interacción


class ContextDocument(Base):
    __tablename__ = "context_document"
    __table_args__ = {"schema": "core"}  # <--- CRUCIAL: Le dice a Python que busque en el esquema "core"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    meta_data = Column(JSONB)  # Para guardar cualquier información adicional sobre el documento
    instant = Column(DateTime, default=datetime.utcnow)