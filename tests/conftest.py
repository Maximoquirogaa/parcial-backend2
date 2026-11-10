"""
Fixtures compartidas para las pruebas de las secciones 5, 6 y 7.

Las pruebas de integración corren contra PostgreSQL real usando la
configuración del `.env` de desarrollo. Todo dato creado por las pruebas se
marca con el prefijo `tdd_` (usuarios, clientes, correos) o `tdd-` (ISBN) y se
elimina al terminar cada prueba, para no ensuciar la base de datos de trabajo.
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.security import crear_token, hash_password

# Registrar todos los modelos en el registry de SQLModel antes de configurar
# cualquier mapper. Sin esto, relaciones por nombre (p. ej. Usuario.movimientos_stock)
# fallan con KeyError cuando un test importa un módulo aislado.
import app.modules.autores.models  # noqa: F401
import app.modules.clientes.models  # noqa: F401
import app.modules.editoriales.models  # noqa: F401
import app.modules.generos.models  # noqa: F401
import app.modules.libros.models  # noqa: F401
import app.modules.usuarios.models  # noqa: F401
import app.modules.ventas.models  # noqa: F401

# ---------------------------------------------------------------------------
# Marcadores de datos de prueba
# ---------------------------------------------------------------------------

def email_tdd(etiqueta: str) -> str:
    """Correo único y reconocible para una prueba concreta."""
    return f"tdd_{etiqueta}_{uuid.uuid4().hex[:8]}@example.com"


def isbn_tdd(etiqueta: str) -> str:
    """ISBN único y reconocible para una prueba concreta."""
    return f"tdd-{etiqueta}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Hash ficticio compartido (se calcula una sola vez por sesión de pytest)
# ---------------------------------------------------------------------------

_cache_hash: dict[str, str] = {}


async def hash_ficticio_compartido() -> str:
    if "valor" not in _cache_hash:
        _cache_hash["valor"] = await hash_password("clave_ficticia_para_timing")
    return _cache_hash["valor"]


# ---------------------------------------------------------------------------
# Motor de prueba y limpieza
# ---------------------------------------------------------------------------

def crear_engine_prueba():
    settings = get_settings()
    return create_async_engine(settings.database_url, poolclass=NullPool, echo=False)


async def limpiar_filas_tdd() -> None:
    """Borra en orden de claves foráneas todo lo creado por las pruebas."""
    engine = crear_engine_prueba()
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SET session_replication_role = 'replica';"))
            await conn.execute(text(
                """
                DELETE FROM movimiento_stock
                WHERE venta_id IN (
                    SELECT v.id FROM venta v
                    JOIN cliente c ON c.id = v.cliente_id
                    WHERE c.email LIKE 'tdd\\_%'
                ) OR libro_id IN (SELECT id FROM libro WHERE isbn LIKE 'tdd-%')
                """
            ))
            await conn.execute(text(
                """
                DELETE FROM evento_seguridad
                WHERE usuario_afectado_id IN (SELECT id FROM usuario WHERE email LIKE 'tdd\\_%')
                   OR actor_id IN (SELECT id FROM usuario WHERE email LIKE 'tdd\\_%')
                   OR detalle LIKE 'TDD%'
                """
            ))
            await conn.execute(text(
                "DELETE FROM intento_acceso WHERE email LIKE 'tdd\\_%'"
            ))
            await conn.execute(text(
                """
                DELETE FROM renglon_venta
                WHERE venta_id IN (
                    SELECT v.id FROM venta v
                    JOIN cliente c ON c.id = v.cliente_id
                    WHERE c.email LIKE 'tdd\\_%'
                )
                """
            ))
            await conn.execute(text(
                "DELETE FROM venta WHERE cliente_id IN "
                "(SELECT id FROM cliente WHERE email LIKE 'tdd\\_%')"
            ))
            await conn.execute(text(
                "DELETE FROM perfil_cliente WHERE cliente_id IN "
                "(SELECT id FROM cliente WHERE email LIKE 'tdd\\_%')"
            ))
            await conn.execute(text(
                "DELETE FROM asignacion_rol WHERE usuario_id IN "
                "(SELECT id FROM usuario WHERE email LIKE 'tdd\\_%')"
            ))
            await conn.execute(text(
                "DELETE FROM cliente WHERE email LIKE 'tdd\\_%' "
                "OR usuario_id IN (SELECT id FROM usuario WHERE email LIKE 'tdd\\_%')"
            ))
            await conn.execute(text(
                "DELETE FROM libro_autor WHERE libro_id IN "
                "(SELECT id FROM libro WHERE isbn LIKE 'tdd-%')"
            ))
            await conn.execute(text("DELETE FROM libro WHERE isbn LIKE 'tdd-%'"))
            await conn.execute(text("DELETE FROM editorial WHERE nombre LIKE 'tdd %'"))
            await conn.execute(text("DELETE FROM genero WHERE nombre LIKE 'tdd %'"))
            await conn.execute(text(
                "DELETE FROM usuario WHERE email LIKE 'tdd\\_%'"
            ))
            await conn.execute(text("SET session_replication_role = 'origin';"))
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Fixture principal: app + cliente HTTP + recursos en app.state
# ---------------------------------------------------------------------------

@pytest.fixture
async def api():
    """
    Devuelve una función `preparar(app)` que:
    - inyecta motor, fábrica de sesiones y hash ficticio en `app.state`
      (como lo haría el lifespan),
    - devuelve un `AsyncClient` ASGI para esa app,
    - y al terminar la prueba cierra recursos y borra las filas `tdd_`.
    """
    preparadas = []

    async def preparar(app):
        engine = crear_engine_prueba()
        fabrica = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        app.state.engine = engine
        app.state.fabrica_sesiones = fabrica
        app.state.hash_ficticio = await hash_ficticio_compartido()
        client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )
        preparadas.append((client, engine))
        return client

    yield preparar

    for client, engine in preparadas:
        await client.aclose()
        await engine.dispose()
    await limpiar_filas_tdd()


@pytest.fixture
async def cliente_principal(api):
    """Cliente HTTP contra la app real `app.main.app` con recursos inyectados."""
    from app.main import app

    return await api(app)


# ---------------------------------------------------------------------------
# Creadores de datos de prueba
# ---------------------------------------------------------------------------

async def crear_usuario_bd(
    fabrica,
    email: str,
    *,
    roles=(),
    activo: bool = True,
    debe_cambiar: bool = False,
    password_hash: str | None = None,
    nombre: str = "TDD Usuario",
) -> int:
    from app.modules.usuarios.models import AsignacionRol, Usuario

    async with fabrica() as session:
        usuario = Usuario(
            email=email,
            password_hash=password_hash or "$2b$12$sin_hash_real_tdd00000000000000000000000000000000000",
            nombre=nombre,
            activo=activo,
            debe_cambiar_password=debe_cambiar,
        )
        session.add(usuario)
        await session.flush()
        for rol in roles:
            session.add(AsignacionRol(usuario_id=usuario.id, rol=rol))
        await session.commit()
        return usuario.id


async def crear_cliente_bd(fabrica, email: str, usuario_id: int | None = None,
                           nombre: str = "TDD Cliente") -> int:
    from app.modules.clientes.models import Cliente

    async with fabrica() as session:
        cliente = Cliente(nombre=nombre, email=email, usuario_id=usuario_id)
        session.add(cliente)
        await session.commit()
        return cliente.id


async def crear_libro_bd(fabrica, isbn: str, *, stock: int = 0,
                         editorial_id: int, titulo: str = "TDD Libro") -> int:
    from decimal import Decimal

    from app.modules.libros.models import Libro

    async with fabrica() as session:
        libro = Libro(
            isbn=isbn,
            titulo=titulo,
            precio=Decimal("1500.00"),
            stock=stock,
            editorial_id=editorial_id,
        )
        session.add(libro)
        await session.commit()
        return libro.id


async def crear_editorial_bd(fabrica, nombre: str) -> int:
    from app.modules.editoriales.models import Editorial

    async with fabrica() as session:
        editorial = Editorial(nombre=nombre, pais="Argentina")
        session.add(editorial)
        await session.commit()
        return editorial.id


async def crear_venta_bd(fabrica, cliente_id: int, libro_id: int,
                         *, cantidad: int = 1, precio="2500.00") -> int:
    """Crea una venta directa (sin movimientos de stock) para probar lecturas."""
    from decimal import Decimal

    from app.modules.ventas.models import RenglonVenta, Venta

    async with fabrica() as session:
        venta = Venta(cliente_id=cliente_id, total=Decimal(precio) * cantidad)
        session.add(venta)
        await session.flush()
        session.add(
            RenglonVenta(
                venta_id=venta.id,
                libro_id=libro_id,
                cantidad=cantidad,
                precio_unitario=Decimal(precio),
            )
        )
        await session.commit()
        return venta.id


# ---------------------------------------------------------------------------
# Sesiones y tokens
# ---------------------------------------------------------------------------

def cookie_de(email: str, roles=()) -> dict[str, str]:
    """Cabecera Cookie con un JWT firmado válido para el correo dado."""
    token = crear_token(sub=email, roles=list(roles))
    return {"Cookie": f"access_token={token}"}


def token_vencido(email: str) -> str:
    """JWT firmado con buena clave pero con exp en el pasado."""
    from datetime import datetime, timezone

    import jwt

    settings = get_settings()
    pasado = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp())
    return jwt.encode(
        {"sub": email, "roles": [], "iat": pasado, "exp": pasado + 60},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def token_firmado_con_clave_mala(email: str) -> str:
    """JWT con firma de otra clave: inválido a propósito."""
    import jwt

    return jwt.encode(
        {"sub": email, "roles": [], "exp": 9999999999},
        "clave_de_otro_firmador",
        algorithm="HS256",
    )


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    """POST /auth/login y devuelve las cabeceras Cookie para reutilizar la sesión."""
    respuesta = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert respuesta.status_code == 200, respuesta.text
    cookie = respuesta.headers.get("set-cookie", "").split(";")[0]
    return {"Cookie": cookie}
