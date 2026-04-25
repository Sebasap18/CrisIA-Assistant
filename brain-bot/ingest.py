# ingest.py
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import os

def procesar_pdf_cliente(ruta_pdf: str, client_id: str):
    print(f"📚 1. Leyendo el archivo {ruta_pdf}...")
    
    # 1. Leer el PDF
    loader = PyPDFLoader(ruta_pdf)
    documentos = loader.load()
    
    print("✂️ 2. Partiendo el documento en párrafos pequeños...")
    
    # 2. Partir el texto en "Chunks" (pedacitos de 500 letras para que Ollama no se sature)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, 
        chunk_overlap=50 # Un pequeño traslape para no cortar ideas por la mitad
    )
    chunks = text_splitter.split_documents(documentos)
    
    # 3. Etiquetar cada párrafo para saber a qué cliente pertenece
    for chunk in chunks:
        chunk.metadata["client_id"] = client_id

    print("🧠 3. Generando vectores matemáticos con Ollama y guardando en ChromaDB...")
    
    # 4. Usar el modelo de Ollama que descargamos para convertir texto a números
    # Asegúrate de que Ollama esté corriendo en otra terminal antes de ejecutar esto
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # 5. Guardar todo en una carpeta local llamada "chroma_db"
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db" # Aquí vivirá tu base de datos NoSQL
    )
    
    print(f"✅ ¡Éxito! El conocimiento del cliente '{client_id}' ha sido inyectado en la base de datos.")

if __name__ == "__main__":
    # Verificamos que el archivo exista antes de procesarlo
    archivo_pdf = "PropuestaComercial.pdf"
    
    if os.path.exists(archivo_pdf):
        # Aquí asociamos este PDF al client_id que tenemos en PostgreSQL
        procesar_pdf_cliente(archivo_pdf, "accesspark_001")
    else:
        print(f"❌ Error: No se encontró el archivo '{archivo_pdf}'. Por favor pon un PDF de prueba en la carpeta.")