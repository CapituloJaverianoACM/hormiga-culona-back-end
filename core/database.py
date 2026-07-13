import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("La variable DATABASE_URL no está configurada en el entorno.")


engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # Mantiene 5 conexiones vivas en memoria
    max_overflow=10,      # Permite hasta 10 conexiones extra en picos de tráfico
    pool_timeout=30,      # Tiempo máximo de espera si el pool está lleno
    pool_recycle=1800     # Recicla las conexiones cada 30 min para evitar desconexiones de Supabase
)