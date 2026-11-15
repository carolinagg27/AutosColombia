"""Restauración segura de una copia de SQLite con el servidor detenido.

Uso en Windows:
    python restaurar_respaldo.py "C:\\Users\\usuario\\Downloads\\autos_colombia_respaldo.db"

Antes de sustituir, se crea una copia preventiva y se verifica la copia nueva.
"""
import argparse
from datetime import datetime
import os
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile

from app.utils.backup import verificar_archivo_respaldo


def _copiar_sqlite(origen, destino):
    conexion_origen = sqlite3.connect(str(origen), timeout=15)
    conexion_destino = sqlite3.connect(str(destino), timeout=15)
    try:
        conexion_origen.backup(conexion_destino)
    finally:
        conexion_destino.close()
        conexion_origen.close()


def restaurar(archivo, destino=None):
    fuente = Path(archivo).resolve()
    destino = (Path(destino).resolve() if destino else
               Path(__file__).resolve().parent / "instance" / "autos_colombia.db")
    resumen = verificar_archivo_respaldo(fuente)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if fuente == destino:
        raise ValueError("El respaldo debe ser un archivo diferente de la base activa.")
    # Debe quedar totalmente cerrado el servidor y cualquier otro proceso
    # con acceso a la base de datos para evitar archivos WAL obsoletos.
    auxiliares = [Path(str(destino) + sufijo) for sufijo in ('-wal', '-shm')]
    if any(p.exists() for p in auxiliares):
        raise ValueError("Hay archivos WAL/SHM de la base activa. Cierra el servidor "
                         "y confirma su cierre antes de restaurar.")
    if destino.is_file():
        copia = destino.with_name(f"autos_colombia_antes_{datetime.now():%Y%m%d_%H%M%S_%f}.db")
        _copiar_sqlite(destino, copia)
        verificar_archivo_respaldo(copia)
        print(f"Copia preventiva: {copia}")
    with NamedTemporaryFile(prefix=".restauracion_", suffix=".db",
                            dir=destino.parent, delete=False) as fichero:
        temporal = Path(fichero.name)
    try:
        _copiar_sqlite(fuente, temporal)
        if verificar_archivo_respaldo(temporal) != resumen:
            raise ValueError("La restauración no conserva los conteos de registros.")
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
    verificar_archivo_respaldo(destino)
    return destino, resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restaurar respaldo de Autos Colombia")
    parser.add_argument("archivo", help="Ruta al archivo .db descargado")
    args = parser.parse_args()
    print("IMPORTANTE: detén la aplicación antes de restaurar.")
    confirmacion = input("¿Confirmas que el servidor está detenido? Escribe SI: ")
    if confirmacion != "SI":
        raise SystemExit("Restauración cancelada.")
    ruta, tablas = restaurar(args.archivo)
    print(f"Restauración verificada: {ruta}")
    print("Registros por tabla:", tablas)
