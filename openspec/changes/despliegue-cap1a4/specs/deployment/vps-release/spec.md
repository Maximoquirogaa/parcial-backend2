# Spec Delta

## Purpose

Define la puesta en línea del TP de los capítulos 1 a 4 en el VPS, la operación del contenedor contra la base provista por la cátedra y la documentación y evidencia que acreditan el despliegue.

## ADDED Requirements

### Requirement: TP de los capítulos 1 a 4 en línea

El TP de los capítulos 1 a 4, sin las modificaciones del parcial, SHALL estar accesible desde fuera del VPS en una URL pública declarada. El despliegue MUST mantenerse en línea hasta la publicación de las notas.

#### Scenario: Acceso público al catálogo

- **WHEN** se consulta `GET /libros/` desde fuera del VPS en la URL declarada
- **THEN** responde 200 con la lista de libros cargados

#### Scenario: Acceso público a la salud

- **WHEN** se consulta `GET /health/ready` desde fuera del VPS
- **THEN** responde 200 e indica que la base está conectada

#### Scenario: Venta desde fuera del VPS

- **WHEN** se envía `POST /ventas/` con el cuerpo de ejemplo del TP
- **THEN** responde 201 con los precios copiados de cada libro y el total calculado por el servidor

### Requirement: Datos iniciales cargados en el servidor

La base del VPS SHALL cargarse ejecutando dentro del contenedor el comando de datos iniciales del README del TP, mediante `docker exec libreria ...`.

#### Scenario: Carga de datos iniciales

- **WHEN** se ejecuta el comando de datos iniciales dentro del contenedor
- **THEN** el catálogo público devuelve los libros del TP y las ventas de ejemplo están disponibles

### Requirement: DEPLOY.md completo

`despliegue/DEPLOY.md` SHALL incluir la URL pública, el día y la hora del despliegue, los comandos `docker build` y `docker run` completos con el nombre del archivo de variables, los cambios hechos al TP para que corra en el contenedor y el procedimiento de actualización. MUST NOT incluir el contenido del archivo de variables ni credenciales reales.

#### Scenario: Revisión de la documentación

- **WHEN** se lee `DEPLOY.md`
- **THEN** constan la URL, la fecha y hora, ambos comandos completos, los cambios aplicados al TP y la actualización, sin secretos

### Requirement: Actualización sin pérdida de datos

El procedimiento de actualización SHALL construir la imagen de nuevo, eliminar el contenedor y volver a ejecutarlo. Los datos MUST sobrevivir porque viven en la base del servidor y no en el contenedor.

#### Scenario: Reemplazo del contenedor

- **WHEN** se ejecuta `docker rm -f libreria` y el mismo `docker run` otra vez
- **THEN** el contenedor vuelve a estar `healthy`, los datos siguen disponibles y las migraciones no se repiten

### Requirement: Evidencia de los casos D

`despliegue/evidencia/` SHALL contener la salida de los casos D-01 a D-08: tamaño de la imagen base, build y run en servidor limpio, pruebas públicas, reinicio, ejecución sin `DATABASE_URL`, contenido de la imagen, usuario del proceso y aviso del comprobante en los logs.

#### Scenario: Revisión de la evidencia

- **WHEN** se recorre la carpeta `evidencia/`
- **THEN** cada caso D-01 a D-08 tiene su archivo con el comando ejecutado y la salida obtenida

#### Scenario: Aviso del comprobante

- **WHEN** se registra una venta y se revisan `docker logs libreria`
- **THEN** el aviso del comprobante aparece después de la línea de la respuesta

### Requirement: Cambios al TP acotados

Al snapshot del TP sólo SHALL agregársele `Dockerfile`, `.dockerignore`, `env.example`, `DEPLOY.md` y `evidencia/`. Su lógica MUST NOT modificarse, salvo un defecto propio que impida el arranque en el contenedor, y ese cambio MUST quedar documentado en `DEPLOY.md`.

#### Scenario: Snapshot congelado

- **WHEN** se compara `despliegue/` con el commit `f934174`
- **THEN** las diferencias se limitan a los archivos de empaquetado, documentación y evidencia, salvo correcciones documentadas

#### Scenario: Defecto propio corregido

- **WHEN** el TP no arranca en el contenedor por una ruta de salud o una configuración propia
- **THEN** se corrige lo mínimo necesario y `DEPLOY.md` describe el cambio y su motivo
