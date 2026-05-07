# app/repositories/history_repository.py
"""
Repositorio de historial de chat sobre PostgreSQL.
Implementa IMemoryRepository para clientes con history_type = 'POSTGRES'.

Principio de Sustitución de Liskov (LSP):
  Puede reemplazar a RedisMemoryRepository sin que ChatService note la diferencia.
"""
from sqlalchemy.orm import Session

from app.domain.interfaces import IMemoryRepository
from app.domain.models import ChatHistory
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PostgresHistoryRepository:
    """
    Implementa IMemoryRepository usando la tabla 'chat_history' en PostgreSQL.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def load_history(self, client_id: str, session_id: str) -> list[dict]:
        """
        Recupera los últimos N mensajes de la sesión ordenados cronológicamente.
        N = settings.HISTORY_MAX_TURNS
        """
        logger.debug(
            "Cargando historial PostgreSQL para client_id='%s', session_id='%s'",
            client_id,
            session_id,
        )
        registros = (
            self._db.query(ChatHistory)
            .filter(
                ChatHistory.client_id == client_id,
                ChatHistory.session_id == session_id,
            )
            .order_by(ChatHistory.instant.desc())
            .limit(settings.HISTORY_MAX_TURNS)
            .all()
        )

        # Invertir para orden cronológico (del más antiguo al más reciente)
        return [
            {"role": reg.role, "content": reg.content}
            for reg in reversed(registros)
        ]

    def save_history(
        self,
        client_id: str,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """
        Persiste el par usuario/asistente como dos registros en la tabla.
        """
        logger.debug(
            "Guardando historial PostgreSQL para client_id='%s', session_id='%s'",
            client_id,
            session_id,
        )
        user_msg = ChatHistory(
            client_id=client_id,
            session_id=session_id,
            role="user",
            content=user_text,
        )
        assistant_msg = ChatHistory(
            client_id=client_id,
            session_id=session_id,
            role="assistant",
            content=assistant_text,
        )
        self._db.add_all([user_msg, assistant_msg])
        self._db.commit()


# Verificación estática de que cumple el protocolo IMemoryRepository
_: IMemoryRepository = PostgresHistoryRepository.__new__(PostgresHistoryRepository)  # type: ignore[assignment]
