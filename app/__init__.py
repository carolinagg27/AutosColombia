"""Inicialización de la aplicación Flask."""
import os
import secrets
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from zoneinfo import ZoneInfo

from app.models import db, Usuario, Celda, Movimiento, Cliente, Vehiculo, Mensualidad

login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def habilitar_claves_foraneas(conexion, _):
    """SQLite necesita activar las claves foráneas en cada conexión."""
    import sqlite3
    if isinstance(conexion, sqlite3.Connection):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def ahora_colombia():
    return datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    secret_file = Path(app.instance_path) / ".secret_key"
    secret = os.getenv("SECRET_KEY")
    if not secret:
        if not secret_file.exists():
            secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
            try:
                secret_file.chmod(0o600)
            except OSError:
                pass
        secret = secret_file.read_text(encoding="utf-8")

    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI="sqlite:///autos_colombia.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    csrf.init_app(app)

    @login_manager.user_loader
    def cargar_usuario(usuario_id):
        try:
            usuario = db.session.get(Usuario, int(usuario_id))
            return usuario if usuario and usuario.activo else None
        except (TypeError, ValueError):
            return None

    @app.template_filter("cop")
    def formato_cop(numero):
        return "$" + f"{int(numero or 0):,}".replace(",", ".")

    @app.context_processor
    def datos_comunes():
        return {"ano_actual": ahora_colombia().year}

    from app.routes import auth, clientes, vehiculos, celdas, movimientos, novedades, pagos, reportes
    for modulo in (auth, clientes, vehiculos, celdas, movimientos, novedades, pagos, reportes):
        app.register_blueprint(modulo.bp)

    @app.get("/")
    def inicio():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        celdas = db.session.query(Celda).all()
        total = len(celdas)
        ocupadas = sum(c.estado == "Ocupada" for c in celdas)
        fuera_servicio = sum(c.estado == "Fuera de servicio" for c in celdas)
        recientes = db.session.query(Movimiento).order_by(Movimiento.id.desc()).limit(7).all()
        return render_template("dashboard.html", total=total, ocupadas=ocupadas,
                               fuera_servicio=fuera_servicio, disponibles=total-ocupadas-fuera_servicio,
                               clientes=db.session.query(Cliente).count(), vehiculos=db.session.query(Vehiculo).count(),
                               movimientos=recientes)

    @app.errorhandler(403)
    def no_autorizado(_):
        return render_template("error.html", codigo=403, mensaje="No tienes permiso para realizar esta operación."), 403

    @app.errorhandler(404)
    def no_encontrado(_):
        return render_template("error.html", codigo=404, mensaje="No encontramos la página solicitada."), 404

    with app.app_context():
        db.create_all()

    return app
