from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class EditorialBase(BaseModel):
    nombre: str
    pais: str


class EditorialCreate(EditorialBase):
    pass


class EditorialUpdate(BaseModel):
    nombre: Optional[str] = None
    pais: Optional[str] = None


class EditorialRead(EditorialBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LibroDeEditorialRead(BaseModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    genero_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

