from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import db, Mensualidad, Pago, Vehiculo
from app.services.pagos_service import registrar_pago
from app.utils.validaciones import fecha_iso, entero_positivo, solo_administrador

bp = Blueprint("pagos", __name__)


@bp.route("/pagos", methods=["GET", "POST"])
@solo_administrador
def lista():
    if request.method == "POST":
        accion = request.form.get("accion")
        try:
            if accion == "mensualidad":
                vehiculo_id = entero_positivo(request.form.get("vehiculo_id"), "vehículo")
                if db.session.get(Vehiculo, vehiculo_id) is None:
                    raise ValueError("Selecciona un vehículo válido.")
                inicio = fecha_iso(request.form.get("fecha_inicio"), "inicio")
                fin = fecha_iso(request.form.get("fecha_fin"), "fin")
                valor = entero_positivo(request.form.get("valor_cop"), "valor")
                if inicio > fin:
                    raise ValueError("La fecha final debe ser posterior o igual al inicio.")
                # No superponer contratos de mensualidad del mismo vehículo.
                solapada = Mensualidad.query.filter(Mensualidad.vehiculo_id == vehiculo_id,
                                                   Mensualidad.fecha_inicio <= fin,
                                                   Mensualidad.fecha_fin >= inicio).first()
                if solapada:
                    raise ValueError("Ya existe una mensualidad para ese vehículo en el período indicado.")
                db.session.add(Mensualidad(vehiculo_id=vehiculo_id, fecha_inicio=inicio,
                                           fecha_fin=fin, valor_cop=valor))
                db.session.commit()
                flash("Mensualidad creada. Registra su pago para autorizar el ingreso.", "success")
            elif accion == "pago":
                mensualidad_id = entero_positivo(request.form.get("mensualidad_id"), "mensualidad")
                registrar_pago(mensualidad_id, request.form.get("metodo"), current_user.id)
                flash("Pago completo registrado.", "success")
            else:
                raise ValueError("Operación desconocida.")
            return redirect(url_for("pagos.lista"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "El pago ya existe o los datos son inválidos.", "danger")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Ocurrió un error al guardar la información.", "danger")
    return render_template("pagos.html", vehiculos=Vehiculo.query.order_by(Vehiculo.placa).all(),
                           mensualidades=Mensualidad.query.order_by(Mensualidad.id.desc()).all(),
                           pagos=Pago.query.order_by(Pago.id.desc()).limit(50).all())
