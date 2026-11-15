"""Pruebas reales de SQLite y sus restricciones; sin dependencias de Flask.

Estas pruebas no sustituyen las pruebas de rutas Flask (test_aceptacion_completa.py).
"""
from datetime import datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sqlite3

import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "sql/modelo_punto6.sql").read_text(encoding="utf-8")
SPEC = spec_from_file_location("autos_backup_independiente", ROOT / "app/utils/backup.py")
backup = module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


@pytest.fixture
def base(tmp_path):
    ruta = tmp_path / "autos prueba 100%.db"
    con = sqlite3.connect(ruta)
    con.executescript(SQL)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("INSERT INTO usuario (nombre,usuario,contrasena_hash,rol,activo) VALUES (?,?,?,?,?)",
                ("Admin", "admin", "hash", "Administrador", 1))
    con.execute("INSERT INTO cliente (documento,nombre,telefono) VALUES (?,?,?)",
                ("100001", "Cliente", "123"))
    con.execute("INSERT INTO vehiculo (placa,tipo,cliente_id) VALUES ('ABC123','Carro',1)")
    con.execute("INSERT INTO vehiculo (placa,tipo,cliente_id) VALUES ('MOT123','Moto',1)")
    con.execute("INSERT INTO celda (numero,tipo,estado) VALUES ('C-01','Carro','Disponible')")
    con.execute("INSERT INTO celda (numero,tipo,estado) VALUES ('M-01','Moto','Disponible')")
    con.commit()
    try:
        yield con, ruta
    finally:
        con.close()


def test_ocho_tablas_y_relaciones(base):
    con, ruta = base
    assert backup.verificar_archivo_respaldo(ruta)["vehiculo"] == 2
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    cols = {r[1]: r[3] for r in con.execute("PRAGMA table_info(movimiento)")}
    assert cols['usuario_entrada_id'] == 1
    assert cols['usuario_salida_id'] == 0


@pytest.mark.parametrize("consulta,datos", [
    ("INSERT INTO usuario (nombre,usuario,contrasena_hash,rol) VALUES (?,?,?,?)",("A","admin","hash","Operario")),
    ("INSERT INTO vehiculo (placa,tipo,cliente_id) VALUES (?,?,?)",("ABC123","Carro",1)),
    ("INSERT INTO celda (numero,tipo) VALUES (?,?)",("C-01","Carro")),
    ("INSERT INTO celda (numero,tipo) VALUES (?,?)",("C-99","Bus")),
    ("INSERT INTO vehiculo (placa,tipo,cliente_id) VALUES (?,?,?)",("XY123","Bus",1)),
    ("INSERT INTO vehiculo (placa,tipo,cliente_id) VALUES (?,?,?)",("XY123","Carro",999)),
])
def test_restricciones_unicidad_tipos_foraneas(base,consulta,datos):
    con, _ = base
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(consulta,datos)
    con.rollback()


def movimiento_activo(con, vehiculo_id, celda_id, hora="2026-11-15 10:00:00"):
    con.execute("""INSERT INTO movimiento
    (vehiculo_id,celda_id,usuario_entrada_id,fecha_entrada,estado)
    VALUES (?,?,1,?,'Activo')""",(vehiculo_id,celda_id,hora))


def test_entrada_salida_usuario_y_celda(base):
    con, ruta = base
    with con:
        movimiento_activo(con,1,1)
        con.execute("UPDATE celda SET estado='Ocupada' WHERE id=1")
    mov = con.execute("SELECT usuario_entrada_id,usuario_salida_id,fecha_salida,estado FROM movimiento").fetchone()
    assert mov == (1,None,None,"Activo")
    assert con.execute("SELECT estado FROM celda WHERE id=1").fetchone()[0] == "Ocupada"
    with con:
        con.execute("""UPDATE movimiento SET usuario_salida_id=1,
        fecha_salida='2026-11-15 11:00:00',estado='Cerrado' WHERE id=1""")
        con.execute("UPDATE celda SET estado='Disponible' WHERE id=1")
    assert con.execute("SELECT estado FROM movimiento WHERE id=1").fetchone()[0] == "Cerrado"
    assert con.execute("SELECT estado FROM celda WHERE id=1").fetchone()[0] == "Disponible"
    assert backup.verificar_archivo_respaldo(ruta)['movimiento'] == 1


def test_indice_unico_por_vehiculo_entrada_activa(base):
    con,_ = base
    movimiento_activo(con,1,1)
    con.commit()
    with pytest.raises(sqlite3.IntegrityError):
        movimiento_activo(con,1,2)
    con.rollback()
    assert con.execute("SELECT COUNT(*) FROM movimiento").fetchone()[0] == 1


def test_indice_unico_por_celda_entrada_activa(base):
    con,_ = base
    movimiento_activo(con,1,1)
    con.commit()
    with pytest.raises(sqlite3.IntegrityError):
        movimiento_activo(con,2,1)
    con.rollback()
    assert con.execute("SELECT COUNT(*) FROM movimiento").fetchone()[0] == 1


def test_movimiento_cerrado_exige_usuario_salida(base):
    con,_ = base
    movimiento_activo(con,1,1)
    con.commit()
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE movimiento SET estado='Cerrado', fecha_salida='2026-11-15 11:00:00' WHERE id=1")
    con.rollback()
    assert con.execute("SELECT estado FROM movimiento WHERE id=1").fetchone()[0] == "Activo"


def test_transaccion_atomica_revierte_celda(base):
    con,_ = base
    movimiento_activo(con,1,1)
    con.commit()
    with pytest.raises(sqlite3.IntegrityError):
        with con:
            con.execute("UPDATE celda SET estado='Ocupada' WHERE id=2")
            movimiento_activo(con,1,2)
    assert con.execute("SELECT estado FROM celda WHERE id=2").fetchone()[0] == "Disponible"


def test_respaldo_en_wal_copia_datos_confirmados(base,tmp_path):
    con,ruta = base
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("INSERT INTO cliente(documento,nombre) VALUES('777','Último registro')")
    con.commit()
    datos = backup.crear_respaldo_bytes(ruta).getvalue()
    assert datos.startswith(b"SQLite format 3\x00")
    descargado = tmp_path / 'base descargada 100%.db'
    descargado.write_bytes(datos)
    conteos = backup.verificar_archivo_respaldo(descargado)
    assert conteos['cliente'] == 2
    restaurada = tmp_path / 'restaurada.db'
    origen = sqlite3.connect(descargado)
    destino = sqlite3.connect(restaurada)
    try:
        origen.backup(destino)
    finally:
        origen.close()
        destino.close()
    assert backup.verificar_archivo_respaldo(restaurada) == conteos


def test_rechaza_archivo_invalido_y_base_incompleta(tmp_path):
    basura = tmp_path / 'basura.db'
    basura.write_bytes(b'no es sqlite')
    with pytest.raises(sqlite3.DatabaseError):
        backup.verificar_archivo_respaldo(basura)
    incompleta = tmp_path / 'incompleta.db'
    with sqlite3.connect(incompleta) as con:
        con.execute('CREATE TABLE usuario (id INTEGER)')
    with pytest.raises(ValueError, match='tablas'):
        backup.verificar_archivo_respaldo(incompleta)


def test_restauracion_atomica_con_copia_preventiva(base,tmp_path):
    """Ejecuta la función real del restaurador, sin importar la aplicación Flask."""
    from sys import modules
    con,original=base
    con.commit()
    copia=tmp_path / 'exportado.db'
    copia.write_bytes(backup.crear_respaldo_bytes(original).getvalue())
    destino=tmp_path / 'restaurar_sobre.db'
    with sqlite3.connect(destino) as receptor:
        receptor.executescript(SQL)
    previo=backup.verificar_archivo_respaldo(destino)
    assert previo['usuario']==0
    spec=spec_from_file_location('restaurador_independiente', ROOT/'restaurar_respaldo.py')
    restaurador=module_from_spec(spec)
    anterior=modules.get('app.utils.backup')
    modules['app.utils.backup']=backup
    try:
        spec.loader.exec_module(restaurador)
    finally:
        if anterior is None:
            modules.pop('app.utils.backup', None)
        else:
            modules['app.utils.backup']=anterior
    ruta, conteos=restaurador.restaurar(copia,destino)
    assert ruta==destino
    assert conteos==backup.verificar_archivo_respaldo(destino)
    assert conteos['usuario']==1
    preventivas=list(tmp_path.glob('autos_colombia_antes_*.db'))
    assert len(preventivas)==1
    assert backup.verificar_archivo_respaldo(preventivas[0])['usuario']==0
    # Un WAL presente impide una restauración riesgosa.
    path_wal=Path(str(destino)+'-wal')
    path_wal.write_bytes(b'archivo de control simulado')
    with pytest.raises(ValueError,match='WAL/SHM'):
        restaurador.restaurar(copia,destino)
