# main.py
import json
import redis # 👈 IMPORTACIÓN DE REDIS

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

# 👈 INICIALIZACIÓN DE REDIS
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
    session_id: str # 👈 AHORA RECIBIMOS LA SESIÓN
    text: str

# 👈 CAMBIO CRÍTICO: Recibe una lista completa, no un solo mensaje
async def generar_respuesta_ollama(lista_de_mensajes: list, modelo: str) -> str:
    url = "http://localhost:11434/api/chat"
    
    payload = {
        "model": modelo,
        "messages": lista_de_mensajes, # 👈 ENVIAMOS LA MEMORIA COMPLETA A LA IA
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

# --- RUTA PRINCIPAL DEL WIDGET ---
@app.post("/api/chat")
async def chat_endpoint(message: IncomingMessage, db: Session = Depends(get_db)):
    
    # 1. Buscar al cliente en PostgreSQL
    client = db.query(models.Client).filter(models.Client.client_id == message.client_id).first()
    
    if not client or client.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Cliente no autorizado o inactivo.")

    # 👈 INICIALIZAR LA VARIABLE DEL HISTORIAL
    historial_chat = []

    # --- RECUPERACIÓN DE MEMORIA ---
    if client.history_type == 'POSTGRES':
        registros = db.query(models.ChatHistory).filter(
            models.ChatHistory.client_id == message.client_id,
            models.ChatHistory.session_id == message.session_id
        ).order_by(models.ChatHistory.created_at.desc()).limit(6).all()
        
        for reg in reversed(registros):
            historial_chat.append({"role": reg.role, "content": reg.content})
            
    else: # Por defecto usa REDIS
        redis_key = f"chat:{message.client_id}:{message.session_id}"
        data = redis_client.get(redis_key)
        historial_chat = json.loads(data) if data else []

    # 2. MAGIA RAG: Buscar en ChromaDB los datos relevantes
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
        
        resultados = vectorstore.similarity_search(
            query=message.text,
            k=3, 
            filter={"client_id": message.client_id}
        )
        
        contexto_extra = "\n\n".join([doc.page_content for doc in resultados])
        
    except Exception as e:
        print(f"Error leyendo ChromaDB: {e}")
        contexto_extra = "" 
        
    # 3. Inyectar el conocimiento (Solo al mensaje actual)
    prompt_enriquecido = f"""INFORMACIÓN ESTRICTA DEL MANUAL (Úsala para responder si es relevante):
{contexto_extra}

PREGUNTA DEL USUARIO:
{message.text}
"""
    
    # 4. PREPARAR EL PAQUETE (Memoria pasada + Pregunta actual enriquecida)
    mensajes_para_ia = historial_chat + [{"role": "user", "content": prompt_enriquecido}]
    
    # 5. Enviar a Ollama
    respuesta_ia = await generar_respuesta_ollama(
        lista_de_mensajes=mensajes_para_ia, 
        modelo=client.model
    )

    # 6. GUARDAR NUEVA INTERACCIÓN EN LA MEMORIA
    if client.history_type == 'POSTGRES':
        pregunta = models.ChatHistory(
            client_id=message.client_id, 
            session_id=message.session_id, 
            role="user", 
            content=message.text # Guardamos solo la pregunta original, no el bloque RAG
        )
        respuesta = models.ChatHistory(
            client_id=message.client_id, 
            session_id=message.session_id, 
            role="assistant", 
            content=respuesta_ia
        )
        db.add_all([pregunta, respuesta])
        db.commit()
        
    else: # Guardamos en REDIS
        historial_chat.append({"role": "user", "content": message.text})
        historial_chat.append({"role": "assistant", "content": respuesta_ia})
        
        # Mantener solo los últimos 6 mensajes y darles 1 hora de vida
        redis_key = f"chat:{message.client_id}:{message.session_id}"
        redis_client.set(redis_key, json.dumps(historial_chat[-6:]), ex=3600)

    return {"response": respuesta_ia}