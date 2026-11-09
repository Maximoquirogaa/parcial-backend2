# Tasks

## 1. Snapshot del TP de los capítulos 1 a 4

- [x] 1.1 Generar `despliegue/` desde el commit congelado con `git archive f934174 | tar -x -C despliegue` y verificar que existen `app/main.py`, `alembic.ini`, `migrations/`, `requirements.txt` y `seed.py`.
- [x] 1.2 Verificar que el snapshot coincide con `f934174` y que no contiene `.env`, `venv`, `__pycache__` ni archivos del refactor de `parcial-cap1a6`; comparar con `git diff --no-index` contra una extracción limpia del commit.

## 2. Empaquetado Docker

- [x] 2.1 Crear `despliegue/Dockerfile` con base `python:3.12-alpine`, `requirements.txt` antes del código, `pip install --no-cache-dir`, usuario no-root, `EXPOSE 8000`, `HEALTHCHECK` sobre `http://127.0.0.1:8000/health/ready` y `CMD` que ejecute `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`; verificar con `docker build -t libreria:cap1a4 despliegue` que la imagen construye sin errores.
- [x] 2.2 Crear `despliegue/.dockerignore` excluyendo `.env`, `venv/`, `.venv/`, `.git/`, `__pycache__/`, `*.pyc`, `.pytest_cache/` y la propia carpeta `evidencia/` sólo si no debe viajar en la imagen; verificar que un build posterior no copia `.env` con `docker run --rm --entrypoint ls /app <imagen>`.
- [x] 2.3 Crear `despliegue/env.example` con la forma `DATABASE_URL=postgresql+asyncpg://usuario:contraseña@host:5432/base` y `SQL_ECHO=false`, sin valores reales; verificar con una búsqueda de credenciales que el archivo no contiene contraseñas ni hosts reales.

## 3. Verificación local de la imagen

- [x] 3.1 Construir la imagen y verificar con `docker images` que `python:3.12-alpine` está por debajo de 100 MB y que `libreria:cap1a4` existe con el `Dockerfile` esperado.
- [x] 3.2 Crear un archivo de variables local fuera del repositorio y ejecutar `docker run -d --name libreria -p 8000:8000 --env-file <archivo> libreria:cap1a4`; verificar que `docker logs` muestra `alembic upgrade head` aplicado y uvicorn escuchando.
- [x] 3.3 Verificar la salud con `docker ps` en estado `healthy` y con `docker exec libreria wget -qO- http://127.0.0.1:8000/health/ready` respondiendo 200.
- [x] 3.4 Verificar que el proceso no corre como root con `docker exec libreria id`, comprobando que el uid es distinto de 0.
- [x] 3.5 Verificar que la imagen no contiene secretos con `docker run --rm --entrypoint ls <imagen> /app` (sin `.env`) y `docker run --rm --entrypoint env <imagen>` (sin `DATABASE_URL` ni contraseñas).
- [x] 3.6 Verificar el caso de arranque sin configuración con `docker run --rm <imagen>` sin `DATABASE_URL`; comprobar que el contenedor termina con código distinto de cero y no queda sirviendo.
- [x] 3.7 Verificar la persistencia y el reinicio con `docker rm -f libreria` y el mismo `docker run`; comprobar que vuelve a `healthy`, que los datos siguen y que las migraciones no se repiten.

## 4. Despliegue en el VPS

- [ ] 4.1 Copiar `despliegue/` al VPS con `scp`/`rsync` y crear allí el archivo de variables (por ejemplo `~/libreria.env`) con `DATABASE_URL` provista por la cátedra, permisos `600` y fuera del repositorio; verificar que el archivo no se versiona ni se imprime en consola.
- [ ] 4.2 Construir la imagen en el VPS con `docker build -t libreria:cap1a4 despliegue`; verificar que termina sin errores y que `docker images` muestra la etiqueta.
- [ ] 4.3 Ejecutar `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file ~/libreria.env` y, si la base está en el host, agregar `--add-host host.docker.internal:host-gateway`; verificar que el contenedor queda `healthy`.
- [ ] 4.4 Cargar los datos iniciales dentro del contenedor con `docker exec libreria python seed.py`; verificar que `GET /libros/` devuelve los libros del TP.
- [ ] 4.5 Probar desde fuera del VPS la URL pública: `GET /health/ready` (200), `GET /libros/` (200 con datos) y `POST /ventas/` con el cuerpo de ejemplo (201 con precios copiados y total calculado).

## 5. Evidencia D-01 a D-08

- [x] 5.1 Guardar `despliegue/evidencia/D-01_imagen_base.txt` con `docker images` mostrando `python:3.12-alpine` por debajo de 100 MB y la imagen del proyecto; verificar que el archivo incluye la salida completa.
- [ ] 5.2 Guardar `despliegue/evidencia/D-02_build_run.txt` con el `docker build` y `docker run` en servidor limpio, `docker ps` en `healthy` y el fragmento de `docker logs` con las migraciones aplicadas; verificar que se lee el estado y las migraciones.
- [ ] 5.3 Guardar `despliegue/evidencia/D-03_url_publica.txt` con las respuestas HTTP a `/health/ready`, `/libros/` y `POST /ventas/` desde fuera del VPS; verificar los códigos 200/200/201 y el cuerpo de la venta.
- [ ] 5.4 Guardar `despliegue/evidencia/D-04_reinicio.txt` con `docker rm -f libreria`, el mismo `docker run`, el estado `healthy`, los datos conservados y las migraciones no repetidas; verificar que el archivo muestra los cuatro puntos.
- [x] 5.5 Guardar `despliegue/evidencia/D-05_sin_database_url.txt` con la ejecución sin `DATABASE_URL`, el código de salida distinto de cero y el error de conexión; verificar que el contenedor no queda sirviendo y explicar el comportamiento del default del TP.
- [x] 5.6 Guardar `despliegue/evidencia/D-06_contenido_imagen.txt` con `docker run --rm --entrypoint ls <imagen> /app` y `docker run --rm --entrypoint env <imagen>`; verificar que no aparece `.env`, `DATABASE_URL` ni contraseñas.
- [x] 5.7 Guardar `despliegue/evidencia/D-07_usuario.txt` con `docker exec libreria id`; verificar que el uid no es 0 y que el archivo muestra el usuario.
- [ ] 5.8 Guardar `despliegue/evidencia/D-08_aviso_comprobante.txt` con el fragmento de `docker logs libreria` posterior a la venta de D-03; verificar que el aviso aparece después de la línea de la respuesta.
- [ ] 5.9 Revisar la carpeta `evidencia/` completa y verificar que existen los ocho archivos D-01 a D-08, que cada uno tiene comando y salida, y que ninguno incluye credenciales reales. (Revisión parcial hecha: D-01/D-05/D-06/D-07 presentes y sin credenciales; faltan D-02/D-03/D-04/D-08 → pendiente de VPS.)

## 6. Documentación del despliegue

- [ ] 6.1 Escribir `despliegue/DEPLOY.md` con la URL pública, el día y la hora del despliegue, los comandos `docker build` y `docker run` completos con el nombre del archivo de variables, los cambios hechos al TP y el procedimiento de actualización; verificar que no incluye el contenido del archivo de variables ni secretos.
- [x] 6.2 Documentar en `DEPLOY.md` cualquier corrección aplicada al TP para que arranque en el contenedor (por ejemplo, una ruta de salud) o dejar constancia explícita de que no hizo falta ninguna; verificar que la sección de cambios coincide con el diff real del snapshot.
- [ ] 6.3 Verificar el procedimiento de actualización ejecutando el ciclo completo en el VPS: construir de nuevo, `docker rm -f libreria`, el mismo `docker run`, comprobar `healthy` y que los datos siguen; ajustar `DEPLOY.md` si algún comando no coincide con lo probado.

## 7. Verificación de integración

- [x] 7.1 Verificar con `git diff --no-index` que el snapshot sólo agrega `Dockerfile`, `.dockerignore`, `env.example`, `DEPLOY.md` y `evidencia/` respecto de `f934174`, sin cambios de lógica no documentados.
- [x] 7.2 Verificar que `despliegue/` no contiene `.env`, `venv`, `.venv` ni `__pycache__`, y que sí contiene `env.example` y la carpeta `evidencia/` completa, de cara al armado del `.zip`.
- [ ] 7.3 Contrastar los requisitos de `specs/deployment/container-image/spec.md` y `specs/deployment/vps-release/spec.md` con la evidencia y `DEPLOY.md`, y confirmar que cada escenario tiene su comprobación registrada.

## Workflow follow-up

- Archivar el change cuando la entrega esté revisada y el despliegue siga en línea hasta la publicación de las notas.
- Sincronizar las specs principales al archivar y verificar el resultado con `openspec status --change "despliegue-cap1a4" --json`.
