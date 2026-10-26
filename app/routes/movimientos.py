from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import db, Celda, Movimiento, Vehiculo
from app.services.movimientos_service import registrar_entrada, registrar_salida

bp = Blueprint("movimientos", __name__)


@bp.route("/entradas", methods=["GET", "POST"])
@login_required
def entradas():
    if request.method == "POST":
        try:
            celda_id = int(request.form.get("celda_id", ""))
            movimiento = registrar_entrada(request.form.get("placa"), celda_id, current_user.id)
            flash(f"Entrada #{movimiento.id} registrada. Celda {movimiento.celda.numero} ocupada.", "success")
            return redirect(url_for("movimientos.entradas"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "La celda o el vehículo ya están ocupados.", "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Error al guardar el ingreso. Inténtalo de nuevo.", "danger")
    return render_template("entradas.html", vehiculos=Vehiculo.query.order_by(Vehiculo.placa).all(),
                           celdas=Celda.query.filter_by(estado="Disponible").order_by(Celda.numero).all())


@bp.route("/salidas", methods=["GET", "POST"])
@login_required
def salidas():
    if request.method == "POST":
        try:
            movimiento_id = int(request.form.get("movimiento_id", ""))
            movimiento = registrar_salida(movimiento_id, current_user.id)
            flash(f"Salida de {movimiento.vehiculo.placa} registrada. Celda liberada.", "success")
            return redirect(url_for("movimientos.salidas"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "No se pudo completar la salida.", "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Error de base de datos al registrar la salida.", "danger")
    activos = Movimiento.query.filter_by(estado="Activo").order_by(Movimiento.fecha_entrada.desc()).all()
    return render_template("salidas.html", movimientos=activos)


@bp.get("/historial")
@login_required
def historial():
    placa = (request.args.get("placa") or "").strip().upper()
    estado = request.args.get("estado") or ""
    desde = request.args.get("desde") or ""
    hasta = request.args.get("hasta") or ""
    consulta = Movimiento.query.join(Vehiculo)
    try:
        if desde:
            date.fromisoformat(desde)
            consulta = consulta.filter(db.func.date(Movimiento.fecha_entrada) >= desde)
        if hasta:
            date.fromisoformat(hasta)
            consulta = consulta.filter(db.func.date(Movimiento.fecha_entrada) <= hasta)
    except ValueError:
        flash("Utiliza un rango de fechas válido.", "warning")
        desde, hasta = "", ""
        consulta = Movimiento.query.join(Vehiculo)
    if placa:
        consulta = consulta.filter(Vehiculo.placa.contains(placa))
    if estado in ("Activo", "Cerrado"):
        consulta = consulta.filter(Movimiento.estado == estado)
    movimientos = consulta.order_by(Movimiento.id.desc()).limit(300).all()
    return render_template("historial.html", movimientos=movimientos, placa=placa, estado=estado, desde=desde, hasta=hasta)
