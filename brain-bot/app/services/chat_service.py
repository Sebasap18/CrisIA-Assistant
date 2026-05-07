# app/services/chat_service.py
"""
Orquestador central del flujo de chat.

Principio de Responsabilidad Única (SRP):
  Este servicio solo coordina la secuencia del flujo de chat.
  No accede directamente a la BD, Redis, Ollama ni ChromaDB.

Principio de Inversión de Dependencias (DIP):
  Depende de interfaces (ILLMService, IRAGService, IClassifierService,
  IMemoryRepository), nunca de implementaciones concretas.
  Las dependencias se inyectan en el constructor.
"""
from sqlalchemy.orm import Session

from app.domain.interfaces import (
    IClassifierService,
    ILLMService,
    IMemoryRepository,
    IRAGService,
)
from app.domain.models import Client
from app.domain.schemas import ChatRequest, ChatResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """
    Orquesta el flujo completo de una interacción de chat:
      1. Cargar historial de la sesión.
      2. Clasificar la intención del usuario.
      3. Recuperar contexto RAG relevante.
      4. Construir el paquete de mensajes enriquecido.
      5. Generar la respuesta con el LLM.
      6. Persistir la nueva interacción en la memoria.
    """

    def __init__(
        self,
        llm: ILLMService,
        rag: IRAGService,
        classifier: IClassifierService,
        memory: IMemoryRepository,
    ) -> None:
        """
        Inicializa el orquestador de chat con sus dependencias.

        Args:
            llm: Servicio generador de texto (LLM).
            rag: Servicio de recuperación de contexto (RAG).
            classifier: Servicio de clasificación de intenciones.
            memory: Repositorio para la gestión del historial de chat.
        """
        self._llm = llm
        self._rag = rag
        self._classifier = classifier
        self._memory = memory


    async def handle_message(
        self,
        request: ChatRequest,
        client: Client,
    ) -> ChatResponse:
        """
        Procesa un mensaje entrante y retorna la respuesta del asistente.

        Args:
            request: Payload del request (client_id, session_id, text).
            client:  Registro del cliente en BD con su configuración.

        Returns:
            ChatResponse con el texto generado por el LLM.
        """
        try:
            logger.info("Iniciando procesamiento de mensaje para client_id='%s', session_id='%s'", 
                        request.client_id, request.session_id)

            # ── 1. Cargar historial de la sesión ─────────────────────────────────
            historial = self._memory.load_history(
                client_id=request.client_id,
                session_id=request.session_id,
            )
            logger.debug("Historial cargado: %d mensajes previos", len(historial))

            # ── 2. Clasificar la intención del usuario ────────────────────────────
            department = await self._classifier.classify(
                text=request.text,
                model=client.model,
            )
            logger.info(
                "Intención '%s' detectada para client='%s'",
                department,
                request.client_id,
            )

            # ── 3. Buscar contexto relevante en ChromaDB (RAG) ────────────────────
            rag_context = self._rag.search(
                query=request.text,
                client_id=request.client_id,
                department=department,
            )
            logger.debug("Contexto RAG recuperado (%d chars)", len(rag_context))

            # ── 4. Construir el paquete de mensajes enriquecido ───────────────────
            # El system prompt personalizado del cliente va primero
            system_message = {"role": "system", "content": client.system_prompt}

            # Enriquecer el texto del usuario con el contexto RAG
            user_content = (
                f"INFORMACIÓN DEL MANUAL (úsala si es relevante):\n{rag_context}\n\n"
                f"PREGUNTA DEL USUARIO:\n{request.text}"
                if rag_context
                else request.text
            )
            user_message = {"role": "user", "content": user_content}

            messages_for_llm = [system_message] + historial + [user_message]
            logger.debug("Paquete de mensajes construido con %d elementos totales", len(messages_for_llm))

            # ── 5. Generar la respuesta con el LLM ───────────────────────────────
            response_text = await self._llm.generate(
                messages=messages_for_llm,
                model=client.model,
            )
            logger.info(
                "Respuesta generada con éxito para client='%s' (%d chars)",
                request.client_id,
                len(response_text),
            )

            # ── 6. Persistir la nueva interacción ─────────────────────────────────
            self._memory.save_history(
                client_id=request.client_id,
                session_id=request.session_id,
                user_text=request.text,
                assistant_text=response_text,
            )
            logger.debug("Interacción persistida en memoria correctamente")

            return ChatResponse(response=response_text)

        except Exception as exc:
            logger.exception("Error inesperado procesando mensaje para client_id='%s': %s", 
                             request.client_id, exc)
            # Retornar una respuesta de error amigable en lugar de dejar que FastAPI lance un 500 sin control
            return ChatResponse(
                response="Lo siento, ha ocurrido un error interno al procesar tu solicitud. Por favor, intenta de nuevo más tarde."
            )

