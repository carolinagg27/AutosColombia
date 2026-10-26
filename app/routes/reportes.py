"""Descarga de una copia consistente de la base de datos SQLite."""
import io
import sqlite3
import tempfile
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, send_file, url_for
from sqlalchemy.exc import SQLAlchemyError

from app import ahora_colombia
from app.models import db
from app.utils.validaciones import solo_administrador

bp = Blueprint("reportes", __name__)


@bp.post("/respaldo")
@solo_administrador
def respaldo():
    # API backup() de SQLite: genera instantánea aun con la base abierta.
    try:
        origen = Path(db.engine.url.database)
        archivo = io.BytesIO()
        with tempfile.TemporaryDirectory() as temporal:
            salida = Path(temporal) / "respaldo.db"
            with sqlite3.connect(str(origen)) as conexion_fuente:
                with sqlite3.connect(str(salida)) as conexion_destino:
                    conexion_fuente.backup(conexion_destino)
            archivo.write(salida.read_bytes())
        archivo.seek(0)
        fecha = ahora_colombia().strftime("%Y%m%d_%H%M")
        return send_file(archivo, mimetype="application/octet-stream", as_attachment=True,
                         download_name=f"autos_colombia_respaldo_{fecha}.db")
    except (OSError, sqlite3.Error, SQLAlchemyError):
        flash("No se pudo generar el respaldo.", "danger")
        return redirect(url_for("inicio"))
