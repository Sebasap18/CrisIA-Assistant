import httpx  # Librería para hacer peticiones HTTP asíncronas muy rápidas

async def generar_respuesta_ollama(mensaje_usuario: str, config_cliente: dict) -> str:
    """
    Se conecta al servidor local de Ollama inyectando la configuración de la BD.
    """
    ollama_url = "http://localhost:11434/api/chat"
    
    # 1. Armamos los mensajes con la personalidad extraída de PostgreSQL
    mensajes = [
        {
            "role": "system", 
            "content": config_cliente["system_prompt"] # Ej: "Eres asesor de AccessPark..."
        },
        {
            "role": "user", 
            "content": mensaje_usuario
        }
    ]

    payload = {
        "model": config_cliente["modelo_ollama"], # Ej: "llama3"
        "messages": mensajes,
        "stream": False # Para recibir la respuesta completa, no palabra por palabra
    }

    # 2. Hacemos la petición a nuestra IA local
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(ollama_url, json=payload, timeout=60.0)
            response.raise_for_status()
            datos = response.json()
            return datos["message"]["content"]
            
        except Exception as e:
            return f"Lo siento, mis sistemas están en mantenimiento. (Error IA: {str(e)})"