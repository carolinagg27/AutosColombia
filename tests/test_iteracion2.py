"""Pruebas de aceptación de Iteración 2 y correcciones del docente.

Ejecutar tras instalar dependencias: python -m pytest -q
"""
from datetime import timedelta
import io
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, ahora_colombia
from app.models import db, Usuario, Cliente, Vehiculo, Celda, Mensualidad, Pago, Movimiento
from app.utils.backup import verificar_archivo_respaldo, TABLAS_ESPERADAS


@pytest.fixture
def app(tmp_path):
    webapp = create_app({
        "TESTING": True, "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "clave-temporal-para-pruebas-iteracion-2",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "iteracion2.db"),
    })
    with webapp.app_context():
        admin = Usuario(nombre="Administrador", usuario="admin", rol="Administrador", activo=True,
                        contrasena_hash=generate_password_hash("Password123"))
        op = Usuario(nombre="Operario", usuario="operario", rol="Operario", activo=True,
                     contrasena_hash=generate_password_hash("Password123"))
        db.session.add_all([admin, op])
        cliente = Cliente(documento="1000000001", nombre="Cliente Prueba", telefono="3000000000")
        db.session.add(cliente)
        db.session.flush()
        db.session.add(Vehiculo(placa="ABC123", tipo="Carro", cliente_id=cliente.id))
        db.session.add(Celda(numero="C-01", tipo="Carro", estado="Disponible"))
        db.session.add(Celda(numero="M-01", tipo="Moto", estado="Disponible"))
        db.session.commit()
    return webapp


@pytest.fixture
def cliente_http(app):
    return app.test_client()


def login(cliente_http, usuario="admin"):
    resp = cliente_http.post("/login", data={"usuario": usuario, "contrasena": "Password123"}, follow_redirects=True)
    assert resp.status_code == 200


def mensualidad_pagada(app):
    with app.app_context():
        vehiculo = Vehiculo.query.filter_by(placa="ABC123").one()
        admin = Usuario.query.filter_by(usuario="admin").one()
        hoy = ahora_colombia().date()
        m = Mensualidad(vehiculo_id=vehiculo.id, fecha_inicio=hoy,
                        fecha_fin=hoy + timedelta(days=29), valor_cop=150000)
        db.session.add(m)
        db.session.flush()
        db.session.add(Pago(mensualidad_id=m.id, usuario_id=admin.id,
                           fecha_pago=ahora_colombia(), valor_cop=150000, metodo="Efectivo"))
        db.session.commit()


def test_consulta_previa_muestra_cliente_y_filtra_celdas(app, cliente_http):
    assert cliente_http.get('/api/vehiculos/consulta?placa=ABC123').status_code == 302
    login(cliente_http)
    sin_pago = cliente_http.get('/api/vehiculos/consulta?placa=abc123')
    assert sin_pago.status_code == 200
    assert sin_pago.json['cliente'] == 'Cliente Prueba'
    assert not sin_pago.json['autorizado']
    mensualidad_pagada(app)
    ok = cliente_http.get('/api/vehiculos/consulta?placa=abc123').json
    assert ok['autorizado'] is True
    assert ok['mensualidad']['pagada'] and ok['mensualidad']['vigente']
    assert [c['numero'] for c in ok['celdas']] == ['C-01']
    assert 'M-01' not in [c['numero'] for c in ok['celdas']]
    assert 'resultado-consulta' in cliente_http.get('/entradas').get_data(as_text=True)


def test_usuarios_edicion_y_roles(app, cliente_http):
    login(cliente_http, 'operario')
    assert cliente_http.get('/usuarios').status_code == 403
    assert cliente_http.post('/usuarios/2/editar', data={'nombre':'Otro','usuario':'otro','rol':'Administrador'}).status_code == 403
    cliente_http.post('/logout')
    login(cliente_http)
    respuesta = cliente_http.post('/usuarios', data={'nombre':'Auxiliar','usuario':'aux','contrasena':'ClaveSegura123', 'rol':'Operario'}, follow_redirects=True)
    assert 'Usuario creado' in respuesta.get_data(as_text=True)
    with app.app_context():
        uid = Usuario.query.filter_by(usuario='aux').one().id
    editado = cliente_http.post(f'/usuarios/{uid}/editar', data={'nombre':'Auxiliar Dos', 'usuario':'aux2','rol':'Operario','contrasena':''}, follow_redirects=True)
    assert 'actualizados' in editado.get_data(as_text=True)
    cliente_http.post(f'/usuarios/{uid}/estado')
    with app.app_context():
        u = db.session.get(Usuario, uid)
        assert u.nombre == 'Auxiliar Dos' and not u.activo


def test_clientes_vehiculos_y_celdas(app, cliente_http):
    login(cliente_http)
    assert cliente_http.post('/clientes', data={'documento':'0005','nombre':'María'}, follow_redirects=True).status_code == 200
    with app.app_context():
        cliente = Cliente.query.filter_by(documento='0005').one()
        cliente_id = cliente.id
    respuesta = cliente_http.post('/vehiculos', data={'placa':'MOTO01','tipo':'Moto','cliente_id':cliente_id},follow_redirects=True)
    assert 'Vehículo registrado' in respuesta.get_data(as_text=True)
    r = cliente_http.post('/celdas/nueva',data={'numero':'C-02','tipo':'Carro'},follow_redirects=True)
    assert 'Celda registrada' in r.get_data(as_text=True)
    with app.app_context():
        celda = Celda.query.filter_by(numero='C-02').one()
        cid = celda.id
    cliente_http.post(f'/celdas/{cid}/editar',data={'numero':'C-03','tipo':'Carro'})
    cliente_http.post(f'/celdas/{cid}/estado',data={'estado':'Fuera de servicio'})
    with app.app_context():
        celda = db.session.get(Celda,cid)
        assert celda.numero == 'C-03' and celda.estado == 'Fuera de servicio'
    tabla = cliente_http.get('/celdas?tipo=Moto&estado=Disponible').get_data(as_text=True)
    assert 'M-01' in tabla and 'C-01' not in tabla


def test_celda_ocupada_y_asociacion_usuario_salida_opcional(app, cliente_http):
    login(cliente_http)
    mensualidad_pagada(app)
    respuesta = cliente_http.post('/entradas',data={'placa':'ABC123','celda_id':'1'},follow_redirects=True)
    assert 'Entrada #' in respuesta.get_data(as_text=True)
    with app.app_context():
        mov = Movimiento.query.one()
        assert mov.usuario_entrada_id is not None
        assert mov.usuario_salida_id is None
        assert mov.fecha_salida is None
        mid = mov.id
    respuesta = cliente_http.post('/celdas/1/editar', data={'numero':'C-99','tipo':'Moto'}, follow_redirects=True)
    assert 'No puedes editar una celda ocupada' in respuesta.get_data(as_text=True)
    respuesta = cliente_http.post('/celdas/1/estado', data={'estado':'Fuera de servicio'},follow_redirects=True)
    assert 'No puedes modificar una celda ocupada' in respuesta.get_data(as_text=True)
    cliente_http.post('/salidas',data={'movimiento_id':str(mid)})
    with app.app_context():
        mov = Movimiento.query.one()
        assert mov.usuario_salida_id is not None and mov.estado == 'Cerrado'
        assert mov.celda.estado == 'Disponible'


def test_respaldo_descarga_y_restauracion(app, cliente_http, tmp_path):
    login(cliente_http)
    archivo = cliente_http.post('/respaldo')
    assert archivo.status_code == 200
    assert 'attachment' in archivo.headers.get('Content-Disposition', '')
    assert archivo.data.startswith(b'SQLite format 3')
    respaldo = tmp_path / 'respaldo_descargado.db'
    respaldo.write_bytes(archivo.data)
    conteos = verificar_archivo_respaldo(respaldo)
    assert set(conteos) == TABLAS_ESPERADAS and conteos['usuario'] == 2
    restaurada = tmp_path / 'restaurada.db'
    origen = sqlite3.connect(str(respaldo))
    destino = sqlite3.connect(str(restaurada))
    try:
        origen.backup(destino)
    finally:
        origen.close()
        destino.close()
    conteos_restaurados = verificar_archivo_respaldo(restaurada)
    assert conteos_restaurados == conteos
