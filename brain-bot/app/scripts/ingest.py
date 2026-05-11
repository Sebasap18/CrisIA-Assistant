# app/scripts/ingest.py
"""
Script CLI para ingestar documentos de contexto en ChromaDB.

Principio de Responsabilidad Única (SRP):
  Solo se encarga de la ingesta de documentos. No es parte del servidor.

Uso:
  python -m app.scripts.ingest
  python -m app.scripts.ingest --client-id accesspark_001
  INGEST_CLIENT_ID=mi_cliente python -m app.scripts.ingest

El CLIENT_ID ya no está hardcodeado — se configura via:
  1. Argumento CLI: --client-id
  2. Variable de entorno: INGEST_CLIENT_ID (en .env o sistema)
"""
import argparse
import os
import sys
from pathlib import Path

# Raíz del proyecto: app/scripts/ -> app/ -> brain-bot/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Asegurar que el directorio raíz del proyecto está en el path
# para que las importaciones de 'app.*' funcionen correctamente
sys.path.insert(0, str(_PROJECT_ROOT))

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.domain.models import ContextDocument

logger = get_logger(__name__)

# Configuración del splitter de texto
_CHUNK_SIZE = 2000
_CHUNK_OVERLAP = 200

# Extensiones de archivo soportadas
_SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def _parse_args() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Ingestar documentos de contexto de un cliente en ChromaDB."
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default=settings.INGEST_CLIENT_ID,
        help=(
            f"ID del cliente a procesar. "
            f"Por defecto: '{settings.INGEST_CLIENT_ID}' (de INGEST_CLIENT_ID en .env)"
        ),
    )
    return parser.parse_args()


def _load_document(file_path: str):
    """
    Carga un documento según su extensión.
    Retorna el loader apropiado o None si el formato no es soportado.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return PyPDFLoader(file_path)
    if ext == ".txt":
        return TextLoader(file_path, encoding="utf-8")

    logger.warning("Formato no soportado: '%s'. Extensiones válidas: %s", ext, _SUPPORTED_EXTENSIONS)
    return None


def ingest_for_client(client_id: str) -> None:
    """
    Ejecuta el proceso completo de ingesta para un cliente:
      1. Consulta los documentos registrados en PostgreSQL.
      2. Carga y fragmenta cada archivo.
      3. Inyecta los metadatos (client_id + etiquetas de la BD).
      4. Indexa los fragmentos en ChromaDB.

    Args:
        client_id: Identificador del cliente a procesar.
    """
    logger.info("Iniciando ingesta para cliente: '%s'", client_id)

    db: Session = SessionLocal()
    try:
        # ── 1. Buscar documentos registrados en PostgreSQL ────────────────────
        documentos_db = (
            db.query(ContextDocument)
            .filter(ContextDocument.client_id == client_id)
            .all()
        )

        if not documentos_db:
            logger.error(
                "No se encontraron documentos en la BD para client_id='%s'.", client_id
            )
            return

        logger.info("Encontrados %d documentos en la BD.", len(documentos_db))

        # ── 2. Inicializar herramientas de procesamiento ──────────────────────
        embeddings = OllamaEmbeddings(model=settings.OLLAMA_EMBED_MODEL)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_CHUNK_OVERLAP,
        )
        chunks_finales = []

        # ── 3. Procesar cada documento ────────────────────────────────────────
        for doc in documentos_db:
            # Resolver ruta relativa desde la raíz del proyecto
            file_path = Path(doc.file_path)
            if not file_path.is_absolute():
                file_path = _PROJECT_ROOT / file_path

            if not file_path.exists():
                logger.warning(
                    "Archivo físico no encontrado en disco: '%s'. Saltando.", file_path
                )
                continue

            logger.info("Procesando: '%s'", doc.file_name)
            loader = _load_document(str(file_path))
            if loader is None:
                continue

            raw_docs = loader.load()
            chunks = splitter.split_documents(raw_docs)
            etiquetas = doc.meta_data or {}
            
            # Si el documento no tiene la etiqueta 'deals', asignarla a 'general' por defecto
            if "deals" not in etiquetas:
                etiquetas["deals"] = "general"

            # Inyectar metadatos a cada fragmento
            for chunk in chunks:
                chunk.metadata = {
                    "client_id": client_id,
                    **etiquetas,  # ej. {"deals": "sales"}
                }
            chunks_finales.extend(chunks)
            logger.info("  → %d fragmentos generados.", len(chunks))

        # ── 4. Guardar en ChromaDB ────────────────────────────────────────────
        if not chunks_finales:
            logger.error("No se pudo procesar ningún texto válido. Abortando.")
            return

        logger.info("Indexando %d fragmentos totales en ChromaDB...", len(chunks_finales))
        Chroma.from_documents(
            documents=chunks_finales,
            embedding=embeddings,
            persist_directory=settings.CHROMA_PATH,
        )
        logger.info("✅ Ingesta completada exitosamente para cliente '%s'.", client_id)

    except Exception as exc:
        logger.error("Error crítico durante la ingesta: %s", exc, exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    args = _parse_args()
    ingest_for_client(client_id=args.client_id)
