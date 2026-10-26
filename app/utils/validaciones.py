"""Funciones pequeñas compartidas entre formularios."""
from datetime import date
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def solo_administrador(funcion):
    @wraps(funcion)
    @login_required
    def protegida(*args, **kwargs):
        if current_user.rol != "Administrador":
            abort(403)
        return funcion(*args, **kwargs)
    return protegida


def obligatorio(texto, campo, longitud=100):
    valor = (texto or "").strip()
    if not valor:
        raise ValueError(f"El campo {campo} es obligatorio.")
    if len(valor) > longitud:
        raise ValueError(f"El campo {campo} supera los {longitud} caracteres.")
    return valor


def entero_positivo(valor, campo):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El campo {campo} debe ser un número entero.")
    if numero <= 0:
        raise ValueError(f"El campo {campo} debe ser mayor que cero.")
    return numero


def fecha_iso(valor, campo):
    try:
        return date.fromisoformat(valor or "")
    except ValueError:
        raise ValueError(f"La fecha de {campo} no es válida.")
