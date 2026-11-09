# Tasks

## 1. Dependencias y configuración base

- [ ] 1.1 Actualizar `requirements.txt` con `fastapi>=0.111`, `sqlmodel==0.0.24`, `sqlalchemy>=2.0`, `asyncpg>=0.30`, `alembic>=1.13`, `pydantic-settings>=2.0`, `bcrypt>=4.0`, `PyJWT>=2.8`, `uvicorn`. Verificación: `pip install -r requirements.txt` termina sin errores en un entorno limpio.
- [ ] 1.2 Crear `env.example` con todas las variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `SECRET_KEY`, `BCRYPT_COST`, `BCRYPT_MAX_CONCURRENT`, `TOKEN_EXPIRE_MINUTES`, `COOKIE_SECURE`, `POOL_SIZE`, `SQL_ECHO`) sin valores reales. Verificación: el archivo no contiene contraseñas ni claves y documenta el formato de cada variable.
- [ ] 1.3 Reescribir `app/core/config.py` con `BaseSettings` y `@computed_field` para `database_url` (`postgresql+asyncpg`), sin valores por defecto para `SECRET_KEY` ni `POSTGRES_PASSWORD`. Verificación: un script que instancia `Settings` sin esas variables falla con error de validación; con todas definidas devuelve la URL esperada.
- [ ] 1.4 Ajustar `app/core/database.py` para exponer la creación del motor con `pool_size` configurado y la fábrica `async_sessionmaker(expire_on_commit=False)`, y `get_session` leyendo `request.app.state.fabrica_sesiones` y cerrando la sesión al final. Verificación: prueba manual de dos peticiones concurrentes que cada una obtiene una sesión distinta y ninguna queda abierta.
- [ ] 1.5 Reescribir el lifespan de `app/main.py` para crear motor y fábrica en `app.state`, calcular el hash ficticio y hacer `dispose()` al apagar; conservar el handler de `IntegrityError` con mensaje propio. Verificación: arrancar con `uvicorn app.main:app` y comprobar que el motor sólo existe tras el inicio y que el apagado registra el cierre.
- [ ] 1.6 Implementar `/health/live` (sin base) y `/health/ready` (`SELECT 1`, 503 si falla) en `app/modules/health/router.py`. Verificación: `GET /health/live` responde 200 con la base caída y `/health/ready` responde 503; con la base arriba, ambas 200.

## 2. Modelos, relaciones y migraciones

- [ ] 2.1 Crear `app/modules/usuarios/models.py` con `Usuario`, `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad`, sus CHECK, `timestamptz`, el índice único parcial de (`usuario_id`, `rol`) con `postgresql_where` y el índice (`email`, `ip`, `cuando`). Verificación: `python -c "import app.modules.usuarios.models"` y revisar el DDL generado por el autogenerate.
- [ ] 2.2 Modificar `app/modules/clientes/models.py` para agregar `usuario_id` nulo y UNIQUE con relación escalar `usuario` y colección inversa en `Usuario`. Verificación: el autogenerate detecta la columna, la FK, el índice y el UNIQUE.
- [ ] 2.3 Crear `app/modules/libros/models.py::MovimientoStock` y modificar `Libro` con `borrado_en`, quitando el UNIQUE común de `isbn` y agregando el índice único parcial con `postgresql_where=borrado_en.is_(None)`; mantener CHECK de precio y stock y declarar la navegación `movimientos`. Verificación: el DDL muestra el índice parcial y el CHECK; el UNIQUE común ya no aparece.
- [ ] 2.4 Importar todos los modelos en `migrations/env.py` para que el autogenerate vea el esquema completo. Verificación: `alembic check` no reporta diferencias después de aplicar las migraciones.
- [ ] 2.5 Generar la tercera migración con `alembic revision --autogenerate`, leerla, corregir nombres/orden si hace falta y dejar el comentario de revisión. Verificación: la migración crea las cinco tablas, `cliente.usuario_id`, `libro.borrado_en`, los índices únicos parciales y los índices de FK, y el comentario lo documenta.
- [ ] 2.6 Escribir a mano la cuarta migración con la función y el disparador `BEFORE UPDATE OR DELETE` sobre `movimiento_stock`, y su `downgrade` que los elimina. Verificación: sobre base vacía, `alembic upgrade head`, `alembic downgrade base` y otra vez `upgrade head` terminan sin error.
- [ ] 2.7 Verificar el disparador desde psql: un `UPDATE` y un `DELETE` sobre `movimiento_stock` son rechazados y un `INSERT` se acepta. Verificación: salida de psql guardada para el caso C-14.

## 3. Repositorios y Unit of Work base

- [ ] 3.1 Implementar `app/core/repository.py` con `BaseRepository[T]` que recibe `session` y `model`, y ofrece `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `add`/`update` hacen `flush()` y nunca `commit()` ni `close()`. Verificación: prueba unitaria con una sesión falsa que confirma que no se llama a `commit`.
- [ ] 3.2 Implementar `SoftDeleteRepository[T]` en el mismo archivo, con filtrado por defecto de `borrado_en`, `get_by_id_including_deleted` y `soft_delete`; comprobar que la base no expone esos métodos. Verificación: prueba con dos libros, uno dado de baja, que el listado devuelve uno y la consulta especial devuelve dos.
- [ ] 3.3 Implementar `app/core/unit_of_work.py` con `UnitOfWork` como gestor de contexto asincrónico: `commit()` al salir sin excepción, `rollback()` con excepción y sin `close()`. Verificación: prueba con un fallo dentro del bloque que comprueba que la fila no quedó y que la sesión sigue abierta.
- [ ] 3.4 Implementar `app/core/paginacion.py` con `ParametrosPagina` (page ≥ 1, 1 ≤ size ≤ 100, default 20), el genérico `Pagina[T]` y la función que calcula `pages` y lanza 422 si la página supera la última. Verificación: pruebas de `total=0` (pages 1), `total=5,size=2` (pages 3) y `page=4,size=2` (422).

## 4. Repositorios, UoW y refactor de módulos existentes

- [ ] 4.1 Crear `repository.py` y `unit_of_work.py` en `editoriales`, `generos` y `autores`, con los repositorios de cada entidad y precarga declarada donde corresponda. Verificación: cada UoW instancia sus repositorios sobre la misma sesión y el import no falla.
- [ ] 4.2 Refactorizar los servicios de `editoriales`, `generos` y `autores` para recibir el UoW, abrirlo con `async with` y no recibir `AsyncSession`; los routers lo construyen por dependencia. Verificación: `grep` no encuentra `AsyncSession` en esos servicios y los endpoints existentes siguen respondiendo igual.
- [ ] 4.3 Refactorizar `libros` con `LibroRepository` (soft delete), `MovimientoStockRepository` y su UoW; implementar `registrar_movimiento_stock` como punto único de escritura y usarlo en alta con `stock_inicial` y reposición. Verificación: alta y reposición dejan stock y movimiento coherentes; no hay otra escritura de `libro.stock` en el código.
- [ ] 4.4 Refactorizar `clientes` con su repositorio y UoW, incluyendo la ficha de perfil y la relación con usuario; ajustar servicios y routers. Verificación: los endpoints de clientes y perfil funcionan y la respuesta incluye el perfil sin consultas por fila.
- [ ] 4.5 Adoptar en todos los listados (`libros`, `editoriales`, `generos`, y los de relación por autor/editorial/género) el envoltorio `{items,total,page,size,pages}` con `ParametrosPagina` y conteo con los mismos filtros. Verificación: casos de página fuera de rango, `size=500`, cero resultados y `titulo=ficc&size=1` responden según C-16.
- [ ] 4.6 Aplicar `extra="forbid"` a todos los schemas de entrada, `exclude_unset` a todos los PATCH, quitar `stock` del PATCH de libro y `password_hash` de toda respuesta; verificar códigos 201/204/404/409/422 en cada router. Verificación: requests de `test/libreria.http` reciben los códigos declarados y un PATCH con `stock` da 422.
- [ ] 4.7 Refactorizar la lectura de `ventas` a repositorio y UoW, con listado paginado y detalle con `selectinload` de cliente, renglones y libros (incluyendo dados de baja). Verificación: el detalle de una venta con 2 y con 4 renglones emite la misma cantidad de consultas con `SQL_ECHO=true`.

## 5. Autenticación

- [ ] 5.1 Implementar `app/core/security.py` con hash/verificación bcrypt en `asyncio.to_thread` bajo semáforo, costo configurable, y emisión/decodificación de JWT con `sub`, `exp` y roles. Verificación: prueba de que el hash cambia en cada llamada, que el costo coincide con la configuración y que un token vencido falla al decodificarse.
- [ ] 5.2 Calcular el hash ficticio en el lifespan y guardarlo en `app.state`; usarlo en el login cuando el correo no existe. Verificación: el tiempo y el cuerpo de un login con correo inexistente son comparables a los de contraseña incorrecta (C-04).
- [ ] 5.3 Implementar el validador de 72 bytes (UTF-8) compartido y aplicarlo a registro, login y contraseña actual/nueva. Verificación: una contraseña de 73 bytes y otra con multibyte que supera 72 dan 422 sin llegar a bcrypt.
- [ ] 5.4 Implementar el conteo de intentos fallidos por `(email, ip)` en 60 s y la respuesta 429 con `Retry-After` antes de cualquier hash. Verificación: el sexto intento seguido responde 429 en pocos milisegundos y los cinco fallos están en `intento_acceso` (C-05).
- [ ] 5.5 Implementar `POST /auth/registro` con un único UoW (usuario + rol CLIENTE + cliente) y hash previo a la transacción; 409 ante correo de usuario o cliente existente sin filas sueltas. Verificación: registro válido 201 con las tres filas; correo repetido 409 y la tabla no gana filas (C-02).
- [ ] 5.6 Implementar `POST /auth/login` con el orden rate limit → verificación → hash ficticio → registro del intento → emisión del token, y respuesta con `mensaje`, `debe_cambiar_password` y `expira_en_segundos`. Verificación: cookie `access_token` con HttpOnly, SameSite=Lax y Max-Age; el cuerpo no trae token; `Authorization: Bearer` sin cookie da 401 (C-03).
- [ ] 5.7 Implementar `POST /auth/logout`, `GET /auth/yo` (usuario, roles vigentes y roles del token) y `POST /auth/cambiar-password` (valida actual, hash previo a la transacción, deja `debe_cambiar_password` en falso y registra evento en el mismo UoW). Verificación: logout borra la cookie; `/auth/yo` refleja la revocación de un rol; el cambio exitoso permite seguir usando la misma cookie.

## 6. Autorización

- [ ] 6.1 Implementar `app/core/dependencies.py` con `get_usuario_actual` (401 por cookie ausente, token inválido/vencido, usuario inexistente o inactivo) usando la sesión de la petición. Verificación: los cuatro escenarios devuelven 401 y una cookie válida devuelve el usuario.
- [ ] 6.2 Implementar `requiere_rol(*roles)` consultando `asignacion_rol` vigente (`revocada_en IS NULL` y `vence_en` nulo o futuro) en cada petición y respondiendo 403. Verificación: revocar un rol con la sesión abierta hace que la siguiente petición dé 403 (C-07) y un rol declarado sólo en el token no concede permiso.
- [ ] 6.3 Implementar el módulo `usuarios`: alta de personal con contraseña provisoria y `debe_cambiar_password=True`, consulta de roles, asignación con vencimiento opcional, revocación y listado paginado de eventos; cada cambio con su evento en la misma transacción. Verificación: alta 201, roles 200/404, asignación 201/409/422 y evento presente sólo si el cambio se confirmó.
- [ ] 6.4 Validar `vence_en` (con zona horaria y futura, 422), cerrar la fila vencida al reasignar y confiar en el índice único parcial para el 409. Verificación: vencimiento pasado y sin zona dan 422; reasignar un rol vencido crea una fila nueva y cierra la anterior.
- [ ] 6.5 Implementar la autoprotección: un ADMIN no puede revocar su propio ADMIN ni dejar el sistema sin administradores vigentes (409). Verificación: el intento del administrador devuelve 409 y su asignación sigue vigente (C-08).
- [ ] 6.6 Montar los dos grupos de rutas en `main.py` y la dependencia `requiere_cambio_resuelto` una sola vez sobre el grupo protegido; ubicar `health`, `auth` y catálogo en el abierto. Verificación: un usuario con cambio pendiente recibe 403 en el grupo protegido y puede usar `/auth`; tras el cambio, la misma cookie accede (C-09).
- [ ] 6.7 Implementar `GET /mis-ventas` y la verificación de dueño en el detalle de venta (personal o cliente dueño, 403 en otro caso, 404 inexistente) sin `requiere_rol` en el detalle. Verificación: cliente ve su venta 200 y la ajena 403; vendedor ve cualquiera (C-06).

## 7. Integridad

- [ ] 7.1 Implementar el registro de `intento_acceso` en sesión y transacción propias con `commit()` explícito y el comentario de tres puntos (qué hace distinto, por qué no comparte la transacción y su costo). Verificación: un login fallido deja la fila aunque la petición se revierta; el comentario está presente (C-05).
- [ ] 7.2 Verificar que cada evento de seguridad de alta de personal, cambio de rol y cambio de contraseña se escribe en el mismo UoW que el cambio. Verificación: forzar un fallo posterior deja el cambio y el evento revertidos juntos; `alembic`/consulta confirma que no hay eventos huérfanos.
- [ ] 7.3 Traducir los `IntegrityError` a 409 con mensaje propio y comprobar que ningún texto de la base llega al cliente. Verificación: alta duplicada de email, ISBN vigente y asignación vigente devuelven 409 con el mismo estilo de mensaje y sin nombre de tabla.

## 8. Ventas atómicas, stock y lecturas

- [ ] 8.1 Implementar `POST /ventas` en un único UoW: valida cliente y libros (409 si no existen o están dados de baja), valida cantidades y stock, crea venta y renglones con precio copiado y total calculado, descuenta stock y registra un movimiento por renglón. Verificación: venta válida 201 con precios y total correctos; `stock = suma(movimientos)` en los libros afectados (C-10).
- [ ] 8.2 Verificar la atomicidad: una venta con stock insuficiente devuelve 409 sin venta, sin descuentos y sin movimientos; otra con cliente o libro inexistente o dado de baja también 409 sin escrituras. Verificación: los stocks y las sumas de movimientos quedan intactos (C-11, C-12).
- [ ] 8.3 Implementar `POST /libros/{id}/reponer`, `GET /libros/{id}/movimientos` y `DELETE /libros/{id}` (204) con borrado lógico, usando el punto único de stock. Verificación: reposición 200 con movimiento; baja 204; el libro no aparece en el catálogo; el mismo ISBN se puede volver a cargar (C-13).
- [ ] 8.4 Agendar el aviso de comprobante con `BackgroundTasks` sólo tras confirmar la venta, con `await asyncio.sleep(0.5)` y un mensaje visible en la consola con el arranque normal de uvicorn. Verificación: el mensaje aparece después de la respuesta en la consola y no aparece si la venta falla (C-10).
- [ ] 8.5 Auditar las lecturas: toda relación en respuesta se precarga en el repositorio y ninguna depende de lazy loading. Verificación: con `SQL_ECHO=true`, los listados y detalles no emiten consultas adicionales por fila y el detalle de venta mantiene consultas fijas (C-15).
- [ ] 8.6 Confirmar que todos los handlers son `async def` y que bcrypt y cualquier otra operación bloqueante corre fuera del bucle. Verificación: revisión con `grep "def "` sobre los routers y prueba de concurrencia de logins que mantiene respuestas de otros endpoints.

## 9. Seed y casos de prueba

- [ ] 9.1 Reescribir `seed.py` para vaciar las tablas en orden de FK con `RESTART IDENTITY` y cargar usuarios (incluido `nuevo@example.com` con cambio pendiente), editoriales, géneros, autores, libros con stock inicial por movimiento, clientes (Lucía con perfil, Tomás sin usuario, Ana con usuario), la venta 1 con sus dos renglones y salidas de stock, y la línea de evento con actor SISTEMA. Verificación: `python seed.py` deja `stock = suma(movimientos)` en los cinco libros y los totales de la venta 1 en 69000.00.
- [ ] 9.2 Actualizar `test/libreria.http` con los casos C-01 a C-13 y C-15/C-16, cada request con su resultado esperado en comentario, sesiones nombradas con `# @name` y `# @no-cookie-jar` más `Cookie` explícita donde se necesiten dos sesiones. Verificación: recorrer el archivo tras `python seed.py` reproduce cada resultado esperado.
- [ ] 9.3 Escribir `test/solo_agregado.sql` con el `UPDATE` y el `DELETE` sobre `movimiento_stock` y el resultado esperado en comentario. Verificación: ejecutarlo en psql rechaza ambas sentencias y la evidencia queda guardada.
- [ ] 9.4 Agregar a `test/` la evidencia de C-14 (psql) y C-15 (consola con las consultas de 2 y 4 renglones). Verificación: los archivos están referenciados en el README y muestran los resultados exigidos.

## 10. Integración final

- [ ] 10.1 Ejecutar el flujo completo desde cero: entorno virtual, `pip install -r requirements.txt`, `.env`, `alembic upgrade head`, `python seed.py`, `uvicorn app.main:app`. Verificación: la app arranca y `/health/ready` responde 200.
- [ ] 10.2 Recorrer C-01 a C-16 de punta a punta y registrar cualquier desvío. Verificación: todos los casos devuelven el código y los datos esperados; no aparece ningún 500.
- [ ] 10.3 Revisar que no queden credenciales en código, `alembic.ini`, `env.example` ni migraciones. Verificación: búsqueda de `postgres:postgres`, `SECRET_KEY=` con valor y `password` en el repositorio no encuentra secretos reales.

## Workflow follow-up

- Archivar el change cuando la implementación y la revisión estén completas.
- Verificar el resultado archivado con `openspec status --change "parcial-cap1a6"`.
