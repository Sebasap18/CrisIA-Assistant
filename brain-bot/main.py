# main.py
"""
Punto de entrada de la aplicación FastAPI.

Este archivo es deliberadamente mínimo — solo:
  1. Crea la instancia de FastAPI con metadatos.
  2. Configura el middleware CORS.
  3. Registra los routers.

Toda la lógica está encapsulada en app/.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat_router import router as chat_router

app = FastAPI(
    title="OmniMind SaaS — Brain Bot API",
    description=(
        "Backend de IA multicliente. Gestiona sesiones de chat con memoria, "
        "clasificación de intenciones y búsqueda RAG sobre documentos propios."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware CORS ───────────────────────────────────────────────────────────
# En producción, restringe allow_origins a los dominios de los clientes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """
    Endpoint de salud para monitoreo del sistema.
    
    Permite verificar que el servidor FastAPI está en ejecución y respondiendo
    correctamente a las peticiones HTTP.
    
    Returns:
        Un diccionario indicando el estado ('ok') y el nombre del servicio.
    """
    return {"status": "ok", "service": "brain-bot"}