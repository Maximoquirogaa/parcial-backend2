from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate
from app.modules.libros.models import Libro


async def create_genero(session: AsyncSession, data: GeneroCreate) -> Genero:
    genero = Genero(nombre=data.nombre)
    session.add(genero)
    try:
        await session.commit()
        await session.refresh(genero)
        return genero
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un género con ese nombre."
        )


async def get_generos(session: AsyncSession) -> Sequence[Genero]:
    query = select(Genero).order_by(Genero.id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_genero_by_id(session: AsyncSession, genero_id: int) -> Genero:
    genero = await session.get(Genero, genero_id)
    if not genero:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Género con ID {genero_id} no encontrado."
        )
    return genero


async def get_libros_de_genero(session: AsyncSession, genero_id: int) -> Sequence[Libro]:
    await get_genero_by_id(session, genero_id)
    query = select(Libro).where(Libro.genero_id == genero_id).order_by(Libro.id)
    result = await session.execute(query)
    return result.scalars().all()

