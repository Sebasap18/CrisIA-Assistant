# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- CONFIGURACIÓN DE LA CONEXIÓN ---
# Reemplaza 'postgres' y 'tu_contraseña' por tus credenciales reales de PostgreSQL
# Formato: postgresql://usuario:contraseña@servidor:puerto/nombre_base_de_datos
SQLALCHEMY_DATABASE_URL = "postgresql://tokio:579378Ap*95121701309@localhost:5432/omnimind_db"

# --- CREACIÓN DEL MOTOR (ENGINE) ---
# El engine es el núcleo que gestiona la comunicación real con PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# --- FÁBRICA DE SESIONES ---
# Cada vez que llega un mensaje al chat, abrimos una sesión temporal con la BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- CLASE BASE PARA MODELOS ORM ---
# Usaremos esto después para mapear nuestras tablas SQL a clases de Python
Base = declarative_base()

# --- FUNCIÓN DE DEPENDENCIA PARA FASTAPI ---
# Esta función es crucial. Se asegura de que cada petición web tenga su propia
# conexión a la BD y, lo más importante, que la cierre al terminar (para no saturar el servidor).
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()