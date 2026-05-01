# main.py
import json
import redis 

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# Importamos nuestra configuración local
from database import get_db
import models

app = FastAPI(title="Omnimind SaaS Backend")

# INICIALIZACIÓN DE REDIS
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Habilitar CORS para que el widget web pueda conectarse
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estructura de datos que esperamos recibir del Frontend
class IncomingMessage(BaseModel):
    client_id: str
    session_id: str 
    text: str

# Función para generar respuesta con el historial completo
async def generar_respuesta_ollama(lista_de_mensajes: list, modelo: str) -> str:
    url = "http://localhost:11434/api/chat"
    
    payload = {
        "model": modelo,
        "messages": lista_de_mensajes, 
        "stream": False, 
        "keep_alive": -1 
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=60.0)
            res.raise_for_status()
            return res.json()["message"]["content"]
            
        except Exception as e:
            print(f"🚨 ERROR INTERNO EN OLLAMA: {str(e)}")
            return "Lo siento, mis sistemas están desconectados en este momento. Por favor intenta más tarde."

# Agente Clasificador
async def clasificar_intencion(mensaje_usuario: str, modelo: str) -> str:
    url = "http://localhost:11434/api/chat"
    
    prompt_clasificador = f"""Actúa como un clasificador automático. 
Lee el siguiente mensaje del usuario y clasifícalo en UNA SOLA de las siguientes categorías:
- "sales" (Si pregunta por precios, productos, ventas, dispensadores, cajeros, catálogo,si quiere comprar).
- "support" (Si pregunta por fallas, mantenimiento, garantías, SLA, ayuda técnica).
- "human_talent" (Si pregunta por empleo, vacantes, si tiene quejas, reclamos, PQR).
- "general" (Si es un saludo, una despedida, o no encaja en las anteriores).

Responde ÚNICAMENTE con la palabra exacta de la categoría, en minúsculas y sin puntos.

Mensaje del usuario: "{mensaje_usuario}"
"""

    payload = {
        "model": modelo,
        "messages": [
            {"role": "user", "content": prompt_clasificador}
        ],
        "stream": False,
        "keep_alive": -1,
        "options": {
            "temperature": 0.0, 
            "num_predict": 10   
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=10.0)
            res.raise_for_status()
            respuesta = res.json()["message"]["content"].strip().lower()
            
            for categoria in ["sales", "support", "human_talent"]:
                if categoria in respuesta:
                    return categoria
            return "general"
            
        except Exception as e:
            print(f"⚠️ Error en clasificador: {e}")
            return "general" 

# --- RUTA PRINCIPAL DEL WIDGET ---
@app.post("/api/chat")
async def chat_endpoint(message: IncomingMessage, db: Session = Depends(get_db)):
    
    # 1. Buscar al cliente en PostgreSQL
    client = db.query(models.Client).filter(models.Client.client_id == message.client_id).first()
    
    if not client or client.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Cliente no autorizado o inactivo.")

    historial_chat = []

    # --- RECUPERACIÓN DE MEMORIA ---
    if client.history_type == 'POSTGRES':
        registros = db.query(models.ChatHistory).filter(
            models.ChatHistory.client_id == message.client_id,
            models.ChatHistory.session_id == message.session_id
        ).order_by(models.ChatHistory.created_at.desc()).limit(6).all()
        
        for reg in reversed(registros):
            historial_chat.append({"role": reg.role, "content": reg.content})
            
    else: 
        redis_key = f"chat:{message.client_id}:{message.session_id}"
        data = redis_client.get(redis_key)
        historial_chat = json.loads(data) if data else []

    # 🤖 1. EL AGENTE CLASIFICADOR DECIDE EL CONTEXTO
    departamento_detectado = await clasificar_intencion(message.text, client.model)
    print(f"🎯 Intención detectada por la IA: {departamento_detectado}")

    # 2. MAGIA RAG: Buscar en ChromaDB aplicando el filtro inteligente
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
        
        condiciones_filtro = [{"client_id": message.client_id}]
        
        if departamento_detectado != "general":
            # Usamos 'deals' porque fue la llave que vimos en tu error anterior
            condiciones_filtro.append({"deals": departamento_detectado}) 

        if len(condiciones_filtro) > 1:
            filtro_busqueda = {"$and": condiciones_filtro}
        else:
            filtro_busqueda = condiciones_filtro[0] 

        resultados = vectorstore.similarity_search(
            query=message.text,
            k=3, 
            filter=filtro_busqueda 
        )
        
        contexto_extra = "\n\n".join([doc.page_content for doc in resultados])
        
    except Exception as e:
        print(f"🚨 Error leyendo ChromaDB: {e}")
        contexto_extra = ""
        
    # 3. Inyectar el conocimiento
    prompt_enriquecido = f"""INFORMACIÓN ESTRICTA DEL MANUAL (Úsala para responder si es relevante):
{contexto_extra}

PREGUNTA DEL USUARIO:
{message.text}
"""
    
    # 👁️ RAYOS X 1: Imprimimos qué contexto le encontró ChromaDB
    print(f"\n--- CONTEXTO ENCONTRADO ---\n{contexto_extra}\n---------------------------")

    # 4. PREPARAR EL PAQUETE
    mensajes_para_ia = historial_chat + [{"role": "user", "content": prompt_enriquecido}]
    
    # 5. Enviar a Ollama
    respuesta_ia = await generar_respuesta_ollama(
        lista_de_mensajes=mensajes_para_ia, 
        modelo=client.model
    )

    # 👁️ RAYOS X 2: Imprimimos la respuesta cruda de Ollama
    print(f"\n🤖 Respuesta cruda de la IA:\n{respuesta_ia}\n---------------------------")

    # 6. GUARDAR NUEVA INTERACCIÓN EN LA MEMORIA
    if client.history_type == 'POSTGRES':
        pregunta = models.ChatHistory(
            client_id=message.client_id, 
            session_id=message.session_id, 
            role="user", 
            content=message.text 
        )
        respuesta = models.ChatHistory(
            client_id=message.client_id, 
            session_id=message.session_id, 
            role="assistant", 
            content=respuesta_ia
        )
        db.add_all([pregunta, respuesta])
        db.commit()
        
    else: 
        historial_chat.append({"role": "user", "content": message.text})
        historial_chat.append({"role": "assistant", "content": respuesta_ia})
        
        redis_key = f"chat:{message.client_id}:{message.session_id}"
        redis_client.set(redis_key, json.dumps(historial_chat[-6:]), ex=3600)

    return {"response": respuesta_ia}