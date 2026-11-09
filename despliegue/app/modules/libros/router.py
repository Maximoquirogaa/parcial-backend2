from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetailRead,
    LibroListRead,
    LibroUpdate,
)
from app.modules.libros.service import (
    create_libro,
    get_libro_detail_by_id,
    get_libros_list,
    update_libro,
)

router = APIRouter(prefix="/libros", tags=["Libros"])


@router.post("/", response_model=LibroDetailRead, status_code=status.HTTP_201_CREATED)
async def post_libro(
    payload: LibroCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_libro(session, payload)


@router.get("/", response_model=list[LibroListRead], status_code=status.HTTP_200_OK)
async def list_libros(
    limit: int = Query(20, ge=1, le=100, description="Paginación: cantidad máxima (1-100)"),
    offset: int = Query(0, ge=0, description="Paginación: desplazamiento desde 0"),
    titulo: Optional[str] = Query(None, description="Filtro insensible a mayúsculas por parte del título"),
    genero_id: Optional[int] = Query(None, description="Filtro por ID de género"),
    session: AsyncSession = Depends(get_session)
):
    return await get_libros_list(
        session,
        limit=limit,
        offset=offset,
        titulo=titulo,
        genero_id=genero_id
    )


@router.get("/{id}", response_model=LibroDetailRead, status_code=status.HTTP_200_OK)
async def get_libro(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_libro_detail_by_id(session, id)


@router.patch("/{id}", response_model=LibroDetailRead, status_code=status.HTTP_200_OK)
async def patch_libro(
    id: int,
    payload: LibroUpdate,
    session: AsyncSession = Depends(get_session)
):
    return await update_libro(session, id, payload)

