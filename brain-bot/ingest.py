# ingest_db_manual.py
import os
from sqlalchemy.orm import Session

# Importamos tu configuración de base de datos y modelos
from database import SessionLocal
import models
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

def ingesta_desde_postgres():
    CLIENT_ID = "accesspark_001"
    
    print(f"🔍 Conectando a PostgreSQL para buscar documentos del cliente: {CLIENT_ID}...")
    db: Session = SessionLocal()
    
    try:
        # 1. Buscamos en la base de datos los documentos de este cliente
        documentos_db = db.query(models.ContextDocument).filter(models.ContextDocument.client_id == CLIENT_ID).all()
        
        if not documentos_db:
            print("❌ No se encontraron documentos en la base de datos para este cliente.")
            return

        print(f"Encontrados {len(documentos_db)} documentos en la BD. Iniciando procesamiento...\n")

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        documentos_finales = []

        # 2. Iteramos sobre lo que nos devolvió PostgreSQL
        for doc in documentos_db:
            ruta_archivo = doc.file_path
            
            # SQLAlchemy convierte automáticamente la columna JSONB a un diccionario de Python
            etiquetas_db = doc.meta_data or {} 

            if not os.path.exists(ruta_archivo):
                print(f"⚠️ ERROR: El archivo físico '{ruta_archivo}' no existe en el disco duro. Saltando...")
                continue

            print(f"📄 Procesando: {doc.file_name} -> Ruta: {ruta_archivo} -> Etiquetas: {etiquetas_db}")
            
            # Cargamos y cortamos el texto
            if ruta_archivo.lower().endswith('.pdf'):
                loader = PyPDFLoader(ruta_archivo)
            elif ruta_archivo.lower().endswith('.txt'):
                loader = TextLoader(ruta_archivo, encoding="utf-8")
            else:
                print(f"⚠️ Formato no soportado para {ruta_archivo}. Solo .pdf o .txt")
                continue
                
            docs_brutos = loader.load()
            chunks = text_splitter.split_documents(docs_brutos)

            # 3. Inyectamos la metadata (Client ID + Etiquetas de la DB)
            for chunk in chunks:
                chunk.metadata = {
                    "client_id": CLIENT_ID,
                    **etiquetas_db  # Esto desempaqueta el JSON {"departamento": "comercial"}
                }
                documentos_finales.append(chunk)

        if not documentos_finales:
            print("\n❌ No se pudo procesar ningún texto válido.")
            return

        # 4. Guardar en ChromaDB
        print(f"\n🧠 Guardando {len(documentos_finales)} fragmentos en ChromaDB...")
        Chroma.from_documents(
            documents=documentos_finales,
            embedding=embeddings,
            persist_directory="./chroma_db"
        )
        print("✅ ¡Base de datos vectorial actualizada con éxito desde PostgreSQL!")
        
    except Exception as e:
        print(f"🚨 Ocurrió un error: {e}")
    finally:
        db.close() # Siempre cerramos la conexión a la BD

if __name__ == "__main__":
    ingesta_desde_postgres()