from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.autores.schemas import (
    AutorCreate,
    AutorRead,
    AutorUpdate,
    LibroDeAutorRead,
)
from app.modules.autores.service import (
    create_autor,
    get_autor_by_id,
    get_libros_de_autor,
    update_autor,
)

router = APIRouter(prefix="/autores", tags=["Autores"])


@router.post("/", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def post_autor(
    payload: AutorCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_autor(session, payload)


@router.get("/{id}", response_model=AutorRead, status_code=status.HTTP_200_OK)
async def get_autor(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_autor_by_id(session, id)


@router.patch("/{id}", response_model=AutorRead, status_code=status.HTTP_200_OK)
async def patch_autor(
    id: int,
    payload: AutorUpdate,
    session: AsyncSession = Depends(get_session)
):
    return await update_autor(session, id, payload)


@router.get("/{id}/libros", response_model=list[LibroDeAutorRead], status_code=status.HTTP_200_OK)
async def get_autor_libros(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_libros_de_autor(session, id)

