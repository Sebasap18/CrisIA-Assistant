# app/core/config.py
"""
Configuración centralizada del proyecto usando pydantic-settings.
Todas las variables sensibles se leen desde el archivo .env,
nunca se hardcodean en el código fuente.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del proyecto: dos niveles arriba de este archivo (app/core/ -> app/ -> brain-bot/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Define y valida todas las variables de configuración del proyecto.
    Pydantic-settings las lee automáticamente desde el archivo .env
    o desde las variables de entorno del sistema operativo.
    """

    # --- Base de Datos PostgreSQL ---
    DATABASE_URL: str

    # --- Redis (caché de historial de chat) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # --- Ollama (servidor LLM local) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: float = 60.0
    OLLAMA_CLASSIFIER_TIMEOUT: float = 10.0
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # --- ChromaDB (vectorstore RAG) ---
    CHROMA_PATH: str = "./chroma_db"
    RAG_TOP_K: int = 3

    # --- Historial de chat (cantidad de turnos a recuperar) ---
    HISTORY_MAX_TURNS: int = 6

    # --- Ingestión de documentos ---
    INGEST_CLIENT_ID: str = "accesspark_001"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instancia singleton — importar desde cualquier módulo con:
#   from app.core.config import settings
settings = Settings()
