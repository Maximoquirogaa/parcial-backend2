from pydantic import BaseModel


class HealthLiveResponse(BaseModel):
    estado: str


class HealthReadyResponse(BaseModel):
    estado: str
    base_de_datos: str

