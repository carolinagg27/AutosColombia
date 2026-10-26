from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app import ahora_colombia
from app.models import db, Movimiento, Novedad
from app.utils.validaciones import obligatorio

bp = Blueprint("novedades", __name__)


@bp.route("/novedades", methods=["GET", "POST"])
@login_required
def lista():
    if request.method == "POST":
        try:
            descripcion = obligatorio(request.form.get("descripcion"), "descripción", 1000)
            movimiento_id = int(request.form.get("movimiento_id", ""))
            movimiento = db.session.get(Movimiento, movimiento_id)
            if not movimiento or movimiento.estado != "Activo":
                raise ValueError("Selecciona un vehículo que todavía esté estacionado.")
            db.session.add(Novedad(movimiento_id=movimiento.id, usuario_id=current_user.id,
                                  descripcion=descripcion, fecha=ahora_colombia()))
            db.session.commit()
            flash("Novedad guardada.", "success")
            return redirect(url_for("novedades.lista"))
        except (ValueError, SQLAlchemyError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "No se pudo guardar la novedad.", "danger")
    return render_template("novedades.html", novedades=Novedad.query.order_by(Novedad.id.desc()).limit(200).all(),
                           activos=Movimiento.query.filter_by(estado="Activo").all())
