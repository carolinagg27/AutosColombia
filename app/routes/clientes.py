from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.models import db, Cliente
from app.utils.validaciones import obligatorio, solo_administrador

bp = Blueprint("clientes", __name__)


@bp.route("/clientes", methods=["GET", "POST"])
@solo_administrador
def lista():
    if request.method == "POST":
        try:
            documento = obligatorio(request.form.get("documento"), "documento", 25)
            nombre = obligatorio(request.form.get("nombre"), "nombre")
            telefono = (request.form.get("telefono") or "").strip()[:30]
            db.session.add(Cliente(documento=documento, nombre=nombre, telefono=telefono))
            db.session.commit()
            flash("Cliente registrado.", "success")
            return redirect(url_for("clientes.lista"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "Este documento ya está registrado.", "danger")
    return render_template("clientes.html", clientes=Cliente.query.order_by(Cliente.nombre).all())


@bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
@solo_administrador
def editar(id):
    cliente = db.get_or_404(Cliente, id)
    if request.method == "POST":
        try:
            cliente.documento = obligatorio(request.form.get("documento"), "documento", 25)
            cliente.nombre = obligatorio(request.form.get("nombre"), "nombre")
            cliente.telefono = (request.form.get("telefono") or "").strip()[:30]
            db.session.commit()
            flash("Cliente actualizado.", "success")
            return redirect(url_for("clientes.lista"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "El documento ya está en uso.", "danger")
    return render_template("editar_cliente.html", cliente=cliente)
