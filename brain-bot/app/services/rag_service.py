# app/services/rag_service.py
"""
Servicio de Recuperación Aumentada de Generación (RAG) usando ChromaDB.
Implementa IRAGService.

Dado un mensaje de usuario y un departamento detectado, busca los fragmentos
de documentos más relevantes para enriquecer el contexto de la respuesta.

Principio de Responsabilidad Única (SRP):
  Solo busca contexto en el vectorstore. No llama al LLM ni gestiona sesiones.
"""
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from app.domain.interfaces import IRAGService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChromaRAGService:
    """
    Implementa IRAGService usando ChromaDB como vectorstore
    y OllamaEmbeddings para generar los vectores de búsqueda.
    """

    def __init__(self) -> None:
        """
        Inicializa el servicio RAG con la configuración de ChromaDB y Ollama.
        """
        self._embed_model = settings.OLLAMA_EMBED_MODEL
        self._chroma_path = settings.CHROMA_PATH
        self._top_k = settings.RAG_TOP_K


    def search(self, query: str, client_id: str, department: str) -> str:
        """
        Busca fragmentos relevantes en ChromaDB aplicando filtros por
        client_id y departamento (cuando aplica).

        Args:
            query:      Texto del mensaje del usuario.
            client_id:  ID del cliente para filtrar documentos.
            department: Categoría detectada ('sales', 'support', etc.)
                        Si es 'general', solo filtra por client_id.

        Returns:
            Texto con los fragmentos más relevantes concatenados.
            Retorna cadena vacía si no hay resultados o hay un error.
        """
        try:
            embeddings = OllamaEmbeddings(model=self._embed_model)
            vectorstore = Chroma(
                persist_directory=self._chroma_path,
                embedding_function=embeddings,
            )

            # Construir el filtro de búsqueda
            filter_conditions: list[dict] = [{"client_id": client_id}]

            if department != "general":
                filter_conditions.append({"deals": department})

            search_filter = (
                {"$and": filter_conditions}
                if len(filter_conditions) > 1
                else filter_conditions[0]
            )

            logger.debug(
                "Búsqueda RAG: client='%s', dept='%s', filtro=%s",
                client_id,
                department,
                search_filter,
            )

            results = vectorstore.similarity_search(
                query=query,
                k=self._top_k,
                filter=search_filter,
            )

            if not results:
                logger.warning("RAG: No se encontraron fragmentos relevantes para query='%s' y filtro=%s", 
                               query, search_filter)
                return ""

            context = "\n\n".join(doc.page_content for doc in results)
            logger.debug("RAG: encontrados %d fragmentos relevantes", len(results))
            return context

        except Exception as exc:
            logger.exception("Error crítico leyendo ChromaDB: %s", exc)
            return ""



# Verificación estática de que cumple el protocolo IRAGService
_: IRAGService = ChromaRAGService()  # type: ignore[assignment]
