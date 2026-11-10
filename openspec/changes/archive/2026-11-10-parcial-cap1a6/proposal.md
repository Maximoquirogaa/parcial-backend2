# Proposal

## Why

El TP de los capítulos 1 a 4 es una API de catálogo, clientes y ventas sin acceso, sin capa de repositorios y con la configuración y el ciclo de vida resueltos de forma provisoria. El parcial de los capítulos 1 a 6 exige llevarla a un sistema con usuarios y roles, autenticación con cookie, autorización decidida en la base, escrituras agrupadas en Unit of Work, garantías de integridad delegadas a PostgreSQL y lecturas sin N+1. Sin este change la entrega no cumple ninguno de los criterios de evaluación de los Ejercicios 1 a 8.

## What Changes

- **Configuración y ciclo de vida**: `Settings` con `pydantic-settings`, `DATABASE_URL` armada con `@computed_field` a partir de variables sueltas y sin secretos por defecto; motor, fábrica de sesiones, hash ficticio y `dispose()` gestionados en el lifespan y guardados en `app.state`; `get_session` toma la fábrica de ahí; `/health/live` y `/health/ready`; dos grupos de rutas en `main.py` (abierto y protegido).
- **Modelo y migraciones**: cinco tablas nuevas (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `movimiento_stock`); `cliente.usuario_id` y `libro.borrado_en`; dos índices únicos parciales (rol vigente e ISBN vigente); dos migraciones nuevas (autogenerate + manual con disparador append-only); upgrade/downgrade reproducibles.
- **Contratos y CRUD**: contratos de entrada con `extra="forbid"`, PATCH con `exclude_unset`, códigos 201/204/404/409/422 consistentes, envoltorio de paginación `{items,total,page,size,pages}`, respuestas sin `password_hash`, stock no editable por PATCH.
- **Autenticación**: bcrypt con costo configurable, ejecutado en `to_thread` bajo semáforo y fuera de la transacción; límite de 72 bytes en el contrato; login con orden rate-limit → verificación → hash ficticio; JWT en cookie `access_token` HttpOnly/SameSite=Lax/Max-Age/Secure configurable; registro, logout, `GET /auth/yo` y cambio de contraseña.
- **Autorización**: `get_usuario_actual` (401), `requiere_rol` contra roles vigentes en la base (403), asignación y revocación con vigencia y validaciones 422, autoprotección del último ADMIN (409), cambio obligatorio de contraseña con dos grupos de rutas, `/mis-ventas`, eventos de seguridad.
- **Repositorios y Unit of Work**: `BaseRepository[T]` y `SoftDeleteRepository[T]`, UoW base y por módulo, refactor de todos los módulos para que los servicios reciban el UoW, routers lo construyan y no lo abran, y punto único de escritura de stock.
- **Integridad**: disparador append-only sobre `movimiento_stock`; `intento_acceso` escrito en sesión y transacción propias con comentario justificativo; `evento_seguridad` en la misma transacción que el cambio que registra.
- **Lecturas y asincronía**: precarga declarada en repositorios, detalle de venta con número fijo de consultas (incluye libros dados de baja), handlers `async def` sin llamadas bloqueantes, aviso de comprobante con `BackgroundTasks` visible en consola.
- **Datos y pruebas**: `seed.py` con el estado inicial de la consigna; `test/` con los casos C-01…C-16 en archivos `.http` y `test/solo_agregado.sql`.
- **Dependencias**: `pydantic-settings`, `bcrypt`, `PyJWT` y versiones mínimas del stack en `requirements.txt`; `env.example` sin secretos.

**BREAKING**: los listados dejan de devolver listas planas y pasan a devolver el envoltorio paginado; los servicios dejan de aceptar una `AsyncSession`; `POST /libros` recibe `stock_inicial` en lugar de `stock`; el esquema requiere `alembic upgrade head` para las dos migraciones nuevas.

## Capabilities

### New Capabilities

- `configuracion-ciclo-vida`: settings desde el entorno sin secretos por defecto, construcción de `DATABASE_URL`, motor y fábrica en el lifespan, `get_session`, salud live/ready y composición de los dos grupos de rutas.
- `modelo-migraciones`: modelo de dominio ampliado con sus restricciones, índices únicos parciales, navegación bidireccional y evolución del esquema sólo por Alembic.
- `contratos-crud`: contratos de entrada/salida separados del modelo, semántica de códigos, PATCH parcial, envoltorio y validación de paginación, prohibición de editar stock.
- `autenticacion`: hash de contraseñas con bcrypt no bloqueante, orden y límite de intentos del login, respuesta indistinguible, token en cookie HttpOnly y ciclo de sesión del usuario.
- `autorizacion`: identidad de la petición, roles vigentes consultados en la base, administración de asignaciones con vigencia, autoprotección, cambio obligatorio y acceso a lo propio.
- `repositorios-uow`: jerarquía de repositorios genéricos, Unit of Work base y por módulo, límites de transacción y punto único de escritura de stock.
- `integridad`: garantías impuestas por la base (append-only) y escrituras con transacción propia o compartida según su razón de ser.
- `lecturas-asincronia`: carga anticipada declarada, detalle de venta con consultas fijas, ausencia de bloqueos en el bucle y trabajo diferido con `BackgroundTasks`.

### Modified Capabilities

<!-- Sin capabilities existentes en openspec/specs: todas son nuevas. -->

## Impact

- **Código afectado**: `app/core/{config,database}.py` reescritos; nuevos `app/core/{security,dependencies,repository,paginacion,unit_of_work}.py`; nuevo módulo `app/modules/usuarios/`; `repository.py` y `unit_of_work.py` en cada módulo existente; `service.py`, `router.py` y `schemas.py` de todos los módulos refactorizados; `models.py` de `libros` y `clientes` modificados; `main.py` con lifespan y grupos de rutas; `seed.py` reescrito.
- **API**: listados con envoltorio paginado, nuevas rutas de `/auth`, `/usuarios`, `/eventos`, `/libros/{id}/reponer`, `/libros/{id}/movimientos` y `/mis-ventas`; cambios de contrato en `POST /libros` y `PATCH /libros/{id}`.
- **Base de datos**: cinco tablas nuevas, dos columnas nuevas, dos índices únicos parciales, dos migraciones nuevas y un disparador.
- **Dependencias**: `pydantic-settings`, `bcrypt`, `PyJWT`; actualización de versiones mínimas de `fastapi`, `sqlmodel`, `sqlalchemy`, `asyncpg`, `alembic`.
- **Configuración**: `.env` deja de tener valores por defecto en código; se agrega `env.example`; nuevas variables (`SECRET_KEY`, `BCRYPT_COST`, `TOKEN_*`, `POOL_SIZE`, `SQL_ECHO`).
- **Fuera de alcance**: Docker, despliegue en el VPS y los casos D (corresponden al change `despliegue-cap1a4`).
