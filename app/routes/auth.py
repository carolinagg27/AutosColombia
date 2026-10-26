"""Inicio de sesión y gestión de operarios."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import db, Usuario
from app.utils.validaciones import obligatorio, solo_administrador

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))
    if request.method == "POST":
        username = (request.form.get("usuario") or "").strip().lower()
        password = request.form.get("contrasena") or ""
        user = Usuario.query.filter_by(usuario=username, activo=True).first()
        if user and check_password_hash(user.contrasena_hash, password):
            login_user(user)
            flash(f"Bienvenido, {user.nombre}.", "success")
            return redirect(url_for("inicio"))
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/usuarios", methods=["GET", "POST"])
@solo_administrador
def usuarios():
    if request.method == "POST":
        try:
            nombre = obligatorio(request.form.get("nombre"), "nombre")
            username = obligatorio(request.form.get("usuario"), "usuario", 60).lower()
            password = obligatorio(request.form.get("contrasena"), "contraseña", 128)
            rol = request.form.get("rol")
            if rol not in ("Administrador", "Operario"):
                raise ValueError("Selecciona un rol válido.")
            if len(password) < 8:
                raise ValueError("La contraseña debe tener al menos 8 caracteres.")
            db.session.add(Usuario(nombre=nombre, usuario=username,
                                   contrasena_hash=generate_password_hash(password), rol=rol, activo=True))
            db.session.commit()
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("auth.usuarios"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else "El nombre de usuario ya existe.", "danger")
    return render_template("usuarios.html", usuarios=Usuario.query.order_by(Usuario.id).all())


@bp.post("/usuarios/<int:id>/estado")
@solo_administrador
def cambiar_estado(id):
    usuario = db.get_or_404(Usuario, id)
    if usuario.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "warning")
    else:
        usuario.activo = not usuario.activo
        db.session.commit()
        flash("Estado de usuario actualizado.", "success")
    return redirect(url_for("auth.usuarios"))
