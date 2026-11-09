"""
Script de inicialización de datos base (Seeder) para la base de datos PostgreSQL.
Carga editoriales, géneros, autores, libros y clientes para que las pruebas .http
puedan ejecutarse de manera predecible y reproducible.
"""
import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import DATABASE_URL
from app.core.database import init_engine_and_sessionmaker
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta



async def seed_data():
    engine, session_maker = init_engine_and_sessionmaker(DATABASE_URL, echo=False)

    async with session_maker() as session:
        # Verificar si ya existen datos para evitar duplicaciones
        existing_editorial = (await session.execute(select(Editorial))).first()
        if existing_editorial:
            print("La base de datos ya contiene registros. Limpiando para estado inicial...")
            # Borrar en orden inverso de dependencias
            await session.execute(select(LibroAutor))
            # Para garantizar estado conocido, eliminamos datos existentes
            from sqlalchemy import text
            await session.execute(text("TRUNCATE TABLE renglon_venta, venta, perfil_cliente, cliente, libro_autor, libro, autor, genero, editorial RESTART IDENTITY CASCADE;"))
            await session.commit()
            session.expunge_all()
            print("Tablas truncadas exitosamente.")

        print("Cargando datos semilla...")

        # 1. Editoriales
        ed1 = Editorial(nombre="Editorial Sudamericana", pais="Argentina")
        ed2 = Editorial(nombre="Editorial Alfaguara", pais="España")
        ed3 = Editorial(nombre="Editorial Planeta", pais="Argentina")
        session.add_all([ed1, ed2, ed3])
        await session.flush()

        # 2. Géneros
        gen1 = Genero(nombre="Novela")
        gen2 = Genero(nombre="Ficción especulativa")
        gen3 = Genero(nombre="Policial")
        session.add_all([gen1, gen2, gen3])
        await session.flush()

        # 3. Autores
        aut1 = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
        aut2 = Autor(nombre="Ricardo Piglia", nacionalidad="Argentina")
        aut3 = Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina")
        aut4 = Autor(nombre="Silvina Ocampo", nacionalidad="Argentina")
        session.add_all([aut1, aut2, aut3, aut4])
        await session.flush()

        # 4. Libros
        lib1 = Libro(
            isbn="978-950-07-0001-1",
            titulo="Rayuela",
            precio=Decimal("25000.00"),
            stock=15,
            editorial_id=ed1.id,
            genero_id=gen1.id,
        )
        lib2 = Libro(
            isbn="978-950-07-0002-2",
            titulo="Respiración artificial",
            precio=Decimal("27000.00"),
            stock=8,
            editorial_id=ed2.id,
            genero_id=gen1.id,
        )
        lib3 = Libro(
            isbn="978-950-07-0003-3",
            titulo="Los que aman, odian",
            precio=Decimal("21000.00"),
            stock=12,
            editorial_id=ed3.id,
            genero_id=gen3.id,
        )
        session.add_all([lib1, lib2, lib3])
        await session.flush()

        # 5. Autorías (Muchos a Muchos con rol y orden)
        la1 = LibroAutor(libro_id=lib1.id, autor_id=aut1.id, rol="autor", orden=1)
        la2 = LibroAutor(libro_id=lib2.id, autor_id=aut2.id, rol="autor", orden=1)
        la3 = LibroAutor(libro_id=lib3.id, autor_id=aut3.id, rol="coautor", orden=1)
        la4 = LibroAutor(libro_id=lib3.id, autor_id=aut4.id, rol="coautor", orden=2)
        session.add_all([la1, la2, la3, la4])

        # 6. Clientes
        cli1 = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
        cli2 = Cliente(nombre="Lucía Beltrán", email="lucia@example.com")
        session.add_all([cli1, cli2])

        await session.commit()
        print("Datos iniciales cargados exitosamente.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
