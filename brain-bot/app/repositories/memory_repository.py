# app/repositories/memory_repository.py
"""
Repositorio de historial de chat sobre Redis.
Implementa IMemoryRepository para clientes con history_type = 'REDIS'.

El historial se guarda serializado en JSON y expira automáticamente tras 1 hora.

Principio de Sustitución de Liskov (LSP):
  Puede reemplazar a PostgresHistoryRepository sin que ChatService note la diferencia.
"""
import json

import redis

from app.domain.interfaces import IMemoryRepository
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# TTL del historial en Redis: 1 hora (en segundos)
_REDIS_TTL_SECONDS = 3600


class RedisMemoryRepository:
    """
    Implementa IMemoryRepository almacenando el historial de chat en Redis.
    El cliente Redis se inyecta como dependencia (DIP / testabilidad).
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _build_key(self, client_id: str, session_id: str) -> str:
        """Genera la clave Redis única para la sesión."""
        return f"chat:{client_id}:{session_id}"

    def load_history(self, client_id: str, session_id: str) -> list[dict]:
        """
        Carga el historial desde Redis. Retorna lista vacía si no existe.
        """
        key = self._build_key(client_id, session_id)
        logger.debug("Cargando historial Redis con clave '%s'", key)
        data = self._redis.get(key)
        return json.loads(data) if data else []

    def save_history(
        self,
        client_id: str,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """
        Agrega el par usuario/asistente al historial y lo guarda en Redis.
        Mantiene solo los últimos N turnos para limitar el tamaño.
        """
        key = self._build_key(client_id, session_id)
        historial = self.load_history(client_id, session_id)

        historial.append({"role": "user", "content": user_text})
        historial.append({"role": "assistant", "content": assistant_text})

        # Mantener solo los últimos N mensajes (= N/2 turnos)
        max_messages = settings.HISTORY_MAX_TURNS
        historial = historial[-max_messages:]

        logger.debug(
            "Guardando historial Redis con clave '%s' (%d mensajes)",
            key,
            len(historial),
        )
        self._redis.set(key, json.dumps(historial), ex=_REDIS_TTL_SECONDS)


# --- Fábrica del cliente Redis (singleton) ---
def create_redis_client() -> redis.Redis:
    """
    Crea y retorna el cliente Redis configurado desde settings.
    Se llama una sola vez al iniciar la aplicación.
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )


# Verificación estática de que cumple el protocolo IMemoryRepository
_: IMemoryRepository = RedisMemoryRepository.__new__(RedisMemoryRepository)  # type: ignore[assignment]
