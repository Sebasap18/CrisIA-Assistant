# main.py
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
    text: str

# Función asíncrona para hablar con tu IA Local (Ollama)
async def generar_respuesta_ollama(mensaje_enriquecido: str, modelo: str) -> str:
    url = "http://localhost:11434/api/chat"
    
    payload = {
        "model": modelo,
        "messages": [
            {"role": "user", "content": mensaje_enriquecido}
        ],
        "stream": False, 
        "keep_alive": -1 
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=60.0)
            res.raise_for_status()
            return res.json()["message"]["content"]
            
        except Exception as e:
            # 👨‍💻 1. LO QUE VES TÚ EN LA TERMINAL (Para depurar si falla):
            print(f"🚨 ERROR INTERNO EN OLLAMA: {str(e)}")
            
            # 👤 2. LO QUE VE EL CLIENTE EN EL CHAT (Elegante y seguro):
            return "Lo siento, mis sistemas están desconectados en este momento. Por favor intenta más tarde."

# --- RUTA PRINCIPAL DEL WIDGET ---
@app.post("/api/chat")
async def chat_endpoint(message: IncomingMessage, db: Session = Depends(get_db)):
    
    # 1. Buscar al cliente en PostgreSQL
    client = db.query(models.Client).filter(models.Client.client_id == message.client_id).first()
    
    if not client or client.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Cliente no autorizado o inactivo.")
    
    # 2. MAGIA RAG: Buscar en ChromaDB los datos relevantes
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        # Conectamos a la base de datos local
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
        
        # Buscamos los 3 párrafos que más se parezcan a la pregunta del usuario, 
        # filtrando SOLO por el ID de este cliente para que no se crucen datos.
        resultados = vectorstore.similarity_search(
            query=message.text,
            k=3, 
            filter={"client_id": message.client_id}
        )
        
        # Unimos los pedacitos de texto encontrados en un solo bloque de texto
        contexto_extra = "\n\n".join([doc.page_content for doc in resultados])
        
    except Exception as e:
        print(f"Error leyendo ChromaDB: {e}")
        contexto_extra = "" # Si hay error, seguimos sin contexto
        
    # 3. Inyectar el conocimiento (Sin el System Prompt de Postgres)
    prompt_enriquecido = f"""INFORMACIÓN ESTRICTA DEL MANUAL (Úsala para responder si es relevante):
{contexto_extra}

PREGUNTA DEL USUARIO:
{message.text}
"""
    
    # 4. Enviar a Ollama
    # Asegúrate de que client.model en tu base de datos ahora diga "accesspark_bot" 
    # (o el nombre que le hayas dado al compilar tu Modelfile).
    respuesta_ia = await generar_respuesta_ollama(
        mensaje_enriquecido=prompt_enriquecido, 
        modelo=client.model
    )
    
    # 5. Devolver la respuesta al widget
    return {"response": respuesta_ia}