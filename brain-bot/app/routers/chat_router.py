# app/routers/chat_router.py
"""
Router HTTP del endpoint de chat.

Principio de Responsabilidad Única (SRP):
  Este módulo SOLO maneja la capa HTTP:
    - Recibir y validar el request.
    - Autorizar al cliente.
    - Delegar al ChatService.
    - Retornar la respuesta HTTP.

  Toda la lógica de negocio vive en ChatService.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas import ChatRequest, ChatResponse
from app.repositories.client_repository import ClientRepository
from app.services.chat_service import ChatService
from app.services.classifier_service import OllamaClassifierService
from app.services.llm_service import OllamaLLMService
from app.services.memory_service import get_memory_repository
from app.services.rag_service import ChromaRAGService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


def _build_chat_service(client, db: Session) -> ChatService:
    """
    Construye el ChatService inyectando todas sus dependencias.
    La memoria se selecciona dinámicamente según la configuración del cliente.
    """
    return ChatService(
        llm=OllamaLLMService(),
        rag=ChromaRAGService(),
        classifier=OllamaClassifierService(),
        memory=get_memory_repository(client=client, db=db),
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Procesa un mensaje del usuario y retorna la respuesta del asistente.",
    responses={
        403: {"description": "Cliente no autorizado o inactivo."},
        500: {"description": "Error interno del servidor."},
    },
)
async def chat_endpoint(
    message: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Endpoint principal del widget de chat.

    Flujo:
      1. Valida que el cliente exista y esté activo en PostgreSQL.
      2. Construye el ChatService con las dependencias del cliente.
      3. Delega el procesamiento completo al ChatService.
      4. Retorna la respuesta generada por la IA.
    """
    # ── Autorización ─────────────────────────────────────────────────────────
    client_repo = ClientRepository(db=db)
    client = client_repo.get_active_client(client_id=message.client_id)

    if client is None:
        logger.warning(
            "Acceso denegado para client_id='%s'", message.client_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cliente no autorizado o inactivo.",
        )

    # ── Delegación al servicio ────────────────────────────────────────────────
    logger.info(
        "Request de chat: client='%s', session='%s'",
        message.client_id,
        message.session_id,
    )

    chat_service = _build_chat_service(client=client, db=db)
    return await chat_service.handle_message(request=message, client=client)
