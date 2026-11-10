"""
Tests TDD — Bloque 5: Flujo de autenticación (5.4, 5.5, 5.6, 5.7) y Casos C-02, C-03, C-05.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario
from tests.conftest import cookie_de, crear_usuario_bd, email_tdd


# ============================================================================
# 5.5: Registro atómico de cliente (C-02)
# ============================================================================

@pytest.mark.asyncio
async def test_registro_exitoso_crea_tres_filas_en_un_uow(cliente_principal: AsyncClient):
    """
    C-02: Registro válido (201) crea usuario, rol CLIENTE y cliente en un único UoW.
    """
    fabrica = app.state.fabrica_sesiones
    email = email_tdd("registro_ok")
    payload = {
        "email": email,
        "password": "Password123!",
        "nombre": "Juan Perez",
    }

    res = await cliente_principal.post("/auth/registro", json=payload)
    assert res.status_code == 201, res.text
    datos = res.json()
    assert datos["email"] == email

    # Verificar que existan exactamente las 3 filas
    async with fabrica() as session:
        # 1. Usuario
        stmt_u = select(Usuario).where(Usuario.email == email)
        u = (await session.execute(stmt_u)).scalar_one_or_none()
        assert u is not None
        assert u.activo is True
        assert u.debe_cambiar_password is False

        # 2. AsignacionRol CLIENTE
        stmt_r = select(AsignacionRol).where(AsignacionRol.usuario_id == u.id)
        roles = (await session.execute(stmt_r)).scalars().all()
        assert len(roles) == 1
        assert roles[0].rol == "CLIENTE"
        assert roles[0].revocada_en is None

        # 3. Cliente
        stmt_c = select(Cliente).where(Cliente.email == email)
        c = (await session.execute(stmt_c)).scalar_one_or_none()
        assert c is not None
        assert c.usuario_id == u.id
        assert c.nombre == "Juan Perez"


@pytest.mark.asyncio
async def test_registro_email_duplicado_da_409(cliente_principal: AsyncClient):
    """
    C-02: Correo de usuario o cliente ya existente da 409 y no duplica filas.
    """
    fabrica = app.state.fabrica_sesiones
    email = email_tdd("registro_dup")
    await crear_usuario_bd(fabrica, email)

    payload = {
        "email": email,
        "password": "Password123!",
        "nombre": "Juan Duplicado",
    }

    res = await cliente_principal.post("/auth/registro", json=payload)
    assert res.status_code == 409, res.text
    assert "Ya existe un usuario o cliente" in res.json()["detail"]


# ============================================================================
# 5.6: Login con cookie HttpOnly (C-03)
# ============================================================================

@pytest.mark.asyncio
async def test_login_exitoso_setea_cookie_httponly_y_sin_token_en_body(cliente_principal: AsyncClient):
    """
    C-03: Login exitoso emite Set-Cookie HttpOnly access_token y el body no contiene el token.
    """
    email = email_tdd("login_ok")
    # Registramos usuario primero
    await cliente_principal.post(
        "/auth/registro",
        json={"email": email, "password": "Password123!", "nombre": "Tester"},
    )

    res = await cliente_principal.post(
        "/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert res.status_code == 200, res.text

    # Cookie HttpOnly
    set_cookie = res.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    # El cuerpo NO contiene el token
    body = res.json()
    assert "token" not in body
    assert "access_token" not in body
    assert body["mensaje"] == "Login exitoso."
    assert "debe_cambiar_password" in body
    assert "expira_en_segundos" in body


@pytest.mark.asyncio
async def test_authorization_bearer_header_sin_cookie_da_401(cliente_principal: AsyncClient):
    """
    C-03: Authorization: Bearer <token> sin cookie da 401 porque el token no se lee de cabecera.
    """
    from app.core.security import crear_token

    email = email_tdd("bearer_test")
    fabrica = app.state.fabrica_sesiones
    await crear_usuario_bd(fabrica, email)
    token = crear_token(sub=email, roles=["CLIENTE"])

    res = await cliente_principal.get(
        "/auth/yo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401


# ============================================================================
# 5.4 & 7.1: Rate limiting y registro de intento_acceso en transacción propia (C-05)
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limiting_sexto_intento_da_429(cliente_principal: AsyncClient):
    """
    C-05: 5 intentos fallidos se registran en intento_acceso; el 6to intento da 429 con Retry-After.
    """
    email = email_tdd("rate_limit")
    fabrica = app.state.fabrica_sesiones

    # 5 intentos fallidos consecutivos
    for _ in range(5):
        res = await cliente_principal.post(
            "/auth/login",
            json={"email": email, "password": "ClaveIncorrecta!"},
        )
        assert res.status_code == 401

    # 6to intento: debe ser 429 Too Many Requests con Retry-After
    res_6 = await cliente_principal.post(
        "/auth/login",
        json={"email": email, "password": "ClaveIncorrecta!"},
    )
    assert res_6.status_code == 429, res_6.text
    assert "Retry-After" in res_6.headers
    assert res_6.headers["Retry-After"] == "60"

    # Verificar que los intentos fallidos quedaron registrados en intento_acceso (7.1)
    async with fabrica() as session:
        stmt = select(IntentoAcceso).where(IntentoAcceso.email == email)
        intentos = (await session.execute(stmt)).scalars().all()
        assert len(intentos) >= 5
        assert all(not i.exitoso for i in intentos)


# ============================================================================
# 5.7: Logout, /auth/yo y cambiar-password
# ============================================================================

@pytest.mark.asyncio
async def test_logout_elimina_cookie(cliente_principal: AsyncClient):
    """
    POST /auth/logout borra la cookie access_token.
    """
    res = await cliente_principal.post("/auth/logout")
    assert res.status_code == 200
    set_cookie = res.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    # La cookie se borra (max-age=0 o fecha expirada)
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower() or "expires=" in set_cookie.lower()


@pytest.mark.asyncio
async def test_auth_yo_devuelve_roles_vigentes_y_roles_token(cliente_principal: AsyncClient):
    """
    GET /auth/yo devuelve el usuario con sus roles vigentes de DB y del token.
    """
    email = email_tdd("yo_test")
    fabrica = app.state.fabrica_sesiones
    await crear_usuario_bd(fabrica, email, roles=("ADMIN", "VENDEDOR"))

    res = await cliente_principal.get(
        "/auth/yo",
        headers=cookie_de(email, roles=["ADMIN", "VENDEDOR"]),
    )
    assert res.status_code == 200, res.text
    datos = res.json()
    assert datos["email"] == email
    assert "ADMIN" in datos["roles_vigentes"]
    assert "VENDEDOR" in datos["roles_vigentes"]
    assert "ADMIN" in datos["roles_token"]


@pytest.mark.asyncio
async def test_cambiar_password_actualiza_hash_y_registra_evento(cliente_principal: AsyncClient):
    """
    POST /auth/cambiar-password valida actual, actualiza hash,
    deja debe_cambiar_password=False y registra EventoSeguridad en mismo UoW (7.2).
    """
    email = email_tdd("cambio_pwd")
    fabrica = app.state.fabrica_sesiones
    from app.core.security import hash_password, verify_password

    hash_inicial = await hash_password("ClaveVieja123!")
    uid = await crear_usuario_bd(fabrica, email, password_hash=hash_inicial, debe_cambiar=True)

    headers = cookie_de(email, roles=["CLIENTE"])

    # 1. Contraseña actual incorrecta -> 401
    bad_res = await cliente_principal.post(
        "/auth/cambiar-password",
        headers=headers,
        json={"password_actual": "Incorrecta!", "password_nueva": "ClaveNueva123!"},
    )
    assert bad_res.status_code == 401

    # 2. Contraseña actual correcta -> 200
    good_res = await cliente_principal.post(
        "/auth/cambiar-password",
        headers=headers,
        json={"password_actual": "ClaveVieja123!", "password_nueva": "ClaveNueva123!"},
    )
    assert good_res.status_code == 200, good_res.text

    # Verificar en DB que el hash cambió, debe_cambiar_password=False, y hay EventoSeguridad
    async with fabrica() as session:
        u = await session.get(Usuario, uid)
        assert u.debe_cambiar_password is False
        assert await verify_password("ClaveNueva123!", u.password_hash) is True

        # EventoSeguridad
        stmt_ev = select(EventoSeguridad).where(
            EventoSeguridad.usuario_afectado_id == uid,
            EventoSeguridad.tipo == "cambio_password",
        )
        ev = (await session.execute(stmt_ev)).scalar_one_or_none()
        assert ev is not None
        assert ev.actor_tipo == "USUARIO"
