# app/services/classifier_service.py
"""
Servicio clasificador de intenciones del usuario.
Implementa IClassifierService.

Usa un LLM con temperatura 0 para categorizar el mensaje del usuario
en uno de los departamentos: sales, support, human_talent, general.

Principio de Responsabilidad Única (SRP):
  Solo clasifica intenciones. No genera respuestas ni accede a la BD.
"""
import httpx

from app.domain.interfaces import IClassifierService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)



class OllamaClassifierService:
    """
    Implementa IClassifierService usando Ollama con temperatura 0
    para obtener clasificaciones deterministas.
    """

    def __init__(self) -> None:
        """
        Inicializa el servicio clasificador con la configuración de Ollama.
        """
        self._base_url = settings.OLLAMA_BASE_URL
        self._timeout = settings.OLLAMA_CLASSIFIER_TIMEOUT


    async def classify(
        self, 
        text: str, 
        model: str, 
        prompt_template: str, 
        valid_categories: set[str], 
        fallback_category: str
    ) -> str:
        """
        Clasifica el texto del usuario y retorna la categoría de departamento
        basándose en la configuración dinámica del cliente.
        """
        url = f"{self._base_url}/api/chat"
        # Reemplazar {message} con el texto real si la plantilla lo requiere
        prompt = prompt_template.format(message=text) if "{message}" in prompt_template else f"{prompt_template}\n\nMensaje: {text}"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": -1,
            "options": {
                "temperature": 0.0,
                "num_predict": 10,
            },
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=self._timeout)
                response.raise_for_status()
                raw = response.json()["message"]["content"].strip().lower()

                # Buscar si alguna categoría válida está contenida en la respuesta
                for category in valid_categories:
                    if category in raw:
                        logger.info("Intención detectada: '%s'", category)
                        return category

                logger.warning("Clasificación ambigua. Respuesta cruda: '%s'. Usando fallback '%s'.", raw, fallback_category)
                return fallback_category

            except Exception as exc:
                logger.error("Error crítico en clasificador (modelo='%s'): %s", model, exc, exc_info=True)
                return fallback_category



# Verificación estática de que cumple el protocolo IClassifierService
_: IClassifierService = OllamaClassifierService()  # type: ignore[assignment]
