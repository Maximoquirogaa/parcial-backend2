-- C-14: Verificación del disparador de solo-agregado sobre movimiento_stock
-- Comprobación de que UPDATE y DELETE son rechazados por el disparador PL/pgSQL

-- 1. Intentar actualizar un movimiento de stock existente (debe fallar con restrict_violation)
UPDATE movimiento_stock
SET cantidad = 999
WHERE id = 1;
-- Resultado esperado:
-- ERROR: La tabla movimiento_stock es de solo agregado: no se permiten operaciones de UPDATE ni DELETE.

-- 2. Intentar borrar un movimiento de stock existente (debe fallar con restrict_violation)
DELETE FROM movimiento_stock
WHERE id = 1;
-- Resultado esperado:
-- ERROR: La tabla movimiento_stock es de solo agregado: no se permiten operaciones de UPDATE ni DELETE.
