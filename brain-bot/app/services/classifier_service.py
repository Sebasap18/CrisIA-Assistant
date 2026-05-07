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

# Categorías válidas que el clasificador puede retornar
VALID_CATEGORIES = frozenset({"sales", "support", "human_talent", "general"})

_CLASSIFIER_PROMPT = """\
Actúa como un clasificador automático.
Lee el siguiente mensaje del usuario y clasifícalo en UNA SOLA de las siguientes categorías:
- "sales" (Si pregunta por precios, productos, ventas, dispensadores, cajeros, catálogo, si quiere comprar).
- "support" (Si pregunta por fallas, mantenimiento, garantías, SLA, ayuda técnica).
- "human_talent" (Si pregunta por empleo, vacantes, si tiene quejas, reclamos, PQR).
- "general" (Si es un saludo, una despedida, o no encaja en las anteriores).

Responde ÚNICAMENTE con la palabra exacta de la categoría, en minúsculas y sin puntos.

Mensaje del usuario: "{message}"
"""


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


    async def classify(self, text: str, model: str) -> str:
        """
        Clasifica el texto del usuario y retorna la categoría de departamento.

        Returns:
            Una de: 'sales', 'support', 'human_talent', 'general'
            En caso de error retorna 'general' (fallback seguro).
        """
        url = f"{self._base_url}/api/chat"
        prompt = _CLASSIFIER_PROMPT.format(message=text)

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
                for category in ("sales", "support", "human_talent"):
                    if category in raw:
                        logger.info("Intención detectada: '%s'", category)
                        return category

                logger.info("Intención detectada: 'general' (fallback). Respuesta cruda: '%s'", raw)
                return "general"


            except Exception as exc:
                logger.error("Error crítico en clasificador (modelo='%s'): %s", model, exc, exc_info=True)
                return "general"



# Verificación estática de que cumple el protocolo IClassifierService
_: IClassifierService = OllamaClassifierService()  # type: ignore[assignment]
