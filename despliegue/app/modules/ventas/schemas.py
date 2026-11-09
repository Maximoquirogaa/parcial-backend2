from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RenglonCreate(BaseModel):
    libro_id: int
    cantidad: int = Field(gt=0, description="La cantidad debe ser mayor a 0")


class VentaCreate(BaseModel):
    cliente_id: int
    renglones: list[RenglonCreate]

    @model_validator(mode="after")
    def validar_reglas_renglones(self):
        # RN-05: Al menos un renglón
        if not self.renglones:
            raise ValueError("Una venta debe tener al menos un renglón.")
        
        # RN-05: Un mismo libro no puede repetirse en varios renglones
        libro_ids = [r.libro_id for r in self.renglones]
        if len(libro_ids) != len(set(libro_ids)):
            raise ValueError("Un mismo libro no puede aparecer en dos renglones de la misma venta.")
        return self


class ClienteEnVentaRead(BaseModel):
    id: int
    nombre: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class RenglonRead(BaseModel):
    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class VentaListRead(BaseModel):
    id: int
    fecha: datetime
    total: Decimal
    cliente_id: int

    model_config = ConfigDict(from_attributes=True)


class VentaDetailRead(BaseModel):
    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteEnVentaRead
    renglones: list[RenglonRead]

    model_config = ConfigDict(from_attributes=True)

