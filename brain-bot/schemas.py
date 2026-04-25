
from pydantic import BaseModel

class IncomingMessage(BaseModel):
    client_id: str
    session_id: str  # Para recordar el hilo de la conversación
    text: str