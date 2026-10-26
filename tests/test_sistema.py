"""Pruebas de las operaciones principales. Ejecutar: python -m pytest -q"""
from datetime import timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import ahora_colombia, create_app
from app.models import db, Celda, Cliente, Mensualidad, Movimiento, Pago, Usuario, Vehiculo


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,  # Solo en las pruebas automáticas.
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "pruebas.db"),
        "SECRET_KEY": "clave-solo-para-pruebas-no-produccion",
    })
    with app.app_context():
        admin = Usuario(nombre="Admin", usuario="admin", contrasena_hash=generate_password_hash("Password123"),
                        rol="Administrador", activo=True)
        operario = Usuario(nombre="Empleado", usuario="operario", contrasena_hash=generate_password_hash("Password123"),
                           rol="Operario", activo=True)
        db.session.add_all([admin, operario])
        cliente = Cliente(documento="123456", nombre="Ana López", telefono="3000000000")
        db.session.add(cliente)
        db.session.flush()
        db.session.add(Vehiculo(placa="ABC123", tipo="Carro", cliente_id=cliente.id))
        db.session.add(Celda(numero="C-01", tipo="Carro", estado="Disponible"))
        db.session.add(Celda(numero="M-01", tipo="Moto", estado="Disponible"))
        db.session.commit()
    yield app


@pytest.fixture
def cliente_http(app):
    return app.test_client()


def entrar_sesion(cliente_http, usuario="admin"):
    respuesta = cliente_http.post("/login", data={"usuario": usuario, "contrasena": "Password123"},
                                  follow_redirects=True)
    assert respuesta.status_code == 200


def crear_mensualidad_pagada(app):
    with app.app_context():
        vehiculo = Vehiculo.query.filter_by(placa="ABC123").one()
        admin = Usuario.query.filter_by(usuario="admin").one()
        hoy = ahora_colombia().date()
        m = Mensualidad(vehiculo_id=vehiculo.id, fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=29),
                        valor_cop=120000)
        db.session.add(m)
        db.session.flush()
        db.session.add(Pago(mensualidad_id=m.id, usuario_id=admin.id, fecha_pago=ahora_colombia(),
                           valor_cop=m.valor_cop, metodo="Efectivo"))
        db.session.commit()


def test_login_y_permisos(app, cliente_http):
    assert cliente_http.get("/").status_code == 302
    entrar_sesion(cliente_http, "operario")
    assert cliente_http.get("/entradas").status_code == 200
    assert cliente_http.get("/clientes").status_code == 403
    assert cliente_http.post("/respaldo").status_code == 403
    assert cliente_http.post("/logout").status_code == 302


def test_entrada_valida_mensualidad_y_salida(app, cliente_http):
    entrar_sesion(cliente_http)
    # Sin pago vigente, la entrada no debe permitirse.
    respuesta = cliente_http.post("/entradas", data={"placa": "ABC123", "celda_id": "1"},
                                  follow_redirects=True)
    assert b"mensualidad vigente" in respuesta.data
    with app.app_context():
        assert Movimiento.query.count() == 0
    crear_mensualidad_pagada(app)
    respuesta = cliente_http.post("/entradas", data={"placa": "abc123", "celda_id": "1"},
                                  follow_redirects=True)
    assert b"Entrada #" in respuesta.data
    with app.app_context():
        assert Movimiento.query.count() == 1
        assert Celda.query.filter_by(numero="C-01").one().estado == "Ocupada"
    # Duplicar la entrada debe bloquearse.
    respuesta = cliente_http.post("/entradas", data={"placa": "ABC123", "celda_id": "1"},
                                  follow_redirects=True)
    assert b"ya est" in respuesta.data
    with app.app_context():
        movimiento_id = Movimiento.query.first().id
    respuesta = cliente_http.post("/salidas", data={"movimiento_id": str(movimiento_id)},
                                  follow_redirects=True)
    assert b"Celda liberada" in respuesta.data
    with app.app_context():
        assert Movimiento.query.first().estado == "Cerrado"
        assert Celda.query.filter_by(numero="C-01").one().estado == "Disponible"
    # No debe poder cerrar dos veces.
    cliente_http.post("/salidas", data={"movimiento_id": str(movimiento_id)})
    with app.app_context():
        assert Movimiento.query.count() == 1


def test_celda_incompatible_y_novedades(app, cliente_http):
    entrar_sesion(cliente_http)
    crear_mensualidad_pagada(app)
    resp = cliente_http.post("/entradas", data={"placa": "ABC123", "celda_id": "2"}, follow_redirects=True)
    assert b"no es compatible" in resp.data
    with app.app_context():
        assert Movimiento.query.count() == 0
    cliente_http.post("/entradas", data={"placa": "ABC123", "celda_id": "1"})
    resp = cliente_http.post("/novedades", data={"movimiento_id": "1", "descripcion": "Revisi\u00f3n"},
                             follow_redirects=True)
    assert b"Novedad guardada" in resp.data
    resp = cliente_http.get("/historial?placa=ABC123&estado=Activo")
    assert b"ABC123" in resp.data


def test_pago_unico_y_respaldo(app, cliente_http):
    entrar_sesion(cliente_http)
    with app.app_context():
        v = Vehiculo.query.one()
        hoy = ahora_colombia().date()
        m = Mensualidad(vehiculo_id=v.id, fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=28), valor_cop=150000)
        db.session.add(m)
        db.session.commit()
        mid = m.id
    resp = cliente_http.post("/pagos", data={"accion": "pago", "mensualidad_id": mid,
                                              "metodo": "Transferencia"}, follow_redirects=True)
    assert b"Pago completo" in resp.data
    cliente_http.post("/pagos", data={"accion": "pago", "mensualidad_id": mid,
                                     "metodo": "Transferencia"})
    with app.app_context():
        assert Pago.query.count() == 1
    copia = cliente_http.post("/respaldo")
    assert copia.status_code == 200
    assert copia.data.startswith(b"SQLite format 3")
