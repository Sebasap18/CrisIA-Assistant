# app/domain/interfaces.py
"""
Interfaces (Protocolos) que definen los contratos de cada servicio.

Principio de Inversión de Dependencias (DIP):
  Los servicios de alto nivel (ChatService) dependen de estas abstracciones,
  NO de implementaciones concretas (redis.Redis, httpx.AsyncClient, etc.).

Principio de Segregación de Interfaces (ISP):
  Cada protocolo es pequeño y específico — ninguna clase está obligada a
  implementar métodos que no necesita.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class IMemoryRepository(Protocol):
    """
    Contrato para cualquier mecanismo de almacenamiento del historial de chat.
    Implementaciones actuales: PostgresHistoryRepository, RedisMemoryRepository.
    """

    def load_history(self, client_id: str, session_id: str) -> list[dict]:
        """
        Retorna los últimos N turnos del historial de la sesión.
        Cada elemento es {"role": "user"|"assistant", "content": "..."}.
        """
        ...

    def save_history(
        self,
        client_id: str,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """
        Persiste el par usuario/asistente de la interacción actual.
        """
        ...


@runtime_checkable
class ILLMService(Protocol):
    """
    Contrato para cualquier proveedor de LLM (Ollama, OpenAI, Anthropic, etc.).
    """

    async def generate(self, messages: list[dict], model: str) -> str:
        """
        Envía una lista de mensajes al modelo y retorna la respuesta en texto.
        `messages` sigue el formato OpenAI: [{"role": "...", "content": "..."}]
        """
        ...


@runtime_checkable
class IRAGService(Protocol):
    """
    Contrato para el sistema de Recuperación Aumentada de Generación (RAG).
    """

    def search(self, query: str, client_id: str, department: str) -> str:
        """
        Busca fragmentos relevantes en el vectorstore para el cliente y
        departamento dados. Retorna el contexto concatenado como texto.
        """
        ...


@runtime_checkable
class IClassifierService(Protocol):
    """
    Contrato para el agente clasificador de intenciones.
    """

    async def classify(
        self, 
        text: str, 
        model: str, 
        prompt_template: str, 
        valid_categories: set[str], 
        fallback_category: str
    ) -> str:
        """
        Clasifica el texto del usuario en una categoría basándose en la configuración dinámica.
        """
        ...
