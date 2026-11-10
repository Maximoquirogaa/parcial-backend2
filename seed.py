"""
Seeder del parcial (capítulos 1 a 6).

Deja la base en un estado conocido y reproducible para los casos C-01 a C-16:
- Vacía TODAS las tablas con TRUNCATE ... RESTART IDENTITY CASCADE.
- Carga usuarios, roles, editoriales, géneros, autores, libros, clientes y la
  venta 1 de Lucía.
- El stock se carga SIEMPRE a través del punto único
  `app.modules.libros.service.registrar_movimiento_stock` (nunca con un UPDATE
  directo), tal como exige la consigna.

Contraseñas de mentira (viven sólo en este archivo y se documentan acá porque
los casos .http las necesitan):

    admin@example.com       -> Admin1234!
    admin2@example.com      -> Admin1234!
    vendedor@example.com    -> Vendedor1234!
    ana@example.com         -> Cliente1234!
    nuevo@example.com       -> Provisoria1234!   (debe_cambiar_password=True)

El script es idempotente: correrlo dos veces deja exactamente el mismo estado.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import init_engine_and_sessionmaker
from app.core.security import hash_password
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.service import registrar_movimiento_stock
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    Usuario,
)
from app.modules.ventas.models import RenglonVenta, Venta


# Orden explícito de todas las tablas del esquema. `CASCADE` hace que el orden
# no sea crítico, pero se listan de la más dependiente a la más independiente
# para que el TRUNCATE sea legible.
_TABLAS = (
    "movimiento_stock",
    "renglon_venta",
    "venta",
    "perfil_cliente",
    "cliente",
    "libro_autor",
    "libro",
    "autor",
    "genero",
    "editorial",
    "intento_acceso",
    "evento_seguridad",
    "asignacion_rol",
    "usuario",
)


async def seed_data() -> None:
    settings = get_settings()
    engine, session_maker = init_engine_and_sessionmaker(
        settings.database_url,
        pool_size=settings.POOL_SIZE,
        echo=settings.SQL_ECHO,
    )

    try:
        async with session_maker() as session:
            print("Iniciando carga de datos iniciales...")

            # -----------------------------------------------------------------
            # 0. Estado limpio. TRUNCATE no dispara el trigger de solo-agregado
            #    (el trigger es BEFORE UPDATE OR DELETE FOR EACH ROW).
            # -----------------------------------------------------------------
            await session.execute(
                text(
                    "TRUNCATE TABLE "
                    + ", ".join(_TABLAS)
                    + " RESTART IDENTITY CASCADE;"
                )
            )
            print("Tablas vaciadas con TRUNCATE RESTART IDENTITY CASCADE.")

            # -----------------------------------------------------------------
            # 1. Usuarios y roles
            # -----------------------------------------------------------------
            # Los hashes se calculan fuera de la transacción de escritura.
            pass_admin = await hash_password("Admin1234!")
            pass_vendedor = await hash_password("Vendedor1234!")
            pass_cliente = await hash_password("Cliente1234!")
            pass_provisoria = await hash_password("Provisoria1234!")

            admin = Usuario(
                email="admin@example.com",
                password_hash=pass_admin,
                nombre="Administrador",
                activo=True,
                debe_cambiar_password=False,
            )
            admin2 = Usuario(
                email="admin2@example.com",
                password_hash=pass_admin,
                nombre="Administrador Dos",
                activo=True,
                debe_cambiar_password=False,
            )
            vendedor = Usuario(
                email="vendedor@example.com",
                password_hash=pass_vendedor,
                nombre="Vendedor",
                activo=True,
                debe_cambiar_password=False,
            )
            ana_usuario = Usuario(
                email="ana@example.com",
                password_hash=pass_cliente,
                nombre="Ana Paz",
                activo=True,
                debe_cambiar_password=False,
            )
            nuevo = Usuario(
                email="nuevo@example.com",
                password_hash=pass_provisoria,
                nombre="Nuevo Vendedor",
                activo=True,
                debe_cambiar_password=True,
            )
            session.add_all([admin, admin2, vendedor, ana_usuario, nuevo])
            await session.flush()

            session.add_all(
                [
                    AsignacionRol(usuario_id=admin.id, rol="ADMIN"),
                    AsignacionRol(usuario_id=admin2.id, rol="ADMIN"),
                    AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR"),
                    AsignacionRol(usuario_id=ana_usuario.id, rol="CLIENTE"),
                    AsignacionRol(usuario_id=nuevo.id, rol="VENDEDOR"),
                ]
            )
            await session.flush()
            print("Usuarios y roles cargados (5 usuarios).")

            # -----------------------------------------------------------------
            # 2. Editoriales, géneros y autores del TP
            # -----------------------------------------------------------------
            ed_sudamericana = Editorial(nombre="Editorial Sudamericana", pais="Argentina")
            ed_alfaguara = Editorial(nombre="Editorial Alfaguara", pais="España")
            ed_planeta = Editorial(nombre="Editorial Planeta", pais="Argentina")
            session.add_all([ed_sudamericana, ed_alfaguara, ed_planeta])
            await session.flush()

            gen_novela = Genero(nombre="Novela")
            gen_ficcion = Genero(nombre="Ficción especulativa")
            gen_policial = Genero(nombre="Policial")
            session.add_all([gen_novela, gen_ficcion, gen_policial])
            await session.flush()

            # Los 4 autores que ya traía el seed del TP (Cortázar, Piglia,
            # Bioy Casares y Ocampo) más Borges (Ficciones/Antología) y Sábato
            # completan los 6 autores pedidos por la consigna.
            cortazar = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
            piglia = Autor(nombre="Ricardo Piglia", nacionalidad="Argentina")
            bioy = Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina")
            ocampo = Autor(nombre="Silvina Ocampo", nacionalidad="Argentina")
            borges = Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina")
            sabato = Autor(nombre="Ernesto Sábato", nacionalidad="Argentina")
            session.add_all([cortazar, piglia, bioy, ocampo, borges, sabato])
            await session.flush()
            print("Editoriales (3), géneros (3) y autores (6) cargados.")

            # -----------------------------------------------------------------
            # 3. Libros (stock inicial en 0; el stock real lo carga el punto
            #    único de movimientos más abajo).
            #    Los cinco títulos, precios y stocks son los de "Datos
            #    iniciales" de la consigna. La consigna sólo detalla los ISBN
            #    de Rayuela y Antología; los restantes siguen la misma serie
            #    978-950-00-000N-X para que el seed sea determinista.
            # -----------------------------------------------------------------
            rayuela = Libro(
                isbn="978-950-00-0001-1",
                titulo="Rayuela",
                precio=Decimal("25000.00"),
                stock=0,
                editorial_id=ed_sudamericana.id,
                genero_id=gen_novela.id,
            )
            antologia = Libro(
                isbn="978-950-00-0002-8",
                titulo="Antología de la literatura fantástica",
                precio=Decimal("30000.00"),
                stock=0,
                editorial_id=ed_sudamericana.id,
                genero_id=gen_ficcion.id,
            )
            ficciones = Libro(
                isbn="978-950-00-0003-6",
                titulo="Ficciones",
                precio=Decimal("22000.00"),
                stock=0,
                editorial_id=ed_sudamericana.id,
                genero_id=gen_ficcion.id,
            )
            respiracion = Libro(
                isbn="978-950-00-0004-4",
                titulo="Respiración artificial",
                precio=Decimal("27000.00"),
                stock=0,
                editorial_id=ed_alfaguara.id,
                genero_id=gen_novela.id,
            )
            bestiario = Libro(
                isbn="978-950-00-0005-2",
                titulo="Bestiario",
                precio=Decimal("19000.00"),
                stock=0,
                editorial_id=ed_planeta.id,
                genero_id=gen_ficcion.id,
            )
            session.add_all([rayuela, antologia, ficciones, respiracion, bestiario])
            await session.flush()

            session.add_all(
                [
                    LibroAutor(libro_id=rayuela.id, autor_id=cortazar.id, rol="autor", orden=1),
                    LibroAutor(libro_id=antologia.id, autor_id=borges.id, rol="coautor", orden=1),
                    LibroAutor(libro_id=antologia.id, autor_id=bioy.id, rol="coautor", orden=2),
                    LibroAutor(libro_id=antologia.id, autor_id=ocampo.id, rol="coautor", orden=3),
                    LibroAutor(libro_id=ficciones.id, autor_id=borges.id, rol="autor", orden=1),
                    LibroAutor(libro_id=respiracion.id, autor_id=piglia.id, rol="autor", orden=1),
                    LibroAutor(libro_id=bestiario.id, autor_id=cortazar.id, rol="autor", orden=1),
                ]
            )
            await session.flush()
            print("Libros (5) y autorías cargados.")

            # -----------------------------------------------------------------
            # 4. Clientes
            # -----------------------------------------------------------------
            lucia = Cliente(nombre="Lucía Fernández", email="lucia@example.com")
            tomas = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
            ana_cliente = Cliente(
                nombre="Ana Paz",
                email="ana@example.com",
                usuario_id=ana_usuario.id,
            )
            session.add_all([lucia, tomas, ana_cliente])
            await session.flush()

            session.add(
                PerfilCliente(
                    cliente_id=lucia.id,
                    telefono="+54 11 4555-1234",
                    direccion="Av. Corrientes 1234, CABA",
                )
            )
            await session.flush()
            print("Clientes (3) y perfil de Lucía cargados.")

            # -----------------------------------------------------------------
            # 5. Stock inicial por el PUNTO ÚNICO de mutación.
            #    Rayuela 11 y Ficciones 10 porque la venta 1 descuenta 1 y 2
            #    respectivamente, dejando el stock final de la consigna.
            # -----------------------------------------------------------------
            stock_inicial = (
                (rayuela, 11),
                (antologia, 5),
                (ficciones, 10),
                (respiracion, 3),
                (bestiario, 1),
            )
            for libro, cantidad in stock_inicial:
                await registrar_movimiento_stock(
                    session,
                    libro=libro,
                    cantidad=cantidad,
                    motivo="Stock inicial",
                )
            print("Stock inicial registrado mediante registrar_movimiento_stock.")

            # -----------------------------------------------------------------
            # 6. Venta 1: Lucía, registrada por vendedor@example.com.
            #    1 Rayuela (25000.00) + 2 Ficciones (22000.00) = 69000.00
            # -----------------------------------------------------------------
            venta = Venta(
                cliente_id=lucia.id,
                total=Decimal("69000.00"),
            )
            session.add(venta)
            await session.flush()

            session.add_all(
                [
                    RenglonVenta(
                        venta_id=venta.id,
                        libro_id=rayuela.id,
                        cantidad=1,
                        precio_unitario=rayuela.precio,
                    ),
                    RenglonVenta(
                        venta_id=venta.id,
                        libro_id=ficciones.id,
                        cantidad=2,
                        precio_unitario=ficciones.precio,
                    ),
                ]
            )
            await session.flush()

            # La salida de stock también pasa por el punto único.
            await registrar_movimiento_stock(
                session,
                libro=rayuela,
                cantidad=-1,
                motivo="Venta",
                venta_id=venta.id,
                usuario_id=vendedor.id,
            )
            await registrar_movimiento_stock(
                session,
                libro=ficciones,
                cantidad=-2,
                motivo="Venta",
                venta_id=venta.id,
                usuario_id=vendedor.id,
            )
            print("Venta 1 (Lucía) y sus movimientos de salida cargados.")

            # -----------------------------------------------------------------
            # 7. Historial de seguridad: actor SISTEMA.
            # -----------------------------------------------------------------
            session.add(
                EventoSeguridad(
                    tipo="carga_datos_iniciales",
                    usuario_afectado_id=None,
                    actor_id=None,
                    actor_tipo="SISTEMA",
                    detalle="Carga de los datos iniciales",
                )
            )
            await session.flush()

            # Chequeo defensivo: stock == suma de movimientos en los 5 libros.
            for libro, _ in stock_inicial:
                stmt = text(
                    "SELECT COALESCE(SUM(cantidad), 0) "
                    "FROM movimiento_stock WHERE libro_id = :libro_id"
                )
                suma = (await session.execute(stmt, {"libro_id": libro.id})).scalar_one()
                if suma != libro.stock:
                    raise RuntimeError(
                        f"Inconsistencia de stock en el libro {libro.id}: "
                        f"stock={libro.stock}, suma_movimientos={suma}"
                    )

            await session.commit()
            print("Datos iniciales cargados exitosamente.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
