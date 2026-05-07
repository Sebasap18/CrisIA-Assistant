# app/services/memory_service.py
"""
Fábrica del servicio de memoria que selecciona la implementación correcta
de IMemoryRepository según la configuración del cliente.

Principio Abierto/Cerrado (OCP):
  Agregar un nuevo backend (ej. Memcached) solo requiere crear la clase
  e incluirla en el factory — sin modificar ChatService.

Principio de Inversión de Dependencias (DIP):
  ChatService recibe IMemoryRepository, no sabe si es Redis o PostgreSQL.
"""
import redis

from app.domain.interfaces import IMemoryRepository
from app.domain.models import Client
from app.repositories.history_repository import PostgresHistoryRepository
from app.repositories.memory_repository import RedisMemoryRepository, create_redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# Singleton del cliente Redis — se crea una sola vez al importar el módulo
_redis_client: redis.Redis = create_redis_client()


def get_memory_repository(client: Client, db) -> IMemoryRepository:
    """
    Factory que retorna la implementación de IMemoryRepository correcta
    según el campo history_type del cliente.

    Args:
        client: Instancia del modelo Client con la configuración.
        db:     Sesión SQLAlchemy (solo usada si history_type == 'POSTGRES').

    Returns:
        Instancia de PostgresHistoryRepository o RedisMemoryRepository.

    Raises:
        ValueError: Si history_type tiene un valor no soportado.
    """
    history_type = client.history_type.upper()

    if history_type == "POSTGRES":
        logger.debug("Usando memoria PostgreSQL para cliente '%s'", client.client_id)
        return PostgresHistoryRepository(db=db)

    if history_type == "REDIS":
        logger.debug("Usando memoria Redis para cliente '%s'", client.client_id)
        return RedisMemoryRepository(redis_client=_redis_client)

    raise ValueError(
        f"history_type '{client.history_type}' no soportado. "
        "Valores válidos: 'POSTGRES', 'REDIS'."
    )
