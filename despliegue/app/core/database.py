from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import DATABASE_URL


def init_engine_and_sessionmaker(
    database_url: str = DATABASE_URL,
    echo: bool = True
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Inicializa el motor asincrónico y la fábrica de sesiones.
    echo=True permite visualizar las consultas emitidas en consola para diagnóstico (requisito no funcional).
    expire_on_commit=False asegura que los objetos mantengan sus atributos accesibles tras hacer commit.
    """
    engine = create_async_engine(database_url, echo=echo)
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_maker


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia FastAPI que provee una sesión asincrónica por petición
    a partir de la fábrica creada en el lifespan y almacenada en app.state.
    """
    session_maker: async_sessionmaker[AsyncSession] = request.app.state.fabrica_sesiones
    async with session_maker() as session:
        yield session

