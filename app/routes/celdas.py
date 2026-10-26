from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.models import db, Celda
from app.utils.validaciones import obligatorio, solo_administrador

bp = Blueprint("celdas", __name__)


@bp.get("/celdas")
@login_required
def lista():
    return render_template("celdas.html", celdas=Celda.query.order_by(Celda.tipo, Celda.numero).all())


@bp.post("/celdas/nueva")
@solo_administrador
def crear():
    try:
        numero = obligatorio(request.form.get("numero"), "número", 12).upper()
        tipo = request.form.get("tipo")
        if tipo not in ("Carro", "Moto"):
            raise ValueError("Selecciona un tipo de celda válido.")
        db.session.add(Celda(numero=numero, tipo=tipo, estado="Disponible"))
        db.session.commit()
        flash("Celda registrada.", "success")
    except (ValueError, IntegrityError) as exc:
        db.session.rollback()
        flash(str(exc) if isinstance(exc, ValueError) else "Este número de celda ya existe.", "danger")
    return redirect(url_for("celdas.lista"))


@bp.post("/celdas/<int:id>/estado")
@solo_administrador
def estado(id):
    celda = db.get_or_404(Celda, id)
    nuevo = request.form.get("estado")
    if celda.estado == "Ocupada":
        flash("No puedes modificar una celda ocupada; primero registra la salida.", "warning")
    elif nuevo not in ("Disponible", "Fuera de servicio"):
        flash("Estado de celda inválido.", "danger")
    else:
        celda.estado = nuevo
        db.session.commit()
        flash("Estado de celda actualizado.", "success")
    return redirect(url_for("celdas.lista"))
