from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
    LibroDeEditorialRead,
)
from app.modules.editoriales.service import (
    create_editorial,
    get_editorial_by_id,
    get_editoriales,
    get_libros_de_editorial,
    update_editorial,
)

router = APIRouter(prefix="/editoriales", tags=["Editoriales"])


@router.post("/", response_model=EditorialRead, status_code=status.HTTP_201_CREATED)
async def post_editorial(
    payload: EditorialCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_editorial(session, payload)


@router.get("/", response_model=list[EditorialRead], status_code=status.HTTP_200_OK)
async def list_editoriales(
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de resultados (1-100)"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial"),
    session: AsyncSession = Depends(get_session)
):
    return await get_editoriales(session, limit=limit, offset=offset)


@router.get("/{id}", response_model=EditorialRead, status_code=status.HTTP_200_OK)
async def get_editorial(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_editorial_by_id(session, id)


@router.patch("/{id}", response_model=EditorialRead, status_code=status.HTTP_200_OK)
async def patch_editorial(
    id: int,
    payload: EditorialUpdate,
    session: AsyncSession = Depends(get_session)
):
    return await update_editorial(session, id, payload)


@router.get("/{id}/libros", response_model=list[LibroDeEditorialRead], status_code=status.HTTP_200_OK)
async def get_editorial_libros(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_libros_de_editorial(session, id)

