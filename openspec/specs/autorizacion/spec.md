# autorizacion Specification

## Purpose
Define cómo la API identifica al usuario de cada petición, decide permisos con los roles vigentes en la base, administra las asignaciones de rol y protege el acceso a lo propio y el cambio obligatorio de contraseña.

## Requirements

### Requirement: Identidad de la petición
La dependencia de usuario actual SHALL responder 401 si no hay cookie, si el token es inválido o venció, o si el usuario no existe o está inactivo.

#### Scenario: Sin cookie
- **WHEN** una ruta autenticada recibe una petición sin cookie
- **THEN** la respuesta es 401

#### Scenario: Token inválido o vencido
- **WHEN** la cookie trae un token con firma inválida o vencido
- **THEN** la respuesta es 401

#### Scenario: Usuario inactivo
- **WHEN** el token es válido pero el usuario fue desactivado
- **THEN** la respuesta es 401

### Requirement: Permisos con roles vigentes en la base
La verificación de rol SHALL consultar en cada petición las asignaciones vigentes —no revocadas y sin vencer— del usuario y SHALL responder 403 cuando ninguna lo autoriza. Los roles del token MUST NOT conceder permisos por sí solos.

#### Scenario: Rol revocado con sesión abierta
- **WHEN** se revoca un rol y el usuario vuelve a llamar a una ruta protegida con la misma cookie
- **THEN** la respuesta es 403 en la siguiente petición

#### Scenario: Rol del token no vigente
- **WHEN** el token declara un rol que ya no está vigente en la base
- **THEN** el permiso se deniega

#### Scenario: Rol vigente
- **WHEN** el usuario tiene una asignación vigente del rol requerido
- **THEN** la petición continúa

### Requirement: Administración de asignaciones de rol
El administrador SHALL poder asignar un rol con vencimiento opcional y revocarlo sin borrar la fila. Reasignar un rol vencido SHALL cerrar la fila anterior y abrir una nueva. Un vencimiento en el pasado o sin zona horaria SHALL responder 422.

#### Scenario: Asignación con vencimiento futuro
- **WHEN** el administrador asigna un rol con una fecha futura con zona horaria
- **THEN** la respuesta es 201 y la asignación queda vigente hasta esa fecha

#### Scenario: Vencimiento en el pasado
- **WHEN** se envía un vencimiento anterior al momento actual
- **THEN** la respuesta es 422

#### Scenario: Vencimiento sin zona horaria
- **WHEN** se envía un vencimiento sin zona horaria
- **THEN** la respuesta es 422

#### Scenario: Reasignar un rol vencido
- **WHEN** se asigna un rol cuya fila anterior ya venció
- **THEN** la fila anterior se cierra y se crea una nueva

#### Scenario: Revocar un rol
- **WHEN** el administrador revoca un rol
- **THEN** la fila queda con fecha de revocación y no se borra

#### Scenario: Rol ya asignado
- **WHEN** se intenta abrir una segunda asignación vigente del mismo rol
- **THEN** la respuesta es 409

### Requirement: Autoprotección del administrador
Un administrador MUST NOT poder revocarse su propio rol ADMIN, y el sistema MUST NOT quedar sin administradores vigentes. La violación SHALL responder 409.

#### Scenario: Auto-revocación
- **WHEN** un administrador intenta revocar su propia asignación ADMIN
- **THEN** la respuesta es 409 y la asignación sigue vigente

#### Scenario: Último administrador
- **WHEN** una operación dejaría al sistema sin ningún ADMIN vigente
- **THEN** la respuesta es 409 y no se aplica

### Requirement: Cambio obligatorio de contraseña
Mientras el usuario tenga `debe_cambiar_password` en verdadero, SHALL poder usar sólo las rutas de `/auth` y las que no piden sesión; cualquier otra ruta protegida SHALL responder 403.

#### Scenario: Bloqueo con cambio pendiente
- **WHEN** un usuario con cambio pendiente llama a una ruta protegida que no es de `/auth`
- **THEN** la respuesta es 403

#### Scenario: Rutas abiertas con cambio pendiente
- **WHEN** el mismo usuario llama a `/auth` o al catálogo público
- **THEN** la petición se atiende

#### Scenario: Después del cambio
- **WHEN** el usuario cambia su contraseña
- **THEN** `debe_cambiar_password` queda en falso y la misma cookie sirve para las rutas protegidas sin volver a iniciar sesión

### Requirement: Acceso a lo propio
Un cliente autenticado SHALL poder ver sus propias ventas y ninguna ajena. `GET /mis-ventas` SHALL pedir sólo autenticación y devolver las ventas del usuario. El detalle de una venta SHALL autorizar al personal o al cliente dueño, y responder 403 a cualquier otro autenticado.

#### Scenario: Cliente ve su venta
- **WHEN** un cliente autenticado consulta el detalle de una venta propia
- **THEN** la respuesta es 200

#### Scenario: Cliente ve una venta ajena
- **WHEN** un cliente autenticado consulta el detalle de una venta de otro cliente
- **THEN** la respuesta es 403

#### Scenario: Mis ventas
- **WHEN** un cliente consulta `/mis-ventas`
- **THEN** la respuesta incluye sólo sus ventas

#### Scenario: Personal ve cualquier venta
- **WHEN** un vendedor o administrador consulta el detalle de una venta
- **THEN** la respuesta es 200

#### Scenario: Detalle inexistente
- **WHEN** se consulta el detalle de una venta que no existe
- **THEN** la respuesta es 404

### Requirement: Registro de eventos de seguridad
Cada alta de personal, cambio de rol y cambio de contraseña SHALL registrar una línea en `evento_seguridad` dentro de la misma transacción que el cambio. Los datos iniciales SHALL registrar una línea con el actor SISTEMA, que es un texto y no un usuario.

#### Scenario: Alta de personal
- **WHEN** el administrador da de alta a un usuario del personal
- **THEN** queda una línea de evento con el actor correspondiente en la misma transacción

#### Scenario: Fallo del cambio
- **WHEN** el cambio de rol falla y la transacción se revierte
- **THEN** no queda ninguna línea de evento de ese cambio

#### Scenario: Carga inicial
- **WHEN** se ejecutan los datos iniciales
- **THEN** existe una línea de evento con actor SISTEMA que describe la carga
