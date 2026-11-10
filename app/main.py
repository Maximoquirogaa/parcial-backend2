import logging
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import init_engine_and_sessionmaker
from app.core.dependencies import requiere_cambio_resuelto
from app.core.security import hash_password
from app.modules.auth.router import router as auth_router
from app.modules.autores.router import (
    router as autores_router,
    router_publico as autores_router_publico,
)
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import (
    router as editoriales_router,
    router_publico as editoriales_router_publico,
)
from app.modules.generos.router import (
    router as generos_router,
    router_publico as generos_router_publico,
)
from app.modules.health.router import router as health_router
from app.modules.libros.router import (
    router as libros_router,
    router_publico as libros_router_publico,
)
from app.modules.usuarios.router import (
    eventos_router,
    router as usuarios_router,
)
from app.modules.ventas.router import (
    mis_ventas_router,
    router as ventas_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("libreria.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1. Inicialización de motor asincrónico y fábrica de sesiones en app.state
    engine, session_maker = init_engine_and_sessionmaker(
        database_url=settings.database_url,
        pool_size=settings.POOL_SIZE,
        echo=settings.SQL_ECHO
    )
    app.state.engine = engine
    app.state.fabrica_sesiones = session_maker

    # 2. Pre-cálculo del hash ficticio del login (bcrypt fuera del bucle, en to_thread)
    app.state.hash_ficticio = await hash_password("clave_ficticia_para_login")

    logger.info("Recursos de base de datos y hash ficticio inicializados en app.state.")

    yield

    # Liberación ordenada de conexiones al apagar
    logger.info("Cerrando conexiones del motor de base de datos...")
    await engine.dispose()
    logger.info("Motor de base de datos cerrado correctamente.")


app = FastAPI(
    title="Librería API",
    description="API asincrónica con FastAPI, SQLModel y PostgreSQL - Programación III UTN",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Conflicto de integridad de datos detectado en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Operación rechazada: conflicto de integridad de datos o registro duplicado."}
    )


# Inclusión de routers en dos grupos.
# Abierto: salud, /auth y catálogo público (sin sesión).
router_abierto = APIRouter()
router_abierto.include_router(health_router)
router_abierto.include_router(auth_router)
router_abierto.include_router(libros_router_publico)
router_abierto.include_router(editoriales_router_publico)
router_abierto.include_router(generos_router_publico)
router_abierto.include_router(autores_router_publico)

# Protegido: exige sesión y bloquea con 403 si el cambio de contraseña está
# pendiente. La dependencia se monta UNA sola vez sobre el grupo.
router_protegido = APIRouter(dependencies=[Depends(requiere_cambio_resuelto)])
router_protegido.include_router(usuarios_router)
router_protegido.include_router(eventos_router)
router_protegido.include_router(editoriales_router)
router_protegido.include_router(generos_router)
router_protegido.include_router(autores_router)
router_protegido.include_router(libros_router)
router_protegido.include_router(clientes_router)
router_protegido.include_router(ventas_router)
router_protegido.include_router(mis_ventas_router)

app.include_router(router_abierto)
app.include_router(router_protegido)
