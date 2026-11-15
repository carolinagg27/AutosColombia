"""Pruebas de aceptación CP-01..CP-19 del punto g).

Requiere Flask y dependencias instaladas, y pytest. Se ejecuta contra una
base SQLite TEMPORAL por caso; jamás modifica instance/autos_colombia.db.
Las pruebas de CSRF usan tokens reales (NO se desactiva la protección).
"""
import re
from datetime import timedelta
from pathlib import Path
from time import perf_counter

import pytest
from werkzeug.security import generate_password_hash, check_password_hash

from app import create_app, ahora_colombia
from app.models import (db, Usuario, Cliente, Vehiculo, Celda, Mensualidad,
                        Movimiento, Pago)
from app.utils.backup import verificar_archivo_respaldo
from restaurar_respaldo import restaurar


@pytest.fixture
def app(tmp_path):
    instancia = create_app({
        'TESTING': True, 'WTF_CSRF_ENABLED': True,
        'SECRET_KEY': 'solo-pruebas-para-casos-de-aceptacion',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'casos_aceptacion.db'),
    })
    with instancia.app_context():
        users = [
            Usuario(nombre='Administrador Principal', usuario='admin', rol='Administrador',
                    activo=True, contrasena_hash=generate_password_hash('Password123')),
            Usuario(nombre='Operario Principal', usuario='operario', rol='Operario',
                    activo=True, contrasena_hash=generate_password_hash('Password123')),
            Usuario(nombre='Operario Inactivo', usuario='inactivo', rol='Operario',
                    activo=False, contrasena_hash=generate_password_hash('Password123')),
        ]
        db.session.add_all(users)
        clientes = [Cliente(documento='DOC1001', nombre='Maria Torres'),
                    Cliente(documento='DOC1002', nombre='Carlos Perez')]
        db.session.add_all(clientes)
        db.session.flush()
        db.session.add_all([
            Vehiculo(placa='ABC123', tipo='Carro', cliente_id=clientes[0].id),
            Vehiculo(placa='LMN456', tipo='Carro', cliente_id=clientes[1].id),
            Vehiculo(placa='MOT789', tipo='Moto', cliente_id=clientes[0].id),
        ])
        db.session.add_all([
            Celda(numero='C-01', tipo='Carro', estado='Disponible'),
            Celda(numero='C-02', tipo='Carro', estado='Disponible'),
            Celda(numero='C-03', tipo='Carro', estado='Fuera de servicio'),
            Celda(numero='M-01', tipo='Moto', estado='Disponible'),
        ])
        db.session.flush()
        hoy = ahora_colombia().date()
        db.session.add_all([
            Mensualidad(vehiculo_id=1,fecha_inicio=hoy-timedelta(days=3),
                       fecha_fin=hoy+timedelta(days=26),valor_cop=150000),
            Mensualidad(vehiculo_id=2,fecha_inicio=hoy-timedelta(days=60),
                       fecha_fin=hoy-timedelta(days=1),valor_cop=150000),
        ])
        db.session.flush()
        db.session.add_all([
            Pago(mensualidad_id=1,usuario_id=1,fecha_pago=ahora_colombia(),
                 valor_cop=150000,metodo='Efectivo'),
            Pago(mensualidad_id=2,usuario_id=1,fecha_pago=ahora_colombia(),
                 valor_cop=150000,metodo='Transferencia'),
        ])
        db.session.commit()
    yield instancia
    with instancia.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def web(app):
    return app.test_client()


def token(web,path='/'):
    response=web.get(path)
    assert response.status_code in (200,302)
    html=response.get_data(as_text=True)
    match=re.search(r'<meta name="csrf-token" content="([^"]+)"',html)
    assert match, f'No se encontró token CSRF en {path}'
    return match.group(1)


def post(web,path,data=None,source='/'):
    data=dict(data or {})
    data['csrf_token']=token(web,source)
    return web.post(path,data=data,follow_redirects=True)


def login(web,user='admin',password='Password123'):
    response=post(web,'/login',{'usuario':user,'contrasena':password},'/login')
    assert response.status_code==200
    return response


def json_vehiculo(web,placa):
    r=web.get('/api/vehiculos/consulta',query_string={'placa':placa})
    assert r.status_code==200
    return r.json


def test_cp01_crear_usuario(app,web):
    login(web)
    page=post(web,'/usuarios',{'nombre':'Nuevo Operario','usuario':'nuevo','contrasena':'ClaveSegura123','rol':'Operario'},'/usuarios')
    assert 'Usuario creado' in page.get_data(as_text=True)
    with app.app_context():
        u=Usuario.query.filter_by(usuario='nuevo').one()
        assert check_password_hash(u.contrasena_hash,'ClaveSegura123') and u.activo


def test_cp02_rechazar_usuario_duplicado(app,web):
    login(web)
    r=post(web,'/usuarios',{'nombre':'Duplicado','usuario':'ADMIN','contrasena':'ClaveSegura123','rol':'Operario'},'/usuarios')
    assert 'ya existe' in r.get_data(as_text=True)
    with app.app_context():
        assert Usuario.query.filter_by(usuario='admin').count()==1


def test_cp03_editar_y_desactivar_usuario(app,web):
    login(web)
    uid=2
    r=post(web,f'/usuarios/{uid}/editar',{'nombre':'Operario Editado','usuario':'operario','rol':'Operario','contrasena':''},f'/usuarios/{uid}/editar')
    assert 'actualizados' in r.get_data(as_text=True)
    post(web,f'/usuarios/{uid}/estado',{},'/usuarios')
    with app.app_context():
        u=db.session.get(Usuario,uid)
        assert u.nombre=='Operario Editado' and not u.activo


def test_cp04_cliente_y_vehiculo(app,web):
    login(web)
    post(web,'/clientes',{'documento':'DOC9009','nombre':'Cliente Nuevo'},'/clientes')
    with app.app_context():
        cid=Cliente.query.filter_by(documento='DOC9009').one().id
    post(web,'/vehiculos',{'placa':'XYX321','tipo':'Carro','cliente_id':str(cid)},'/vehiculos')
    with app.app_context():
        assert Vehiculo.query.filter_by(placa='XYX321').one().cliente_id==cid


def test_cp05_crear_filtrar_celdas(app,web):
    login(web)
    post(web,'/celdas/nueva',{'numero':'C-99','tipo':'Carro'},'/celdas')
    r=web.get('/celdas?tipo=Carro&estado=Disponible').get_data(as_text=True)
    assert 'C-99' in r and 'M-01' not in r and 'C-03' not in r


def test_cp06_bloquear_celda_ocupada(app,web):
    login(web)
    post(web,'/entradas',{'placa':'ABC123','celda_id':'1'},'/entradas')
    r=post(web,'/celdas/1/editar',{'numero':'C-66','tipo':'Moto'},'/celdas/1/editar')
    assert 'No puedes editar una celda ocupada' in r.get_data(as_text=True)
    r=post(web,'/celdas/1/estado',{'estado':'Fuera de servicio'},'/celdas')
    assert 'No puedes modificar una celda ocupada' in r.get_data(as_text=True)
    with app.app_context():
        c=db.session.get(Celda,1)
        assert (c.numero,c.tipo,c.estado)==('C-01','Carro','Ocupada')


def test_cp07_consulta_previa_de_cliente_y_vigencia(web):
    login(web)
    data=json_vehiculo(web,'abc123')
    assert data['autorizado'] and data['cliente']=='Maria Torres'
    assert data['tipo']=='Carro' and data['mensualidad']['pagada']
    assert data['mensualidad']['vigente'] and data['mensualidad']['inicio']
    assert 'resultado-consulta' in web.get('/entradas').get_data(as_text=True)


def test_cp08_filtrar_celdas_compatibles(web):
    login(web)
    celdas=json_vehiculo(web,'ABC123')['celdas']
    assert {c['numero'] for c in celdas}=={'C-01','C-02'}
    assert all(c['tipo']=='Carro' for c in celdas)


def test_cp09_integracion_entrada_salida(app,web):
    login(web)
    r=post(web,'/entradas',{'placa':'ABC123','celda_id':'1'},'/entradas')
    assert 'Entrada #' in r.get_data(as_text=True)
    with app.app_context():
        m=Movimiento.query.one();mid=m.id
        assert m.estado=='Activo' and m.usuario_entrada_id==1
        assert m.usuario_salida_id is None and m.fecha_salida is None
        assert db.session.get(Celda,1).estado=='Ocupada'
    r=post(web,'/salidas',{'movimiento_id':str(mid)},'/salidas')
    assert 'Celda liberada' in r.get_data(as_text=True)
    with app.app_context():
        m=Movimiento.query.one()
        assert m.estado=='Cerrado' and m.usuario_salida_id==1
        assert db.session.get(Celda,1).estado=='Disponible'


def test_cp10_descarga_y_restauracion(app,web,tmp_path):
    login(web)
    r=post(web,'/respaldo',{},'/')
    assert r.status_code==200
    assert 'attachment' in r.headers['Content-Disposition']
    assert r.data.startswith(b'SQLite format 3\x00')
    descarga=tmp_path/'descarga.db';descarga.write_bytes(r.data)
    assert verificar_archivo_respaldo(descarga)['usuario']==3
    recuperada=tmp_path/'restaurada.db'
    ruta,conteos=restaurar(descarga,recuperada)
    assert ruta==recuperada and verificar_archivo_respaldo(ruta)==conteos


def test_cp11_acceso_denegado_para_operario(web):
    login(web,'operario')
    for route in ['/usuarios','/clientes','/vehiculos','/pagos']:
        assert web.get(route).status_code==403
    for route in ['/celdas/nueva','/respaldo','/usuarios/1/estado']:
        assert web.post(route,data={'csrf_token':token(web)}).status_code==403


def test_cp12_cuenta_inactiva_no_inicia_sesion(web):
    page=post(web,'/login',{'usuario':'inactivo','contrasena':'Password123'},'/login')
    assert 'incorrectos' in page.get_data(as_text=True)
    assert web.get('/usuarios').status_code==302


def test_cp13_campos_usuario_obligatorios(app,web):
    login(web)
    r=post(web,'/usuarios',{'nombre':'','usuario':'x','contrasena':'ClaveSegura123','rol':'Operario'},'/usuarios')
    assert 'obligatorio' in r.get_data(as_text=True)
    r=post(web,'/usuarios',{'nombre':'X','usuario':'xx','contrasena':'123','rol':'Operario'},'/usuarios')
    assert 'al menos 8' in r.get_data(as_text=True)
    with app.app_context():
        assert Usuario.query.filter(Usuario.usuario.in_(['x','xx'])).count()==0


def test_cp14_celda_duplicada(app,web):
    login(web)
    r=post(web,'/celdas/nueva',{'numero':'C-01','tipo':'Carro'},'/celdas')
    assert 'ya existe' in r.get_data(as_text=True)
    with app.app_context():
        assert Celda.query.filter_by(numero='C-01').count()==1


def test_cp15_deshabilitar_y_rehabilitar(app,web):
    login(web)
    post(web,'/celdas/1/estado',{'estado':'Fuera de servicio'},'/celdas')
    assert 'C-01' not in {c['numero'] for c in json_vehiculo(web,'ABC123')['celdas']}
    post(web,'/celdas/1/estado',{'estado':'Disponible'},'/celdas')
    assert 'C-01' in {c['numero'] for c in json_vehiculo(web,'ABC123')['celdas']}


@pytest.mark.parametrize('celda_id', ['3','4'])
def test_cp16_rechazar_celda_no_compatible_o_inhabilitada(app,web,celda_id):
    login(web)
    r=post(web,'/entradas',{'placa':'ABC123','celda_id':celda_id},'/entradas')
    assert 'no es compatible' in r.get_data(as_text=True) or 'no está disponible' in r.get_data(as_text=True)
    with app.app_context():
        assert Movimiento.query.count()==0


def test_cp17_mensualidad_vencida(app,web):
    login(web)
    assert json_vehiculo(web,'LMN456')['autorizado'] is False
    post(web,'/entradas',{'placa':'LMN456','celda_id':'1'},'/entradas')
    with app.app_context():
        assert Movimiento.query.count()==0


def test_cp18_rechazar_ingreso_duplicado(app,web):
    login(web)
    post(web,'/entradas',{'placa':'ABC123','celda_id':'1'},'/entradas')
    r=post(web,'/entradas',{'placa':'ABC123','celda_id':'2'},'/entradas')
    assert 'ya está dentro' in r.get_data(as_text=True)
    with app.app_context():
        assert Movimiento.query.filter_by(estado='Activo').count()==1


def test_cp19_tiempo_consulta_referencia_local(web):
    # Verificación automática de referencia local. La compatibilidad real de
    # Chrome/Edge y los tiempos en Windows también requieren prueba manual.
    login(web)
    comienzo=perf_counter()
    for _ in range(3):
        assert web.get('/celdas').status_code==200
        assert web.get('/usuarios').status_code==200
        assert json_vehiculo(web,'ABC123')['autorizado']
    segundos=perf_counter()-comienzo
    assert segundos < 15, f'Consultas de prueba extraordinariamente lentas: {segundos:.2f}s'


def test_csrf_real_impide_post_sin_token(app,web):
    login(web)
    r=web.post('/usuarios',data={'nombre':'Intruso','usuario':'sin_csrf',
                                 'contrasena':'Password123','rol':'Operario'})
    assert r.status_code==400
    with app.app_context():
        assert Usuario.query.filter_by(usuario='sin_csrf').first() is None


def test_filtros_usuarios_y_cliente_inexistente(web):
    login(web)
    html=web.get('/usuarios?buscar=operario&rol=Operario&estado=inactivo').get_data(as_text=True)
    assert 'Operario Inactivo' in html and 'Administrador Principal' not in html
    sin_placa=web.get('/api/vehiculos/consulta?placa=NOEXISTE')
    assert sin_placa.status_code==404 and not sin_placa.json['autorizado']
