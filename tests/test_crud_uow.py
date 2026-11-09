import inspect
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest
from pydantic import ValidationError
from httpx import AsyncClient, ASGITransport

# Import all models to ensure SQLModel registry is populated for relationships
import app.modules.editoriales.models  # noqa: F401
import app.modules.autores.models      # noqa: F401
import app.modules.libros.models       # noqa: F401
import app.modules.clientes.models     # noqa: F401
import app.modules.ventas.models       # noqa: F401
import app.modules.generos.models      # noqa: F401
import app.modules.usuarios.models     # noqa: F401

from app.core.database import get_session
from app.core.paginacion import Pagina
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.core.unit_of_work import UnitOfWork
from app.main import app

# Module imports to be tested
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate, EditorialRead, LibroDeEditorialRead
from app.modules.generos.schemas import GeneroCreate, GeneroRead, LibroDeGeneroRead
from app.modules.autores.schemas import AutorCreate, AutorUpdate, AutorRead, LibroDeAutorRead
from app.modules.libros.schemas import (
    LibroCreate,
    LibroUpdate,
    AutorLibroCreate,
    LibroListRead,
    LibroDetailRead,
    ReponerStockRequest,
)
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteUpdate,
    PerfilCreate,
    ClienteRead,
    ClienteDetailRead,
    VentaResumenRead,
)
from app.modules.ventas.schemas import (
    VentaCreate,
    RenglonCreate,
    VentaListRead,
    VentaDetailRead,
)


# ============================================================================
# Task 4.1 & 4.2: Editoriales, Generos, Autores Repositories and UoW
# ============================================================================

def test_editoriales_uow_and_repository():
    from app.modules.editoriales.repository import EditorialRepository
    from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
    import app.modules.editoriales.service as editorial_service

    session = AsyncMock()
    uow = EditorialesUnitOfWork(session)
    assert isinstance(uow, UnitOfWork)
    assert isinstance(uow.editoriales, EditorialRepository)
    assert isinstance(uow.editoriales, BaseRepository)
    assert uow.editoriales.session is session

    # Check services take uow and do not take AsyncSession
    for name, func in inspect.getmembers(editorial_service, inspect.isfunction):
        if not name.startswith("_") and func.__module__ == editorial_service.__name__:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            assert "session" not in param_names, f"{name} should not have session parameter"
            assert "uow" in param_names, f"{name} should have uow parameter"


def test_generos_uow_and_repository():
    from app.modules.generos.repository import GeneroRepository
    from app.modules.generos.unit_of_work import GenerosUnitOfWork
    import app.modules.generos.service as genero_service

    session = AsyncMock()
    uow = GenerosUnitOfWork(session)
    assert isinstance(uow, UnitOfWork)
    assert isinstance(uow.generos, GeneroRepository)
    assert isinstance(uow.generos, BaseRepository)
    assert uow.generos.session is session

    for name, func in inspect.getmembers(genero_service, inspect.isfunction):
        if not name.startswith("_") and func.__module__ == genero_service.__name__:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            assert "session" not in param_names, f"{name} should not have session parameter"
            assert "uow" in param_names, f"{name} should have uow parameter"


def test_autores_uow_and_repository():
    from app.modules.autores.repository import AutorRepository
    from app.modules.autores.unit_of_work import AutoresUnitOfWork
    import app.modules.autores.service as autor_service

    session = AsyncMock()
    uow = AutoresUnitOfWork(session)
    assert isinstance(uow, UnitOfWork)
    assert isinstance(uow.autores, AutorRepository)
    assert isinstance(uow.autores, BaseRepository)
    assert uow.autores.session is session

    for name, func in inspect.getmembers(autor_service, inspect.isfunction):
        if not name.startswith("_") and func.__module__ == autor_service.__name__:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            assert "session" not in param_names, f"{name} should not have session parameter"
            assert "uow" in param_names, f"{name} should have uow parameter"


# ============================================================================
# Task 4.3: Libros Repository, Movimientos, UoW and Single Stock Point
# ============================================================================

def test_libros_uow_and_repositories():
    from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
    from app.modules.libros.unit_of_work import LibrosUnitOfWork
    import app.modules.libros.service as libro_service

    session = AsyncMock()
    uow = LibrosUnitOfWork(session)
    assert isinstance(uow, UnitOfWork)
    assert isinstance(uow.libros, LibroRepository)
    assert isinstance(uow.libros, SoftDeleteRepository)
    assert isinstance(uow.movimientos, MovimientoStockRepository)
    assert isinstance(uow.movimientos, BaseRepository)
    assert uow.libros.session is session
    assert uow.movimientos.session is session

    for name, func in inspect.getmembers(libro_service, inspect.isfunction):
        if not name.startswith("_") and func.__module__ == libro_service.__name__:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            assert "session" not in param_names, f"{name} should not have session parameter"


@pytest.mark.asyncio
async def test_single_point_of_stock_mutation():
    from app.modules.libros.models import Libro, MovimientoStock
    from app.modules.libros.service import registrar_movimiento_stock

    session = AsyncMock()
    session.add = MagicMock()

    libro = Libro(
        id=1,
        isbn="978-950-07-0001-1",
        titulo="Test Book",
        precio=Decimal("100.00"),
        stock=5,
        editorial_id=1,
    )

    # Restock +10
    mov = await registrar_movimiento_stock(
        session_o_uow=session,
        libro=libro,
        cantidad=10,
        motivo="Reposición",
        usuario_id=1,
    )

    assert libro.stock == 15
    assert isinstance(mov, MovimientoStock)
    assert mov.cantidad == 10
    assert mov.motivo == "Reposición"
    assert mov.libro_id == 1
    assert session.add.called
    assert session.flush.called

    # Cantidad = 0 should be rejected
    with pytest.raises(ValueError):
        await registrar_movimiento_stock(
            session_o_uow=session,
            libro=libro,
            cantidad=0,
            motivo="Invalido",
        )


# ============================================================================
# Task 4.4: Clientes Repositories, UoW and Perfil
# ============================================================================

def test_clientes_uow_and_repository():
    from app.modules.clientes.repository import ClienteRepository, PerfilClienteRepository
    from app.modules.clientes.unit_of_work import ClientesUnitOfWork
    import app.modules.clientes.service as cliente_service

    session = AsyncMock()
    uow = ClientesUnitOfWork(session)
    assert isinstance(uow, UnitOfWork)
    assert isinstance(uow.clientes, ClienteRepository)
    assert isinstance(uow.perfiles, PerfilClienteRepository)
    assert uow.clientes.session is session
    assert uow.perfiles.session is session

    for name, func in inspect.getmembers(cliente_service, inspect.isfunction):
        if not name.startswith("_") and func.__module__ == cliente_service.__name__:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            assert "session" not in param_names, f"{name} should not have session parameter"
            assert "uow" in param_names, f"{name} should have uow parameter"


# ============================================================================
# Task 4.7: Ventas Repository and UoW
# ============================================================================

def test_ventas_uow_and_repository():
    from app.modules.ventas.repository import VentaRepository
    from app.modules.ventas.unit_of_work import VentasUnitOfWork
    import app.modules.ventas.service as venta_service

    session = AsyncMock()
    uow = VentasUnitOfWork(session)
    assert isinstance(uow, UnitOfWork)
    assert isinstance(uow.ventas, VentaRepository)
    assert uow.ventas.session is session

    for name, func in inspect.getmembers(venta_service, inspect.isfunction):
        if not name.startswith("_") and func.__module__ == venta_service.__name__:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            assert "session" not in param_names, f"{name} should not have session parameter"


# ============================================================================
# Task 4.6: Schemas extra="forbid", LibroUpdate no stock, password_hash not exposed
# ============================================================================

def test_input_schemas_reject_extra_fields():
    schemas_to_test = [
        (EditorialCreate, {"nombre": "Editorial X", "pais": "Argentina", "extra_field": "bad"}),
        (EditorialUpdate, {"nombre": "Editorial Y", "extra_field": "bad"}),
        (GeneroCreate, {"nombre": "Ficción", "extra_field": "bad"}),
        (AutorCreate, {"nombre": "Autor X", "nacionalidad": "Argentina", "extra_field": "bad"}),
        (AutorUpdate, {"nombre": "Autor Y", "extra_field": "bad"}),
        (
            LibroCreate,
            {
                "isbn": "978-950-07-0001-1",
                "titulo": "Libro X",
                "precio": "100.00",
                "stock": 5,
                "editorial_id": 1,
                "extra_field": "bad",
            },
        ),
        (LibroUpdate, {"titulo": "Nuevo Titulo", "extra_field": "bad"}),
        (AutorLibroCreate, {"autor_id": 1, "rol": "autor", "orden": 1, "extra_field": "bad"}),
        (ClienteCreate, {"nombre": "Cliente X", "email": "cl@test.com", "extra_field": "bad"}),
        (ClienteUpdate, {"nombre": "Cliente Y", "extra_field": "bad"}),
        (PerfilCreate, {"telefono": "123456", "direccion": "Calle 123", "extra_field": "bad"}),
        (RenglonCreate, {"libro_id": 1, "cantidad": 2, "extra_field": "bad"}),
        (VentaCreate, {"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 1}], "extra_field": "bad"}),
        (ReponerStockRequest, {"cantidad": 5, "motivo": "Reposición", "extra_field": "bad"}),
    ]

    for schema_cls, payload in schemas_to_test:
        with pytest.raises(ValidationError) as exc_info:
            schema_cls(**payload)
        errors = exc_info.value.errors()
        assert any(e["type"] == "extra_forbidden" for e in errors), f"{schema_cls.__name__} did not forbid extra field"


def test_libro_update_does_not_have_stock_field():
    assert "stock" not in LibroUpdate.model_fields
    with pytest.raises(ValidationError) as exc_info:
        LibroUpdate(stock=10)
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_password_hash_never_exposed_in_read_schemas():
    output_schemas = [
        EditorialRead,
        LibroDeEditorialRead,
        GeneroRead,
        LibroDeGeneroRead,
        AutorRead,
        LibroDeAutorRead,
        LibroListRead,
        LibroDetailRead,
        ClienteRead,
        ClienteDetailRead,
        VentaResumenRead,
        VentaListRead,
        VentaDetailRead,
    ]
    for schema_cls in output_schemas:
        assert "password_hash" not in schema_cls.model_fields, f"{schema_cls.__name__} exposes password_hash"


# ============================================================================
# Task 4.5: Standardize list endpoints to return Pagina[T]
# ============================================================================

def get_all_app_routes(app):
    routes = []
    for r in app.routes:
        if hasattr(r, "original_router"):
            routes.extend(r.original_router.routes)
        else:
            routes.append(r)
    return routes


def test_router_list_endpoints_return_pagina_model():
    routes_to_check = [
        ("/libros/", "GET"),
        ("/libros/{id}/movimientos", "GET"),
        ("/editoriales/", "GET"),
        ("/editoriales/{id}/libros", "GET"),
        ("/generos/", "GET"),
        ("/generos/{id}/libros", "GET"),
        ("/autores/{id}/libros", "GET"),
        ("/ventas/", "GET"),
        ("/clientes/{id}/ventas", "GET"),
    ]

    all_routes = get_all_app_routes(app)
    for path, method in routes_to_check:
        matching_routes = [r for r in all_routes if getattr(r, "path", None) == path and method in r.methods]
        assert len(matching_routes) == 1, f"Route {method} {path} not found in app routes"
        route = matching_routes[0]
        resp_model = route.response_model
        assert resp_model is not None, f"Route {method} {path} has no response_model"
        assert issubclass(resp_model, Pagina), f"Route {method} {path} response_model {resp_model} is not Pagina[T]"


@pytest.mark.asyncio
async def test_pagination_and_forbid_extra_via_http():
    session_mock = AsyncMock()

    async def override_session():
        yield session_mock

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. size=500 should be rejected with 422
            res = await client.get("/libros/?size=500")
            assert res.status_code == 422

            # 2. PATCH /libros/1 with stock should be rejected with 422
            res = await client.patch("/libros/1", json={"stock": 10})
            assert res.status_code == 422

            # 3. POST /editoriales/ with extra field should be rejected with 422
            res = await client.post("/editoriales/", json={"nombre": "Bad", "pais": "Arg", "extra": 123})
            assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# Triangulation: C-16 Pagination Edge Cases & Soft Delete Detail Queries
# ============================================================================

@pytest.mark.asyncio
async def test_c16_pagination_service_edge_cases():
    from app.core.paginacion import ParametrosPagina
    from app.modules.libros.unit_of_work import LibrosUnitOfWork
    from app.modules.libros.service import get_libros_list
    from fastapi import HTTPException

    session = AsyncMock()
    uow = LibrosUnitOfWork(session)

    # 1. Zero results -> items=[], total=0, page=1, pages=1
    uow.libros.count_con_filtros = AsyncMock(return_value=0)
    uow.libros.listar_con_filtros = AsyncMock(return_value=[])

    pagina = await get_libros_list(uow, params=ParametrosPagina(page=1, size=20))
    assert pagina.items == []
    assert pagina.total == 0
    assert pagina.page == 1
    assert pagina.pages == 1

    # 2. Page out of range -> 422
    uow.libros.count_con_filtros = AsyncMock(return_value=5)
    uow.libros.listar_con_filtros = AsyncMock(return_value=[])

    with pytest.raises(HTTPException) as exc_info:
        await get_libros_list(uow, params=ParametrosPagina(page=4, size=2))
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_patch_exclude_unset_behavior():
    from app.modules.libros.models import Libro
    from app.modules.libros.schemas import LibroUpdate
    from app.modules.libros.service import update_libro
    from app.modules.libros.unit_of_work import LibrosUnitOfWork

    session = AsyncMock()
    uow = LibrosUnitOfWork(session)

    libro = Libro(
        id=1,
        isbn="978-950-07-0001-1",
        titulo="Original Title",
        precio=Decimal("1500.00"),
        stock=10,
        editorial_id=1,
    )
    uow.libros.get_by_id = AsyncMock(return_value=libro)
    uow.libros.update = AsyncMock()
    uow.libros.get_detail_by_id = AsyncMock(return_value=libro)

    # Only send titulo to PATCH
    patch_payload = LibroUpdate(titulo="New Title Only")
    await update_libro(uow, libro_id=1, data=patch_payload)

    # Verify titulo changed, but isbn and precio were NOT overwritten with None
    assert libro.titulo == "New Title Only"
    assert libro.isbn == "978-950-07-0001-1"
    assert libro.precio == Decimal("1500.00")
    assert libro.stock == 10
