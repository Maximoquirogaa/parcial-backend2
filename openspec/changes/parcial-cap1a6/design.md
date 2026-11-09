# Design

## Context

Ver `proposal.md` — Why. El punto de partida es el TP de los capítulos 1 a 4 ya presente en el repositorio:

- `app/core/config.py` usa `python-dotenv` y un `DATABASE_URL` con credenciales por defecto; `app/core/database.py` ya sabe crear motor y fábrica, pero `app/main.py` los toma de un módulo importado.
- Los servicios reciben `AsyncSession` y consultan con `select()` directo; no hay capa de repositorios ni Unit of Work.
- Los listados usan `limit/offset` y devuelven listas planas.
- `cliente` no tiene `usuario_id`; `libro` no tiene `borrado_en` y el ISBN es UNIQUE común.
- No existen usuarios, roles, autenticación, intento de acceso, eventos de seguridad ni movimiento de stock.
- Hay dos migraciones Alembic (`f929122fc980`, `7e0413ea1de1`) que representan el esquema actual.
- `app/main.py` es el punto de entrada (`uvicorn app.main:app`), aunque la consigna escriba `main.py` en la raíz; se conserva la ruta existente para no romper el arranque ni el despliegue.

Restricciones que condicionan el diseño: SQLModel 0.0.24 sobre SQLAlchemy 2.0 async, PostgreSQL 16, esquema sólo por Alembic, ningún repositorio confirma, ningún servicio construye su UoW, ninguna lectura depende de lazy loading y ninguna llamada a bcrypt bloquea el bucle.

## Goals / Non-Goals

**Goals:**

- Reorganizar la API en `Router → Service → UoW → Repository → Model` sin cambiar el comportamiento público más allá de lo que exigen las specs.
- Aislar los recursos de base en el ciclo de vida de la aplicación y hacer que cada petición use una sola sesión, incluso cuando la identidad y el UoW conviven.
- Dejar la autorización decidida por la base en cada petición, sin confiar en los roles del token.
- Garantizar atomicidad en registro, venta y auditoría, y delegar en PostgreSQL el sólo agregado y la unicidad.
- Mantener el detalle de venta con consultas fijas y el aviso de comprobante fuera del camino de la respuesta.

**Non-Goals:**

- Concurrencia y actualizaciones perdidas (capítulo 7): no se agregan bloqueos ni niveles de aislamiento especiales.
- Cola de tareas con Redis (capítulo 8): el aviso usa `BackgroundTasks` y puede perderse en un reinicio.
- Un segundo mecanismo de sólo agregado por permisos de rol de base: alcanza con el disparador.
- Docker, despliegue y casos D: pertenecen a `despliegue-cap1a4`.
- Invalidación de sesiones al cambiar contraseña: el cambio no emite token nuevo ni revoca cookies.

## Decisions

### Configuración y ciclo de vida

- **`pydantic-settings` con `@computed_field`**: `Settings` declara las variables sueltas de PostgreSQL, `SECRET_KEY`, `BCRYPT_COST`, `TOKEN_EXPIRE_MINUTES`, `COOKIE_SECURE`, `POOL_SIZE`, `SQL_ECHO`, etc. `database_url` se calcula con `@computed_field` y el driver `postgresql+asyncpg`. `SECRET_KEY` y `POSTGRES_PASSWORD` no tienen default; su ausencia produce un error de validación al instanciar `Settings`, por lo que la app no arranca. Alternativa descartada: `load_dotenv()` + `os.getenv`, que ya demostró permitir secretos por defecto y no valida tipos.
- **Instancia única de settings por módulo, sin secretos en logs**: se expone `settings = Settings()` en `app/core/config.py` y se usa `settings.database_url` sólo en el lifespan. El `env.example` documenta todas las variables sin valores.
- **Lifespan como único dueño de los recursos**: crea `engine` y `async_sessionmaker(expire_on_commit=False)` a partir de `settings`, calcula una vez el hash ficticio con bcrypt (en `to_thread`, antes de atender), guarda ambos en `app.state.engine` y `app.state.fabrica_sesiones`, y al apagar hace `await engine.dispose()`. La creación del motor no ocurre al importar, lo que evita el desfase entre servidor y pruebas.
- **`get_session` desde `app.state`**: dependencia `async def` que lee `request.app.state.fabrica_sesiones`, abre una sesión por petición y la cierra con `async with`/`finally`. No se cachea la fábrica en una variable de módulo.
- **Salud separada**: `/health/live` no toca la base; `/health/ready` ejecuta `SELECT 1` con el motor del estado y traduce cualquier excepción a 503. Se mantiene el router `health` liviano.
- **Dos grupos de rutas**: un `APIRouter` abierto (health, auth, catálogo público) y un `APIRouter` protegido con `dependencies=[Depends(requiere_cambio_resuelto)]` montado una sola vez; las rutas que además exigen rol agregan `Depends(requiere_rol(...))`. FastAPI suma dependencias, por eso el control obligatorio se monta en el grupo y no ruta por ruta.

### Modelo y migraciones

- **SQLModel con restricciones explícitas**: `asignacion_rol` e `libro` declaran índices únicos parciales con `Index(..., unique=True, postgresql_where=...)` en `__table_args__`. `Libro.isbn` deja de tener `unique=True` e `index=True` común y pasa al índice parcial. `borrado_en` y el resto de fechas nuevas usan `DateTime(timezone=True)`; `movimiento_stock.cantidad` es entero con CHECK `cantidad <> 0`.
- **Navegación bidireccional**: `Cliente.usuario` es `Relationship` escalar con `back_populates`; `Usuario.clientes` es la colección inversa (a lo sumo una fila por UNIQUE). `Libro.movimientos`, `MovimientoStock.libro`, `MovimientoStock.venta`, `Venta.movimientos` se declaran en ambos extremos. `AsignacionRol.usuario` y `EventoSeguridad` no navegan porque el actor es texto.
- **Dos migraciones nuevas**: la tercera se genera con `alembic revision --autogenerate`, se lee y se corrige si hace falta (por ejemplo, nombres de índices o el orden de FK), con comentario de revisión; crea las cinco tablas, `cliente.usuario_id`, `libro.borrado_en`, reemplaza el UNIQUE de ISBN por el índice parcial y añade índices de FK. La cuarta se escribe a mano y crea la función y el disparador `BEFORE UPDATE OR DELETE` sobre `movimiento_stock`; su `downgrade` los elimina. Alternativa descartada: un `create_all` o un `op.execute` suelto en el arranque, que impide reproducir el esquema desde cero.
- **Autogenerate requiere metadata completa**: se importan todos los modelos en `migrations/env.py` para que la comparación vea las tablas nuevas y detecte también los cambios en `cliente` y `libro`.

### Contratos, paginación y errores

- **Schemas Pydantic v2 con `extra="forbid"`**: `model_config = ConfigDict(extra="forbid")` en todos los de entrada. `UsuarioSalida`/`ClienteSalida` nunca declaran `password_hash`. `POST /libros` recibe `stock_inicial` y `autores`; `LibroPatch` no declara `stock`. Los PATCH usan `model_dump(exclude_unset=True)`.
- **Envoltorio de paginación en `app/core/paginacion.py`**: un `ParametrosPagina` valida `page >= 1` y `1 <= size <= 100` (default 20) y una función `paginar(items, total, page, size)` calcula `pages = max(1, ceil(total/size))` y lanza 422 si `page > pages` con `total > 0`. Las respuestas usan un genérico `Pagina[T]` con `items/total/page/size/pages`. Alternativa descartada: mantener `limit/offset`, que no cumple el contrato de la consigna y permite páginas no deterministas.
- **Búsqueda parametrizada**: `ilike` con parámetro ligado (`Libro.titulo.ilike(f"%{titulo}%")` pasando el valor como bind), evitando concatenación en SQL.
- **Traducción de errores**: los servicios levantan excepciones de dominio (`Conflicto`, `NoEncontrado`, `NoAutorizado`, `Prohibido`) y los routers las traducen a 409/404/401/403. Se conserva el handler global de `IntegrityError` como red de seguridad, pero con mensaje propio y sin `exc.orig` en la respuesta; la validación de contrato cubre el resto para que nada inválido llegue a 500.

### Autenticación

- **`app/core/security.py`**: `hash_password`, `verify_password`, `crear_token`, `decodificar_token`. El costo sale de `settings.BCRYPT_COST`. Todas las llamadas a bcrypt pasan por `await asyncio.to_thread(...)` y un `asyncio.Semaphore(settings.BCRYPT_MAX_CONCURRENT)` de módulo. El hash ficticio se calcula en el lifespan y se guarda en `app.state.hash_ficticio`; si no estuviera disponible, se usa un hash constante precalculado del mismo costo.
- **Contrato de 72 bytes**: un validador Pydantic compartido mide `len(valor.encode("utf-8")) <= 72` y devuelve 422 antes de tocar bcrypt, tanto en registro, login como en el cambio.
- **Orden del login**: (1) contar `intento_acceso` fallidos por `(email, ip)` en los últimos 60 s; si `>= 5`, responder 429 con `Retry-After` sin hash; (2) buscar usuario; (3) verificar contra su hash o contra el ficticio; (4) registrar el intento en transacción propia; (5) si es correcto, emitir token. El conteo se reinicia porque la ventana es móvil y los fallos anteriores quedan en la tabla sin contar.
- **Cookie**: `set_cookie("access_token", token, httponly=True, samesite="lax", max_age=segundos, secure=settings.COOKIE_SECURE, path="/")`. El cuerpo del login lleva sólo mensaje, `debe_cambiar_password` y `expira_en_segundos`. La dependencia lee `request.cookies.get("access_token")`; nunca `Authorization`.
- **Registro y eventos**: el registro de un cliente abre un único UoW con los repositorios de usuario, asignación y cliente; el hash se calcula antes de abrir el UoW. `POST /usuarios` (alta de personal) calcula el hash antes, escribe usuario + asignación + evento en un solo UoW, con `debe_cambiar_password=True` y contraseña provisoria. El cambio de contraseña calcula el hash nuevo antes de abrir el UoW y escribe usuario + evento.

### Autorización y transacciones

- **Sesión compartida**: `get_uow` depende de `get_session` y construye el UoW del módulo con esa sesión. `get_usuario_actual` también depende de `get_session`, de modo que identidad, rol, servicio, repositorios y eventos comparten una única sesión y una única conexión del pool. Alternativa descartada: dependencias con sesión propia, que duplican conexiones por petición.
- **Roles vigentes en cada petición**: `requiere_rol(*roles)` consulta `asignacion_rol` con `revocada_en IS NULL` y `(vence_en IS NULL OR vence_en > now())`. El token incluye roles informativos para `/auth/yo`, no para permisos.
- **Dos grupos de rutas**: `requiere_cambio_resuelto` se ejecuta como dependencia del grupo protegido, lee el usuario actual y responde 403 si `debe_cambiar_password`; `/auth` queda en el grupo abierto para permitir el cambio.
- **Asignaciones con vigencia**: asignar valida `vence_en` con zona horaria y futura (422), cierra la fila vencida si existe, y confía en el índice único parcial para el 409. Revocar llama al servicio, que rechaza la auto-revocación del ADMIN y la revocación del último admin vigente (409). La comprobación del último admin cuenta asignaciones ADMIN vigentes dentro del mismo UoW.
- **Lo propio**: `GET /mis-ventas` filtra por el `usuario_id` del cliente asociado al usuario; el detalle de venta decide en el servicio si el actor es personal (rol vigente) o el dueño, y responde 403 si no es ninguno. `GET /ventas/{id}` no lleva `requiere_rol`.
- **`intento_acceso` fuera de la transacción de la petición**: se usa una `AsyncSession` creada desde la fábrica del estado, con `async with` y `commit()` explícito, y un comentario que documenta qué hace distinto, por qué no puede compartir la transacción (el fallo que se cuenta es el que la revierte) y su costo (deja filas aunque la petición falle).

### Repositorios, UoW y stock

- **`BaseRepository[T]`** recibe `session` y `model: type[T]`, y ofrece `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `add`/`update` hacen `await session.flush()`, nunca `commit()`. `SoftDeleteRepository[T]` agrega `get_by_id_including_deleted` y `soft_delete`, y sobreescribe los listados para filtrar `borrado_en IS NULL`.
- **Repositorios por entidad** con métodos nombrados por lo que traen (`get_by_isbn`, `get_con_autores`, `listar_con_filtros`, `get_con_renglones_y_libros`), y las opciones de precarga (`selectinload`/`joinedload`) declaradas dentro del método que las necesita. Alternativa descartada: precargar en el servicio, que acopla la consulta a la capa de negocio.
- **UoW base** con `__aenter__`/`__aexit__`: en el `__aexit__` hace `commit()` si no hubo excepción y `rollback()` si la hubo, y nunca `close()`. Cada módulo expone `UnitOfWorkDe<Modulo>` que instancia sus repositorios con `self.session`.
- **Flujo de capas**: el router recibe el UoW por `Depends`, lo pasa al servicio, y el servicio lo abre con `async with`. Ningún servicio construye el UoW ni recibe `AsyncSession`. Los handlers de lectura usan `await uow.__aenter__()`/`__aexit__` vía el mismo servicio, o el servicio usa un patrón `async with` uniforme.
- **Punto único de escritura de stock**: un método del servicio/repositorio de libros (`registrar_movimiento_stock`) inserta el `MovimientoStock` y actualiza `libro.stock` en la misma sesión. Lo usan el alta con `stock_inicial`, la reposición y la venta; el PATCH no toca stock y `seed.py` pasa por el mismo camino.
- **Venta atómica**: el servicio de ventas, dentro de un UoW, resuelve cliente y libros (incluyendo dados de baja para detectar 409), valida cantidades y stock, crea la venta, copia precios, calcula total, crea renglones y llama al punto único de stock por cada renglón. Un `Conflicto` revierte todo. El `BackgroundTasks` se agenda sólo después de que el `async with` confirmó.

### Lecturas y pruebas

- **Detalle de venta sin N+1**: el repositorio de ventas usa `selectinload(Venta.renglones).selectinload(RenglonVenta.libro)` y `selectinload(Venta.cliente)` en una consulta (más la del cliente si se resuelve aparte), y el detalle de libros dados de baja se obtiene de la relación precargada, sin lazy. La cantidad de sentencias queda fija y se verifica con `SQL_ECHO=true` en `test/evidencia`.
- **BackgroundTasks**: el servicio devuelve la venta y el router agenda `background_tasks.add_task(avisar_comprobante, ...)`; el aviso hace `await asyncio.sleep(0.5)` y usa `logging.getLogger("libreria.avisos")` con `print`/logger ya configurado por `logging.basicConfig` del `main`, para que el mensaje aparezca con uvicorn por defecto.
- **Seed**: script async que usa la fábrica de sesiones, trunca las tablas en orden de FK (`movimiento_stock`, `evento_seguridad`, `intento_acceso`, `asignacion_rol`, `usuario`, `renglon_venta`, `venta`, `perfil_cliente`, `cliente`, `libro_autor`, `libro`, `autor`, `genero`, `editorial`) con `RESTART IDENTITY`, y carga los datos de la sección «Datos iniciales», incluido el stock inicial por movimientos y la venta 1 con sus salidas.
- **Pruebas `.http`**: un archivo por bloque de casos o un archivo maestro con `# @name` por sesión y `# @no-cookie-jar`; cada request lleva el resultado esperado en comentario y el archivo indica que se corre `python seed.py` antes. `test/solo_agregado.sql` demuestra C-14 desde psql.

## Risks / Trade-offs

- **`selectinload` vs. `joinedload` en colecciones**: `joinedload` sobre renglones duplica filas y puede romper el conteo → se usa `selectinload` para colecciones y una consulta adicional fija, nunca una por fila.
- **Una sola sesión para identidad y UoW**: si una dependencia confirma, el UoW pierde atomicidad → la identidad y el rol sólo leen; el único `commit` es el del UoW (y el explícito de `intento_acceso` en su sesión aparte).
- **`intento_acceso` deja filas aunque la petición falle**: es el costo buscado y está documentado; puede crecer sin límite → se acepta para el parcial; la ventana de conteo es de 60 s y el índice compuesto sostiene la consulta.
- **Dos grupos de rutas**: una ruta mal ubicada en el grupo abierto quedaría sin el control obligatorio → se revisa que todo router de negocio se monte en el grupo protegido y sólo health/auth/catálogo en el abierto; las pruebas C-09 lo verifican.
- **`autogenerate` puede no ver el disparador**: por eso la cuarta migración es manual; si el autogenerate propone cambios espurios se corrigen a mano y se documenta.
- **`Secure` configurable**: en HTTP local debe quedar en `false` o el navegador no envía la cookie → default `false` en desarrollo, `true` documentado para producción.
- **bcrypt con costo alto**: subir el costo enmienda el tiempo de login y el hash ficticio → `BCRYPT_COST` configurable y el hash ficticio se calcula con el mismo costo en el lifespan.

## Migration Plan

1. Actualizar `requirements.txt` y `env.example`; crear el `.env` local con `SECRET_KEY` y `POSTGRES_*`.
2. Implementar settings, database, lifespan y salud; verificar que la app arranca sin crear el motor al importar.
3. Escribir modelos y generar la tercera migración con autogenerate; leerla, corregirla y aplicarla.
4. Escribir a mano la cuarta migración del disparador; probar `upgrade head`, `downgrade base` y `upgrade head` sobre base vacía.
5. Implementar repositorios y UoW base, refactorizar módulos y paginación.
6. Implementar seguridad, dependencias y módulo `usuarios`; montar los dos grupos de rutas.
7. Implementar venta atómica, movimientos y el punto único de stock; ajustar seed.
8. Ejecutar `python seed.py` y recorrer C-01…C-16; capturar C-14 y C-15 en `evidencia/`.

**Rollback**: `alembic downgrade` a la revisión anterior elimina tablas, columnas, índices y disparador; el código se revierte con el control de versiones. No hay datos de producción que preservar: la base se recrea con `seed.py`.

## Open Questions

- Ninguna pendiente que cambie specs, enfoque o desglose de tareas.
