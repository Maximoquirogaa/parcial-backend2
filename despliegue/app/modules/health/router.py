from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.health.schemas import HealthLiveResponse, HealthReadyResponse
from app.modules.health.service import check_database_readiness

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=HealthLiveResponse, status_code=status.HTTP_200_OK)
async def health_live():
    """
    Verifica que el proceso del servidor esté vivo sin tocar la base de datos.
    Cumple con el contrato esperado: {"estado": "vivo"}.
    """
    return {"estado": "vivo"}


@router.get("/ready", response_model=HealthReadyResponse, status_code=status.HTTP_200_OK)
async def health_ready(session: AsyncSession = Depends(get_session)):
    """
    Verifica la conectividad con la base de datos ejecutando SELECT 1.
    """
    try:
        is_ready = await check_database_readiness(session)
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"estado": "error", "detalle": "Respuesta inesperada de la base de datos"}
            )
        return {"estado": "listo", "base_de_datos": "conectada"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"estado": "error", "detalle": str(exc)}
        )

