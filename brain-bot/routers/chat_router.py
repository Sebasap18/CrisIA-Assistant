from fastapi import APIRouter, Depends, HTTPException
from schemas import IncomingMessage
from services.ollama_services import generar_respuesta_ollama
# Supongamos que tienes una función que consulta PostgreSQL
from services.client_service import obtener_config_cliente 

router = APIRouter()

@router.post("/api/chat")
async def chat_endpoint(message: IncomingMessage):
    # 1. Validar el cliente en PostgreSQL
    # Va a la BD y trae el system_prompt, webhooks y el modelo de IA asignado
    cliente_config = obtener_config_cliente(message.client_id)
    
    if not cliente_config or not cliente_config["activo"]:
        raise HTTPException(status_code=403, detail="Cliente no válido o inactivo.")
    
    # 2. Enviar a Ollama con la configuración inyectada
    # Aquí la IA procesa el mensaje actuando como el cliente específico
    respuesta_ia = await generar_respuesta_ollama(message.text, cliente_config)
    
    # 3. (Opcional) Lógica de Webhooks
    # Si la IA determina en su respuesta que debe ejecutar una acción (ej. devuelve JSON),
    # aquí leerías la tabla 'webhooks' y harías un requests.post() hacia el CRM del cliente.
    
    # 4. Devolver la respuesta al widget de Lit (Frontend)
    return {
        "response": respuesta_ia
    }