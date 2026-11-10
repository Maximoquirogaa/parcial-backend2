"""Pruebas del módulo usuarios: asignación de roles con vigencia (tareas 6.3/6.4)."""
import pytest

from app.main import app
from tests.conftest import cookie_de, crear_usuario_bd, email_tdd


@pytest.mark.asyncio
async def test_vencimiento_en_el_pasado_da_422(cliente_principal):
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_roles")
    email_objetivo = email_tdd("objetivo")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))
    id_objetivo = await crear_usuario_bd(fabrica, email_objetivo)

    respuesta = await cliente_principal.post(
        f"/usuarios/{id_objetivo}/roles",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
        json={"rol": "VENDEDOR", "vence_en": "2000-01-01T00:00:00+00:00"},
    )
    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.asyncio
async def test_vencimiento_sin_zona_horaria_da_422(cliente_principal):
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_roles")
    email_objetivo = email_tdd("objetivo")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))
    id_objetivo = await crear_usuario_bd(fabrica, email_objetivo)

    respuesta = await cliente_principal.post(
        f"/usuarios/{id_objetivo}/roles",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
        json={"rol": "VENDEDOR", "vence_en": "2999-01-01T00:00:00"},
    )
    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.asyncio
async def test_asignacion_futura_201_y_duplicada_409(cliente_principal):
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_roles")
    email_objetivo = email_tdd("objetivo")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))
    id_objetivo = await crear_usuario_bd(fabrica, email_objetivo)
    headers = cookie_de(email_admin, roles=["ADMIN"])
    cuerpo = {"rol": "VENDEDOR", "vence_en": "2999-01-01T00:00:00+00:00"}

    primera = await cliente_principal.post(
        f"/usuarios/{id_objetivo}/roles", headers=headers, json=cuerpo
    )
    assert primera.status_code == 201, primera.text

    repetida = await cliente_principal.post(
        f"/usuarios/{id_objetivo}/roles", headers=headers, json=cuerpo
    )
    assert repetida.status_code == 409, repetida.text


@pytest.mark.asyncio
async def test_roles_de_usuario_inexistente_da_404(cliente_principal):
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_roles")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))

    respuesta = await cliente_principal.get(
        "/usuarios/999999/roles",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
    )
    assert respuesta.status_code == 404, respuesta.text


@pytest.mark.asyncio
async def test_revocar_rol_con_sesion_abierta_da_403_en_la_siguiente(cliente_principal):
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_roles")
    email_vendedor = email_tdd("vendedor_revocado")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))
    id_vendedor = await crear_usuario_bd(fabrica, email_vendedor, roles=("VENDEDOR",))

    cookie_vendedor = cookie_de(email_vendedor, roles=["VENDEDOR"])
    antes = await cliente_principal.get(
        "/ventas/", headers=cookie_vendedor
    )
    assert antes.status_code == 200, antes.text

    revocacion = await cliente_principal.delete(
        f"/usuarios/{id_vendedor}/roles/VENDEDOR",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
    )
    assert revocacion.status_code == 200, revocacion.text

    despues = await cliente_principal.get(
        "/ventas/", headers=cookie_vendedor
    )
    assert despues.status_code == 403, despues.text
