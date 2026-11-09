"""
Script ejecutor automatizado de verificación para los casos C-01 a C-08.
Permite validar toda la suite de pruebas y observar en consola las consultas SQL emitidas (C-07).
"""
import asyncio
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from httpx import AsyncClient, ASGITransport
from app.main import app, lifespan



async def run_all_tests():
    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000") as client:
            print("\n" + "="*70)
            print(" INICIANDO EJECUCIÓN DE CASOS DE PRUEBA C-01 A C-08")
            print("="*70 + "\n")

            # C-01: Parámetro de ruta no entero -> 422
            res = await client.get("/editoriales/no-es-entero")
            print(f"[C-01] Parámetro no entero: Status {res.status_code} (Esperado 422)")
            assert res.status_code == 422

            # C-02A: Email repetido -> 409
            res = await client.post("/clientes/", json={"nombre": "Test", "email": "tomas@example.com"})
            print(f"[C-02A] Email duplicado: Status {res.status_code} (Esperado 409) -> {res.json()['detail']}")
            assert res.status_code == 409

            # C-02B: ISBN repetido -> 409
            res = await client.post("/libros/", json={
                "isbn": "978-950-07-0001-1",
                "titulo": "Test Clon",
                "precio": "100.00",
                "stock": 1,
                "editorial_id": 1,
                "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}]
            })
            print(f"[C-02B] ISBN duplicado: Status {res.status_code} (Esperado 409) -> {res.json()['detail']}")
            assert res.status_code == 409

            # C-03: Segundo perfil para el mismo cliente -> 409
            res1 = await client.post("/clientes/1/perfil", json={"telefono": "1144556677", "direccion": "Av. Corrientes 1234"})
            print(f"[C-03] Primer perfil cliente 1: Status {res1.status_code} (Esperado 201)")
            assert res1.status_code == 201

            res2 = await client.post("/clientes/1/perfil", json={"telefono": "1199887766", "direccion": "Calle Falsa 123"})
            print(f"[C-03] Segundo perfil cliente 1: Status {res2.status_code} (Esperado 409) -> {res2.json()['detail']}")
            assert res2.status_code == 409

            # C-04: Editorial o autor inexistente -> 409
            res = await client.post("/libros/", json={
                "isbn": "978-000-00-0000-0",
                "titulo": "Inexistente",
                "precio": "100.00",
                "stock": 1,
                "editorial_id": 9999,
                "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}]
            })
            print(f"[C-04] Editorial inexistente: Status {res.status_code} (Esperado 409) -> {res.json()['detail']}")
            assert res.status_code == 409

            # C-05: Venta con libro inexistente -> 409
            res = await client.post("/ventas/", json={
                "cliente_id": 1,
                "renglones": [{"libro_id": 9999, "cantidad": 1}]
            })
            print(f"[C-05] Venta libro inexistente: Status {res.status_code} (Esperado 409) -> {res.json()['detail']}")
            assert res.status_code == 409

            # C-06: Venta válida con dos renglones -> 201 y total calculado
            res_v = await client.post("/ventas/", json={
                "cliente_id": 1,
                "renglones": [
                    {"libro_id": 1, "cantidad": 2},
                    {"libro_id": 2, "cantidad": 1}
                ]
            })
            print(f"[C-06] Venta válida: Status {res_v.status_code} (Esperado 201)")
            assert res_v.status_code == 201
            v_data = res_v.json()
            print(f"       Total calculado por servidor: ${v_data['total']} (Esperado 77000.00)")
            assert v_data["total"] == "77000.00"
            venta_id = v_data["id"]

            # C-07: Detalle de libro y de venta (Consultas fijas sin N+1)
            print("\n" + "-"*50)
            print("[C-07A] EMITIENDO CONSULTA DETALLE DE LIBRO (id=3 con 2 autores):")
            print("-"*50)
            res_l3 = await client.get("/libros/3")
            assert res_l3.status_code == 200
            print(f"       Detalle libro obtenido OK: {res_l3.json()['titulo']}")

            print("\n" + "-"*50)
            print(f"[C-07B] EMITIENDO CONSULTA DETALLE DE VENTA (id={venta_id} con 2 renglones):")
            print("-"*50)
            res_v_det = await client.get(f"/ventas/{venta_id}")
            assert res_v_det.status_code == 200
            print(f"       Detalle venta obtenido OK: Total ${res_v_det.json()['total']}")

            # C-08: Búsqueda con inyección SQL (' OR '1'='1) -> 200 con lista vacía
            res_sqli = await client.get("/libros/?titulo=%27%20OR%20%271%27%3D%271")
            print(f"\n[C-08] Búsqueda con SQL Injection (' OR '1'='1): Status {res_sqli.status_code} (Esperado 200)")
            print(f"       Resultados retornados: {res_sqli.json()} (Esperado lista vacía [])")
            assert res_sqli.status_code == 200
            assert res_sqli.json() == []

            print("\n" + "="*70)
            print(" ¡TODOS LOS CASOS DE PRUEBA C-01 A C-08 FINALIZARON EXITOSAMENTE!")
            print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
