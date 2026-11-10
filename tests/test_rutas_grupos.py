"""Pruebas de composición de los dos grupos de rutas (tarea 6.6).

Verifican que el catálogo queda en el grupo abierto y que `/auth`,
`/usuarios` y `/eventos` están montados, con `/usuarios` y `/eventos`
dentro del grupo protegido (401 sin cookie en lugar de 404).
"""
import pytest


@pytest.mark.asyncio
async def test_catalogo_publico_sin_cookie(cliente_principal):
    respuesta = await cliente_principal.get("/libros/")
    assert respuesta.status_code == 200, respuesta.text


@pytest.mark.asyncio
async def test_auth_montado_en_grupo_abierto(cliente_principal):
    # Cuerpo inválido: la ruta existe y responde 422 sin pedir sesión.
    respuesta = await cliente_principal.post("/auth/login", json={})
    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.asyncio
async def test_usuarios_montado_en_grupo_protegido(cliente_principal):
    respuesta = await cliente_principal.get("/usuarios/1/roles")
    assert respuesta.status_code == 401, respuesta.text


@pytest.mark.asyncio
async def test_eventos_montado_en_grupo_protegido(cliente_principal):
    respuesta = await cliente_principal.get("/eventos")
    assert respuesta.status_code == 401, respuesta.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metodo,ruta,payload",
    [
        ("post", "/editoriales/", {"nombre": "x", "pais": "Argentina"}),
        ("post", "/generos/", {"nombre": "x"}),
        ("post", "/autores/", {"nombre": "x", "nacionalidad": "Argentina"}),
        ("post", "/clientes/", {"nombre": "x", "email": "x@example.com"}),
        ("post", "/ventas/", {"cliente_id": 1, "renglones": []}),
    ],
)
async def test_mutaciones_en_grupo_protegido(cliente_principal, metodo, ruta, payload):
    respuesta = await getattr(cliente_principal, metodo)(ruta, json=payload)
    assert respuesta.status_code == 401, respuesta.text
