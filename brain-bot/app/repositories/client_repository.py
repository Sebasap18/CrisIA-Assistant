# app/repositories/client_repository.py
"""
Repositorio de acceso a datos para la entidad Client.

Principio de Responsabilidad Única (SRP):
  Este módulo solo se encarga de las operaciones CRUD sobre la tabla 'client'.
  No contiene lógica de negocio.
"""
from sqlalchemy.orm import Session

from app.domain.models import Client
from app.core.logging import get_logger

logger = get_logger(__name__)


class ClientRepository:
    """
    Provee métodos de acceso a datos para la entidad Client.
    Recibe la sesión de BD como dependencia (DIP).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_client_id(self, client_id: str) -> Client | None:
        """
        Busca un cliente por su client_id de negocio.
        Retorna None si no existe.
        """
        logger.debug("Buscando cliente con client_id='%s'", client_id)
        return (
            self._db.query(Client)
            .filter(Client.client_id == client_id)
            .first()
        )

    def get_active_client(self, client_id: str) -> Client | None:
        """
        Retorna el cliente solo si existe y está activo (status = 'ACTIVE').
        Retorna None si no existe o está inactivo.
        """
        client = self.get_by_client_id(client_id)
        if client is None:
            logger.warning("Cliente no encontrado: '%s'", client_id)
            return None
        if not client.is_active():
            logger.warning(
                "Cliente '%s' encontrado pero inactivo (status='%s')",
                client_id,
                client.status,
            )
            return None
        return client
