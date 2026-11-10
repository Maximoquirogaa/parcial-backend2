# integridad Specification

## Purpose
Define las garantías de integridad que impone la base de datos y las reglas de transacción de las dos escrituras de auditoría: los intentos de acceso y los eventos de seguridad.

## Requirements

### Requirement: Movimientos de stock de sólo agregado
La base SHALL rechazar cualquier `UPDATE` o `DELETE` sobre `movimiento_stock` mediante un disparador instalado por migración, sin importar el origen de la sentencia.

#### Scenario: Update directo
- **WHEN** se ejecuta un `UPDATE` sobre `movimiento_stock` desde psql
- **THEN** la base rechaza la sentencia con un error

#### Scenario: Delete directo
- **WHEN** se ejecuta un `DELETE` sobre `movimiento_stock` desde psql
- **THEN** la base rechaza la sentencia con un error

#### Scenario: Inserciones permitidas
- **WHEN** se inserta un movimiento nuevo
- **THEN** la escritura se acepta

#### Scenario: Disparador reversible
- **WHEN** se ejecuta el downgrade de la migración del disparador
- **THEN** el disparador y su función se eliminan

### Requirement: Intento de acceso en transacción propia
Cada intento de login, correcto o fallido, SHALL registrarse en `intento_acceso` usando una sesión y una transacción propias que se confirman siempre, independientes de la transacción de la petición. El código SHALL documentar qué hace distinto, por qué no puede compartir la transacción y su costo.

#### Scenario: Login fallido
- **WHEN** un login falla y la transacción de la petición se revierte
- **THEN** el intento fallido queda registrado en `intento_acceso`

#### Scenario: Login exitoso
- **WHEN** un login es exitoso
- **THEN** el intento exitoso también queda registrado

#### Scenario: Justificación documentada
- **WHEN** se lee el código que registra el intento
- **THEN** el comentario explica las tres cosas: qué hace distinto, por qué no comparte la transacción y que deja filas aunque la petición falle

#### Scenario: Costo aceptado
- **WHEN** la petición falla después de registrar el intento
- **THEN** la fila del intento permanece, como se declara en el comentario

### Requirement: Eventos de seguridad en la transacción del cambio
Los eventos de seguridad de altas de personal, cambios de rol y cambios de contraseña SHALL escribirse en la misma transacción que el cambio que los origina y MUST NOT usar una transacción propia.

#### Scenario: Cambio exitoso
- **WHEN** se completa un alta de personal o un cambio de rol
- **THEN** el evento y el cambio quedan confirmados juntos

#### Scenario: Cambio revertido
- **WHEN** el cambio se revierte
- **THEN** el evento tampoco queda persistido

### Requirement: Restricciones como garantía de unicidad
Las unicidades y reglas de negocio que la base puede garantizar SHALL imponerse con restricciones e índices, sin depender de una consulta previa que verifique duplicados.

#### Scenario: Alta duplicada concurrente
- **WHEN** dos altas con el mismo dato único llegan casi a la vez
- **THEN** la base rechaza una de las dos y la API la traduce a 409

#### Scenario: Sin verificación previa
- **WHEN** se revisa el servicio de alta
- **THEN** no existe una consulta de existencia usada como única defensa contra el duplicado
