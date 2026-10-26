"""Registro de pagos completos de mensualidades."""
from app import ahora_colombia
from app.models import db, Mensualidad, Pago


def registrar_pago(mensualidad_id, metodo, usuario_id):
    mensualidad = db.session.get(Mensualidad, mensualidad_id)
    if not mensualidad:
        raise ValueError("La mensualidad no existe.")
    if mensualidad.pago:
        raise ValueError("Esta mensualidad ya está pagada.")
    if metodo not in ("Efectivo", "Transferencia"):
        raise ValueError("Selecciona un método de pago válido.")
    pago = Pago(mensualidad_id=mensualidad.id, usuario_id=usuario_id,
                fecha_pago=ahora_colombia(), valor_cop=mensualidad.valor_cop, metodo=metodo)
    db.session.add(pago)
    db.session.commit()
    return pago
