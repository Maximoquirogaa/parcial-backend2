from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Genero(SQLModel, table=True):
    __tablename__ = "genero"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(nullable=False, unique=True, index=True)

    # Relación 1 a N con Libro (agregación opcional)
    libros: list["Libro"] = Relationship(back_populates="genero")

