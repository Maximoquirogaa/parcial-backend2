from typing import Optional
from pydantic import BaseModel, ConfigDict


class AutorBase(BaseModel):
    nombre: str
    nacionalidad: str

    model_config = ConfigDict(extra="forbid")


class AutorCreate(AutorBase):
    pass


class AutorUpdate(BaseModel):
    nombre: Optional[str] = None
    nacionalidad: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AutorRead(AutorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LibroDeAutorRead(BaseModel):
    id: int
    isbn: str
    titulo: str
    rol: str
    orden: int

    model_config = ConfigDict(from_attributes=True)
