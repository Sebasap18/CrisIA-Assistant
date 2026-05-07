# app/core/database.py
"""
Configuración del motor de base de datos SQLAlchemy.
La URL de conexión se obtiene de settings (variable de entorno DATABASE_URL),
nunca se hardcodea en el código.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

# --- Motor de conexión a PostgreSQL ---
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # Detecta conexiones muertas antes de usarlas
    pool_size=10,         # Conexiones simultáneas máximas en el pool
    max_overflow=20,      # Conexiones extra permitidas bajo alta carga
)

# --- Fábrica de sesiones ---
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# --- Clase base para todos los modelos ORM ---
Base = declarative_base()


# --- Dependencia FastAPI: provee y cierra la sesión por cada request ---
def get_db() -> Generator[Session, None, None]:
    """
    Generador de sesiones de base de datos para inyección de dependencias en FastAPI.
    Garantiza que la sesión siempre se cierre al finalizar la petición,
    incluso si ocurre una excepción.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
