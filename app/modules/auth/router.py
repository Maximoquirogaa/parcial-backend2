from fastapi import APIRouter, Depends, Request, Response, status

from app.core.dependencies import get_roles_del_token, get_usuario_actual
from app.modules.auth.schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    RegistroRequest,
    UsuarioActualRead,
)
from app.modules.auth.service import (
    cambiar_password,
    login,
    logout,
    obtener_yo,
    registrar_usuario,
)
from app.modules.usuarios.models import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def post_registro(
    payload: RegistroRequest,
    request: Request,
):
    """Registro de nuevo cliente. Crea usuario, rol CLIENTE y ficha de cliente en un UoW."""
    return await registrar_usuario(request, payload)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def post_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
):
    """
    Login. Emite cookie HttpOnly 'access_token'.
    El cuerpo NO contiene el token.
    """
    return await login(request, response, payload)


@router.post("/logout", response_model=MensajeResponse, status_code=status.HTTP_200_OK)
async def post_logout(response: Response):
    """Cierra sesión borrando la cookie 'access_token'."""
    return await logout(response)


@router.get("/yo", response_model=UsuarioActualRead, status_code=status.HTTP_200_OK)
async def get_yo(
    request: Request,
    usuario: Usuario = Depends(get_usuario_actual),
    roles_token: list[str] = Depends(get_roles_del_token),
):
    """Devuelve el usuario autenticado con sus roles vigentes en DB y roles del token."""
    return await obtener_yo(request, usuario, roles_token)


@router.post("/cambiar-password", response_model=MensajeResponse, status_code=status.HTTP_200_OK)
async def post_cambiar_password(
    payload: CambiarPasswordRequest,
    request: Request,
    usuario: Usuario = Depends(get_usuario_actual),
):
    """Cambia la contraseña del usuario autenticado."""
    return await cambiar_password(
        request,
        usuario,
        payload.password_actual,
        payload.password_nueva,
    )
