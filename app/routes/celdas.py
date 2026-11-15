"""Administrar celdas; no permite cambiar una celda ocupada."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.models import db, Celda, Movimiento
from app.utils.validaciones import obligatorio, solo_administrador

bp = Blueprint("celdas", __name__)


@bp.get("/celdas")
@login_required
def lista():
    tipo = request.args.get("tipo", "")
    estado = request.args.get("estado", "")
    consulta = Celda.query
    if tipo in ("Carro", "Moto"):
        consulta = consulta.filter_by(tipo=tipo)
    else:
        tipo = ""
    if estado in ("Disponible", "Ocupada", "Fuera de servicio"):
        consulta = consulta.filter_by(estado=estado)
    else:
        estado = ""
    return render_template("celdas.html", celdas=consulta.order_by(Celda.tipo, Celda.numero).all(),
                           tipo_filtro=tipo, estado_filtro=estado)


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


def ocupada_en_movimiento(id):
    return Movimiento.query.filter_by(celda_id=id, estado="Activo").first() is not None


@bp.route("/celdas/<int:id>/editar", methods=["GET", "POST"])
@solo_administrador
def editar(id):
    celda = db.get_or_404(Celda, id)
    if request.method == "POST":
        try:
            if celda.estado == "Ocupada" or ocupada_en_movimiento(celda.id):
                raise ValueError("No puedes editar una celda ocupada.")
            numero = obligatorio(request.form.get("numero"), "número", 12).upper()
            tipo = request.form.get("tipo")
            if tipo not in ("Carro", "Moto"):
                raise ValueError("Selecciona un tipo de celda válido.")
            celda.numero, celda.tipo = numero, tipo
            db.session.commit()
            flash("Celda actualizada.", "success")
            return redirect(url_for("celdas.lista"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "Este número de celda ya existe.", "danger")
    return render_template("editar_celda.html", celda=celda)


@bp.post("/celdas/<int:id>/estado")
@solo_administrador
def estado(id):
    celda = db.get_or_404(Celda, id)
    nuevo = request.form.get("estado")
    if celda.estado == "Ocupada" or ocupada_en_movimiento(celda.id):
        flash("No puedes modificar una celda ocupada; primero registra la salida.", "warning")
    elif nuevo not in ("Disponible", "Fuera de servicio"):
        flash("Estado de celda inválido.", "danger")
    else:
        celda.estado = nuevo
        db.session.commit()
        flash("Estado de celda actualizado.", "success")
    return redirect(url_for("celdas.lista"))
