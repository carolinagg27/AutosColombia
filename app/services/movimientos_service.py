"""Reglas de negocio de ingreso y salida. Se guarda todo en una transacción."""
from app import ahora_colombia
from app.models import db, Vehiculo, Celda, Movimiento, Mensualidad


def registrar_entrada(placa, celda_id, usuario_id):
    placa = (placa or "").strip().upper().replace(" ", "")
    vehiculo = Vehiculo.query.filter_by(placa=placa).first()
    if not vehiculo:
        raise ValueError("Vehículo no registrado.")
    if Movimiento.query.filter_by(vehiculo_id=vehiculo.id, estado="Activo").first():
        raise ValueError("Este vehículo ya está dentro del parqueadero.")
    hoy = ahora_colombia().date()
    mensualidades = Mensualidad.query.filter_by(vehiculo_id=vehiculo.id).all()
    if not any(m.esta_vigente(hoy) for m in mensualidades):
        raise ValueError("El vehículo no tiene una mensualidad vigente y pagada.")
    celda = db.session.get(Celda, int(celda_id))
    if not celda or not celda.esta_disponible():
        raise ValueError("La celda no está disponible.")
    if celda.tipo != vehiculo.tipo:
        raise ValueError("La celda no es compatible con el tipo de vehículo.")
    movimiento = Movimiento(vehiculo_id=vehiculo.id, celda_id=celda.id,
                            usuario_entrada_id=usuario_id, fecha_entrada=ahora_colombia(), estado="Activo")
    db.session.add(movimiento)
    celda.estado = "Ocupada"
    db.session.commit()
    return movimiento


def registrar_salida(movimiento_id, usuario_id):
    movimiento = db.session.get(Movimiento, movimiento_id)
    if not movimiento or movimiento.estado != "Activo":
        raise ValueError("No existe una entrada activa para registrar la salida.")
    movimiento.cerrar_salida(usuario_id, ahora_colombia())
    movimiento.celda.estado = "Disponible"
    db.session.commit()
    return movimiento
