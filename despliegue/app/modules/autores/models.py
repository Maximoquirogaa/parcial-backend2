from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.libros.models import LibroAutor


class Autor(SQLModel, table=True):
    __tablename__ = "autor"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(nullable=False)
    nacionalidad: str = Field(nullable=False)

    # Relación con la entidad de asociación LibroAutor
    libro_autores: list["LibroAutor"] = Relationship(back_populates="autor")

