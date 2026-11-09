from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.generos.schemas import GeneroCreate, GeneroRead, LibroDeGeneroRead
from app.modules.generos.service import (
    create_genero,
    get_generos,
    get_libros_de_genero,
)

router = APIRouter(prefix="/generos", tags=["Géneros"])


@router.post("/", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def post_genero(
    payload: GeneroCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_genero(session, payload)


@router.get("/", response_model=list[GeneroRead], status_code=status.HTTP_200_OK)
async def list_generos(session: AsyncSession = Depends(get_session)):
    return await get_generos(session)


@router.get("/{id}/libros", response_model=list[LibroDeGeneroRead], status_code=status.HTTP_200_OK)
async def get_genero_libros(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_libros_de_genero(session, id)

