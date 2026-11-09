from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class GeneroCreate(BaseModel):
    nombre: str


class GeneroRead(BaseModel):
    id: int
    nombre: str

    model_config = ConfigDict(from_attributes=True)


class LibroDeGeneroRead(BaseModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int

    model_config = ConfigDict(from_attributes=True)

