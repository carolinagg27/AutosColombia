from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.models import db, Cliente, Vehiculo
from app.utils.validaciones import obligatorio, solo_administrador

bp = Blueprint("vehiculos", __name__)


def datos_vehiculo():
    placa = obligatorio(request.form.get("placa"), "placa", 12).upper().replace(" ", "")
    tipo = request.form.get("tipo")
    if tipo not in ("Carro", "Moto"):
        raise ValueError("Selecciona un tipo de vehículo válido.")
    try:
        cliente_id = int(request.form.get("cliente_id", ""))
    except ValueError:
        raise ValueError("Selecciona un cliente válido.")
    if db.session.get(Cliente, cliente_id) is None:
        raise ValueError("El cliente seleccionado no existe.")
    return placa, tipo, cliente_id


@bp.route("/vehiculos", methods=["GET", "POST"])
@solo_administrador
def lista():
    if request.method == "POST":
        try:
            placa, tipo, cliente_id = datos_vehiculo()
            db.session.add(Vehiculo(placa=placa, tipo=tipo, cliente_id=cliente_id))
            db.session.commit()
            flash("Vehículo registrado.", "success")
            return redirect(url_for("vehiculos.lista"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "Esta placa ya está registrada.", "danger")
    return render_template("vehiculos.html", vehiculos=Vehiculo.query.order_by(Vehiculo.placa).all(),
                           clientes=Cliente.query.order_by(Cliente.nombre).all())


@bp.route("/vehiculos/<int:id>/editar", methods=["GET", "POST"])
@solo_administrador
def editar(id):
    vehiculo = db.get_or_404(Vehiculo, id)
    if request.method == "POST":
        try:
            placa, tipo, cliente_id = datos_vehiculo()
            if tipo != vehiculo.tipo and any(m.estado == "Activo" for m in vehiculo_movimientos(vehiculo.id)):
                raise ValueError("No puedes cambiar el tipo de un vehículo estacionado.")
            vehiculo.placa, vehiculo.tipo, vehiculo.cliente_id = placa, tipo, cliente_id
            db.session.commit()
            flash("Vehículo actualizado.", "success")
            return redirect(url_for("vehiculos.lista"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "Esa placa ya está en uso.", "danger")
    return render_template("editar_vehiculo.html", vehiculo=vehiculo,
                           clientes=Cliente.query.order_by(Cliente.nombre).all())


def vehiculo_movimientos(vehiculo_id):
    from app.models import Movimiento
    return Movimiento.query.filter_by(vehiculo_id=vehiculo_id, estado="Activo").all()
