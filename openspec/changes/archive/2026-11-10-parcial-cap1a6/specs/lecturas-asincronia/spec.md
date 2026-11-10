# Spec Delta

## Purpose

Define cómo se leen las relaciones sin caer en N+1, cómo se garantiza un número fijo de consultas en el detalle de una venta y cómo se ejecuta el trabajo diferido sin bloquear la respuesta.

## ADDED Requirements

### Requirement: Carga anticipada declarada en el repositorio
Toda respuesta que incluya datos de una relación SHALL obtenerlos con carga anticipada declarada en el método del repositorio que los necesita. Ninguna lectura SHALL depender de la carga perezosa.

#### Scenario: Listado con relación
- **WHEN** se lista una entidad que expone datos de una relación
- **THEN** la consulta del repositorio precarga esa relación y no se dispara una consulta por fila

#### Scenario: Lazy loading prohibido
- **WHEN** se revisa el código de lectura
- **THEN** ninguna respuesta depende de que una relación se cargue al acceder al atributo

#### Scenario: Cantidad de consultas estable
- **WHEN** aumenta la cantidad de filas de una relación precargada
- **THEN** la cantidad de consultas de la lectura no aumenta con las filas

### Requirement: Detalle de venta con consultas fijas
El detalle de una venta SHALL incluir su cliente, sus renglones y el libro de cada renglón, incluso si el libro está dado de baja, y SHALL resolverse con un número fijo de consultas que no crece con la cantidad de renglones.

#### Scenario: Venta con dos renglones
- **WHEN** se consulta el detalle de una venta con dos renglones
- **THEN** se emite una cantidad determinada de consultas

#### Scenario: Venta con cuatro renglones
- **WHEN** se consulta el detalle de una venta con cuatro renglones
- **THEN** se emite la misma cantidad de consultas que con dos renglones

#### Scenario: Libro dado de baja en el detalle
- **WHEN** uno de los libros de la venta está dado de baja
- **THEN** el detalle igualmente muestra su título y datos

#### Scenario: Cliente inexistente en el detalle
- **WHEN** se consulta una venta inexistente
- **THEN** la respuesta es 404

### Requirement: Handlers asincrónicos sin bloqueo
Todos los handlers SHALL ser `async def` y MUST NOT ejecutar llamadas bloqueantes dentro del bucle de eventos.

#### Scenario: Handler asincrónico
- **WHEN** se inspeccionan los handlers de la aplicación
- **THEN** todos están declarados como `async def`

#### Scenario: Operación costosa
- **WHEN** una operación requiere trabajo de CPU o de una biblioteca bloqueante, como bcrypt
- **THEN** se ejecuta fuera del bucle y el servidor sigue atendiendo otras peticiones

### Requirement: Aviso de comprobante en segundo plano
Al registrar una venta exitosa, la API SHALL agendar con `BackgroundTasks` el aviso del comprobante al cliente. El aviso SHALL simularse con una espera asíncrona y un mensaje de registro que se vea en la consola con el arranque normal del servidor, y SHALL ejecutarse después de enviar la respuesta y sólo si la operación se confirmó.

#### Scenario: Aviso tras la respuesta
- **WHEN** se registra una venta válida
- **THEN** la respuesta se envía primero y el mensaje del aviso aparece después en la consola

#### Scenario: Mensaje visible
- **WHEN** se arranca el servidor con el comando normal y se registra una venta
- **THEN** el mensaje del aviso es visible en la consola con la configuración de registro por defecto

#### Scenario: Operación fallida
- **WHEN** el registro de la venta falla y se revierte
- **THEN** no se agenda ni se ejecuta el aviso
