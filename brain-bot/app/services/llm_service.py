# app/services/llm_service.py
"""
Servicio de generación de texto usando Ollama como proveedor LLM.
Implementa ILLMService.

Principio Abierto/Cerrado (OCP):
  Para agregar otro proveedor (OpenAI, Anthropic), basta con crear
  una nueva clase que implemente ILLMService — sin tocar este archivo.
"""
import httpx

from app.domain.interfaces import ILLMService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaLLMService:
    """
    Implementa ILLMService conectándose al servidor local de Ollama.
    La URL base y el timeout se leen desde settings (no hardcodeados).
    """

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL
        self._timeout = settings.OLLAMA_TIMEOUT

    async def generate(self, messages: list[dict], model: str) -> str:
        """
        Envía el historial de mensajes a Ollama y retorna la respuesta en texto.

        Args:
            messages: Lista en formato OpenAI [{"role": "...", "content": "..."}]
            model:    Nombre del modelo Ollama a usar (ej. "llama3")

        Returns:
            Texto de respuesta del modelo. En caso de error, retorna mensaje amigable.
        """
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": -1,
        }

        logger.debug("Enviando %d mensajes al modelo '%s'", len(messages), model)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=self._timeout)
                response.raise_for_status()
                content = response.json()["message"]["content"]
                logger.debug("Respuesta recibida de Ollama (%d chars)", len(content))
                return content

            except httpx.TimeoutException:
                logger.error("Timeout al conectar con Ollama (modelo='%s')", model)
                return (
                    "Lo siento, el tiempo de respuesta de la IA superó el límite. "
                    "Por favor intenta de nuevo."
                )
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Error HTTP de Ollama: status=%d, detail=%s",
                    exc.response.status_code,
                    exc.response.text,
                )
                return "Lo siento, el servicio de IA retornó un error. Intenta más tarde."
            except Exception as exc:
                logger.error("Error inesperado en OllamaLLMService: %s", exc)
                return (
                    "Lo siento, mis sistemas están desconectados en este momento. "
                    "Por favor intenta más tarde."
                )


# Verificación estática de que cumple el protocolo ILLMService
_: ILLMService = OllamaLLMService()  # type: ignore[assignment]
