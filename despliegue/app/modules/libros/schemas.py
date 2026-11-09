from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead


# Sub-esquema para asociar autores al crear un libro
class AutorLibroCreate(BaseModel):
    autor_id: int
    rol: Literal["autor", "coautor", "traductor", "ilustrador"]
    orden: int = Field(ge=1, description="El orden de autoría debe ser >= 1")


# DTO de entrada para crear libro
class LibroCreate(BaseModel):
    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0, description="El precio debe ser mayor que cero")
    stock: int = Field(ge=0, default=0, description="El stock no puede ser negativo")
    editorial_id: int
    genero_id: Optional[int] = None
    autores: list[AutorLibroCreate] = []


# DTO de entrada para actualización parcial
class LibroUpdate(BaseModel):
    isbn: Optional[str] = None
    titulo: Optional[str] = None
    precio: Optional[Decimal] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    editorial_id: Optional[int] = None
    genero_id: Optional[int] = None


# DTO de autor dentro del detalle del libro
class AutorEnLibroRead(BaseModel):
    id: int
    nombre: str
    nacionalidad: str
    rol: str
    orden: int


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

