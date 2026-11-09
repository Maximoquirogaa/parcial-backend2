from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead


# Sub-esquema para asociar autores al crear un libro
class AutorLibroCreate(BaseModel):
    autor_id: int
    rol: Literal["autor", "coautor", "traductor", "ilustrador"]
    orden: int = Field(default=1, ge=1, description="El orden de autoría debe ser >= 1")

    model_config = ConfigDict(extra="forbid")


# DTO de entrada para crear libro
class LibroCreate(BaseModel):
    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0, description="El precio debe ser mayor que cero")
    stock: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("stock", "stock_inicial"),
        description="Stock inicial del libro (>= 0)"
    )
    editorial_id: int
    genero_id: Optional[int] = None
    autores: list[AutorLibroCreate] = []

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# DTO de entrada para actualización parcial (PATCH)
# RN: stock no puede modificarse por PATCH (punto único de stock)
class LibroUpdate(BaseModel):
    isbn: Optional[str] = None
    titulo: Optional[str] = None
    precio: Optional[Decimal] = Field(default=None, gt=0)
    editorial_id: Optional[int] = None
    genero_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


# DTO de solicitud de reposición de stock
class ReponerStockRequest(BaseModel):
    cantidad: int = Field(gt=0, description="Cantidad a reponer (debe ser mayor a cero)")
    motivo: str = Field(default="Reposición", description="Motivo del movimiento de stock")

    model_config = ConfigDict(extra="forbid")


# DTO de lectura de movimiento de stock
class MovimientoStockRead(BaseModel):
    id: int
    libro_id: int
    cantidad: int
    motivo: str
    cuando: datetime
    venta_id: Optional[int] = None
    usuario_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# DTO de autor dentro del detalle del libro
class AutorEnLibroRead(BaseModel):
    id: int
    nombre: str
    nacionalidad: str
    rol: str
    orden: int

    model_config = ConfigDict(from_attributes=True)


# DTO de listado de libros con editorial y género
class LibroListRead(BaseModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: Optional[EditorialRead] = None
    genero: Optional[GeneroRead] = None

    model_config = ConfigDict(from_attributes=True)


# DTO de detalle completo de libro (con editorial, género y autores)
class LibroDetailRead(BaseModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: Optional[EditorialRead] = None
    genero: Optional[GeneroRead] = None
    autores: list[AutorEnLibroRead] = []

    model_config = ConfigDict(from_attributes=True)
