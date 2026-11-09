import math
from typing import Generic, Sequence, TypeVar
from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field

T = TypeVar("T")


class ParametrosPagina(BaseModel):
    page: int = Field(default=1, ge=1, description="Número de página (base 1)")
    size: int = Field(default=20, ge=1, le=100, description="Cantidad de elementos por página (1-100)")


def get_parametros_pagina(
    page: int = Query(default=1, ge=1, description="Número de página"),
    size: int = Query(default=20, ge=1, le=100, description="Tamaño de página")
) -> ParametrosPagina:
    return ParametrosPagina(page=page, size=size)


class Pagina(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int


def paginar(items: Sequence[T], total: int, page: int, size: int) -> Pagina[T]:
    """
    Calcula la paginación y valida que la página solicitada no supere la última página calculada.
    Si total == 0, pages = 1 y page = 1 es válido.
    """
    if total == 0:
        pages = 1
    else:
        pages = math.ceil(total / size)

    if page > pages:
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail=f"La página {page} supera la última página disponible ({pages})."
        )

    return Pagina[T](
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )
