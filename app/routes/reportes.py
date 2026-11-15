"""Descarga de respaldo SQLite y verificación de su integridad."""
import sqlite3
from flask import Blueprint, flash, redirect, send_file, url_for
from app import ahora_colombia
from app.models import db
from app.utils.backup import crear_respaldo_bytes
from app.utils.validaciones import solo_administrador

bp = Blueprint("reportes", __name__)


@bp.post("/respaldo")
@solo_administrador
def respaldo():
    try:
        archivo = crear_respaldo_bytes(db.engine.url.database)
        fecha = ahora_colombia().strftime("%Y%m%d_%H%M%S")
        respuesta = send_file(
            archivo, as_attachment=True, mimetype="application/x-sqlite3",
            download_name=f"autos_colombia_respaldo_{fecha}.db",
        )
        respuesta.headers["Cache-Control"] = "no-store"
        return respuesta
    except (ValueError, OSError, sqlite3.Error):
        flash("No fue posible generar el respaldo. Comprueba el archivo de base de datos.", "danger")
        return redirect(url_for("inicio"))
