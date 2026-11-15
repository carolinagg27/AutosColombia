"""Entradas, salidas y consulta previa del vehículo para el operario."""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import ahora_colombia
from app.models import db, Celda, Movimiento, Vehiculo, Mensualidad
from app.services.movimientos_service import registrar_entrada, registrar_salida

bp = Blueprint("movimientos", __name__)


def normalizar_placa(valor):
    return (valor or "").strip().upper().replace(" ", "")


@bp.get("/api/vehiculos/consulta")
@login_required
def consultar_vehiculo():
    """Permite VER el cliente, vigencia y celdas compatibles antes de confirmar.
    La comprobación se repite en el servidor al registrar, para evitar confiar en el navegador.
    """
    placa = normalizar_placa(request.args.get("placa"))
    if not placa:
        return jsonify(encontrado=False, autorizado=False, motivo="Escribe una placa."), 400
    vehiculo = Vehiculo.query.filter_by(placa=placa).first()
    if not vehiculo:
        return jsonify(encontrado=False, autorizado=False, motivo="Vehículo no registrado."), 404

    hoy = ahora_colombia().date()
    mensualidades = Mensualidad.query.filter_by(vehiculo_id=vehiculo.id).order_by(Mensualidad.fecha_fin.desc()).all()
    mensualidad = next((m for m in mensualidades if m.esta_vigente(hoy)), None)
    ultima = mensualidad or (mensualidades[0] if mensualidades else None)
    movimiento_activo = Movimiento.query.filter_by(vehiculo_id=vehiculo.id, estado="Activo").first()
    # No ofrecer celdas que figuren en un movimiento activo, aun si el estado
    # persistido estuviera desincronizado por datos antiguos.
    ocupadas = db.session.query(Movimiento.celda_id).filter(Movimiento.estado == "Activo")
    celdas = (Celda.query.filter_by(tipo=vehiculo.tipo, estado="Disponible")
              .filter(~Celda.id.in_(ocupadas))
              .order_by(Celda.numero).all())

    motivo = ""
    if movimiento_activo:
        motivo = "El vehículo ya tiene una entrada activa."
    elif not mensualidad:
        motivo = "No tiene una mensualidad vigente y pagada."
    elif not celdas:
        motivo = "No hay celdas disponibles para este tipo de vehículo."

    return jsonify(
        encontrado=True, autorizado=not motivo, motivo=motivo,
        placa=vehiculo.placa, cliente=vehiculo.cliente.nombre, tipo=vehiculo.tipo,
        mensualidad={
            "inicio": ultima.fecha_inicio.strftime("%d/%m/%Y") if ultima else None,
            "fin": ultima.fecha_fin.strftime("%d/%m/%Y") if ultima else None,
            "pagada": bool(ultima and ultima.pago),
            "vigente": bool(mensualidad),
        },
        celdas=[{"id": c.id, "numero": c.numero, "tipo": c.tipo} for c in celdas],
    )


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
    return render_template("entradas.html", vehiculos=Vehiculo.query.order_by(Vehiculo.placa).all())


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
