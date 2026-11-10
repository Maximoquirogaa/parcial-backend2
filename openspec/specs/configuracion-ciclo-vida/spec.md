# configuracion-ciclo-vida Specification

## Purpose
Define cómo la aplicación obtiene su configuración del entorno, construye y libera sus recursos de base de datos durante el ciclo de vida y expone su estado de salud y la separación entre rutas abiertas y protegidas.

## Requirements

### Requirement: Configuración leída del entorno sin secretos por defecto
La aplicación SHALL leer su configuración de variables de entorno o de un archivo `.env` no versionado. La contraseña de la base y la clave de firma de tokens MUST NOT tener valores por defecto en el código: si faltan, la aplicación no SHALL arrancar.

#### Scenario: Falta la clave de firma
- **WHEN** se inicia la aplicación sin la variable de la clave de firma
- **THEN** el arranque falla con un error de configuración y el proceso no queda atendiendo

#### Scenario: Configuración completa
- **WHEN** están definidas todas las variables requeridas
- **THEN** la aplicación arranca y expone la configuración resuelta sin credenciales impresas

### Requirement: Dirección de la base derivada de variables sueltas
La dirección de conexión SHALL armarse a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y `POSTGRES_PORT`, con el driver asincrónico de PostgreSQL, como atributo calculado y no como valor fijo.

#### Scenario: Variables sueltas definidas
- **WHEN** están definidas las cinco variables de PostgreSQL
- **THEN** la configuración expone una única dirección de base con el driver asincrónico y los componentes indicados

#### Scenario: Cambio de host
- **WHEN** cambia `POSTGRES_HOST`
- **THEN** la dirección calculada refleja el nuevo host sin modificar código

### Requirement: Recursos de base creados en el ciclo de vida
El motor asincrónico, con el tamaño de pool declarado en la configuración, y la fábrica de sesiones SHALL crearse al iniciar la aplicación y guardarse en el estado de la aplicación, nunca al importar un módulo. Al apagar, el motor SHALL liberarse con `dispose()`.

#### Scenario: Arranque
- **WHEN** la aplicación completa su inicio
- **THEN** el motor y la fábrica de sesiones están disponibles en el estado de la aplicación

#### Scenario: Apagado
- **WHEN** la aplicación se detiene
- **THEN** el motor libera sus conexiones ordenadamente

#### Scenario: Importación sin bucle de eventos
- **WHEN** se importa el módulo de la aplicación sin iniciar el servidor
- **THEN** no se crea ningún motor ni conexión a la base

### Requirement: Sesión por petición
Cada petición que necesita base de datos SHALL recibir una sesión creada desde la fábrica del estado de la aplicación, con `expire_on_commit=False`, y la sesión SHALL cerrarse al terminar la petición.

#### Scenario: Petición atendida
- **WHEN** una petición usa la dependencia de sesión
- **THEN** obtiene una sesión propia y esta se cierra al finalizar la petición

#### Scenario: Objetos tras confirmar
- **WHEN** una operación confirma la transacción y la respuesta lee atributos del objeto
- **THEN** los atributos siguen disponibles sin recargar

### Requirement: Salud viva y salud lista
La aplicación SHALL exponer `GET /health/live`, que responde 200 sin tocar la base, y `GET /health/ready`, que ejecuta una consulta mínima contra la base y responde 503 cuando esta no contesta.

#### Scenario: Proceso vivo con base caída
- **WHEN** la base no responde y se consulta `/health/live`
- **THEN** la respuesta es 200

#### Scenario: Base disponible
- **WHEN** la base responde a la consulta mínima y se consulta `/health/ready`
- **THEN** la respuesta es 200

#### Scenario: Base caída
- **WHEN** la base no responde y se consulta `/health/ready`
- **THEN** la respuesta es 503

### Requirement: Dos grupos de rutas
La aplicación SHALL montar un grupo de rutas abierto, sin sesión, y un grupo protegido con el control del cambio obligatorio de contraseña montado una sola vez. `/auth` MUST permanecer en el grupo abierto.

#### Scenario: Ruta pública
- **WHEN** se consulta el catálogo sin cookie
- **THEN** la respuesta no exige sesión

#### Scenario: Ruta protegida
- **WHEN** se consulta una ruta del grupo protegido sin cookie
- **THEN** la respuesta es 401

#### Scenario: Control único
- **WHEN** se recorre una ruta protegida con cambio de contraseña pendiente
- **THEN** el bloqueo se aplica una sola vez y no se duplica por ruta
