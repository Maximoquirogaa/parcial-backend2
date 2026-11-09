from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def init_engine_and_sessionmaker(
    database_url: str,
    pool_size: int = 5,
    echo: bool = False
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Inicializa el motor asincrónico con el tamaño de pool configurado
    y la fábrica de sesiones con expire_on_commit=False.
    """
    engine = create_async_engine(
        database_url,
        pool_size=pool_size,
        echo=echo
    )
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
    Garantiza que la sesión se cierre al finalizar la petición.
    """
    session_maker: async_sessionmaker[AsyncSession] = request.app.state.fabrica_sesiones
    async with session_maker() as session:
        yield session
