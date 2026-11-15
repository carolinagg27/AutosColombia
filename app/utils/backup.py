"""Respaldo íntegro de SQLite (Windows y Linux) mediante SQLite Backup API.

No se sirve un archivo temporal abierto: los manejadores se cierran antes de que
Flask genere la respuesta de descarga. Se comprueban tablas y claves foráneas.
"""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
import sqlite3

TABLAS_ESPERADAS = frozenset({
    "usuario", "cliente", "vehiculo", "celda",
    "mensualidad", "pago", "movimiento", "novedad",
})


def verificar_archivo_respaldo(ruta):
    """Comprueba integridad, relaciones y tablas; retorna el conteo de registros."""
    ruta = Path(ruta).resolve()
    if not ruta.is_file():
        raise ValueError("El archivo de respaldo no existe.")
    # %20 permite rutas con espacios; también admite rutas Windows con ':' y '/'.
    uri = 'file:' + quote(ruta.as_posix(), safe='/:') + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as conexion:
        integridad = conexion.execute("PRAGMA integrity_check").fetchone()
        if not integridad or integridad[0] != "ok":
            raise ValueError("El archivo SQLite está dañado.")
        claves_invalidas = conexion.execute("PRAGMA foreign_key_check").fetchall()
        if claves_invalidas:
            raise ValueError("El respaldo contiene referencias inválidas entre tablas.")
        tablas = {r[0] for r in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not TABLAS_ESPERADAS.issubset(tablas):
            raise ValueError("El respaldo no contiene todas las tablas del parqueadero.")
        return {
            nombre: conexion.execute(f'SELECT count(*) FROM "{nombre}"').fetchone()[0]
            for nombre in sorted(TABLAS_ESPERADAS)
        }


def crear_respaldo_bytes(ruta_origen):
    """Hace una copia transaccional, la verifica y la devuelve lista para descargar."""
    origen = Path(ruta_origen).resolve()
    if not origen.is_file():
        raise ValueError("No se encontró la base de datos del sistema.")
    with TemporaryDirectory(prefix="autos_colombia_backup_") as temporal:
        destino = Path(temporal) / "autos_colombia_respaldo.db"
        conn_origen = sqlite3.connect(str(origen), timeout=15)
        conn_destino = sqlite3.connect(str(destino), timeout=15)
        try:
            conn_origen.backup(conn_destino)
        finally:
            conn_destino.close()
            conn_origen.close()
        verificar_archivo_respaldo(destino)
        contenido = destino.read_bytes()
    archivo = BytesIO(contenido)
    archivo.seek(0)
    return archivo
