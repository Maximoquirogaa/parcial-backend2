import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta raíz del backend (donde reside el archivo .env)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar variables de entorno desde el archivo .env
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Librería API"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/libreria_db"
    )

settings = Settings()
DATABASE_URL = settings.DATABASE_URL

