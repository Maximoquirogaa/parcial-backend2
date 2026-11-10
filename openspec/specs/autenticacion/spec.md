# autenticacion Specification

## Purpose
Define cómo se registran, autentican y mantienen sesión los usuarios: almacenamiento seguro de contraseñas, login resistente a enumeración y fuerza bruta, y transporte del token en una cookie HttpOnly.

## Requirements

### Requirement: Registro atómico de cliente
El auto-registro SHALL crear en una sola unidad de trabajo el usuario, su asignación de rol CLIENTE y su ficha de cliente. Si ya existe un cliente con ese correo, SHALL responder 409 y no apropiarse de la ficha existente ni dejar filas sueltas.

#### Scenario: Registro exitoso
- **WHEN** se registra un correo nuevo con datos válidos
- **THEN** la respuesta es 201 y existen las tres filas: usuario, rol CLIENTE y cliente

#### Scenario: Correo de cliente ya existente
- **WHEN** se registra un correo que ya pertenece a un cliente
- **THEN** la respuesta es 409 con mensaje propio y no se crea ninguna fila nueva

#### Scenario: Correo de usuario ya existente
- **WHEN** se registra un correo que ya pertenece a un usuario
- **THEN** la respuesta es 409 con mensaje propio y no se crea ninguna fila nueva

#### Scenario: Fallo a mitad del registro
- **WHEN** una de las tres escrituras del registro falla
- **THEN** ninguna de las tres queda persistida

### Requirement: Contraseñas con bcrypt no bloqueante
Las contraseñas SHALL almacenarse con bcrypt usando un costo tomado de la configuración. Toda llamada a bcrypt SHALL ejecutarse fuera del bucle de eventos, en un hilo, bajo un semáforo que limite la concurrencia. El hash SHALL calcularse antes de abrir la transacción.

#### Scenario: Costo configurable
- **WHEN** cambia el costo declarado en la configuración
- **THEN** los hashes nuevos se generan con ese costo sin modificar código

#### Scenario: Concurrencia limitada
- **WHEN** llegan varias peticiones que requieren hash a la vez
- **THEN** sólo el número permitido se ejecuta simultáneamente y el bucle de eventos sigue atendiendo otras peticiones

#### Scenario: Transacción no retenida
- **WHEN** se registra o cambia una contraseña
- **THEN** el cálculo del hash ocurre antes de que la transacción tome la conexión

### Requirement: Límite de 72 bytes en contraseñas
Todo campo que llegue a bcrypt —registro, login y contraseña actual del cambio— SHALL aceptar como máximo 72 bytes y SHALL validarse en bytes, no en caracteres.

#### Scenario: Contraseña dentro del límite
- **WHEN** se envía una contraseña de hasta 72 bytes
- **THEN** la validación del contrato la acepta

#### Scenario: Contraseña demasiado larga
- **WHEN** se envía una contraseña de más de 72 bytes o con caracteres multibyte que superan ese total
- **THEN** la respuesta es 422 y no se llega a bcrypt

### Requirement: Orden del login y límite de intentos
El login SHALL evaluar primero el límite de intentos; si se superó, SHALL responder 429 con `Retry-After` sin calcular ningún hash. Superado ese control, SHALL verificar la contraseña contra el usuario o contra un hash ficticio si el correo no existe.

#### Scenario: Sexto intento fallido
- **WHEN** se acumulan cinco intentos fallidos del mismo correo desde la misma IP en 60 segundos y llega el sexto
- **THEN** la respuesta es 429 con `Retry-After` y se resuelve en pocos milisegundos

#### Scenario: Login correcto reinicia el conteo
- **WHEN** un login correcto ocurre después de fallos previos
- **THEN** los fallos siguen registrados pero dejan de contar para el límite

#### Scenario: Límite por correo e IP
- **WHEN** los fallos provienen de otra IP o de otro correo
- **THEN** no afectan el conteo de este correo y esta IP

### Requirement: Login indistinguible
El login SHALL responder el mismo cuerpo y un tiempo comparable exista o no el correo, y exista o no la contraseña correcta.

#### Scenario: Correo inexistente
- **WHEN** se intenta iniciar sesión con un correo que no existe
- **THEN** la respuesta es 401 con el mismo cuerpo que un fallo de contraseña y un tiempo parecido

#### Scenario: Contraseña incorrecta
- **WHEN** se intenta iniciar sesión con un correo existente y contraseña incorrecta
- **THEN** la respuesta es 401 con el mismo cuerpo y un tiempo parecido

### Requirement: Token en cookie HttpOnly
El login exitoso SHALL emitir un JWT firmado con sujeto, vencimiento y roles vigentes, y SHALL enviarlo sólo en una cookie `access_token` con `HttpOnly`, `SameSite=Lax`, `Max-Age` igual a la duración del token y `Secure` configurable. El cuerpo de la respuesta MUST NOT contener el token. La autenticación SHALL leerse sólo de la cookie.

#### Scenario: Set-Cookie del login
- **WHEN** un login es exitoso
- **THEN** la respuesta incluye `Set-Cookie` con HttpOnly, SameSite Lax y Max-Age, y el cuerpo no contiene el token

#### Scenario: Sin cookie
- **WHEN** se llama a una ruta autenticada sin cookie
- **THEN** la respuesta es 401

#### Scenario: Token por cabecera
- **WHEN** se envía `Authorization: Bearer <token>` sin cookie
- **THEN** la respuesta es 401, porque el token no se lee de la cabecera

#### Scenario: Secure configurable
- **WHEN** la configuración indica cookie segura
- **THEN** la cookie se emite con el atributo correspondiente

### Requirement: Consulta de la sesión actual
`GET /auth/yo` SHALL devolver el usuario autenticado, sus roles vigentes en la base y los roles que declara el token.

#### Scenario: Sesión válida
- **WHEN** se consulta `/auth/yo` con una cookie válida
- **THEN** la respuesta incluye los datos del usuario, sus roles vigentes y los roles del token

#### Scenario: Rol revocado
- **WHEN** un rol se revoca y se vuelve a consultar `/auth/yo` con la misma cookie
- **THEN** la lista de roles vigentes ya no lo incluye y la de roles del token sí

### Requirement: Cierre de sesión
`POST /auth/logout` SHALL borrar la cookie de sesión y responder 200.

#### Scenario: Logout
- **WHEN** se cierra la sesión
- **THEN** la respuesta es 200 y la cookie queda borrada

#### Scenario: Reutilizar la cookie cerrada
- **WHEN** se intenta usar la cookie anterior después del logout
- **THEN** el cliente ya no la envía y las rutas autenticadas responden 401

### Requirement: Cambio de contraseña
`POST /auth/cambiar-password` SHALL exigir sesión, validar la contraseña actual, aceptar la nueva con el límite de 72 bytes, actualizar el hash y dejar `debe_cambiar_password` en falso. SHALL responder 401 sin sesión y 422 ante datos inválidos.

#### Scenario: Cambio exitoso
- **WHEN** un usuario autenticado envía su contraseña actual correcta y una nueva válida
- **THEN** la respuesta es 200, el hash se actualiza y `debe_cambiar_password` queda en falso

#### Scenario: Contraseña actual incorrecta
- **WHEN** la contraseña actual no coincide
- **THEN** la respuesta es 401 y el hash no cambia

#### Scenario: Sin sesión
- **WHEN** se llama al cambio sin cookie
- **THEN** la respuesta es 401

#### Scenario: Nueva contraseña inválida
- **WHEN** la nueva contraseña supera 72 bytes o no cumple el contrato
- **THEN** la respuesta es 422 y el hash no cambia
