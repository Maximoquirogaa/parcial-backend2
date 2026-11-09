from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """
    Unit of Work base como gestor de contexto asincrónico.
    - commit() al salir sin excepción.
    - rollback() al salir con excepción y relanza el error.
    - NO cierra la sesión, la cual pertenece al ciclo de vida de la petición FastAPI.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
