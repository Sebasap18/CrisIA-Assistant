from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
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