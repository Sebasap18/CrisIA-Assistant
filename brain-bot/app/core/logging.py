# app/core/logging.py
"""
Logger centralizado del proyecto.
Reemplaza todos los print() del código original con logs estructurados
que incluyen timestamp, nivel y módulo de origen.
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger configurado con el nombre del módulo que lo solicita.

    Uso:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Mensaje informativo")
        logger.error("Error crítico: %s", error)
    """
    logger = logging.getLogger(name)

    # Evitar duplicar handlers si el logger ya fue configurado
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Handler que escribe en consola (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Formato: [2026-05-01 15:30:00] INFO     app.services.chat_service — Mensaje
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # No propagar al root logger para evitar logs duplicados
    logger.propagate = False

    return logger
