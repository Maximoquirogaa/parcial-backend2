from pathlib import Path
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "Librería API"
    VERSION: str = "1.0.0"

    # Base de datos: sin valores por defecto para credenciales requeridas
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Parámetros de pool y conexión
    POOL_SIZE: int = 5
    SQL_ECHO: bool = False

    # Seguridad / JWT / Cookies
    SECRET_KEY: str
    TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = False

    # Bcrypt
    BCRYPT_COST: int = 12
    BCRYPT_MAX_CONCURRENT: int = 4

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


def get_settings() -> Settings:
    return Settings()
