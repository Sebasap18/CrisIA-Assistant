# app/domain/schemas.py
"""
Schemas Pydantic para validación y serialización de requests/responses de la API.
Definen el contrato de la API — separados de los modelos ORM.
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Payload que envía el widget frontend al endpoint POST /api/chat.
    """
    client_id: str = Field(
        ...,
        description="Identificador único del cliente/empresa en la plataforma.",
        examples=["accesspark_001"],
    )
    session_id: str = Field(
        ...,
        description="Identificador de la sesión del usuario final. "
                    "Agrupa los mensajes de una misma conversación.",
        examples=["session_abc123"],
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Mensaje de texto enviado por el usuario final.",
        examples=["¿Cuánto cuesta el dispensador de tickets?"],
    )


class ChatResponse(BaseModel):
    """
    Respuesta que retorna la API al widget frontend.
    """
    response: str = Field(
        ...,
        description="Respuesta generada por el modelo de IA.",
    )


# Alias de compatibilidad — IncomingMessage era el nombre original en schemas.py
IncomingMessage = ChatRequest
